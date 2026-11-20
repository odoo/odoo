__all__=(
        'Ean13BarcodeWidget','isEanString',
        'Ean8BarcodeWidget', 'UPCA', 'Ean5BarcodeWidget', 'ISBNBarcodeWidget',
        )
from reportlab.graphics.shapes import Group, String, Rect
from reportlab.lib import colors
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.validators import isNumber, isColor, isString, Validator, isBoolean, NoneOr
from reportlab.lib.attrmap import *
from reportlab.graphics.charts.areas import PlotArea
from reportlab.lib.units import mm
from reportlab.lib.utils import asNative

#work out a list of manufacturer codes....
_eanNumberSystems = [
         ('00-13', 'USA & Canada'),
         ('20-29', 'In-Store Functions'),
         ('30-37', 'France'),
         ('40-44', 'Germany'),
         ('45', 'Japan (also 49)'),
         ('46', 'Russian Federation'),
         ('471', 'Taiwan'),
         ('474', 'Estonia'),
         ('475', 'Latvia'),
         ('477', 'Lithuania'),
         ('479', 'Sri Lanka'),
         ('480', 'Philippines'),
         ('482', 'Ukraine'),
         ('484', 'Moldova'),
         ('485', 'Armenia'),
         ('486', 'Georgia'),
         ('487', 'Kazakhstan'),
         ('489', 'Hong Kong'),
         ('49', 'Japan (JAN-13)'),
         ('50', 'United Kingdom'),
         ('520', 'Greece'),
         ('528', 'Lebanon'),
         ('529', 'Cyprus'),
         ('531', 'Macedonia'),
         ('535', 'Malta'),
         ('539', 'Ireland'),
         ('54', 'Belgium & Luxembourg'),
         ('560', 'Portugal'),
         ('569', 'Iceland'),
         ('57', 'Denmark'),
         ('590', 'Poland'),
         ('594', 'Romania'),
         ('599', 'Hungary'),
         ('600-601', 'South Africa'),
         ('609', 'Mauritius'),
         ('611', 'Morocco'),
         ('613', 'Algeria'),
         ('619', 'Tunisia'),
         ('622', 'Egypt'),
         ('625', 'Jordan'),
         ('626', 'Iran'),
         ('64', 'Finland'),
         ('690-692', 'China'),
         ('70', 'Norway'),
         ('729', 'Israel'),
         ('73', 'Sweden'),
         ('740', 'Guatemala'),
         ('741', 'El Salvador'),
         ('742', 'Honduras'),
         ('743', 'Nicaragua'),
         ('744', 'Costa Rica'),
         ('746', 'Dominican Republic'),
         ('750', 'Mexico'),
         ('759', 'Venezuela'),
         ('76', 'Switzerland'),
         ('770', 'Colombia'),
         ('773', 'Uruguay'),
         ('775', 'Peru'),
         ('777', 'Bolivia'),
         ('779', 'Argentina'),
         ('780', 'Chile'),
         ('784', 'Paraguay'),
         ('785', 'Peru'),
         ('786', 'Ecuador'),
         ('789', 'Brazil'),
         ('80-83', 'Italy'),
         ('84', 'Spain'),
         ('850', 'Cuba'),
         ('858', 'Slovakia'),
         ('859', 'Czech Republic'),
         ('860', 'Yugloslavia'),
         ('869', 'Turkey'),
         ('87', 'Netherlands'),
         ('880', 'South Korea'),
         ('885', 'Thailand'),
         ('888', 'Singapore'),
         ('890', 'India'),
         ('893', 'Vietnam'),
         ('899', 'Indonesia'),
         ('90-91', 'Austria'),
         ('93', 'Australia'),
         ('94', 'New Zealand'),
         ('955', 'Malaysia'),
         ('977', 'International Standard Serial Number for Periodicals (ISSN)'),
         ('978', 'International Standard Book Numbering (ISBN)'),
         ('979', 'International Standard Music Number (ISMN)'),
         ('980', 'Refund receipts'),
         ('981-982', 'Common Currency Coupons'),
         ('99', 'Coupons')
         ]

