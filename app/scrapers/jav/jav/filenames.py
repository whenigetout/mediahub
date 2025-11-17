#!/usr/bin/env python3
"""
extract_jav_codes.py

Usage:
    python extract_jav_codes.py "D:\hide\Ecchi no Folder Ni\mediahub D drive" -o out.csv

Features:
- Recursively finds video files under one or more root folders
- Extracts JAV codes from filenames using a permissive regex and normalizes them (e.g. JUQ184 -> JUQ-184)
- Outputs CSV and JSON (both written unless --json/--csv flags used)
- Prints a small summary

Adjust the video extensions and regex patterns below if needed.
"""

from pathlib import Path
import re
import argparse
import csv
import json
from typing import Optional, List, Dict

VIDEO_EXTS = {
    ".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".webm", ".mpeg", ".mpg", ".m4v", 'ts'
}

# Candidate regex patterns (case-insensitive). Tweak/add patterns if you find other formats.
MASTER_PATTERNS = [
    r"\b[A-Z]{1,5}-\d{2,4}[A-Z]?\b",   # ABC-123 or ABC-123A
    r"\b[A-Z]{1,5}\d{2,4}[A-Z]?\b",    # ABC123 or ABC123A
]

master_re = re.compile("|".join(f"({p})" for p in MASTER_PATTERNS), re.I)


def extract_jav_code(filename: str, preserve_leading_zeros: bool = True) -> Optional[str]:
    """Extract and normalize JAV code from a filename.
    Returns normalized code like ABC-123 or None.
    By default preserves any leading zeros in the numeric part (e.g., NAFZ-001).
    Set preserve_leading_zeros=False to strip leading zeros (NAFZ-1).
    """
    if not filename:
        return None

    m = master_re.search(filename)
    if not m:
        return None

    # find which group matched (same approach you used)
    matched = next((g for g in m.groups() if g), None)
    if not matched:
        return None

    code = matched.upper().replace("_", "-").replace(" ", "").strip()

    # Accept numeric part as-is, optionally strip leading zeros
    m2 = re.match(r"^([A-Z]+)-?([0-9]+)([A-Z]?)$", code)
    if m2:
        prefix, num_str, suffix = m2.groups()
        if preserve_leading_zeros:
            norm = f"{prefix}-{num_str}{suffix}"
        else:
            # strip leading zeros safely (but preserve "0" if number is 0)
            norm = f"{prefix}-{int(num_str):d}{suffix}"
        return norm

    # fallback: return the uppercase matched token
    return code


def find_video_files(roots: List[Path]) -> List[Path]:
    """Recursively find files with video extensions under the given root paths."""
    files = []
    for root in roots:
        if not root.exists():
            print(f"[warn] root does not exist: {root}")
            continue
        # rglob can be used to check all files and filter extension
        for p in root.rglob("*"):
            if p.is_file(): #and p.suffix.lower() in VIDEO_EXTS:
                files.append(p)
    return sorted(files)


def build_records(files: List[Path], base_roots: List[Path]) -> List[Dict]:
    """Return a list of dict records with path, filename, jav_code, dirname, ext, relative_path."""
    records = []
    for p in files:
        fname = p.name
        code = extract_jav_code(fname)
        # compute which root contains this file to build a relative path (first matching root)
        rel = None
        for root in base_roots:
            try:
                if root in p.parents or p == root:
                    rel = str(p.relative_to(root))
                    break
            except Exception:
                rel = None
        records.append({
            "full_path": str(p.resolve()),
            "filename": fname,
            "jav_code": code,
            "dir": str(p.parent),
            "ext": p.suffix.lower(),
            "relative_path": rel
        })
    return records


def write_csv(records: List[Dict], out_csv: Path):
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        fieldnames = ["full_path", "relative_path", "dir", "filename", "ext", "jav_code"]
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow({k: r.get(k, "") for k in fieldnames})


def write_json(records: List[Dict], out_json: Path):
    with out_json.open("w", encoding="utf-8") as fh:
        json.dump(records, fh, indent=2, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser(description="Recursively extract filenames and JAV codes from folder(s)")
    ap.add_argument("roots", nargs="+", help="Root folder(s) to scan")
    ap.add_argument("-o", "--out", default="jav_codes.csv", help="Output base filename (csv & json)")
    ap.add_argument("--csv", action="store_true", help="Write CSV output")
    ap.add_argument("--json", action="store_true", help="Write JSON output")
    ap.add_argument("--no-csv", dest="csv_force_false", action="store_true", help="Do not write CSV")
    ap.add_argument("--no-json", dest="json_force_false", action="store_true", help="Do not write JSON")
    ap.add_argument("--exts", help="Comma-separated extra extensions to consider (e.g. .ts,.rmvb)")
    args = ap.parse_args()

    roots = [Path(r) for r in args.roots]
    if args.exts:
        for e in args.exts.split(","):
            e = e.strip().lower()
            if e and not e.startswith("."):
                e = "." + e
            VIDEO_EXTS.add(e)

    files = find_video_files(roots)
    print(f"Found {len(files)} video files under {len(roots)} root(s).")

    records = build_records(files, roots)

    out_base = Path(args.out)
    write_csv_flag = not args.json_force_false
    write_json_flag = not args.csv_force_false

    # default behavior: write both csv and json unless flags say otherwise
    if not args.csv and not args.json:
        write_csv_flag = True
        write_json_flag = True

    if write_csv_flag:
        csv_path = out_base.with_suffix(".csv") if out_base.suffix == "" else out_base
        if csv_path.suffix.lower() != ".csv":
            csv_path = csv_path.with_suffix(".csv")
        write_csv(records, csv_path)
        print(f"Wrote CSV → {csv_path}")

    if write_json_flag:
        json_path = out_base.with_suffix(".json") if out_base.suffix == "" else out_base.with_suffix(".json")
        write_json(records, json_path)
        print(f"Wrote JSON → {json_path}")

    # summary
    total = len(records)
    with_code = sum(1 for r in records if r["jav_code"])
    print(f"Total files: {total}; files with detected jav code: {with_code}")
    if with_code < total:
        print("Some files had no jav code detected. You can tweak regex patterns in the script.")


if __name__ == "__main__":
    main()
