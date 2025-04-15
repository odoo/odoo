# Copyright (c) 2006, Mathieu Fenniak
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# * Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
# * The name of the author may not be used to endorse or promote products
# derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
Utility functions for PDF library.
"""
__author__ = "Mathieu Fenniak"
__author_email__ = "biziqe@mathieu.fenniak.net"


import sys

try:
    import __builtin__ as builtins
except ImportError:  # Py3
    import builtins


xrange_fn = getattr(builtins, "xrange", range)
_basestring = getattr(builtins, "basestring", str)

bytes_type = type(bytes()) # Works the same in Python 2.X and 3.X
string_type = getattr(builtins, "unicode", str)
int_types = (int, long) if sys.version_info[0] < 3 else (int,)


# Make basic type tests more consistent
def isString(s):
    """Test if arg is a string. Compatible with Python 2 and 3."""
    return isinstance(s, _basestring)


def isInt(n):
    """Test if arg is an int. Compatible with Python 2 and 3."""
    return isinstance(n, int_types)


def isBytes(b):
    """Test if arg is a bytes instance. Compatible with Python 2 and 3."""
    return isinstance(b, bytes_type)


#custom implementation of warnings.formatwarning
def formatWarning(message, category, filename, lineno, line=None):
    file = filename.replace("/", "\\").rsplit("\\", 1)[1] # find the file name
    return "%s: %s [%s:%s]\n" % (category.__name__, message, file, lineno)


def readUntilWhitespace(stream, maxchars=None):
    """
    Reads non-whitespace characters and returns them.
    Stops upon encountering whitespace or when maxchars is reached.
    """
    txt = b_("")
    while True:
        tok = stream.read(1)
        if tok.isspace() or not tok:
            break
        txt += tok
        if len(txt) == maxchars:
            break
    return txt


def readNonWhitespace(stream):
    """
    Finds and reads the next non-whitespace character (ignores whitespace).
    """
    tok = WHITESPACES[0]
    while tok in WHITESPACES:
        tok = stream.read(1)
    return tok


def skipOverWhitespace(stream):
    """
    Similar to readNonWhitespace, but returns a Boolean if more than
    one whitespace character was read.
    """
    tok = WHITESPACES[0]
    cnt = 0;
    while tok in WHITESPACES:
        tok = stream.read(1)
        cnt+=1
    return (cnt > 1)


def skipOverComment(stream):
    tok = stream.read(1)
    stream.seek(-1, 1)
    if tok == b_('%'):
        while tok not in (b_('\n'), b_('\r')):
            tok = stream.read(1)


def readUntilRegex(stream, regex, ignore_eof=False):
    """
    Reads until the regular expression pattern matched (ignore the match)
    Raise PdfStreamError on premature end-of-file.
    :param bool ignore_eof: If true, ignore end-of-line and return immediately
    """
    name = b_('')
    while True:
        tok = stream.read(16)
        if not tok:
            # stream has truncated prematurely
            if ignore_eof == True:
                return name
            else:
                raise PdfStreamError("Stream has ended unexpectedly")
        m = regex.search(tok)
        if m is not None:
            name += tok[:m.start()]
            stream.seek(m.start()-len(tok), 1)
            break
        name += tok
    return name


class ConvertFunctionsToVirtualList(object):
    def __init__(self, lengthFunction, getFunction):
        self.lengthFunction = lengthFunction
        self.getFunction = getFunction

    def __len__(self):
        return self.lengthFunction()

    def __getitem__(self, index):
        if isinstance(index, slice):
            indices = xrange_fn(*index.indices(len(self)))
            cls = type(self)
            return cls(indices.__len__, lambda idx: self[indices[idx]])
        if not isInt(index):
            raise TypeError("sequence indices must be integers")
        len_self = len(self)
        if index < 0:
            # support negative indexes
            index = len_self + index
        if index < 0 or index >= len_self:
            raise IndexError("sequence index out of range")
        return self.getFunction(index)


def RC4_encrypt(key, plaintext):
    S = [i for i in range(256)]
    j = 0
    for i in range(256):
        j = (j + S[i] + ord_(key[i % len(key)])) % 256
        S[i], S[j] = S[j], S[i]
    i, j = 0, 0
    retval = b_("")
    for x in range(len(plaintext)):
        i = (i + 1) % 256
        j = (j + S[i]) % 256
        S[i], S[j] = S[j], S[i]
        t = S[(S[i] + S[j]) % 256]
        retval += b_(chr(ord_(plaintext[x]) ^ t))
    return retval


def matrixMultiply(a, b):
    return [[sum([float(i)*float(j)
                  for i, j in zip(row, col)]
                ) for col in zip(*b)]
            for row in a]


def markLocation(stream):
    """Creates text file showing current location in context."""
    # Mainly for debugging
    RADIUS = 5000
    stream.seek(-RADIUS, 1)
    outputDoc = open('PyPDF2_pdfLocation.txt', 'w')
    outputDoc.write(stream.read(RADIUS))
    outputDoc.write('HERE')
    outputDoc.write(stream.read(RADIUS))
    outputDoc.close()
    stream.seek(-RADIUS, 1)


class PyPdfError(Exception):
    pass


class PdfReadError(PyPdfError):
    pass


class PageSizeNotDefinedError(PyPdfError):
    pass


class PdfReadWarning(UserWarning):
    pass


class PdfStreamError(PdfReadError):
    pass


if sys.version_info[0] < 3:
    def b_(s):
        return s
else:
    B_CACHE = {}

    def b_(s):
        bc = B_CACHE
        if s in bc:
            return bc[s]
        if type(s) == bytes:
            return s
        else:
            r = s.encode('latin-1')
            if len(s) < 2:
                bc[s] = r
            return r


def u_(s):
    if sys.version_info[0] < 3:
        return unicode(s, 'unicode_escape')
    else:
        return s


def str_(b):
    if sys.version_info[0] < 3:
        return b
    else:
        if type(b) == bytes:
            return b.decode('latin-1')
        else:
            return b


def ord_(b):
    if sys.version_info[0] < 3 or type(b) == str:
        return ord(b)
    else:
        return b


def chr_(c):
    if sys.version_info[0] < 3:
        return c
    else:
        return chr(c)


def barray(b):
    if sys.version_info[0] < 3:
        return b
    else:
        return bytearray(b)


def hexencode(b):
    if sys.version_info[0] < 3:
        return b.encode('hex')
    else:
        import codecs
        coder = codecs.getencoder('hex_codec')
        return coder(b)[0]


def hexStr(num):
    return hex(num).replace('L', '')


WHITESPACES = [b_(x) for x in [' ', '\n', '\r', '\t', '\x00']]