manufacturerCodes = {}
for (k, v) in _eanNumberSystems:
    words = k.split('-')
    if len(words)==2:
        fromCode = int(words[0])
        toCode = int(words[1])
        for code in range(fromCode, toCode+1):
            manufacturerCodes[code] = v
    else:
        manufacturerCodes[int(k)] = v

def nDigits(n):
    class _ndigits(Validator):
        def test(self,x):
            return type(x) is str and len(x)<=n and len([c for c in x if c in "0123456789"])==n
    return _ndigits()

class Ean13BarcodeWidget(PlotArea):
    codeName = "EAN13"
    _attrMap = AttrMap(BASE=PlotArea,
        value = AttrMapValue(nDigits(12), desc='the number'),
        fontName = AttrMapValue(isString, desc='fontName'),
        fontSize = AttrMapValue(isNumber, desc='font size'),
        x = AttrMapValue(isNumber, desc='x-coord'),
        y = AttrMapValue(isNumber, desc='y-coord'),
        barFillColor = AttrMapValue(isColor, desc='bar color'),
        barHeight = AttrMapValue(isNumber, desc='Height of bars.'),
        barWidth = AttrMapValue(isNumber, desc='Width of bars.'),
        barStrokeWidth = AttrMapValue(isNumber, desc='Width of bar borders.'),
        barStrokeColor = AttrMapValue(isColor, desc='Color of bar borders.'),
        textColor = AttrMapValue(isColor, desc='human readable text color'),
        humanReadable = AttrMapValue(isBoolean, desc='if human readable'),
        quiet = AttrMapValue(isBoolean, desc='if quiet zone to be used'),
        lquiet = AttrMapValue(isBoolean, desc='left quiet zone length'),
        rquiet = AttrMapValue(isBoolean, desc='right quiet zone length'),
        )
    _digits=12
    _start_right = 7    #for ean-13 left = [0:7] right=[7:13]
    _nbars = 113
    barHeight = 25.93*mm    #millimeters
    barWidth = (37.29/_nbars)*mm
    humanReadable = 1
    _0csw = 1
    _1csw = 3

    #Left Hand Digits.
    _left = (   ("0001101", "0011001", "0010011", "0111101",
                "0100011", "0110001", "0101111", "0111011",
                "0110111", "0001011",
                ),  #odd left hand digits
                ("0100111", "0110011", "0011011", "0100001",
                "0011101", "0111001", "0000101", "0010001",
                "0001001", "0010111"),  #even left hand digits
            )

    _right = ("1110010", "1100110", "1101100", "1000010",
            "1011100", "1001110", "1010000", "1000100",
            "1001000", "1110100")

    quiet = 1
    rquiet = lquiet = None
    _tail = "101"
    _sep = "01010"

    _lhconvert={
            "0": (0,0,0,0,0,0),
            "1": (0,0,1,0,1,1),
            "2": (0,0,1,1,0,1),
            "3": (0,0,1,1,1,0),
            "4": (0,1,0,0,1,1),
            "5": (0,1,1,0,0,1),
            "6": (0,1,1,1,0,0),
            "7": (0,1,0,1,0,1),
            "8": (0,1,0,1,1,0),
            "9": (0,1,1,0,1,0)
            }
    fontSize = 8        #millimeters
    fontName = 'Helvetica'
    textColor = barFillColor = colors.black
    barStrokeColor = None
    barStrokeWidth = 0
    x = 0
    y = 0
    def __init__(self,value='123456789012',**kw):
        value = str(value) if isinstance(value,int) else asNative(value)
        self.value=max(self._digits-len(value),0)*'0'+value[:self._digits]
        for k, v in kw.items():
            setattr(self, k, v)

    width = property(lambda self: self.barWidth*(self._nbars-18+self._calc_quiet(self.lquiet)+self._calc_quiet(self.rquiet)))

    def wrap(self,aW,aH):
        return self.width,self.barHeight

    def _encode_left(self,s,a):
        cp = self._lhconvert[s[0]]      #convert the left hand numbers
        _left = self._left
        z = ord('0')
        for i,c in enumerate(s[1:self._start_right]):
            a(_left[cp[i]][ord(c)-z])

    def _short_bar(self,i):
        i += 9 - self._lquiet
        return self.humanReadable and ((12<i<55) or (57<i<101))

    def _calc_quiet(self,v):
        if self.quiet:
            if v is None:
                v = 9
            else:
                x = float(max(v,0))/self.barWidth
                v = int(x)
                if v-x>0: v += 1
        else:
            v = 0
        return v

    def draw(self):
        g = Group()
        gAdd = g.add
        barWidth = self.barWidth
        width = self.width
        barHeight = self.barHeight
        x = self.x
        y = self.y
        gAdd(Rect(x,y,width,barHeight,fillColor=None,strokeColor=None,strokeWidth=0))
        s = self.value+self._checkdigit(self.value)
        self._lquiet = lquiet = self._calc_quiet(self.lquiet)
        rquiet = self._calc_quiet(self.rquiet)
        b = [lquiet*'0',self._tail] #the signal string
        a = b.append
        self._encode_left(s,a)
        a(self._sep)

        z = ord('0')
        _right = self._right
        for c in s[self._start_right:]:
            a(_right[ord(c)-z])
        a(self._tail)
        a(rquiet*'0')

        fontSize = self.fontSize
        barFillColor = self.barFillColor
        barStrokeWidth = self.barStrokeWidth
        barStrokeColor = self.barStrokeColor

        fth = fontSize*1.2
        b = ''.join(b)

        lrect = None
        for i,c in enumerate(b):
            if c=="1":
                dh = self._short_bar(i) and fth or 0
                yh = y+dh
                if lrect and lrect.y==yh:
                    lrect.width += barWidth
                else:
                    lrect = Rect(x,yh,barWidth,barHeight-dh,fillColor=barFillColor,strokeWidth=barStrokeWidth,strokeColor=barStrokeColor)
                    gAdd(lrect)
            else:
                lrect = None
            x += barWidth

        if self.humanReadable: self._add_human_readable(s,gAdd)
        return g

    def _add_human_readable(self,s,gAdd):
        barWidth = self.barWidth
        fontSize = self.fontSize
        textColor = self.textColor
        fontName = self.fontName
        fth = fontSize*1.2
        # draw the num below the line.
        c = s[0]
        w = stringWidth(c,fontName,fontSize)
        x = self.x+barWidth*(self._lquiet-8)
        y = self.y + 0.2*fth

        gAdd(String(x,y,c,fontName=fontName,fontSize=fontSize,fillColor=textColor))
        x = self.x + (33-9+self._lquiet)*barWidth

        c = s[1:7]
        gAdd(String(x,y,c,fontName=fontName,fontSize=fontSize,fillColor=textColor,textAnchor='middle'))

        x += 47*barWidth
        c = s[7:]
        gAdd(String(x,y,c,fontName=fontName,fontSize=fontSize,fillColor=textColor,textAnchor='middle'))

    def _checkdigit(cls,num):
        z = ord('0')
        iSum = cls._0csw*sum([(ord(x)-z) for x in num[::2]]) \
                 + cls._1csw*sum([(ord(x)-z) for x in num[1::2]])
        return chr(z+((10-(iSum%10))%10))
    _checkdigit=classmethod(_checkdigit)

