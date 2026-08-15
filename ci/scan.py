"""BookHarness style + burstiness + banned-language scanner.

Reads the Markdown chapter files of a manuscript and reports, per chapter and per manuscript:
em dashes, semicolons, banned words, banned phrases, ellipsis overuse, sentence-length variety,
fragment count, And/But/So openings. Enforces STYLE_RULES.md via tools/style_rules.py.

Usage:
    python scan.py [MANUSCRIPT_DIR]
Default MANUSCRIPT_DIR: ./01-manuscript relative to the current directory.
Exit code 0 = all targets met; 1 = at least one violation.

Origin: JOMO run_scan.py, generalized to any manuscript directory and wired to style_rules.py.
"""
import os, re, sys, glob

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style_rules import (BANNED_WORDS, BANNED_PHRASES, STIFF_TRANSITIONS,
                         PREACHY_PHRASES, TARGETS, REPEATED_OPENER_TICS, REASSURANCE_TICS,
                         HUMAN_TEXTURE_GATES)

# Consecutive-word doublings that are legitimate English (never flag as a sweep seam).
DOUBLE_WORD_ALLOW = {"had", "that", "so", "no", "very", "really", "ha"}
# Dinkus / scene-break lines that legitimately hold an odd count of '*'.
_DINKUS = {"* * *", "***", "• • •", "* * * *"}


def _syllables(word):
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    groups = re.findall(r"[aeiouy]+", w)
    n = len(groups)
    if w.endswith("e") and not w.endswith(("le", "ue", "ee", "ie")):
        n -= 1
    return max(1, n)


def readability(body):
    """Flesch Reading Ease + Flesch-Kincaid grade level (estimates)."""
    words = re.findall(r"[A-Za-z']+", body)
    sents = [s for s in re.split(r"[.!?]+", body) if s.strip()]
    nw, ns = len(words), max(1, len(sents))
    if nw == 0:
        return 0.0, 0.0
    syl = sum(_syllables(w) for w in words)
    wps, spw = nw / ns, syl / nw
    fre = 206.835 - 1.015 * wps - 84.6 * spw
    grade = 0.39 * wps + 11.8 * spw - 15.59
    return round(fre, 1), round(grade, 1)


def analyze(text):
    body = re.sub(r"^#.*$", "", text, flags=re.MULTILINE).strip()
    words = body.split()
    wc = len(words)
    fre, grade = readability(body)
    sents = [s.strip() for s in re.split(r"[.!?]+", body)
             if len(s.strip().split()) >= 2]
    sl = [len(s.split()) for s in sents]
    avg = sum(sl) / len(sl) if sl else 0
    std = (sum((x - avg) ** 2 for x in sl) / len(sl)) ** 0.5 if sl else 0
    em = text.count(chr(0x2014)) + len(re.findall(r"(?<!-)--(?!-)", text))
    semi = text.count(";")
    # curly/smart punctuation: manuscripts are authored in ASCII punctuation; a
    # curly quote or apostrophe is a copy-paste defect that corrupts DOCX build.
    curly = len(re.findall(r"[‘’“”]", text))
    # doubled consecutive word ("the the", "and and") = classic mechanical-sweep seam. A sweep seam is
    # a lowercase function word; a repeated word inside a TITLE or proper noun ("Making Hybrid Work
    # Work", "New York, New York") is legitimate, so both-capitalized repeats are exempt.
    dbl = []
    for m in re.finditer(r"\b(\w{2,})\s+(\w{2,})\b", text):
        a, b = m.group(1), m.group(2)
        if a.lower() != b.lower() or a.lower() in DOUBLE_WORD_ALLOW or a.isdigit():
            continue
        if a[0].isupper() and b[0].isupper():   # title / proper-noun repeat, not a sweep seam
            continue
        dbl.append(f"{a} {b}")
    # leaked markdown emphasis: a line with an odd number of '*' that is not a dinkus.
    star = sum(1 for ln in text.splitlines()
               if ln.strip() not in _DINKUS and ln.strip().count("*") % 2 == 1)
    elli = text.count("...") + text.count("…")
    abs_st = len(re.findall(r"(?:^|\.\s|!\s|\?\s)(And |But |So )", body))
    frags = len([s for s in sents if len(s.split()) <= 4])
    tl = text.lower()
    bw = [(w, len(re.findall(r"\b" + re.escape(w) + r"\b", tl)))
          for w in BANNED_WORDS]
    bw = [(w, c) for w, c in bw if c]
    bp = [(p, tl.count(p)) for p in BANNED_PHRASES]
    bp = [(p, c) for p, c in bp if c]
    pp = [(p, tl.count(p)) for p in PREACHY_PHRASES]
    pp = [(p, c) for p, c in pp if c]
    stiff = 0
    for w in STIFF_TRANSITIONS:
        stiff += len(re.findall(r"(?:^|\.\s|!\s|\?\s)" + w + r"\b", body))
    return dict(wc=wc, ns=len(sl), avg=round(avg, 1), std=round(std, 1),
                mn=min(sl) if sl else 0, mx=max(sl) if sl else 0,
                em=em, semi=semi, curly=curly, dbl=dbl, star=star,
                elli=elli, abs=abs_st, frags=frags,
                bw=bw, bp=bp, pp=pp, stiff=stiff, fre=fre, grade=grade)


