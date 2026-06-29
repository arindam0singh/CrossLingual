# Known Limitations

Documented failure cases for the KrutiDev → Unicode converter.

---

## 1. English text rendered through the KrutiDev font

**Root cause**: KrutiDev is a font, not an encoding. When an author types English
letters in a KrutiDev-font text box, the PDF stores the raw ASCII codepoints — the
same codepoints that represent Hindi characters in KrutiDev. The rule-based converter
has no way to know whether `E` means "ए (the vowel)" or the English letter `E`.

**Effect**: English acronyms, proper nouns, and model names get converted as if they
were Hindi, producing garbage output.

**Examples from SM_Oct2025.pdf**:

| KrutiDev (raw) | Converter output | Expected output | Context |
|---|---|---|---|
| `EOTS` | `म्व्ज्ै` | `EOTS` | Electro-Optical Tracking System (p10) |
| `NG` | `छघ` | `NG` | Missile/system suffix (p10: N=छ, G=घ) |
| `LOS` | `स्व्ै` | `LOS` | Line-Of-Sight (p10) |
| `DMR` | `डडत्` | `DMR` | Defence Metallurgical Research (steel grade `DMR-1700`) |
| `SMRSAM` | `ैडत्ै।ड` | `SMRSAM` | Surface-to-Surface Missile System (p10) |
| `Banshee` | `ठंदेीमम` | `Banshee` | Drone model name (aerial target) (p10) |
| `BCP/CU/CCU` | `ठछच्/छन्/` | `BCP/CU/CCU` | Bus topology abbreviations (p10; `/` now correct after `@`→`/` fix) |
| `IRSS` | `प्त्ैै` | `IRSS` | Index of Radar Signature System (p13) |
| `RCS` | `त्ब्ै` | `RCS` | Radar Cross Section abbreviation (p13) |
| `NIRVANA` | `छप्त्ट।छ।` | `NIRVANA` | Software tool name: N=छ, I=प्, R=त्, V=ट, A=।, N=छ, A=। (p13) |
| `3-D` | `३-क्` | `3-D` | Three-dimensional; D(U+0044) maps to क् (p10) |
| `POSH` | `च्व्ैभ` | `POSH` | Prevention of Sexual Harassment Act; P=च्, O=व्, S=ै, H=भ (p19) |

**Solvable without ML via font-aware extraction**: Span-level inspection of this PDF
(via `page.get_text("dict")`) reveals that every English span is set in
`TimesNewRomanPSMT` or `TimesNewRomanPS-BoldMT`, while every Hindi span is in a
`KrutiDev*` variant. The fix is to check the span font at extraction time:
- If font contains "KrutiDev" → convert with the rule-based converter
- Else → keep the span text as-is (it is already readable Unicode)

This is implemented in `src/extract_pdf.py` via `extract_pages(..., font_aware=True)`
(default). When a `mapping` is passed to `extract_and_convert_pages()`, conversion
happens inline per-span so English acronyms are preserved exactly.

---

## 2. Double-k rendering artifact (FIXED for systematic cases)

**Root cause**: The KrutiDev font renderer in this PDF inserts a spurious `k` glyph
(which maps to the ā matra `ा`) immediately after certain consonant glyphs as a
visual alignment placeholder. This `k` has no phonetic meaning.

**Affected consonants** (confirmed from corpus analysis of SM_Oct2025.pdf):

| KrutiDev char | Unicode | Notes |
|---|---|---|
| `H` | भ | |
| `F` | थ | most common; appears in साथ, तथा, स्थित, स्थापित, समर्थन, धातु… |
| `'` | श | |
| `/` | ध | |
| `Ù` (U+00D9) | त्त | double-ta cluster |

**Fix implemented**: `artifact_k_chars` in `converter.py` (Steps 2 and 4). After
emitting the Unicode for any of these five consonants, the converter checks whether
the next raw character is `k` and consumes it without output.

**Verified words now correct**:
साथ, तथा, भी, भिलाई, स्थित, स्थापित, धातुकर्म, गुणवत्ता, शक्ति, समर्थन, मार्गदर्शन, हथियार, मार्गदर्शन…

