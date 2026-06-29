"""
PDF text extraction for KrutiDev-encoded Hindi PDFs.

Uses PyMuPDF (fitz) to extract raw text from each page. Because the PDF uses
the KrutiDev font, the extracted text will be garbled ASCII — that is expected.
The raw ASCII output is what you feed to converter.py.

Usage (command line):
    python src/extract_pdf.py path/to/file.pdf --pages 1-5 --out data/extracted/output.txt

Usage (programmatic):
    from src.extract_pdf import extract_pages
    raw = extract_pages("newsletter.pdf", start_page=1, end_page=3)
    # raw is a dict: {page_num: raw_text_string}
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional


def _is_kruti_font(font_name: str) -> bool:
    """Return True if the font name is a KrutiDev variant (needs conversion)."""
    lower = font_name.lower()
    return "krutidev" in lower or "kruti-dev" in lower or "kruti dev" in lower


def _page_to_text_font_aware(page, mapping=None) -> str:
    """
    Reconstruct page text preserving font boundaries.

    When `mapping` is provided (a pre-loaded converter mapping dict), KrutiDev
    spans are converted to Unicode inline and non-KrutiDev spans (English
    acronyms, numerals, etc.) are passed through unchanged.

    When `mapping` is None, all spans are returned as raw text (KrutiDev ASCII
    for Hindi spans, literal Unicode for English spans) — useful for saving a
    raw file that will be converted in a separate step.

    Within each line, spans are joined without extra whitespace; lines are
    separated by newlines, matching the behaviour of get_text("text").
    """
    if mapping is not None:
        from src.converter import convert as _convert
    else:
        _convert = None  # type: ignore[assignment]

    parts: list[str] = []
    blocks = page.get_text("dict")["blocks"]
    for blk in blocks:
        if blk.get("type") != 0:  # skip image blocks
            continue
        for line in blk["lines"]:
            line_parts: list[str] = []
            for span in line["spans"]:
                txt = span["text"]
                if not txt:
                    continue
                if _is_kruti_font(span["font"]):
                    # KrutiDev span: convert if mapping provided, else keep raw
                    line_parts.append(_convert(txt, mapping=mapping) if _convert else txt)
                else:
                    # Non-KrutiDev span (e.g. English in Times New Roman): keep as-is
                    line_parts.append(txt)
            if line_parts:
                parts.append("".join(line_parts))
    return "\n".join(parts)


def extract_pages(
    pdf_path: str | Path,
    start_page: int = 1,
    end_page: Optional[int] = None,
    font_aware: bool = True,
) -> dict[int, str]:
    """
    Extract raw text from a PDF file.

    Parameters
    ----------
    pdf_path : str or Path
        Path to the PDF file.
    start_page : int
        First page to extract (1-indexed, inclusive).
    end_page : int, optional
        Last page to extract (1-indexed, inclusive). Defaults to last page.
    font_aware : bool
        If True (default), use span-level font detection to preserve English
        text that is set in a non-KrutiDev font (e.g. EOTS, DMR, Banshee).
        If False, fall back to plain get_text("text") which loses font info.

    Returns
    -------
    dict[int, str]
        Mapping of 1-indexed page number → raw extracted text string.
        For KrutiDev PDFs, the text will be garbled ASCII mixed with any
        already-Unicode spans (English acronyms, numerals, etc.).

    Raises
    ------
    FileNotFoundError
        If the PDF path does not exist.
    ImportError
        If PyMuPDF (fitz) is not installed.
    ValueError
        If the page range is invalid.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError as e:
        raise ImportError(
            "PyMuPDF is required. Install it with: pip install pymupdf"
        ) from e

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(str(pdf_path))
    total_pages = len(doc)

    # Validate and normalise page range (convert to 0-indexed for fitz)
    start_0 = start_page - 1
    end_0 = (end_page - 1) if end_page is not None else (total_pages - 1)

    if start_0 < 0 or start_0 >= total_pages:
        raise ValueError(
            f"start_page={start_page} is out of range for a {total_pages}-page PDF."
        )
    if end_0 < start_0 or end_0 >= total_pages:
        raise ValueError(
            f"end_page={end_page} is out of range for a {total_pages}-page PDF."
        )

    result: dict[int, str] = {}
    for page_0 in range(start_0, end_0 + 1):
        page = doc[page_0]
        if font_aware:
            text = _page_to_text_font_aware(page)
        else:
            text = page.get_text("text")
        result[page_0 + 1] = text

    doc.close()
    return result


def extract_and_save(
    pdf_path: str | Path,
    output_path: str | Path,
    start_page: int = 1,
    end_page: Optional[int] = None,
) -> None:
    """
    Extract text from a PDF and write it to a file.

    Each page is separated by a header line:
        --- Page N ---
    so you can see where pages begin when inspecting the raw output.
    """
    pages = extract_pages(pdf_path, start_page=start_page, end_page=end_page)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        for page_num in sorted(pages):
            f.write(f"--- Page {page_num} ---\n")
            f.write(pages[page_num])
            f.write("\n")

    print(f"Extracted {len(pages)} page(s) from '{pdf_path}' -> '{output_path}'")


def _parse_page_range(range_str: str) -> tuple[int, Optional[int]]:
    """Parse '3' or '3-7' into (start, end) ints."""
    if "-" in range_str:
        parts = range_str.split("-", 1)
        return int(parts[0]), int(parts[1])
    return int(range_str), int(range_str)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract raw text from a KrutiDev-encoded PDF."
    )
    parser.add_argument("pdf", help="Path to the PDF file.")
    parser.add_argument(
        "--pages",
        default=None,
        help="Page range to extract, e.g. '1' or '1-5'. Default: all pages.",
    )
    parser.add_argument(
        "--out",
        default=None,
        help=(
            "Output file path. Default: data/extracted/<pdf_stem>_raw.txt"
        ),
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    start, end = _parse_page_range(args.pages) if args.pages else (1, None)

    if args.out:
        output_path = Path(args.out)
    else:
        output_path = (
            Path("data") / "extracted" / f"{pdf_path.stem}_raw.txt"
        )

    try:
        extract_and_save(pdf_path, output_path, start_page=start, end_page=end)
    except (FileNotFoundError, ValueError, ImportError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
