"""
Unit tests for the KrutiDev → Unicode converter.

HOW TO ADD TEST CASES
---------------------
Add entries to KNOWN_CONVERSIONS below. Each entry is:
    (krutidev_input, expected_unicode_output, description)

The description is shown in the pytest output when a test fails, so make it
specific: what word/phrase is being tested and where you found the example.

Run tests:
    pytest tests/test_converter.py -v

To see which characters are still unmapped (pass-through), run:
    pytest tests/test_converter.py -v -s
and look for characters in the output that are not Devanagari.
"""

from __future__ import annotations

import pytest
from src.converter import load_mapping, convert


# ---------------------------------------------------------------------------
# Ground-truth test cases
# ---------------------------------------------------------------------------
# Format: (krutidev_input, expected_unicode, description)
#
# Add more rows as you extract text from the PDFs and manually verify
# the correct output. The description field helps you find failing cases.
#
# VERIFIED means confirmed from the task description or your PDFs.
# DERIVED means constructed from individual verified mappings.

KNOWN_CONVERSIONS: list[tuple[str, str, str]] = [
    # -----------------------------------------------------------------------
    # From the task description — the primary ground-truth example
    # -----------------------------------------------------------------------
    (
        "MhvkjMhvks lekpkj",
        "डीआरडीओ समाचार",
        "DRDO Samachar — primary verified example from task description",
    ),

    # -----------------------------------------------------------------------
    # Isolated verified mappings (derived from the primary example)
    # -----------------------------------------------------------------------
    (
        "l",
        "स",
        "single char: l → स (sa) [verified]",
    ),
    (
        "e",
        "म",
        "single char: e → म (ma) [verified]",
    ),
    (
        "k",
        "ा",
        "single char: k → ā matra (ा) [verified]",
    ),
    (
        "p",
        "च",
        "single char: p → च (ca) [verified]",
    ),
    (
        "j",
        "र",
        "single char: j → र (ra) [verified]",
    ),
    (
        "M",
        "ड",
        "single char: M → ड (ḍa) [verified]",
    ),
    (
        "h",
        "ी",
        "single char: h → ī matra (ी) [verified]",
    ),

    # -----------------------------------------------------------------------
    # Conjunct / multi-char sequences (verified from primary example)
    # -----------------------------------------------------------------------
    (
        "vk",
        "आ",
        "conjunct: vk → standalone आ (ā) [verified from 'vkj'→'आर']",
    ),
    (
        "vks",
        "ओ",
        "conjunct: vks → standalone ओ (o) [verified from 'MhvkjMhvks'→'डीआरडीओ']",
    ),

    # -----------------------------------------------------------------------
    # i-matra reordering — the main complexity
    # -----------------------------------------------------------------------
    # In KrutiDev: f + consonant  (i-matra BEFORE consonant)
    # In Unicode:  consonant + ि  (i-matra AFTER consonant)
    # Example: 'fl' should give 'सि' (si), not 'fस'
    (
        "fl",
        "सि",
        "i-matra reorder: f + l(स) → सि  [i-matra rule: f goes AFTER the consonant]",
    ),
    (
        "fM",
        "डि",
        "i-matra reorder: f + M(ड) → डि",
    ),
    (
        "fp",
        "चि",
        "i-matra reorder: f + p(च) → चि",
    ),

    # -----------------------------------------------------------------------
    # Multi-word / sentence-level
    # -----------------------------------------------------------------------
    (
        "lekpkj",
        "समाचार",
        "word: samāchār (news) — from primary example",
    ),
    (
        "MhvkjMhvks",
        "डीआरडीओ",
        "word: DRDO acronym — from primary example",
    ),

    # -----------------------------------------------------------------------
    # Verified from SM_Oct2025.pdf pages 7 and 10
    # -----------------------------------------------------------------------

    # Words verified from page 7
    (
        "gSnjkckn",
        "हैदराबाद",
        "word: Hyderabad — p7 (g=ह, S=ै, n=द, j=र, k=ा, c=ब, k=ा, n=द)",
    ),
    (
        "j{kk",
        "रक्षा",
        "word: rakshā (defence) — p7 ({k conjunct → क्ष)",
    ),
    (
        "gLrkarfjr",
        "हस्तांतरित",
        "word: hastāntarit (transferred) — p7 (L=स्, a=ं)",
    ),
    (
        "mPp",
        "उच्च",
        "word: uccha (high) — p7 (m=उ, P=च्, p=च)",
    ),
    (
        "mUur",
        "उन्नत",
        "word: unnat (advanced) — p7 (U=न्, u=न, r=त)",
    ),
    (
        "LVhy",
        "स्टील",
        "word: steel (transliterated) — p7 (L=स्, V=ट, h=ी, y=ल)",
    ),
    (
        ";g",
        "यह",
        "word: yah (this) — p7 (;=य, g=ह)",
    ),
    (
        "}kjk",
        "द्वारा",
        "word: dvārā (by/through) — p7 (}=द्व conjunct)",
    ),
    (
        ",oa",
        "एवं",
        "word: evam (and) — p7 (,=ए, o=व, a=ं)",
    ),
    (
        "y{;",
        "लक्ष्य",
        "word: lakshya (target) — p7/p10 (y=ल, {=क्ष्, ;=य)",
    ),
    (
        "le>kSrk",
        "समझौता",
        "word: samjhautā (agreement) — p7 (>=झ, S=ै → ौ via kS conjunct)",
    ),

    # Words verified from page 10
    (
        "dks",
        "को",
        "word: ko (to/for) — p10 (d=क, ks conjunct → ो)",
    ),
    (
        "[kkst",
        "खोज",
        "word: khoj (search) — p10 ([k conjunct → ख, ks conjunct → ो)",
    ),
    (
        "ladsr",
        "संकेत",
        "word: sanket (signal) — p10 (a=ं, l=स, d=क, s=े, r=त)",
    ),
    (
        "djrk",
        "करता",
        "word: kartā (does) — p10 (d=क, j=र, r=त, k=ा)",
    ),
    (
        "felkby",
        "मिसाइल",
        "word: missile — p10 (f+e=मि, l=स, k=ा, b=इ, y=ल)",
    ),
    (
        "ç.kkyh",
        "प्रणाली",
        "word: pranāli (system) — p10 (ç=प्र, .k conjunct → ण, k=ा, y=ल, h=ी)",
    ),

    # Reph reordering (Z) — verified from p10
    (
        "dk;ZØe",
        "कार्यक्रम",
        "word: kāryakram (programme) — p10 reph Z reordering: ;Z → र्य",
    ),
    (
        "egRoiw.kZ",
        "महत्वपूर्ण",
        "word: mahatvapūrna (important) — p10 reph Z + .k conjunct",
    ),

    # i-matra before half-form — verified from p10
    (
        "fufnZ\"V",
        "निर्दिष्ट",
        "word: nirdisht (specified) — p10 half-form skip + reph + \"=ष्",
    ),
    (
        "fuf\"Ø;",
        "निष्क्रिय",
        "word: nishkriya (passive) — p10 \"=ष्(half-form) skipped by i-matra, Ø=क्र",
    ),
    (
        "iqf\"V",
        "पुष्टि",
        "word: pushti (confirmation) — p10 (i=प, q=ु, f+\"=ष्(half)+V=टि)",
    ),
    (
        "Lopkfyr",
        "स्वचालित",
        "word: svachālit (automatic) — p10 (L=स्, o=व, p=च, k=ा, f+y=लि, r=त)",
    ),
    (
        ":i ls",
        "रूप से",
        "phrase: rūp se (in the form of) — p10 (:=रू, i=प, l=स, s=े)",
    ),
    (
        "nsgjknwu",
        "देहरादून",
        "city: Dehradun — p10 (n=द, s=े, g=ह, j=र, k=ा, n=द, w=ू, u=न)",
    ),
    (
        ",sfrgkfld",
        "ऐतिहासिक",
        "word: aitihasik (historic) — p10 (,s conjunct → ऐ, r=त, f+g=हि, k=ा, f+l=सि, d=क)",
    ),
    (
        "çfr\"Bku",
        "प्रतिष्ठान",
        "word: pratisthān (institution) — p10 (ç=प्र, f+r=ति, \"=ष्, B=ठ, k=ा, u=न)",
    ),

    # -----------------------------------------------------------------------
    # Bug fixes verified from PDF vs real output (p7)
    # -----------------------------------------------------------------------
    (
        "M‚",
        "डॉ",
        "chandra-O matra: M‚ → डॉ (Dr.) — p7. ‚ (U+201A) = ॉ (U+0949); was wrongly passing through giving ड‚.",
    ),
    (
        "M‚ lehj oh dker]",
        "डॉ समीर वी कामत,",
        "comma fix: ] (U+005D) → , — p7. KrutiDev uses ] for comma; ASCII comma maps to ए.",
    ),

    # -----------------------------------------------------------------------
    # Punctuation mappings (p7/p10 verified)
    # -----------------------------------------------------------------------
    (
        "çdkj gSa%",
        "प्रकार हैं:",
        "colon: % → : — p7 (çdkj gSa% ends a list intro; not a percentage sign here).",
    ),
    (
        "¼Mh,evkj,y½",
        "(डीएमआरएल)",
        "bracket map: ¼ → ( and ½ → ) — p7. KrutiDev uses ¼ ½ as standard parentheses.",
    ),

    # -----------------------------------------------------------------------
    # Artifact-k drop: consonants H/F/'/ध/Ù always emit a spurious k glyph
    # -----------------------------------------------------------------------
    (
        "lkFk",
        "साथ",
        "artifact-k drop: F=थ + k(artifact) — साथ (with, together). Raw has F+k but only one char expected.",
    ),
    (
        "rFkk",
        "तथा",
        "artifact-k drop: F=थ + k(artifact) + k(real ā) — तथा (thus/and). Confirms second k is real.",
    ),
    (
        "Hkh",
        "भी",
        "artifact-k drop: H=भ + k(artifact) + h=ī — भी (also). Without skip: भाई (sister) — wrong.",
    ),
    (
        "fLFkr",
        "स्थित",
        "artifact-k drop + i-matra + half-form: f+L(half-skip)+F(थ+ि)+k(artifact) → स्थित.",
    ),
    (
        "/kkrqdeZ",
        "धातुकर्म",
        "artifact-k drop: /=ध + k(artifact) + k(real ā) — धातुकर्म (metallurgy).",
    ),
    (
        "xq.koÙkk",
        "गुणवत्ता",
        "artifact-k drop: Ù=त्त (U+00D9) + k(artifact) + k(real ā) — गुणवत्ता (quality).",
    ),
    (
        "LFkkfir",
        "स्थापित",
        "artifact-k drop: F=थ + kk — L(स्)+F(थ)+k(artifact)+k(ā) → स्थापित (established).",
    ),
    (
        "'kfä",
        "शक्ति",
        "artifact-k drop: '=श + k(artifact) + f+ä(क्ति) → शक्ति (power/strength).",
    ),
    (
        "leFkZu",
        "समर्थन",
        "artifact-k drop + reph: F=थ+k(artifact consumed before Z) → समर्थन (support).",
    ),
    (
        "ekxZn'kZu",
        "मार्गदर्शन",
        "artifact-k drop + reph: both xZ and 'kZ chains now clean — मार्गदर्शन (guidance).",
    ),

    # -----------------------------------------------------------------------
    # = -> त्र (direct mapping; formerly missing; =k conjunct removed as wrong)
    # -----------------------------------------------------------------------
    (
        ";a=",
        "यंत्र",
        "= -> त्र: yantra (p10: ;=य, a=ं, ==त्र). = was unmapped, passing through as =.",
    ),
    (
        "ra=",
        "तंत्र",
        "= -> त्र: tantra (p7: ra==तं+त्र).",
    ),
    (
        "ea=ky;",
        "मंत्रालय",
        "= -> त्र: mantralaya (p7: ea==मंत्र; =k conjunct was wrongly firing as ज्ञ — removed).",
    ),
    (
        "Kkiu",
        "ज्ञापन",
        "K -> ज्ञ still works after =k conjunct removal (ज्ञ is encoded as K, not =k).",
    ),
    (
        "ikfjfLFkfrdh ra= dks vkSj etcwr djrs",
        "पारिस्थितिकी तंत्र को और मजबूत करते",
        "= -> त्र: full phrase from p7 raw — 'पारिस्थितिकी तंत्र'.",
    ),

    # -----------------------------------------------------------------------
    # ) -> द्ध (da+halant+dha conjunct; ASCII ) is the KrutiDev द्ध glyph)
    # -----------------------------------------------------------------------
    (
        "çfrc)rk",
        "प्रतिबद्धता",
        ") -> द्ध: pratibaddhata (p7: çfr=प्रति, c=ब, )=द्ध, r=त, k=ā).",
    ),
    (
        "ifj'kq)rk",
        "परिशुद्धता",
        ") -> द्ध: parishuddhatā (p10: ifj=परि, 'kq=शु (artifact-k drop), )=द्ध, r=त, k=ā).",
    ),

    # -----------------------------------------------------------------------
    # "k -> ष conjunct  (" = KrutiDev sha-retroflex glyph, ASCII double-quote)
    # artifact-k after " glyph gives plain ष, not ष्+ā
    # -----------------------------------------------------------------------
    (
        'fo"k;d',
        "विषयक",
        '"k conjunct -> ष: vishayak (p7: fo=वि, "k=ष, ;=य, d=क). '
        'Without conjunct: "->ष·, k->ā giving wrong विष्ायक.',
    ),
    (
        'fo\'ks"kKrk',   # f o ' k s " k K r k
        "विशेषज्ञता",
        '"k conjunct -> ष: vishesha-jnata (p7: fo=वि, \'k=श(artifact), '
        's=े, "k=ष, K=ज्ञ, r=त, k=ā).',
    ),
    (
        'fo\'ks"krk,\xa1',   # fo'ks"krk + , + ¡ (U+00A1 chandrabindu)
        "विशेषताएँ",
        '"k conjunct -> ष: visheshataen (p7: fo=वि, \'k=श(artifact), '
        's=े, "k=ष, r=त, k=ā, ,=ए, ¡=ँ → विशेषताएँ).',
    ),

    # -----------------------------------------------------------------------
    # [ -> ख् (kha+halant) for half-kha before ya/other non-k consonants
    # -----------------------------------------------------------------------
    (
        "eq[;",
        "मुख्य",
        "[ -> ख्: mukhy (p10: e=म, q=ु, [=ख्, ;=य). "
        "Conjunct '[k'->ख fires when k follows; standalone [ gives half-form.",
    ),
    (
        "çeq[k",
        "प्रमुख",
        "[ -> ख: pramukha (p7: [k conjunct fires -> full ख, k=ā -> मुख).",
    ),

    # -----------------------------------------------------------------------
    # < -> ढ, + -> ़ (nukta) — dha-nukta pair for ढ़
    # -----------------------------------------------------------------------
    (
        "ih<+h",
        "पीढ़ी",
        "< -> ढ, + -> ़: pidhi (p10: i=प, h=ी, <=ढ, +=़, h=ी → पीढ़ी). "
        "KrutiDev uses < for ढ and + for nukta (U+093C).",
    ),

    # -----------------------------------------------------------------------
    # रeph: ā preserved after artifact_k fix (no longer discarded)
    # -----------------------------------------------------------------------
    (
        "mi;ksxdrkZ",
        "उपयोगकर्ता",
        "reph preserves final ā: upayogakarta (p10). "
        "Before fix: drkZ -> कर्त (ā silently dropped by reph step). "
        "artifact_k_chars consumes spurious k before Z fires, so ā here is real.",
    ),
    (
        "drkZ",
        "कर्ता",
        "reph preserves ā: karta (basic — d=क, r=त, k=ā, Z=रeph -> कर्ता).",
    ),

    # -----------------------------------------------------------------------
    # & -> hyphen
    # -----------------------------------------------------------------------
    (
        'cgq&fo"k;d',
        "बहु-विषयक",
        '& -> hyphen: bahu-vishayak (p7: cgq=बहु, &=-, fo"k;d=विषयक). '
        "KrutiDev uses & for the hyphen glyph.",
    ),

    # -----------------------------------------------------------------------
    # U+2013 (–) -> दृ  and  conjunct '; -> श्य  — परिदृश्य
    # -----------------------------------------------------------------------
    (
        "ifj–';",          # i f j – ' ;
        "परिदृश्य",
        "U+2013->दृ + conjunct';->श्य: paridrishya (p10: ifj=परि, –=दृ, ';=श्य). "
        "– is the KrutiDev ligature glyph for दृ (da+vocalic-r-matra). "
        "Without conjunct: '->श, ;->य giving परिदृशय (halant missing).",
    ),
    (
        "–';",             # – ' ;   (standalone दृश्य)
        "दृश्य",
        "U+2013->दृ + conjunct';->श्य: drishya standalone. "
        "Verifies both mappings without the ifj prefix.",
    ),

    # -----------------------------------------------------------------------
    # U+2014 (—) -> कृ  — उत्कृष्ट
    # -----------------------------------------------------------------------
    (
        "mR—\"V",          # m R — " V
        "उत्कृष्ट",
        'U+2014->कृ: utkrisht (p7: m=उ, R=त्, —=कृ, "V=ष्ट -> उत्कृष्ट). '
        "— is the KrutiDev ligature glyph for कृ (ka+vocalic-r-matra). "
        "Confirmed from ÝSDpj VQusl dk mR—\"V la;kstu=उत्कृष्ट संयोजन (p7).",
    ),

    # -----------------------------------------------------------------------
    # 'p -> श्च conjunct + i-matra half-form fix for निश्चित/निश्चय
    # -----------------------------------------------------------------------
    (
        "fu" + chr(0x27) + "p;",
        "निश्चय",
        "conjunct 'p->श्च: nishchay (p7: fu=नि, 'p=श्च, ;=य). "
        "' at current pos + p fires the 2-char conjunct. "
        "Without conjunct: '->श, p->च gives निशचय (halant missing).",
    ),
    (
        "lqfuf" + chr(0x27) + "pr",
        "सुनिश्चित",
        "i-matra half-form fix: sunishchit (p7 corpus: lq=सु, fu=नि, "
        "then f-i-matra fires, ' in artifact_k_chars + next≠k → emits श् as half-form, "
        "p=च gets the ि → श्चि, r=त → सुनिश्चित). "
        "Before fix: f consumed ' as consonant giving शि, result was सुनिशिचत.",
    ),

    # -----------------------------------------------------------------------
    # Ý (U+00DD) -> फ्र  and  D (U+0044) -> क्  — फ्रैक्चर
    # -----------------------------------------------------------------------
    (
        "ÝSDpj",
        "फ्रैक्चर",
        "Ý->फ्र + D->क्: fracture (p7: Ý=फ्र combined glyph, S=ै, D=क्, p=च, j=र). "
        "Ý (U+00DD) is the KrutiDev ligature for फ्र, analogous to ç→प्र. "
        "D was wrongly mapped to ड (UNVERIFIED); corpus proves D=क् via अक्तूबर.",
    ),
    (
        "vDrwcj",
        "अक्तूबर",
        "D->क् bonus: October (p7 date line: v=अ, D=क्, r=त, w=ू, c=ब, j=र → अक्तूबर). "
        "Before fix: vDrwcj → अडतूबर (D was mapped to ड).",
    ),
]


