# spec for ten-words-per-week
branch: claude/feature/ten-words-per-week

## Summary
Each weekly word set currently has 5 words, and only a few sample weeks have data (Primary 1–3, Secondary 1–2). Fill every week of both levels with exactly 10 words: all 30 Primary weeks and all 20 Secondary weeks, 500 words in total, with themes and words suitable for children aged 10–12. Existing databases are upgraded by adding the new words alongside the existing ones, and the app refuses to start if any week does not have exactly 10 words.

Tests also change from one-shot to repeatable. The existing test history (all from 5-word tests) is cleared once, for the pre-go-live history only, after the database has been backed up. From then on, learners can take each week's test up to 3 times, and every attempt is kept with its week, timestamp and attempt number. Each question in an attempt is recorded as correct, incorrect or unattempted, and the test has a Skip button.

## Functional requirements

### Word content
- All 30 Primary weeks and all 20 Secondary weeks have a theme and exactly 10 words.
- Themes and words are friendly to children aged 10–12: familiar, positive topics, with no frightening, violent or mature content.
- Primary words are the easier set; Secondary words are more challenging, but still within reach of a 10–12 year old.
- The existing sample weeks keep their current theme and 5 words, plus 5 new words that fit that theme.
- Every word has a word, part of speech, meaning and example sentence. Meanings and sentences use simple language a 10–12 year old understands. Synonyms and antonyms are provided wherever a sensible one exists.
- Each example sentence contains the word in exactly the form being tested, so it can be blanked out cleanly in the test.
- No word appears more than once within the same level.
- Weekly themes:

| Week | Primary | Secondary |
|---|---|---|
| 1 | Feelings | Character |
| 2 | Nature | Debate |
| 3 | At School | Exploration and Discovery |
| 4 | Animals | Technology and Gaming |
| 5 | Food and Cooking | Ancient Civilisations |
| 6 | Weather | Our Planet |
| 7 | Sports and Games | Mysteries and Detectives |
| 8 | Family and Friends | Teamwork and Leadership |
| 9 | The Ocean | The Human Body |
| 10 | Space | News and Media |
| 11 | Music | Inventors and Ideas |
| 12 | Travel and Transport | Extreme Weather |
| 13 | Healthy Bodies | Friendship and Emotions |
| 14 | Inventions | Space Exploration |
| 15 | Festivals and Celebrations | Fantasy and Imagination |
| 16 | Books and Stories | Healthy Living |
| 17 | Dinosaurs | Buildings and Cities |
| 18 | In the City | Oceans and Rivers |
| 19 | Farm Life | Courage and Heroes |
| 20 | Art and Colours | Persuasive Writing |
| 21 | Time and Seasons | |
| 22 | Jobs and People | |
| 23 | Camping and Adventure | |
| 24 | Minibeasts | |
| 25 | Shopping and Money | |
| 26 | Myths and Legends | |
| 27 | Kindness and Helping | |
| 28 | Science Lab | |
| 29 | Caring for the Environment | |
| 30 | Tricky Spellings Review | |

### Enforcing exactly 10 words
- On startup, the app checks the word data. If either level has the wrong number of weeks, or any week has more or fewer than 10 words, the app does not start and reports which level and week is wrong.

### Upgrading existing databases
- On startup, the app adds any words from the word data that are missing from the database, instead of only seeding an empty database. Existing words and user accounts are left untouched.
- Adding words is safe to repeat: restarting the app never creates duplicate words.
- Before the history is deleted, the database is backed up automatically.
- All existing pre-go-live test history (attempts and answers) is deleted once. This happens only once and never again after go-live, not on every restart.

### Retakes and attempt history
- A learner can take each week's test up to 3 times, per level. A 4th attempt is refused.
- Every attempt is saved with its level, week, attempt number (1, 2 or 3 for that learner and week), score and completion timestamp.
- Each question in an attempt is recorded as correct, incorrect or unattempted.
- The test page has a Skip button. Skipping a word before any try is made records it as unattempted. Skipping after a wrong try records it as incorrect.
- The 3-tries-per-word rule and the per-word "tries" count still apply within each attempt.
- The week page shows how many attempts the learner has made and the latest score, with buttons to view results and to take the test again while attempts remain.
- The results page shows the latest attempt's word breakdown, plus a list of all previous attempts for that week (attempt number, date and time, score). Any previous attempt's breakdown can be opened.
- The plan page marks a week as completed after at least one attempt, and shows the attempt count and the latest score.
- The admin dashboard keeps the per-week average calculation unchanged.
- The admin learner table shows, for each learner, tests completed out of the number of weeks with a completion percentage, and attempts used out of (weeks x 3) with a percentage.
- The admin dashboard also has a table of every test showing its score percentage and the counts of correct, incorrect and unattempted questions.

