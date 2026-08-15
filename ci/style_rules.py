"""Canonical rule lists for BookHarness tools.

This is the importable mirror of STYLE_RULES.md (the human-readable single source of truth).
scan.py, ai_audit_fix.py, and run_checklists.py all import from here so there is exactly one
place the banned-language rules live. If you change STYLE_RULES.md, change this file in the
same edit, and vice versa.
"""

# ---- Section 2: punctuation targets ----
EM_DASH = chr(0x2014)  # em dash, referenced as a code point to keep the literal glyph out of the file
ELLIPSIS = "…"

# ---- Section 3: banned words (Tier 1), target 0 each ----
BANNED_WORDS = [
    # verbs
    "delve", "leverage", "utilize", "harness", "streamline", "underscore", "foster",
    "embrace", "empower", "elevate", "unleash", "spearhead", "revolutionize", "catalyze",
    "reimagine", "illuminate", "elucidate", "showcase", "embark", "bolster", "augment",
    "cultivate", "galvanize", "facilitate", "commence", "ascertain", "endeavor", "curate",
    # adjectives
    "robust", "cutting-edge", "pivotal", "crucial", "vibrant", "intricate",
    "meticulous", "seamless", "groundbreaking", "holistic", "multifaceted", "nuanced",
    "transformative", "unprecedented", "unparalleled", "innovative", "compelling", "paramount",
    "quintessential", "nascent", "burgeoning", "ever-evolving",  # ever-evolving added 2026-08-15 (Section 15 B1)
    # nouns
    "tapestry", "realm", "paradigm", "synergy", "testament", "beacon", "cornerstone",
    "underpinnings", "interplay", "myriad", "plethora", "game-changer",  # game-changer added 2026-08-15 (B1)
    # adverbs
    "meticulously", "seamlessly", "pivotally", "profoundly", "indelibly", "intricately",
    "relentlessly", "tirelessly", "vibrantly",
]

# ---- Section 4: banned phrases, target 0 ----
BANNED_PHRASES = [
    "in today's", "in the ever-evolving", "in the rapidly shifting", "in the dynamic world",
    "in the realm of", "in the age of", "imagine a world where", "picture this",
    "have you ever wondered",
    "it is important to note", "it's important to note", "it is worth noting", "it's worth noting",
    "it should be noted", "it goes without saying",
    "at its core", "the reality is", "here's the thing", "let me be clear", "on a deeper level",
    "let's take a closer look", "let's dive into", "let's delve into", "let's explore",
    "let's break this down", "let's unpack", "when it comes to", "in this chapter we will",
    "it's not just", "not only", "it's not about",
    "on the one hand", "on the other hand",
    "in conclusion", "in summary", "to summarize", "the future looks bright",
    "only time will tell", "one thing is certain", "as we move forward", "at the end of the day",
    "experts believe", "studies show", "research suggests", "industry leaders agree",
    "a watershed moment", "a testament to", "serves as a reminder", "setting the stage for",
    "plays a crucial role", "has revolutionized", "stands as a testament to",
]

# stiff transitions (flagged at sentence start)
STIFF_TRANSITIONS = [
    "Moreover", "Furthermore", "Additionally", "Consequently", "Hence", "Indeed", "Thus",
    "Undoubtedly", "Certainly", "Arguably", "Nevertheless", "Notably", "Essentially",
    "Accordingly", "Subsequently",
]

# ---- Section 7: banned preachy phrases ----
PREACHY_PHRASES = [
    "true happiness comes from", "the secret to a good life", "what really matters is",
    "if you just", "all you have to do is", "the answer is simple", "once you realize",
    "when you finally understand", "the key to", "the truth is", "life is too short to",
    "you owe it to yourself", "you deserve to", "imagine a life where", "what if i told you",
    "here's what nobody tells you",
]

