from django.contrib import admin

from .models import DictionaryWord


@admin.register(DictionaryWord)
class DictionaryWordAdmin(admin.ModelAdmin):
    list_display = ("word", "syllables", "ipa_full", "rhyme_key")
    search_fields = ("word", "rhyme_key")
    ordering = ("word",)
