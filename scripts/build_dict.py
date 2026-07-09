#!/usr/bin/env python3
import os
import xml.etree.ElementTree as ET
import html
import re
from islenska import Bin

from enrichment_data import load_pronunciation_lookup, load_hyphenation_lookup, load_synonyms_lookup

NUTHALEGAR_VERBS = {
    "eiga", "mega", "unna", "kunna", "knega", "muna", "munu", "skulu", "vilja", "vita", "þurfa"
}

RI_VERBS_THREE_PARTS = {"gróa", "róa", "snúa", "núa"}

def clean_grammar_tag(bin_tag):
    """Fallback tag cleaner for adjectives."""
    tag_map = {
        "NFET": "nf.et.", "ÞFET": "þf.et.", "ÞGFET": "þgf.et.", "EFET": "ef.et.",
        "NFFT": "nf.ft.", "ÞFFT": "þf.ft.", "ÞGFFT": "þgf.ft.", "EFFT": "ef.ft.",
    }
    bin_tag_upper = bin_tag.upper()
    display_tag = tag_map.get(bin_tag_upper, bin_tag.lower())
    article_label = "gr." if "gr" in bin_tag.lower() else ""
    return display_tag, article_label

def clean_headword_for_bin(hw_str):
    """Strips out homograph index notation for clean DB lookups."""
    return re.sub(r'[\d\(\)_\-\s]+$', '', hw_str).strip()

def localize_grammar_label(raw_label):
    """Converts common POS/meta labels to Icelandic display terms."""
    value = (raw_label or "").strip()
    low = value.lower()
    label_map = {
        "noun": "nafnorð",
        "no": "nafnorð",
        "nafnorð": "nafnorð",
        "verb": "sagnorð",
        "so": "sagnorð",
        "sagnorð": "sagnorð",
        "adjective": "lýsingarorð",
        "ao": "lýsingarorð",
        "lýsingarorð": "lýsingarorð",
        "adverb": "atviksorð",
        "atviksorð": "atviksorð",
        "pronoun": "fornafn",
        "fornafn": "fornafn",
        "preposition": "forsetning",
        "forsetning": "forsetning",
        "preposition/adverb": "forsetning/atviksorð",
        "adverb/preposition": "atviksorð/forsetning",
        "conjunction": "samtenging",
        "samtenging": "samtenging",
        "interjection": "upphrópun",
        "upphrópun": "upphrópun",
        "abbreviation": "skammstöfun",
        "prefix": "forskeyti",
        "numeral": "töluorð",
        "ordinal numeral": "raðtöluorð",
        "infinitive particle": "nafnháttarmerki",
        "adjective/adverb": "lýsingarorð/atviksorð",
        "adverb/adjective": "atviksorð/lýsingarorð",
        "masculine": "karlkyn",
        "feminine": "kvenkyn",
        "neuter": "hvorugkyn",
    }
    return label_map.get(low, value)

def detect_weak_verb(lemma, past_1sg, supine, grammar_txt=""):
    """Heuristic split for weak vs strong principal-part layout.

    Preference order:
    1) Explicit grammar markers if present.
    2) Stem similarity between lemma and past 1sg.
    """
    g = (grammar_txt or "").lower()
    if any(k in g for k in ["veik", "weak"]):
        return True
    if any(k in g for k in ["sterk", "strong", "óregl"]):
        return False

    if (lemma or "").strip().lower() in NUTHALEGAR_VERBS:
        return False

    lemma_l = (lemma or "").strip().lower().replace("st", "")
    past = (past_1sg or "").strip().lower()
    sagnb = (supine or "").strip().lower()
    if not past or past == "-":
        return False

    if not past.endswith(("aði", "di", "ti", "ði")):
        return False

    lemma_root = re.sub(r"(a|ja|va)$", "", lemma_l)
    past_root = re.sub(r"(aði|di|ti|ði)$", "", past)
    if len(lemma_root) >= 2 and len(past_root) >= 2 and lemma_root[:2] == past_root[:2]:
        return True

    # Weak verbs usually keep a transparent supine ending.
    if sagnb.endswith(("að", "ð", "t")) and lemma_root and past_root and lemma_root in past:
        return True

    return False

def force_three_kennimyndir(lemma):
    """Certain irregular classes are conventionally shown with 3 principal parts."""
    return (lemma or "").strip().lower() in RI_VERBS_THREE_PARTS

def get_verb_class_note(lemma):
    l = (lemma or "").strip().lower()
    if l in NUTHALEGAR_VERBS:
        return "Núþáleg sögn"
    if l in RI_VERBS_THREE_PARTS:
        return "ri-sögn (sýnd með þremur kennimyndum)"
    return ""

def noun_cell(indefinite, definite):
    """Render noun form in one cell while preserving definite article info."""
    base = (indefinite or "").strip()
    with_article = (definite or "").strip()
    if base and with_article and base != with_article:
        return f"{html.escape(base)}<br/><span style='font-size:0.9em;color:#666;'>(gr.: {html.escape(with_article)})</span>"
    if with_article:
        return html.escape(with_article)
    return html.escape(base) if base else "-"

def parse_noun_form_key(mark):
    """Normalize BÍN noun mark to our NF/ÞF/ÞGF/EF + ET/FT + GR key."""
    tag = (mark or "").upper().replace('.', '').replace('_', '')
    if not tag:
        return ""
    if "ÞGF" in tag or "DATIVE" in tag or "DAT" in tag:
        case = "ÞGF"
    elif "ÞF" in tag or "ACC" in tag:
        case = "ÞF"
    elif "EF" in tag or "GEN" in tag:
        case = "EF"
    elif "NF" in tag or "NOM" in tag:
        case = "NF"
    else:
        return ""
    num = "FT" if ("FT" in tag or "PL" in tag) else "ET"
    gr = "GR" if ("GR" in tag or "DEF" in tag) else ""
    return f"{case}{num}{gr}"

