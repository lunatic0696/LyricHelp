"""Brazilian Portuguese phonetics for rhyme matching.

Implements grapheme-to-phoneme (G2P) conversion, stress detection, syllable
counting, and rhyme key extraction following Brazilian Portuguese grammar and
phonology. Completely independent from the English/CMU-ARPABET pipeline.

Phonological features captured:
- Portuguese stress rules (paroxítona/oxítona by word ending, explicit accents)
- Nasal vowels: ã, õ, and V + m/n before consonant
- Nasal diphthongs: ão /ɐ̃w̃/, ãe /ɐ̃j̃/, õe /õj̃/
- Word-final nasal endings: -am /ɐ̃w̃/, -em /ẽj̃/, -im /ĩ/, -om /õ/, -um /ũ/
- Palatalization: /t/ → /tʃ/, /d/ → /dʒ/ before /i/ (Brazilian)
- Vowel reduction: final unstressed a → /ɐ/, e → /i/, o → /u/
- Digraphs: lh /ʎ/, nh /ɲ/, ch /ʃ/, rr /ʁ/, ss /s/, qu, gu
- L-vocalization at syllable end: /l/ → /w/
- Open/closed mid vowels distinguished by accent (é/ê, ó/ô)
- Hiatus vs diphthong disambiguation (i/u + nh/lh → hiatus)

References:
- Bechara, E. "Moderna Gramática Portuguesa" (stress rules, accent)
- Cunha & Cintra, "Nova Gramática do Português Contemporâneo"
- Cristófaro Silva, T. "Fonética e Fonologia do Português Brasileiro"

Rhyme matching levels:
- Perfect (rima consoante): identical phonetic tail from the stressed vowel.
- Assonant (rima toante): same vowel sequence in the rhyme tail.
"""

from __future__ import annotations

import re
from typing import List, Tuple

# --- Character classes -------------------------------------------------------

STRESS_ACCENTS = set("áéíóúâêô")          # explicit stress accents
NASAL_TILDE = set("ãõ")                    # nasal + (usually) stress
OTHER_ACCENTS = set("àü")                  # grave / diaeresis (no stress)
ACCENTED_VOWELS = STRESS_ACCENTS | NASAL_TILDE | OTHER_ACCENTS
PLAIN_VOWELS = set("aeiou")
VOWELS = PLAIN_VOWELS | ACCENTED_VOWELS
STRONG_VOWELS = set("aeoáéóâêôãõà")
WEAK_UNACCENTED = {"i", "u"}
CONSONANT_CHARS = set("bcdfghjklmnpqrstvwxyzç")

VALID_WORD_RE = re.compile(r"^[a-záéíóúâêôãõàüç'\-]+$")


# --- Word validation ---------------------------------------------------------

def is_valid_word(word: str) -> bool:
    w = word.strip().lower()
    if len(w) < 2:
        return False
    if not VALID_WORD_RE.match(w):
        return False
    return any(c in VOWELS for c in w)


def _clean(word: str) -> str:
    return word.strip().lower().replace("-", "").replace("'", "")


def _deaccent(c: str) -> str:
    return {
        "á": "a", "à": "a", "â": "a", "ã": "a",
        "é": "e", "ê": "e",
        "í": "i",
        "ó": "o", "ô": "o", "õ": "o",
        "ú": "u", "ü": "u",
    }.get(c, c)


# --- Syllable nuclei ---------------------------------------------------------

