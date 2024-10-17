# numdb.py - module for handling hierarchically organised numbers
#
# Copyright (C) 2010-2019 Arthur de Jong
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301 USA

"""Query structured number format files with number properties.

This module contains functions for reading and querying a database that
stores numbers that use a hierarchical format (e.g. ISBN, IBAN, phone
numbers, etc).

To read a database from a file:

>>> with open('tests/numdb-test.dat', 'r') as f:
...     dbfile = read(f)

To split a number:

>>> dbfile.split('01006')
['0', '100', '6']
>>> dbfile.split('902006')
['90', '20', '06']
>>> dbfile.split('909856')
['90', '985', '6']

To split the number and get properties for each part:

>>> dbfile.info('01006') == [
...     ('0',   {'prop1': 'foo'}),
...     ('100', {'prop2': 'bar'}),
...     ('6',   {}),
... ]
True
>>> dbfile.info('02006') == [
...     ('0',   {'prop1': 'foo'}),
...     ('200', {'prop2': 'bar', 'prop3': 'baz'}),
...     ('6',   {}),
... ]
True
>>> dbfile.info('03456') == [
...     ('0', {'prop1': 'foo'}),
...     ('345', {'prop2': 'bar', 'prop3': 'baz'}),
...     ('6', {}),
... ]
True
>>> dbfile.info('902006') == [
...     ('90', {'prop1': 'booz'}),
...     ('20', {'prop2': 'foo'}),
...     ('06', {}),
... ]
True
>>> dbfile.info('909856') == [
...     ('90', {'prop1': 'booz'}),
...     ('985', {'prop2': 'fooz'}),
...     ('6', {}),
... ]
True
>>> dbfile.info('9889') == [
...     ('98', {'prop1': 'booz'}),
...     ('89', {'prop2': 'foo'}),
... ]
True
>>> dbfile.info('633322') == [
...     ('6', {'prop1': 'boo'}),
...     ('333', {'prop2': 'bar', 'prop3': 'baz', 'prop4': 'bla'}),
...     ('22', {}),
... ]
True

"""

import re

from pkg_resources import resource_stream


_line_re = re.compile(
    r'^(?P<indent> *)'
    r'(?P<ranges>([^-,\s]+(-[^-,\s]+)?)(,[^-,\s]+(-[^-,\s]+)?)*)\s*'
    r'(?P<props>.*)$')
_prop_re = re.compile(
    r'(?P<prop>[0-9a-zA-Z-_]+)="(?P<value>[^"]*)"')

# this is a cache of open databases
_open_databases = {}

# the prefixes attribute of NumDB is structured as follows:
# prefixes = [
#   [ length, low, high, props, children ]
#   ...
# ]
# where children is a prefixes structure in its own right
# (there is no expected ordering within the list)


class NumDB():
    """Number database."""

    def __init__(self):
        """Construct an empty database."""
        self.prefixes = []

    @staticmethod
    def _merge(results):
        """Merge the provided list of possible results into a single result
        list (this is a generator)."""
        # expand the results to all have the same length
        ml = max(len(x) for x in results)
        results = [x + (ml - len(x)) * [None]
                   for x in results]
        # go over each part
        for parts in zip(*results):
            # regroup parts into parts list and properties list
            partlist, proplist = list(zip(*(x for x in parts if x)))
            part = min(partlist, key=len)
            props = {}
            for p in proplist:
                props.update(p)
            yield part, props

    @staticmethod
    def _find(number, prefixes):
        """Lookup the specified number in the list of prefixes, this will
        return basically what info() should return but works recursively."""
        if not number:
            return []
        results = []
        if prefixes:
            for length, low, high, props, children in prefixes:
                if low <= number[:length] <= high and len(number) >= length:
                    results.append([(number[:length], props)] +
                                   NumDB._find(number[length:], children))
        # not-found fallback
        if not results:
            return [(number, {})]
        # merge the results into a single result
        return list(NumDB._merge(results))

    def info(self, number):
        """Split the provided number in components and associate properties
        with each component. This returns a tuple of tuples. Each tuple
        consists of a string (a part of the number) and a dict of properties.
        """
        return NumDB._find(number, self.prefixes)

    def split(self, number):
        """Split the provided number in components. This returns a tuple with
        the number of components identified."""
        return [part for part, props in self.info(number)]


def _parse(fp):
    """Read lines of text from the file pointer and generate indent, length,
    low, high, properties tuples."""
    for line in fp:
        # ignore comments
        if line[0] == '#' or line.strip() == '':
            continue  # pragma: no cover (optimisation takes it out)
        # any other line should parse
        match = _line_re.search(line)
        indent = len(match.group('indent'))
        ranges = match.group('ranges')
        props = dict(_prop_re.findall(match.group('props')))
        for rnge in ranges.split(','):
            if '-' in rnge:
                low, high = rnge.split('-')
            else:
                low, high = rnge, rnge
            yield indent, len(low), low, high, props


def read(fp):
    """Return a new database with the data read from the specified file."""
    last_indent = 0
    db = NumDB()
    stack = {0: db.prefixes}
    for indent, length, low, high, props in _parse(fp):
        if indent > last_indent:
            # populate the children field of the last indent
            stack[last_indent][-1][4] = []
            stack[indent] = stack[last_indent][-1][4]
        stack[indent].append([length, low, high, props, None])
        last_indent = indent
    return db


def get(name):
    """Open a database with the specified name to perform queries on."""
    if name not in _open_databases:
        import codecs
        reader = codecs.getreader('utf-8')
        with reader(resource_stream(__name__, name + '.dat')) as fp:
            _open_databases[name] = read(fp)
    return _open_databases[name]
