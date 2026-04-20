from django.db import models


class DictionaryWord(models.Model):
    """
    Local English pronunciation row (CMU-derived). rhyme_key stores the ARPABET
    rhyme tail (from the stressed vowel onward); ipa_full is derived for display.
    """

    language = models.CharField(max_length=16, db_index=True, default="en")
    word = models.CharField(max_length=120, db_index=True)
    phones = models.CharField(max_length=200)
    syllables = models.PositiveSmallIntegerField(db_index=True)
    rhyme_key = models.CharField(max_length=120, db_index=True)
    rhyme_last1 = models.CharField(max_length=12, db_index=True)
    rhyme_last2 = models.CharField(max_length=24, db_index=True, default="")
    ipa_full = models.CharField(max_length=300)

    class Meta:
        ordering = ["language", "word"]
        indexes = [
            models.Index(fields=["rhyme_key", "syllables"], name="lyrichelp_rhyme_key_syl_idx"),
            models.Index(fields=["language", "rhyme_key"], name="lyrichelp_languag_a17cc1_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["language", "word"], name="uniq_word_per_language"),
        ]

    def __str__(self) -> str:
        return self.word
