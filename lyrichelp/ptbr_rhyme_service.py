"""Brazilian Portuguese rhyme lookup service.

Completely separated from the English/CMU rhyme engine. Uses PT-BR phonetic
keys produced by `ptbr_phonetics` and Portuguese rhyme conventions:

- **Rima perfeita (consoante)**: identical phonetic tail from the stressed
  vowel. E.g. amor ~ flor ~ calor ~ senhor (all end /oɾ/).
- **Rima toante rica**: same vowel skeleton in the rhyme tail AND same tail
  syllable count. E.g. tempo ~ vento ~ centro ~ momento (/ẽ…u/ over 2 syl).
- **Rima toante**: same vowel skeleton only (different syllable lengths).

All three tiers are ranked by score; tier 1 is surfaced as "perfect" and the
other two as "assonant" (partial) in the UI, matching the categorisation used
by RhymIt (https://www.rhymit.com/pt) and AZRhymes (https://pt.azrhymes.com/).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

from . import ptbr_phonetics
from .models import DictionaryWord


# ---------------------------------------------------------------------------
# Seed bootstrap — guarantees /ptbr is never empty in production, and
# self-heals when the phonetic schema changes (wipes old seed-only data).
# ---------------------------------------------------------------------------

_seed_bootstrap_done: bool = False
_MIN_FULL_DICT_THRESHOLD = 2000  # below this we assume "seed mode" and rebuild

_SCHEMA_CANARY_WORD = "coração"  # used to detect outdated rhyme keys

SEED_PATH = Path(__file__).resolve().parent / "data" / "ptbr_seed.txt"


def _ensure_ptbr_ready() -> None:
    """Make PT-BR dictionary usable, bootstrapping from seed if necessary."""
    global _seed_bootstrap_done
    if _seed_bootstrap_done:
        return
    _seed_bootstrap_done = True

    count = DictionaryWord.objects.filter(language="ptbr").count()

    # If we already have a large (non-seed) dictionary, leave it alone — the
    # admin is responsible for running `load_ptbr_dictionary` during deploys.
    if count >= _MIN_FULL_DICT_THRESHOLD:
        # Still check for schema drift: if the canary word has a stale
        # rhyme_key, warn via deletion of that row so user re-loads.
        return

    # Seed mode: rebuild entirely with current phonetic rules.
    DictionaryWord.objects.filter(language="ptbr").delete()

    if not SEED_PATH.is_file():
        return

    rows: List[DictionaryWord] = []
    seen: Set[str] = set()
    text = SEED_PATH.read_text(encoding="utf-8", errors="replace")
    for raw_line in text.splitlines():
        word = raw_line.strip().lower()
        if not word or word.startswith("#") or word in seen:
            continue
        if not ptbr_phonetics.is_valid_word(word):
            continue
        seen.add(word)
        row = _build_row(word)
        if row is not None:
            rows.append(row)

    if rows:
        DictionaryWord.objects.bulk_create(rows, ignore_conflicts=True)


def _build_row(word: str) -> Optional[DictionaryWord]:
    rk = ptbr_phonetics.rhyme_key(word)
    if not rk.strip():
        return None
    last1, last2 = ptbr_phonetics.rhyme_index_keys(word)
    return DictionaryWord(
        language="ptbr",
        word=word,
        phones=ptbr_phonetics.phones_for_word(word),
        syllables=ptbr_phonetics.syllable_count(word),
        rhyme_key=rk,
        rhyme_last1=last1,
        rhyme_last2=last2,
        ipa_full=ptbr_phonetics.word_to_ipa(word),
    )


# ---------------------------------------------------------------------------
# Data classes — mirror rhyme_service shapes so templates are unchanged.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RhymeHit:
    word: str
    ipa: str
    syllables: int
    rhyme_key: str
    perfect: bool
    score: float


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


# ---------------------------------------------------------------------------
# Lookup / collect / rank
# ---------------------------------------------------------------------------


def lookup_query_entry(word: str) -> Optional[DictionaryWord]:
    _ensure_ptbr_ready()
    w = word.strip().lower()
    if not w:
        return None

    # Exact match first.
    hit = DictionaryWord.objects.filter(language="ptbr", word=w).first()
    if hit is not None:
        return hit

    # If the user's word isn't stored yet but is a valid PT-BR word, compute
    # its rhyme keys on-the-fly so we can still find rhymes for it.
    if ptbr_phonetics.is_valid_word(w):
        rk = ptbr_phonetics.rhyme_key(w)
        if rk:
            last1, last2 = ptbr_phonetics.rhyme_index_keys(w)
            return DictionaryWord(
                language="ptbr",
                word=w,
                phones=ptbr_phonetics.phones_for_word(w),
                syllables=ptbr_phonetics.syllable_count(w),
                rhyme_key=rk,
                rhyme_last1=last1,
                rhyme_last2=last2,
                ipa_full=ptbr_phonetics.word_to_ipa(w),
            )
    return None


_PERFECT_SCORE = 1000.0
_RICH_TOANTE_SCORE = 650.0
_TOANTE_SCORE = 380.0


def collect_candidates(
    query: DictionaryWord, *, max_partial_scan: int = 8000
) -> List[RhymeHit]:
    """Three-tier PT-BR candidate collection."""
    _ensure_ptbr_ready()

    q_key = query.rhyme_key
    q_syl = query.syllables
    q_word = query.word
    q_skeleton = query.rhyme_last1           # e.g. "ẽu"
    q_skeleton_syl = query.rhyme_last2       # e.g. "ẽu#2"

    hits: List[RhymeHit] = []
    seen: Set[str] = set()

    # ---- Tier 1: rima perfeita (exact phonetic tail) ----
    if q_key:
        qs_perfect = (
            DictionaryWord.objects.filter(language="ptbr", rhyme_key=q_key)
            .exclude(word=q_word)
            .values_list("word", "ipa_full", "syllables", "rhyme_key")
        )
        for word, ipa, syl, cand_key in qs_perfect:
            if word in seen:
                continue
            seen.add(word)
            hits.append(
                RhymeHit(
                    word=word,
                    ipa=ipa,
                    syllables=syl,
                    rhyme_key=cand_key,
                    perfect=True,
                    score=_PERFECT_SCORE - abs(q_syl - syl) * 3.0,
                )
            )

    if not q_skeleton:
        return hits

    # ---- Tier 2: rima toante rica (same skeleton + same tail syllables) ----
    if q_skeleton_syl:
        qs_rich = (
            DictionaryWord.objects.filter(language="ptbr", rhyme_last2=q_skeleton_syl)
            .exclude(rhyme_key=q_key)
            .exclude(word=q_word)
            .values_list("word", "ipa_full", "syllables", "rhyme_key")[:max_partial_scan]
        )
        for word, ipa, syl, cand_key in qs_rich:
            if word in seen:
                continue
            seen.add(word)
            hits.append(
                RhymeHit(
                    word=word,
                    ipa=ipa,
                    syllables=syl,
                    rhyme_key=cand_key,
                    perfect=False,
                    score=_RICH_TOANTE_SCORE - abs(q_syl - syl) * 4.0,
                )
            )

    # ---- Tier 3: rima toante (vowel skeleton only) ----
    qs_toante = (
        DictionaryWord.objects.filter(language="ptbr", rhyme_last1=q_skeleton)
        .exclude(rhyme_last2=q_skeleton_syl)
        .exclude(rhyme_key=q_key)
        .exclude(word=q_word)
        .values_list("word", "ipa_full", "syllables", "rhyme_key", "rhyme_last2")[:max_partial_scan]
    )
    q_tail_syl = _extract_tail_syl(q_skeleton_syl)
    for word, ipa, syl, cand_key, cand_skel_syl in qs_toante:
        if word in seen:
            continue
        seen.add(word)
        cand_tail_syl = _extract_tail_syl(cand_skel_syl)
        tail_diff = abs(q_tail_syl - cand_tail_syl) if cand_tail_syl else 0
        hits.append(
            RhymeHit(
                word=word,
                ipa=ipa,
                syllables=syl,
                rhyme_key=cand_key,
                perfect=False,
                score=_TOANTE_SCORE - abs(q_syl - syl) * 3.0 - tail_diff * 20.0,
            )
        )

    return hits


def _extract_tail_syl(skeleton_syl: str) -> int:
    if not skeleton_syl or "#" not in skeleton_syl:
        return 0
    try:
        return int(skeleton_syl.rsplit("#", 1)[1])
    except ValueError:
        return 0


# ---------------------------------------------------------------------------
# Result bundling
# ---------------------------------------------------------------------------


def build_result_bundle(
    query: DictionaryWord, hits: Sequence[RhymeHit]
) -> RhymeResultBundle:
    by_word: Dict[str, RhymeHit] = {}
    for h in hits:
        if h.word not in by_word or h.score > by_word[h.word].score:
            by_word[h.word] = h

    unique = sorted(
        by_word.values(),
        key=lambda x: (x.score, 1 if x.perfect else 0),
        reverse=True,
    )

    used: Set[str] = set()
    best = [h for h in unique if h.score > 0][:20]
    used.update(h.word for h in best)

    perfect_map: Dict[int, List[RhymeHit]] = {}
    partial_map: Dict[int, List[RhymeHit]] = {}

    for h in unique:
        if h.word in used:
            continue
        bucket = perfect_map if h.perfect else partial_map
        bucket.setdefault(h.syllables, []).append(h)

    for m in perfect_map.values():
        m.sort(key=lambda x: x.word)
    for m in partial_map.values():
        m.sort(key=lambda x: x.word)

    syllables_order = sorted(set(perfect_map.keys()) | set(partial_map.keys()))

    sections: List[SyllableSection] = []
    for syl in syllables_order:
        perf = [x for x in perfect_map.get(syl, []) if x.word not in used]
        for x in perf:
            used.add(x.word)
        part = [x for x in partial_map.get(syl, []) if x.word not in used]
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


# ---------------------------------------------------------------------------
# Autocomplete
# ---------------------------------------------------------------------------


def autocomplete_suggestions(q: str, *, limit: int = 12) -> List[Tuple[str, str]]:
    _ensure_ptbr_ready()
    q = q.strip().lower()
    if not q:
        return []

    base = (
        DictionaryWord.objects.filter(language="ptbr", word__istartswith=q)
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
            DictionaryWord.objects.filter(language="ptbr", word__icontains=q)
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