### Existing behaviour to keep
- The spelling test asks all 10 words in random order and is scored out of 10.
- Docs (README and CLAUDE.md) describe the full word set, the 10-word rule and the retake behaviour.

## Figma Design reference(only if referenced)
- Not referenced.

## Possible edge cases
- An existing database with 5-word weeks must gain the 5 new words for those weeks and all words for the new weeks, with no duplicates of the original 5.
- A word whose meaning or sentence was edited in the word data but already exists in the database: adding missing words does not update it.
- The one-time clearing of test history must not run again after go-live or after new 10-word attempts exist, or it would wipe real progress.
- A learner tries to start a 4th attempt for a week: it is refused.
- A learner skips every question: the attempt is saved with all questions unattempted.
- A learner submits the same attempt twice (double-click or browser resubmit), which should not create two attempts.
- Two attempts finishing within the same second still get distinct attempt numbers.
- A learner switches level; attempt history is kept separately per level.
- A word whose spelling differs between British and American English (e.g. "practise"), causing correct-looking answers to be marked wrong.
- An example sentence that contains the word in a different form (plural, past tense), so the blanked-out sentence gives away or garbles the answer.
- A test abandoned partway through: nothing is saved and no attempt number is used up.
- The startup check fails on a typo in the word data; the error must say exactly which level and week to fix.

## Acceptance criteria
- All 30 Primary and 20 Secondary weeks in the plan show their theme and "10 words"; no week shows "Coming soon".
- Opening any week shows 10 word cards, with content suitable for children aged 10–12.
- No duplicate words exist within a level.
- Starting with a fresh database seeds all 500 words without errors.
- Starting against an existing database with 5-word weeks, users and test attempts results in 10 words per week, all users kept, all old test attempts removed, and a backup of the database made first.
- Restarting the app again changes neither the word count nor any new attempts.
- Removing a word from one week in the word data makes the app refuse to start, with an error naming that level and week.
- A learner can take the same week's test three times; the week shows 3 attempts, each with its own timestamp, score and attempt number 1, 2 and 3. A 4th attempt is refused.
- Each question in an attempt is recorded as correct, incorrect or unattempted; the Skip button records unattempted (no tries) or incorrect (after a wrong try).
- The plan page shows the latest score for each completed week.
- The results page shows the latest attempt and lists all earlier attempts, and each earlier attempt's breakdown can be viewed.
- The admin dashboard shows correct per-week averages (calculation unchanged), the learner table with tests completed / weeks and attempts used / (weeks x 3) with percentages, and a table of every test with its score percentage and correct, incorrect and unattempted counts.

## Open Questions
- Resolved: fill all 30 Primary and 20 Secondary weeks, with themes chosen for children aged 10–12.
- Resolved: add missing words to existing databases alongside the existing ones.
- Resolved: exactly 10 words per week, enforced at startup.
- Resolved: clear existing pre-go-live test history once only (never after go-live), after backing up the database.
- Resolved: retakes are limited to 3 attempts per week per learner, with every attempt recorded with its week, timestamp and attempt number.
- Resolved: the admin per-week average calculation is unchanged.
- Resolved: the plan page shows the latest score for completed weeks.
- Resolved: each question is recorded as correct, incorrect or unattempted, and the test has a Skip button.
- Resolved: the admin learner view shows tests completed / weeks and attempts used / (weeks x 3) with percentages, plus a table of every test with its score percentage.

## Testing guidelines
Create a test file(s) in the ./tests folder for the new feature, and create meaningful tests for the following cases, without going too heavy.
- Primary has 30 weeks and Secondary has 20 weeks, numbered without gaps, each with a theme.
- Every week in both word lists contains exactly 10 words with the required fields (word, part of speech, meaning, sentence).
- Every example sentence contains its word.
- No duplicate words exist within a level.
- The startup check rejects word data where a week has 9 or 11 words.
- A fresh database seeds 500 words.
- Upgrading a database with 5-word weeks and an old attempt adds the missing words, keeps the user, and removes the old attempt.
- Running startup twice creates no duplicate words and keeps attempts made after the upgrade.
- Taking the same week's test twice creates two attempts numbered 1 and 2, each with a timestamp and a total of 10.
- A 4th attempt for the same week is refused.
- Skipping with no tries records the question as unattempted; skipping after a wrong try records it as incorrect.
- The plan page shows the latest score, not the best.
- The upgrade makes a database backup before clearing old history, and does not clear history a second time.
- The admin learner table and the table of every test show the correct percentages and correct/incorrect/unattempted counts.
- The results page lists all attempts for the week.
