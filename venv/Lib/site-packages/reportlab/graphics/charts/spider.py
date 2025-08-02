    #Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/graphics/charts/spider.py
# spider chart, also known as radar chart

__version__='3.3.0'
__doc__="""Spider Chart

Normal use shows variation of 5-10 parameters against some 'norm' or target.
When there is more than one series, place the series with the largest
numbers first, as it will be overdrawn by each successive one.
"""

from math import sin, cos, pi

from reportlab.lib import colors
from reportlab.lib.validators import isNumber, isListOfNumbersOrNone,\
                                    isColorOrNone, isListOfStringsOrNone, OneOf,\
                                    isBoolean, isNumberOrNone,\
                                    isStringOrNone, isStringOrNone, EitherOr,\
                                    isCallable
from reportlab.lib.attrmap import *
from reportlab.graphics.shapes import Group, Drawing, Line, Rect, Polygon, PolyLine, \
    STATE_DEFAULTS
from reportlab.graphics.widgetbase import TypedPropertyCollection, PropHolder
from reportlab.graphics.charts.areas import PlotArea
from reportlab.graphics.charts.legends import _objStr
from reportlab.graphics.charts.piecharts import WedgeLabel
from reportlab.graphics.widgets.markers import makeMarker, uSymbol2Symbol, isSymbol

class StrandProperty(PropHolder):

    _attrMap = AttrMap(
        strokeWidth = AttrMapValue(isNumber,desc='width'),
        fillColor = AttrMapValue(isColorOrNone,desc='filling color'),
        strokeColor = AttrMapValue(isColorOrNone,desc='stroke color'),
        strokeDashArray = AttrMapValue(isListOfNumbersOrNone,desc='dashing pattern, e.g. (3,2)'),
        symbol = AttrMapValue(EitherOr((isStringOrNone,isSymbol)), desc='Widget placed at data points.',advancedUsage=1),
        symbolSize= AttrMapValue(isNumber, desc='Symbol size.',advancedUsage=1),
        name = AttrMapValue(isStringOrNone, desc='Name of the strand.'),
        )

    def __init__(self):
        self.strokeWidth = 1
        self.fillColor = None
        self.strokeColor = STATE_DEFAULTS["strokeColor"]
        self.strokeDashArray = STATE_DEFAULTS["strokeDashArray"]
        self.symbol = None
        self.symbolSize = 5
        self.name = None

class SpokeProperty(PropHolder):
    _attrMap = AttrMap(
        strokeWidth = AttrMapValue(isNumber,desc='width'),
        fillColor = AttrMapValue(isColorOrNone,desc='filling color'),
        strokeColor = AttrMapValue(isColorOrNone,desc='stroke color'),
        strokeDashArray = AttrMapValue(isListOfNumbersOrNone,desc='dashing pattern, e.g. (2,1)'),
        labelRadius = AttrMapValue(isNumber,desc='label radius',advancedUsage=1),
        visible = AttrMapValue(isBoolean,desc="True if the spoke line is to be drawn"),
        )

    def __init__(self,**kw):
        self.strokeWidth = 0.5
        self.fillColor = None
        self.strokeColor = STATE_DEFAULTS["strokeColor"]
        self.strokeDashArray = STATE_DEFAULTS["strokeDashArray"]
        self.visible = 1
        self.labelRadius = 1.05

class SpokeLabel(WedgeLabel):
    def __init__(self,**kw):
        WedgeLabel.__init__(self,**kw)
        if '_text' not in list(kw.keys()): self._text = ''

class StrandLabel(SpokeLabel):
    _attrMap = AttrMap(BASE=SpokeLabel,
            format = AttrMapValue(EitherOr((isStringOrNone,isCallable)),desc="Format for the label"),
            dR = AttrMapValue(isNumberOrNone,desc="radial shift for label"),
            )
    def __init__(self,**kw):
        self.format = ''
        self.dR = 0
        SpokeLabel.__init__(self,**kw)

