##
# <p>Copyright (c) 2006-2012 Stephen John Machin, Lingfo Pty Ltd</p>
# <p>This module is part of the xlrd package, which is released under a BSD-style licence.</p>
##

# timemachine.py -- adaptation for single codebase.
# Currently supported: 2.6 to 2.7, 3.2+
# usage: from timemachine import *

from __future__ import print_function

import sys

python_version = sys.version_info[:2] # e.g. version 2.6 -> (2, 6)

if python_version >= (3, 0):
    # Python 3
    BYTES_LITERAL = lambda x: x.encode('latin1')
    UNICODE_LITERAL = lambda x: x
    BYTES_ORD = lambda byte: byte
    from io import BytesIO as BYTES_IO
    def fprintf(f, fmt, *vargs):
        fmt = fmt.replace("%r", "%a")
        if fmt.endswith('\n'):
            print(fmt[:-1] % vargs, file=f)
        else:
            print(fmt % vargs, end=' ', file=f)
    EXCEL_TEXT_TYPES = (str, bytes, bytearray) # xlwt: isinstance(obj, EXCEL_TEXT_TYPES)
    REPR = ascii
    xrange = range
    unicode = lambda b, enc: b.decode(enc)
    ensure_unicode = lambda s: s
    unichr = chr
else:
    # Python 2
    BYTES_LITERAL = lambda x: x
    UNICODE_LITERAL = lambda x: x.decode('latin1')
    BYTES_ORD = ord
    from cStringIO import StringIO as BYTES_IO
    def fprintf(f, fmt, *vargs):
        if fmt.endswith('\n'):
            print(fmt[:-1] % vargs, file=f)
        else:
            print(fmt % vargs, end=' ', file=f)
    try:
        EXCEL_TEXT_TYPES = basestring # xlwt: isinstance(obj, EXCEL_TEXT_TYPES)
    except NameError:
        EXCEL_TEXT_TYPES = (str, unicode)
    REPR = repr
    xrange = xrange
    # following used only to overcome 2.x ElementTree gimmick which
    # returns text as `str` if it's ascii, otherwise `unicode`
    ensure_unicode = unicode # used only in xlsx.py
