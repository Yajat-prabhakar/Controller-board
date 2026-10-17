"""Build a comprehensive bilingual English + Hinglish (Roman Hindi) dictionary.

Combines:
1. HermitDave English 50k frequency list (conversational / subtitles).
2. Smat26 Roman Urdu / Hindi conversational corpus & dictionary (20k+ sentences).
3. Indic crowd transliteration Hindi Roman vocabulary (15k+ words).
4. Curated high-frequency chat words & bigram transitions for both English and Hinglish.
"""
import collections
import csv
import io
import json
import math
import os
import re
import urllib.request

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "controller_keyboard", "data")
OUTPUT_DICT = os.path.join(DATA_DIR, "dictionary.json")
OUTPUT_WORDS = os.path.join(DATA_DIR, "words.txt")

WORD_RE = re.compile(r"^[a-z]+(?:'[a-z]+)?$")

# Curated core conversational Hinglish words given top priority
CORE_HINGLISH = [
    # Question / Basic
    "kya", "kyu", "kyun", "kaise", "kaisa", "kaisi", "kab", "kaha", "kahan", "kaun", "kitna", "kitni",
    "haan", "nahi", "nhi", "na", "mat", "bhi", "hi", "to", "toh", "aur", "ya", "lekin", "magar", "par",
    # Pronouns
    "aap", "aapko", "aapka", "aapki", "aapke", "tum", "tumhe", "tumhara", "tumhari", "tumhare",
    "mai", "main", "mera", "meri", "mere", "mujhe", "muje", "hum", "humein", "humara", "humari",
    "yeh", "ye", "woh", "wo", "uska", "uski", "uske", "use", "unka", "unki", "unke", "unhe", "kisi", "sab",
    # Common verbs & states
    "hai", "hain", "ho", "hoon", "hun", "tha", "thi", "the",
    "kar", "karo", "karein", "karna", "karni", "karne", "karte", "karti", "karta", "kiya", "kiye", "ke",
    "raha", "rahi", "rahe", "hoga", "hogi", "hoge", "honge", "hua", "hui", "hue", "hogaya", "hogayi",
    "dekh", "dekho", "dekha", "dekhna", "sun", "suno", "suna", "bol", "bolo", "bola", "bolna",
    "bata", "batao", "batana", "samajh", "samjha", "samjhe", "soch", "socha", "socho",
    "ja", "jaa", "jao", "jana", "gaya", "gayi", "gaye", "aa", "aao", "aana", "aaya", "aayi", "aaye",
    "chal", "chalo", "chalna", "mil", "milo", "mila", "mile", "rakh", "rakho", "rakha", "le", "lo", "liya", "diya",
    # Chat expressions / slang
    "bhai", "bhaiya", "bro", "yaar", "dost", "sir", "madam",
    "achha", "accha", "achhi", "acchi", "theek", "thik", "sahi", "galat", "bilkul", "pakka",
    "pata", "maloom", "yaad", "shukriya", "dhanyawad", "namaste", "alvida",
    "thoda", "thodi", "zyada", "bohot", "bahut", "kam", "jyada", "kuch", "koi", "sabse",
    "abhi", "aaj", "kal", "parso", "subah", "shaam", "raat", "din", "waqt", "time", "jaldi", "dhire",
    "ajeeb", "badiya", "badhiya", "mast", "shandar", "zabardast", "bawal", "tabahi", "tabartod", "tabrtod",
    "baat", "kaam", "chiz", "cheez", "ghar", "dukan", "jagah", "paas", "dur",
]

CORE_BIGRAMS = {
    "kya": ["hai", "hua", "baat", "kar", "karein", "karo", "hoga", "chahiye", "pata"],
    "nahi": ["hai", "hoga", "hua", "pata", "karna", "tha", "milega", "samjha"],
    "nhi": ["hai", "hoga", "pata", "hua", "yaar"],
    "kaise": ["ho", "hai", "karein", "karo", "hoga", "batao"],
    "bhai": ["kya", "kaise", "sun", "dekh", "kaha", "ek", "ye"],
    "yaar": ["kya", "tu", "ye", "mat", "chal", "sahi"],
    "theek": ["hai", "tha", "hoga", "se"],
    "thik": ["hai", "tha", "hoga"],
    "accha": ["hai", "to", "theek", "yaar", "bhai"],
    "achha": ["hai", "to", "theek", "yaar", "bhai"],
    "bahut": ["achha", "badiya", "sahi", "zyada", "kam", "khoob"],
    "bohot": ["achha", "badiya", "sahi", "zyada", "kam"],
    "main": ["bhi", "to", "kar", "nahi", "aaj", "kya", "dekh"],
    "mai": ["bhi", "to", "kar", "nahi", "aaj", "kya"],
    "aap": ["kaise", "kya", "kaha", "batao", "bhi"],
    "tum": ["kaise", "kya", "kaha", "batao", "bhi"],
    "ye": ["kya", "bhi", "to", "sahi", "nahi", "dekh"],
    "yeh": ["kya", "bhi", "to", "sahi", "nahi"],
    "wo": ["bhi", "to", "kya", "kaha", "nahi"],
    "woh": ["bhi", "to", "kya", "kaha", "nahi"],
    "thank": ["you", "so", "very"],
    "how": ["are", "is", "was", "can", "to", "about"],
    "what": ["is", "are", "do", "about", "happened", "if"],
    "let": ["me", "us", "go", "it"],
    "see": ["you", "all", "what", "how"],
    "good": ["morning", "night", "afternoon", "evening", "job", "luck"],
}