class Ean8BarcodeWidget(Ean13BarcodeWidget):
    codeName = "EAN8"
    _attrMap = AttrMap(BASE=Ean13BarcodeWidget,
        value = AttrMapValue(nDigits(7), desc='the number'),
        )
    _start_right = 4    #for ean-13 left = [0:7] right=[7:13]
    _nbars = 85
    _digits=7
    _0csw = 3
    _1csw = 1

    def _encode_left(self,s,a):
        cp = self._lhconvert[s[0]]      #convert the left hand numbers
        _left = self._left[0]
        z = ord('0')
        for i,c in enumerate(s[0:self._start_right]):
            a(_left[ord(c)-z])

    def _short_bar(self,i):
        i += 9 - self._lquiet
        return self.humanReadable and ((12<i<41) or (43<i<73))

    def _add_human_readable(self,s,gAdd):
        barWidth = self.barWidth
        fontSize = self.fontSize
        textColor = self.textColor
        fontName = self.fontName
        fth = fontSize*1.2
        # draw the num below the line.
        y = self.y + 0.2*fth

        x = (26.5-9+self._lquiet)*barWidth

        c = s[0:4]
        gAdd(String(x,y,c,fontName=fontName,fontSize=fontSize,fillColor=textColor,textAnchor='middle'))

        x = (59.5-9+self._lquiet)*barWidth
        c = s[4:]
        gAdd(String(x,y,c,fontName=fontName,fontSize=fontSize,fillColor=textColor,textAnchor='middle'))