# ---------------------------------------------------------------------------
# Test infrastructure
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def mapping():
    """Load the mapping once for the whole test module."""
    return load_mapping()


@pytest.mark.parametrize(
    "krutidev, expected, description",
    KNOWN_CONVERSIONS,
    ids=[case[2][:60] for case in KNOWN_CONVERSIONS],  # truncate for readable IDs
)
def test_conversion(krutidev: str, expected: str, description: str, mapping: dict) -> None:
    """Each row in KNOWN_CONVERSIONS is a test case."""
    result = convert(krutidev, mapping=mapping)
    assert result == expected, (
        f"\nCase: {description}"
        f"\nInput (krutidev): {repr(krutidev)}"
        f"\nExpected unicode: {repr(expected)}"
        f"\nGot:              {repr(result)}"
        f"\n\nIf the mapping is wrong, edit data/krutidev_map.json and re-run."
    )


# ---------------------------------------------------------------------------
# Structural / robustness tests (not mapping-specific)
# ---------------------------------------------------------------------------

def test_empty_string(mapping: dict) -> None:
    assert convert("", mapping=mapping) == ""


def test_spaces_preserved(mapping: dict) -> None:
    result = convert("l e", mapping=mapping)
    # 'l'→स, ' '→' ', 'e'→म
    assert " " in result


