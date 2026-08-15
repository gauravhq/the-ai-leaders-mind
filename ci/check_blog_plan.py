"""BookHarness blog-plan verifier (SOURCE-level; stdlib only, no network).

Asserts the blog obeys checklist 25 items 7d + 12: EXACTLY 200 posts, a strict WEEKLY cadence, and a
FIRST post dated ONE YEAR BEFORE the site launch. This complements tools/verify_site.py (which checks
the BUILT _site): a genuine one-year-before drip only renders ~52 pages at launch, so the full 200 and
the weekly schedule can only be counted at the SOURCE (src/posts), not in the built output.

GATING checks (all must pass to exit 0):
  COUNT           src/posts holds EXACTLY 200 dated posts (YYYY-MM-DD-<slug>.md).
  CADENCE         every consecutive pair of posts is exactly 7 days apart (weekly, no gaps/dupes).
  START           (when the launch date is known) the first post is within 10 days of launch minus one
                  year. LIVE-AT-LAUNCH: ~52 posts are dated on or before launch.
Launch date resolution: --launch YYYY-MM-DD, else SRC/_data/site.js `datePublished:"YYYY-MM-DD"`. When
neither is available the START/LIVE checks are skipped (noted), and COUNT + CADENCE still gate.

Usage: python check_blog_plan.py [SRC_DIR] [--launch YYYY-MM-DD]     (SRC_DIR default: ./src)

Origin: this harness (runnable half of checklist 25 items 7d/12, the source-side companion to
tools/verify_site.py).
"""
import datetime
import glob
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

EXPECTED_POSTS = 200
_NAME_RE = re.compile(r"(\d{4}-\d{2}-\d{2})-.+\.md$")


def post_dates(posts_dir):
    """Sorted list of post dates parsed from YYYY-MM-DD-<slug>.md filenames in posts_dir."""
    out = []
    for f in glob.glob(os.path.join(posts_dir, "*.md")):
        m = _NAME_RE.match(os.path.basename(f))
        if m:
            out.append(datetime.date.fromisoformat(m.group(1)))
    return sorted(out)


def read_launch(src):
    """Best-effort launch date from src/_data/site.js `datePublished:"YYYY-MM-DD"` (the book/site pub date)."""
    p = os.path.join(src, "_data", "site.js")
    if os.path.exists(p):
        m = re.search(r'datePublished:\s*"(\d{4}-\d{2}-\d{2})"', open(p, encoding="utf-8").read())
        if m:
            return datetime.date.fromisoformat(m.group(1))
    return None


def minus_one_year(d):
    try:
        return d.replace(year=d.year - 1)
    except ValueError:  # Feb 29 -> Feb 28 the prior year
        return d.replace(year=d.year - 1, day=28)


def check(src, launch=None):
    """Return (results, notes): results are (name, ok, evidence) gating tuples; notes are advisory strings."""
    results, notes = [], []
    dates = post_dates(os.path.join(src, "posts"))
    n = len(dates)
    results.append((f"COUNT: exactly {EXPECTED_POSTS} posts", n == EXPECTED_POSTS, f"{n} post(s)"))

    gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
    bad = [g for g in gaps if g != 7]
    results.append(("CADENCE: weekly (+7 days each)", len(dates) > 1 and not bad,
                    "all 7d apart" if not bad else f"{len(bad)} non-weekly gap(s), e.g. {bad[0]}d"))

    if launch is None:
        launch = read_launch(src)
    if launch and dates:
        target = minus_one_year(launch)
        delta = abs((dates[0] - target).days)
        results.append((f"START: first post ~1yr before launch ({launch})", delta <= 10,
                        f"first={dates[0]} target={target} ({delta}d off)"))
        live = sum(1 for d in dates if d <= launch)
        results.append(("LIVE-AT-LAUNCH: ~52 posts live", 50 <= live <= 54, f"{live} live at launch"))
    else:
        notes.append("launch date unknown (pass --launch or set site.js datePublished): START/LIVE skipped")
    return results, notes


def main():
    argv = sys.argv[1:]
    launch = None
    if "--launch" in argv:
        i = argv.index("--launch")
        launch = datetime.date.fromisoformat(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    src = argv[0] if argv else os.path.join(os.getcwd(), "src")
    if not os.path.isdir(os.path.join(src, "posts")):
        print(f"No posts dir found under: {src}")
        print("Point this at the Eleventy source dir that contains posts/ (see checklist 25 item 7d).")
        sys.exit(1)

    results, notes = check(src, launch)
    print("=" * 72)
    print(f"BOOKHARNESS BLOG-PLAN CHECK  ->  {src}")
    print("=" * 72)
    for name, ok, ev in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name:<46}  {ev}")
    for note in notes:
        print(f"  [note]  {note}")
    all_pass = all(ok for _n, ok, _e in results)
    print("\n" + ("BLOG PLAN OK." if all_pass
                  else "BLOG PLAN FAILED. Fix before publishing (checklist 25 items 7d / 12)."))
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
