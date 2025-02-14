# Script Shredder

**Script Shredder** is a Python tool for processing Japanese text files and generating learning resources—including an Anki flashcard deck. It supports multiple input formats such as `.ass` (Advanced SubStation Alpha), `.srt` (SubRip Subtitle), and `.txt` (plain text) files.

## Overview

Script Shredder performs the following tasks:

- **Input Processing:**  
  Reads Japanese text from files placed in an `input` folder located in the current working directory.  
  - For `.ass` and `.srt` files, it extracts only the "Default" dialogue lines.  
  - For `.txt` files, it processes each non-empty line as input text.

- **Tokenization:**  
  Uses [MeCab](https://taku910.github.io/mecab/) (with UniDic) to tokenize the text and normalize Japanese words.

- **Translation Lookup:**  
  Looks up each token’s English translation and kana reading using a local JSON dictionary file (`dictionary.json`).

- **Output Generation:**  
  Generates several output files in an `output` folder:
  - **output.txt:** A summary of processed tokens grouped by input file.
  - **frequency_output.txt:** A frequency list of vocabulary items (grouped by normalized base form).
  - **scrap.txt:** A list of tokens that could not be translated.
  - **output_data.json:** A JSON structure that groups tokens by normalized base and surface variants—with up to 5 example sentences per variant.
  - **ambiguous_entries.json / ambiguous_entries.txt:** Files listing ambiguous tokens (pure-kana tokens whose normalized forms differ).

- **Anki Flashcard Deck Creation:**  
  Generates an Anki flashcard deck (as `generated_anki_deck.apkg`) from vocabulary items that appear at least 5 times (by normalized base form). Each flashcard contains:
  - The base word  
  - Its reading and English translation  
  - Up to 5 example sentences collected from the text data

- **Ambiguity Filtering:**  
  Tokens that are ambiguous (i.e. pure-kana tokens with differing normalized forms) are removed from the flashcard deck and saved separately.

## Requirements

- Python 3.6+
- [MeCab](https://taku910.github.io/mecab/) with [UniDic](https://unidic.ninjal.ac.jp/)
- A JSON dictionary file (`dictionary.json`) (see **Dictionary Attribution and License** below)
- The `anki_flashcard_creator.py` module (for Anki deck creation)
- Standard Python modules (`os`, `sys`, `json`, etc.)

## Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/yourusername/yourrepo.git
   cd yourrepo

2. **(Optional) Create a Virtual Environment:**

    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate

3. **Install Dependencies: Create a requirements.txt file listing your dependencies (e.g., MeCab, genanki, etc.) and run:**

    pip install -r requirements.txt

**Ensure that MeCab and UniDic are installed and properly configured on your system.**

**Usage**

    Prepare Input Files:
    Place your Japanese text files (with extensions .ass, .srt, or .txt) into the input folder located in the working directory.
    If the folder does not exist, Script Shredder will create it on the first run and then exit, prompting you to add files.

    Run the Script:

    python shredder.py

    The script will process your files, generate various output files in the output folder, and (if vocabulary items meet the frequency threshold) create an Anki deck file (generated_anki_deck.apkg).

**Building a Standalone Executable**

    To bundle Script Shredder as a one‑file executable using PyInstaller, run a command similar to:

    pyinstaller --onefile --console --hidden-import=genanki --add-data "dictionary.json;." --add-data "anki_flashcard_creator.py;." --add-data "Z:/Path/To/UniDic/dicdir;unidic/dicdir" shredder.py

    Note: Do not include the input folder in the build; Script Shredder expects the input folder to be in the current working directory.

**Dictionary Attribution and License**

    Script Shredder uses a simplified version of the JMdict-simplified dictionary.
    The original XML files (e.g., JMdict.xml, JMdict_e.xml, JMdict_e_examp.xml, and JMnedict.xml) are the property of the Electronic Dictionary Research and Development Group (EDRDG), initiated by Jim Breen in 1991.

    Note: The dictionary data used in this project is derived from JMdict-simplified, which is available under the Creative Commons Attribution-ShareAlike License (V4.0). [repo](https://github.com/scriptin/jmdict-simplified)

**License Summary**

    The dictionary files and all derived files are distributed under the Creative Commons Attribution-ShareAlike License (V4.0). In summary, you are free to:

    Share: Copy, distribute, and transmit the work.
    Remix: Adapt, transform, and build upon the work.

**Under the following conditions:**

    Attribution:
    You must provide appropriate credit. For example, if you use or publish material based on these files, clearly acknowledge that the data is derived from JMdict-simplified / JMdict by the EDRDG.
    Share Alike:
    Any adaptations of the data must be distributed under the same or a compatible license.

**For full license details:**

    Creative Commons Attribution-ShareAlike License (V4.0) Deed
    Full License Text

**Output Files**

    All generated files are placed in the output folder:

        output.txt: Processed token summary grouped by input file.
        frequency_output.txt: Vocabulary frequency list.
        scrap.txt: List of tokens that could not be translated.
        output_data.json: JSON structure grouping vocabulary items with up to 5 example sentences per surface variant.
        ambiguous_entries.json / ambiguous_entries.txt: Lists of ambiguous tokens.
        generated_anki_deck.apkg: An Anki flashcard deck (if applicable).

**Script Shredder is distributed under the Creative Commons Attribution-ShareAlike License (V4.0).**
