from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET

from . import rhyme_service


def home(request: HttpRequest) -> HttpResponse:
    return render(request, "lyrichelp/home.html")

def home_ptbr(request: HttpRequest) -> HttpResponse:
    return render(request, "lyrichelp/ptbr/home.html")


@require_GET
def search_results(request: HttpRequest) -> HttpResponse:
    return _search_results_for_language(
        request,
        language="en",
        template="lyrichelp/results.html",
        home_route="lyrichelp:home",
        results_route="lyrichelp:results",
        autocomplete_route="lyrichelp:autocomplete",
    )


@require_GET
def search_results_ptbr(request: HttpRequest) -> HttpResponse:
    return _search_results_for_language(
        request,
        language="ptbr",
        template="lyrichelp/ptbr/results.html",
        home_route="lyrichelp:home_ptbr",
        results_route="lyrichelp:results_ptbr",
        autocomplete_route="lyrichelp:autocomplete_ptbr",
    )


def _search_results_for_language(
    request: HttpRequest,
    *,
    language: str,
    template: str,
    home_route: str,
    results_route: str,
    autocomplete_route: str,
) -> HttpResponse:
    q = (request.GET.get("q") or "").strip()
    if not q:
        return redirect(home_route)

    entry = rhyme_service.lookup_query_entry(q, language=language)
    if entry is None:
        return render(
            request,
            template,
            {
                "missing_word": q,
                "suggestions": rhyme_service.autocomplete_suggestions(q, language=language, limit=8),
                "home_route": home_route,
                "results_route": results_route,
                "autocomplete_route": autocomplete_route,
            },
        )

    hits = rhyme_service.collect_candidates(entry, language=language)
    bundle = rhyme_service.build_result_bundle(entry, hits)

    return render(
        request,
        template,
        {
            "bundle": bundle,
            "missing_word": None,
            "home_route": home_route,
            "results_route": results_route,
            "autocomplete_route": autocomplete_route,
        },
    )


@require_GET
def autocomplete(request: HttpRequest) -> JsonResponse:
    return _autocomplete_for_language(request, language="en")


@require_GET
def autocomplete_ptbr(request: HttpRequest) -> JsonResponse:
    return _autocomplete_for_language(request, language="ptbr")


def _autocomplete_for_language(request: HttpRequest, *, language: str) -> JsonResponse:
    q = (request.GET.get("q") or "").strip()
    rows = rhyme_service.autocomplete_suggestions(q, language=language, limit=14)
    return JsonResponse({"suggestions": [{"word": w, "ipa": ipa} for w, ipa in rows]})
