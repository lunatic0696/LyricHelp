from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("lyrichelp", "0002_rename_rhyme_fields"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="dictionaryword",
            name="lyrichelp_d_rime_d09204_idx",
        ),
        migrations.AddField(
            model_name="dictionaryword",
            name="language",
            field=models.CharField(db_index=True, default="en", max_length=16),
        ),
        migrations.AlterField(
            model_name="dictionaryword",
            name="word",
            field=models.CharField(db_index=True, max_length=120),
        ),
        migrations.AddIndex(
            model_name="dictionaryword",
            index=models.Index(fields=["rhyme_key", "syllables"], name="lyrichelp_rhyme_key_syl_idx"),
        ),
        migrations.AddIndex(
            model_name="dictionaryword",
            index=models.Index(fields=["language", "rhyme_key"], name="lyrichelp_languag_a17cc1_idx"),
        ),
        migrations.AddConstraint(
            model_name="dictionaryword",
            constraint=models.UniqueConstraint(fields=("language", "word"), name="uniq_word_per_language"),
        ),
    ]
