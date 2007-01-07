__all__=(
        'Ean13BarcodeWidget','isEanString',
        )
from reportlab.graphics.shapes import Group, String, Rect
from reportlab.lib import colors
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.validators import isNumber, isColor, isString, Validator, isBoolean
from reportlab.lib.attrmap import *
from reportlab.graphics.charts.areas import PlotArea
from reportlab.lib.units import mm

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

class isEan13String(Validator):
    def test(self,x):
        return type(x) is str and len(x)<=12 and len([c for c in x if c in "0123456789"])==12
isEan13String = isEan13String()

class Ean13BarcodeWidget(PlotArea):
    codeName = "EAN13"
    _attrMap = AttrMap(BASE=PlotArea,
        value = AttrMapValue(isEan13String, desc='the number'),
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
    textColor = barFillColor = barStrokeColor = colors.black
    barStrokeWidth = 0
    x = 0
    y = 0
    def __init__(self,value='123456789012',**kw):
        self.value=max(self._digits-len(value),0)*'0'+value[:self._digits]
        for k, v in kw.iteritems():
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
                    lrect = Rect(x,yh,barWidth,barHeight-dh,fillColor=barFillColor,strokeWidth=barStrokeWidth,strokeColor=barFillColor)
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

    @classmethod
    def _checkdigit(cls,num):
        z = ord('0')
        iSum = cls._0csw*sum([(ord(x)-z) for x in num[::2]]) \
                 + cls._1csw*sum([(ord(x)-z) for x in num[1::2]])
        return chr(z+((10-(iSum%10))%10))

class isEan8String(Validator):
    def test(self,x):
        return type(x) is str and len(x)<=7 and len([c for c in x if c in "0123456789"])==7
isEan8String = isEan8String()

class Ean8BarcodeWidget(Ean13BarcodeWidget):
    codeName = "EAN8"
    _attrMap = AttrMap(BASE=Ean13BarcodeWidget,
        value = AttrMapValue(isEan8String, desc='the number'),
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
