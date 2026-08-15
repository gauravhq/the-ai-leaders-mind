"""BookHarness marketing-site verifier (built Eleventy _site directory; stdlib only, no network).

Given the BUILT static site (the Eleventy `_site` output dir, see templates/website/site-scaffold.md
and STAGE 9 in BOOK_HARNESS.md), this reports a PASS/FAIL line per rule and exits 0 only if every
GATING rule passes, else 1. It is the runnable half of checklist 25 (Marketing Website): the things
that checklist currently asks a human to eyeball (sitemap/RSS/JSON-LD validity, no dangling links, no
em dashes, no future-dated posts) are asserted mechanically here so a broken build cannot ship silently.

It reads the rendered files themselves, so it works on a site built by any Eleventy config, not just
this harness's scaffold. It does NOT crawl the network and never fetches anything.

GATING rules (all must pass to exit 0):
  SITEMAP   sitemap.xml exists, is well-formed XML, lists >= 1 <loc>, every <loc> is absolute (http/https),
            and no <lastmod> is in the future.
  FEED      feed.xml exists, is well-formed RSS 2.0 (rss > channel > item), every item has a non-empty
            title, link, and guid, every <pubDate> parses as RFC-822, and none is in the future.
  ROBOTS    robots.txt exists and carries a "Sitemap:" line.
  LLMS      llms.txt exists (the LLM-readable one-page map).
  JSONLD    every <script type="application/ld+json"> block in every .html page parses as valid JSON
            (this is the guard for the HTML-escaped &quot;/&#39; JSON-LD bug the scaffold warns about).
  ENTITY    if a Person JSON-LD @id exists, some WebSite/Book author references it (the author reads as
            ONE connected entity, not three unlinked name mentions). Skipped when no Person @id is present.
  LINKS     every site-internal href/src in every .html page resolves to a real file in _site
            (external http/https/mailto/tel/# refs are ignored).
  EMDASH    no em dash (U+2014) in any rendered .html/.xml/.txt output (the harness's zero-em-dash rule
            applied to the site the same way scan.py applies it to the book).
  FAQCOUNT  if a FAQPage is present, its mainEntity lists >= 100 questions (checklist 25 item 14d).
            Advisory (skipped) when the built site ships no FAQPage.

ADVISORY rules (surfaced, never block): JSONLD-PRESENT (the site ships some structured data),
FAVICON (a favicon file exists so the site serves no /favicon.ico 404).

Pure helpers (import and unit-test WITHOUT a built site):
  jsonld_blocks(html)                 -> list  raw JSON strings inside <script type=ld+json> tags
  parse_jsonld(html)                  -> tuple (parsed_objs, error_strings)
  entities_by_id(parsed_objs)         -> tuple (person_ids:set, author_refs:set)
  internal_refs(html)                 -> list  every internal href/src value (external schemes dropped)
  url_to_candidates(ref, page_rel)    -> list  candidate _site-relative file paths a ref could resolve to
  is_absolute_url(loc)               -> bool
  rfc822_future(datestr, now=None)    -> tuple (parsed_ok, is_future)
  w3cdate_future(datestr, now=None)   -> tuple (parsed_ok, is_future)
  has_emdash(text)                    -> bool

Usage:  python verify_site.py PATH_TO_BUILT_SITE          (default: ./_site)

Origin: this harness (fills the runnable gap under checklist 25 / BOOK_HARNESS STAGE 9). Models its
gating/reporting shape on tools/verify_epub.py so the two site/eBook verifiers read the same way.
"""
import json
import os
import posixpath
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

sys.stdout.reconfigure(encoding="utf-8")

EM_DASH = "—"
# a small clock-skew grace so a build finishing at the same second a post is dated is not "future"
_FUTURE_GRACE_SECONDS = 300
# checklist 25 item 14d: a FAQPage must carry at least this many research-based questions
FAQ_MIN = 100

_LDJSON_RE = re.compile(
    r'<script[^>]*type\s*=\s*["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.I | re.S,
)
_REF_RE = re.compile(r'(?:href|src)\s*=\s*(["\'])(.*?)\1', re.I)
_EXTERNAL_RE = re.compile(r'^(?:https?:|mailto:|tel:|data:|javascript:|#)', re.I)


# ---------------- pure helpers ----------------
def has_emdash(text):
    return EM_DASH in (text or "")


def is_absolute_url(loc):
    return bool(re.match(r'^https?://', (loc or "").strip(), re.I))


