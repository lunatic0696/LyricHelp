from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("lyrichelp", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="dictionaryword",
            old_name="rime",
            new_name="rhyme_key",
        ),
        migrations.RenameField(
            model_name="dictionaryword",
            old_name="rime_last1",
            new_name="rhyme_last1",
        ),
        migrations.RenameField(
            model_name="dictionaryword",
            old_name="rime_last2",
            new_name="rhyme_last2",
        ),
    ]
