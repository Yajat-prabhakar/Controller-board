"""Word prediction: prefix completion + next-word (bigram) prediction + learning.

Scoring for a candidate word w, given the typed prefix and the previous word:
    score = base_frequency(w) + user_frequency(w) + bigram(prev, w)
- base_frequency comes from the bundled frequency-ordered word list.
- user_frequency / bigram are learned locally from what you type.
"""
import bisect
import json
import math
import os
import threading
from collections import Counter, defaultdict

_FALLBACK_WORDS = (
    "the of and to a in for is on that by this with i you it not or be are from at as your all "
    "have new more an was we will home can us about if page my has search free but our one other "
    "do no information time they site he up may what which their news out use any there see only "
    "so his when contact here business who web also now help get pm view online first am been would "
    "how were me services some these click its like service than find price date back top people had "
    "list name just over state year day into email two health world next used go work last most"
).split()

_CONTRACTIONS = (
    "don't can't won't i'm it's that's you're i'll i've didn't doesn't isn't wasn't couldn't "
    "wouldn't shouldn't let's there's he's she's we're they're i'd you'll we'll they'll aren't "
    "haven't what's you've we've they've hasn't weren't"
).split()


def _is_word(w):
    return 0 < len(w) <= 30 and all(c.isalpha() or c == "'" for c in w) and any(c.isalpha() for c in w)


class Predictor:
    def __init__(self, words_path=None, user_path=None, learn=True):
        self.learn_enabled = learn
        self.user_path = user_path
        self._lock = threading.Lock()
        self._dirty = False

        words = []
        self.base_bigrams = {}

        # 1. Try loading dictionary.json (contains full words list + bigrams)
        json_path = None
        if words_path:
            candidate_json = os.path.join(os.path.dirname(words_path), "dictionary.json")
            if os.path.exists(candidate_json):
                json_path = candidate_json
            elif words_path.endswith(".json") and os.path.exists(words_path):
                json_path = words_path

        if json_path:
            try:
                with open(json_path, encoding="utf-8") as f:
                    data = json.load(f)
                    words = [w.strip().lower() for w in data.get("words", []) if _is_word(w.strip().lower())]
                    self.base_bigrams = data.get("bigrams", {})
            except (OSError, ValueError):
                words = []

        # 2. Fallback to words.txt if dictionary.json wasn't loaded
        if not words and words_path and os.path.exists(words_path):
            with open(words_path, encoding="utf-8") as f:
                words = [w.strip().lower() for w in f if _is_word(w.strip().lower())]

        if not words:
            words = list(_FALLBACK_WORDS)

        self.rank = {}
        for i, w in enumerate(words):
            self.rank.setdefault(w, i)
        for w in _CONTRACTIONS:
            self.rank.setdefault(w, 150)
        self.sorted_words = sorted(self.rank)
        self.top_words = sorted(self.rank, key=self.rank.get)[:40]

        self.user_uni = Counter()
        self.user_bi = defaultdict(Counter)
        self._load_user()

    # -- persistence --------------------------------------------------------
    def _load_user(self):
        if not self.user_path or not os.path.exists(self.user_path):
            return
        try:
            with open(self.user_path, encoding="utf-8") as f:
                data = json.load(f)
            self.user_uni.update(data.get("unigrams", {}))
            for prev, nxt in data.get("bigrams", {}).items():
                self.user_bi[prev].update(nxt)
        except (OSError, ValueError):
            pass

    def save(self):
        if not self.user_path or not self._dirty:
            return
        with self._lock:
            data = {"unigrams": dict(self.user_uni),
                    "bigrams": {p: dict(c) for p, c in self.user_bi.items() if c}}
            self._dirty = False
        os.makedirs(os.path.dirname(self.user_path), exist_ok=True)
        tmp = self.user_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, self.user_path)

    def clear_learned(self):
        with self._lock:
            self.user_uni.clear()
            self.user_bi.clear()
            self._dirty = True
        self.save()

    @property
    def learned_count(self):
        return len(self.user_uni)

    # -- learning -----------------------------------------------------------
    def learn(self, word, prev=None):
        if not self.learn_enabled:
            return
        word = word.lower().strip("'")
        if not _is_word(word) or len(word) < 2 and word not in ("a", "i"):
            return
        with self._lock:
            self.user_uni[word] += 1
            if prev:
                self.user_bi[prev.lower()][word] += 1
            self._dirty = True

    # -- prediction ---------------------------------------------------------
    def _score(self, word, prev):
        r = self.rank.get(word, 100000)
        base = 1.0 / math.sqrt(1 + r)
        user = 0.6 * math.log1p(self.user_uni.get(word, 0))
        bi = 0.0
        if prev:
            if prev in self.user_bi and word in self.user_bi[prev]:
                bi += 2.0 * math.log1p(self.user_bi[prev][word])
            elif prev in self.base_bigrams and word in self.base_bigrams[prev]:
                idx = self.base_bigrams[prev].index(word)
                bi += 1.2 / (1 + idx)
        return base + user + bi

    def suggest(self, prefix, prev=None, k=4):
        """Return up to k lowercase words. Empty prefix = predict the next word."""
        prefix = (prefix or "").lower()
        prev = prev.lower() if prev else None
        results = []

        if prefix:
            cands = set()
            # Fast prefix search in 80k vocabulary
            i = bisect.bisect_left(self.sorted_words, prefix)
            count = 0
            while i < len(self.sorted_words) and self.sorted_words[i].startswith(prefix) and count < 800:
                cands.add(self.sorted_words[i])
                i += 1
                count += 1
            cands.update(w for w in self.user_uni if w.startswith(prefix))
            cands.discard(prefix)
            results = sorted(cands, key=lambda w: (-self._score(w, prev), w))[:k]
        else:
            seen = set()
            # 1. Learned personal bigrams
            if prev and prev in self.user_bi:
                for w, _ in self.user_bi[prev].most_common(k):
                    if w not in seen:
                        results.append(w)
                        seen.add(w)
            # 2. Built-in contextual bigrams (e.g., "kya" -> "hai", "thank" -> "you")
            if len(results) < k and prev and prev in self.base_bigrams:
                for w in self.base_bigrams[prev]:
                    if w not in seen:
                        results.append(w)
                        seen.add(w)
                    if len(results) == k:
                        break
            # 3. Top frequent vocabulary
            if len(results) < k:
                for w in self.top_words:
                    if w not in seen:
                        results.append(w)
                        seen.add(w)
                    if len(results) == k:
                        break
        return results
