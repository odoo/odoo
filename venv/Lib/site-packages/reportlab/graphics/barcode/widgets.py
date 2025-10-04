#copyright ReportLab Europe Limited. 2000-2016
#see license.txt for license details
__version__='3.3.0'
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
        'BarcodeUSPS_4State',
        )

from reportlab.lib.validators import isInt, isNumber, isString, isColorOrNone, isBoolean, EitherOr, isNumberOrNone
from reportlab.lib.attrmap import AttrMap, AttrMapValue
from reportlab.lib.colors import black
from reportlab.lib.utils import rl_exec
from reportlab.graphics.shapes import Rect, Group, String
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

    textColor = barFillColor = black
    barStrokeColor = None
    barStrokeWidth = 0
    _BCC = None
    def __init__(self,_value='',**kw):
        PlotArea.__init__(self)
        if 'width' in self.__dict__: del self.__dict__['width']
        if 'height' in self.__dict__: del self.__dict__['height']
        self.x = self.y = 0
        kw.setdefault('value',_value)
        self._BCC.__init__(self,**kw)

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

def _BCW(doc,codeName,attrMap,mod,value,**kwds):
    """factory for Barcode Widgets"""
    _pre_init = kwds.pop('_pre_init','')
    _methods = kwds.pop('_methods','')
    name = 'Barcode'+codeName
    ns = vars().copy()
    code = 'from %s import %s' % (mod,codeName)
    rl_exec(code,ns)
    ns['_BarcodeWidget'] = _BarcodeWidget
    ns['doc'] = ("\n\t'''%s'''" % doc) if doc else ''
    code = '''class %(name)s(_BarcodeWidget,%(codeName)s):%(doc)s
\t_BCC = %(codeName)s
\tcodeName = %(codeName)r
\tdef __init__(self,**kw):%(_pre_init)s
\t\t_BarcodeWidget.__init__(self,%(value)r,**kw)%(_methods)s''' % ns
    rl_exec(code,ns)
    Klass = ns[name]
    if attrMap: Klass._attrMap = attrMap
    for k, v in kwds.items():
        setattr(Klass,k,v)
    return Klass

BarcodeI2of5 = _BCW(
    """Interleaved 2 of 5 is used in distribution and warehouse industries.

    It encodes an even-numbered sequence of numeric digits. There is an optional
    module 10 check digit; if including this, the total length must be odd so that
    it becomes even after including the check digit.  Otherwise the length must be
    even. Since the check digit is optional, our library does not check it.
    """,
    "I2of5",
    AttrMap(BASE=_BarcodeWidget,
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
        ),
    'reportlab.graphics.barcode.common',
    1234,
    _tests = [
        '12',
        '1234',
        '123456',
        '12345678',
        '1234567890'
        ],
    )

BarcodeCode128 = _BCW("""Code 128 encodes any number of characters in the ASCII character set.""",
                "Code128",
                AttrMap(BASE=BarcodeI2of5,UNWANTED=('bearers','checksum','ratio','checksum','stop')),
                'reportlab.graphics.barcode.code128',
                "AB-12345678",
                _tests = ['ReportLab Rocks!', 'PFWZF'],
                )

BarcodeCode128Auto = _BCW(
                'Modified Code128 to use auto encoding',
                'Code128Auto',
                AttrMap(BASE=BarcodeCode128),
                'reportlab.graphics.barcode.code128',
                'XY149740345GB'
                )

BarcodeStandard93=_BCW("""This is a compressed form of Code 39""",
                        "Standard93",
                        AttrMap(BASE=BarcodeCode128,
                                stop = AttrMapValue(isBoolean, desc='if we use start/stop symbols (default 1)'),
                                ),
                        'reportlab.graphics.barcode.code93',
                        "CODE 93",
                        )

BarcodeExtended93=_BCW("""This is a compressed form of Code 39, allowing the full ASCII charset""",
                        "Extended93",
                        AttrMap(BASE=BarcodeCode128,
                                stop = AttrMapValue(isBoolean, desc='if we use start/stop symbols (default 1)'),
                                ),
                        'reportlab.graphics.barcode.code93',
                        "L@@K! Code 93 ;-)",
                        )

BarcodeStandard39=_BCW("""Code39 is widely used in non-retail, especially US defence and health.
                        Allowed characters are 0-9, A-Z (caps only), space, and -.$/+%*.""",
                        "Standard39",
                        AttrMap(BASE=BarcodeI2of5),
                        'reportlab.graphics.barcode.code39',
                        "A012345B%R",
                        )

BarcodeExtended39=_BCW("""Extended 39 encodes the full ASCII character set by encoding
                        characters as pairs of Code 39 characters; $, /, % and + are used as
                        shift characters.""",
                        "Extended39",
                        AttrMap(BASE=BarcodeI2of5),
                        'reportlab.graphics.barcode.code39',
                        "A012345B}",
                        )

BarcodeMSI=_BCW("""MSI is used for inventory control in retail applications.

                There are several methods for calculating check digits so we
                do not implement one.
                """,
                "MSI",
                AttrMap(BASE=BarcodeI2of5),
                'reportlab.graphics.barcode.common',
                1234,
                )

BarcodeCodabar=_BCW("""Used in blood banks, photo labs and FedEx labels.
                    Encodes 0-9, -$:/.+, and four start/stop characters A-D.""",
                    "Codabar",
                    AttrMap(BASE=BarcodeI2of5),
                    'reportlab.graphics.barcode.common',
                    "A012345B",
                    )