class UPCA(Ean13BarcodeWidget):
    codeName = "UPCA"
    _attrMap = AttrMap(BASE=Ean13BarcodeWidget,
        value = AttrMapValue(nDigits(11), desc='the number'),
        )
    _start_right = 6
    _digits = 11
    _0csw = 3
    _1csw = 1
    _nbars = 1+7*11+2*3+5

    #these methods contributed by Kyle Macfarlane
    #https://bitbucket.org/kylemacfarlane/
    def _encode_left(self,s,a):
        cp = self._lhconvert[s[0]]      #convert the left hand numbers
        _left = self._left[0]
        z = ord('0')
        for i,c in enumerate(s[0:self._start_right]):
            a(_left[ord(c)-z])

    def _short_bar(self,i):
        i += 9 - self._lquiet
        return self.humanReadable and ((18<i<55) or (57<i<93))

    def _add_human_readable(self,s,gAdd):
        barWidth = self.barWidth
        fontSize = self.fontSize
        textColor = self.textColor
        fontName = self.fontName
        fth = fontSize*1.2
        # draw the num below the line.
        c = s[0]
        w = stringWidth(c,fontName,fontSize)
        x = self.x+barWidth*(self._lquiet-8)
        y = self.y + 0.2*fth

        gAdd(String(x,y,c,fontName=fontName,fontSize=fontSize,fillColor=textColor))
        x = self.x + (38-9+self._lquiet)*barWidth

        c = s[1:6]
        gAdd(String(x,y,c,fontName=fontName,fontSize=fontSize,fillColor=textColor,textAnchor='middle'))

        x += 36*barWidth
        c = s[6:11]
        gAdd(String(x,y,c,fontName=fontName,fontSize=fontSize,fillColor=textColor,textAnchor='middle'))

        x += 32*barWidth
        c = s[11]
        gAdd(String(x,y,c,fontName=fontName,fontSize=fontSize,fillColor=textColor))

