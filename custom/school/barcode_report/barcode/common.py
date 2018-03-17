# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from reportlab.platypus.flowables import Flowable
from reportlab.lib.units import inch
import string


class Barcode(Flowable):
    """Abstract Base for BarCodes. Includes implementations of
    some methods suitable for the more primitive BarCode types"""

    def __init__(self, value=''):
        self.value = value

        if not hasattr(self, 'gap'):
            self.gap = None
        self.validate()
        self.encode()
        self.decompose()
        self.computeSize()

    def validate(self):
        self.valid = 1
        self.validated = self.value

    def encode(self):
        self.encoded = self.validated

    def decompose(self):
        self.decomposed = self.encoded

    def computeSize(self, *args):
        xdim = self.xdim
        wx = xdim * self.ratio

        if self.gap is None:
            self.gap = xdim

        w = 0.0

        for c in self.decomposed:
            if c in 'sb':
                w = w + xdim
            elif c in 'SB':
                w = w + wx
            else:  # 'i'
                w = w + self.gap

        if self.height is None:
            self.height = w * 0.15
            self.height = max(0.25 * inch, self.height)
            if self.bearers:
                self.height = self.height + self.bearers * 2.0 * xdim

        if self.quiet:
            w = w + self.lquiet + self.rquiet
            self.xo = self.lquiet
        else:
            self.xo = 0.0

        self.width = w

    def draw(self):
        xdim = self.xdim
        wx = xdim * self.ratio

        left = self.xo
        b = self.bearers * xdim
        bb = b * 0.5
        tb = self.height - (b * 1.5)

        for c in self.decomposed:
            if c == 'i':
                left = left + self.gap
            elif c == 's':
                left = left + xdim
            elif c == 'S':
                left = left + wx
            elif c == 'b':
                self.rect(left, bb, xdim, tb)
                left = left + xdim
            elif c == 'B':
                self.rect(left, bb, wx, tb)
                left = left + wx

        if self.bearers:
            self.rect(self.lquiet, 0.0,
                      self.width - (self.lquiet + self.rquiet), b)
            self.rect(self.lquiet, self.height - b,
                      self.width - (self.lquiet + self.rquiet), b)

    def rect(self, x, y, w, h):
        self.canv.rect(x, y, w, h, stroke=0, fill=1)


class MultiWidthBarcode(Barcode):
    """Base for variable-bar-width codes like Code93 and Code128"""

    def computeSize(self, *args):
        xdim = self.xdim
        oa, oA = ord('a') - 1, ord('A') - 1

        w = 0.0

        for c in self.decomposed:
            oc = ord(c)
            if c in string.lowercase:
                w = w + xdim * (oc - oa)
            elif c in string.uppercase:
                w = w + xdim * (oc - oA)

        if self.height is None:
            self.height = w * 0.15
            self.height = max(0.25 * inch, self.height)

        if self.quiet:
            w = w + self.lquiet + self.rquiet
            self.xo = self.lquiet
        else:
            self.xo = 0.0

        self.width = w

    def draw(self):
        oa, oA = ord('a') - 1, ord('A') - 1
        xdim = self.xdim
        left = self.xo

        for c in self.decomposed:
            oc = ord(c)
            if c in string.lowercase:
                left = left + (oc - oa) * xdim
            elif c in string.uppercase:
                w = (oc - oA) * xdim
                self.rect(left, 0.0, w, self.height)
                left = left + w


