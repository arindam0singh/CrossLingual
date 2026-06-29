"""
KrutiDev-010 → Unicode Devanagari converter.

KrutiDev is a legacy Hindi font that maps Devanagari glyphs onto ASCII
codepoints. When a PDF using this font is text-extracted, the result is
garbled ASCII. This module converts that ASCII back to proper Unicode.

Algorithm overview:
  1. Load the mapping table from data/krutidev_map.json.
  2. For each position in the input string, try multi-char "conjunct" rules
     first (longest match wins). Conjuncts cover standalone vowels like
     आ (vk) and ओ (vks), and consonant clusters like क्ष.
  3. Handle the i-matra reversal: in KrutiDev the short 'i' matra (ि) is
     stored BEFORE the consonant it modifies (a typewriter constraint). In
     Unicode it must come AFTER. So 'fk' → क + ि = 'कि', not 'fक'.
  4. Apply single-char substitution for everything else.
  5. Unrecognised characters are passed through unchanged so you can see
     what still needs mapping.

The mapping is in data/krutidev_map.json — edit that file to correct errors.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Map loading
# ---------------------------------------------------------------------------

def _default_map_path() -> Path:
    """Return the default path to krutidev_map.json relative to this file."""
    # src/converter.py → project root → data/krutidev_map.json
    return Path(__file__).parent.parent / "data" / "krutidev_map.json"


def load_mapping(map_path: Optional[str | Path] = None) -> dict:
    """
    Load and parse the KrutiDev mapping JSON file.

    Parameters
    ----------
    map_path : str or Path, optional
        Path to krutidev_map.json. Defaults to data/krutidev_map.json
        relative to the project root.

    Returns
    -------
    dict with keys:
        conjuncts  : list of (krutidev_str, unicode_str) sorted longest-first
        i_matra_chars : set of single chars that trigger i-matra reordering
        i_matra_unicode : the Unicode char for the short i matra (ि)
        direct     : dict mapping single ASCII char → Unicode string
    """
    path = Path(map_path) if map_path else _default_map_path()
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    # --- conjuncts: list of (source, target), sorted longest-first so that
    #     longer patterns are tried before shorter ones overlap them.
    conjunct_list = [
        (entry["krutidev"], entry["unicode"])
        for entry in raw["conjuncts"]["entries"]
    ]
    conjunct_list.sort(key=lambda x: len(x[0]), reverse=True)

    # --- i-matra
    i_matra_chars = set(raw["i_matra"]["i_matra_chars"])
    i_matra_unicode = raw["i_matra"]["i_matra_unicode"]

    # --- direct: dict for O(1) lookup
    direct = {
        entry["krutidev"]: entry["unicode"]
        for entry in raw["direct"]["entries"]
    }

    return {
        "conjuncts": conjunct_list,
        "i_matra_chars": i_matra_chars,
        "i_matra_unicode": i_matra_unicode,
        "direct": direct,
    }


# ---------------------------------------------------------------------------
# Core conversion
# ---------------------------------------------------------------------------

def convert(text: str, mapping: Optional[dict] = None, map_path: Optional[str | Path] = None) -> str:
    """
    Convert a KrutiDev-encoded string to Unicode Devanagari.

    Parameters
    ----------
    text : str
        Raw ASCII text extracted from a KrutiDev PDF.
    mapping : dict, optional
        Pre-loaded mapping dict from load_mapping(). Pass this when converting
        many strings to avoid reloading the file each time.
    map_path : str or Path, optional
        Path to an alternative mapping JSON file. Ignored if `mapping` is given.

    Returns
    -------
    str
        Unicode Devanagari string. Unrecognised chars are kept as-is so you
        can identify gaps in the mapping table.
    """
    if mapping is None:
        mapping = load_mapping(map_path)

    # U+2019 (RIGHT SINGLE QUOTATION MARK ') is sometimes extracted from PDFs
    # instead of U+0027 (APOSTROPHE '). Both represent the KrutiDev sha glyph.
    # Normalise here so all downstream rules (artifact_k_chars, conjuncts) fire
    # uniformly without duplicating every entry.
    text = text.replace('’', "'")

    conjuncts = mapping["conjuncts"]
    i_matra_chars = mapping["i_matra_chars"]
    i_matra_unicode = mapping["i_matra_unicode"]
    direct = mapping["direct"]

    # Certain KrutiDev consonant glyphs extend visually to the right and the
    # PDF renderer inserts a spurious 'k' (normally ā-matra) immediately after
    # them as a spacing placeholder.  That first 'k' carries no phonetic value
    # and must be consumed without producing output.
    #
    # Confirmed from corpus analysis of SM_Oct2025.pdf:
    #   H = भ   F = थ   ' = श   / = ध   Ù (U+00D9) = त्त
    #
    # The conjunct-based consonants (.k→ण, {k→क्ष, [k→ख) are NOT in this set —
    # there the first 'k' is part of the conjunct rule and the second 'k' is
    # the real ā matra.
    artifact_k_chars: frozenset[str] = frozenset({'H', 'F', "'", '/', '\xd9', '?', '\xe8'})

    result: list[str] = []
    i = 0
    n = len(text)

    while i < n:
        char = text[i]

        # ------------------------------------------------------------------
        # Step 1: Try conjunct (multi-char) patterns, longest first.
        # This handles standalone vowels (vk→आ, vks→ओ) and consonant clusters.
        # ------------------------------------------------------------------
        matched_conjunct = False
        for kd_seq, uni_seq in conjuncts:
            seq_len = len(kd_seq)
            if text[i:i + seq_len] == kd_seq:
                result.append(uni_seq)
                i += seq_len
                matched_conjunct = True
                break

        if matched_conjunct:
            continue

        # ------------------------------------------------------------------
        # Step 2: i-matra reordering.
        #
        # In KrutiDev the short 'i' matra (ि) is placed BEFORE the consonant
        # it belongs to (typewriter constraint). Unicode requires: consonant THEN ि.
        #
        # Complication: in consonant clusters like स्थित (encoded fLFkr), a
        # half-form consonant like L (=स्) may appear between f and the target.
        # Half-forms are identified by their Unicode ending with virama (्).
        # We emit all leading half-forms first, then attach ि to the next char.
        # ------------------------------------------------------------------
        if char in i_matra_chars:
            i += 1
            # Emit any leading half-form consonants (those ending with ् virama)
            while i < n:
                peek = direct.get(text[i], text[i])
                if peek.endswith('्'):  # U+094D = ् virama
                    # Before consuming as a half-form, check whether this char
                    # starts a conjunct that yields a FULL consonant (not ending
                    # in virama). If so the conjunct is the i-matra host, not a
                    # prefix half-form — break so the host step below handles it.
                    # e.g. f"kZd: " has direct="ष्", but "k->ष (full), so break.
                    is_conjunct_host = any(
                        text[i:i + len(kd)] == kd and not uni.endswith('्')
                        for kd, uni in conjuncts
                    )
                    if is_conjunct_host:
                        break
                    result.append(peek)
                    i += 1
                elif text[i] in artifact_k_chars and i + 1 < n and text[i + 1] != 'k':
                    # artifact_k consonant (श, भ, थ, ध, त्त) followed by a real
                    # consonant — emit as a half-form so i-matra binds to what follows.
                    # e.g. f'p -> श् + चि = श्चि (for निश्चित) rather than शि + च.
                    result.append(direct.get(text[i], text[i]) + '्')
                    i += 1
                else:
                    break
            if i < n:
                # Try conjunct host first (e.g. "k->ष so f"kZd gives षि not ष्ि)
                host_matched = False
                for kd_seq, uni_seq in conjuncts:
                    if (text[i:i + len(kd_seq)] == kd_seq
                            and not uni_seq.endswith('्')):
                        result.append(uni_seq)
                        result.append(i_matra_unicode)
                        i += len(kd_seq)
                        host_matched = True
                        break
                if not host_matched:
                    next_char = text[i]
                    consonant_uni = direct.get(next_char, next_char)
                    result.append(consonant_uni)
                    i += 1
                    # Consume the artifact 'k' that follows certain consonant glyphs
                    if next_char in artifact_k_chars and i < n and text[i] == 'k':
                        i += 1
                    # Consume ्र suffix glyphs (z→्र, ª→्र) BEFORE emitting ि.
                    # Without this: f+c+z → बि्र (wrong). With it: → ब्रि (correct).
                    while i < n and direct.get(text[i], '') == '्र':
                        result.append(direct.get(text[i]))
                        i += 1
                    result.append(i_matra_unicode)
            else:
                result.append(i_matra_unicode)
            continue

        # ------------------------------------------------------------------
        # Step 3: Reph reordering.
        #
        # Z represents the reph form of र (र् placed above the following
        # consonant). In KrutiDev, the reph glyph is typed AFTER the consonant
        # it sits above; Unicode requires र् BEFORE that consonant.
        #
        # Fix: when Z is seen, pop the last output token and re-insert in the
        # order: र् + <popped_token>. This reverses the KrutiDev ordering.
        # Matra chars (aa, ii, etc.) between the consonant and Z are moved too.
        # ------------------------------------------------------------------
        if char == 'Z':
            reph = 'र्'
            # Collect matras that appear between the consonant and Z.
            # In this KrutiDev PDF, the font renderer inserts a spurious ā (ा)
            # glyph after many consonants as a rendering artifact (from a double 'k').
            # Other matras (ि, ी, ु …) are real and must be preserved.
            # Strategy: pop all matras, discard only ā (U+093E), keep the rest.
            matras: list[str] = []
            while result and result[-1] in {
                'ा', 'ि', 'ी', 'ु', 'ू', 'े', 'ै', 'ो', 'ौ', 'ं', 'ः', 'ँ', 'ृ',
            }:
                matras.append(result.pop())
            # Pop the consonant the reph belongs to, then prepend र्
            if result:
                consonant_tok = result.pop()
                result.append(reph)
                result.append(consonant_tok)
            else:
                result.append(reph)
            # Re-append all matras in original order.
            # artifact_k_chars consumed the spurious k before Z fires,
            # so any ा here is a genuine vowel (e.g. कर्ता from drkZ).
            result.extend(reversed(matras))
            i += 1
            continue

        # ------------------------------------------------------------------
        # Step 4: Single-char direct substitution.
        # ------------------------------------------------------------------
        if char in direct:
            result.append(direct[char])
        else:
            # Unknown char — keep it so we can see what needs mapping.
            result.append(char)
        i += 1
        # Consume the artifact 'k' that follows certain consonant glyphs
        if char in artifact_k_chars and i < n and text[i] == 'k':
            i += 1

    # '(' (ASCII U+0028) maps to '।' (danda) in KrutiDev.  But attribution
    # lines start with '(' in the raw and use it as a true opening bracket.
    # Detect by inspecting the *raw input*: if text[0] == '(' we know the
    # line opened with a bracket, and we restore both the opening '(' (which
    # became '।') and the closing ')' (which became 'द्ध').
    if text and text[0] == '(' and result:
        if result[0] == '।':
            result[0] = '('
        if len(result) >= 2 and result[-1] == 'द्ध':
            result[-1] = ')'

    return "".join(result)


# ---------------------------------------------------------------------------
# Convenience CLI entry point
# ---------------------------------------------------------------------------

def convert_string(krutidev_text: str, map_path: Optional[str | Path] = None) -> str:
    """
    Thin wrapper: load mapping once and convert. Useful for quick one-off use.
    """
    mapping = load_mapping(map_path)
    return convert(krutidev_text, mapping=mapping)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python converter.py '<krutidev text>'")
        sys.exit(1)

    raw = sys.argv[1]
    result = convert_string(raw)
    print(result)
