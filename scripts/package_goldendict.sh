#!/usr/bin/env bash
# Build the GoldenDict (Linux/Windows) dictionary folder from the Apple
# Dictionary source XML.
#
# Prerequisite: src/IcelandicDictionary.xml already built by scripts/build_dict.py.
#
# NOTE ON LICENSING. The INO lexical data is CC BY-NC-ND 4.0. The ND clause
# forbids distributing converted versions, and a StarDict set is a converted
# version just as much as a .dictionary bundle is. So this deliberately does NOT
# produce a release zip: it builds a folder for you to point your own GoldenDict
# at, on your own machines. Do not publish the output.
#
# The .dict is dictzip-compressed by scripts/dictzip.py - no external binary
# needed, so this produces the same artifact on any machine with Python.
set -euo pipefail

cd "$(dirname "$0")/.."

OUT=dist/goldendict

rm -rf "$OUT"
mkdir -p "$OUT"

python3 scripts/build_stardict.py src/IcelandicDictionary.xml \
    --out "$OUT" \
    --name Islenska \
    --bookname "Íslenska" \
    --website "https://github.com/Josolon/icelandic-dictionary" \
    --description "Íslensk nútímamálsorðabók with BÍN morphology, pronunciation and hyphenation. Data: Stofnun Árna Magnússonar / CLARIN Iceland (CC BY-NC-ND 4.0); morphology via BÍN (Miðeind ehf.). Built locally for personal use - not for redistribution."

python3 scripts/verify_stardict.py "$OUT/Islenska"

cp src/GoldenDictArticle.css "$OUT/article-style.css"
cp docs/GOLDENDICT.md "$OUT/README.md"
cp LICENSE "$OUT/LICENSE"
cp CREDITS.md "$OUT/CREDITS.md"

echo
echo "Built $OUT - point GoldenDict at this folder."
echo "Personal use only: the INO data's ND clause forbids redistributing it."
du -sh "$OUT"