class I2of5(Barcode):
    """
    Interleaved 2 of 5 is a numeric-only BarCode.  It encodes an even
    number of digits; if an odd number is given, a 0 is prepended.

    Options that may be passed to constructor:

        value (int, or numeric string. required.):
            The value to encode.

        xdim (float, default .0075):
            X-Dimension, or width of the smallest element
            Minimum is .0075 inch (7.5 miles).

        ratio (float, default 2.2):
            The ratio of wide elements to narrow elements.
            Must be between 2.0 and 3.0 (or 2.2 and 3.0 if the
            xdim is greater than 20 miles (.02 inch))

        gap (float or None, default None):
            width of interCharacter gap. None means "use xdim".

        height (float, see default below):
            Height of the symbol.  Default is the height of the two
            bearer bars (if they exist) plus the greater of .25 inch
            or .15 times the symbol's length.

        checksum (bool, default 1):
            Whether to compute and include the check digit

        bearers (float, in units of xdim. default 3.0):
            Height of bearer bars (horizontal bars along the top and
            bottom of the barCode). Default is 3 x-dimensions.
            Set to zero for no bearer bars. (Bearer bars help detect
            missCans, so it is suggested to leave them on).

        quiet (bool, default 1):
            Whether to include quiet zones in the symbol.

        lquiet (float, see default below):
            Quiet zone size to left of code, if quiet is true.
            Default is the greater of .25 inch, or .15 times the symbol's
            length.

        rquiet (float, defaults as above):
            Quiet zone size to right left of code, if quiet is true.

    Sources of Information on Interleaved 2 of 5:

    http://www.semiconductor.agilent.com/barcode/sg/Misc/i_25.html
    http://www.adams1.com/pub/russadam/i25code.html

    Official Spec, "ANSI/AIM BC2-1995, USS" is available for US$45 from
    http://www.aimglobal.org/aimstore/
    """

    patterns = {'start': 'bsbs',
                'stop': 'Bsb',
                'B0': 'bbBBb', 'S0': 'ssSSs',
                'B1': 'BbbbB', 'S1': 'SsssS',
                'B2': 'bBbbB', 'S2': 'sSssS',
                'B3': 'BBbbb', 'S3': 'SSsss',
                'B4': 'bbBbB', 'S4': 'ssSsS',
                'B5': 'BbBbb', 'S5': 'SsSss',
                'B6': 'bBBbb', 'S6': 'sSSss',
                'B7': 'bbbBB', 'S7': 'sssSS',
                'B8': 'BbbBb', 'S8': 'SssSs',
                'B9': 'bBbBb', 'S9': 'sSsSs'}

    def __init__(self, value='', **args):
        self.height = None
        self.xdim = inch * 0.0075
        self.ratio = 2.2
        self.checksum = 1
        self.bearers = 3.0
        self.quiet = 1
        self.lquiet = self.rquiet = None

        if isinstance(value, 1):
            value = str(value)

        for (k, v) in args.items():
            setattr(self, k, v)

        if self.quiet:
            if self.lquiet is None:
                self.lquiet = min(inch * 0.25, self.xdim * 10.0)
                self.rquiet = min(inch * 0.25, self.xdim * 10.0)
        else:
            self.lquiet = self.rquiet = 0.0

        Barcode.__init__(self, value)

    def validate(self):
        vval = ""
        self.valid = 1

        for c in string.strip(self.value):

            if c not in string.digits:
                self.valid = 0
                continue
            vval = vval + c
        self.validated = vval
        return vval

    def encode(self):
        s = self.validated
        # make sure result will be a multiple of 2 digits long,
        # checksum included

        if (((len(self.validated) % 2 == 0) and self.checksum) or
                ((len(self.validated) % 2 == 1) and not self.checksum)):
            s = '0' + s

        if self.checksum:
            c = 0
            cm = 3

            for d in s:
                c = c + cm * int(d)
                if cm == 3:
                    cm = 1
                else:
                    cm = 3

            d = 10 - (int(d) % 10)
            s += repr(d)
        self.encoded = s

    def decompose(self):
        dval = self.patterns['start']

        for i in range(0, len(self.encoded), 2):
            b = self.patterns['B' + self.encoded[i]]
            s = self.patterns['S' + self.encoded[i + 1]]

            for i in range(0, len(b)):
                dval = dval + b[i] + s[i]

        self.decomposed = dval + self.patterns['stop']
        return self.decomposed


class MSI(Barcode):
    """
    MSI is a numeric-only barCode.

    Options that may be passed to constructor:

        value (int, or numeric string. required.):
            The value to encode.

        xdim (float, default .0075):
            X-Dimension, or width of the smallest element

        ratio (float, default 2.2):
            The ratio of wide elements to narrow elements.

        gap (float or None, default None):
            width of interCharacter gap. None means "use xdim".

        height (float, see default below):
            Height of the symbol.  Default is the height of the two
            bearer bars (if they exist) plus the greater of .25 inch
            or .15 times the symbol's length.

        checksum (bool, default 1):
            Whether to compute and include the check digit

        bearers (float, in units of xdim. default 0):
            Height of bearer bars (horizontal bars along the top and
            bottom of the barCode). Default is 0 (no bearers).

        lquiet (float, see default below):
            Quiet zone size to left of code, if quiet is true.
            Default is the greater of .25 inch, or 10 xdims.

        rquiet (float, defaults as above):
            Quiet zone size to right left of code, if quiet is true.

    Sources of Information on MSI Bar Code:

    http://www.semiconductor.agilent.com/barcode/sg/Misc/msi_code.html
    http://www.adams1.com/pub/russadam/plessy.html
    """

    patterns = {'start': 'Bs', 'stop': 'bSb',
                '0': 'bSbSbSbS', '1': 'bSbSbSBs',
                '2': 'bSbSBsbS', '3': 'bSbSBsBs',
                '4': 'bSBsbSbS', '5': 'bSBsbSBs',
                '6': 'bSBsBsbS', '7': 'bSBsBsBs',
                '8': 'BsbSbSbS', '9': 'BsbSbSBs'}

    def __init__(self, value="", **args):
        self.height = None
        self.xdim = inch * 0.0075
        self.ratio = 2.2
        self.checksum = 1
        self.bearers = 0.0
        self.quiet = 1
        self.lquiet = self.rquiet = None

        if isinstance(value, 1):
            value = str(value)

        for (k, v) in args.items():
            setattr(self, k, v)

        if self.quiet:
            if self.lquiet is None:
                self.lquiet = max(inch * 0.25, self.xdim * 10.0)
                self.rquiet = max(inch * 0.25, self.xdim * 10.0)
        else:
            self.lquiet = self.rquiet = 0.0
            Barcode.__init__(self, value)

    def validate(self):
        vval = ""
        self.valid = 1
        for c in string.strip(self.value):
            if c not in string.digits:
                self.valid = 0
                continue
            vval = vval + c
        self.validated = vval
        return vval

    def encode(self):
        s = self.validated

        if self.checksum:
            c = ''
            for i in range(1, len(s), 2):
                c = c + s[i]
            d = str(int(c) * 2)
            t = 0
            for c in d:
                t = t + int(c)
            for i in range(0, len(s), 2):
                t = t + int(s[i])
            c = 10 - (t % 10)

            s = s + str(c)

        self.encoded = s

    def decompose(self):
        dval = self.patterns['start']

        for c in self.encoded:
            dval = dval + self.patterns[c]

        self.decomposed = dval + self.patterns['stop']
        return self.decomposed


