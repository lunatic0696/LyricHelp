from __future__ import annotations

import re

VOWELS = "aeiouáéíóúâêôãõàü"
ACCENTED_VOWELS = "áéíóúâêôãõà"
WORD_RE = re.compile(r"^[a-záéíóúâêôãõàüç-]+$", re.IGNORECASE)

_DIGRAPHS = {
    "nh": "ɲ",
    "lh": "ʎ",
    "ch": "ʃ",
    "rr": "ʁ",
    "ss": "s",
    "qu": "k",
    "gu": "g",
}

_SINGLE = {
    "a": "a",
    "á": "a",
    "â": "ɐ",
    "ã": "ɐ̃",
    "à": "a",
    "e": "e",
    "é": "ɛ",
    "ê": "e",
    "i": "i",
    "í": "i",
    "o": "o",
    "ó": "ɔ",
    "ô": "o",
    "õ": "õ",
    "u": "u",
    "ú": "u",
    "ü": "u",
    "b": "b",
    "c": "k",
    "ç": "s",
    "d": "d",
    "f": "f",
    "g": "g",
    "h": "",
    "j": "ʒ",
    "k": "k",
    "l": "l",
    "m": "m",
    "n": "n",
    "p": "p",
    "q": "k",
    "r": "ɾ",
    "s": "s",
    "t": "t",
    "v": "v",
    "w": "w",
    "x": "ʃ",
    "y": "i",
    "z": "z",
    "-": "",
}


def is_valid_word(word: str) -> bool:
    return bool(WORD_RE.match(word.strip().lower()))


def syllable_count(word: str) -> int:
    groups = re.findall(r"[aeiouáéíóúâêôãõàü]+", word.lower())
    return max(1, len(groups))


def _stress_vowel_index(word: str) -> int:
    w = word.lower()
    positions = [i for i, ch in enumerate(w) if ch in VOWELS]
    if not positions:
        return max(0, len(w) - 1)

    accented = [i for i, ch in enumerate(w) if ch in ACCENTED_VOWELS]
    if accented:
        return accented[-1]

    if (
        w.endswith(("a", "e", "o", "as", "es", "os", "am", "em", "ens"))
        and len(positions) >= 2
    ):
        return positions[-2]
    return positions[-1]


def _to_tokens(text: str) -> list[str]:
    t = text.lower()
    out: list[str] = []
    i = 0
    while i < len(t):
        pair = t[i : i + 2]
        if pair in _DIGRAPHS:
            mapped = _DIGRAPHS[pair]
            if mapped:
                out.append(mapped)
            i += 2
            continue
        ch = t[i]
        mapped = _SINGLE.get(ch, ch)
        if mapped:
            out.append(mapped)
        i += 1
    return out


def phones_for_word(word: str) -> str:
    return " ".join(_to_tokens(word))


def rhyme_key(word: str) -> str:
    w = word.strip().lower()
    if not w:
        return ""
    stress = _stress_vowel_index(w)
    tail = w[stress:]
    return " ".join(_to_tokens(tail))


def word_to_ipa(word: str) -> str:
    inner = " ".join(_to_tokens(word))
    return f"/{inner}/"