def _is_diphthong_at(w: str, i: int) -> bool:
    """
    Return True if w[i] and w[i+1] form a single syllable nucleus (diphthong).

    Falling diphthongs (strong + weak unaccented): ai, ei, oi, ui*, au, eu, iu, ou
    Nasal diphthongs: ão, ãe, õe
    Hiatus exception: weak vowel (i/u) before nh/lh → hiatus (e.g. "rainha")
    """
    if i + 1 >= len(w):
        return False
    v1, v2 = w[i], w[i + 1]
    if v1 not in VOWELS or v2 not in VOWELS:
        return False

    # Nasal diphthongs
    if v1 == "ã" and v2 in {"o", "e"}:
        return True
    if v1 == "õ" and v2 == "e":
        return True

    # Falling diphthong: strong + weak unaccented
    if v1 in STRONG_VOWELS and v2 in WEAK_UNACCENTED:
        # Hiatus exception: i/u + nh or lh
        if i + 3 < len(w) and w[i + 2] in "nl" and w[i + 3] == "h":
            return False
        # Hiatus exception: accented weak vowel (not possible here since v2 is plain)
        return True

    return False


def syllable_peaks(word: str) -> List[int]:
    """Return character indices where each syllable's vowel nucleus begins."""
    w = _clean(word)
    peaks: List[int] = []
    i = 0
    n = len(w)
    while i < n:
        if w[i] not in VOWELS:
            i += 1
            continue
        peaks.append(i)
        if _is_diphthong_at(w, i):
            # Consume diphthong's second vowel
            i += 2
            # Triphthong (uai, uei, etc.) — very rare; usually 'ua/ue' before 'i'
            if i < n and w[i] in VOWELS and _is_diphthong_at(w, i - 1):
                i += 1
            continue
        i += 1
    return peaks


def _nucleus_end(w: str, start: int) -> int:
    """End index (exclusive) of the nucleus starting at `start`."""
    if start >= len(w) or w[start] not in VOWELS:
        return start
    end = start + 1
    if _is_diphthong_at(w, start):
        end += 1
        # Triphthong check
        if end < len(w) and w[end] in VOWELS and _is_diphthong_at(w, end - 1):
            end += 1
    return end


def syllable_count(word: str) -> int:
    return max(1, len(syllable_peaks(word)))


# --- Stress detection --------------------------------------------------------

def find_stressed_peak(word: str) -> int:
    """Return the index (in `syllable_peaks`) of the stressed syllable."""
    w = _clean(word)
    peaks = syllable_peaks(w)
    if not peaks:
        return -1
    if len(peaks) == 1:
        return 0

    # 1) Explicit stress accent (á, é, í, ó, ú, â, ê, ô)
    for idx in range(len(peaks) - 1, -1, -1):
        pos = peaks[idx]
        end = _nucleus_end(w, pos)
        for p in range(pos, end):
            if w[p] in STRESS_ACCENTS:
                return idx

    # 2) Nasal tilde (ã, õ) — marks stress in absence of explicit accent
    for idx in range(len(peaks) - 1, -1, -1):
        pos = peaks[idx]
        end = _nucleus_end(w, pos)
        for p in range(pos, end):
            if w[p] in NASAL_TILDE:
                return idx

    # 3) Ending rules: paroxítona vs oxítona
    last = w[-1]
    last2 = w[-2:] if len(w) >= 2 else w
    last3 = w[-3:] if len(w) >= 3 else w

    # Paroxítona (penultimate stress):
    #   ends in vowel a/e/o (± final s)
    #   ends in -am / -em / -ens (verbal endings)
    paroxitona = False
    if last in {"a", "e", "o"}:
        paroxitona = True
    elif last == "s" and len(w) >= 2 and w[-2] in {"a", "e", "o"}:
        paroxitona = True
    elif last2 in {"am", "em"}:
        paroxitona = True
    elif last3 == "ens":
        paroxitona = True

    if paroxitona:
        return max(0, len(peaks) - 2)

    # Oxítona (last syllable stressed): i, u, l, r, z, and other consonants
    return len(peaks) - 1


# --- Grapheme-to-phoneme -----------------------------------------------------

VOWEL_PHONES = {
    "a", "ɐ", "ɐ̃", "e", "ẽ", "ɛ", "i", "ĩ", "o", "õ", "ɔ", "u", "ũ",
    "w", "w̃", "j", "j̃",
}