# ---- Checklist 24 (macro authenticity): repeated opener tics + reassurance formulas ----
# ADVISORY frequency audit only (scan.py prints, does not hard-fail). The AI-smell here is CUMULATIVE
# frequency + predictable placement, not presence, so a human decides which to cut per checklist 24
# Priority 1 (openers) / Priority 10 (reassurance). Counted with word boundaries (no nested double-count).
REPEATED_OPENER_TICS = [
    "here is", "one more thing", "the good news", "this matters because", "the difference is",
    "the point is", "that is the whole", "it is worth", "let me be honest", "notice what",
    "the thing about",
]
REASSURANCE_TICS = [
    "do not judge yourself", "not a character flaw", "you are human", "you will slip",
    "do not have to fix it", "be gentle", "not a failure", "is not failure", "be kind to yourself",
    "forgive yourself", "none of this is a", "this is not weakness", "you are not broken",
]

# ---- Per-chapter burstiness targets (Sections 6, 8) ----
# This is the CURRENTLY-ENFORCED subset (scan.py reads these). Section 15's richer bands are the target
# end-state in HUMAN_TEXTURE_GATES below; they are NOT wired into --gate yet (see the note there).
TARGETS = {
    "em_dash": 0,
    "semicolon": 0,            # LEGACY / unused by the gate now: Section 15 A3 made semicolons a manuscript
                               # rate band (0.5-2 per 1,000 words), enforced as a SOFT advisory in scan.py
                               # via HUMAN_TEXTURE_GATES["semicolons_per_1k"]. Em dash stays the hard gate.
    "banned_words": 0,
    "banned_phrases": 0,
    "sentence_std_min": 8.0,   # stddev of sentence length in words; Section 15 C1 raises the target to 10.0
    "fragments_min": 3,        # sentences <= 4 words
    "abs_starts_min": 3,       # And/But/So sentence openings
    "ellipsis_max_per_chapter": 1,
}

# =============================================================================
# Section 15: HUMAN-TEXTURE RULEBOOK (rates, not bans) - added 2026-08-15
# -----------------------------------------------------------------------------
# "Zero is a fingerprint": most of these are RATES, not bans. This block is the machine-readable mirror of
# STYLE_RULES.md Section 15. LIVE now: scan.py reads semicolons_per_1k and flags the whole-manuscript rate
# as a SOFT advisory when outside the band (no longer hard-blocks on a semicolon). STILL a target end-state
# (not yet wired into scan.py): the rhythm/structure/paragraph metrics below and the std >= 10 target (the
# variety advisory still defaults to 8; pass --min-std 10 for Section 15). Em dash stays the hard gate.

# B2: rate-capped lexicon (max ~1 per 2,000 words each; NOT banned). Several also live in BANNED_WORDS
# (Section 3), which stays the stricter gate until reconciliation; treat this as the target end-state.
RATE_CAPPED_WORDS = [
    "crucial", "vital", "pivotal", "robust", "holistic", "leverage", "harness", "foster", "empower",
    "elevate", "landscape", "navigate", "journey", "intricate", "nuanced", "profound", "transformative",
]

# B3: paragraph-opener HARD ZEROs (as openers), plus the combined transition cap (<=1 per 10,000 words).
PARAGRAPH_OPENER_HARD_ZERO = ["in conclusion", "overall,", "ultimately,"]
TRANSITION_COMBINED_CAP = {"words": ["moreover", "furthermore", "additionally"], "max": 1, "per_words": 10000}

