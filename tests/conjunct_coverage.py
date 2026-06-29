"""
Conjunct coverage test — exhaustive check of all KrutiDev cluster mappings.

Each entry: (raw_krutidev, expected_unicode, label)
Run with: python tests/conjunct_coverage.py
"""

import sys
import os
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.converter import load_mapping, convert

# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

CASES = [
    # --- user's confirmed failing list ---
    ("vDVwcj",        "अक्टूबर",       "क्ट  — October"),
    ("v/;{k",         "अध्यक्ष",       "ध्य+क्ष — chairman"),
    ("fo'oluh;rk",    "विश्वसनीयता",   "श्व — reliability"),
    ("nq?kZVuk",      "दुर्घटना",      "घ+reph — accident"),
    ("C;wjks",        "ब्यूरो",        "ब्य — bureau"),
    ("okf.kfT;d",     "वाणिज्यिक",     "णिज्य — commercial (T→ज् fix)"),
    ("/kkrqdeZ",      "धातुकर्म",      "reph — metallurgy"),

    # --- T → ज् verification ---
    ("jkT;",          "राज्य",         "T→ज् in ज्य — state"),
    ("lqlfTtr",       "सुसज्जित",      "T→ज् in ज्ज — equipped"),
    ("T;ksRluk",      "ज्योत्सना",     "T→ज् standalone — name"),

    # --- ~ → ् (halant) verification ---
    ("mn~?kkVu",      "उद्घाटन",       "~→् — inauguration"),
    ("ln~Hkko",       "सद्भाव",        "~→· — goodwill"),
    ("iV~Vj",         "पट्टर",         "~→· — surname Pattar"),
    ("mM~M;u",        "उड्डयन",        "ड्ड via ~ — aviation"),

    # --- æz artifact fix ---
    ("dsaæ",          "केंद्र",        "द्र — no z artifact"),
    ("dsaæz",         "केंद्र",        "द्र — spurious z absorbed"),

    # --- high-frequency conjuncts ---
    ("ijh{kk",        "परीक्षा",       "क्ष"),
    ("fe=",           "मित्र",         "त्र"),
    ("Kku",           "ज्ञान",         "ज्ञ"),
    ("Jh",            "श्री",          "श्र"),
    ("cq)",           "बुद्ध",         "द्ध"),
    ("}kjk",          "द्वारा",        "द्व"),
    ("fo|k",          "विद्या",        "द्य"),
    ("ifj–';",        "परिदृश्य",      "दृ+श्य"),
    ("'kfä",          "शक्ति",         "क्त"),
    ("Øe",            "क्रम",          "क्र"),
    ("çse",           "प्रेम",         "प्र"),
    ("xzke",          "ग्राम",         "ग्र"),
    ("czãksl",        "ब्रह्मोस",      "ब्र+ह्म"),
    ("fu'p;",         "निश्चय",        "श्च"),
    ("oLrq",          "वस्तु",         "स्त"),
    ("LFkku",         "स्थान",         "स्थ"),
    ('d"V',           "कष्ट",          "ष्ट"),
    ("cUn",           "बन्द",          "न्द"),
    ("vUr",           "अन्त",          "न्त"),
    ("dEi",           "कम्प",          "म्प"),
    ("dYi",           "कल्प",          "ल्प"),
    ("ih<+h",         "पीढ़ी",          "ढ़"),
    ("yM+dk",         "लड़का",          "ड़"),
    ("Q+ksu",         "फ़ोन",           "फ़"),
    ("t+ehu",         "ज़मीन",          "ज़"),
    ("deZ",           "कर्म",          "reph — karma"),
    ("/eZ",           "धर्म",          "reph — dharma"),
    ("fuHkZj",        "निर्भर",        "pre-र reph"),

    # --- other conjugants / single-char fixes from earlier sessions ---
    ("fo'ys\"k.k",    "विश्लेषण",      "श्ल+ष"),
    ("MkW",           "डॉ",            "chandra-O matra"),
    ("'kS{kf.kd",     "शैक्षणिक",      "f.k 3-char conjunct"),
    ("czãkaM",        "ब्रह्मांड",     "ã=ह्म"),
    ("fpfàr",         "चिह्नित",       "à=ह्न"),
    ("ikBîØe",        "पाठ्यक्रम",     "B=ठ, î=्य"),
    ("ÅtkZ",          "ऊर्जा",         "Å=ऊ"),
    ("_rqjkt",        "ऋतुराज",        "_=ऋ"),
    ("Le`fr",         "स्मृति",        "`=ृ"),
    ("mís';",         "उद्देश्य",      "í=द्द"),
    ("¶ys;j",         "फ्लेयर",        "¶=फ्"),
    ("ÝSDpj",         "फ्रैक्चर",      "Ý=फ्र"),
    ("lEesyu",        "सम्मेलन",       "E=म्"),
    ("fnYyh",         "दिल्ली",        "Y=ल्"),
    ("fo'ofo|ky;",    "विश्वविद्यालय", "श्व+द्य (full word)"),
    ("v/;;u",         "अध्ययन",        "ध्य — study (;; doubled)"),

    # --- i-matra + ्र suffix ordering (fcz fix) ---
    ("gkbfczM",       "हाइब्रिड",     "fcz — i-matra before ब्र cluster (Hybrid)"),

    # --- क्ट (retroflex ट, DV) vs क्त (dental त, Dr / ä) ---
    # These two clusters are encoded differently; both must be correct.
    ("vDVwcj",        "अक्टूबर",      "DV=क्ट retroflex ट — October (article body)"),
    ("M‚DVj",    "डॉक्टर",       "DV=क्ट retroflex ट — Doctor"),
    ("vDrwcj",        "अक्तूबर",      "Dr=क्त dental त — October (alt Hindi spelling)"),
    ("'kf\xe4",       "शक्ति",        "ä=क्त dental conjunct — Shakti"),
    ("eq\xe4",        "मुक्त",        "ä=क्त dental conjunct — Mukta"),
    ("Hk\xe4",        "भक्त",         "ä=क्त dental conjunct — Bhakta"),
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run():
    mapping = load_mapping()
    pass_count = 0
    fail_count = 0
    failures = []

    col_w = max(len(r) for r, *_ in CASES) + 2

    print(f"\n{'RAW':<{col_w}}  {'STATUS':<6}  {'LABEL'}")
    print("-" * 80)

    for raw, expected, label in CASES:
        got = convert(raw, mapping)
        if got == expected:
            status = "PASS"
            pass_count += 1
            print(f"{raw!r:<{col_w}}  {status:<6}  {label}")
        else:
            status = "FAIL"
            fail_count += 1
            print(f"{raw!r:<{col_w}}  {status:<6}  {label}")
            failures.append((raw, expected, got, label))

    print("-" * 80)
    print(f"\n{pass_count} PASS  {fail_count} FAIL  (total {len(CASES)})\n")

    if failures:
        print("=== FAILURES (codepoint diagnosis) ===\n")
        for raw, expected, got, label in failures:
            print(f"  [{label}]  raw={raw!r}")
            print(f"    expected: {expected!r}")
            exp_cp = " ".join(f"U+{ord(c):04X}({c})" for c in expected)
            print(f"      codepoints: {exp_cp}")
            print(f"    got:      {got!r}")
            got_cp = " ".join(f"U+{ord(c):04X}({c})" for c in got)
            print(f"      codepoints: {got_cp}")
            print()
        sys.exit(1)
    else:
        print("All conjunct coverage tests PASS.")
        sys.exit(0)


if __name__ == "__main__":
    run()
