# -*- coding: utf-8 -*-
# to remove if we decide to add a dependency on six or future
# very strongly inspired by https://github.com/pallets/werkzeug/blob/master/werkzeug/_compat.py
import sys

PY2 = sys.version_info[0] == 2

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
