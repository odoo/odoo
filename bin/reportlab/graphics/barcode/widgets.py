#copyright ReportLab Europe Limited. 2000-2006
#see license.txt for license details
__version__=''' $Id: widgets.py 2851 2006-05-08 14:34:45Z rgbecker $ '''
__all__= (
        'BarcodeI2of5',
        'BarcodeCode128',
        'BarcodeStandard93',
        'BarcodeExtended93',
        'BarcodeStandard39',
        'BarcodeExtended39',
        'BarcodeMSI',
        'BarcodeCodabar',
        'BarcodeCode11',
        'BarcodeFIM',
        'BarcodePOSTNET',
        )

from reportlab.lib.validators import isInt, isNumber, isColor, isString, isColorOrNone, OneOf, isBoolean, EitherOr, isNumberOrNone
from reportlab.lib.attrmap import AttrMap, AttrMapValue
from reportlab.lib.colors import black
from reportlab.graphics.shapes import Line, Rect, Group, NotImplementedError, String
from reportlab.graphics.charts.areas import PlotArea

'''
#snippet

#first make your Drawing
from reportlab.graphics.shapes import Drawing
d= Drawing(100,50)

#create and set up the widget
from reportlab.graphics.barcode.widgets import BarcodeStandard93
bc = BarcodeStandard93()
bc.value = 'RGB-123456'

#add to the drawing and save
d.add(bc)
#   d.save(formats=['gif','pict'],fnRoot='bc_sample')
'''

class _BarcodeWidget(PlotArea):
    _attrMap = AttrMap(BASE=PlotArea,
        barStrokeColor = AttrMapValue(isColorOrNone, desc='Color of bar borders.'),
        barFillColor = AttrMapValue(isColorOrNone, desc='Color of bar interior areas.'),
        barStrokeWidth = AttrMapValue(isNumber, desc='Width of bar borders.'),
        value = AttrMapValue(EitherOr((isString,isNumber)), desc='Value.'),
        textColor = AttrMapValue(isColorOrNone, desc='Color of human readable text.'),
        valid = AttrMapValue(isBoolean),
        validated = AttrMapValue(isString,desc="validated form of input"),
        encoded = AttrMapValue(None,desc="encoded form of input"),
        decomposed = AttrMapValue(isString,desc="decomposed form of input"),
        canv = AttrMapValue(None,desc="temporarily used for internal methods"),
        gap = AttrMapValue(isNumberOrNone, desc='Width of inter character gaps.'),
        )

    barStrokeColor = barFillColor = textColor = black
    barStrokeWidth = 0
    _BCC = None
    def __init__(self,BCC=None,_value='',**kw):
        self._BCC = BCC
        class Combiner(self.__class__,BCC):
            __name__ = self.__class__.__name__
        self.__class__ = Combiner
        PlotArea.__init__(self)
        self.x = self.y = 0
        kw.setdefault('value',_value)
        BCC.__init__(self,**kw)

    def rect(self,x,y,w,h,**kw):
        self._Gadd(Rect(self.x+x,self.y+y,w,h,
                    strokeColor=self.barStrokeColor,strokeWidth=self.barStrokeWidth, fillColor=self.barFillColor))

    def draw(self):
        if not self._BCC: raise NotImplementedError("Abstract class %s cannot be drawn" % self.__class__.__name__)
        self.canv = self
        G = Group()
        self._Gadd = G.add
        self._Gadd(Rect(self.x,self.y,self.width,self.height,fillColor=None,strokeColor=None,strokeWidth=0.0001))
        self._BCC.draw(self)
        del self.canv, self._Gadd
        return G

    def annotate(self,x,y,text,fontName,fontSize,anchor='middle'):
        self._Gadd(String(self.x+x,self.y+y,text,fontName=fontName,fontSize=fontSize,
                            textAnchor=anchor,fillColor=self.textColor))

