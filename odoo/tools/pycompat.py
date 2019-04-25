# -*- coding: utf-8 -*-
# to remove if we decide to add a dependency on six or future
# very strongly inspired by https://github.com/pallets/werkzeug/blob/master/werkzeug/_compat.py
#pylint: disable=deprecated-module
import csv
import codecs
import collections
import io
import sys


PY2 = sys.version_info[0] == 2

_Writer = collections.namedtuple('_Writer', 'writerow writerows')
if PY2:
    # pylint: disable=long-builtin,unichr-builtin,unicode-builtin,undefined-variable
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

    _reader = codecs.getreader('utf-8')
    _writer = codecs.getwriter('utf-8')
    def csv_reader(stream, **params):
        assert not isinstance(stream, io.TextIOBase),\
            "For cross-compatibility purposes, csv_reader takes a bytes stream"
        return csv.reader(_reader(stream), **params)
    def csv_writer(stream, **params):
        assert not isinstance(stream, io.TextIOBase), \
            "For cross-compatibility purposes, csv_writer takes a bytes stream"
        return csv.writer(_writer(stream), **params)

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