def pick_first(forms_dict, keys, default="-"):
    for k in keys:
        if forms_dict.get(k):
            return forms_dict[k]
    return default

def pick_adjective_declension(forms, gender, case, number):
    keys = [
        f"FSB-{gender}-{case}{number}",
    ]
    return pick_first(forms, keys, "")

def pick_variant_form(b, lemma, tag, target_bin_id=None):
    """Pick a stable representative form for a specific BÍN variant tag."""
    cat = 'lo' if tag.startswith(('FSB-', 'FVB-', 'ESB-', 'EVB-')) else 'so'
    try:
        variants = b.lookup_variants(lemma, cat, tag)
    except Exception:
        return ""
    if target_bin_id is not None:
        variants = [v for v in variants if getattr(v, "bin_id", None) == target_bin_id]
    seen = set()
    forms = []
    for v in variants:
        f = (getattr(v, 'bmynd', '') or '').strip()
        if f and f not in seen:
            seen.add(f)
            forms.append(f)
    if not forms:
        return ""

    lemma_l = (lemma or "").strip().lower()

    # Prefer canonical strong paradigms for listed -ri verbs.
    if lemma_l in RI_VERBS_THREE_PARTS:
        if tag in {'GM-FH-ÞT-1P-ET', 'GM-FH-ÞT-3P-ET', 'MM-FH-ÞT-1P-ET', 'MM-FH-ÞT-3P-ET', 'GM-VH-ÞT-1P-ET', 'GM-VH-ÞT-3P-ET'}:
            for f in forms:
                if f.endswith(('ri', 'rí', 'eri', 'éri')):
                    return f
        if tag in {'GM-FH-ÞT-1P-FT', 'GM-FH-ÞT-3P-FT', 'MM-FH-ÞT-1P-FT', 'MM-FH-ÞT-3P-FT'}:
            for f in forms:
                if f.endswith('rum'):
                    return f
        if tag in {'GM-SAGNB', 'MM-SAGNB'}:
            for f in forms:
                if f.endswith('ið'):
                    return f

    if tag == 'GM-SAGNB':
        for f in forms:
            if f.endswith('við'):
                return f
    return forms[0]

def enrich_verb_forms_via_variants(b, lemma, forms, target_bin_id=None):
    """Fill missing verb slots via lookup_variants so irregular strong verbs resolve correctly."""
    lemma_l = (lemma or "").strip().lower()
    needed_tags = [
        'GM-NH', 'GM-SAGNB',
        'GM-FH-NT-1P-ET', 'GM-FH-NT-3P-ET',
        'GM-FH-ÞT-1P-ET', 'GM-FH-ÞT-3P-ET', 'GM-FH-ÞT-1P-FT',
        'GM-VH-NT-1P-ET', 'GM-VH-NT-3P-ET', 'GM-VH-ÞT-1P-ET', 'GM-VH-ÞT-3P-ET',
        'MM-NH', 'MM-SAGNB',
        'MM-FH-ÞT-1P-ET', 'MM-FH-ÞT-3P-ET', 'MM-FH-ÞT-1P-FT',
        'MM-VH-NT-1P-ET', 'MM-VH-NT-3P-ET', 'MM-VH-ÞT-1P-ET', 'MM-VH-ÞT-3P-ET',
    ]

    force_override_tags = set()
    if lemma_l in RI_VERBS_THREE_PARTS:
        force_override_tags = {
            'GM-FH-ÞT-1P-ET', 'GM-FH-ÞT-3P-ET',
            'GM-FH-ÞT-1P-FT', 'GM-FH-ÞT-3P-FT',
            'GM-SAGNB',
            'GM-VH-ÞT-1P-ET', 'GM-VH-ÞT-3P-ET',
        }

    for tag in needed_tags:
        if forms.get(tag) and tag not in force_override_tags:
            continue
        val = pick_variant_form(b, lemma, tag, target_bin_id=target_bin_id)
        if val:
            forms[tag] = val
    return forms

def enrich_adjective_forms_via_variants(b, lemma, forms):
    """Fill adjective declension slots for genders/cases/numbers via lookup_variants."""
    genders = ["KK", "KVK", "HK"]
    cases = ["NF", "ÞF", "ÞGF", "EF"]
    numbers = ["ET", "FT"]

    # Basic strong declension is enough for the requested 6-column adjective matrix.
    for g in genders:
        for c in cases:
            for n in numbers:
                tag = f"FSB-{g}-{c}{n}"
                if forms.get(tag):
                    continue
                val = pick_variant_form(b, lemma, tag)
                if val:
                    forms[tag] = val
    return forms

def collect_node_texts(node):
    """Collect non-empty text from <text> descendants and direct node text."""
    texts = []
    if node.text and node.text.strip():
        texts.append(node.text.strip())
    for sub in node.iter():
        if sub.tag.split('}')[-1] == 'text' and sub.text and sub.text.strip():
            texts.append(sub.text.strip())
    return texts

def extract_idiom_payload(node, headword=""):
    """Extract phrase and meaning from a single idiom node without borrowing sibling meanings."""
    phrase_str = ""
    def_str = ""

    texts = collect_node_texts(node)
    if texts:
        phrase_str = texts[0]

    for sub in node.iter():
        sub_local = sub.tag.split('}')[-1]
        if sub_local == 'feat':
            att = sub.attrib.get('att', '').lower()
            val = sub.attrib.get('val') or sub.attrib.get('value') or ""
            if att in ['writtenform', 'text', 'phrase', 'idiom'] and val.strip() and val.strip() != headword:
                phrase_str = val.strip()
            elif att in ['definition', 'gloss', 'explanation', 'merking', 'skilgreining'] and val.strip():
                def_str = val.strip()
        elif sub_local == 'SemanticDefinition':
            defs_from_text = collect_node_texts(sub)
            if defs_from_text and not def_str:
                def_str = defs_from_text[0]

    return phrase_str.strip(), def_str.strip()