class BarcodeI2of5(_BarcodeWidget):
    """Interleaved 2 of 5 is used in distribution and warehouse industries.

    It encodes an even-numbered sequence of numeric digits. There is an optional
    module 10 check digit; if including this, the total length must be odd so that
    it becomes even after including the check digit.  Otherwise the length must be
    even. Since the check digit is optional, our library does not check it.
    """

    _tests = [
        '12',
        '1234',
        '123456',
        '12345678',
        '1234567890'
        ]
    codeName = "I2of5"
    _attrMap = AttrMap(BASE=_BarcodeWidget,
        barWidth = AttrMapValue(isNumber,'''(float, default .0075):
            X-Dimension, or width of the smallest element
            Minumum is .0075 inch (7.5 mils).'''),
        ratio = AttrMapValue(isNumber,'''(float, default 2.2):
            The ratio of wide elements to narrow elements.
            Must be between 2.0 and 3.0 (or 2.2 and 3.0 if the
            barWidth is greater than 20 mils (.02 inch))'''),
        gap = AttrMapValue(isNumberOrNone,'''(float or None, default None):
            width of intercharacter gap. None means "use barWidth".'''),
        barHeight = AttrMapValue(isNumber,'''(float, see default below):
            Height of the symbol.  Default is the height of the two
            bearer bars (if they exist) plus the greater of .25 inch
            or .15 times the symbol's length.'''),
        checksum = AttrMapValue(isBoolean,'''(bool, default 1):
            Whether to compute and include the check digit'''),
        bearers = AttrMapValue(isNumber,'''(float, in units of barWidth. default 3.0):
            Height of bearer bars (horizontal bars along the top and
            bottom of the barcode). Default is 3 x-dimensions.
            Set to zero for no bearer bars. (Bearer bars help detect
            misscans, so it is suggested to leave them on).'''),
        quiet = AttrMapValue(isBoolean,'''(bool, default 1):
            Whether to include quiet zones in the symbol.'''),

        lquiet = AttrMapValue(isNumber,'''(float, see default below):
            Quiet zone size to left of code, if quiet is true.
            Default is the greater of .25 inch, or .15 times the symbol's
            length.'''),

        rquiet = AttrMapValue(isNumber,'''(float, defaults as above):
            Quiet zone size to right left of code, if quiet is true.'''),
        fontName = AttrMapValue(isString, desc='human readable font'),
        fontSize = AttrMapValue(isNumber, desc='human readable font size'),
        humanReadable = AttrMapValue(isBoolean, desc='if human readable'),
        stop = AttrMapValue(isBoolean, desc='if we use start/stop symbols (default 1)'),
        )
    _bcTransMap = {}

    def __init__(self,**kw):
        from reportlab.graphics.barcode.common import I2of5
        _BarcodeWidget.__init__(self,I2of5,1234,**kw)

class BarcodeCode128(BarcodeI2of5):
    """Code 128 encodes any number of characters in the ASCII character set.
    """
    _tests = [
        'ReportLab Rocks!'
        ]
    codeName = "Code128"
    _attrMap = AttrMap(BASE=BarcodeI2of5,UNWANTED=('bearers','checksum','ratio','checksum','stop'))
    def __init__(self,**kw):
        from reportlab.graphics.barcode.code128 import Code128
        _BarcodeWidget.__init__(self,Code128,"AB-12345678",**kw)

class BarcodeStandard93(BarcodeCode128):
    """This is a compressed form of Code 39"""
    codeName = "Standard93"
    _attrMap = AttrMap(BASE=BarcodeCode128,
        stop = AttrMapValue(isBoolean, desc='if we use start/stop symbols (default 1)'),
        )
    def __init__(self,**kw):
        from reportlab.graphics.barcode.code93 import Standard93
        _BarcodeWidget.__init__(self,Standard93,"CODE 93",**kw)

class BarcodeExtended93(BarcodeStandard93):
    """This is a compressed form of Code 39, allowing the full ASCII charset"""
    codeName = "Extended93"
    def __init__(self,**kw):
        from reportlab.graphics.barcode.code93 import Extended93
        _BarcodeWidget.__init__(self,Extended93,"L@@K! Code 93 ;-)",**kw)

class BarcodeStandard39(BarcodeI2of5):
    """Code39 is widely used in non-retail, especially US defence and health.
    Allowed characters are 0-9, A-Z (caps only), space, and -.$/+%*.
    """

    codeName = "Standard39"
    def __init__(self,**kw):
        from reportlab.graphics.barcode.code39 import Standard39
        _BarcodeWidget.__init__(self,Standard39,"A012345B%R",**kw)

class BarcodeExtended39(BarcodeI2of5):
    """Extended 39 encodes the full ASCII character set by encoding
    characters as pairs of Code 39 characters; $, /, % and + are used as
    shift characters."""

    codeName = "Extended39"
    def __init__(self,**kw):
        from reportlab.graphics.barcode.code39 import Extended39
        _BarcodeWidget.__init__(self,Extended39,"A012345B}",**kw)

class BarcodeMSI(BarcodeI2of5):
    """MSI is used for inventory control in retail applications.

    There are several methods for calculating check digits so we
    do not implement one.
    """
    codeName = "MSI"
    def __init__(self,**kw):
        from reportlab.graphics.barcode.common import MSI
        _BarcodeWidget.__init__(self,MSI,1234,**kw)

class BarcodeCodabar(BarcodeI2of5):
    """Used in blood banks, photo labs and FedEx labels.
    Encodes 0-9, -$:/.+, and four start/stop characters A-D.
    """
    codeName = "Codabar"
    def __init__(self,**kw):
        from reportlab.graphics.barcode.common import Codabar
        _BarcodeWidget.__init__(self,Codabar,"A012345B",**kw)

