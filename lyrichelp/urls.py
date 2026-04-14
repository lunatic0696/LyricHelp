from django.urls import path

from . import views

app_name = "lyrichelp"

urlpatterns = [
    path("", views.home, name="home"),
    path("results/", views.search_results, name="results"),
    path("api/autocomplete/", views.autocomplete, name="autocomplete"),
]
