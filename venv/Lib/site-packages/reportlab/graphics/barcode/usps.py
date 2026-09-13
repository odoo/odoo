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
from reportlab.graphics.barcode.common import Barcode
from string import digits as string_digits, whitespace as string_whitespace
from reportlab.lib.utils import asNative

_fim_patterns = {
    'A' : "||  |  ||",
    'B' : "| || || |",
    'C' : "|| | | ||",
    'D' : "||| | |||",
    # XXX There is an E.
    # The below has been seen, but dunno if it is E or not:
    # 'E' : '|||| ||||'
}

_postnet_patterns = {
    '1' : "...||",    '2' : "..|.|",    '3' : "..||.",    '4' : ".|..|",
    '5' : ".|.|.",    '6' : ".||..",    '7' : "|...|",    '8' : "|..|.",
    '9' : "|.|..",    '0' : "||...",    'S' : "|",
}

class FIM(Barcode):
    """
    FIM (Facing ID Marks) encode only one letter.
    There are currently four defined:

    A   Courtesy reply mail with pre-printed POSTNET
    B   Business reply mail without pre-printed POSTNET
    C   Business reply mail with pre-printed POSTNET
    D   OCR Readable mail without pre-printed POSTNET

    Options that may be passed to constructor:

        value (single character string from the set A - D. required.):
            The value to encode.

        quiet (bool, default 0):
            Whether to include quiet zones in the symbol.

    The following may also be passed, but doing so will generate nonstandard
    symbols which should not be used. This is mainly documented here to
    show the defaults:

        barHeight (float, default 5/8 inch):
            Height of the code. This might legitimately be overriden to make
            a taller symbol that will 'bleed' off the edge of the paper,
            leaving 5/8 inch remaining.

        lquiet (float, default 1/4 inch):
            Quiet zone size to left of code, if quiet is true.
            Default is the greater of .25 inch, or .15 times the symbol's
            length.

        rquiet (float, default 15/32 inch):
            Quiet zone size to right left of code, if quiet is true.

    Sources of information on FIM:

    USPS Publication 25, A Guide to Business Mail Preparation
    http://new.usps.com/cpim/ftp/pubs/pub25.pdf
    """
    barWidth = inch * (1.0/32.0)
    spaceWidth = inch * (1.0/16.0)
    barHeight = inch * (5.0/8.0)
    rquiet = inch * (0.25)
    lquiet = inch * (15.0/32.0)
    quiet = 0
    def __init__(self, value='', **args):
        value = str(value) if isinstance(value,int) else asNative(value)
        for k, v in args.items():
            setattr(self, k, v)

        Barcode.__init__(self, value)

    def validate(self):
        self.valid = 1
        self.validated = ''
        for c in self.value:
            if c in string_whitespace:
                continue
            elif c in "abcdABCD":
                self.validated = self.validated + c.upper()
            else:
                self.valid = 0

        if len(self.validated) != 1:
            raise ValueError("Input must be exactly one character")

        return self.validated

    def decompose(self):
        self.decomposed = ''
        for c in self.encoded:
            self.decomposed = self.decomposed + _fim_patterns[c]

        return self.decomposed

    def computeSize(self):
        self._width = (len(self.decomposed) - 1) * self.spaceWidth + self.barWidth
        if self.quiet:
            self._width += self.lquiet + self.rquiet
        self._height = self.barHeight

    def draw(self):
        self._calculate()
        left = self.quiet and self.lquiet or 0
        for c in self.decomposed:
            if c == '|':
                self.rect(left, 0.0, self.barWidth, self.barHeight)
            left += self.spaceWidth
        self.drawHumanReadable()

    def _humanText(self):
        return self.value

class POSTNET(Barcode):
    """
    POSTNET is used in the US to encode "zip codes" (postal codes) on
    mail. It can encode 5, 9, or 11 digit codes. I've read that it's
    pointless to do 5 digits, since USPS will just have to re-print
    them with 9 or 11 digits.

    Sources of information on POSTNET:

    USPS Publication 25, A Guide to Business Mail Preparation
    http://new.usps.com/cpim/ftp/pubs/pub25.pdf
    """
    quiet = 0
    shortHeight = inch * 0.050
    barHeight = inch * 0.125
    barWidth = inch * 0.018
    spaceWidth = inch * 0.0275
    def __init__(self, value='', **args):
        value = str(value) if isinstance(value,int) else asNative(value)
        for k, v in args.items():
            setattr(self, k, v)

        Barcode.__init__(self, value)

    def validate(self):
        self.validated = ''
        self.valid = 1
        count = 0
        for c in self.value:
            if c in (string_whitespace + '-'):
                pass
            elif c in string_digits:
                count = count + 1
                if count == 6:
                    self.validated = self.validated + '-'
                self.validated = self.validated + c
            else:
                self.valid = 0

        if len(self.validated) not in [5, 10, 12]:
            self.valid = 0

        return self.validated

    def encode(self):
        self.encoded = "S"
        check = 0
        for c in self.validated:
            if c in string_digits:
                self.encoded = self.encoded + c
                check = check + int(c)
            elif c == '-':
                pass
            else:
                raise ValueError("Invalid character in input")
        check = (10 - check) % 10
        self.encoded = self.encoded + repr(check) + 'S'
        return self.encoded

    def decompose(self):
        self.decomposed = ''
        for c in self.encoded:
            self.decomposed = self.decomposed + _postnet_patterns[c]
        return self.decomposed

    def computeSize(self):
        self._width = len(self.decomposed) * self.barWidth + (len(self.decomposed) - 1) * self.spaceWidth
        self._height = self.barHeight

    def draw(self):
        self._calculate()
        sdown = self.barHeight - self.shortHeight
        left = 0

        for c in self.decomposed:
            if c == '.':
                h = self.shortHeight
            else:
                h = self.barHeight
            self.rect(left, 0.0, self.barWidth, h)
            left = left + self.barWidth + self.spaceWidth
        self.drawHumanReadable()

    def _humanText(self):
        return self.encoded[1:-1]
