#
# Copyright (c) 1996-2000 Tyler C. Sarna <tsarna@sarna.org>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. All advertising materials mentioning features or use of this software
#    must display the following acknowledgement:
#      This product includes software developed by Tyler C. Sarna.
# 4. Neither the name of the author nor the names of contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#

from reportlab.lib.units import inch
from reportlab.lib.utils import asNative
from reportlab.graphics.barcode.common import Barcode
from string import ascii_uppercase, ascii_lowercase, digits as string_digits

_patterns = {
    '0':    ("bsbSBsBsb", 0),       '1': ("BsbSbsbsB", 1),
    '2':    ("bsBSbsbsB", 2),       '3': ("BsBSbsbsb", 3),
    '4':    ("bsbSBsbsB", 4),       '5': ("BsbSBsbsb", 5),
    '6':    ("bsBSBsbsb", 6),       '7': ("bsbSbsBsB", 7),
    '8':    ("BsbSbsBsb", 8),       '9': ("bsBSbsBsb", 9),
    'A':    ("BsbsbSbsB", 10),      'B': ("bsBsbSbsB", 11),
    'C':    ("BsBsbSbsb", 12),      'D': ("bsbsBSbsB", 13),
    'E':    ("BsbsBSbsb", 14),      'F': ("bsBsBSbsb", 15),
    'G':    ("bsbsbSBsB", 16),      'H': ("BsbsbSBsb", 17),
    'I':    ("bsBsbSBsb", 18),      'J': ("bsbsBSBsb", 19),
    'K':    ("BsbsbsbSB", 20),      'L': ("bsBsbsbSB", 21),
    'M':    ("BsBsbsbSb", 22),      'N': ("bsbsBsbSB", 23),
    'O':    ("BsbsBsbSb", 24),      'P': ("bsBsBsbSb", 25),
    'Q':    ("bsbsbsBSB", 26),      'R': ("BsbsbsBSb", 27),
    'S':    ("bsBsbsBSb", 28),      'T': ("bsbsBsBSb", 29),
    'U':    ("BSbsbsbsB", 30),      'V': ("bSBsbsbsB", 31),
    'W':    ("BSBsbsbsb", 32),      'X': ("bSbsBsbsB", 33),
    'Y':    ("BSbsBsbsb", 34),      'Z': ("bSBsBsbsb", 35),
    '-':    ("bSbsbsBsB", 36),      '.': ("BSbsbsBsb", 37),
    ' ':    ("bSBsbsBsb", 38),      '*': ("bSbsBsBsb", None),
    '$':    ("bSbSbSbsb", 39),      '/': ("bSbSbsbSb", 40),
    '+':    ("bSbsbSbSb", 41),      '%': ("bsbSbSbSb", 42)
    }

_stdchrs = string_digits + ascii_uppercase + "-. $/+%"

_extended = {
    '\0':   "%U",    '\01':  "$A",    '\02':  "$B",    '\03':  "$C",
    '\04':  "$D",    '\05':  "$E",    '\06':  "$F",    '\07':  "$G",
    '\010': "$H",    '\011': "$I",    '\012': "$J",    '\013': "$K",
    '\014': "$L",    '\015': "$M",    '\016': "$N",    '\017': "$O",
    '\020': "$P",    '\021': "$Q",    '\022': "$R",    '\023': "$S",
    '\024': "$T",    '\025': "$U",    '\026': "$V",    '\027': "$W",
    '\030': "$X",    '\031': "$Y",    '\032': "$Z",    '\033': "%A",
    '\034': "%B",    '\035': "%C",    '\036': "%D",    '\037': "%E",
    '!':    "/A",    '"':    "/B",    '#':    "/C",    '$':    "/D",
    '%':    "/E",    '&':    "/F",    '\'':   "/G",    '(':    "/H",
    ')':    "/I",    '*':    "/J",    '+':    "/K",    ',':    "/L",
    '/':    "/O",    ':':    "/Z",    ';':    "%F",    '<':    "%G",
    '=':    "%H",    '>':    "%I",    '?':    "%J",    '@':    "%V",
    '[':    "%K",    '\\':   "%L",    ']':    "%M",    '^':    "%N",
    '_':    "%O",    '`':    "%W",    'a':    "+A",    'b':    "+B",
    'c':    "+C",    'd':    "+D",    'e':    "+E",    'f':    "+F",
    'g':    "+G",    'h':    "+H",    'i':    "+I",    'j':    "+J",
    'k':    "+K",    'l':    "+L",    'm':    "+M",    'n':    "+N",
    'o':    "+O",    'p':    "+P",    'q':    "+Q",    'r':    "+R",
    's':    "+S",    't':    "+T",    'u':    "+U",    'v':    "+V",
    'w':    "+W",    'x':    "+X",    'y':    "+Y",    'z':    "+Z",
    '{':    "%P",    '|':    "%Q",    '}':    "%R",    '~':    "%S",
    '\177': "%T"
    }