def jsonld_blocks(html):
    """Return the raw text inside every <script type="application/ld+json"> block."""
    return [m.group(1).strip() for m in _LDJSON_RE.finditer(html or "")]


def parse_jsonld(html):
    """Parse every ld+json block. Returns (parsed_objects, error_strings).

    A block may be a single object or a list; both are flattened into parsed_objects.
    An error string is recorded per block that is not valid JSON (this is the check that catches
    the HTML-escaped &quot;/&#39; corruption the scaffold warns about)."""
    parsed, errors = [], []
    for i, raw in enumerate(jsonld_blocks(html)):
        try:
            obj = json.loads(raw)
        except Exception as e:  # noqa: BLE001 - report the block, do not crash the gate
            snippet = raw[:60].replace("\n", " ")
            errors.append(f"block #{i + 1} is not valid JSON: {e} :: {snippet}")
            continue
        if isinstance(obj, list):
            parsed.extend(x for x in obj if isinstance(x, dict))
        elif isinstance(obj, dict):
            # a @graph container holds its nodes in a list
            graph = obj.get("@graph")
            if isinstance(graph, list):
                parsed.extend(x for x in graph if isinstance(x, dict))
            else:
                parsed.append(obj)
    return parsed, errors


def _author_ref_ids(node):
    """Collect @id values referenced by an author (or publisher) property of a JSON-LD node."""
    out = set()
    for key in ("author", "publisher", "creator"):
        val = node.get(key)
        cands = val if isinstance(val, list) else [val]
        for c in cands:
            if isinstance(c, dict) and c.get("@id"):
                out.add(c["@id"])
            elif isinstance(c, str) and c.startswith(("http", "#", "urn:")):
                out.add(c)
    return out


def entities_by_id(parsed_objs):
    """Return (person_ids, author_refs): the @ids of Person nodes, and the @ids referenced as
    author/publisher/creator by any node. The ENTITY gate holds when every Person @id is referenced."""
    person_ids, author_refs = set(), set()
    for node in parsed_objs:
        t = node.get("@type")
        types = t if isinstance(t, list) else [t]
        if "Person" in types and node.get("@id"):
            person_ids.add(node["@id"])
        author_refs |= _author_ref_ids(node)
    return person_ids, author_refs


def internal_refs(html):
    """Every internal href/src value in the HTML (external schemes and pure #fragments dropped)."""
    out = []
    for m in _REF_RE.finditer(html or ""):
        ref = m.group(2).strip()
        if not ref or _EXTERNAL_RE.match(ref):
            continue
        out.append(ref)
    return out


def url_to_candidates(ref, page_rel):
    """Candidate _site-relative POSIX file paths a ref could resolve to.

    page_rel is the current page's path relative to the site root (POSIX, e.g. "blog/x/index.html").
    A root-absolute ref ("/blog/x/") resolves from the site root; a relative ref resolves from the
    page's directory. A directory-style URL ("foo/") maps to "foo/index.html". The fragment/query is
    stripped. Returns >= 1 candidate; the caller passes if ANY candidate exists on disk."""
    ref = ref.split("#", 1)[0].split("?", 1)[0]
    if not ref:
        return []
    if ref.startswith("/"):
        base = ref.lstrip("/")
    else:
        page_dir = posixpath.dirname(page_rel)
        base = posixpath.normpath(posixpath.join(page_dir, ref))
    if base in ("", "."):
        base = "index.html"
    cands = [base]
    if ref.endswith("/") or not posixpath.splitext(base)[1]:
        cands.append(posixpath.join(base, "index.html").replace("\\", "/"))
        cands.append(base + ".html")
    return [c.replace("\\", "/").lstrip("/") for c in cands]


def rfc822_future(datestr, now=None):
    """(parsed_ok, is_future) for an RFC-822 date (RSS <pubDate>)."""
    now = now or datetime.now(timezone.utc)
    try:
        dt = parsedate_to_datetime(datestr)
    except Exception:  # noqa: BLE001
        return (False, False)
    if dt is None:
        return (False, False)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (True, (dt - now).total_seconds() > _FUTURE_GRACE_SECONDS)


def w3cdate_future(datestr, now=None):
    """(parsed_ok, is_future) for a W3C/ISO-8601 date (sitemap <lastmod>)."""
    now = now or datetime.now(timezone.utc)
    s = (datestr or "").strip()
    if not s:
        return (False, False)
    iso = s.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(iso)
    except Exception:  # noqa: BLE001
        # a bare date (YYYY-MM-DD) is valid W3C datetime for sitemaps
        try:
            dt = datetime.strptime(s[:10], "%Y-%m-%d")
        except Exception:  # noqa: BLE001
            return (False, False)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (True, (dt - now).total_seconds() > _FUTURE_GRACE_SECONDS)


