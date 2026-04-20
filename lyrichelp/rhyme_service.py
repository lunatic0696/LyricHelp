from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Set, Tuple

from django.db.models import Q

from . import phonetics
from .models import DictionaryWord


@dataclass(frozen=True)
class RhymeHit:
    word: str
    ipa: str
    syllables: int
    rhyme_key: str
    perfect: bool
    score: float


def lookup_query_entry(word: str, *, language: str = "en") -> DictionaryWord | None:
    w = word.strip().lower()
    if not w:
        return None
    return DictionaryWord.objects.filter(language=language, word=w).first()


def collect_candidates(
    query: DictionaryWord,
    *,
    language: str = "en",
    max_partial_scan: int = 12000,
) -> List[RhymeHit]:
    q_key = query.rhyme_key
    q_syl = query.syllables
    q_word = query.word
    last1 = query.rhyme_last1
    last2 = query.rhyme_last2

    hits: List[RhymeHit] = []

    qs_perfect = (
        DictionaryWord.objects.filter(language=language, rhyme_key=q_key)
        .exclude(word=q_word)
        .values_list("word", "ipa_full", "syllables", "rhyme_key")
    )
    for word, ipa, syl, cand_key in qs_perfect:
        hits.append(
            RhymeHit(
                word=word,
                ipa=ipa,
                syllables=syl,
                rhyme_key=cand_key,
                perfect=True,
                score=phonetics.match_score(q_key, cand_key, q_syl, syl),
            )
        )

    partial_qs = (
        DictionaryWord.objects.filter(language=language).filter(
            Q(rhyme_last1=last1) | Q(rhyme_last2=last2)
        )
        .exclude(rhyme_key=q_key)
        .exclude(word=q_word)
        .distinct()
    )[:max_partial_scan]

    for row in partial_qs.iterator():
        if not phonetics.is_partial_rhyme(q_key, row.rhyme_key):
            continue
        hits.append(
            RhymeHit(
                word=row.word,
                ipa=row.ipa_full,
                syllables=row.syllables,
                rhyme_key=row.rhyme_key,
                perfect=False,
                score=phonetics.match_score(q_key, row.rhyme_key, q_syl, row.syllables),
            )
        )

    return hits


@dataclass
class SyllableSection:
    syllables: int
    perfect: List[RhymeHit]
    partial: List[RhymeHit]


@dataclass
class RhymeResultBundle:
    query_word: str
    query_ipa: str
    query_syllables: int
    best_matches: List[RhymeHit]
    by_syllable: List[SyllableSection]


def build_result_bundle(query: DictionaryWord, hits: Sequence[RhymeHit]) -> RhymeResultBundle:
    """
    Assign each word to at most one place: best matches (up to 20), then syllable buckets.
    """
    by_word: Dict[str, RhymeHit] = {}
    for h in hits:
        if h.word not in by_word or h.score > by_word[h.word].score:
            by_word[h.word] = h

    unique = list(by_word.values())
    unique.sort(
        key=lambda x: (x.score, 1 if x.perfect else 0),
        reverse=True,
    )

    used: Set[str] = set()
    best = [h for h in unique if h.score > 0][:20]
    for h in best:
        used.add(h.word)

    perfect_map: Dict[int, List[RhymeHit]] = {}
    partial_map: Dict[int, List[RhymeHit]] = {}

    q_key = query.rhyme_key
    for h in unique:
        if h.word in used:
            continue
        syl = h.syllables
        if h.perfect:
            perfect_map.setdefault(syl, []).append(h)
        elif phonetics.is_partial_rhyme(q_key, h.rhyme_key):
            partial_map.setdefault(syl, []).append(h)

    for m in perfect_map.values():
        m.sort(key=lambda x: x.word)
    for m in partial_map.values():
        m.sort(key=lambda x: x.word)

    syllables_order = sorted(
        set(perfect_map.keys()) | set(partial_map.keys()),
    )

    sections: List[SyllableSection] = []
    for syl in syllables_order:
        perf = [x for x in perfect_map.get(syl, []) if x.word not in used]
        for x in perf:
            used.add(x.word)
        part = [
            x
            for x in partial_map.get(syl, [])
            if x.word not in used and phonetics.is_partial_rhyme(q_key, x.rhyme_key)
        ]
        for x in part:
            used.add(x.word)
        if perf or part:
            sections.append(SyllableSection(syllables=syl, perfect=perf, partial=part))

    return RhymeResultBundle(
        query_word=query.word,
        query_ipa=query.ipa_full,
        query_syllables=query.syllables,
        best_matches=best,
        by_syllable=sections,
    )


def autocomplete_suggestions(q: str, *, language: str = "en", limit: int = 12) -> List[Tuple[str, str]]:
    """Return (word, ipa) pairs ordered by relevance."""
    q = q.strip().lower()
    if len(q) < 1:
        return []

    base = (
        DictionaryWord.objects.filter(language=language, word__istartswith=q)
        .values_list("word", "ipa_full")[: limit * 2]
    )
    rows = list(base)
    rows.sort(key=lambda t: (len(t[0]), t[0]))
    out: List[Tuple[str, str]] = []
    seen: Set[str] = set()
    for w, ipa in rows:
        if w in seen:
            continue
        seen.add(w)
        out.append((w, ipa))
        if len(out) >= limit:
            break

    if len(out) < limit and len(q) >= 2:
        rest = limit - len(out)
        fuzzy = (
            DictionaryWord.objects.filter(language=language, word__icontains=q)
            .exclude(word__in=seen)
            .values_list("word", "ipa_full")[: rest * 3]
        )
        fuzzy_l = sorted(fuzzy, key=lambda t: (len(t[0]), t[0]))
        for w, ipa in fuzzy_l:
            if w in seen:
                continue
            seen.add(w)
            out.append((w, ipa))
            if len(out) >= limit:
                break

    return out