class Codabar(Barcode):
    """
    CodaBar is a numeric plus some punctuation ("-$:/.+") barCode
    with four start/stop characters (A, B, C, and D).

    Options that may be passed to constructor:

        value (string. required.):
            The value to encode.

        xdim (float, default .0065):
            X-Dimension, or width of the smallest element
            minimum is 6.5 miles (.0065 inch)

        ratio (float, default 2.0):
            The ratio of wide elements to narrow elements.

        gap (float or None, default None):
            width of interCharacter gap. None means "use xdim".

        height (float, see default below):
            Height of the symbol.  Default is the height of the two
            bearer bars (if they exist) plus the greater of .25 inch
            or .15 times the symbol's length.

        checksum (bool, default 0):
            Whether to compute and include the check digit

        bearers (float, in units of xdim. default 0):
            Height of bearer bars (horizontal bars along the top and
            bottom of the BarCode). Default is 0 (no bearers).

        quiet (bool, default 1):
            Whether to include quiet zones in the symbol.

        lquiet (float, see default below):
            Quiet zone size to left of code, if quiet is true.
            Default is the greater of .25 inch, or 10 xdim

        rquiet (float, defaults as above):
            Quiet zone size to right left of code, if quiet is true.

    Sources of Information on CodaBar

    http://www.semiconductor.agilent.com/barcode/sg/Misc/codabar.html
    http://www.barcodeman.com/codabar.html

    Official Spec, "ANSI/AIM BC3-1995, USS" is available for US$45 from
    http://www.aimglobal.org/aimstore/
    """

    patterns = {'0': 'bsbsbSB', '1': 'bsbsBSb', '2': 'bsbSbsB',
                '3': 'BSbsbsb', '4': 'bsBsbSb', '5': 'BsbsbSb',
                '6': 'bSbsbsB', '7': 'bSbsBsb', '8': 'bSBsbsb',
                '9': 'BsbSbsb', '-': 'bsbSBsb', '$': 'bsBSbsb',
                ':': 'BsbsBsB', '/': 'BsBsbsB', '.': 'BsBsBsb',
                '+': 'bsBsBsB', 'A': 'bsBSbSb', 'B': 'bSbSbsB',
                'C': 'bsbSbSB', 'D': 'bsbSBSb'}

    values = {'0': 0, '1': 1, '2': 2, '3': 3, '4': 4,
              '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
              '-': 10, '$': 11, ':': 12, '/': 13, '.': 14,
              '+': 15, 'A': 16, 'B': 17, 'C': 18, 'D': 19}

    chars = string.digits + "-$:/.+"

    def __init__(self, value='', **args):
        self.height = None
        self.xdim = inch * 0.0065
        self.ratio = 2.0  # XXX ?
        self.checksum = 0
        self.bearers = 0.0
        self.quiet = 1
        self.lquiet = self.rquiet = None

        if isinstance(value, 1):
            value = str(value)

        for (k, v) in args.items():
            setattr(self, k, v)

        if self.quiet:
            if self.lquiet is None:
                self.lquiet = min(inch * 0.25, self.xdim * 10.0)
                self.rquiet = min(inch * 0.25, self.xdim * 10.0)
        else:
            self.lquiet = self.rquiet = 0.0

        Barcode.__init__(self, value)

    def validate(self):
        vval = ""
        self.valid = 1
        s = string.strip(self.value)
        for i in range(0, len(s)):
            c = s[i]
            if c not in self.chars:
                if ((i != 0) and (i != len(s) - 1)) or (c not in 'ABCD'):
                    self.Valid = 0
                    continue
            vval = vval + c

        if vval[0] not in 'ABCD':
            vval = 'A' + vval
        if vval[-1] not in 'ABCD':
            vval = vval + vval[0]

        self.validated = vval
        return vval

    def encode(self):
        s = self.validated

        if self.checksum:
            v = 0
            if s:
                v = v + self.values[v]
            v = 16 - (v % 16)
            s = s + self.chars[v]

        self.encoded = s

    def decompose(self):
        dval = ""
        for c in self.encoded:
            dval = dval + self.patterns[c] + 'i'
        self.decomposed = dval[:-1]
        return self.decomposed