class Ean5BarcodeWidget(Ean13BarcodeWidget):
    """
    EAN-5 barcodes can print the human readable price, set:
        price=True
    """
    codeName = "EAN5"
    _attrMap = AttrMap(BASE=Ean13BarcodeWidget,
                       price=AttrMapValue(isBoolean,
                                          desc='whether to display the price or not'),
                       value=AttrMapValue(nDigits(5), desc='the number'),
                       )
    _nbars = 48
    _digits = 5
    _sep = '01'
    _tail = '01011'
    _0csw = 3
    _1csw = 9

    _lhconvert = {
        "0": (1, 1, 0, 0, 0),
        "1": (1, 0, 1, 0, 0),
        "2": (1, 0, 0, 1, 0),
        "3": (1, 0, 0, 0, 1),
        "4": (0, 1, 1, 0, 0),
        "5": (0, 0, 1, 1, 0),
        "6": (0, 0, 0, 1, 1),
        "7": (0, 1, 0, 1, 0),
        "8": (0, 1, 0, 0, 1),
        "9": (0, 0, 1, 0, 1)
    }

    def _checkdigit(cls, num):
        z = ord('0')
        iSum = cls._0csw * sum([(ord(x) - z) for x in num[::2]]) \
               + cls._1csw * sum([(ord(x) - z) for x in num[1::2]])
        return chr(z + iSum % 10)

    def _encode_left(self, s, a):
        check = self._checkdigit(s)
        cp = self._lhconvert[check]
        _left = self._left
        _sep = self._sep
        z = ord('0')
        full_code = []
        for i, c in enumerate(s):
            full_code.append(_left[cp[i]][ord(c) - z])
        a(_sep.join(full_code))

    def _short_bar(self, i):
        i += 9 - self._lquiet
        return self.humanReadable and ((12 < i < 41) or (43 < i < 73))

    def _add_human_readable(self, s, gAdd):
        barWidth = self.barWidth
        fontSize = self.fontSize
        textColor = self.textColor
        fontName = self.fontName
        fth = fontSize * 1.2
        # draw the num below the line.
        y = self.y + 0.2 * fth

        x = self.x + (self._nbars + self._lquiet * 2) * barWidth / 2

        gAdd(String(x, y, s, fontName=fontName, fontSize=fontSize,
                    fillColor=textColor, textAnchor='middle'))

        price = getattr(self,'price',None)
        if price:
            price = None
            if s[0] in '3456':
                price = '$'
            elif s[0] in '01':
                price = asNative(b'\xc2\xa3')

            if price is None:
                return

            price += s[1:3] + '.' + s[3:5]
            y += self.barHeight
            gAdd(String(x, y, price, fontName=fontName, fontSize=fontSize,
                        fillColor=textColor, textAnchor='middle'))

    def draw(self):
        g = Group()
        gAdd = g.add
        barWidth = self.barWidth
        width = self.width
        barHeight = self.barHeight
        x = self.x
        y = self.y
        gAdd(Rect(x, y, width, barHeight, fillColor=None, strokeColor=None,
                  strokeWidth=0))
        s = self.value
        self._lquiet = lquiet = self._calc_quiet(self.lquiet)
        rquiet = self._calc_quiet(self.rquiet)
        b = [lquiet * '0' + self._tail]  # the signal string
        a = b.append
        self._encode_left(s, a)

        a(rquiet * '0')

        fontSize = self.fontSize
        barFillColor = self.barFillColor
        barStrokeWidth = self.barStrokeWidth
        barStrokeColor = self.barStrokeColor

        fth = fontSize * 1.2
        b = ''.join(b)

        lrect = None
        for i, c in enumerate(b):
            if c == "1":
                dh = fth
                yh = y + dh
                if lrect and lrect.y == yh:
                    lrect.width += barWidth
                else:
                    lrect = Rect(x, yh, barWidth, barHeight - dh,
                                 fillColor=barFillColor,
                                 strokeWidth=barStrokeWidth,
                                 strokeColor=barStrokeColor)
                    gAdd(lrect)
            else:
                lrect = None
            x += barWidth

        if self.humanReadable:
            self._add_human_readable(s, gAdd)
        return g

class ISBNBarcodeWidget(Ean13BarcodeWidget):
    """
    ISBN Barcodes optionally print the EAN-5 supplemental price
    barcode (with the price in dollars or pounds). Set price to a string
    that follows the EAN-5 for ISBN spec:

        leading digit 0, 1 = GBP
                      3    = AUD
                      4    = NZD
                      5    = USD
                      6    = CAD
        next 4 digits = price between 00.00 and 99.98, i.e.:

        price='52499' # $24.99 USD
    """
    codeName = 'ISBN'
    _attrMap = AttrMap(BASE=Ean13BarcodeWidget,
                       price=AttrMapValue(
                           NoneOr(nDigits(5)),
                           desc='None or the price to display'),
                       )
    def draw(self):
        g = Ean13BarcodeWidget.draw(self)

        price = getattr(self,'price',None)
        if not price:
            return g

        bounds = g.getBounds()
        x = bounds[2]
        pricecode = Ean5BarcodeWidget(x=x, value=price, price=True,
                                      humanReadable=True,
                                      barHeight=self.barHeight, quiet=self.quiet)
        g.add(pricecode)
        return g

    def _add_human_readable(self, s, gAdd):
        Ean13BarcodeWidget._add_human_readable(self,s, gAdd)
        barWidth = self.barWidth
        barHeight = self.barHeight
        fontSize = self.fontSize
        textColor = self.textColor
        fontName = self.fontName
        fth = fontSize * 1.2
        y = self.y + 0.2 * fth + barHeight
        x = self._lquiet * barWidth

        isbn = 'ISBN '
        segments = [s[0:3], s[3:4], s[4:9], s[9:12], s[12]]
        isbn += '-'.join(segments)

        gAdd(String(x, y, isbn, fontName=fontName, fontSize=fontSize,
                    fillColor=textColor))
