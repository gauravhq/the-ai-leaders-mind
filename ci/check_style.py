"""CI humanizer gate: run the vendored BookHarness scan.py over the blog posts AND the FAQ answers.

Strips YAML front matter from src/posts/*.md and extracts src/_data/faqs.js Q&As into a temp dir of
body-only Markdown, then runs `scan.py --gate` on it. scan.py --gate exits nonzero ONLY on HARD defects
(em dashes, semicolons out of the Section 15 band, curly punctuation, banned words/phrases); soft
advisories never block. This is the source-side style gate that complements verify_site.py's rendered
EMDASH gate.

Usage: python ci/check_style.py [SRC_DIR]     (default: ./src)
"""
import glob
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def strip_front_matter(text):
    m = re.match(r"^---\n.*?\n---\n", text, re.S)
    return text[m.end():] if m else text


def title_of(text):
    m = re.search(r'title:\s*"([^"]*)"', text)
    return m.group(1) if m else "post"


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.getcwd(), "src")
    tmp = tempfile.mkdtemp(prefix="ci_style_")
    n = 0

    for f in sorted(glob.glob(os.path.join(src, "posts", "*.md"))):
        t = open(f, encoding="utf-8").read()
        out = "# " + title_of(t) + "\n\n" + strip_front_matter(t).strip() + "\n"
        open(os.path.join(tmp, os.path.basename(f)), "w", encoding="utf-8", newline="\n").write(out)
        n += 1

    faqjs = os.path.join(src, "_data", "faqs.js")
    if os.path.exists(faqjs):
        raw = open(faqjs, encoding="utf-8").read()
        data = json.loads(raw.split("module.exports =", 1)[1].strip().rstrip(";"))
        groups = data["groups"] if isinstance(data, dict) and "groups" in data else data
        for g in groups:
            md = "# " + g.get("category", "faq") + "\n\n" + "\n\n".join(
                it["q"] + "\n" + it["a"] for it in g.get("items", []))
            open(os.path.join(tmp, "faq-" + str(g.get("id", "x")) + ".md"),
                 "w", encoding="utf-8", newline="\n").write(md + "\n")
            n += 1

    print("ci/check_style: scanning %d source file(s) (posts + FAQ) for HARD style defects" % n)
    sys.exit(subprocess.call([sys.executable, os.path.join(HERE, "scan.py"), "--gate", tmp]))


if __name__ == "__main__":
    main()