def _is_vowel_phone(p: str) -> bool:
    return p in VOWEL_PHONES


def _vowel_phone(ch: str, is_stress: bool, is_end: bool, is_pre_final_s: bool) -> str:
    """Phone for a single vowel grapheme outside nasal contexts."""
    if ch == "á" or ch == "à":
        return "a"
    if ch == "â":
        return "ɐ"
    if ch == "ã":
        return "ɐ̃"
    if ch == "é":
        return "ɛ"
    if ch == "ê":
        return "e"
    if ch == "í":
        return "i"
    if ch == "ó":
        return "ɔ"
    if ch == "ô":
        return "o"
    if ch == "õ":
        return "õ"
    if ch == "ú" or ch == "ü":
        return "u"
    if ch == "a":
        if (is_end or is_pre_final_s) and not is_stress:
            return "ɐ"
        return "a"
    if ch == "e":
        if (is_end or is_pre_final_s) and not is_stress:
            return "i"  # BR final -e → /i/
        return "e"
    if ch == "i":
        return "i"
    if ch == "o":
        if (is_end or is_pre_final_s) and not is_stress:
            return "u"  # BR final -o → /u/
        return "o"
    if ch == "u":
        return "u"
    return ch


def _consonant_phone(ch: str, prev_ch: str, next_ch: str, next2: str, i: int, n: int) -> str:
    if ch == "b":
        return "b"
    if ch == "c":
        return "s" if next_ch in {"e", "i", "é", "ê", "í"} else "k"
    if ch == "ç":
        return "s"
    if ch == "d":
        # BR palatalization: /d/ → /dʒ/ before /i/ (incl. final -de = /dʒi/)
        if next_ch in {"i", "í"}:
            return "dʒ"
        if next_ch == "e" and i + 2 == n:
            return "dʒ"
        return "d"
    if ch == "f":
        return "f"
    if ch == "g":
        return "ʒ" if next_ch in {"e", "i", "é", "ê", "í"} else "g"
    if ch == "h":
        return ""
    if ch == "j":
        return "ʒ"
    if ch == "k":
        return "k"
    if ch == "l":
        # L-vocalization at syllable end in BR: /l/ → /w/
        if next_ch == "" or next_ch not in VOWELS:
            return "w"
        return "l"
    if ch == "m":
        return "m"
    if ch == "n":
        return "n"
    if ch == "p":
        return "p"
    if ch == "q":
        return "k"
    if ch == "r":
        # Strong /ʁ/ word-initial or after n/l/s/m
        if i == 0 or prev_ch in {"n", "l", "s", "m", "r"}:
            return "ʁ"
        # Otherwise tap /ɾ/ (intervocalic or syllable-final in BR)
        return "ɾ"
    if ch == "s":
        if prev_ch in VOWELS and next_ch in VOWELS:
            return "z"
        return "s"
    if ch == "t":
        # BR palatalization: /t/ → /tʃ/ before /i/
        if next_ch in {"i", "í"}:
            return "tʃ"
        if next_ch == "e" and i + 2 == n:
            return "tʃ"
        return "t"
    if ch == "v":
        return "v"
    if ch == "w":
        return "w"
    if ch == "x":
        # Complex; default /ʃ/. Accurate only via per-word lexicon.
        return "ʃ"
    if ch == "y":
        return "i"
    if ch == "z":
        if i == n - 1:
            return "s"  # BR final -z often devoices to /s/
        return "z"
    return ""


