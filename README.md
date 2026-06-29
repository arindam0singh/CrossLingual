# KrutiDev → Unicode Converter for DRDO Hindi PDFs

Recovers Unicode Devanagari from legacy KrutiDev-encoded Hindi text
extracted from DRDO newsletter PDFs.

## Project structure

```
DRDO/
├── data/
│   ├── krutidev_map.json   ← THE mapping table — edit this to fix errors
│   ├── raw/                ← put your PDF files here
│   └── extracted/          ← raw extracted text is written here
├── src/
│   ├── converter.py        ← KrutiDev→Unicode conversion logic
│   └── extract_pdf.py      ← PDF text extraction (PyMuPDF)
├── tests/
│   └── test_converter.py   ← pytest tests with known examples
├── notebooks/              ← Jupyter notebooks for exploration
├── requirements.txt
└── README.md
```

## Setup

```bash
pip install -r requirements.txt
```

## Step 1: Extract raw text from a PDF

From the project root:

```bash
python src/extract_pdf.py data/raw/newsletter.pdf --pages 1-5 --out data/extracted/newsletter_raw.txt
```

- `--pages 3` extracts only page 3
- `--pages 1-10` extracts pages 1 through 10
- Omit `--pages` to extract all pages
- Omit `--out` to auto-name the file in `data/extracted/`

The output file will contain garbled ASCII — that is expected for KrutiDev text.

## Step 2: Convert a string

Quick one-off test from the command line:

```bash
python src/converter.py "MhvkjMhvks lekpkj"
# → डीआरडीओ समाचार
```

Programmatic use in a script or notebook:

```python
from src.converter import load_mapping, convert

# Load once, reuse many times:
mapping = load_mapping()
result = convert("MhvkjMhvks lekpkj", mapping=mapping)
print(result)  # डीआरडीओ समाचार
```

## Step 3: Run the tests

```bash
pytest tests/ -v
```

Expected output: all tests pass. If a mapping is wrong, the test output shows
the expected vs. actual Unicode so you know exactly which char to fix in
`data/krutidev_map.json`.

## Correcting the mapping

The file `data/krutidev_map.json` is the single source of truth.

1. Extract a page from your PDF (Step 1).
2. Find a word or phrase you can identify — e.g., a proper noun or headline.
3. Look at the raw ASCII chars and compare to the expected Unicode.
4. Edit the matching entry in `krutidev_map.json`:
   - Under `direct.entries`: change the `unicode` value for a single char.
   - Under `conjuncts.entries`: add or modify a multi-char rule.
5. Add the case to `tests/test_converter.py` → `KNOWN_CONVERSIONS`.
6. Run `pytest` to verify.

Entries marked `VERIFIED` in the map are confirmed from ground-truth examples.
Entries marked `UNVERIFIED` are best-guess estimates from the Remington
Hindi keyboard layout — they will likely need correction.

## How KrutiDev encoding works

KrutiDev is a font, not an encoding. Each ASCII character in the font is
*drawn* as a specific Devanagari glyph. When a PDF is extracted, you get
the raw ASCII codepoints, not the visual Devanagari.

Three complications:
1. **Standalone vowels** (आ, ओ, औ) are composed of multiple keystrokes in
   KrutiDev. E.g., `vk` → `आ`. These are handled by the `conjuncts` table.
2. **The short i-matra** (ि) is stored *before* its consonant in KrutiDev
   (a typewriter mechanical constraint), but Unicode requires it *after*.
   E.g., `fM` (i-matra, then ड) → `डि` in Unicode. This is the i-matra
   reordering rule in `converter.py`.
3. **Consonant clusters** (क्ष, ज्ञ, त्र) may have dedicated multi-char
   glyph sequences. Add them to `conjuncts` as you encounter them.