# Full acceptance-gate set (STYLE_RULES.md Section 15 table + the A/C/D/E numeric rules). Tuple = inclusive
# (low, high) range; a bare number = a max (or min where the key says _min). Units: _per_1k = per 1,000
# words, _pct = share of the named population, _per_Nk = per N,000 words.
HUMAN_TEXTURE_GATES = {
    "em_dash_count": (0, 0),
    "semicolons_per_1k": (0.5, 2.0),
    "colons_midsentence_per_1k_max": 4.0,
    "parentheticals_per_1k": (1.0, 3.0),
    "ellipsis_per_chapter_max": 1.0,
    "sentence_std_min": 10.0,
    "mean_sentence_len": (14, 18),
    "sentences_le_5w_pct_min": 10.0,
    "sentences_ge_35w_pct": (3.0, 6.0),
    "max_consecutive_samelen_run": 2,          # sentences whose lengths fall within 2 words of each other
    "fragments_pct": (2.0, 5.0),
    "single_sentence_para_pct": (5.0, 12.0),
    "sentences_per_para_std_min": 1.5,
    "max_consecutive_same_para_sentcount": 3,
    "topic_support_conclusion_para_pct_max": 25.0,
    "section_len_variance_pct_min": 30.0,
    "triads_share_of_lists_pct_max": 40.0,
    "rhetorical_q_then_answer_per_3k_max": 1.0,
    "section_open_rhetorical_q_pct_max": 20.0,
    "para_end_punchline_pct_max": 30.0,
    "not_x_it_y_per_15k_max": 1.0,
    "not_just_x_but_y_per_15k_max": 1.0,
    "b2_rate_cap_per_2k_each_max": 1.0,
    "unresolved_cases_pct_min": 30.0,          # F1 (human-judged); the rest of Section 15 F stays human-owned
}

