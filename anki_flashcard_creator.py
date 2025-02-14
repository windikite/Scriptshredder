#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
anki_flashcard_creator.py

This module defines a function create_anki_deck(entries, output_folder, deck_name)
that creates an Anki flashcard deck from a list of entries.
Each entry should be a dictionary with the following keys:
  - "Word": The token as originally found (e.g. kanji if available)
  - "Reading": The kana reading of the word (from dictionary lookup)
  - "Translation": The English translation of the word
  - "Sentences": A list (up to 5) of example full dialogue sentences where the word appears
  - "Tag": A string tag indicating frequency (e.g. "very_common", "common", etc.)

The deck is built so that the front side uses JavaScript to randomly pick one sentence from the Sentences field
(with the token highlighted) and the back side shows that sentence along with the word’s reading and translation.

All output is placed in the output folder.
"""

import os
import json
import genanki

def create_anki_deck(entries, output_folder="output", deck_name="generated_anki_deck"):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    model = genanki.Model(
        model_id=1607392319,
        name='Custom Flashcard Model',
        fields=[
            {'name': 'Word'},
            {'name': 'Sentences'},  # JSON array as string
            {'name': 'Reading'},
            {'name': 'Translation'},
        ],
        templates=[
            {
                'name': 'Card 1',
                'qfmt': r'''
<div id="front" style="text-align: center; margin-top: 20px;">
  <span id="word" style="font-size: 24px; font-weight: bold;">{{Word}}</span>
  <span id="sentences" style="display: none;">{{Sentences}}</span>
  <p id="sentence-display" style="font-size: 20px; margin-top: 20px;"></p>
  <script>
    var word = document.getElementById("word").innerHTML.trim();
    var rawSentences = document.getElementById("sentences").innerHTML.trim();
    var sentences = JSON.parse(rawSentences);
    var chosen = sentences[Math.floor(Math.random() * sentences.length)];
    var escaped = word.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
    var highlightedSentence = chosen.replace(new RegExp(escaped, "g"), "<span style='color: yellow;'>" + word + "</span>");
    document.getElementById("sentence-display").innerHTML = highlightedSentence;
  </script>
</div>
''',
                'afmt': r'''
<div id="back" style="text-align: center; margin-top: 20px;">
  <span id="word" style="font-size: 24px; font-weight: bold;">{{Word}}</span>
  <p style="font-size: 20px; margin-top: 20px;">{{Reading}} - {{Translation}}</p>
</div>
'''
            }
        ]
    )

    deck = genanki.Deck(
        deck_id=2059400110,
        name=deck_name
    )

    # Sort entries are assumed to be pre-sorted.
    for entry in entries:
        word = entry.get("Word", "")
        reading = entry.get("Reading", "")
        translation = entry.get("Translation", "")
        sentences_list = entry.get("Sentences", [])[:5]
        sentences_json = json.dumps(sentences_list, ensure_ascii=False)
        note = genanki.Note(
            model=model,
            fields=[word, sentences_json, reading, translation],
            tags=[entry.get("Tag", "")]
        )
        deck.add_note(note)

    package = genanki.Package(deck)
    deck_filename = os.path.join(output_folder, f"{deck_name}.apkg")
    package.write_to_file(deck_filename)
    print(f"Anki deck created: {deck_filename}")
