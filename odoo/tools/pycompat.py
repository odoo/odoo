# -*- coding: utf-8 -*-
# to remove if we decide to add a dependency on six or future
# very strongly inspired by https://github.com/pallets/werkzeug/blob/master/werkzeug/_compat.py
import sys

PY2 = sys.version_info[0] == 2

if PY2:
    # pylint: disable=long-builtin,dict-iter-method
    integer_types = (int, long)
    round = round

    keys = lambda d: iter(d.iterkeys())
    values = lambda d: iter(d.itervalues())
    items = lambda d: iter(d.iteritems())

    # noinspection PyUnresolvedReferences
    from itertools import imap, izip, ifilter

    def implements_iterator(cls):
        cls.next = cls.__next__
        del cls.__next__
        return cls

    exec ('def reraise(tp, value, tb=None):\n raise tp, value, tb')
else:
    import builtins, math
    # pylint: disable=bad-functions
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

    def implements_iterator(cls):
        return cls

    def reraise(tp, value, tb=None):
        if value.__traceback__ != tb:
            raise value.with_traceback(tb)
        raise value