# =============================================================================
# AI-SMELL TEMPLATE / MOTIF FREQUENCY (tools/ai_smell_scan.py, checklist 27 AR-19..AR-22)
# -----------------------------------------------------------------------------
# These are ADVISORY frequency lists, not banned language. Each is a rhetorical template, motif, or
# hedge that is fine ONCE but reads machine-shaped when it recurs on a predictable cadence (the exact
# signal a stylometric AI-smell review flags: uniform templates + conspicuous polish). ai_smell_scan.py
# counts them PER CHAPTER so a human can thin the high-frequency ones to a chapter-level budget rather
# than deleting every instance. Genre/title/author-agnostic: no book-specific words. Regexes are matched
# case-insensitively on word boundaries. Origin: JOMO "Selective Ambition" 160-item AI-smell audit,
# 2026-08-05.
AI_SMELL_PATTERNS = {
    # paired-negation and negative-cause templates (audit #11-13)
    "paired-negation (Not X. Not Y.)": r"\bnot\s+\w+[.,]\s+not\s+\w+\b",
    "negative-cause (Not because... Because)": r"\bnot because\b",
    # filler / signpost transitions (audit #14,15,20)
    "filler-transition (that's/here's the thing/trap/part)":
        r"\b(that's|here's|and here's) the (thing|trap|part|point|difference)\b|\bthe (thing|point) is,?\b",
    "worst-part escalator": r"\band (the|what makes it) worse\b|\bthe worst part\b",
    "not-a-system denial": r"\bnot a (system|framework|philosophy|formula|method|manifesto|prescription)\b",
    # honesty / caveat announcers (audit #18,19)
    "honesty-marker (to be honest / if I'm honest)":
        r"\b(to be honest|if i'?m honest|i'?ll be honest|i should be honest|honestly,)\b",
    "caveat-announcer (one caveat / to be careful)":
        r"\b(one caveat|one clarification|one thing to name|i want to be careful|a note (before|on)|worth saying)\b",
    # memory / hedge openers (audit #16,17)
    "memory-opener (I remember)": r"(^|\.\s|\n)\s*i remember\b",
    "hedge-softener (I think / I guess)": r"\bi (think|guess|suppose)\b",
    # categorical expanders and lesson-tells (audit #97-99)
    "categorical-expander (the kind where / the version of me)":
        r"\bthe (kind|sort) (where|that|of)\b|\bthe version of (me|you)\b|\bthe one where\b",
    "lesson-tell (which tells you something)":
        r"\bwhich tells you something\b|\bwhich is exactly (what|the)\b|\bthat's the (whole )?(point|trap|thing)\b",
    # reader-management / embodied prompts (audit #67-71)
    "reader-prompt (you know this / sit with that)":
        r"\byou (already )?know (this|the|what|which)\b|\bsit with (that|this|it)\b|\bnotice what (happens|you)\b",
    # false endings (audit #105,106)
    "false-ending (that's all / one more thing)":
        r"\bthat's all\b|\bone more thing\b|\bhere's the (last|final) thing\b",
    # personification of abstractions (audit #58-61); present AND past tense
    "personified-abstraction (guilt/fear/ambition + verb)":
        r"\b(guilt|fear|ambition|the algorithm|comparison|the list|the fear|the guilt|the project|the idea)\s+"
        r"(say|says|said|whisper|whispers|whispered|sit|sits|sat|follow|follows|followed|"
        r"wait|waits|waited|demand|demands|demanded|get bored|gets bored|got bored|"
        r"leave|leaves|left|announce|announces|announced|scream|screams|screamed|know|knows|knew)\b",
    # interpretive-announcer (gap 4 / transcript "excessive interpretive guidance"): telling the reader
    # what a moment MEANT instead of letting action or consequence show it. Fine once; a tell in bulk.
    "interpretive-announcer (the truth was / what X realized)":
        r"\bthe truth was\b|\bwhat (he|she|they|it|i) (realized|understood|saw|knew|learned) was\b|"
        r"\bwhat mattered was\b|\bthe real question (is|was)\b|\bthe point was\b|\bin that moment\b|"
        r"\bbecame (it|them)\b",
    # ---- 2026-08-13 gap detectors (from the publication-audit coverage map,
    # WRITING_IMPROVEMENTS_HARNESS_COVERAGE_*.md): tells the audit flagged that the harness did not yet
    # watch. All ADVISORY (ai_smell_scan reports frequency), never a hard gate, never count-to-zero: thin
    # the smell, keep the strongest. Text is lowercased before matching, so patterns are lowercase.
    "invented-precision (decimal percent / exact story counts / exact dollars)":  # gap 1.3
        r"\b\d{1,3}\.\d+ percent\b|\b\d{2,4} (applications|transactions|employees|decisions|loans|"
        r"loan applications|candidates|hires|records|families)\b|\$\d{1,3},\d{3}\b",
    "contrast-epigram (X, not a Y)":  # gap 6.1 (broadens paired-negation / not-a-system to the general form)
        r",\s+not\s+(a|an|the|your)\s+\w+\b",
    "direct-observation-claim (I watched / one hospital learned)":  # gap 1.2 (composite told as observed fact)
        r"\bi (watched|have watched|know a|knew a)\b|\bone (hospital|company|bank|firm|grocery chain|"
        r"retailer|regional hospital) (learned|discovered|found|had)\b",
    "chapter-return (Back to <Name>)":  # gap 3.3 (every chapter loops back to its opening character)
        r"back to (sarah|carla|elena|marcus|thomas|patricia|kevin|priya|david|michael|renata|"
        r"catherine|grace)\b|#{1,4} back to \w+",
    "next-chapter-preview (that is where we go next)":  # gap 3.2 (formulaic hand-off to the next chapter)
        r"\bthat is where (we go next|this actually begins|the (real )?work)\b|\bwhich brings us to\b|"
        r"\bthe next chapter\b|\bthe (final|last) chapter (takes up|is)\b|\bthat is the work (waiting|of)\b",
    "lost-hyphen compound (AIassisted / humanAI / decisionmaking)":  # gap 15.1 (source-side typo guard)
        r"\b(aiassisted|aishaped|humanai|humancomputer|decisionmaking|highstakes|selfprotective|feedbackrich|"
        r"tshaped|loadplanning|datascience|muchcited|whiteassociated|femaleassociated|biasdriven|"
        r"performancemanagement|publicdomain|humanrobot|futureproofing|twoperson|longterm|realworld)\b",
    "named-taxonomy (the three/four/five ... X)":  # gap 4.1/4.2 (framework-packaging density)
        r"\bthe (three|four|five|six|seven) (phases|biases|fears|principles|practices|layers|steps|"
        r"stages|dimensions|traps|questions|mechanisms|ways|variations|forces)\b|"
        r"\b\w+-(part|step|stage|layer|phase) (model|framework|system|architecture)\b",
}
# Weekday scene-openers (audit #3,4): a day of the week near a sentence start.
AI_SMELL_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
# Over-certain absolutes / universals (audit #13,14,19,27,36,42,43,46,54,58; round-2 overclaim class).
# Kept deliberately NARROW to the genuinely overclaim-prone forms; common benign words like
# "nothing"/"everything" are excluded so the signal is not drowned in noise.
AI_SMELL_ABSOLUTES = [
    "always", "never", "every time", "everyone", "nobody", "no one", "all of us",
    "100%", "100 percent", "exactly like", "the only way", "will always", "will never",
    "can't ever", "impossible to", "guaranteed", "almost always", "every single",
]
# Recurring MOTIF words (audit #53-56, #152 metaphor-ownership): ai_smell_scan reports which chapters
# each appears in, so a metaphor can be assigned to ONE owning chapter and cross-use flagged.
AI_SMELL_MOTIFS = [
    "buffet", "scoreboard", "treadmill", "the race", "the wall came down", "the shelf", "the bin",
    "cold coffee", "cold tea", "gone cold", "the door", "the room", "friction", "highlight reel",
]
# Leaked editorial instructions / unresolved placeholders that must never ship in body text
# (audit #97 leaked "should be confirmed"; #103/#104 placeholders). ai_smell_scan flags these HARD.
AI_SMELL_PLACEHOLDERS = [
    r"\bto be (confirmed|assigned|added|determined|decided)\b", r"\bTBD\b", r"\bTODO\b", r"\bFIXME\b",
    r"\[[^\]]*(placeholder|to be|tbd|insert|xxx)[^\]]*\]", r"\bshould be confirmed\b",
    r"\bplaceholder\b", r"\blorem ipsum\b",
]
# ---- Gap 1: metaphor COHERENCE candidate frames (advisory; ai_smell_scan lists each match so a human
# checks it survives a literal read and that one conceptual field owns one image). NOT count-to-zero:
# metaphor is welcome; SATURATION and INCOHERENCE are the smell. Kept to the distinctive costume-metaphor
# frame the transcript flagged (fear wearing a technical costume, faith in a lab coat, fear in a good
# suit) to stay low-noise. Coherence itself is a human judgement (HUMAN_VOICE Section 4, the 6 questions).
AI_SMELL_METAPHOR_SHAPES = [
    r"\b\w+\s+(wearing|dressed in|in)\s+(a|an|the)\s+(\w+\s+)?(costume|suit|coat|mask|disguise|uniform|clothing)\b",
]
# ---- Gap 2: emotional-intensity markers (advisory PROXY). ai_smell_scan measures their density per
# chapter and flags LOW spread across chapters (every chapter equally hot = emotional flatlining, the
# transcript's uniform-volume tell). A crude lexical proxy, never a verdict: a human reads the contour
# (HUMAN_VOICE Section 4A, the baseline -> turn -> release map and the 1-to-5 label test).
AI_SMELL_INTENSITY_MARKERS = [
    "dread", "fear", "terror", "anguish", "grief", "crisis", "existential", "devastating",
    "haunting", "harrowing", "unbearable", "shattering", "raw", "aching", "desperate", "urgent",
    "profound", "profoundly", "deeply", "utterly", "overwhelming", "wrenching", "searing",
]
# ---- Gap 6: pseudo-humanizing SENSORY FILLER (advisory). Generic weather/coffee/light detail dropped in
# to "warm up" prose is itself an AI tell (transcript: "do not add irrelevant sensory detail"). Flagged so
# a human removes it or replaces it with a detail that does real work (grounds AND reveals). Never a reason
# to fabricate a specific.
AI_SMELL_SENSORY_FILLER = [
    r"\bbirds (chirp|chirped|were chirping|sang)\b", r"\bsunlight (streamed|poured|filtered|spilled)\b",
    r"\bthe smell of (fresh )?coffee\b", r"\bcoffee (filled|warmed) the\b",
    r"\brain (tapped|drummed|pattered)\b", r"\bthe air (felt|hung|grew) (heavy|thick|still)\b",
    r"\ba (gentle|soft|cool) breeze\b", r"\bthe (warm|golden|pale) (glow|light) of\b",
]