_extchrs = _stdchrs + ascii_lowercase + \
    "\000\001\002\003\004\005\006\007\010\011\012\013\014\015\016\017" + \
    "\020\021\022\023\024\025\026\027\030\031\032\033\034\035\036\037" + \
    "*!'#&\"(),:;<=>?@[\\]^_`{|}~\177"

def _encode39(value, cksum, stop):
    v = sum([_patterns[c][1] for c in value]) % 43
    if cksum:
        value += _stdchrs[v]
    if stop: value = '*'+value+'*'
    return value

class _Code39Base(Barcode):
    barWidth = inch * 0.0075
    lquiet = None
    rquiet = None
    quiet = 1
    gap = None
    barHeight = None
    ratio = 2.2
    checksum = 1
    bearers = 0.0
    stop = 1
    def __init__(self, value = "", **args):
        value = asNative(value)
        for k, v in args.items():
            setattr(self, k, v)

        if self.quiet:
            if self.lquiet is None:
                self.lquiet = max(inch * 0.25, self.barWidth * 10.0)
                self.rquiet = max(inch * 0.25, self.barWidth * 10.0)
        else:
            self.lquiet = self.rquiet = 0.0

        Barcode.__init__(self, value)

    def decompose(self):
        dval = ""
        for c in self.encoded:
            dval = dval + _patterns[c][0] + 'i'
        self.decomposed = dval[:-1]
        return self.decomposed

    def _humanText(self):
        return self.stop and self.encoded[1:-1] or self.encoded

class Standard39(_Code39Base):
    """
    Options that may be passed to constructor:

        value (int, or numeric string required.):
            The value to encode.

        barWidth (float, default .0075):
            X-Dimension, or width of the smallest element
            Minumum is .0075 inch (7.5 mils).

        ratio (float, default 2.2):
            The ratio of wide elements to narrow elements.
            Must be between 2.0 and 3.0 (or 2.2 and 3.0 if the
            barWidth is greater than 20 mils (.02 inch))

        gap (float or None, default None):
            width of intercharacter gap. None means "use barWidth".

        barHeight (float, see default below):
            Height of the symbol.  Default is the height of the two
            bearer bars (if they exist) plus the greater of .25 inch
            or .15 times the symbol's length.

        checksum (bool, default 1):
            Wether to compute and include the check digit

        bearers (float, in units of barWidth. default 0):
            Height of bearer bars (horizontal bars along the top and
            bottom of the barcode). Default is 0 (no bearers).

        quiet (bool, default 1):
            Wether to include quiet zones in the symbol.

        lquiet (float, see default below):
            Quiet zone size to left of code, if quiet is true.
            Default is the greater of .25 inch, or .15 times the symbol's
            length.

        rquiet (float, defaults as above):
            Quiet zone size to right left of code, if quiet is true.

        stop (bool, default 1):
            Whether to include start/stop symbols.

    Sources of Information on Code 39:

    http://www.semiconductor.agilent.com/barcode/sg/Misc/code_39.html
    http://www.adams1.com/pub/russadam/39code.html
    http://www.barcodeman.com/c39_1.html

    Official Spec, "ANSI/AIM BC1-1995, USS" is available for US$45 from
    http://www.aimglobal.org/aimstore/
    """
    def validate(self):
        vval = [].append
        self.valid = 1
        for c in self.value:
            if c in ascii_lowercase:
                c = c.upper()
            if c not in _stdchrs:
                self.valid = 0
                continue
            vval(c)
        self.validated = ''.join(vval.__self__)
        return self.validated

    def encode(self):
        self.encoded = _encode39(self.validated, self.checksum, self.stop)
        return self.encoded

class Extended39(_Code39Base):
    """
    Extended Code 39 is a convention for encoding additional characters
    not present in stanmdard Code 39 by using pairs of characters to
    represent the characters missing in Standard Code 39.

    See Standard39 for arguments.

    Sources of Information on Extended Code 39:

    http://www.semiconductor.agilent.com/barcode/sg/Misc/xcode_39.html
    http://www.barcodeman.com/c39_ext.html
    """
    def validate(self):
        vval = ""
        self.valid = 1
        for c in self.value:
            if c not in _extchrs:
                self.valid = 0
                continue
            vval = vval + c
        self.validated = vval
        return vval

    def encode(self):
        self.encoded = ""
        for c in self.validated:
            if c in _extended:
                self.encoded = self.encoded + _extended[c]
            elif c in _stdchrs:
                self.encoded = self.encoded + c
            else:
                raise ValueError
        self.encoded = _encode39(self.encoded, self.checksum,self.stop)
        return self.encoded