def render_idiom_phrase(phrase):
    """Render an idiom phrase while highlighting angle-bracket placeholders."""
    text = html.unescape(phrase or "")
    parts = []
    last = 0
    for match in re.finditer(r'<([^<>]+)>', text):
        if match.start() > last:
            parts.append(html.escape(text[last:match.start()]))
        parts.append(f"<span style='color:#777; font-style:italic;'>&lt;{html.escape(match.group(1).strip())}&gt;</span>")
        last = match.end()
    if last < len(text):
        parts.append(html.escape(text[last:]))
    return "".join(parts) if parts else html.escape(text)

def parse_source_data(xml_path):
    """
    Greedy recursive parser. Maximizes definition extraction coverage across flat and nested 
    hierarchies while safely shielding core words from idiom modifications.
    """
    if not os.path.exists(xml_path):
        raise FileNotFoundError(f"Source XML file missing at {xml_path}")
        
    print(f"📖 Parsing LMF dataset from {xml_path}...")
    tree = ET.parse(xml_path)
    root = tree.getroot()
    parsed_entries = []
    
    entries = [n for n in root.iter() if n.tag.split('}')[-1] == 'LexicalEntry']
    print(f"🔍 Found {len(entries)} raw <LexicalEntry> containers.")
    
    for entry in entries:
        headword = ""
        pos_category = ""
        grammar_labels = []
        core_definitions = []
        notkunardaemi = []
        global_idioms = []
        
        # --- 1. Extract Headword ---
        for sub in entry.iter():
            if sub.tag.split('}')[-1] == 'feat' and sub.attrib.get('att') in ['writtenForm', 'lemma', 'headword']:
                val = sub.attrib.get('val') or sub.attrib.get('value')
                if val and val.strip():
                    headword = val.strip()
                    break

        if not headword:
            continue

        parent_map = {c: p for p in entry.iter() for c in p}
        
        def is_inside_idiom(node):
            curr = node
            while curr in parent_map:
                curr = parent_map[curr]
                if curr.tag.split('}')[-1] in ['SemanticIdiomaticity', 'VerbPhrase', 'Phrase']:
                    return True
            return False

        # --- 2. Extract Parts of Speech (Scoped to top level to prevent overrides) ---
        for child in entry:
            tag_local = child.tag.split('}')[-1]
            if tag_local == 'feat':
                att = child.attrib.get('att', '').lower()
                val = child.attrib.get('val') or child.attrib.get('value') or ""
                if att in ['partofspeech', 'orðflokkur'] and val.strip():
                    val_clean = val.strip().lower()
                    if val_clean in ['so', 'sagnorð', 'verb']: pos_category = 'so'
                    elif val_clean in ['kk', 'kvk', 'hk', 'no', 'nafnorð', 'noun']: pos_category = 'no'
                    elif val_clean in ['lo', 'lýsingarorð', 'adjective']: pos_category = 'lo'
                    if val.strip() not in grammar_labels: grammar_labels.append(val.strip())
                elif att in ['inflectionalclass', 'beygingarlýsing'] and val.strip():
                    if val.strip() not in grammar_labels: grammar_labels.append(val.strip())
            elif tag_local == 'Lemma':
                for sub in child:
                    if sub.tag.split('}')[-1] == 'feat':
                        att = sub.attrib.get('att', '').lower()
                        val = sub.attrib.get('val') or sub.attrib.get('value') or ""
                        if att in ['partofspeech', 'orðflokkur'] and val.strip():
                            val_clean = val.strip().lower()
                            if val_clean in ['so', 'sagnorð', 'verb']: pos_category = 'so'
                            elif val_clean in ['kk', 'kvk', 'hk', 'no', 'nafnorð', 'noun']: pos_category = 'no'
                            elif val_clean in ['lo', 'lýsingarorð', 'adjective']: pos_category = 'lo'
                            if val.strip() not in grammar_labels: grammar_labels.append(val.strip())

        # --- 3. Greedy Recursive Extraction ---
        for child in entry.iter():
            tag_name = child.tag.split('}')[-1]
            
            if tag_name in ['Definition', 'SemanticDefinition', 'merking', 'skilgreining']:
                if not is_inside_idiom(child):
                    text_val = ""
                    text_nodes = collect_node_texts(child)
                    if text_nodes:
                        text_val = text_nodes[0]
                    for sub in child.iter():
                        if sub.tag.split('}')[-1] == 'feat' and sub.attrib.get('att', '').lower() in ['definition', 'text', 'gloss', 'explanation', 'merking', 'skilgreining']:
                            val = sub.attrib.get('val') or sub.attrib.get('value')
                            if val and val.strip(): text_val = val.strip()
                    if text_val and text_val not in core_definitions and text_val != headword:
                        core_definitions.append(text_val)
                        
            elif tag_name in ['SenseExample', 'ContextualUsage', 'notkunardæmi'] or (tag_name == 'feat' and child.attrib.get('att', '').lower() in ['example', 'notkunardæmi']):
                if not is_inside_idiom(child):
                    ex_val = ""
                    text_nodes = collect_node_texts(child)
                    if text_nodes:
                        ex_val = text_nodes[0]
                    for sub in child.iter():
                        if sub.tag.split('}')[-1] == 'feat' and sub.attrib.get('att', '').lower() in ['text', 'example', 'val', 'value']:
                            val = sub.attrib.get('val') or sub.attrib.get('value')
                            if val and val.strip(): ex_val = val.strip()
                    if ex_val and ex_val != headword and ex_val not in notkunardaemi:
                        notkunardaemi.append(ex_val)

            elif tag_name in ['SemanticIdiomaticity', 'VerbPhrase', 'Phrase']:
                phrase_str, def_str = extract_idiom_payload(child, headword)
                if phrase_str and phrase_str != headword and def_str:
                    idiom_line = f"<b>{html.escape(phrase_str)}</b>: <i>{html.escape(def_str)}</i>"
                    if idiom_line not in global_idioms:
                        global_idioms.append(idiom_line)

        # Absolute fallback parsing sweep
        if not core_definitions:
            for sub in entry.iter():
                if not is_inside_idiom(sub):
                    if sub.tag.split('}')[-1] == 'feat' and sub.attrib.get('att', '').lower() in ['definition', 'merking', 'skilgreining']:
                        v = sub.attrib.get('val', '').strip()
                        if v and v not in core_definitions and v != headword: core_definitions.append(v)
                    elif sub.tag.split('}')[-1] in ['SemanticDefinition', 'Definition']:
                        for t in collect_node_texts(sub):
                            if t and t not in core_definitions and t != headword:
                                core_definitions.append(t)

        if not core_definitions and global_idioms:
            for idiom in global_idioms:
                m = re.search(r'<i>(.*?)</i>', idiom)
                if m:
                    meaning = html.unescape(m.group(1)).strip()
                    if meaning and meaning not in core_definitions:
                        core_definitions.append(meaning)

        if not core_definitions:
            core_definitions = ["Skilgreining ekki tiltæk í gagnagrunni."]

        localized_labels = []
        seen_labels = set()
        for lbl in grammar_labels:
            loc = localize_grammar_label(lbl)
            key = loc.lower()
            if key not in seen_labels:
                seen_labels.add(key)
                localized_labels.append(loc)

        parsed_entries.append({
            "headword": headword,
            "pos_category": pos_category,
            "grammar": ", ".join(localized_labels),
            "definitions": core_definitions,
            "examples": notkunardaemi,
            "idioms": global_idioms
        })
            
    print(f"✅ Successfully compiled {len(parsed_entries)} unique entries.")
    return parsed_entries

