#!/usr/bin/env python3
"""Flatten the game's submissions into a CSV with one column per question.

The app records a run as a res.partner whose Notes field holds the whole
transcript as HTML. That is readable but useless in a spreadsheet, so this
turns each transcript into columns: one per question, plus the best match and
the runners-up.

    python3 export_submissions.py export.csv     flatten a Contacts export
    python3 export_submissions.py --db jm_poc    read a local database instead

Export Contacts from the web UI with the Email, Phone, Name and Notes columns,
then type the command and drop the downloaded file on the terminal to fill the
path in. The flattened copy is written next to it as <name>_flat.csv, so that
one drop is the whole invocation; --out overrides the destination.

This file is standalone: nothing but the standard library, no build.json, no
sibling data file. Copy it wherever the export lands and run it there.

Reading a database is the other mode, for a machine that can open one: it
shells out to odoo-bin, which it looks for next to this script and in the
directories above it. Point --odoo-bin, --python and --addons-path at the right
places when that guess is wrong.
"""

import argparse
import csv
import html
import json
import os
import re
import subprocess
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))

# Fixed columns around the questions. The transcript writes the ranking as a
# final paragraph, in this same wording -- see screens/*_result.js.
BEST_PREFIX = 'Best match:'
RUNNERS_PREFIX = 'Runners-up:'
LEAD_COLUMNS = ['Email', 'Phone', 'Name']
TAIL_COLUMNS = ['Best match', 'Runners-up']

# Several picked answers of a multiple-choice question land in one cell.
MULTI_JOIN = ' | '

# Column order, copied from data/questions.json so this script stays standalone.
# Ordering by first appearance instead would let a visitor who skipped an
# optional question shuffle the columns of a whole export. A question that is
# not listed here is not lost: it is appended in the order it turns up, so an
# edited questionnaire still exports in full, just with the new columns last.
QUESTIONS = [
    "What's your name?",
    'What is your email address?',
    'What is your phone number?',
    'What are you looking for?',
    'What languages can you work in?',
    'What do you enjoy the most?',
    'What task would you love?',
    'How do you prefer to work?',
    'How would your family/friends describe you?',
]

# Run by odoo shell. Only partners carrying a transcript are submissions;
# ordinary contacts share the model and must stay out.
READ = '''
import json
partners = env['res.partner'].search([('comment', 'like', %(needle)s)], order='id')
rows = [{
    'Email': p.email or '',
    'Phone': p.phone or '',
    'Name': p.name or '',
    'Notes': p.comment or '',
} for p in partners]
print('ROWS_JSON ' + json.dumps(rows))
'''


def dropped_path(raw):
    """Make sense of a path a file manager wrote into the terminal.

    A drop is a paste, and what lands depends on the terminal: a bare path, a
    quoted one, or a file:// URI with the spaces and brackets percent-encoded.
    The shell strips quoting it recognises, so what argparse hands us can still
    be any of the three.
    """
    raw = raw.strip()
    for quote in ('"', "'"):
        if len(raw) > 1 and raw.startswith(quote) and raw.endswith(quote):
            raw = raw[1:-1]
    if raw.startswith('file://'):
        raw = urllib.parse.unquote(urllib.parse.urlparse(raw).path)
    return raw


def default_output(source):
    """Where a flattened copy of a dropped file goes: right next to it."""
    folder, name = os.path.split(source)
    stem = os.path.splitext(name)[0]
    return os.path.join(folder, '%s_flat.csv' % stem)


def find_upwards(name, start):
    """First `name` found in `start` or any directory above it."""
    folder = os.path.abspath(start)
    while True:
        candidate = os.path.join(folder, name)
        if os.path.exists(candidate):
            return candidate
        parent = os.path.dirname(folder)
        if parent == folder:
            return None
        folder = parent


def text(fragment):
    """One transcript line as plain text: no markup, no entities."""
    return html.unescape(re.sub(r'<[^>]+>', '', fragment)).strip()


def parse_notes(notes):
    """Split one transcript into {question: answer}, best match, runners-up."""
    answers, best, runners = {}, '', ''
    for block in re.findall(r'<p>(.*?)</p>', notes or '', re.S):
        lines = [text(part) for part in re.split(r'<br\s*/?>', block)]
        lines = [line for line in lines if line]
        if not lines:
            continue
        head, rest = lines[0], lines[1:]
        if head.startswith(BEST_PREFIX):
            best = head[len(BEST_PREFIX):].strip()
            for line in rest:
                if line.startswith(RUNNERS_PREFIX):
                    runners = line[len(RUNNERS_PREFIX):].strip()
            continue
        answers[head] = MULTI_JOIN.join(rest)
    return answers, best, runners