**Residual limitation**: Any other consonant glyph in this PDF that also triggers
the spurious-k behavior but is NOT in `artifact_k_chars` will still produce an
incorrect ā. Add the character to the set in `converter.py` if encountered.

---

## 3. Punctuation mappings (RESOLVED)

KrutiDev uses non-obvious codepoints for common punctuation. All confirmed cases are
now mapped in `data/krutidev_map.json`:

| KrutiDev char | Unicode | Notes |
|---|---|---|
| `]` (U+005D) | `,` | Hindi comma; ASCII `,` maps to ए (standalone e vowel) |
| `%` | `:` | Colon (not percent sign) |
| `¼` (U+00BC) | `(` | Opening parenthesis |
| `½` (U+00BD) | `)` | Closing parenthesis |
| `)` (U+0029) | `द्ध` | da+halant+dha conjunct — VERIFIED from `çfrc)rk`=`प्रतिबद्धता`, `ifj'kq)rk`=`परिशुद्धता` |
| `=` (U+003D) | `त्र` | ta+halant+ra cluster — VERIFIED from `;a=`=`यंत्र`, `ea=ky;`=`मंत्रालय` |

**Note on `=` vs `=k`**: The unverified conjunct `=k` → `ज्ञ` was removed. `ज्ञ` is
correctly handled by `K` (capital K, a single KrutiDev glyph). In sequences like
`ea=ky;` (मंत्रालय), `=` gives `त्र` and `k` gives ā — no conjunct needed.

**Note on `)` in structural context**: ASCII `)` in structural English text (e.g., the
outer `)` in attribution lines) will incorrectly convert to `द्ध` in the raw converter.
Font-aware extraction (Section 1) prevents this — structural parens are in
`TimesNewRoman` and are preserved as-is.

**Known residual**: The ASCII `,` → ए mapping is correct for Hindi vowel use but
converts literal commas inside English abbreviations (e.g., `BCP,CU`). This is
subsumed by the font-aware extraction fix (section 1) — English spans bypass the
converter entirely.

**`)` in attribution lines (PARTIAL FIX)**: ASCII `)` normally converts to `द्ध` (a
verified conjunct used in ~38 Hindi words in this PDF). Attribution lines like
`(राम सरन, ..., देहरादून)` use ASCII `)` as a closing bracket. The raw converter
repairs this when the output line starts with `(` and the last emitted token is `द्ध`
— replacing `द्ध` with `)`. This covers the typical attribution pattern. Attribution
lines enclosed with `¼...½` (KrutiDev parentheses) are not affected and always work
correctly.

---

## 4. Version-number decimal point (`&` ambiguity)

**What it is**: KrutiDev uses `&` (U+0026) for the hyphen/dash character.
The same `&` is also used for the decimal point in version numbers.

**Effect**: `3&D` → `३-D` (correct: dash), but `3&0` → `३-०` (wrong: shows
`३-०` instead of `३.०`).

**Example** (p13): `¼MhchvkbZ,e 3&0½ ds vuqlkj` → `(डीबीआईएम ३-०) के अनुसार`
Expected: `(डीबीआईएम ३.०) के अनुसार` (DBIM version 3.0)

**Workaround**: None simple — `&` → `-` is correct in more contexts (compound
words, date ranges, `3-D`) than `&` → `.` (only version numbers). Disambiguate
in post-processing if needed.

---

## 5. Grade-designation quote marker (`^`) — FIXED

**What it was**: ASCII caret `^` (U+005E) was passing through unchanged, giving
`^एफ^` for grade designations.

**Fix applied**: `^` → `'` (APOSTROPHE U+0027) in `data/krutidev_map.json`.

**Current output** (p13): `ih ds iVuk;d] oSKkfud ^,Q^` → `पी के पटनायक, वैज्ञानिक 'एफ'` ✓

**Note on double-caret**: `^^text` (two carets before an English title) now gives `''text`.
This occurs only in English title spans which are Tier-3 (Section 1).
