"""Optional pronunciation/hyphenation lookups from CLARIN-IS datasets.

Both sources are CC BY licensed (unlike the CC BY-NC-ND INO data) and are
staged locally via scripts/fetch_supplementary_data.sh. If a dataset hasn't
been fetched, the corresponding loader returns an empty dict and the build
proceeds without that enrichment.
"""
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
PRONUNCIATION_TSV = os.path.join(DATA_DIR, "pronunciation", "pronunciation.tsv")
HYPHENATION_TXT = os.path.join(DATA_DIR, "hyphenation", "hyph_is_list.txt")


def load_pronunciation_lookup(path=PRONUNCIATION_TSV):
    """word (lowercase) -> (ipa, sampa). Empty dict if dataset not staged."""
    lookup = {}
    if not os.path.exists(path):
        return lookup
    with open(path, encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if not parts or not parts[0]:
                continue
            word = parts[0].strip().lower()
            ipa = parts[1].strip() if len(parts) > 1 else ""
            sampa = parts[2].strip() if len(parts) > 2 else ""
            if word and word not in lookup:
                lookup[word] = (ipa, sampa)
    return lookup


def load_hyphenation_lookup(path=HYPHENATION_TXT):
    """word (lowercase, hyphens stripped) -> hyphenated form. Empty dict if not staged."""
    lookup = {}
    if not os.path.exists(path):
        return lookup
    with open(path, encoding="utf-8") as f:
        for line in f:
            hyphenated = line.strip()
            if not hyphenated:
                continue
            plain = hyphenated.replace("-", "").lower()
            if plain and plain not in lookup:
                lookup[plain] = hyphenated
    return lookup
