from django.urls import path

from . import views

app_name = "lyrichelp"

urlpatterns = [
    path("", views.home, name="home"),
    path("results/", views.search_results, name="results"),
    path("api/autocomplete/", views.autocomplete, name="autocomplete"),
    path("ptbr/", views.home_ptbr, name="home_ptbr"),
    path("ptbr/results/", views.search_results_ptbr, name="results_ptbr"),
    path("ptbr/api/autocomplete/", views.autocomplete_ptbr, name="autocomplete_ptbr"),
]
