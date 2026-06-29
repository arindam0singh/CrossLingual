"""
Show raw KrutiDev text alongside the converter output, line by line.
Writes a UTF-8 report file alongside each raw file so Devanagari renders.

Usage:
    python scripts/compare_raw_vs_converted.py data/extracted/SM_Oct2025_p7_raw.txt
    (no args = processes both p7 and p10 default files)
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

# Allow importing from src/ when run from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.converter import load_mapping, convert

SEP_WIDTH = 70


def compare_file(raw_path: str | Path, out: io.TextIOWrapper | None = None) -> None:
    raw_path = Path(raw_path)
    text = raw_path.read_text(encoding="utf-8")
    mapping = load_mapping()

    lines_out: list[str] = [
        f"\n{'='*SEP_WIDTH}",
        f"FILE: {raw_path.name}",
        f"{'='*SEP_WIDTH}",
        f"{'RAW KRUTIDEV':<35} | CONVERTED UNICODE",
        "-" * SEP_WIDTH,
    ]

    for line in text.splitlines():
        if not line.strip():
            continue
        converted = convert(line, mapping=mapping)
        lines_out.append(f"RAW: {line}")
        lines_out.append(f"OUT: {converted}")
        lines_out.append("")

    report = "\n".join(lines_out)

    # Write UTF-8 report file
    report_path = raw_path.with_suffix(".comparison.txt")
    report_path.write_text(report, encoding="utf-8")

    # Print to console safely (replace unencodable chars)
    if out is None:
        sys.stdout.buffer.write((report + "\n").encode("utf-8", errors="replace"))
    else:
        out.write(report + "\n")

    print(f"[report written to {report_path}]", file=sys.stderr)


if __name__ == "__main__":
    paths = sys.argv[1:] if len(sys.argv) > 1 else [
        "data/extracted/SM_Oct2025_p7_raw.txt",
        "data/extracted/SM_Oct2025_p10_raw.txt",
    ]
    for p in paths:
        compare_file(p)
