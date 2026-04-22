"""
Phonetic utilities: CMU ARPABET parsing, rhyme tail (stressed vowel + coda), syllable count,
and ARPABET-to-IPA rendering for display. Rhyme logic uses phoneme strings derived
from the CMU Pronouncing Dictionary (same source as standard IPA transcriptions).

Rhyme rules (English, per Wikipedia / American Heritage Dictionary / Wiktionary):
- Perfect rhyme (full / exact / true rhyme): identical stressed vowel AND all
  subsequent phonemes; onset of the stressed syllable must differ.
- Half / slant / near rhyme: same final coda consonants OR same stressed vowel
  (assonance), but not both — Poetry Foundation, Literary Devices.

CMU stress markers: 0 = unstressed, 1 = primary, 2 = secondary. For rhyme
matching, levels 1 and 2 are treated as equivalent: a secondary-stressed vowel
followed by consonants (e.g. ``microwave`` /EY2 V/) perfect-rhymes with a
primary-stressed counterpart (``save`` /EY1 V/). This matches the guidance in
the UBC Poetry Form Checker assignment and the synthesis across multiple
academic and pedagogical sources ("stress level (1 vs 2) on that vowel does not
need to match").

Consequence for the stored ``rhyme_key``: we strip the numeric stress digit on
every phone in the tail so two words that share the stressed-vowel-onwards
phonemes compare equal as strings. The stress marker is still used *internally*
when locating the tail (we start from the last vowel bearing 1 or 2).
"""
from __future__ import annotations

import re
from typing import List, Tuple

_VOWEL_SUFFIX = re.compile(r"^[A-Z]{1,2}[012]$")


def _is_vowel_phone(phone: str) -> bool:
    return bool(_VOWEL_SUFFIX.match(phone))


def split_phones(phones_str: str) -> List[str]:
    return phones_str.upper().split()


def _strip_stress(phone: str) -> str:
    """Return the phone without its trailing CMU stress digit (0/1/2)."""
    if phone and phone[-1] in "012":
        return phone[:-1]
    return phone


def syllable_count(phones_str: str) -> int:
    """Count syllables: each CMU vowel token ends with 0, 1, or 2."""
    return sum(1 for p in split_phones(phones_str) if _is_vowel_phone(p))


def rhyming_part(phones_str: str) -> str:
    """
    Return the rhyme tail (ARPABET, stress-digits stripped).

    The tail starts at the last vowel that carries stress (primary=1 or
    secondary=2); if the word has no stressed vowel, we fall back to the last
    vowel of any kind. Stress digits are removed from every phone in the
    returned tail so that, e.g., ``EY2 V`` and ``EY1 V`` compare as equal
    strings and ``microwave`` can perfect-rhyme with ``save``.
    """
    phones = split_phones(phones_str)
    if not phones:
        return ""

    start = -1
    for i in range(len(phones) - 1, -1, -1):
        p = phones[i]
        if _is_vowel_phone(p) and p[-1] in "12":
            start = i
            break

    if start < 0:
        for i in range(len(phones) - 1, -1, -1):
            p = phones[i]
            if _is_vowel_phone(p):
                start = i
                break

    if start < 0:
        return " ".join(_strip_stress(p) for p in phones)

    return " ".join(_strip_stress(p) for p in phones[start:])


def longest_common_suffix_len(a: List[str], b: List[str]) -> int:
    i, j = len(a) - 1, len(b) - 1
    n = 0
    while i >= 0 and j >= 0 and a[i] == b[j]:
        n += 1
        i -= 1
        j -= 1
    return n


def is_perfect_rhyme(query_key: str, candidate_key: str) -> bool:
    return query_key == candidate_key and query_key != ""


def is_partial_rhyme(query_key: str, candidate_key: str) -> bool:
    if query_key == candidate_key:
        return False
    a = query_key.split()
    b = candidate_key.split()
    if not a or not b:
        return False
    lcs = longest_common_suffix_len(a, b)
    if lcs == 0:
        return False
    shorter = min(len(a), len(b))
    # Compatible but not full: meaningful overlap on the rhyme tail
    return lcs >= min(2, shorter) or (
        lcs == 1 and len(a) >= 2 and len(b) >= 2
    )