def word_to_phones(word: str) -> Tuple[List[str], int]:
    """
    Convert a PT-BR word to IPA-like phone tokens along with the index of the
    stressed vowel phone within the returned list.
    """
    w = _clean(word)
    peaks = syllable_peaks(w)
    stressed_peak = find_stressed_peak(w)
    stress_char_pos = peaks[stressed_peak] if stressed_peak >= 0 else -1

    phones: List[str] = []
    stressed_phone_index = -1

    def emit(phone: str, is_stressed_vowel: bool = False) -> None:
        nonlocal stressed_phone_index
        if phone == "":
            return
        if is_stressed_vowel and stressed_phone_index < 0:
            stressed_phone_index = len(phones)
        phones.append(phone)

    n = len(w)
    i = 0

    while i < n:
        ch = w[i]
        next_ch = w[i + 1] if i + 1 < n else ""
        next2 = w[i + 2] if i + 2 < n else ""
        prev_ch = w[i - 1] if i > 0 else ""
        is_stress_pos = (i == stress_char_pos)
        is_end = (i == n - 1)
        is_pre_final_s = (i == n - 2 and next_ch == "s")

        # --- Nasal diphthongs (ão, ãe, õe) ---
        if ch == "ã" and next_ch == "o":
            emit("ɐ̃", is_stress_pos)
            emit("w̃")
            i += 2
            continue
        if ch == "ã" and next_ch == "e":
            emit("ɐ̃", is_stress_pos)
            emit("j̃")
            i += 2
            continue
        if ch == "õ" and next_ch == "e":
            emit("õ", is_stress_pos)
            emit("j̃")
            i += 2
            continue

        # --- Word-final V + m (am, em, im, om, um) ---
        if ch in VOWELS and next_ch == "m" and i + 2 == n:
            plain = _deaccent(ch)
            if plain == "a":
                emit("ɐ̃", is_stress_pos)
                emit("w̃")
            elif plain == "e":
                emit("ẽ", is_stress_pos)
                emit("j̃")
            elif plain == "i":
                emit("ĩ", is_stress_pos)
            elif plain == "o":
                emit("õ", is_stress_pos)
            elif plain == "u":
                emit("ũ", is_stress_pos)
            i += 2
            continue

        # --- Word-final V + ns (-ens, -ans, etc.) ---
        if ch in VOWELS and next_ch == "n" and next2 == "s" and i + 3 == n:
            plain = _deaccent(ch)
            if plain == "e":
                emit("ẽ", is_stress_pos)
                emit("j̃")
                emit("s")
            elif plain in {"a", "i", "o", "u"}:
                nasal = {"a": "ɐ̃", "i": "ĩ", "o": "õ", "u": "ũ"}[plain]
                emit(nasal, is_stress_pos)
                emit("s")
            else:
                # Fallback
                emit(plain, is_stress_pos)
                emit("n")
                emit("s")
            i += 3
            continue

        # --- Vowel + m/n + consonant → nasalize (not nh digraph) ---
        if ch in VOWELS and next_ch in {"m", "n"} and i + 2 < n:
            third = w[i + 2]
            is_nh = (next_ch == "n" and third == "h")
            if not is_nh and third not in VOWELS:
                plain = _deaccent(ch)
                nasal_map = {"a": "ɐ̃", "e": "ẽ", "i": "ĩ", "o": "õ", "u": "ũ"}
                # Preserve accent-derived qualities where meaningful
                if ch == "ê":
                    emit("ẽ", is_stress_pos)
                elif ch == "ô":
                    emit("õ", is_stress_pos)
                elif ch == "â":
                    emit("ɐ̃", is_stress_pos)
                else:
                    emit(nasal_map.get(plain, plain), is_stress_pos)
                i += 2  # consume the m/n
                continue

        # --- Plain vowel ---
        if ch in VOWELS:
            phone = _vowel_phone(ch, is_stress_pos, is_end, is_pre_final_s)
            emit(phone, is_stress_pos)
            i += 1
            continue

        # --- Consonant digraphs ---
        if ch == "l" and next_ch == "h":
            emit("ʎ")
            i += 2
            continue
        if ch == "n" and next_ch == "h":
            emit("ɲ")
            i += 2
            continue
        if ch == "c" and next_ch == "h":
            emit("ʃ")
            i += 2
            continue
        if ch == "r" and next_ch == "r":
            emit("ʁ")
            i += 2
            continue
        if ch == "s" and next_ch == "s":
            emit("s")
            i += 2
            continue
        if ch == "q" and next_ch == "u":
            # qu + e/i → /k/; qu + a/o → /kw/
            if next2 in {"e", "i", "é", "ê", "í"}:
                emit("k")
                i += 2
                continue
            emit("k")
            emit("w")
            i += 2
            continue
        if ch == "g" and next_ch == "u":
            if next2 in {"e", "i", "é", "ê", "í"}:
                emit("g")
                i += 2
                continue
            emit("g")
            emit("w")
            i += 2
            continue

        # --- Single consonant ---
        phone = _consonant_phone(ch, prev_ch, next_ch, next2, i, n)
        if phone:
            emit(phone)
        i += 1

    # Safety: if we somehow missed the stress marker, mark the last vowel phone
    if stressed_phone_index < 0:
        for idx in range(len(phones) - 1, -1, -1):
            if _is_vowel_phone(phones[idx]):
                stressed_phone_index = idx
                break

    return phones, stressed_phone_index


