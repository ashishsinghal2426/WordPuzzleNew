import copy

import pytest

from words_data import WordDataError, validate_word_data

WEEKS = {'primary': 2, 'secondary': 1}
PER_WEEK = 2


def make_word(word, sentence=None):
    return {'word': word, 'pos': 'noun', 'meaning': f'Meaning of {word}.',
            'sentence': sentence or f'This is a {word} today.',
            'synonyms': [], 'antonyms': []}


def make_week(n, words, theme='Theme'):
    return {'week': n, 'theme': theme, 'words': [make_word(w) for w in words]}


def good_primary():
    return [make_week(1, ['apple', 'berry']), make_week(2, ['cherry', 'damson'])]


def good_secondary():
    return [make_week(1, ['eagle', 'falcon'])]


def run(primary=None, secondary=None, weeks=WEEKS, per_week=PER_WEEK):
    return validate_word_data(
        good_primary() if primary is None else primary,
        good_secondary() if secondary is None else secondary,
        weeks, per_week)


def test_valid_data_has_no_problems():
    assert run() == []


def test_week_count():
    assert 'primary: expected 2 weeks, found 1' in run(primary=good_primary()[:1])


def test_missing_week_number():
    secondary = [make_week(2, ['eagle', 'falcon'])]
    assert 'secondary: week 1 missing' in run(secondary=secondary)


def test_duplicate_week_number():
    primary = [make_week(1, ['apple', 'berry']), make_week(1, ['cherry', 'damson'])]
    problems = run(primary=primary)
    assert 'primary: week 1 appears more than once' in problems
    assert 'primary: week 2 missing' in problems


def test_missing_theme():
    primary = good_primary()
    primary[1]['theme'] = ''
    assert 'primary week 2: missing theme' in run(primary=primary)


def test_word_count():
    primary = good_primary()
    primary[0]['words'].pop()
    assert 'primary week 1: expected 2 words, found 1' in run(primary=primary)


@pytest.mark.parametrize('field', ['word', 'pos', 'meaning', 'sentence'])
def test_required_fields(field):
    secondary = good_secondary()
    secondary[0]['words'][0][field] = '  '
    problems = run(secondary=secondary)
    label = "'eagle'" if field != 'word' else "''"
    assert f'secondary week 1 {label}: missing {field}' in problems


def test_word_letters_only():
    primary = good_primary()
    primary[0]['words'][0] = make_word('ice cream', 'We like ice cream.')
    assert "primary week 1 'ice cream': word must be letters only" in run(primary=primary)


def test_hyphen_allowed():
    primary = good_primary()
    primary[0]['words'][0] = make_word('well-known', 'She is well-known here.')
    assert run(primary=primary) == []


def test_sentence_must_contain_word():
    primary = good_primary()
    primary[0]['words'][0]['sentence'] = 'Nothing relevant here.'
    assert "primary week 1 'apple': sentence does not contain the word" in run(primary=primary)


def test_sentence_match_is_case_insensitive():
    primary = good_primary()
    primary[0]['words'][0]['sentence'] = 'APPLE pie is nice.'
    assert run(primary=primary) == []


def test_sentence_match_is_whole_word():
    primary = good_primary()
    primary[0]['words'][0] = make_word('cat', 'The category was large.')
    assert "primary week 1 'cat': sentence does not contain the word" in run(primary=primary)


def test_duplicate_word_within_level():
    primary = good_primary()
    primary[1]['words'][0] = make_word('apple')
    assert "primary: 'apple' appears in weeks 1 and 2" in run(primary=primary)


def test_duplicate_word_is_case_insensitive():
    primary = good_primary()
    primary[1]['words'][0] = make_word('Apple')
    assert "primary: 'apple' appears in weeks 1 and 2" in run(primary=primary)


def test_same_word_across_levels_is_allowed():
    secondary = [make_week(1, ['apple', 'falcon'])]
    assert run(secondary=secondary) == []


def test_all_problems_are_collected():
    primary = copy.deepcopy(good_primary())[:1]
    primary[0]['theme'] = ''
    problems = run(primary=primary)
    assert 'primary: expected 2 weeks, found 1' in problems
    assert 'primary week 1: missing theme' in problems


def test_word_data_error_holds_problems():
    err = WordDataError(['a', 'b'])
    assert err.problems == ['a', 'b']
    assert 'a' in str(err) and 'b' in str(err)


def test_duplicate_word_within_same_week():
    primary = good_primary()
    primary[0]['words'][1] = make_word('apple')
    assert "primary week 1: 'apple' appears more than once" in run(primary=primary)


# ── Real word data ────────────────────────────────────────────────────────────

import re  # noqa: E402

import main  # noqa: E402
from words_data import PRIMARY_WORDS, SECONDARY_WORDS  # noqa: E402

REAL = [('primary', PRIMARY_WORDS, 30), ('secondary', SECONDARY_WORDS, 20)]


@pytest.mark.parametrize('level,data,weeks', REAL)
def test_real_data_shape(level, data, weeks):
    assert [w['week'] for w in data] == list(range(1, weeks + 1))
    for week in data:
        assert week['theme'].strip()
        assert len(week['words']) == 10


@pytest.mark.parametrize('level,data,weeks', REAL)
def test_real_data_words_are_valid(level, data, weeks):
    seen = set()
    for week in data:
        for w in week['words']:
            for field in ('word', 'pos', 'meaning', 'sentence'):
                assert w[field].strip(), (level, week['week'], w['word'], field)
            assert re.fullmatch(r'[A-Za-z]+(-[A-Za-z]+)*', w['word']), w['word']
            assert re.search(r'\b' + re.escape(w['word']) + r'\b', w['sentence'], re.I), w['word']
            key = w['word'].lower()
            assert key not in seen, key
            seen.add(key)


def test_real_data_passes_validator():
    assert validate_word_data(PRIMARY_WORDS, SECONDARY_WORDS,
                              main.WEEKS_PER_LEVEL, main.WORDS_PER_WEEK) == []


def test_real_data_has_500_words():
    total = sum(len(w['words']) for w in PRIMARY_WORDS + SECONDARY_WORDS)
    assert total == 500


def test_setup_database_refuses_invalid_data(app, monkeypatch):
    broken = copy.deepcopy(PRIMARY_WORDS)
    broken[0]['words'].pop()
    monkeypatch.setattr(main, 'PRIMARY_WORDS', broken)
    with pytest.raises(WordDataError) as exc:
        main.setup_database()
    assert 'primary week 1: expected 10 words, found 9' in exc.value.problems