def match_score(query_key: str, candidate_key: str, query_syl: int, cand_syl: int) -> float:
    """Higher is better for ranking best matches."""
    a = query_key.split()
    b = candidate_key.split()
    lcs = longest_common_suffix_len(a, b)
    perfect = query_key == candidate_key and query_key
    syl_pen = abs(query_syl - cand_syl)
    if perfect:
        return 1000.0 - syl_pen * 5.0
    if lcs == 0:
        return -1.0
    overlap = lcs / max(len(a), len(b), 1)
    return 300.0 * overlap + 50.0 * (lcs / max(len(b), 1)) - syl_pen * 8.0


# ARPABET (CMU) to IPA (broad American English). Stress encoded on vowel digits.
_BASE_VOWELS: dict[str, Tuple[str, str, str]] = {
    # base -> (ipa_0 unstressed-ish, ipa_1 primary, ipa_2 secondary)
    "AA": ("ɑ", "ɑ", "ɑ"),
    "AE": ("æ", "æ", "æ"),
    "AH": ("ə", "ʌ", "ʌ"),
    "AO": ("ɔ", "ɔ", "ɔ"),
    "AW": ("aʊ", "aʊ", "aʊ"),
    "AY": ("aɪ", "aɪ", "aɪ"),
    "EH": ("ɛ", "ɛ", "ɛ"),
    "ER": ("ɚ", "ɝ", "ɝ"),
    "EY": ("eɪ", "eɪ", "eɪ"),
    "IH": ("ɪ", "ɪ", "ɪ"),
    "IY": ("i", "i", "i"),
    "OW": ("oʊ", "oʊ", "oʊ"),
    "OY": ("ɔɪ", "ɔɪ", "ɔɪ"),
    "UH": ("ʊ", "ʊ", "ʊ"),
    "UW": ("u", "u", "u"),
}

_CONSONANTS = {
    "B": "b",
    "CH": "tʃ",
    "D": "d",
    "DH": "ð",
    "F": "f",
    "G": "ɡ",
    "HH": "h",
    "JH": "dʒ",
    "K": "k",
    "L": "l",
    "M": "m",
    "N": "n",
    "NG": "ŋ",
    "P": "p",
    "R": "ɹ",
    "S": "s",
    "SH": "ʃ",
    "T": "t",
    "TH": "θ",
    "V": "v",
    "W": "w",
    "Y": "j",
    "Z": "z",
    "ZH": "ʒ",
}


def _phone_to_ipa(phone: str) -> str:
    p = phone.upper().strip()
    if _is_vowel_phone(p):
        base = p[:-1]
        stress = p[-1]
        triple = _BASE_VOWELS.get(base)
        if not triple:
            return p.lower()
        u, one, two = triple
        if stress == "0":
            return u
        if stress == "1":
            return "ˈ" + one
        return "ˌ" + two
    return _CONSONANTS.get(p, p.lower())


def phones_to_ipa(phones_str: str) -> str:
    """Space-separated IPA chunks; wrapped in slashes for display."""
    parts = [_phone_to_ipa(x) for x in split_phones(phones_str)]
    inner = " ".join(parts)
    return f"/{inner}/"


def rhyme_tail_to_ipa(rhyme_arpabet: str) -> str:
    return phones_to_ipa(rhyme_arpabet)


def rhyme_tail_keys(rhyme_key: str) -> Tuple[str, str]:
    """Return (last_phone, last_two_phones_or_single) for indexing."""
    parts = rhyme_key.split()
    if not parts:
        return "", ""
    last1 = parts[-1]
    if len(parts) >= 2:
        last2 = f"{parts[-2]} {parts[-1]}"
    else:
        last2 = last1
    return last1, last2


def parse_cmudict_line(line: str) -> Tuple[str, str] | None:
    """
    Parse one data line from cmudict. Returns (word_lower, phones) or None.
    Skips comment lines and variant markers beyond the first field.
    """
    line = line.strip()
    if not line or line.startswith(";;;"):
        return None
    if "(" in line.split()[0]:
        # e.g. WORD(2) — variant; still valid
        pass
    parts = line.split()
    if len(parts) < 2:
        return None
    raw_word = parts[0]
    word = re.sub(r"\(\d+\)$", "", raw_word).lower()
    phones = " ".join(parts[1:])
    return word, phones