BarcodeCode11=_BCW("""Used mostly for labelling telecommunications equipment.
                    It encodes numeric digits.""",
                    'Code11',
                    AttrMap(BASE=BarcodeI2of5,
                        checksum = AttrMapValue(isInt,'''(integer, default 2):
                            Whether to compute and include the check digit(s).
                            (0 none, 1 1-digit, 2 2-digit, -1 auto, default -1):
                            How many checksum digits to include. -1 ("auto") means
                            1 if the number of digits is 10 or less, else 2.'''),
                            ),
                    'reportlab.graphics.barcode.common',
                    "01234545634563",
                    )

BarcodeFIM=_BCW("""
                FIM was developed as part of the POSTNET barcoding system.
                FIM (Face Identification Marking) is used by the cancelling machines
                to sort mail according to whether or not they have bar code
                and their postage requirements. There are four types of FIM
                called FIM A, FIM B, FIM C, and FIM D.

                The four FIM types have the following meanings:
                    FIM A- Postage required pre-barcoded
                    FIM B - Postage pre-paid, no bar code exists
                    FIM C- Postage prepaid prebarcoded
                    FIM D- Postage required, no bar code exists""",
                "FIM",
                AttrMap(BASE=_BarcodeWidget,
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
                    ),
                'reportlab.graphics.barcode.usps',
                "A",
                )

BarcodePOSTNET=_BCW('',
                    "POSTNET",
                    AttrMap(BASE=_BarcodeWidget,
                            barWidth = AttrMapValue(isNumber,'''(float, default 0.018*in): the bar width.'''),
                            spaceWidth = AttrMapValue(isNumber,'''(float or None, default 0.0275in): width of intercharacter gap.'''),
                            shortHeight = AttrMapValue(isNumber,'''(float, default 0.05in): The short bar height.'''),
                            barHeight = AttrMapValue(isNumber,'''(float, default 0.125in): The full bar height.'''),
                            fontName = AttrMapValue(isString, desc='human readable font'),
                            fontSize = AttrMapValue(isNumber, desc='human readable font size'),
                            humanReadable = AttrMapValue(isBoolean, desc='if human readable'),
                            ),
                    'reportlab.graphics.barcode.usps',
                    "78247-1043",
                    )

BarcodeUSPS_4State=_BCW('',
                        "USPS_4State",
                        AttrMap(BASE=_BarcodeWidget,
                            widthSize = AttrMapValue(isNumber,'''(float, default 1): the bar width size adjustment between 0 and 1.'''),
                            heightSize = AttrMapValue(isNumber,'''(float, default 1): the bar height size adjustment between 0 and 1.'''),
                            fontName = AttrMapValue(isString, desc='human readable font'),
                            fontSize = AttrMapValue(isNumber, desc='human readable font size'),
                            tracking = AttrMapValue(isString, desc='tracking data'),
                            routing = AttrMapValue(isString, desc='routing data'),
                            humanReadable = AttrMapValue(isBoolean, desc='if human readable'),
                            barWidth = AttrMapValue(isNumber, desc='barWidth'),
                            barHeight = AttrMapValue(isNumber, desc='barHeight'),
                            pitch = AttrMapValue(isNumber, desc='pitch'),
                            ),
                        'reportlab.graphics.barcode.usps4s',
                        '01234567094987654321',
                        _pre_init="\n\t\tkw.setdefault('routing','01234567891')\n",
                        _methods = "\n\tdef annotate(self,x,y,text,fontName,fontSize,anchor='middle'):\n\t\t_BarcodeWidget.annotate(self,x,y,text,fontName,fontSize,anchor='start')\n"
                        )
BarcodeECC200DataMatrix = _BCW(
    'ECC200DataMatrix',
    'ECC200DataMatrix',
    AttrMap(BASE=_BarcodeWidget,
        x=AttrMapValue(isNumber, desc='X position of the lower-left corner of the barcode.'),
        y=AttrMapValue(isNumber, desc='Y position of the lower-left corner of the barcode.'),
        barWidth=AttrMapValue(isNumber, desc='Size of data modules.'),
        barFillColor=AttrMapValue(isColorOrNone, desc='Color of data modules.'),
        value=AttrMapValue(EitherOr((isString,isNumber)), desc='Value.'),
        height=AttrMapValue(None, desc='ignored'),
        width=AttrMapValue(None, desc='ignored'),
        strokeColor=AttrMapValue(None, desc='ignored'),
        strokeWidth=AttrMapValue(None, desc='ignored'),
        fillColor=AttrMapValue(None, desc='ignored'),
        background=AttrMapValue(None, desc='ignored'),
        debug=AttrMapValue(None, desc='ignored'),
        gap=AttrMapValue(None, desc='ignored'),
        row_modules=AttrMapValue(None, desc='???'),
        col_modules=AttrMapValue(None, desc='???'),
        row_regions=AttrMapValue(None, desc='???'),
        col_regions=AttrMapValue(None, desc='???'),
        cw_data=AttrMapValue(None, desc='???'),
        cw_ecc=AttrMapValue(None, desc='???'),
        row_usable_modules = AttrMapValue(None, desc='???'),
        col_usable_modules = AttrMapValue(None, desc='???'),
        valid = AttrMapValue(None, desc='???'),
        validated = AttrMapValue(None, desc='???'),
        decomposed = AttrMapValue(None, desc='???'),
    ),
    'reportlab.graphics.barcode.ecc200datamatrix',
    'JGB 0204H20B012722900021AC35B2100001003241014241014TPS01  WJ067073605GB185 MOUNT PLEASANT MAIL CENTER         EC1A1BB9ZGBREC1A1BB  EC1A1BB  STEST FILE       FOR SPEC                                       '
    )

if __name__=='__main__':
    raise ValueError('widgets.py has no script function')
