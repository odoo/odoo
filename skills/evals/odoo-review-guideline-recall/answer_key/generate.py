"""Write the judges, the reward weights and the oracle review from catalogue.py.

    python3 answer_key/generate.py <checkout with the PR applied> .

Run from the task folder. The line numbers come from the checkout, and an
anchor that no longer matches its file stops the generation.
"""

import sys
import textwrap
from pathlib import Path

from catalogue import AREAS, ISSUES

repo, task = Path(sys.argv[1]), Path(sys.argv[2])
tests = task / 'tests'

HEADER = '''# LLM judge: recall of the seeded issues in one area.
# Area: {title}.
# Rules: {source}.
# One binary criterion per issue; the area's score is the share found.
[judge]
judge = "anthropic/claude-opus-5-5"
files = ["/logs/verifier/review.md"]
reasoning_effort = "high"
guard = "flag"
'''

CRITERION = '''
[[criterion]]
name = "{name}"
type = "binary"
description = """
Seeded issue in {where}:
{issue}

Passes when the review in /logs/verifier/review.md reports this problem at
this spot, in any wording and with any severity, possibly grouped with
similar findings as long as this spot is identified (file and line, or the
method, field, record or file it is in). Fails when the review does not
mention it, or covers it only with a general remark that does not point at
this spot.
"""
'''


def locate(path, anchor):
    if path is None:
        return 'the commit message'
    source = repo / path
    assert source.exists(), f"{path} does not exist"
    if anchor is None:
        return f"`{path}`"
    lines = source.read_text().splitlines()
    hits = [i + 1 for i, line in enumerate(lines) if anchor in line]
    assert hits, f"anchor {anchor!r} not found in {path}"
    return f"`{path}`, line {hits[0]}"


def toml_text(text):
    assert '"""' not in text
    return text.replace('\\', '\\\\')


weights = {}
review = [
    '# Review of the equipment_booking PR (answer key)',
    '',
    'Every seeded issue, by area. Generated from the task\'s issue catalogue.',
]
total = 0
for area, issues in ISSUES.items():
    title, source = AREAS[area]
    out = [HEADER.format(title=title, source=source)]
    review += ['', f'## {title}', '']
    for name, path, anchor, issue in issues:
        where = locate(path, anchor)
        out.append(CRITERION.format(name=name, where=where, issue=textwrap.fill(toml_text(issue), 76)))
        review.append(f'- {where}: {issue}')
    (tests / area).mkdir(parents=True, exist_ok=True)
    (tests / area / 'judge.toml').write_text(''.join(out))
    weights[area] = len(issues)
    total += len(issues)

(task / 'solution' / 'review.md').write_text('\n'.join(review) + '\n')

weight_lines = ', '.join(f'{area} = {count}.0' for area, count in weights.items())
(tests / 'reward.toml').write_text(f'''# reward: the share of the {total} seeded issues the review reports. Every
# issue weighs the same, so each area weighs its number of issues; the
# guidelines rank no rule above another. Each area is also its own score (the
# recall in that area).
# precision: reported, kept out of the reward (weight 0).
[[reward]]
name = "reward"
aggregation = "weighted-mean"
weights = {{ {weight_lines}, precision = 0.0 }}
''')
print(total, weights)