def main():
    args = sys.argv[1:]
    # --gate: exit non-zero ONLY on HARD defects (em dash, semicolon, curly punctuation,
    # banned words/phrases, doubled-word seams, leaked markdown). Soft burstiness
    # advisories (variety, ellipsis, fragments, And/But/So, tics) are printed but do
    # NOT block. build_final_pdf.py calls this mode so a hard defect can never reach
    # the PDF, while a slightly-low sentence-variety score never blocks a ship.
    gate = "--gate" in args
    if gate:
        args.remove("--gate")
    grade_target = None
    if "--grade" in args:
        gi = args.index("--grade")
        grade_target = float(args[gi + 1])
        del args[gi:gi + 2]
    total_min = total_max = None
    if "--total-min" in args:
        ti = args.index("--total-min"); total_min = int(args[ti + 1]); del args[ti:ti + 2]
    if "--total-max" in args:
        ti = args.index("--total-max"); total_max = int(args[ti + 1]); del args[ti:ti + 2]
    min_std = TARGETS["sentence_std_min"]
    if "--min-std" in args:
        si = args.index("--min-std"); min_std = float(args[si + 1]); del args[si:si + 2]
    ms_dir = args[0] if args else os.path.join(os.getcwd(), "01-manuscript")
    files = sorted(glob.glob(os.path.join(ms_dir, "*.md")))
    if not files:
        print(f"No .md files found in {ms_dir}")
        sys.exit(2)

    total_em = total_semi = total_curly = total_dbl = total_star = 0
    total_bw, total_bp = {}, {}
    tic_counts = {}
    rows, violations = [], []
    total_hard = 0   # count of HARD defects across the manuscript (gate signal)

    for fp in files:
        name = os.path.splitext(os.path.basename(fp))[0]
        with open(fp, encoding="utf-8") as f:
            raw = f.read()
        if raw.lstrip().startswith("%%PART%%"):   # part-divider page, not prose
            continue
        tl_raw = raw.lower()
        for t in REPEATED_OPENER_TICS + REASSURANCE_TICS:   # checklist 24 advisory frequency audit
            c = len(re.findall(r"\b" + re.escape(t) + r"\b", tl_raw))
            if c:
                tic_counts[t] = tic_counts.get(t, 0) + c
        r = analyze(raw)
        rows.append((name, r))
        total_em += r["em"]
        total_semi += r["semi"]
        total_curly += r["curly"]
        total_dbl += len(r["dbl"])
        total_star += r["star"]
        for w, c in r["bw"]:
            total_bw[w] = total_bw.get(w, 0) + c
        for p, c in r["bp"]:
            total_bp[p] = total_bp.get(p, 0) + c

        # HARD defects: objective, always-wrong, block the build in --gate mode.
        hard = []
        if r["em"]:
            hard.append(f"EM DASHES: {r['em']}")
        # Semicolons are no longer a per-chapter HARD defect. Section 15 A3 makes them a manuscript-level
        # RATE band (0.5-2.0 per 1,000 words), checked as a SOFT advisory after the loop. Em dash stays hard.
        if r["curly"]:
            hard.append(f"CURLY/SMART PUNCTUATION: {r['curly']} (author in ASCII quotes)")
        if r["dbl"]:
            hard.append("DOUBLED WORDS (sweep seam): " + ", ".join(f"'{d}'" for d in r["dbl"][:8]))
        if r["star"]:
            hard.append(f"LEAKED MARKDOWN '*': {r['star']} line(s)")
        if r["bw"]:
            hard.append("WORDS: " + ", ".join(f"{w}({c})" for w, c in r["bw"]))
        if r["bp"]:
            hard.append("PHRASES: " + ", ".join(f"'{p}'({c})" for p, c in r["bp"]))
        # SOFT advisories: quality/burstiness signals; a human decides, never block a ship.
        soft = []
        if r["elli"] > TARGETS["ellipsis_max_per_chapter"]:
            soft.append(f"ELLIPSIS: {r['elli']} (max {TARGETS['ellipsis_max_per_chapter']})")
        if r["pp"]:
            soft.append("PREACHY: " + ", ".join(f"'{p}'({c})" for p, c in r["pp"]))
        if r["stiff"]:
            soft.append(f"STIFF OPENERS: {r['stiff']}")
        # Reference-style sections (appendix / app-x, glossary, references, notes, TOC, front/back
        # matter) are not narrative prose, so the burstiness checks do not apply to them.
        is_reference = re.search(
            r"appendix|app[-_]|glossary|reference|notes|toc|copyright|about|front|contents|"
            r"dedication|epigraph|preface|discussion|acknowledg",
            name, re.I)
        if r["wc"] > 800 and not is_reference:
            if r["std"] < min_std:
                soft.append(f"LOW VARIETY: std={r['std']} (target >= {min_std})")
            if r["frags"] < TARGETS["fragments_min"]:
                soft.append(f"FEW FRAGMENTS: {r['frags']} (target >= {TARGETS['fragments_min']})")
            if r["abs"] < TARGETS["abs_starts_min"]:
                soft.append(f"FEW And/But/So: {r['abs']} (target >= {TARGETS['abs_starts_min']})")
            if grade_target is not None and r["grade"] > grade_target:
                soft.append(f"READING LEVEL: grade {r['grade']} > target {grade_target}")
        total_hard += len(hard)
        if hard or soft:
            violations.append((name, hard, soft))

    print("=" * 78)
    print("BOOKHARNESS STYLE + BURSTINESS SCAN")
    print("=" * 78)
    print(f"Manuscript: {ms_dir}")
    print(f"Files: {len(files)}   Total em dashes: {total_em}   Total semicolons: {total_semi}")
    print(f"Curly/smart punctuation: {total_curly}   Doubled-word seams: {total_dbl}   "
          f"Leaked markdown '*': {total_star}")
    print("\n-- BANNED WORDS (manuscript) --")
    print("  CLEAN" if not total_bw else
          "\n".join(f"  {w}: {c}" for w, c in sorted(total_bw.items(), key=lambda x: -x[1])))
    print("\n-- BANNED PHRASES (manuscript) --")
    print("  CLEAN" if not total_bp else
          "\n".join(f"  '{p}': {c}" for p, c in sorted(total_bp.items(), key=lambda x: -x[1])))

    # Checklist 24 macro-authenticity audit: ADVISORY only (cumulative frequency, not a hard gate). A
    # human decides which to thin per Priority 1 (openers) / Priority 10 (reassurance). >= 8 flagged high.
    print("\n-- REPEATED OPENER / REASSURANCE TICS (checklist 24, advisory - watch cumulative frequency) --")
    if not tic_counts:
        print("  none")
    else:
        for t, c in sorted(tic_counts.items(), key=lambda x: -x[1]):
            print(f"  '{t}': {c}" + ("   <-- high, thin these first" if c >= 8 else ""))

    print(f"\n{'Chapter':<22}{'Words':>6}{'Snts':>5}{'Avg':>5}{'Std':>5}{'Frag':>5}"
          f"{'ABS':>4}{'Em':>3}{';':>3}{'GL':>6}{'FRE':>6}")
    print("-" * 78)
    for name, r in rows:
        print(f"{name[:22]:<22}{r['wc']:>6}{r['ns']:>5}{r['avg']:>5}{r['std']:>5}{r['frags']:>5}"
              f"{r['abs']:>4}{r['em']:>3}{r['semi']:>3}{r['grade']:>6}{r['fre']:>6}")
    print("GL = Flesch-Kincaid grade level, FRE = Flesch Reading Ease (higher = easier). "
          "Use --grade N to flag chapters above a target grade.")

    # length profile: total words + chapter-length variation (uniform lengths read inhuman)
    total_words = sum(r["wc"] for _, r in rows)
    chap_wc = [r["wc"] for _, r in rows if r["wc"] >= 600]
    ms_violations = []
    cv = 0.0
    if len(chap_wc) >= 3:
        m = sum(chap_wc) / len(chap_wc)
        sd = (sum((x - m) ** 2 for x in chap_wc) / len(chap_wc)) ** 0.5
        cv = sd / m if m else 0.0
    print("\n-- LENGTH PROFILE --")
    print(f"  Total words: {total_words}")
    if chap_wc:
        print(f"  Chapters (>=600w): {len(chap_wc)}  min {min(chap_wc)}  max {max(chap_wc)}  "
              f"mean {int(sum(chap_wc)/len(chap_wc))}  length-variation CV {cv:.2f}")
    if total_min and total_words < total_min:
        ms_violations.append(f"TOTAL {total_words} words < target min {total_min}")
    if total_max and total_words > total_max:
        ms_violations.append(f"TOTAL {total_words} words > target max {total_max}")
    if len(chap_wc) >= 3 and cv < 0.12:
        ms_violations.append(f"CHAPTERS TOO UNIFORM: length CV {cv:.2f} < 0.12 "
                             f"(vary chapter lengths; equal-length chapters read inhuman)")
    # Section 15 A3: semicolons are a RATE band, not a ban. SOFT advisory (never blocks a build) when the
    # whole-manuscript rate falls outside 0.5-2.0 per 1,000 words. Too few, including zero, is itself a
    # fingerprint; too many is a tell. Re-seed to the low end of the band, do not drive to zero.
    if total_words >= 2000:
        semi_per_1k = total_semi / total_words * 1000
        lo, hi = HUMAN_TEXTURE_GATES["semicolons_per_1k"]
        if not (lo <= semi_per_1k <= hi):
            ms_violations.append(f"SEMICOLON RATE {semi_per_1k:.2f}/1k outside band {lo}-{hi} "
                                 f"({total_semi} in {total_words} words; Section 15 A3)")

    print("\n-- VIOLATIONS --")
    if not violations and not ms_violations:
        print("  NONE. All targets met.")
    else:
        for name, hard, soft in violations:
            print(f"  {name}:")
            for i in hard:
                print(f"    - [HARD]  {i}")
            for i in soft:
                print(f"    - [soft]  {i}")
        for mv in ms_violations:
            print(f"  MANUSCRIPT [soft]: {mv}")

    print("\n-- GATE --")
    if total_hard:
        print(f"  HARD DEFECTS: {total_hard}  -> BUILD BLOCKED (fix before shipping).")
    else:
        print("  HARD DEFECTS: 0  -> build gate PASS (soft advisories, if any, are for human review).")

    if gate:
        # Build-gate mode: block only on objective hard defects.
        sys.exit(1 if total_hard else 0)
    # Full-audit mode: surface everything (hard + soft + manuscript-level) as before.
    sys.exit(1 if (violations or ms_violations or total_hard) else 0)


if __name__ == "__main__":
    main()
