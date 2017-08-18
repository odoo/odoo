# -*- coding: utf-8 -*-
# to remove if we decide to add a dependency on six or future
# very strongly inspired by https://github.com/pallets/werkzeug/blob/master/werkzeug/_compat.py
#pylint: disable=deprecated-module
import csv
import collections
import io
import sys


PY2 = sys.version_info[0] == 2

_Writer = collections.namedtuple('_Writer', 'writerow writerows')
if PY2:
    # pylint: disable=long-builtin,unichr-builtin,unicode-builtin
    unichr = unichr
    text_type = unicode
    string_types = (str, unicode)
    def to_native(source, encoding='utf-8', falsy_empty=False):
        if not source and falsy_empty:
            return ''

        if isinstance(source, text_type):
            return source.encode(encoding)

        return str(source)

    integer_types = (int, long)
    round = round

    keys = lambda d: iter(d.iterkeys())
    values = lambda d: iter(d.itervalues())
    items = lambda d: iter(d.iteritems())

    # noinspection PyUnresolvedReferences
    from itertools import imap, izip, ifilter

    def implements_to_string(cls):
        cls.__unicode__ = cls.__str__
        cls.__str__ = lambda x: x.__unicode__().encode('utf-8')
        return cls

    def implements_iterator(cls):
        cls.next = cls.__next__
        del cls.__next__
        return cls

    exec ('def reraise(tp, value, tb=None):\n raise tp, value, tb')

    def csv_reader(stream, **params):
        for row in csv.reader(stream, **params):
            yield [c.decode('utf-8') for c in row]
    def csv_writer(stream, **params):
        w = csv.writer(stream, **params)
        return _Writer(
            writerow=lambda r: w.writerow([c.encode('utf-8') for c in r]),
            writerows=lambda rs: w.writerows(
                [c.encode('utf-8') for c in r]
                for r in rs
            )
        )
else:
    import builtins, math
    # pylint: disable=bad-functions
    unichr = chr
    text_type = str
    string_types = (str,)
    def to_native(source, encoding='utf-8', falsy_empty=False):
        if not source and falsy_empty:
            return ''

        if isinstance(source, bytes):
            return source.decode(encoding)

        return str(source)

    integer_types = (int,)
    def round(f):
        # P3's builtin round differs from P2 in the following manner:
        # * it rounds half to even rather than up (away from 0)
        # * round(-0.) loses the sign (it returns -0 rather than 0)
        # * round(x) returns an int rather than a float
        #
        # this compatibility shim implements Python 2's round in terms of
        # Python 3's so that important rounding error under P3 can be
        # trivially fixed, assuming the P2 behaviour to be debugged and
        # correct.
        roundf = builtins.round(f)
        if builtins.round(f + 1) - roundf != 1:
            return f + math.copysign(0.5, f)
        # copysign ensures round(-0.) -> -0 *and* result is a float
        return math.copysign(roundf, f)

    keys = lambda d: iter(d.keys())
    values = lambda d: iter(d.values())
    items = lambda d: iter(d.items())

    imap = map
    izip = zip
    ifilter = filter

    def implements_to_string(cls):
        return cls

    def implements_iterator(cls):
        return cls

    def reraise(tp, value, tb=None):
        if value.__traceback__ != tb:
            raise value.with_traceback(tb)
        raise value

    def csv_reader(stream, **params):
        assert not isinstance(stream, io.TextIOBase),\
            "For cross-compatibility purposes, csv_reader takes a bytes stream"
        return csv.reader(io.TextIOWrapper(stream, encoding='utf-8'), **params)
    def csv_writer(stream, **params):
        assert not isinstance(stream, io.TextIOBase), \
            "For cross-compatibility purposes, csv_writer takes a bytes stream"
        return csv.writer(io.TextIOWrapper(stream, encoding='utf-8', line_buffering=True), **params)

def to_text(source):
    """ Generates a text value (an instance of text_type) from an arbitrary 
    source.
    
    * False and None are converted to empty strings
    * text is passed through
    * bytes are decoded as UTF-8
    * rest is textified via the current version's relevant data model method
    """
    if source is None or source is False:
        return u''

    if isinstance(source, bytes):
        return source.decode('utf-8')

    return text_type(source)