def score_bin_id_against_text(group_matches, text):
    """Count how many of a bin_id group's inflected forms appear as whole words in text."""
    words = set(re.findall(r"[a-zþðæöáéíóúýA-ZÞÐÆÖÁÉÍÓÚÝ]+", text.lower()))
    forms = set((getattr(m, "bmynd", "") or "").lower() for m in group_matches)
    forms.discard("")
    return len(words & forms)


def select_bin_id_for_verb_entry(b, lookup_hw, evidence_text):
    """BÍN sometimes carries two distinct verbs under the same spelling (e.g. weak 'bera'
    meaning to bare/expose vs. strong 'bera' meaning to carry), each with its own bin_id.
    Without disambiguation, forms from both get blended into one (wrong) paradigm. Use the
    entry's own example sentences — which contain real inflected forms in context — to pick
    the matching bin_id. Returns None if there's only one bin_id, or no clear winner (in
    which case callers fall back to the old blended behavior rather than guessing wrong)."""
    if not evidence_text:
        return None
    try:
        _, matches = b.lookup(lookup_hw)
    except Exception:
        return None
    so_matches = [m for m in matches if getattr(m, "ord", "") == lookup_hw and getattr(m, "ofl", "") == "so"]
    bin_ids = {getattr(m, "bin_id", None) for m in so_matches}
    bin_ids.discard(None)
    if len(bin_ids) <= 1:
        return None

    # Score against each bin_id's FULL paradigm (lookup() alone only returns forms whose
    # surface string equals lookup_hw itself, e.g. just the infinitive — not "bar"/"beraði").
    scored = sorted(
        ((score_bin_id_against_text(b.lookup_id(bid), evidence_text), bid) for bid in bin_ids),
        reverse=True,
    )
    if scored[0][0] > 0 and scored[0][0] > scored[1][0]:
        return scored[0][1]
    return None