def _setupLabel(labelClass, text, radius, cx, cy, angle, car, sar, sty):
    L = labelClass()
    L._text = text
    L.x = cx + radius*car
    L.y = cy + radius*sar
    L._pmv = angle*180/pi
    L.boxAnchor = sty.boxAnchor
    L.dx = sty.dx
    L.dy = sty.dy
    L.angle = sty.angle
    L.boxAnchor = sty.boxAnchor
    L.boxStrokeColor = sty.boxStrokeColor
    L.boxStrokeWidth = sty.boxStrokeWidth
    L.boxFillColor = sty.boxFillColor
    L.strokeColor = sty.strokeColor
    L.strokeWidth = sty.strokeWidth
    L.leading = sty.leading
    L.width = sty.width
    L.maxWidth = sty.maxWidth
    L.height = sty.height
    L.textAnchor = sty.textAnchor
    L.visible = sty.visible
    L.topPadding = sty.topPadding
    L.leftPadding = sty.leftPadding
    L.rightPadding = sty.rightPadding
    L.bottomPadding = sty.bottomPadding
    L.fontName = sty.fontName
    L.fontSize = sty.fontSize
    L.fillColor = sty.fillColor
    return L

class SpiderChart(PlotArea):
    _attrMap = AttrMap(BASE=PlotArea,
        data = AttrMapValue(None, desc='Data to be plotted, list of (lists of) numbers.'),
        labels = AttrMapValue(isListOfStringsOrNone, desc="optional list of labels to use for each data point"),
        startAngle = AttrMapValue(isNumber, desc="angle of first slice; like the compass, 0 is due North"),
        direction = AttrMapValue( OneOf('clockwise', 'anticlockwise'), desc="'clockwise' or 'anticlockwise'"),
        strands = AttrMapValue(None, desc="collection of strand descriptor objects"),
        spokes = AttrMapValue(None, desc="collection of spoke descriptor objects"),
        strandLabels = AttrMapValue(None, desc="collection of strand label descriptor objects"),
        spokeLabels = AttrMapValue(None, desc="collection of spoke label descriptor objects"),
        )

    def makeSwatchSample(self, rowNo, x, y, width, height):
        baseStyle = self.strands
        styleIdx = rowNo % len(baseStyle)
        style = baseStyle[styleIdx]
        strokeColor = getattr(style, 'strokeColor', getattr(baseStyle,'strokeColor',None))
        fillColor = getattr(style, 'fillColor', getattr(baseStyle,'fillColor',None))
        strokeDashArray = getattr(style, 'strokeDashArray', getattr(baseStyle,'strokeDashArray',None))
        strokeWidth = getattr(style, 'strokeWidth', getattr(baseStyle, 'strokeWidth',0))
        symbol = getattr(style, 'symbol', getattr(baseStyle, 'symbol',None))
        ym = y+height/2.0
        if fillColor is None and strokeColor is not None and strokeWidth>0:
            bg = Line(x,ym,x+width,ym,strokeWidth=strokeWidth,strokeColor=strokeColor,
                    strokeDashArray=strokeDashArray)
        elif fillColor is not None:
            bg = Rect(x,y,width,height,strokeWidth=strokeWidth,strokeColor=strokeColor,
                    strokeDashArray=strokeDashArray,fillColor=fillColor)
        else:
            bg = None
        if symbol:
            symbol = uSymbol2Symbol(symbol,x+width/2.,ym,color)
            if bg:
                g = Group()
                g.add(bg)
                g.add(symbol)
                return g
        return symbol or bg

    def getSeriesName(self,i,default=None):
        '''return series name i or default'''
        return _objStr(getattr(self.strands[i],'name',default))

    def __init__(self):
        PlotArea.__init__(self)

        self.data = [[10,12,14,16,14,12], [6,8,10,12,9,11]]
        self.labels = None  # or list of strings
        self.labels = ['a','b','c','d','e','f']
        self.startAngle = 90
        self.direction = "clockwise"

        self.strands = TypedPropertyCollection(StrandProperty)
        self.spokes = TypedPropertyCollection(SpokeProperty)
        self.spokeLabels = TypedPropertyCollection(SpokeLabel)
        self.spokeLabels._text = None
        self.strandLabels = TypedPropertyCollection(StrandLabel)
        self.x = 10
        self.y = 10
        self.width = 180
        self.height = 180

    def demo(self):
        d = Drawing(200, 200)
        d.add(SpiderChart())
        return d

    def normalizeData(self, outer = 0.0):
        """Turns data into normalized ones where each datum is < 1.0,
        and 1.0 = maximum radius.  Adds 10% at outside edge by default"""
        data = self.data
        assert min(list(map(min,data))) >=0, "Cannot do spider plots of negative numbers!"
        norm = max(list(map(max,data)))
        norm *= (1.0+outer)
        if norm<1e-9: norm = 1.0
        self._norm = norm
        return [[e/norm for e in row] for row in data]

    def _innerDrawLabel(self, sty, radius, cx, cy, angle, car, sar, labelClass=StrandLabel):
        "Draw a label for a given item in the list."
        fmt = sty.format
        value = radius*self._norm
        if not fmt:
            text = None
        elif isinstance(fmt,str):
            if fmt == 'values':
                text = sty._text
            else:
                text = fmt % value
        elif hasattr(fmt,'__call__'):
            text = fmt(value)
        else:
            raise ValueError("Unknown formatter type %s, expected string or function" % fmt)

        if text:
            dR = sty.dR
            if dR:
                radius += dR/self._radius
            L = _setupLabel(labelClass, text, radius, cx, cy, angle, car, sar, sty)
            if dR<0: L._anti = 1
        else:
            L = None
        return L

    def draw(self):
        # normalize slice data
        g = self.makeBackground() or Group()

        xradius = self.width/2.0
        yradius = self.height/2.0
        self._radius = radius = min(xradius, yradius)
        cx = self.x + xradius
        cy = self.y + yradius

        data = self.normalizeData()

        self._seriesCount = len(data)
        n = len(data[0])

        #labels
        if self.labels is None:
            labels = [''] * n
        else:
            labels = self.labels
            #there's no point in raising errors for less than enough errors if
            #we silently create all for the extreme case of no labels.
            i = n-len(labels)
            if i>0:
                labels = labels + ['']*i

        S = []
        STRANDS = []
        STRANDAREAS = []
        syms = []
        labs = []
        csa = []
        angle = self.startAngle*pi/180
        direction = self.direction == "clockwise" and -1 or 1
        angleBetween = direction*(2 * pi)/float(n)
        spokes = self.spokes
        spokeLabels = self.spokeLabels
        for i in range(n):
            car = cos(angle)*radius
            sar = sin(angle)*radius
            csa.append((car,sar,angle))
            si = self.spokes[i]
            if si.visible:
                spoke = Line(cx, cy, cx + car, cy + sar, strokeWidth = si.strokeWidth, strokeColor=si.strokeColor, strokeDashArray=si.strokeDashArray)
            S.append(spoke)
            sli = spokeLabels[i]
            text = sli._text
            if not text: text = labels[i]
            if text:
                S.append(_setupLabel(WedgeLabel, text, si.labelRadius, cx, cy, angle, car, sar, sli))
            angle += angleBetween

        # now plot the polygons
        rowIdx = 0
        strands = self.strands
        strandLabels = self.strandLabels
        for row in data:
            # series plot
            rsty = strands[rowIdx]
            points = []
            car, sar = csa[-1][:2]
            r = row[-1]
            points.append(cx+car*r)
            points.append(cy+sar*r)
            for i in range(n):
                car, sar, angle = csa[i]
                r = row[i]
                points.append(cx+car*r)
                points.append(cy+sar*r)
                L = self._innerDrawLabel(strandLabels[(rowIdx,i)], r, cx, cy, angle, car, sar, labelClass=StrandLabel)
                if L: labs.append(L)
                sty = strands[(rowIdx,i)]
                uSymbol = sty.symbol

                # put in a marker, if it needs one
                if uSymbol:
                    s_x =  cx+car*r
                    s_y = cy+sar*r
                    s_fillColor = sty.fillColor
                    s_strokeColor = sty.strokeColor
                    s_strokeWidth = sty.strokeWidth
                    s_angle = 0
                    s_size = sty.symbolSize
                    if type(uSymbol) is type(''):
                        symbol = makeMarker(uSymbol,
                                    size = s_size,
                                    x =  s_x,
                                    y = s_y,
                                    fillColor = s_fillColor,
                                    strokeColor = s_strokeColor,
                                    strokeWidth = s_strokeWidth,
                                    angle = s_angle,
                                    )
                    else:
                        symbol = uSymbol2Symbol(uSymbol,s_x,s_y,s_fillColor)
                        for k,v in (('size', s_size), ('fillColor', s_fillColor),
                                    ('x', s_x), ('y', s_y),
                                    ('strokeColor',s_strokeColor), ('strokeWidth',s_strokeWidth),
                                    ('angle',s_angle),):
                            if getattr(symbol,k,None) is None:
                                try:
                                    setattr(symbol,k,v)
                                except:
                                    pass
                    syms.append(symbol)

            # make up the 'strand'
            if rsty.fillColor:
                strand = Polygon(points)
                strand.fillColor = rsty.fillColor
                strand.strokeColor = None
                strand.strokeWidth = 0
                STRANDAREAS.append(strand)
            if rsty.strokeColor and rsty.strokeWidth:
                strand = PolyLine(points)
                strand.strokeColor = rsty.strokeColor
                strand.strokeWidth = rsty.strokeWidth
                strand.strokeDashArray = rsty.strokeDashArray
                STRANDS.append(strand)
            rowIdx += 1

        for s in (STRANDAREAS+STRANDS+syms+S+labs): g.add(s)
        return g

