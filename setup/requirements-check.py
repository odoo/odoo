#!/usr/bin/env python
"""
Checks versions from the requirements files against distribution-provided
versions, taking distribution's Python version in account e.g. if checking
against a release which bundles Python 3.5, checks the 3.5 version of
requirements.

* only shows requirements for which at least one release diverges from the
  matching requirements version
* empty cells mean that specific release matches its requirement (happens when
  checking multiple releases: one of the other releases may mismatch the its
  requirements necessating showing the row)

Only handles the subset of requirements files we're currently using:
* no version spec or strict equality
* no extras
* only sys_platform and python_version environment markers
"""

import argparse
import gzip
import itertools
import json
import operator
import re
import string

from abc import ABC, abstractmethod
from pathlib import Path
from urllib.request import urlopen
from sys import stdout, stderr
from typing import Dict, List, Set, Optional, Any, Tuple

Version = Tuple[int, ...]
def parse_version(vstring: str) -> Optional[Version]:
    if not vstring:
        return None
    return tuple(map(int, vstring.split('.')))

# shared beween debian and ubuntu
SPECIAL = {
    'pytz': 'tz',
    'libsass': 'libsass-python',
}
def unfuck(s: str) -> str:
    """ Try to strip the garbage from the version string, just remove everything
    following the first `+`, `~` or `-`
    """
    return re.match(r'''
        (?:\d+:)? # debian crud prefix
        (.*?) # the shit we actually want
        (?:~|\+|-|\.dfsg)
        .*
    ''', s, flags=re.VERBOSE)[1]

class Distribution(ABC):
    def __init__(self, release):
        self._release = release

    @abstractmethod
    def get_version(self, package: str) -> Optional[Version]:
        ...

    def __str__(self):
        return f'{type(self).__name__.lower()} {self._release}'

    @classmethod
    def get(cls, name):
        try:
            return next(
                c
                for c in cls.__subclasses__()
                if c.__name__.lower() == name
            )
        except StopIteration:
            raise ValueError(f"Unknown distribution {name!r}")

class Debian(Distribution):
    def get_version(self, package):
        """ Try to find which version of ``package`` is in Debian release {release}
        """
        package = SPECIAL.get(package, package)
        # try the python prefix first: some packages have a native of foreign $X and
        # either the bindings or a python equivalent at python-X, or just a name
        # collision
        for prefix in ['python-', '']:
            res = json.load(urlopen(f'https://sources.debian.org/api/src/{prefix}{package}'))
            if res.get('error') is None:
                break
        if res.get('error'):
            return

        return next(
            parse_version(unfuck(distr['version']))
            for distr in res['versions']
            if distr['area'] == 'main'
            if self._release in distr['suites']
        )

class Ubuntu(Distribution):
    """ Ubuntu doesn't have an API, instead it has a huge text file
    """
    def __init__(self, release):
        super().__init__(release)

        self._packages = {}
        # ideally we should request the proper Content-Encoding but PUC
        # apparently does not care, and returns a somewhat funky
        # content-encoding (x-gzip) anyway
        data = gzip.open(
            urlopen(f'https://packages.ubuntu.com/source/{release}/allpackages?format=txt.gz'),
            mode='rt', encoding='utf-8'
        )
        for line in itertools.islice(data, 6, None): # first 6 lines is garbage header
            # ignore the restricted, security, universe, multiverse tags
            m = re.match(r'(\S+) \(([^)]+)\)', line.strip())
            assert m, f"invalid line {line.strip()!r}"
            self._packages[m[1]] = m[2]

    def get_version(self, package):
        package = SPECIAL.get(package, package)
        for prefix in ['python3-', 'python-', '']:
            v = self._packages.get(f'{prefix}{package}')
            if v:
                return parse_version(unfuck(v))
        return None

class Markers:
    """ Simplistic RD parser for requirements env markers.

    Evaluation of the env markers is so basic it goes to brunch in uggs.
    """
    def __init__(self, s=None):
        self.rules = False
        if s is not None:
            self.rules, rest = self._parse_marker(s)
            assert not rest

    def evaluate(self, context: Dict[str, Any]) -> bool:
        if not self.rules:
            return True
        return self._eval(self.rules, context)

    def _eval(self, rule, context):
        if rule[0] == 'OR':
            return self._eval(rule[1], context) or self._eval(rule[2], context)
        elif rule[0] == 'AND':
            return self._eval(rule[1], context) and self._eval(rule[2], context)
        elif rule[0] == 'ENV':
            return context[rule[1]]
        elif rule[0] == 'LIT':
            return rule[1]
        else:
            op, var1, var2 = rule
            var1 = self._eval(var1, context)
            var2 = self._eval(var2, context)

            # NOTE: currently doesn't follow PEP440 version matching at all
            if op == '==': return var1 == var2
            elif op == '!=': return var1 != var2
            elif op == '<': return var1 < var2
            elif op == '<=': return var1 <= var2
            elif op == '>': return var1 > var2
            elif op == '>=': return var1 >= var2
            else:
                raise NotImplementedError(f"Operator {op!r}")

    def _parse_marker(self, s):
        return self._parse_or(s)

    def _parse_or(self, s):
        sub1, rest = self._parse_and(s)
        expr, n = re.subn(r'^\s*or\b', '', rest, count=1)
        if not n:
            return sub1, rest
        sub2, rest = self._parse_and(expr)
        return ('OR', sub1, sub2), rest

    def _parse_and(self, s):
        sub1, rest = self._parse_expr(s)
        expr, n = re.subn(r'\s*and\b', '', rest, count=1)
        if not n:
            return sub1, rest
        sub2, rest = self._parse_expr(expr)
        return ('AND', sub1, sub2), rest

    def _parse_expr(self, s):
        expr, n = re.subn(r'^\s*\(', '', s, count=1)
        if n:
            sub, rest = self.parse_marker(expr)
            rest, n = re.subn(r'\s*\)', '', rest, count=1)
            assert n, f"expected closing parenthesis, found {rest}"
            return sub, rest

        var1, rest = self._parse_var(s)
        op, rest = self._parse_op(rest)
        var2, rest = self._parse_var(rest)
        return (op, var1, var2), rest

    def _parse_op(self, s):
        m = re.match(r'''
            \s*
            (<= | < | != | >= | > | ~= | ===? | in \b | not \s+ in \b)
            (.*)
        ''', s, re.VERBOSE)
        assert m, f"no operator in {s!r}"
        return m.groups()

    def _parse_var(self, s):
        python_str = re.escape(string.printable.translate(str.maketrans({
            '"': '',
            "'": '',
            '\\': '',
            '-': '',
        })))
        m = re.match(fr'''
            \s*
            (:?
                # TODO: add more envvars
                (?P<env>python_version | os_name | sys_platform)
              | " (?P<dquote>['{python_str}-]*) "
              | ' (?P<squote>["{python_str}-]*) '
            )
            (?P<rest>.*)
        ''', s, re.VERBOSE)
        assert m, f"failed to find marker var in {s}"
        if m['env']:
            return ('ENV', m['env']), m['rest']
        return ('LIT', m['dquote'] or m['squote'] or ''), m['rest']

