"""Sort the tests of an Odoo test log into the agent's own and the existing ones.

    test_failures.py classify <log> <own_files> <new_modules>
        Print one JSON object: the agent's own tests (run, failed) and the
        existing tests (run, failed), plus `base_tags`, the --test-tags that
        re-run the failed existing tests on the base commit.
    test_failures.py failed <log>
        Print the failed tests of a log, one JSON object per line.

A test is the agent's own when it belongs to a new module, or to a test file
the agent added to an existing module (<own_files>: one path per line,
relative to the checkout, e.g. addons/stock/tests/test_printing.py). A
class whose setup fails reports one `setUpClass` failure, keyed by class with
no method.
"""
import json
import re
import sys
from pathlib import Path

# odoo.addons.<module>.tests.<file>: Starting <Class>.<method> ...
STARTED = re.compile(r' odoo\.addons\.(\w+)\.tests\.([\w.]+): Starting (\w+)\.(\w+) \.\.\.')
# odoo.addons.<module>.tests.<file>: FAIL: <Class>.<method>   (also ERROR:)
FAILED = re.compile(r' odoo\.addons\.(\w+)\.tests\.([\w.]+): (?:FAIL|ERROR): (\w+)\.(\w+)\b')
# odoo.tests.suite: ERROR: setUpClass (odoo.addons.<module>.tests.<file>.<Class>)
SETUP_FAILED = re.compile(r'(?:FAIL|ERROR): setUpClass \(odoo\.addons\.(\w+)\.tests\.([\w.]+)\.(\w+)\)')


def _path(module, file):
    return f"{module}/tests/{file.replace('.', '/')}.py"


def failed(log):
    out = []
    for line in Path(log).read_text(errors='replace').splitlines():
        if m := FAILED.search(line):
            module, file, cls, method = m.groups()
            out.append({'module': module, 'file': _path(module, file), 'class': cls, 'method': method})
        elif m := SETUP_FAILED.search(line):
            module, file, cls = m.groups()
            out.append({'module': module, 'file': _path(module, file), 'class': cls, 'method': None})
    # one entry per test
    return list({(f['module'], f['class'], f['method']): f for f in out}.values())


def started(log):
    out = {}
    for line in Path(log).read_text(errors='replace').splitlines():
        if m := STARTED.search(line):
            module, file, cls, method = m.groups()
            out[(module, cls, method)] = _path(module, file)
    return out


def classify(log, own_files, new_modules):
    own_paths = {p.strip() for p in Path(own_files).read_text().splitlines() if p.strip()}
    new = {m for m in new_modules.split(',') if m}

    def is_own(module, path):
        return module in new or any(own.endswith(path) for own in own_paths)

    run = started(log)
    fails = failed(log)
    own_run = [k for k, path in run.items() if is_own(k[0], path)]
    existing_run = [k for k, path in run.items() if not is_own(k[0], path)]
    own_failed = [f for f in fails if is_own(f['module'], f['file'])]
    existing_failed = [f for f in fails if not is_own(f['module'], f['file'])]
    tags = sorted({
        f"/{f['module']}:{f['class']}" + (f".{f['method']}" if f['method'] else '')
        for f in existing_failed
    })
    return {
        'own': {'run': len(own_run), 'failed': own_failed},
        'existing': {'run': len(existing_run), 'failed': existing_failed},
        'base_tags': ','.join(tags),
    }


if __name__ == '__main__':
    command, *args = sys.argv[1:]
    if command == 'classify':
        print(json.dumps(classify(*args)))
    elif command == 'failed':
        for f in failed(*args):
            print(json.dumps(f))