def sample1():
    "Make a simple spider chart"
    d = Drawing(400, 400)
    sp = SpiderChart()
    sp.x = 50
    sp.y = 50
    sp.width = 300
    sp.height = 300
    sp.data = [[10,12,14,16,14,12], [6,8,10,12,9,15],[7,8,17,4,12,8]]
    sp.labels = ['a','b','c','d','e','f']
    sp.strands[0].strokeColor = colors.cornsilk
    sp.strands[1].strokeColor = colors.cyan
    sp.strands[2].strokeColor = colors.palegreen
    sp.strands[0].fillColor = colors.cornsilk
    sp.strands[1].fillColor = colors.cyan
    sp.strands[2].fillColor = colors.palegreen
    sp.spokes.strokeDashArray = (2,2)
    d.add(sp)
    return d


def sample2():
    "Make a spider chart with markers, but no fill"
    d = Drawing(400, 400)
    sp = SpiderChart()
    sp.x = 50
    sp.y = 50
    sp.width = 300
    sp.height = 300
    sp.data = [[10,12,14,16,14,12], [6,8,10,12,9,15],[7,8,17,4,12,8]]
    sp.labels = ['U','V','W','X','Y','Z']
    sp.strands.strokeWidth = 1
    sp.strands[0].fillColor = colors.pink
    sp.strands[1].fillColor = colors.lightblue
    sp.strands[2].fillColor = colors.palegreen
    sp.strands[0].strokeColor = colors.red
    sp.strands[1].strokeColor = colors.blue
    sp.strands[2].strokeColor = colors.green
    sp.strands.symbol = "FilledDiamond"
    sp.strands[1].symbol = makeMarker("Circle")
    sp.strands[1].symbol.strokeWidth = 0.5
    sp.strands[1].symbol.fillColor = colors.yellow
    sp.strands.symbolSize = 6
    sp.strandLabels[0,3]._text = 'special'
    sp.strandLabels[0,1]._text = 'one'
    sp.strandLabels[0,0]._text = 'zero'
    sp.strandLabels[1,0]._text = 'Earth'
    sp.strandLabels[2,2]._text = 'Mars'
    sp.strandLabels.format = 'values'
    sp.strandLabels.dR = -5
    d.add(sp)
    return d


if __name__=='__main__':
    d = sample1()
    from reportlab.graphics.renderPDF import drawToFile
    drawToFile(d, 'spider.pdf')
    d = sample2()
    drawToFile(d, 'spider2.pdf')