def parse_spec(line: str) -> (str, (Optional[str], Optional[str]), Markers):
    """ Parse a requirements specification (a line of requirements)

    Returns the package name, a version spec (operator and comparator) possibly
    None and a Markers object.

    Not correctly supported:

    * version matching, not all operators are implemented and those which are
      almost certainly don't match PEP 440

    Not supported:

    * url requirements
    * multi-versions spec
    * extras
    * continuations

    Full grammar is at https://www.python.org/dev/peps/pep-0508/#complete-grammar
    """
    # weirdly a distribution name can apparently start with a number
    name, rest = re.match(r'([\w\d](?:[._-]*[\w\d]+)*)\s*(.*)', line.strip()).groups()
    # skipping extras
    version_cmp = version = None
    versionspec = re.match(r'''
        (< | <= | != | == | >= | > | ~= | ===)
        \s*
        ([\w\d_.*+!-]+)
        \s*
        (.*)
    ''', rest, re.VERBOSE)
    if versionspec:
        version_cmp, version, rest = versionspec.groups()
    markers = Markers()
    if rest[:1] == ';':
        markers = Markers(rest[1:])

    return name, (version_cmp, version), markers

def parse_requirements(reqpath: Path) -> Dict[str, List[Tuple[str, Markers]]]:
    """ Parses a requirement file to a dict of {package: [(version, markers)]}

    The env markers express *whether* that specific dep applies.
    """
    reqs = {}
    for line in reqpath.open('r', encoding='utf-8'):
        if line.isspace() or line.startswith('#'):
            continue

        name, (op, version), markers = parse_spec(line)
        assert op is None or op == '==', f"unexpected version comparator {op}"
        reqs.setdefault(name, []).append((version, markers))
    return reqs

def main(args):
    checkers = [
        Distribution.get(distro)(release)
        for version in args.release
        for (distro, release) in [version.split(':')]
    ]

    stderr.write(f"Fetch Python versions...\n")
    pyvers = [
        '.'.join(map(str, checker.get_version('python3-defaults')[:2]))
        for checker in checkers
    ]

    uniq = sorted(v for v in set(pyvers))
    table = [
        ['']
        + [f'req {v}' for v in uniq]
        + [f'{checker._release} ({version})' for checker, version in zip(checkers, pyvers)]
    ]

    reqs = parse_requirements((Path.cwd() / __file__).parent.parent / 'requirements.txt')
    tot = len(reqs) * len(checkers)

    def progress(n=iter(range(tot+1))):
        stderr.write(f"\rFetch requirements: {next(n)} / {tot}")

    progress()
    for req, options in reqs.items():
        row = [req]
        byver = {}
        for pyver in uniq:
            # FIXME: when multiple options apply, check which pip uses
            #        (first-matching. best-matching, latest, ...)
            for version, markers in options:
                if markers.evaluate({
                    'python_version': pyver,
                    'sys_platform': 'linux',
                }):
                    byver[pyver] = version
                    break
            row.append(byver.get(pyver) or '')
        # this requirement doesn't apply, ignore
        if not byver:
            # normally the progressbar is updated when processing each
            # requirement against each checker, if the requirement doesn't apply
            # to any checker we still need to consider the requirement fetched /
            # resolved for each checker or our tally is incorrect
            for _ in checkers:
                progress()
            continue

        mismatch = False
        for i, c in enumerate(checkers):
            req_version = byver.get(pyvers[i], '')
            check_version = '.'.join(map(str, c.get_version(req.lower()) or ['<missing>']))
            progress()
            if req_version != check_version:
                row.append(check_version)
                mismatch = True
            else:
                row.append('')

        # only show row if one of the items diverges from requirement
        if mismatch:
            table.append(row)
    stderr.write('\n')

    # evaluate width of columns
    sizes = [0] * (len(checkers) + len(uniq) + 1)
    for row in table:
        sizes = [
            max(s, len(cell))
            for s, cell in zip(sizes, row)
        ]

    # format table
    for row in table:
        stdout.write('| ')
        for cell, width in zip(row, sizes):
            stdout.write(f'{cell:<{width}} | ')
        stdout.write('\n')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        'release', nargs='+',
        help="Release to check against, should use the format '{distro}:{release}' e.g. 'debian:sid'"
    )
    args = parser.parse_args()
    main(args)