def read_database(args):
    """Ask odoo shell for the submissions, as JSON on one line."""
    odoo_bin = args.odoo_bin or find_upwards('odoo-bin', HERE)
    if not odoo_bin:
        sys.exit('No odoo-bin found above %s -- pass --odoo-bin.' % HERE)
    addons_path = args.addons_path or os.path.join(os.path.dirname(odoo_bin), 'addons')
    cmd = [
        args.python, odoo_bin, 'shell',
        '-d', args.db,
        '--addons-path=%s' % addons_path,
        '--no-http', '--log-level=warn',
    ]
    print('Reading %s ...' % args.db)
    script = READ % {'needle': json.dumps(BEST_PREFIX)}
    done = subprocess.run(cmd, input=script, capture_output=True, text=True)
    for line in done.stdout.splitlines():
        if line.startswith('ROWS_JSON '):
            return json.loads(line[len('ROWS_JSON '):])
    sys.exit('Read failed. Check --python, --odoo-bin and --addons-path.\n%s\n%s'
             % (done.stdout[-2000:], done.stderr[-2000:]))


def read_csv(path):
    """Flatten a Contacts export from the web UI instead of a database."""
    if not os.path.isfile(path):
        sys.exit('No such file: %s' % path)
    print('Reading %s ...' % path)
    with open(path, newline='', encoding='utf-8-sig') as fh:
        rows = list(csv.DictReader(fh))
    if rows and 'Notes' not in rows[0]:
        sys.exit('No Notes column in %s -- nothing to flatten.' % path)
    return [{key: row.get(key) or '' for key in LEAD_COLUMNS + ['Notes']}
            for row in rows
            if BEST_PREFIX in (row.get('Notes') or '')]


def write_csv(path, rows):
    order = list(QUESTIONS)
    parsed = []
    for row in rows:
        answers, best, runners = parse_notes(row['Notes'])
        parsed.append((row, answers, best, runners))
        for question in answers:
            if question not in order:
                order.append(question)  # asked, but not one of the known columns

    columns = LEAD_COLUMNS + order + TAIL_COLUMNS
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        out = csv.DictWriter(fh, fieldnames=columns, quoting=csv.QUOTE_ALL)
        out.writeheader()
        for row, answers, best, runners in parsed:
            record = {key: row[key] for key in LEAD_COLUMNS}
            record.update({question: answers.get(question, '') for question in order})
            record['Best match'] = best
            record['Runners-up'] = runners
            out.writerow(record)
    print('  wrote %d submission(s), %d columns -> %s'
          % (len(parsed), len(columns), path))


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('csv', nargs='?', metavar='FILE',
                        help='a Contacts export to flatten -- drop the file on the '
                             'terminal to fill this in')
    parser.add_argument('--out', metavar='FILE',
                        help='where to write (default: next to FILE as <name>_flat.csv, '
                             'or submissions.csv beside this script for --db)')
    parser.add_argument('--db', metavar='NAME',
                        help='read this local database instead of a file')
    parser.add_argument('--python', default=sys.executable, metavar='EXE',
                        help='interpreter that can run Odoo (default: %(default)s)')
    parser.add_argument('--odoo-bin', metavar='PATH',
                        help='odoo-bin to shell out to (default: found above this script)')
    parser.add_argument('--addons-path', metavar='PATH',
                        help="addons path for that database (default: odoo-bin's addons)")
    args = parser.parse_args()

    if args.csv and args.db:
        sys.exit('Give a file or --db, not both.')
    if not args.csv and not args.db:
        parser.print_help()
        sys.exit('\nNothing to read: pass a Contacts export, or --db NAME.')

    if args.csv:
        source = dropped_path(args.csv)
        destination = args.out or default_output(source)
        if os.path.abspath(destination) == os.path.abspath(source):
            sys.exit('That would overwrite the file it reads: %s' % source)
        rows = read_csv(source)
    else:
        rows = read_database(args)
        destination = args.out or os.path.join(HERE, 'submissions.csv')
    write_csv(destination, rows)


if __name__ == '__main__':
    main()