# --- Rhyme keys --------------------------------------------------------------

def rhyme_phones(word: str) -> List[str]:
    """Phones from the stressed vowel onward (the rhyme tail)."""
    phones, stress = word_to_phones(word)
    if stress < 0:
        return list(phones)
    return phones[stress:]


def rhyme_key(word: str) -> str:
    """
    Canonical perfect-rhyme key: the full phonetic tail from the stressed vowel.
    Two words with the same rhyme_key form a rima perfeita (consoante).
    """
    tail = rhyme_phones(word)
    key = "".join(tail)
    return key[:120]  # fits the DB column


def assonance_key(word: str) -> str:
    """
    Assonant rhyme key: the vowel sequence of the rhyme tail.
    Two words sharing this key (but not rhyme_key) form a rima toante:
    same stressed vowel and same vowel pattern across remaining syllables.
    """
    tail = rhyme_phones(word)
    vowels = [p for p in tail if _is_vowel_phone(p)]
    key = "".join(vowels)
    return key[:12]


def stressed_vowel_key(word: str) -> str:
    """The stressed vowel alone — broad partial lookup (same tonic vowel)."""
    tail = rhyme_phones(word)
    for p in tail:
        if _is_vowel_phone(p):
            return p[:24]
    return ""


def tail_syllable_count(word: str) -> int:
    """Number of syllables from the stressed syllable to the end, inclusive."""
    stressed = find_stressed_peak(word)
    if stressed < 0:
        return 1
    total = syllable_count(word)
    return max(1, total - stressed)


def rhyme_index_keys(word: str) -> Tuple[str, str]:
    """
    Return (assonance_key, assonance_key#tail_syllables) used for index lookup.

    - First value: vowel skeleton of the rhyme tail (assonance_key).
    - Second value: the skeleton plus "#N" where N is how many syllables the
      tail spans. This lets us distinguish same-vowel-different-length matches
      (e.g. tempo [ẽu, 2 syl] vs canção [ɐ̃w̃, 1 syl]).
    """
    skeleton = assonance_key(word)
    tail_syl = tail_syllable_count(word)
    tagged = f"{skeleton}#{tail_syl}"[:24]
    return skeleton, tagged


# --- Display helpers ---------------------------------------------------------

def phones_for_word(word: str) -> str:
    phones, _ = word_to_phones(word)
    return " ".join(phones)[:200]


def word_to_ipa(word: str) -> str:
    phones, stress = word_to_phones(word)
    if stress >= 0:
        parts = list(phones)
        parts[stress] = "ˈ" + parts[stress]
        inner = "".join(parts)
    else:
        inner = "".join(phones)
    return ("/" + inner + "/")[:300]
