#!/usr/bin/env python3
"""One-time conversion: WordList_IPA_SAMPA.xls -> pronunciation.tsv (word, ipa, sampa).

Avoids requiring xlrd at every build; only needed once during data staging.
"""
import sys

import xlrd


def convert(xls_path, tsv_path):
    wb = xlrd.open_workbook(xls_path)
    sheet = wb.sheet_by_index(0)
    with open(tsv_path, "w", encoding="utf-8") as out:
        for row in range(sheet.nrows):
            word = str(sheet.cell_value(row, 0)).strip()
            ipa = str(sheet.cell_value(row, 1)).strip() if sheet.ncols > 1 else ""
            sampa = str(sheet.cell_value(row, 2)).strip() if sheet.ncols > 2 else ""
            if not word:
                continue
            out.write(f"{word}\t{ipa}\t{sampa}\n")
    print(f"Wrote {sheet.nrows} rows to {tsv_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: convert_pronunciation_xls.py <in.xls> <out.tsv>")
        sys.exit(1)
    convert(sys.argv[1], sys.argv[2])
