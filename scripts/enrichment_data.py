"""Optional pronunciation/hyphenation lookups from CLARIN-IS datasets.

Both sources are CC BY licensed (unlike the CC BY-NC-ND INO data) and are
staged locally via scripts/fetch_supplementary_data.sh. If a dataset hasn't
been fetched, the corresponding loader returns an empty dict and the build
proceeds without that enrichment.
"""
import os
import re

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
PRONUNCIATION_TSV = os.path.join(DATA_DIR, "pronunciation", "pronunciation.tsv")
HYPHENATION_TXT = os.path.join(DATA_DIR, "hyphenation", "hyph_is_list.txt")
SYNONYMS_TXT = os.path.join(DATA_DIR, "synonyms", "core-isl.txt")

_SYNSET_LINE_RE = re.compile(r"^\w+\s+\[[^\]]*\]\s+\[([^\]]*)\]\s*(.*)$")


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


def load_synonyms_lookup(path=SYNONYMS_TXT):
    """word (lowercase) -> sorted list of synonyms drawn from the same IceWordNet
    synset (translation headword + its listed synonyms), unioned across every
    line/sense the word appears in. Empty dict if dataset not staged.

    Each source line looks like:
        a [able%5:00:00:capable:00] [fær] hæfileikamikill
    i.e. <pos> [<wordnet sense key>] [<icelandic translation>] <comma-separated synonyms>
    The file is ISO-8859-1 encoded with CRLF line endings.
    """
    synsets = {}
    if not os.path.exists(path):
        return synsets
    with open(path, encoding="iso-8859-1") as f:
        for line in f:
            match = _SYNSET_LINE_RE.match(line.strip())
            if not match:
                continue
            translation, rest = match.groups()
            words = [translation.strip()]
            words += [w.strip() for w in rest.split(",")]
            # Drop multi-word entries — these are stray English glosses left in
            # place of a missing Icelandic synonym (e.g. "concerned with concrete
            # problems or data"), not real synonyms.
            words = [w.lower() for w in words if w and " " not in w]
            unique_words = sorted(set(words))
            if len(unique_words) < 2:
                continue
            for word in unique_words:
                bucket = synsets.setdefault(word, set())
                bucket.update(w for w in unique_words if w != word)

    return {word: sorted(others) for word, others in synsets.items()}