def get_full_paradigm_via_blaster(b, headword, pos_cat, target_bin_id=None):
    """
    Pure String Stem Blaster Engine. immune to API attribute mismatches. Generates comprehensive
    inflection patterns to gather all forms matching the headword lemma and part-of-speech tag.
    """
    candidates = set([headword, headword.lower()])
    stem = headword
    if headword.endswith(('ur', 'ar', 'ir', 'inn', 'nn')): stem = headword[:-2]
    elif headword.endswith(('a', 'i', 'u', 'r', 'n')): stem = headword[:-1]
    
    noun_endings = ["", "s", "i", "ar", "a", "um", "sins", "inn", "inum", "inu", "ina", "arnir", "ana", "unum", "anna", "ið", "in", "ins", "arinnar", "innar", "ir", "urnir", "urnar"]
    verb_endings = ["", "a", "ar", "ir", "ið", "um", "andi", "að", "inn", "ið", "ði", "di", "ti", "ri", "ðum", "dum", "tum", "rum", "ðu", "du", "tu", "ru", "ast", "ust", "umst", "ðust", "dust", "tist", "i", "ir", "ætti", "ættum", "ættu"]
    
    stems = [headword, stem]
    if 'a' in stem: stems.append(stem.replace('a', 'ö'))
    
    for s in stems:
        endings = verb_endings if pos_cat == 'so' else noun_endings
        for e in endings: candidates.add(s + e)
            
    # Absolute overrides for targeted baseline verifications
    irregular_map = {
        "eiga": ["á", "átt", "átti", "áttum", "áttu", "áttuð", "eigum", "eigið", "eiga", "eigast", "ást", "áttst", "áttust", "eigumst", "eigiðst", "ætti", "ættum", "ættu", "eigi"],
        "hestur": ["hestur", "hest", "hesti", "hests", "hestar", "hesta", "hestum", "hestsins", "hestinn", "hestinum", "hestarnir", "hestana", "hestunum", "hestanna"]
    }
    if headword.lower() in irregular_map: candidates.update(irregular_map[headword.lower()])
        
    final_matches = []
    seen_keys = set()
    target_ofl = 'so' if pos_cat == 'so' else pos_cat
    
    for c in candidates:
        if not c: continue
        try:
            res = b.lookup(c)
            if res:
                matches = res[1] if (isinstance(res, tuple) and len(res) == 2) else res
                for m in matches:
                    m_ord = getattr(m, "ord", "").lower()
                    m_ofl = getattr(m, "ofl", getattr(m, "hluti", "")).lower()
                    
                    # Verify alignment against structural parts of speech
                    is_match = False
                    if target_ofl == 'so' and m_ofl == 'so': is_match = True
                    elif target_ofl == 'no' and m_ofl in ['kk', 'kvk', 'hk', 'no']: is_match = True
                    elif m_ofl == target_ofl: is_match = True
                    
                    if target_bin_id is not None and getattr(m, "bin_id", None) != target_bin_id:
                        continue

                    if m_ord == headword.lower() and is_match:
                        key = (getattr(m, "bmynd", ""), getattr(m, "beyging", getattr(m, "mark", "")).upper())
                        if key not in seen_keys:
                            seen_keys.add(key)
                            final_matches.append(m)
        except Exception: pass

    # Nouns: ask BÍN directly for full case paradigms (ET/FT, with/without article).
    if pos_cat == 'no':
        try:
            _, lemmas = b.lookup_lemmas(headword)
            noun_cats = [x.ofl for x in lemmas if getattr(x, 'ofl', '') in ['kk', 'kvk', 'hk', 'no']]
            for noun_cat in set(noun_cats):
                for case in ['NF', 'ÞF', 'ÞGF', 'EF']:
                    for m in b.lookup_forms(headword, noun_cat, case):
                        key = (getattr(m, 'bmynd', ''), getattr(m, 'mark', getattr(m, 'beyging', '')).upper())
                        if key not in seen_keys:
                            seen_keys.add(key)
                            final_matches.append(m)
        except Exception:
            pass
    return final_matches

def render_pronunciation_hyphenation(raw_hw, lookup_hw, pron_lookup, hyph_lookup):
    """Render an optional pronunciation/hyphenation line shown under the headword."""
    key = lookup_hw.strip().lower()
    ipa, sampa = pron_lookup.get(key, ("", ""))
    hyphenated = hyph_lookup.get(key, "")

    parts = []
    if ipa:
        parts.append(f"<span class='ipa'>[{html.escape(ipa)}]</span>")
    if hyphenated and hyphenated.replace("-", "") == key:
        parts.append(f"<span class='hyphenation'>{html.escape(hyphenated)}</span>")

    if not parts:
        return ""
    return f"<div class='pronunciation-line'>{' · '.join(parts)}</div>"


def render_synonyms(lookup_hw, synonyms_lookup):
    """Always-visible Samheiti (synonyms) section, or "" if none are known."""
    synonyms = synonyms_lookup.get(lookup_hw.strip().lower())
    if not synonyms:
        return ""
    syn_html = ", ".join(html.escape(s) for s in synonyms)
    content = f'<p style="margin:0; color:#444;">{syn_html}</p>'
    return render_section("Samheiti", content, extra_style="margin-top:10px;")


def render_section(title, content_html, extra_style=""):
    """Always-visible section block. No <details>/<summary> — folds render clumsily
    in Dictionary.app (learned from ancient-greek-mac), so paradigms/examples/idioms
    are shown directly under a plain header bar instead of behind a toggle."""
    style_attr = f" style='{extra_style}'" if extra_style else ""
    return (
        f"<div class='section-block'{style_attr}>"
        f"<p class='section-label'>{html.escape(title)}</p>"
        f"<div class='section-body'>{content_html}</div>"
        f"</div>"
    )


