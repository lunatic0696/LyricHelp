from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET

from . import rhyme_service


def home(request: HttpRequest) -> HttpResponse:
    return render(request, "lyrichelp/home.html")


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
        },
    )


@require_GET
def autocomplete(request: HttpRequest) -> JsonResponse:
    q = (request.GET.get("q") or "").strip()
    rows = rhyme_service.autocomplete_suggestions(q, limit=14)
    return JsonResponse({"suggestions": [{"word": w, "ipa": ipa} for w, ipa in rows]})
