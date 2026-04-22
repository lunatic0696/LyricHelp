import urllib.error
import urllib.request
from pathlib import Path

from django.core.management.base import BaseCommand

from lyrichelp import ptbr_phonetics
from lyrichelp.models import DictionaryWord

PTBR_URLS = (
    "https://raw.githubusercontent.com/pythonprobr/palavras/master/palavras.txt",
    "https://raw.githubusercontent.com/fserb/pt-br/master/words.txt",
)


class Command(BaseCommand):
    help = "Load Brazilian Portuguese words and build local phonetic rhyme keys."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-download",
            action="store_true",
            help="Use existing lyrichelp/data/ptbr_words.txt when available.",
        )

    def handle(self, *args, **options):
        data_dir = Path(__file__).resolve().parent.parent.parent / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        target = data_dir / "ptbr_words.txt"
        fallback = data_dir / "ptbr_seed.txt"

        if options["skip_download"] and target.is_file():
            self.stdout.write(f"Using existing PT-BR list at {target}")
        else:
            last_err: Exception | None = None
            for url in PTBR_URLS:
                self.stdout.write(f"Downloading PT-BR words from {url} ...")
                try:
                    urllib.request.urlretrieve(url, target)
                    last_err = None
                    break
                except (urllib.error.URLError, OSError) as e:
                    last_err = e
                    self.stdout.write(self.style.WARNING(f"Failed: {e}"))
            if last_err is not None:
                if fallback.is_file():
                    self.stdout.write(self.style.WARNING("Using bundled PT-BR fallback list."))
                    target = fallback
                else:
                    raise last_err

        raw = target.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("latin-1")

        words: set[str] = set()
        for line in text.splitlines():
                token = line.strip().split()[0].lower() if line.strip() else ""
                if len(token) < 2:
                    continue
                if not ptbr_phonetics.is_valid_word(token):
                    continue
                words.add(token)

        self.stdout.write(f"Parsed {len(words)} PT-BR words.")

        DictionaryWord.objects.filter(language="ptbr").delete()

        batch: list[DictionaryWord] = []
        chunk = 3000

        def flush():
            if batch:
                DictionaryWord.objects.bulk_create(batch, batch_size=chunk)
                batch.clear()

        for word in sorted(words):
            rk = ptbr_phonetics.rhyme_key(word)
            if not rk.strip():
                continue
            last1, last2 = ptbr_phonetics.rhyme_index_keys(word)
            batch.append(
                DictionaryWord(
                    language="ptbr",
                    word=word,
                    phones=ptbr_phonetics.phones_for_word(word),
                    syllables=ptbr_phonetics.syllable_count(word),
                    rhyme_key=rk,
                    rhyme_last1=last1,
                    rhyme_last2=last2,
                    ipa_full=ptbr_phonetics.word_to_ipa(word),
                )
            )
            if len(batch) >= chunk:
                flush()

        flush()
        total = DictionaryWord.objects.filter(language="ptbr").count()
        self.stdout.write(self.style.SUCCESS(f"Loaded {total} PT-BR dictionary rows."))