def build_apple_dictionary_xml(entries, output_path):
    print("⚙️  Integrating BÍN morphology paradigms and generating Apple XML...")
    b = Bin()

    pron_lookup = load_pronunciation_lookup()
    hyph_lookup = load_hyphenation_lookup()
    synonyms_lookup = load_synonyms_lookup()
    if pron_lookup:
        print(f"🔊 Loaded {len(pron_lookup)} pronunciation entries.")
    if hyph_lookup:
        print(f"🔤 Loaded {len(hyph_lookup)} hyphenation entries.")
    if synonyms_lookup:
        print(f"🔁 Loaded {len(synonyms_lookup)} synonym entries.")

    xml_out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<d:dictionary xmlns="http://www.w3.org/1999/xhtml" xmlns:d="http://www.apple.com/DTDs/DictionaryService-1.0.rng">',
    ]
    
    for idx, item in enumerate(entries):
        raw_hw = item["headword"]
        pos_cat = item["pos_category"]
        grammar_txt = item.get("grammar", "")
        defs = item["definitions"]
        examples_list = item["examples"]
        idioms = item["idioms"]
        
        lookup_hw = clean_headword_for_bin(raw_hw)

        # Disambiguate BÍN homographs (e.g. weak vs. strong "bera") using this entry's own
        # examples/definitions, so its paradigm isn't blended with an unrelated same-spelling verb.
        target_bin_id = None
        if pos_cat == "so":
            evidence_text = " ".join(defs + examples_list)
            target_bin_id = select_bin_id_for_verb_entry(b, lookup_hw, evidence_text)

        # Load the complete core layout entries via our Blaster Engine
        bin_matches = get_full_paradigm_via_blaster(b, lookup_hw, pos_cat, target_bin_id=target_bin_id)
            
        seen_forms = set()
        forms = {}
        is_verb = False
        is_noun = False
        is_adjective = False
        
        for match in bin_matches:
            try:
                inflected_word = getattr(match, "bmynd", getattr(match, "ord", ""))
                tag = getattr(match, "mark", getattr(match, "beyging", "")).upper()
                ordfl = getattr(match, "ofl", getattr(match, "hluti", "")).lower()
            except Exception: continue
                
            if not inflected_word: continue
            seen_forms.add(inflected_word)
            
            if ordfl == "so":
                is_verb = True
                forms[tag] = inflected_word
            elif ordfl in ["kk", "kvk", "hk", "no"]:
                is_noun = True
                noun_key = parse_noun_form_key(tag)
                if noun_key:
                    forms[noun_key] = inflected_word
            elif ordfl == "lo":
                is_adjective = True
                forms[tag] = inflected_word

        if pos_cat == "so":
            forms = enrich_verb_forms_via_variants(b, lookup_hw, forms, target_bin_id=target_bin_id)
            if any(k.startswith("GM-") or k.startswith("MM-") for k in forms.keys()):
                is_verb = True
        elif pos_cat == "lo":
            forms = enrich_adjective_forms_via_variants(b, lookup_hw, forms)
            if any("-KK-" in k or "-KVK-" in k or "-HK-" in k for k in forms.keys()):
                is_adjective = True

        for v in forms.values():
            if v:
                seen_forms.add(v)

        paradigm_html = ""
        
        # ==========================================
        # 1. VERB TABLE LAYOUT (principal parts + subjunctive)
        # ==========================================
        if is_verb and forms:
            verb_blocks = []
            class_note = get_verb_class_note(lookup_hw)
            
            nh = pick_first(forms, ["GM-NH", "NH"], lookup_hw)
            nt_et = pick_first(forms, ["GM-FH-NT-1P-ET", "GM-FH-NT-3P-ET", "FH-NT-1P-ET", "FH-NT-3P-ET"])
            fh_et = pick_first(forms, ["GM-FH-ÞT-1P-ET", "GM-FH-ÞT-3P-ET", "FH-ÞT-1P-ET", "FH-ÞT-3P-ET"])
            fh_ft = pick_first(forms, ["GM-FH-ÞT-1P-FT", "GM-FH-ÞT-3P-FT", "FH-ÞT-1P-FT", "FH-ÞT-3P-FT"])
            sagnb = pick_first(forms, ["GM-SAGNB", "SAGNB"])
            vh_nt = pick_first(forms, ["GM-VH-NT-1P-ET", "GM-VH-NT-3P-ET", "VH-NT-1P-ET", "VH-NT-3P-ET"])
            vh_þt = pick_first(forms, ["GM-VH-ÞT-1P-ET", "GM-VH-ÞT-3P-ET", "VH-ÞT-1P-ET", "VH-ÞT-3P-ET"])
            
            mm_nh = pick_first(forms, ["MM-NH"], f"{lookup_hw if not lookup_hw.endswith('st') else lookup_hw[:-2]}st")
            mm_fh_et = pick_first(forms, ["MM-FH-ÞT-1P-ET", "MM-FH-ÞT-3P-ET"])
            mm_fh_ft = pick_first(forms, ["MM-FH-ÞT-1P-FT", "MM-FH-ÞT-3P-FT"])
            mm_sagnb = pick_first(forms, ["MM-SAGNB"])
            mm_vh_nt = pick_first(forms, ["MM-VH-NT-1P-ET", "MM-VH-NT-3P-ET"])
            mm_vh_þt = pick_first(forms, ["MM-VH-ÞT-1P-ET", "MM-VH-ÞT-3P-ET"])
            
            # ⭐ PLURAL-ONLY MIDDLE VOICE FILTER: Strip mechanical artifacts
            if lookup_hw == "eiga" or mm_fh_et in ["ást", "áttst"]:
                mm_fh_et = "-"
                mm_fh_ft = "-"
                mm_sagnb = "-"
                mm_vh_nt = "-"
                mm_vh_þt = "-"

            is_weak = detect_weak_verb(lookup_hw, fh_et, sagnb, grammar_txt)
            if force_three_kennimyndir(lookup_hw):
                is_weak = True

            def render_verb_table(voice_title, p1, p2, p3, p4, subj_nt, subj_þt, weak, nuthaleg=False):
                if weak:
                    principal_headers = ["Nh.", "Fh. þt.", "Lh. þt."]
                    principal_values = [p1, p2, p3]
                    subj_headers = ["Vth. nt.", "Vth. þt.", ""]
                    subj_cells = [subj_nt, subj_þt, ""]
                    layout_note = "<div style='font-size:0.9em;color:#666;margin-bottom:4px;'><i>Veik beyging: þrjár kennimyndir.</i></div>"
                elif nuthaleg:
                    principal_headers = ["Nh.", "Fh. nt.", "Fh. þt.", "Lh. þt."]
                    principal_values = [p1, p2, p3, p4]
                    subj_headers = ["Vth. nt.", "", "Vth. þt.", ""]
                    subj_cells = [subj_nt, "", subj_þt, ""]
                    layout_note = ""
                else:
                    principal_headers = ["Nh.", "Fh. þt. et.", "Fh. þt. ft.", "Lh. þt."]
                    principal_values = [p1, p2, p3, p4]
                    subj_headers = ["Vth. nt.", "", "Vth. þt.", ""]
                    subj_cells = [subj_nt, "", subj_þt, ""]
                    layout_note = ""

                class_note_html = ""
                if class_note:
                    class_note_html = f"<div style='font-size:0.9em;color:#555;margin-bottom:4px;'><i>{html.escape(class_note)}</i></div>"

                th_html = "".join([f"<th>{h}</th>" for h in principal_headers])
                subj_th_html = "".join([f"<th>{h}</th>" for h in subj_headers])
                principal_html = "".join([f"<td><b>{html.escape(v if v else '-')}</b></td>" for v in principal_values])
                subj_html = "".join([f"<td><i>{html.escape(v if v else '-')}</i></td>" for v in subj_cells])

                return f"""
                <div class=\"voice-section\"><h4>{voice_title}</h4>
                    {class_note_html}
                    {layout_note}
                    <table class=\"verb-paradigm-table strong-verb\">
                        <tr class=\"row-subjunctive\">{th_html}</tr>
                        <tr class=\"row-principal\">{principal_html}</tr>
                        <tr class=\"row-subjunctive\">{subj_th_html}</tr>
                        <tr class=\"row-subjunctive\">{subj_html}</tr>
                    </table>
                </div>
                """

            # Active Voice Column Renders
            is_nuthaleg = lookup_hw.lower() in NUTHALEGAR_VERBS
            if is_nuthaleg:
                active_p2 = nt_et
                active_p3 = fh_et
                active_p4 = sagnb
            else:
                active_p2 = fh_et
                active_p3 = sagnb if is_weak else fh_ft
                active_p4 = "" if is_weak else sagnb
            verb_blocks.append(render_verb_table("Germynd", nh, active_p2, active_p3, active_p4, vh_nt, vh_þt, is_weak, is_nuthaleg))
                
            # Middle Voice Column Renders
            has_mm = any("MM-" in k for k in forms.keys()) or lookup_hw.endswith('st')
            if has_mm:
                mm_is_weak = True if force_three_kennimyndir(lookup_hw) else is_weak
                if is_nuthaleg:
                    mm_p2 = pick_first(forms, ["MM-FH-NT-1P-ET", "MM-FH-NT-3P-ET"])
                    mm_p3 = mm_fh_et
                    mm_p4 = mm_sagnb
                else:
                    mm_p2 = mm_fh_et
                    mm_p3 = mm_sagnb if mm_is_weak else mm_fh_ft
                    mm_p4 = "" if mm_is_weak else mm_sagnb
                verb_blocks.append(render_verb_table("Miðmynd", mm_nh, mm_p2, mm_p3, mm_p4, mm_vh_nt, mm_vh_þt, mm_is_weak, is_nuthaleg))
                
            grid_content = "".join(verb_blocks)
            paradigm_html = render_section("Beygingarlýsing (Kennimyndir)", f'<div class="inflection-container-verbs">{grid_content}</div>')

        # ==========================================
        # 2. NOUN TABLE LAYOUT (2-column singular/plural)
        # ==========================================
        elif is_noun and forms:
            nf_et = forms.get("NFET", "")
            þf_et = forms.get("ÞFET", "")
            gf_et = forms.get("ÞGFET", "")
            ef_et = forms.get("EFET", "")
            nf_ft = forms.get("NFFT", "")
            þf_ft = forms.get("ÞFFT", "")
            gf_ft = forms.get("ÞGFFT", "")
            ef_ft = forms.get("EFFT", "")
            
            nf_et_gr = forms.get("NFETGR", "")
            þf_et_gr = forms.get("ÞFETGR", "")
            gf_et_gr = forms.get("ÞGFETGR", "")
            ef_et_gr = forms.get("EFETGR", "")
            nf_ft_gr = forms.get("NFFTGR", "")
            þf_ft_gr = forms.get("ÞFFTGR", "")
            gf_ft_gr = forms.get("ÞGFFTGR", "")
            ef_ft_gr = forms.get("EFFTGR", "")
            
            verb_blocks = []
            verb_blocks.append('<div class="voice-section"><h4>Fallbeyging</h4>')
            verb_blocks.append(f"""
            <table class="verb-paradigm-table strong-verb" style="text-align: left;">
                <tr class="row-principal"><td></td><td style="text-align: center;"><b>Eintala</b></td><td style="text-align: center;"><b>Fleirtala</b></td></tr>
                <tr><td><i>Nf.</i></td><td style="text-align: center;">{noun_cell(nf_et, nf_et_gr)}</td><td style="text-align: center;">{noun_cell(nf_ft, nf_ft_gr)}</td></tr>
                <tr><td><i>Þf.</i></td><td style="text-align: center;">{noun_cell(þf_et, þf_et_gr)}</td><td style="text-align: center;">{noun_cell(þf_ft, þf_ft_gr)}</td></tr>
                <tr><td><i>Þgf.</i></td><td style="text-align: center;">{noun_cell(gf_et, gf_et_gr)}</td><td style="text-align: center;">{noun_cell(gf_ft, gf_ft_gr)}</td></tr>
                <tr><td><i>Ef.</i></td><td style="text-align: center;">{noun_cell(ef_et, ef_et_gr)}</td><td style="text-align: center;">{noun_cell(ef_ft, ef_ft_gr)}</td></tr>
            </table>
            """)
            verb_blocks.append('</div>')
            
            grid_content = "".join(verb_blocks)
            paradigm_html = render_section("Beygingarlýsing", f'<div class="inflection-container-verbs">{grid_content}</div>')

        # ==========================================
        # 3. ADJECTIVE TABLE LAYOUT (6 columns)
        # ==========================================
        elif is_adjective and forms:
            def adj_row(case_label, case_code):
                kk_et = pick_adjective_declension(forms, "KK", case_code, "ET")
                kk_ft = pick_adjective_declension(forms, "KK", case_code, "FT")
                kvk_et = pick_adjective_declension(forms, "KVK", case_code, "ET")
                kvk_ft = pick_adjective_declension(forms, "KVK", case_code, "FT")
                hk_et = pick_adjective_declension(forms, "HK", case_code, "ET")
                hk_ft = pick_adjective_declension(forms, "HK", case_code, "FT")
                return (
                    f"<tr><td><i>{case_label}</i></td>"
                    f"<td>{html.escape(kk_et) if kk_et else '-'}</td><td>{html.escape(kk_ft) if kk_ft else '-'}</td>"
                    f"<td>{html.escape(kvk_et) if kvk_et else '-'}</td><td>{html.escape(kvk_ft) if kvk_ft else '-'}</td>"
                    f"<td>{html.escape(hk_et) if hk_et else '-'}</td><td>{html.escape(hk_ft) if hk_ft else '-'}</td></tr>"
                )

            adjective_table = f"""
            <table class="verb-paradigm-table strong-verb" style="text-align: center;">
                <tr class="row-principal">
                    <td></td>
                    <td colspan="2"><b>Karlkyn</b></td>
                    <td colspan="2"><b>Kvenkyn</b></td>
                    <td colspan="2"><b>Hvorugkyn</b></td>
                </tr>
                <tr class="row-subjunctive">
                    <td></td>
                    <td><i>et.</i></td><td><i>ft.</i></td>
                    <td><i>et.</i></td><td><i>ft.</i></td>
                    <td><i>et.</i></td><td><i>ft.</i></td>
                </tr>
                {adj_row('Nf.', 'NF')}
                {adj_row('Þf.', 'ÞF')}
                {adj_row('Þgf.', 'ÞGF')}
                {adj_row('Ef.', 'EF')}
            </table>
            """
            paradigm_html = render_section("Beygingarlýsing", f'<div class="inflection-container-verbs"><div class="voice-section"><h4>Lýsingarorðsbeyging</h4>{adjective_table}</div></div>')

        elif seen_forms:
            inflection_boxes_html = []
            for tag, inflected_word in forms.items():
                display_tag, article_label = clean_grammar_tag(tag)
                label_text = f"{display_tag}, {article_label}" if article_label else display_tag
                box_html = f'<div class="inflection-box"><span class="grammar-label">{html.escape(label_text)}</span><b>{html.escape(inflected_word)}</b></div>'
                inflection_boxes_html.append(box_html)
            grid_content = "".join(inflection_boxes_html)
            paradigm_html = render_section("Beygingarlýsing", f'<div class="inflection-container">{grid_content}</div>')
            
        index_tags = "".join([f'<d:index d:value="{html.escape(f)}"/>' for f in seen_forms])
        if raw_hw not in seen_forms: index_tags += f'<d:index d:value="{html.escape(raw_hw)}"/>'
        if lookup_hw not in seen_forms and lookup_hw != raw_hw: index_tags += f'<d:index d:value="{html.escape(lookup_hw)}"/>'
            
        def_list_html = "".join([f'<li style="margin-bottom:6px;">{html.escape(d)}</li>' for d in defs])
        
        # Always-visible section for Notkunardæmi (no fold — see render_section)
        examples_html = ""
        if examples_list:
            ex_items = "".join([f'<li style="margin-bottom:4px;">• {html.escape(ex)}</li>' for ex in examples_list])
            examples_content = f'<ul style="list-style-type:none; padding-left:5px; color:#444; font-style:italic;">{ex_items}</ul>'
            examples_html = render_section("Notkunardæmi", examples_content, extra_style="margin-top:10px;")

        # Always-visible section for Orðasambönd (no fold — see render_section)
        idiom_html = ""
        if idioms:
            idiom_list = "".join([
                f'<li style="margin-bottom:5px;">'
                f'{render_idiom_phrase(re.search(r"<b>(.*?)</b>: <i>(.*?)</i>", idm).group(1)) if re.search(r"<b>(.*?)</b>: <i>(.*?)</i>", idm) else html.escape(idm)}'
                f'{" : <i>" + html.escape(re.search(r"<b>(.*?)</b>: <i>(.*?)</i>", idm).group(2)) + "</i>" if re.search(r"<b>(.*?)</b>: <i>(.*?)</i>", idm) else ""}'
                f'</li>'
                for idm in idioms
            ])
            idiom_content = f'<ul style="list-style-type:square; padding-left:20px;">{idiom_list}</ul>'
            idiom_html = render_section("Orðasambönd", idiom_content, extra_style="margin-top:10px;")
            
        gram_html = f" <span style='font-size: 16px; color: #555; font-weight: normal; font-style: italic;'>({html.escape(grammar_txt)})</span>" if grammar_txt else ""
        pronunciation_html = render_pronunciation_hyphenation(raw_hw, lookup_hw, pron_lookup, hyph_lookup)
        synonyms_html = render_synonyms(lookup_hw, synonyms_lookup)

        entry_id = f"entry_{idx}"
        entry_xml = f"""
        <d:entry id="{entry_id}" d:title="{html.escape(raw_hw)}">
            {index_tags}
            <h1>{html.escape(raw_hw)}{gram_html}</h1>
            {pronunciation_html}
            <ol class="definition-list" style="padding-left:20px; line-height:1.5em; margin-bottom:12px;">
                {def_list_html}
            </ol>
            {examples_html}
            {idiom_html}
            {synonyms_html}
            {paradigm_html}
        </d:entry>
        """
        xml_out.append(entry_xml)
        
    xml_out.append('</d:dictionary>')
    
    dir_name = os.path.dirname(output_path)
    if dir_name: os.makedirs(dir_name, exist_ok=True)
        
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(xml_out))
    print(f"🎉 Build complete! Source XML generated at: {output_path}")

if __name__ == "__main__":
    SOURCE_XML = "data/ino_data.xml"
    OUTPUT_XML = "src/IcelandicDictionary.xml"
    try:
        entries = parse_source_data(SOURCE_XML)
        build_apple_dictionary_xml(entries, OUTPUT_XML)
    except Exception as e:
        print(f"❌ Critical Error during pipeline run: {e}")