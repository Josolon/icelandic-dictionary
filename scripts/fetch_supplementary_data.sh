#!/usr/bin/env bash
# Downloads optional enrichment datasets (pronunciation, hyphenation) from the
# CLARIN-IS repository and stages them under data/. Both sources are CC BY
# licensed (unlike the CC BY-NC-ND INO data), so they may be freely re-derived.
#
# Safe to re-run; re-downloads and overwrites the staged files.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DATA_DIR="${REPO_ROOT}/data"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "${WORK_DIR}"' EXIT

PRON_URL="https://repository.clarin.is/repository/xmlui/bitstream/handle/20.500.12537/198/pron_dict.zip?sequence=1&isAllowed=y"
HYPH_URL="https://repository.clarin.is/repository/xmlui/bitstream/handle/20.500.12537/86/hyphenation-is.zip?sequence=1&isAllowed=y"

echo "[1/4] Downloading Pronunciation Dictionary for Icelandic (CC BY 3.0)"
curl -sL "${PRON_URL}" -o "${WORK_DIR}/pron_dict.zip"
mkdir -p "${DATA_DIR}/pronunciation"
unzip -o -q "${WORK_DIR}/pron_dict.zip" -d "${DATA_DIR}/pronunciation"

echo "[2/4] Downloading Icelandic Hyphenation Dictionary 2.0 (CC BY 4.0)"
curl -sL "${HYPH_URL}" -o "${WORK_DIR}/hyphenation-is.zip"
mkdir -p "${DATA_DIR}/hyphenation"
unzip -o -q "${WORK_DIR}/hyphenation-is.zip" -d "${WORK_DIR}/hyphenation-extract"
cp "${WORK_DIR}/hyphenation-extract/hyphenation-is/hyph_is_list.txt" "${DATA_DIR}/hyphenation/"
cp "${WORK_DIR}/hyphenation-extract/hyphenation-is/README.md" "${DATA_DIR}/hyphenation/README_upstream.md"

echo "[3/4] Converting pronunciation .xls to .tsv (word, ipa, sampa)"
PYTHON_BIN="${REPO_ROOT}/venv/bin/python3"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi
"${PYTHON_BIN}" -m pip install --quiet xlrd
"${PYTHON_BIN}" "${SCRIPT_DIR}/convert_pronunciation_xls.py" \
  "${DATA_DIR}/pronunciation/WordList_IPA_SAMPA.xls" \
  "${DATA_DIR}/pronunciation/pronunciation.tsv"

echo "[4/4] Done. Staged data:"
echo "  ${DATA_DIR}/pronunciation/pronunciation.tsv"
echo "  ${DATA_DIR}/hyphenation/hyph_is_list.txt"