def test_unknown_chars_pass_through(mapping: dict) -> None:
    """Characters not in the mapping should be kept as-is (visible gaps)."""
    result = convert("\x00\x01", mapping=mapping)
    assert result == "\x00\x01"


def test_i_matra_at_end_of_string(mapping: dict) -> None:
    """
    Trailing i-matra with no following consonant should not crash.
    The converter should emit the matra as-is.
    """
    result = convert("f", mapping=mapping)
    assert result == "ि"


def test_conjunct_takes_priority_over_single(mapping: dict) -> None:
    """
    'vks' must convert to ओ (conjunct), not अ + ा + े (three separate chars).
    This verifies that conjunct rules fire before single-char rules.
    """
    result = convert("vks", mapping=mapping)
    assert result == "ओ", (
        f"Expected conjunct 'vks'→'ओ' but got {repr(result)}. "
        "Check that conjuncts are tried before direct substitution."
    )


def test_longer_conjunct_before_shorter(mapping: dict) -> None:
    """
    'vks' (3-char conjunct → ओ) must win over 'vk' (2-char conjunct → आ).
    The algorithm tries longest conjunct first.
    """
    result = convert("vks", mapping=mapping)
    assert result == "ओ"   # NOT आ + े


def test_load_mapping_returns_expected_structure() -> None:
    """Smoke-test that the mapping file loads cleanly."""
    m = load_mapping()
    assert "conjuncts" in m
    assert "i_matra_chars" in m
    assert "direct" in m
    assert len(m["conjuncts"]) > 0
    assert len(m["direct"]) > 0
    assert "f" in m["i_matra_chars"]