class BarcodeCode11(BarcodeI2of5):
    """Used mostly for labelling telecommunications equipment.
    It encodes numeric digits.
    """
    codeName = "Code11"
    _attrMap = AttrMap(BASE=BarcodeI2of5,
        checksum = AttrMapValue(isInt,'''(integer, default 2):
            Whether to compute and include the check digit(s).
            (0 none, 1 1-digit, 2 2-digit, -1 auto, default -1):
            How many checksum digits to include. -1 ("auto") means
            1 if the number of digits is 10 or less, else 2.'''),
            )
    def __init__(self,**kw):
        from reportlab.graphics.barcode.common import Code11
        _BarcodeWidget.__init__(self,Code11,"01234545634563",**kw)

class BarcodeFIM(_BarcodeWidget):
    """
    FIM was developed as part of the POSTNET barcoding system. FIM (Face Identification Marking) is used by the cancelling machines to sort mail according to whether or not they have bar code and their postage requirements. There are four types of FIM called FIM A, FIM B, FIM C, and FIM D.

    The four FIM types have the following meanings:
        FIM A- Postage required pre-barcoded
        FIM B - Postage pre-paid, no bar code exists
        FIM C- Postage prepaid prebarcoded
        FIM D- Postage required, no bar code exists
    """
    codeName = "FIM"
    _attrMap = AttrMap(BASE=_BarcodeWidget,
        barWidth = AttrMapValue(isNumber,'''(float, default 1/32in): the bar width.'''),
        spaceWidth = AttrMapValue(isNumber,'''(float or None, default 1/16in):
            width of intercharacter gap. None means "use barWidth".'''),
        barHeight = AttrMapValue(isNumber,'''(float, default 5/8in): The bar height.'''),
        quiet = AttrMapValue(isBoolean,'''(bool, default 0):
            Whether to include quiet zones in the symbol.'''),
        lquiet = AttrMapValue(isNumber,'''(float, default: 15/32in):
            Quiet zone size to left of code, if quiet is true.'''),
        rquiet = AttrMapValue(isNumber,'''(float, default 1/4in):
            Quiet zone size to right left of code, if quiet is true.'''),
        fontName = AttrMapValue(isString, desc='human readable font'),
        fontSize = AttrMapValue(isNumber, desc='human readable font size'),
        humanReadable = AttrMapValue(isBoolean, desc='if human readable'),
        )
    def __init__(self,**kw):
        from reportlab.graphics.barcode.usps import FIM
        _BarcodeWidget.__init__(self,FIM,"A",**kw)

class BarcodePOSTNET(_BarcodeWidget):
    codeName = "POSTNET"
    _attrMap = AttrMap(BASE=_BarcodeWidget,
        barWidth = AttrMapValue(isNumber,'''(float, default 0.018*in): the bar width.'''),
        spaceWidth = AttrMapValue(isNumber,'''(float or None, default 0.0275in): width of intercharacter gap.'''),
        shortHeight = AttrMapValue(isNumber,'''(float, default 0.05in): The short bar height.'''),
        barHeight = AttrMapValue(isNumber,'''(float, default 0.125in): The full bar height.'''),
        fontName = AttrMapValue(isString, desc='human readable font'),
        fontSize = AttrMapValue(isNumber, desc='human readable font size'),
        humanReadable = AttrMapValue(isBoolean, desc='if human readable'),
        )
    def __init__(self,**kw):
        from reportlab.graphics.barcode.usps import POSTNET
        _BarcodeWidget.__init__(self,POSTNET,"78247-1043",**kw)

if __name__=='__main__':
    import os, sys, glob
    from reportlab.graphics.shapes import Drawing
    os.chdir(os.path.dirname(sys.argv[0]))
    if not os.path.isdir('out'):
        os.mkdir('out')
    map(os.remove,glob.glob(os.path.join('out','*')))
    html = ['<html><head></head><body>']
    a = html.append
    for C in (BarcodeI2of5,
            BarcodeCode128,
            BarcodeStandard93,
            BarcodeExtended93,
            BarcodeStandard39,
            BarcodeExtended39,
            BarcodeMSI,
            BarcodeCodabar,
            BarcodeCode11,
            BarcodeFIM,
            BarcodePOSTNET,
            ):
        name = C.__name__
        i = C()
        D = Drawing(100,50)
        D.add(i)
        D.save(formats=['gif','pict'],outDir='out',fnRoot=name)
        a('<h2>%s</h2><img src="%s.gif"><br>' % (name, name))
    a('</body></html>')
    open(os.path.join('out','index.html'),'w').write('\n'.join(html))