class Code11(Barcode):
    """
    Code 11 is an almost-numeric barCode. It encodes the digits 0-9 plus
    dash ("-"). 11 characters total, hence the name.

        value (int or string. required.):
            The value to encode.

        xdim (float, default .0075):
            X-Dimension, or width of the smallest element

        ratio (float, default 2.2):
            The ratio of wide elements to narrow elements.

        gap (float or None, default None):
            width of interCharacter gap. None means "use xdim".

        height (float, see default below):
            Height of the symbol.  Default is the height of the two
            bearer bars (if they exist) plus the greater of .25 inch
            or .15 times the symbol's length.

        checksum (0 none, 1 1-digit, 2 2-digit, -1 auto, default -1):
            How many checksum digits to include. -1 ("auto") means
            1 if the number of digits is 10 or less, else 2.

        bearers (float, in units of xdim. default 0):
            Height of bearer bars (horizontal bars along the top and
            bottom of the BarCode). Default is 0 (no bearers).

        quiet (bool, default 1):
            Whether to include quiet zones in the symbol.

        lquiet (float, see default below):
            Quiet zone size to left of code, if quiet is true.
            Default is the greater of .25 inch, or 10 xdim

        rquiet (float, defaults as above):
            Quiet zone size to right left of code, if quiet is true.

    Sources of Information on Code 11:

    http://www.cwi.nl/people/dik/english/codes/barcodes.html
    """

    chars = string.digits + '-'

    patterns = {'0': 'bsbsB', '1': 'BsbsB', '2': 'bSbsB',
                '3': 'BSbsb', '4': 'bsBsB', '5': 'BsBsb',
                '6': 'bSBsb', '7': 'bsbSB', '8': 'BsbSb',
                '9': 'Bsbsb', '-': 'bsBsb', 'S': 'bsBSb'}

    values = {'0': 0, '1': 1, '2': 2, '3': 3, '4': 4,
              '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '-': 10}

    def __init__(self, value='', **args):
        self.height = None
        self.xdim = inch * 0.0075
        self.ratio = 2.2  # XXX ?
        self.checksum = -1  # Auto
        self.bearers = 0.0
        self.quiet = 1
        self.lquiet = self.rquiet = None

        if isinstance(value, 1):
            value = str(value)

        for (k, v) in args.items():
            setattr(self, k, v)

        if self.quiet:
            if self.lquiet is None:
                self.lquiet = min(inch * 0.25, self.xdim * 10.0)
                self.rquiet = min(inch * 0.25, self.xdim * 10.0)
        else:
            self.lquiet = self.rquiet = 0.0

        Barcode.__init__(self, value)

    def validate(self):
        vval = ""
        self.valid = 1
        s = string.strip(self.value)
        for i in range(0, len(s)):
            c = s[i]
            if c not in self.chars:
                self.Valid = 0
                continue
            vval = vval + c
        self.validated = vval
        return vval

    def encode(self):
        s = self.validated

        if self.checksum == -1:
            if len(s) <= 10:
                self.checksum = 1
            else:
                self.checksum = 2

        if self.checksum > 0:
            # compute first checksum
            i, v, c = 0, 1, 0
            while i < len(s):
                c = c + v * string.index(self.chars, s[-(i + 1)])
                i = i + 1
                v = v + 1
                if v > 10:
                    v = 1
            s = s + self.chars[c % 11]

        if self.checksum > 1:
            # compute second checksum
            i, v, c = 0, 1, 0
            while i < len(s):
                c = c + v * string.index(self.chars, s[-(i + 1)])
                i = i + 1
                v = v + 1
                if v > 9:
                    v = 1
            s = s + self.chars[c % 10]

        self.encoded = 'S' + s + 'S'

    def decompose(self):
        dval = ""
        for c in self.encoded:
            dval = dval + self.patterns[c] + 'i'
        self.decomposed = dval[:-1]
        return self.decomposed
