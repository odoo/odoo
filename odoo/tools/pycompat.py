# -*- coding: utf-8 -*-
# to remove if we decide to add a dependency on six or future
# very strongly inspired by https://github.com/pallets/werkzeug/blob/master/werkzeug/_compat.py
import sys

PY2 = sys.version_info[0] == 2

if PY2:
    # pylint: disable=long-builtin,xrange-builtin
    integer_types = (int, long)

    range = xrange

    # noinspection PyUnresolvedReferences
    from itertools import imap, izip, ifilter

    def implements_iterator(cls):
        cls.next = cls.__next__
        del cls.__next__
        return cls
else:
    integer_types = (int,)

    range = range

    imap = map
    izip = zip
    ifilter = filter

    def implements_iterator(cls):
        return cls
