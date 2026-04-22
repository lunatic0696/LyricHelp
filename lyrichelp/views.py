from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET

from . import ptbr_rhyme_service, rhyme_service


def home(request: HttpRequest) -> HttpResponse:
    return render(request, "lyrichelp/home.html")


def home_ptbr(request: HttpRequest) -> HttpResponse:
    return render(request, "lyrichelp/ptbr/home.html")


# ---------------------------------------------------------------------------
# English (CMU / ARPABET)
# ---------------------------------------------------------------------------


@require_GET
def search_results(request: HttpRequest) -> HttpResponse:
    q = (request.GET.get("q") or "").strip()
    if not q:
        return redirect("lyrichelp:home")

    entry = rhyme_service.lookup_query_entry(q)
    if entry is None:
        return render(
            request,
            "lyrichelp/results.html",
            {
                "missing_word": q,
                "suggestions": rhyme_service.autocomplete_suggestions(q, limit=8),
                "home_route": "lyrichelp:home",
                "results_route": "lyrichelp:results",
                "autocomplete_route": "lyrichelp:autocomplete",
            },
        )

    hits = rhyme_service.collect_candidates(entry)
    bundle = rhyme_service.build_result_bundle(entry, hits)
    return render(
        request,
        "lyrichelp/results.html",
        {
            "bundle": bundle,
            "missing_word": None,
            "home_route": "lyrichelp:home",
            "results_route": "lyrichelp:results",
            "autocomplete_route": "lyrichelp:autocomplete",
        },
    )


@require_GET
def autocomplete(request: HttpRequest) -> JsonResponse:
    q = (request.GET.get("q") or "").strip()
    rows = rhyme_service.autocomplete_suggestions(q, limit=14)
    return JsonResponse({"suggestions": [{"word": w, "ipa": ipa} for w, ipa in rows]})


# ---------------------------------------------------------------------------
# Brazilian Portuguese — completely independent pipeline
# ---------------------------------------------------------------------------


@require_GET
def search_results_ptbr(request: HttpRequest) -> HttpResponse:
    q = (request.GET.get("q") or "").strip()
    if not q:
        return redirect("lyrichelp:home_ptbr")

    entry = ptbr_rhyme_service.lookup_query_entry(q)
    if entry is None:
        return render(
            request,
            "lyrichelp/ptbr/results.html",
            {
                "missing_word": q,
                "suggestions": ptbr_rhyme_service.autocomplete_suggestions(q, limit=8),
                "home_route": "lyrichelp:home_ptbr",
                "results_route": "lyrichelp:results_ptbr",
                "autocomplete_route": "lyrichelp:autocomplete_ptbr",
            },
        )

    hits = ptbr_rhyme_service.collect_candidates(entry)
    bundle = ptbr_rhyme_service.build_result_bundle(entry, hits)
    return render(
        request,
        "lyrichelp/ptbr/results.html",
        {
            "bundle": bundle,
            "missing_word": None,
            "home_route": "lyrichelp:home_ptbr",
            "results_route": "lyrichelp:results_ptbr",
            "autocomplete_route": "lyrichelp:autocomplete_ptbr",
        },
    )


@require_GET
def autocomplete_ptbr(request: HttpRequest) -> JsonResponse:
    q = (request.GET.get("q") or "").strip()
    rows = ptbr_rhyme_service.autocomplete_suggestions(q, limit=14)
    return JsonResponse({"suggestions": [{"word": w, "ipa": ipa} for w, ipa in rows]})