def _localname(tag):
    return tag.rsplit("}", 1)[-1].lower()


# ---------------- file-level checks ----------------
def _read(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _iter_files(root, exts):
    for dirpath, _dirs, names in os.walk(root):
        for n in names:
            if os.path.splitext(n)[1].lower() in exts:
                yield os.path.join(dirpath, n)


def check_sitemap(root, results, now):
    path = os.path.join(root, "sitemap.xml")
    if not os.path.exists(path):
        results.append(("SITEMAP: sitemap.xml present", False, "not found at site root"))
        return
    try:
        tree = ET.parse(path)
    except Exception as e:  # noqa: BLE001
        results.append(("SITEMAP: well-formed XML", False, str(e)))
        return
    locs, future = [], []
    for el in tree.iter():
        if _localname(el.tag) == "loc" and (el.text or "").strip():
            locs.append(el.text.strip())
        if _localname(el.tag) == "lastmod":
            ok, fut = w3cdate_future(el.text or "", now)
            if ok and fut:
                future.append((el.text or "").strip())
    results.append(("SITEMAP: >= 1 <loc>", len(locs) >= 1, f"{len(locs)} url(s)"))
    non_abs = [l for l in locs if not is_absolute_url(l)]
    results.append(("SITEMAP: every <loc> absolute", not non_abs,
                    "all absolute" if not non_abs else f"{len(non_abs)} relative, e.g. {non_abs[0]}"))
    results.append(("SITEMAP: no future <lastmod>", not future,
                    "none future" if not future else f"future-dated: {future[0]}"))


def check_feed(root, results, now):
    path = os.path.join(root, "feed.xml")
    if not os.path.exists(path):
        results.append(("FEED: feed.xml present", False, "not found at site root"))
        return
    try:
        tree = ET.parse(path)
    except Exception as e:  # noqa: BLE001
        results.append(("FEED: well-formed XML", False, str(e)))
        return
    root_el = tree.getroot()
    results.append(("FEED: root is <rss>", _localname(root_el.tag) == "rss", _localname(root_el.tag)))
    items = [el for el in tree.iter() if _localname(el.tag) == "item"]
    results.append(("FEED: >= 1 <item>", len(items) >= 1, f"{len(items)} item(s)"))
    missing, bad_dates, future = 0, [], []
    for it in items:
        kids = {_localname(k.tag): (k.text or "").strip() for k in list(it)}
        if not (kids.get("title") and kids.get("link") and kids.get("guid")):
            missing += 1
        pd = kids.get("pubdate", "")
        if pd:
            ok, fut = rfc822_future(pd, now)
            if not ok:
                bad_dates.append(pd)
            elif fut:
                future.append(pd)
    results.append(("FEED: every item has title/link/guid", missing == 0,
                    "all complete" if missing == 0 else f"{missing} item(s) missing a field"))
    results.append(("FEED: every <pubDate> parses (RFC-822)", not bad_dates,
                    "all parse" if not bad_dates else f"unparseable: {bad_dates[0]}"))
    results.append(("FEED: no future <pubDate>", not future,
                    "none future" if not future else f"future-dated: {future[0]}"))


def check_robots_llms(root, results):
    robots = os.path.join(root, "robots.txt")
    if not os.path.exists(robots):
        results.append(("ROBOTS: robots.txt present", False, "not found at site root"))
    else:
        txt = _read(robots)
        has_sitemap = any(l.strip().lower().startswith("sitemap:") for l in txt.splitlines())
        results.append(("ROBOTS: has a Sitemap: line", has_sitemap,
                        "Sitemap line found" if has_sitemap else "no Sitemap: line"))
    llms = os.path.join(root, "llms.txt")
    results.append(("LLMS: llms.txt present", os.path.exists(llms),
                    "found" if os.path.exists(llms) else "not found at site root"))


def check_html(root, results, advisories):
    html_files = sorted(_iter_files(root, {".html", ".htm"}))
    all_files = set()
    for dirpath, _d, names in os.walk(root):
        for n in names:
            rel = os.path.relpath(os.path.join(dirpath, n), root).replace("\\", "/")
            all_files.add(rel)

    json_errors, dangling, person_ids_all, author_refs_all, jsonld_seen = [], [], set(), set(), 0
    for hp in html_files:
        html = _read(hp)
        page_rel = os.path.relpath(hp, root).replace("\\", "/")
        parsed, errs = parse_jsonld(html)
        jsonld_seen += len(jsonld_blocks(html))
        for e in errs:
            json_errors.append(f"{page_rel}: {e}")
        pids, arefs = entities_by_id(parsed)
        person_ids_all |= pids
        author_refs_all |= arefs
        for ref in internal_refs(html):
            cands = url_to_candidates(ref, page_rel)
            if cands and not any(c in all_files for c in cands):
                dangling.append(f"{page_rel} -> {ref}")

    results.append(("JSONLD: every ld+json block is valid JSON", not json_errors,
                    "all valid" if not json_errors else f"{len(json_errors)} bad, e.g. {json_errors[0]}"))
    # ENTITY gate only applies when a Person @id is actually present.
    if person_ids_all:
        unref = [pid for pid in person_ids_all if pid not in author_refs_all]
        results.append(("ENTITY: every Person @id is referenced as author", not unref,
                        "author entity linked" if not unref else f"unreferenced Person @id: {unref[0]}"))
    results.append(("LINKS: every internal href/src resolves", not dangling,
                    "all resolve" if not dangling else f"{len(dangling)} dangling, e.g. {dangling[0]}"))

    advisories.append(("JSONLD-PRESENT: site ships structured data", jsonld_seen > 0,
                       f"{jsonld_seen} ld+json block(s)" if jsonld_seen else "no JSON-LD found"))
    favicon = any(os.path.exists(os.path.join(root, f))
                  for f in ("favicon.svg", "favicon.ico", "favicon.png"))
    advisories.append(("FAVICON: a favicon file exists", favicon,
                       "present" if favicon else "no favicon.{svg,ico,png} (a /favicon.ico 404 will occur)"))


def check_emdash(root, results):
    hits = []
    for fp in _iter_files(root, {".html", ".htm", ".xml", ".txt"}):
        if has_emdash(_read(fp)):
            hits.append(os.path.relpath(fp, root).replace("\\", "/"))
    results.append(("EMDASH: zero em dashes in rendered output", not hits,
                    "0 em dashes" if not hits else f"em dash in {len(hits)} file(s), e.g. {hits[0]}"))


def check_faq(root, results, advisories):
    """A FAQPage (checklist 25 item 14d) must carry >= FAQ_MIN questions. GATING when a FAQPage is
    present; advisory when the built site has none (a minimal fixture may omit it)."""
    total_q, found = 0, False
    for hp in sorted(_iter_files(root, {".html", ".htm"})):
        parsed, _errs = parse_jsonld(_read(hp))
        for node in parsed:
            t = node.get("@type")
            types = t if isinstance(t, list) else [t]
            if "FAQPage" in types:
                found = True
                me = node.get("mainEntity")
                if isinstance(me, list):
                    total_q += sum(1 for x in me if isinstance(x, dict))
    if found:
        results.append((f"FAQCOUNT: FAQPage carries >= {FAQ_MIN} questions",
                        total_q >= FAQ_MIN, f"{total_q} question(s)"))
    else:
        advisories.append(("FAQCOUNT: a FAQPage is present",
                           False, "no FAQPage JSON-LD found (checklist 25 item 14d)"))


def verify(root, now=None):
    """Run every check against a built site dir. Returns (results, advisories, all_pass)."""
    now = now or datetime.now(timezone.utc)
    results, advisories = [], []
    check_sitemap(root, results, now)
    check_feed(root, results, now)
    check_robots_llms(root, results)
    check_html(root, results, advisories)
    check_emdash(root, results)
    check_faq(root, results, advisories)
    all_pass = all(ok for _n, ok, _e in results)
    return results, advisories, all_pass


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    root = args[0] if args else os.path.join(os.getcwd(), "_site")
    if not os.path.isdir(root):
        print(f"Built site directory not found: {root}")
        print("Point this at the Eleventy _site output dir (see BOOK_HARNESS.md STAGE 9).")
        sys.exit(1)

    results, advisories, all_pass = verify(root)
    print("=" * 78)
    print(f"BOOKHARNESS SITE VERIFY  ->  {root}")
    print("=" * 78)
    for name, ok, ev in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name:<48}  {ev}")
    if advisories:
        print("\n-- ADVISORIES (surfaced, do NOT block) --")
        for name, ok, ev in advisories:
            print(f"  [{'ok' if ok else 'REVIEW'}]  {name:<46}  {ev}")
    print("\n" + ("ALL SITE GATES PASS." if all_pass
                  else "ONE OR MORE SITE GATES FAILED. Fix before publishing (checklist 25)."))
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
