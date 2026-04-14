from django.db import models


class DictionaryWord(models.Model):
    """
    Local English pronunciation row (CMU-derived). rhyme_key stores the ARPABET
    rhyme tail (from the stressed vowel onward); ipa_full is derived for display.
    """

    word = models.CharField(max_length=120, db_index=True, unique=True)
    phones = models.CharField(max_length=200)
    syllables = models.PositiveSmallIntegerField(db_index=True)
    rhyme_key = models.CharField(max_length=120, db_index=True)
    rhyme_last1 = models.CharField(max_length=12, db_index=True)
    rhyme_last2 = models.CharField(max_length=24, db_index=True, default="")
    ipa_full = models.CharField(max_length=300)

    class Meta:
        ordering = ["word"]
        indexes = [
            models.Index(fields=["rhyme_key", "syllables"]),
        ]

    def __str__(self) -> str:
        return self.word
