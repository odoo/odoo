#
# ReportLab QRCode widget
#
# Ported from the Javascript library QRCode for Javascript by Sam Curren
#
# URL: http://www.d-project.com/
# http://d-project.googlecode.com/svn/trunk/misc/qrcode/js/qrcode.js
# qrcode.js is copyright (c) 2009 Kazuhiko Arase
#
# Original ReportLab module by German M. Bravo
#
# modified and improved by Anders Hammarquist <iko@openend.se>
# and used with permission under the ReportLab License
#
# The word "QR Code" is registered trademark of
# DENSO WAVE INCORPORATED
#   http://www.denso-wave.com/qrcode/faqpatent-e.html

__all__ = ('QrCodeWidget')

import itertools

from reportlab.platypus.flowables import Flowable
from reportlab.graphics.shapes import Group, Rect
from reportlab.lib import colors
from reportlab.lib.validators import isNumber, isNumberOrNone, isColor, Validator
from reportlab.lib.attrmap import AttrMap, AttrMapValue
from reportlab.graphics.widgetbase import Widget
from reportlab.lib.units import mm
from reportlab.lib.utils import asUnicodeEx, isUnicode
from reportlab.graphics.barcode import qrencoder

class isLevel(Validator):
    def test(self, x):
        return x in ['L', 'M', 'Q', 'H']
isLevel = isLevel()

class isUnicodeOrQRList(Validator):
    def _test(self, x):
        if isUnicode(x):
            return True
        if all(isinstance(v, qrencoder.QR) for v in x):
            return True
        return False

    def test(self, x):
        return self._test(x) or self.normalizeTest(x)

    def normalize(self, x):
        if self._test(x):
            return x
        try:
            return asUnicodeEx(x)
        except UnicodeError:
            raise ValueError("Can't convert to unicode: %r" % x)
isUnicodeOrQRList = isUnicodeOrQRList()

class SRect(Rect):
    def __init__(self, x, y, width, height, fillColor=colors.black):
        Rect.__init__(self, x, y, width, height, fillColor=fillColor,
                      strokeColor=None, strokeWidth=0)

class QrCodeWidget(Widget):
    codeName = "QR"
    _attrMap = AttrMap(
        BASE = Widget,
        value = AttrMapValue(isUnicodeOrQRList, desc='QRCode data'),
        x = AttrMapValue(isNumber, desc='x-coord'),
        y = AttrMapValue(isNumber, desc='y-coord'),
        barFillColor = AttrMapValue(isColor, desc='bar color'),
        barWidth = AttrMapValue(isNumber, desc='Width of bars.'), # maybe should be named just width?
        barHeight = AttrMapValue(isNumber, desc='Height of bars.'), # maybe should be named just height?
        barBorder = AttrMapValue(isNumber, desc='Width of QR border.'), # maybe should be named qrBorder?
        barLevel = AttrMapValue(isLevel, desc='QR Code level.'), # maybe should be named qrLevel
        qrVersion = AttrMapValue(isNumberOrNone, desc='QR Code version. None for auto'),
        # Below are ignored, they make no sense
        barStrokeWidth = AttrMapValue(isNumber, desc='Width of bar borders.'),
        barStrokeColor = AttrMapValue(isColor, desc='Color of bar borders.'),
        )
    x = 0
    y = 0
    barFillColor = colors.black
    barStrokeColor = None
    barStrokeWidth = 0
    barHeight = 32*mm
    barWidth = 32*mm
    barBorder = 4
    barLevel = 'L'
    qrVersion = None
    value = None

    def __init__(self, value='Hello World', **kw):
        self.value = isUnicodeOrQRList.normalize(value)
        for k, v in kw.items():
            setattr(self, k, v)

        ec_level = getattr(qrencoder.QRErrorCorrectLevel, self.barLevel)

        self.__dict__['qr'] = qrencoder.QRCode(self.qrVersion, ec_level)

        if isUnicode(self.value):
            self.addData(self.value)
        elif self.value:
            for v in self.value:
                self.addData(v)

    def addData(self, value):
        self.qr.addData(value)

    def draw(self):
        self.qr.make()

        g = Group()

        color = self.barFillColor
        border = self.barBorder
        width = self.barWidth
        height = self.barHeight
        x = self.x
        y = self.y

        g.add(SRect(x, y, width, height, fillColor=None))

        moduleCount = self.qr.getModuleCount()
        minwh = float(min(width, height))
        boxsize = minwh / (moduleCount + border * 2.0)
        offsetX = x + (width - minwh) / 2.0
        offsetY = y + (minwh - height) / 2.0

        for r, row in enumerate(self.qr.modules):
            row = map(bool, row)
            c = 0
            for t, tt in itertools.groupby(row):
                isDark = t
                count = len(list(tt))
                if isDark:
                    x = (c + border) * boxsize
                    y = (r + border + 1) * boxsize
                    s = SRect(offsetX + x, offsetY + height - y, count * boxsize, boxsize,
                            fillColor=color)
                    g.add(s)
                c += count

        return g


# Flowable version

class QrCode(Flowable):
    height = 32*mm
    width = 32*mm
    qrBorder = 4
    qrLevel = 'L'
    qrVersion = None
    value = None

    def __init__(self, value=None, **kw):
        self.value = isUnicodeOrQRList.normalize(value)

        for k, v in kw.items():
            setattr(self, k, v)

        ec_level = getattr(qrencoder.QRErrorCorrectLevel, self.qrLevel)

        self.qr = qrencoder.QRCode(self.qrVersion, ec_level)

        if isUnicode(self.value):
            self.addData(self.value)
        elif self.value:
            for v in self.value:
                self.addData(v)

    def addData(self, value):
        self.qr.addData(value)

    def draw(self):
        self.qr.make()

        moduleCount = self.qr.getModuleCount()
        border = self.qrBorder
        xsize = self.width / (moduleCount + border * 2.0)
        ysize = self.height / (moduleCount + border * 2.0)

        for r, row in enumerate(self.qr.modules):
            row = map(bool, row)
            c = 0
            for t, tt in itertools.groupby(row):
                isDark = t
                count = len(list(tt))
                if isDark:
                    x = (c + border) * xsize
                    y = self.height - (r + border + 1) * ysize
                    self.rect(x, y, count * xsize, ysize * 1.05)
                c += count

    def rect(self, x, y, w, h):
        self.canv.rect(x, y, w, h, stroke=0, fill=1)
