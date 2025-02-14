#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Main Script for Processing Japanese Text Files and Generating Outputs & Anki Deck

This script processes all Japanese text files in the "input" folder located in the current working directory.
It accepts files in various formats (.ass, .srt, or .txt).

The script performs the following:
  - For .ass and .srt files: Extracts only the "Default" dialogue lines.
  - For .txt files: Reads the text content directly.
  - Tokenizes each line using MeCab (with UniDic).
  - Looks up each token’s English translation and kana reading using a local JSON dictionary.
  - Only tokens with a valid translation (i.e. not "??? (Not found)") are used in final outputs;
    tokens that cannot be translated are written to scrap.txt.
  - Global duplicate filtering is applied for text outputs; however, the JSON structure
    (which is used to build flashcards) is built using all non-ambiguous tokens, so that up to 5 example sentences
    per surface variant are retained.
  - Frequency counts are computed based on the normalized base form.
  - Only words that appear 5 or more times (by base form) are added to the Anki deck.
  - Ambiguous tokens (pure-kana tokens whose normalized forms differ) are output to separate JSON and TXT files.

If the "input" folder does not exist in the working directory, it will be created automatically.
Place your .ass, .srt, or .txt Japanese text files in that folder.
"""

import os
import sys
import re
import json
import unicodedata
import MeCab
from collections import defaultdict, Counter

# --- Helper for resource paths (for bundled files) ---
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS  # PyInstaller temporary folder
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- Output Folder ---
OUTPUT_FOLDER = "output"
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

# --- Input Folder (in current working directory) ---
input_folder = os.path.join(os.getcwd(), "input")
if not os.path.exists(input_folder):
    os.makedirs(input_folder)
    print(f"Created '{input_folder}' folder. Please add your .ass, .srt, or .txt files there and re-run the script.")
    sys.exit(0)

# --- MeCab Setup ---
try:
    import unidic
    dic_dir = resource_path(unidic.DICDIR).replace('\\', '/')
    print("Using UniDic from:", dic_dir)
except ImportError:
    dic_dir = resource_path("path/to/your/UniDic/dicdir").replace('\\', '/')
    print("Using manually specified UniDic path:", dic_dir)

tagger = MeCab.Tagger(f'-d "{dic_dir}"')

# --- Load JSON Dictionary (no JLPT) ---
def load_json_dictionary(dict_path="dictionary.json"):
    mapping = {}
    dict_full_path = resource_path(dict_path)
    if os.path.exists(dict_full_path):
        with open(dict_full_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for entry in data.get("words", []):
            glosses = []
            for sense in entry.get("sense", []):
                for gloss in sense.get("gloss", []):
                    if gloss.get("lang") == "eng" and gloss.get("text"):
                        glosses.append(gloss.get("text"))
            translation = glosses[0].split(';')[0].strip() if glosses else "??? (Not found)"
            # For kana entries:
            for kana_obj in entry.get("kana", []):
                if "text" not in kana_obj:
                    continue
                candidate = kana_obj["text"]
                reading = candidate
                mapping.setdefault(candidate, []).append((translation, reading))
            # For kanji entries:
            for kanji_obj in entry.get("kanji", []):
                if "text" not in kanji_obj:
                    continue
                candidate = kanji_obj["text"]
                reading = None
                kana_lookup = []
                for kana_obj in entry.get("kana", []):
                    if "text" in kana_obj:
                        kana_lookup.append((kana_obj["text"], kana_obj.get("appliesToKanji", [])))
                for ktext, applies in kana_lookup:
                    if candidate in applies or '*' in applies:
                        reading = ktext
                        break
                if not reading:
                    reading = candidate
                mapping.setdefault(candidate, []).append((translation, reading))
    else:
        print("Warning: JSON dictionary file not found at", dict_full_path, ". Using an empty dictionary.")
    return mapping

word_dictionary = load_json_dictionary()

# --- Lookup Function (returns primary and ignores extra variants) ---
def lookup_translation(word):
    # Returns (primary, []) where primary is (translation, reading)
    entries = word_dictionary.get(word)
    if not entries:
        return (("??? (Not found)", "N/A"), [])
    primary = entries[0]
    return (primary, [])

# --- Token Filtering ---
def is_all_punctuation(text):
    return all(unicodedata.category(ch).startswith('P') for ch in text)

def contains_kanji(s):
    return any(0x4E00 <= ord(ch) <= 0x9FFF for ch in s)

def is_unwanted_token(surface, features):
    if not surface.strip():
        return True
    try:
        if len(surface) == 1 and "HIRAGANA" in unicodedata.name(surface[0]):
            return True
    except ValueError:
        pass
    if all(ord(ch) < 128 for ch in surface):
        return True
    if is_all_punctuation(surface):
        return True
    fields = features.split(',')
    if fields:
        pos = fields[0]
        excluded_pos = {"助詞", "助動詞", "記号", "接続詞", "連体詞"}
        if pos in excluded_pos:
            return True
    return False

# --- File Extraction ---
def clean_ass_line(text):
    return re.sub(r'\{.*?\}', '', text).replace(r'\N', ' ').strip()

def extract_dialogue_lines(filename):
    dialogue_lines = []
    ext = os.path.splitext(filename)[1].lower()
    with open(filename, 'r', encoding='utf-8-sig') as f:
        if ext in ['.ass', '.srt']:
            in_events = False
            for line in f:
                line = line.rstrip('\n')
                if line.startswith('[Events]'):
                    in_events = True
                    continue
                if in_events and line.startswith('Dialogue:'):
                    parts = line.split(',', 9)
                    if len(parts) >= 10:
                        style = parts[3].strip().lower()
                        if style != "default":
                            continue
                        dialogue_text = clean_ass_line(parts[9])
                        dialogue_lines.append(dialogue_text)
        elif ext == '.txt':
            for line in f:
                line = line.strip()
                if line:
                    dialogue_lines.append(line)
        else:
            print(f"Unsupported file format: {filename}")
    return dialogue_lines

# --- Annotate Surface Word Meanings ---
def annotate_surface_meaning(base, surface, base_meaning):
    if surface == base:
        return f"{base_meaning} (general meaning)"
    elif surface.endswith("ます"):
        return f"{base_meaning} (polite form)"
    elif surface.endswith("ました"):
        return f"{base_meaning} (past tense)"
    else:
        return base_meaning

# --- Token Processing (delayed normalization for pure kana) ---
def process_dialogue_line(sentence):
    """
    Tokenize a sentence using MeCab.
    For pure kana tokens, leave base as the original surface (and record potential_base from MeCab).
    For tokens with Kanji, use normalized form (with additional normalization for verbs/adjectives).
    Returns tokens as tuples:
      (base, surface, base_reading, translation, surface_reading, sentence, potential_base)
    """
    tokens = []
    node = tagger.parseToNode(sentence)
    while node:
        if node.surface:
            tokens.append((node.surface, node.feature, sentence))
        node = node.next

    processed = []
    for surface, features, sentence in tokens:
        if is_unwanted_token(surface, features):
            continue
        fields = features.split(',')
        potential_base = fields[6] if len(fields) > 6 and fields[6] != "*" else surface
        if not contains_kanji(surface):
            base = surface
        else:
            base = fields[6] if len(fields) > 6 and fields[6] != "*" else surface
            if contains_kanji(surface):
                base = surface
            elif contains_kanji(base):
                base = base
            else:
                known_base = word_dictionary.get(surface)
                if known_base:
                    base = known_base[0][0]
            part_of_speech = fields[0]
            if part_of_speech == "動詞" and len(fields) > 6 and fields[6] != "*" and contains_kanji(fields[6]):
                base = fields[6]
            if part_of_speech == "形容詞" and len(fields) > 6 and fields[6] != "*":
                base = fields[6]
        (primary, _) = lookup_translation(base)
        translation, base_reading = primary
        primary_surface, _ = lookup_translation(surface)
        _, surface_reading = primary_surface
        if surface_reading == "N/A":
            surface_reading = base_reading
        processed.append((base, surface, base_reading, translation, surface_reading, sentence, potential_base))
    return processed

# --- Build JSON Structure ---
def build_json_structure(tokens):
    """
    Build a JSON structure grouping tokens by base form and then by surface variant.
    Each token is a tuple:
      (base, surface, base_reading, translation, surface_reading, sentence, potential_base, filename)
    For each surface variant, up to 5 example sentences are retained.
    """
    words = {}
    for token in tokens:
        base, surface, base_reading, translation, surface_reading, sentence, potential_base, filename = token
        if translation == "??? (Not found)":
            continue
        if base not in words:
            words[base] = {
                "base_word": base,
                "reading": base_reading,
                "meaning": translation,
                "variants": {}
            }
        variants = words[base]["variants"]
        if surface not in variants:
            variants[surface] = {
                "surface_word": surface,
                "reading": surface_reading,
                "surface_word_meaning": annotate_surface_meaning(base, surface, translation),
                "surface_sentences": [sentence]
            }
        else:
            if sentence not in variants[surface]["surface_sentences"] and len(variants[surface]["surface_sentences"]) < 5:
                variants[surface]["surface_sentences"].append(sentence)
    word_list = []
    for entry in words.values():
        entry["variants"] = list(entry["variants"].values())
        word_list.append(entry)
    return {"words": word_list}

# --- Ambiguity Detection Helper ---
def detect_ambiguous_tokens(tokens):
    """
    For pure kana tokens, check if their potential_base values differ.
    Returns (ambiguous_groups, ambiguous_tokens) where ambiguous_groups maps surface -> list of tokens.
    """
    ambiguous_groups = defaultdict(list)
    for token in tokens:
        base, surface, base_reading, translation, surface_reading, sentence, potential_base = token[:7]
        if not contains_kanji(surface):
            ambiguous_groups[surface].append(token)
    ambiguous_tokens = []
    for surface, token_list in ambiguous_groups.items():
        potential_bases = {t[6] for t in token_list}
        if len(potential_bases) > 1:
            ambiguous_tokens.extend(token_list)
    return ambiguous_groups, ambiguous_tokens

# --- Main Execution ---
def main():
    # Process files from the "input" folder.
    if not os.path.exists(input_folder):
        os.makedirs(input_folder)
        print(f"Created '{input_folder}' folder. Please add your .ass, .srt, or .txt files there and re-run the script.")
        return

    global_tokens = []  # Each token: (base, surface, base_reading, translation, surface_reading, sentence, potential_base, filename)
    per_file_totals = defaultdict(int)
    scrap_by_file = defaultdict(list)

    for filename in sorted(os.listdir(input_folder)):
        if not filename.lower().endswith((".ass", ".srt", ".txt")):
            continue
        filepath = os.path.join(input_folder, filename)
        dialogue_lines = extract_dialogue_lines(filepath)
        for line in dialogue_lines:
            tokens = process_dialogue_line(line)
            for token in tokens:
                base, surface, base_reading, translation, surface_reading, sentence, potential_base = token
                if translation == "??? (Not found)":
                    if len(surface) > 1:
                        scrap_by_file[filename].append((surface, surface_reading, translation, sentence))
                else:
                    global_tokens.append((base, surface, base_reading, translation, surface_reading, sentence, potential_base, filename))
                per_file_totals[filename] += 1

    # Detect ambiguous tokens (for pure kana with differing potential_base values).
    ambiguous_groups, ambiguous_tokens = detect_ambiguous_tokens(global_tokens)
    non_ambiguous_tokens = [token for token in global_tokens if (contains_kanji(token[1]) or token[1] not in ambiguous_groups)]
    
    # For output.txt, deduplicate tokens by surface.
    global_seen = {}
    duplicates_dropped = defaultdict(int)
    final_tokens = []
    for token in global_tokens:
        base, surface, base_reading, translation, surface_reading, sentence, potential_base, filename = token
        key = surface
        if key in global_seen:
            duplicates_dropped[filename] += 1
        else:
            global_seen[key] = token
            final_tokens.append(token)

    file_groups = defaultdict(list)
    for token in final_tokens:
        _, surface, base_reading, translation, surface_reading, sentence, potential_base, filename = token
        file_groups[filename].append(token)

    out_lines = ["Final Vocabulary List (grouped by file):\n"]
    for fname in sorted(per_file_totals.keys()):
        final_count = len([t for t in final_tokens if t[7] == fname])
        stats = {
            'kept_initial': per_file_totals[fname],
            'duplicates_dropped': duplicates_dropped[fname],
            'final_kept': final_count
        }
        out_lines.append(f"=== {fname} ===")
        out_lines.append(f"Kept initially: {stats['kept_initial']}, Duplicates dropped: {stats['duplicates_dropped']}, Final kept: {stats['final_kept']}")
        out_lines.append("Token\tReading\tTranslation\tSentence")
        out_lines.append("-" * 80)
        for token in sorted(file_groups.get(fname, []), key=lambda x: x[1]):
            _, surface, base_reading, translation, surface_reading, sentence, _, _ = token
            out_lines.append(f"{surface}\t{surface_reading}\t{translation}\t{sentence}")
        out_lines.append("\n")
    output_text = "\n".join(out_lines)
    with open(os.path.join(OUTPUT_FOLDER, "output.txt"), "w", encoding="utf-8") as f_out:
        f_out.write(output_text)
    print(output_text)

    # Prepare frequency_output.txt (by base form from non-ambiguous tokens).
    freq_counter = Counter(token[0] for token in non_ambiguous_tokens)
    freq_lines = ["Final Vocabulary Grouped by Frequency (descending):\n"]
    for base_word, count in freq_counter.most_common():
        token = next((t for t in non_ambiguous_tokens if t[0] == base_word), None)
        if token:
            base, surface, base_reading, translation, surface_reading, sentence, potential_base, filename = token
            freq_lines.append(f"{base_word}\t{surface_reading}\t{translation}\tFrequency: {count}\tSample: {sentence}")
    freq_output_text = "\n".join(freq_lines)
    with open(os.path.join(OUTPUT_FOLDER, "frequency_output.txt"), "w", encoding="utf-8") as f_freq:
        f_freq.write(freq_output_text)

    # Prepare scrap.txt.
    scrap_lines = ["Scrap (Unidentified) Tokens (grouped by file):\n"]
    for fname in sorted(scrap_by_file.keys()):
        scrap_lines.append(f"=== {fname} ===")
        scrap_lines.append("Token\tReading\tTranslation\tSentence")
        scrap_lines.append("-" * 60)
        for token in sorted(scrap_by_file[fname], key=lambda x: x[3]):
            surface, surface_reading, translation, sentence = token
            scrap_lines.append(f"{surface}\t{surface_reading}\t{translation}\t{sentence}")
        scrap_lines.append("\n")
    scrap_output = "\n".join(scrap_lines)
    with open(os.path.join(OUTPUT_FOLDER, "scrap.txt"), "w", encoding="utf-8") as f_scrap:
        f_scrap.write(scrap_output)

    # --- Build JSON Structure ---
    json_tokens = non_ambiguous_tokens
    json_data = build_json_structure([(t[0], t[1], t[2], t[3], t[4], t[5], t[6], t[7]) for t in json_tokens])
    json_output_path = os.path.join(OUTPUT_FOLDER, "output_data.json")
    with open(json_output_path, "w", encoding="utf-8") as json_file:
        json.dump(json_data, json_file, ensure_ascii=False, indent=2)
    print(f"JSON output written to {json_output_path}")

    # Build ambiguous JSON structure.
    ambiguous_json = build_json_structure([(t[0], t[1], t[2], t[3], t[4], t[5], t[6], t[7]) for t in ambiguous_tokens])
    ambiguous_json_path = os.path.join(OUTPUT_FOLDER, "ambiguous_entries.json")
    with open(ambiguous_json_path, "w", encoding="utf-8") as amb_json_file:
        json.dump(ambiguous_json, amb_json_file, ensure_ascii=False, indent=2)
    print(f"Ambiguous JSON output written to {ambiguous_json_path}")

    # Prepare ambiguous_entries.txt.
    amb_lines = ["Ambiguous Entries for Manual Review:\n"]
    for surface, tokens in sorted(ambiguous_groups.items()):
        potential_bases = {t[6] for t in tokens}
        if len(potential_bases) > 1:
            amb_lines.append(f"Surface: {surface}")
            for token in tokens:
                base, surface, base_reading, translation, surface_reading, sentence, potential_base, filename = token
                amb_lines.append(f"  Potential Base: {potential_base}, Reading: {surface_reading}, Translation: {translation}, Sentence: {sentence}")
            amb_lines.append("\n")
    ambiguous_txt_path = os.path.join(OUTPUT_FOLDER, "ambiguous_entries.txt")
    with open(ambiguous_txt_path, "w", encoding="utf-8") as amb_txt_file:
        amb_txt_file.write("\n".join(amb_lines))
    print(f"Ambiguous text output written to {ambiguous_txt_path}")

    # --- Prepare Flashcard Entries for Anki ---
    freq_by_base = Counter(token[0] for token in non_ambiguous_tokens)
    flashcard_entries = []
    for word in json_data["words"]:
        base_word = word["base_word"]
        if freq_by_base[base_word] < 5:
            continue
        sentences = []
        for variant in word["variants"]:
            for s in variant["surface_sentences"]:
                if s not in sentences:
                    sentences.append(s)
                if len(sentences) >= 5:
                    break
            if len(sentences) >= 5:
                break
        entry = {
            "Word": base_word,
            "Reading": word["reading"],
            "Translation": word["meaning"],
            "Sentences": sentences,
            "Frequency": freq_by_base[base_word]
        }
        flashcard_entries.append(entry)
    if flashcard_entries:
        try:
            import anki_flashcard_creator
            anki_flashcard_creator.create_anki_deck(flashcard_entries,
                                                    output_folder=OUTPUT_FOLDER,
                                                    deck_name="generated_anki_deck")
        except ImportError:
            print("anki_flashcard_creator module not found. Please ensure it is in the PYTHONPATH.")
    else:
        print("No flashcard entries met the frequency threshold.")

if __name__ == "__main__":
    main()
