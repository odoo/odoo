# -*- coding: utf-8 -*-
# very strongly inspired by https://github.com/pallets/werkzeug/blob/master/werkzeug/_compat.py
#pylint: disable=deprecated-module
import csv
import codecs
import collections
import io

PY2 = False

_Writer = collections.namedtuple('_Writer', 'writerow writerows')
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
