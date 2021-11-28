import os

import nltk
from nltk.corpus import stopwords
from nltk.stem.wordnet import WordNetLemmatizer
from nltk.tag import pos_tag
from nltk.tokenize import word_tokenize
import regex as re
from unidecode import unidecode

in_path = 'corpus/raw'
out_path = 'corpus/nltk_out'

# NLTK setup.
nltk.download('averaged_perceptron_tagger')
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')
nltk.download('universal_tagset')
stop_words = set(stopwords.words("english"))
wnl = WordNetLemmatizer()

# Regex
defuzzer = re.compile(r"([^a-zA-Z0-9]+)")

files = [f for f in os.listdir(in_path) if f.endswith(".txt")]
i = 1
for file in files:

    print(f"{i}/{len(files)}: {file[:60]}...")
    i = i + 1

    # Skip ahead if we've already done this one.
    if os.path.exists(os.path.join(out_path, file)):
        continue

    # Load text and remove special characters.
    with open(os.path.join(in_path, file), "r", encoding="utf-8") as f:
        text = unidecode(f.read())

    # De-fuzz.
    text = defuzzer.sub(" ", text)

    # Tokenize.
    tokenized_text = word_tokenize(text)
    text = []

    # Remove stopwords.
    for word in [w for w in tokenized_text if w not in stop_words]:
        text.append(word)

    # PoS Tag.
    text = pos_tag(text, tagset="universal")

    # Lemmatize.
    for x in range(len(text)):
        word, pos = text[x]
        if pos == "VERB":
            pos = "v"
        elif pos == "ADJ":
            pos = "a"
        elif pos == "ADV":
            pos = "r"
        else:
            pos = "n"
        text[x] = wnl.lemmatize(word, pos=pos)

    # Save text to file.
    text = " ".join(text)
    with open(os.path.join(out_path, file), "w", encoding="utf-8") as f:
        f.write(text)

print("** DONE **")