def clean_word(w):
    w = w.lower().strip(" ,.!?:;\"'()[]{}<>/\\|@#$%^&*~`_+-=")
    if WORD_RE.match(w) and len(w) <= 25:
        return w
    return None


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode("utf-8", errors="ignore")


def build():
    print("1. Fetching English 50k frequency list...")
    en_raw = fetch("https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/en/en_50k.txt")

    print("2. Fetching Roman Hindi / Urdu dataset...")
    ro_csv = fetch("https://raw.githubusercontent.com/Smat26/Roman-Urdu-Dataset/master/Dataset/Roman%20Urdu%20DataSet.csv")

    print("3. Fetching Roman Hindi / Urdu dictionary...")
    ro_dict = fetch("https://raw.githubusercontent.com/Smat26/Roman-Urdu-Dataset/master/Dictionary/Roman-Urdu-Dictionary.txt")

    print("4. Fetching Indic crowd transliteration pairs...")
    hi_crowd = fetch("https://raw.githubusercontent.com/anoopkunchukuttan/crowd-indic-transliteration-data/master/crowd_transliterations.hi-en.txt")

    unigrams = collections.Counter()
    bigrams = collections.defaultdict(collections.Counter)

    # 1. Process English 50k
    for line in en_raw.splitlines():
        parts = line.strip().split()
        if len(parts) == 2:
            w = clean_word(parts[0])
            if w:
                try:
                    count = int(parts[1])
                    unigrams[w] += max(10, int(math.log10(count + 1) * 2000))
                except ValueError:
                    unigrams[w] += 100

    # 2. Process Roman Hindi CSV
    reader = csv.reader(io.StringIO(ro_csv))
    for row in reader:
        if not row:
            continue
        tokens = [clean_word(t) for t in re.findall(r"[a-zA-Z']+", row[0])]
        tokens = [t for t in tokens if t]
        for i, t in enumerate(tokens):
            unigrams[t] += 400
            if i > 0:
                prev = tokens[i - 1]
                bigrams[prev][t] += 10

    # 3. Process Roman Hindi dictionary
    for line in ro_dict.splitlines():
        if ":" in line:
            w = clean_word(line.split(":", 1)[0])
            if w:
                unigrams[w] += 300

    # 4. Process Indic crowd transliteration
    for line in hi_crowd.splitlines():
        parts = line.strip().split("\t")
        if parts:
            w = clean_word(parts[0])
            if w:
                unigrams[w] += 250

    # 5. Inject core Hinglish & core bigrams with high priority
    for idx, w in enumerate(CORE_HINGLISH):
        unigrams[w] += 30000 - (idx * 50)  # Top priority ranks

    for prev, next_list in CORE_BIGRAMS.items():
        for rank, nxt in enumerate(next_list):
            bigrams[prev][nxt] += 500 - (rank * 30)

    # Clean & prune bigrams (keep top 6 transitions per word)
    pruned_bigrams = {}
    for prev, counts in bigrams.items():
        top = [w for w, _ in counts.most_common(6)]
        if top:
            pruned_bigrams[prev] = top

    # Sort all unigrams by frequency descending
    sorted_words = [w for w, _ in unigrams.most_common()]

    print(f"Total vocabulary size: {len(sorted_words)} words")
    print(f"Total bigram contexts: {len(pruned_bigrams)} words")

    os.makedirs(DATA_DIR, exist_ok=True)

    # Save words.txt for backwards compatibility (ordered by frequency)
    with open(OUTPUT_WORDS, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted_words) + "\n")

    # Save full dictionary.json with unigrams and bigrams
    dict_data = {
        "words": sorted_words,
        "bigrams": pruned_bigrams,
    }
    with open(OUTPUT_DICT, "w", encoding="utf-8") as f:
        json.dump(dict_data, f, ensure_ascii=False)

    print(f"Successfully saved to {OUTPUT_WORDS} and {OUTPUT_DICT}")


if __name__ == "__main__":
    build()
