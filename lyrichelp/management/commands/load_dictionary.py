import urllib.error
import urllib.request
from pathlib import Path

from django.core.management.base import BaseCommand

from lyrichelp import phonetics
from lyrichelp.models import DictionaryWord

CMUDICT_URLS = (
    "https://raw.githubusercontent.com/Alexir/CMUdict/master/cmudict-0.7b",
    "https://raw.githubusercontent.com/cmusphinx/cmudict/master/cmudict-0.7b",
)


class Command(BaseCommand):
    help = "Download CMUdict to local data/ and populate DictionaryWord (IPA derived from phones)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-download",
            action="store_true",
            help="Use existing lyrichelp/data/cmudict-0.7b without fetching.",
        )

    def handle(self, *args, **options):
        data_dir = Path(__file__).resolve().parent.parent.parent / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        target = data_dir / "cmudict-0.7b"

        if options["skip_download"] and target.is_file():
            self.stdout.write(f"Using existing CMUdict at {target}")
        else:
            last_err: Exception | None = None
            for url in CMUDICT_URLS:
                self.stdout.write(f"Downloading CMUdict from {url} ...")
                try:
                    urllib.request.urlretrieve(url, target)
                    last_err = None
                    break
                except (urllib.error.URLError, OSError) as e:
                    last_err = e
                    self.stdout.write(self.style.WARNING(f"Failed: {e}"))
            if last_err is not None:
                raise last_err

        word_to_phones: dict[str, str] = {}
        with target.open("r", encoding="latin-1", errors="replace") as f:
            for line in f:
                parsed = phonetics.parse_cmudict_line(line)
                if not parsed:
                    continue
                word, phones = parsed
                if word not in word_to_phones:
                    word_to_phones[word] = phones

        self.stdout.write(f"Parsed {len(word_to_phones)} unique headwords.")

        DictionaryWord.objects.all().delete()

        batch: list[DictionaryWord] = []
        chunk = 3000

        def flush():
            if batch:
                DictionaryWord.objects.bulk_create(batch, batch_size=chunk)
                batch.clear()

        for word, phones in word_to_phones.items():
            r = phonetics.rhyming_part(phones)
            if not r.strip():
                continue
            last1, last2 = phonetics.rhyme_tail_keys(r)
            batch.append(
                DictionaryWord(
                    word=word,
                    phones=phones,
                    syllables=phonetics.syllable_count(phones),
                    rhyme_key=r,
                    rhyme_last1=last1,
                    rhyme_last2=last2,
                    ipa_full=phonetics.phones_to_ipa(phones),
                )
            )
            if len(batch) >= chunk:
                flush()

        flush()

        self.stdout.write(
            self.style.SUCCESS(f"Loaded {DictionaryWord.objects.count()} dictionary rows.")
        )
