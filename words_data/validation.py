import re

REQUIRED_FIELDS = ('word', 'pos', 'meaning', 'sentence')
LETTERS_ONLY = re.compile(r'^[A-Za-z]+(-[A-Za-z]+)*$')


class WordDataError(Exception):
    """Raised when the word data breaks the rules; .problems lists each one."""

    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__('Invalid word data:\n' + '\n'.join(f'  - {p}' for p in self.problems))


def _check_level(level, data, expected_weeks, words_per_week):
    problems = []

    if len(data) != expected_weeks:
        problems.append(f'{level}: expected {expected_weeks} weeks, found {len(data)}')

    week_numbers = [entry.get('week') for entry in data]
    for n in range(1, expected_weeks + 1):
        if n not in week_numbers:
            problems.append(f'{level}: week {n} missing')
        elif week_numbers.count(n) > 1:
            problems.append(f'{level}: week {n} appears more than once')
    for n in week_numbers:
        if not isinstance(n, int) or not 1 <= n <= expected_weeks:
            problems.append(f'{level}: unexpected week number {n!r}')

    first_week_of = {}
    for entry in data:
        week = entry.get('week')
        label = f'{level} week {week}'
        words = entry.get('words') or []

        if not (entry.get('theme') or '').strip():
            problems.append(f'{label}: missing theme')
        if len(words) != words_per_week:
            problems.append(f'{label}: expected {words_per_week} words, found {len(words)}')

        for item in words:
            text = (item.get('word') or '').strip()
            name = f"{label} '{text}'"
            for field in REQUIRED_FIELDS:
                if not (item.get(field) or '').strip():
                    problems.append(f'{name}: missing {field}')
            if text and not LETTERS_ONLY.match(text):
                problems.append(f'{name}: word must be letters only')
            sentence = (item.get('sentence') or '').strip()
            if text and sentence and not re.search(
                    r'(?<![A-Za-z])' + re.escape(text) + r'(?![A-Za-z])', sentence, re.IGNORECASE):
                problems.append(f'{name}: sentence does not contain the word')
            if text:
                key = text.lower()
                if key not in first_week_of:
                    first_week_of[key] = week
                elif first_week_of[key] == week:
                    problems.append(f"{label}: '{key}' appears more than once")
                else:
                    problems.append(f"{level}: '{key}' appears in weeks {first_week_of[key]} and {week}")

    return problems


def validate_word_data(primary, secondary, weeks, words_per_week):
    """Return a list of human-readable problems; an empty list means the data is valid."""
    problems = []
    problems += _check_level('primary', primary, weeks['primary'], words_per_week)
    problems += _check_level('secondary', secondary, weeks['secondary'], words_per_week)
    return problems
