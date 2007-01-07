#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/graphics/charts/legends.py
"""This will be a collection of legends to be used with charts.
"""
__version__=''' $Id: legends.py 2604 2005-06-08 10:12:46Z rgbecker $ '''

import copy, operator

from reportlab.lib import colors
from reportlab.lib.validators import isNumber, OneOf, isString, isColorOrNone,\
        isNumberOrNone, isListOfNumbersOrNone, isStringOrNone, isBoolean,\
        NoneOr, AutoOr, isAuto, Auto, isBoxAnchor, SequenceOf
from reportlab.lib.attrmap import *
from reportlab.pdfbase.pdfmetrics import stringWidth, getFont
from reportlab.graphics.widgetbase import Widget, TypedPropertyCollection, PropHolder
from reportlab.graphics.shapes import Drawing, Group, String, Rect, Line, STATE_DEFAULTS
from reportlab.graphics.charts.areas import PlotArea
from reportlab.graphics.widgets.markers import uSymbol2Symbol, isSymbol
from reportlab.lib.utils import isSeqType


def _getStr(s):
    if isSeqType(s):
        return map(str,s)
    else:
        return str(s)

def _getLines(s):
    if isSeqType(s):
        return tuple([(x or '').split('\n') for x in s])
    else:
        return (s or '').split('\n')

def _getLineCount(s):
    T = _getLines(s)
    if isSeqType(s):
        return max([len(x) for x in T])
    else:
        return len(T)

def _getWidth(s,fontName, fontSize, sepSpace=0):
    if isSeqType(s):
        sum = 0
        for t in s:
            m = [stringWidth(x, fontName, fontSize) for x in t.split('\n')]
            sum += m and max(m) or 0
        sum += (len(s)-1)*sepSpace
        return sum
    m = [stringWidth(x, fontName, fontSize) for x in s.split('\n')]
    return m and max(m) or 0

class Legend(Widget):
    """A simple legend containing rectangular swatches and strings.

    The swatches are filled rectangles whenever the respective
    color object in 'colorNamePairs' is a subclass of Color in
    reportlab.lib.colors. Otherwise the object passed instead is
    assumed to have 'x', 'y', 'width' and 'height' attributes.
    A legend then tries to set them or catches any error. This
    lets you plug-in any widget you like as a replacement for
    the default rectangular swatches.

    Strings can be nicely aligned left or right to the swatches.
    """

    _attrMap = AttrMap(
        x = AttrMapValue(isNumber, desc="x-coordinate of upper-left reference point"),
        y = AttrMapValue(isNumber, desc="y-coordinate of upper-left reference point"),
        deltax = AttrMapValue(isNumberOrNone, desc="x-distance between neighbouring swatches"),
        deltay = AttrMapValue(isNumberOrNone, desc="y-distance between neighbouring swatches"),
        dxTextSpace = AttrMapValue(isNumber, desc="Distance between swatch rectangle and text"),
        autoXPadding = AttrMapValue(isNumber, desc="x Padding between columns if deltax=None"),
        autoYPadding = AttrMapValue(isNumber, desc="y Padding between rows if deltay=None"),
        yGap = AttrMapValue(isNumber, desc="Additional gap between rows"),
        dx = AttrMapValue(isNumber, desc="Width of swatch rectangle"),
        dy = AttrMapValue(isNumber, desc="Height of swatch rectangle"),
        columnMaximum = AttrMapValue(isNumber, desc="Max. number of items per column"),
        alignment = AttrMapValue(OneOf("left", "right"), desc="Alignment of text with respect to swatches"),
        colorNamePairs = AttrMapValue(None, desc="List of color/name tuples (color can also be widget)"),
        fontName = AttrMapValue(isString, desc="Font name of the strings"),
        fontSize = AttrMapValue(isNumber, desc="Font size of the strings"),
        fillColor = AttrMapValue(isColorOrNone, desc=""),
        strokeColor = AttrMapValue(isColorOrNone, desc="Border color of the swatches"),
        strokeWidth = AttrMapValue(isNumber, desc="Width of the border color of the swatches"),
        swatchMarker = AttrMapValue(NoneOr(AutoOr(isSymbol)), desc="None, Auto() or makeMarker('Diamond') ..."),
        callout = AttrMapValue(None, desc="a user callout(self,g,x,y,(color,text))"),
        boxAnchor = AttrMapValue(isBoxAnchor,'Anchor point for the legend area'),
        variColumn = AttrMapValue(isBoolean,'If true column widths may vary (default is false)'),
        dividerLines = AttrMapValue(OneOf(0,1,2,3,4,5,6,7),'If 1 we have dividers between the rows | 2 for extra top | 4 for bottom'),
        dividerWidth = AttrMapValue(isNumber, desc="dividerLines width"),
        dividerColor = AttrMapValue(isColorOrNone, desc="dividerLines color"),
        dividerDashArray = AttrMapValue(isListOfNumbersOrNone, desc='Dash array for dividerLines.'),
        dividerOffsX = AttrMapValue(SequenceOf(isNumber,emptyOK=0,lo=2,hi=2), desc='divider lines X offsets'),
        dividerOffsY = AttrMapValue(isNumber, desc="dividerLines Y offset"),
        sepSpace = AttrMapValue(isNumber, desc="separator spacing"),
        colEndCallout = AttrMapValue(None, desc="a user callout(self,g, x, xt, y,width, lWidth)"),
       )

    def __init__(self):
        # Upper-left reference point.
        self.x = 0
        self.y = 0

        # Alginment of text with respect to swatches.
        self.alignment = "left"

        # x- and y-distances between neighbouring swatches.
        self.deltax = 75
        self.deltay = 20
        self.autoXPadding = 5
        self.autoYPadding = 2

        # Size of swatch rectangle.
        self.dx = 10
        self.dy = 10

        # Distance between swatch rectangle and text.
        self.dxTextSpace = 10

        # Max. number of items per column.
        self.columnMaximum = 3

        # Color/name pairs.
        self.colorNamePairs = [ (colors.red, "red"),
                                (colors.blue, "blue"),
                                (colors.green, "green"),
                                (colors.pink, "pink"),
                                (colors.yellow, "yellow") ]

        # Font name and size of the labels.
        self.fontName = STATE_DEFAULTS['fontName']
        self.fontSize = STATE_DEFAULTS['fontSize']
        self.fillColor = STATE_DEFAULTS['fillColor']
        self.strokeColor = STATE_DEFAULTS['strokeColor']
        self.strokeWidth = STATE_DEFAULTS['strokeWidth']
        self.swatchMarker = None
        self.boxAnchor = 'nw'
        self.yGap = 0
        self.variColumn = 0
        self.dividerLines = 0
        self.dividerWidth = 0.5
        self.dividerDashArray = None
        self.dividerColor = colors.black
        self.dividerOffsX = (0,0)
        self.dividerOffsY = 0
        self.sepSpace = 0
        self.colEndCallout = None

    def _getChartStyleName(self,chart):
        for a in 'lines', 'bars', 'slices', 'strands':
            if hasattr(chart,a): return a
        return None

    def _getChartStyle(self,chart):
        return getattr(chart,self._getChartStyleName(chart),None)
        
    def _getTexts(self,colorNamePairs):
        if not isAuto(colorNamePairs):
            texts = [_getStr(p[1]) for p in colorNamePairs]
        else:
            chart = colorNamePairs.chart
            texts = [str(chart.getSeriesName(i,'series %d' % i)) for i in xrange(chart._seriesCount)]
        return texts

    def _calculateMaxWidth(self, colorNamePairs):
        "Calculate the maximum width of some given strings."
        M = []
        a = M.append
        for t in self._getTexts(colorNamePairs):
            M.append(_getWidth(t, self.fontName, self.fontSize,self.sepSpace))
        if not M: return 0
        if self.variColumn:
            columnMaximum = self.columnMaximum
            return [max(M[r:r+columnMaximum]) for r in range(0,len(M),self.columnMaximum)]
        else:
            return max(M)

    def _calcHeight(self):
        dy = self.dy
        yGap = self.yGap
        thisy = upperlefty = self.y - dy
        fontSize = self.fontSize
        ascent=getFont(self.fontName).face.ascent/1000.
        if ascent==0: ascent=0.718 # default (from helvetica)
        ascent *= fontSize
        leading = fontSize*1.2
        deltay = self.deltay
        if not deltay: deltay = max(dy,leading)+self.autoYPadding
        columnCount = 0
        count = 0
        lowy = upperlefty
        lim = self.columnMaximum - 1
        for name in self._getTexts(self.colorNamePairs):
            y0 = thisy+(dy-ascent)*0.5
            y = y0 - _getLineCount(name)*leading
            leadingMove = 2*y0-y-thisy
            newy = thisy-max(deltay,leadingMove)-yGap
            lowy = min(y,newy,lowy)
            if count==lim:
                count = 0
                thisy = upperlefty
                columnCount = columnCount + 1
            else:
                thisy = newy
                count = count+1
        return upperlefty - lowy

    def _defaultSwatch(self,x,thisy,dx,dy,fillColor,strokeWidth,strokeColor):
        return Rect(x, thisy, dx, dy,
                    fillColor = fillColor,
                    strokeColor = strokeColor,
                    strokeWidth = strokeWidth,
                    )

    def draw(self):
        colorNamePairs = self.colorNamePairs
        autoCP = isAuto(colorNamePairs)
        if autoCP:
            chart = getattr(colorNamePairs,'chart',getattr(colorNamePairs,'obj',None))
            swatchMarker = None
            autoCP = Auto(obj=chart)
            n = chart._seriesCount
            chartTexts = self._getTexts(colorNamePairs)
        else:
            swatchMarker = getattr(self,'swatchMarker',None)
            if isAuto(swatchMarker):
                chart = getattr(swatchMarker,'chart',getattr(swatchMarker,'obj',None))
                swatchMarker = Auto(obj=chart)
            n = len(colorNamePairs)
        dx = self.dx
        dy = self.dy
        alignment = self.alignment
        columnMaximum = self.columnMaximum
        deltax = self.deltax
        deltay = self.deltay
        dxTextSpace = self.dxTextSpace
        fontName = self.fontName
        fontSize = self.fontSize
        fillColor = self.fillColor
        strokeWidth = self.strokeWidth
        strokeColor = self.strokeColor
        leading = fontSize*1.2
        yGap = self.yGap
        if not deltay:
            deltay = max(dy,leading)+self.autoYPadding
        ba = self.boxAnchor
        baw = ba not in ('nw','w','sw','autox')
        maxWidth = self._calculateMaxWidth(colorNamePairs)
        nCols = int((n+columnMaximum-1)/columnMaximum)
        xW = dx+dxTextSpace+self.autoXPadding
        variColumn = self.variColumn
        if variColumn:
            width = reduce(operator.add,maxWidth,0)+xW*nCols
        else:
            deltax = max(maxWidth+xW,deltax)
            width = nCols*deltax
            maxWidth = nCols*[maxWidth]

        thisx = self.x
        thisy = self.y - self.dy
        if ba not in ('ne','n','nw','autoy'):
            height = self._calcHeight()
            if ba in ('e','c','w'):
                thisy += height/2.
            else:
                thisy += height
        if baw:
            if ba in ('n','c','s'):
                thisx -= width/2
            else:
                thisx -= width
        upperlefty = thisy

        g = Group()
        def gAdd(t,g=g,fontName=fontName,fontSize=fontSize,fillColor=fillColor):
            t.fontName = fontName
            t.fontSize = fontSize
            t.fillColor = fillColor
            return g.add(t)

        ascent=getFont(fontName).face.ascent/1000.
        if ascent==0: ascent=0.718 # default (from helvetica)
        ascent *= fontSize # normalize

        lim = columnMaximum - 1
        callout = getattr(self,'callout',None)
        dividerLines = self.dividerLines
        if dividerLines:
            dividerWidth = self.dividerWidth
            dividerColor = self.dividerColor
            dividerDashArray = self.dividerDashArray
            dividerOffsX = self.dividerOffsX
            dividerOffsY = self.dividerOffsY

        for i in xrange(n):
            if autoCP:
                col = autoCP
                col.index = i
                name = chartTexts[i]
            else:
                col, name = colorNamePairs[i]
                if isAuto(swatchMarker):
                    col = swatchMarker
                    col.index = i
                if isAuto(name):
                    name = getattr(swatchMarker,'chart',getattr(swatchMarker,'obj',None)).getSeriesName(i,'series %d' % i)
            T = _getLines(name)
            S = []
            j = int(i/columnMaximum)

            # thisy+dy/2 = y+leading/2
            y = y0 = thisy+(dy-ascent)*0.5

            if callout: callout(self,g,thisx,y,(col,name))
            if alignment == "left":
                if isSeqType(name):
                    for t in T[0]:
                        S.append(String(thisx,y,t,fontName=fontName,fontSize=fontSize,fillColor=fillColor,
                                textAnchor = "start"))
                        y -= leading
                    yd = y
                    y = y0
                    for t in T[1]:
                        S.append(String(thisx+maxWidth[j],y,t,fontName=fontName,fontSize=fontSize,fillColor=fillColor,
                                textAnchor = "end"))
                        y -= leading
                    y = min(yd,y)
                else:
                    for t in T:
                        # align text to left
                        S.append(String(thisx+maxWidth[j],y,t,fontName=fontName,fontSize=fontSize,fillColor=fillColor,
                                textAnchor = "end"))
                        y -= leading
                x = thisx+maxWidth[j]+dxTextSpace
            elif alignment == "right":
                if isSeqType(name):
                    y0 = y
                    for t in T[0]:
                        S.append(String(thisx+dx+dxTextSpace,y,t,fontName=fontName,fontSize=fontSize,fillColor=fillColor,
                                textAnchor = "start"))
                        y -= leading
                    yd = y
                    y = y0
                    for t in T[1]:
                        S.append(String(thisx+dx+dxTextSpace+maxWidth[j],y,t,fontName=fontName,fontSize=fontSize,fillColor=fillColor,
                                textAnchor = "end"))
                        y -= leading
                    y = min(yd,y)
                else:
                    for t in T:
                        # align text to right
                        S.append(String(thisx+dx+dxTextSpace,y,t,fontName=fontName,fontSize=fontSize,fillColor=fillColor,
                                textAnchor = "start"))
                        y -= leading
                x = thisx
            else:
                raise ValueError, "bad alignment"
            leadingMove = 2*y0-y-thisy

            if dividerLines:
                xd = thisx+dx+dxTextSpace+maxWidth[j]+dividerOffsX[1]
                yd = thisy+dy*0.5+dividerOffsY
                if ((dividerLines&1) and i%columnMaximum) or ((dividerLines&2) and not i%columnMaximum):
                    g.add(Line(thisx+dividerOffsX[0],yd,xd,yd,
                        strokeColor=dividerColor, strokeWidth=dividerWidth, strokeDashArray=dividerDashArray))

                if (dividerLines&4) and (i%columnMaximum==lim or i==(n-1)):
                    yd -= max(deltay,leadingMove)+yGap
                    g.add(Line(thisx+dividerOffsX[0],yd,xd,yd,
                        strokeColor=dividerColor, strokeWidth=dividerWidth, strokeDashArray=dividerDashArray))

            # Make a 'normal' color swatch...
            if isAuto(col):
                chart = getattr(col,'chart',getattr(col,'obj',None))
                g.add(chart.makeSwatchSample(getattr(col,'index',i),x,thisy,dx,dy))
            elif isinstance(col, colors.Color):
                if isSymbol(swatchMarker):
                    g.add(uSymbol2Symbol(swatchMarker,x+dx/2.,thisy+dy/2.,col))
                else:
                    g.add(self._defaultSwatch(x,thisy,dx,dy,fillColor=col,strokeWidth=strokeWidth,strokeColor=strokeColor))
            else:
                try:
                    c = copy.deepcopy(col)
                    c.x = x
                    c.y = thisy
                    c.width = dx
                    c.height = dy
                    g.add(c)
                except:
                    pass

            map(gAdd,S)
            if self.colEndCallout and (i%columnMaximum==lim or i==(n-1)):
                if alignment == "left":
                    xt = thisx
                else:
                    xt = thisx+dx+dxTextSpace
                yd = thisy+dy*0.5+dividerOffsY - (max(deltay,leadingMove)+yGap)
                self.colEndCallout(self, g, thisx, xt, yd, maxWidth[j], maxWidth[j]+dx+dxTextSpace)

            if i%columnMaximum==lim:
                if variColumn:
                    thisx += maxWidth[j]+xW
                else:
                    thisx = thisx+deltax
                thisy = upperlefty
            else:
                thisy = thisy-max(deltay,leadingMove)-yGap

        return g

    def demo(self):
        "Make sample legend."

        d = Drawing(200, 100)

        legend = Legend()
        legend.alignment = 'left'
        legend.x = 0
        legend.y = 100
        legend.dxTextSpace = 5
        items = 'red green blue yellow pink black white'.split()
        items = map(lambda i:(getattr(colors, i), i), items)
        legend.colorNamePairs = items

        d.add(legend, 'legend')

        return d

class TotalAnnotator:
    def __init__(self, lText='Total', rText='0.0', fontName='Times-Roman', fontSize=10,
            fillColor=colors.black, strokeWidth=0.5, strokeColor=colors.black, strokeDashArray=None,
            dx=0, dy=0, dly=0, dlx=(0,0)):
        self.lText = lText
        self.rText = rText
        self.fontName = fontName
        self.fontSize = fontSize
        self.fillColor = fillColor
        self.dy = dy
        self.dx = dx
        self.dly = dly
        self.dlx = dlx
        self.strokeWidth = strokeWidth
        self.strokeColor = strokeColor
        self.strokeDashArray = strokeDashArray

    def __call__(self,legend, g, x, xt, y, width, lWidth):
        from reportlab.graphics.shapes import String, Line
        fontSize = self.fontSize
        fontName = self.fontName
        fillColor = self.fillColor
        strokeColor = self.strokeColor
        strokeWidth = self.strokeWidth
        ascent=getFont(fontName).face.ascent/1000.
        if ascent==0: ascent=0.718 # default (from helvetica)
        ascent *= fontSize
        leading = fontSize*1.2
        yt = y+self.dy-ascent*1.3
        if self.lText and fillColor:
            g.add(String(xt,yt,self.lText,
                fontName=fontName,
                fontSize=fontSize,
                fillColor=fillColor,
                textAnchor = "start"))
        if self.rText:
            g.add(String(xt+width,yt,self.rText,
                fontName=fontName,
                fontSize=fontSize,
                fillColor=fillColor,
                textAnchor = "end"))
        if strokeWidth and strokeColor:
            yL = y+self.dly-leading
            g.add(Line(x+self.dlx[0],yL,x+self.dlx[1]+lWidth,yL,
                    strokeColor=strokeColor, strokeWidth=strokeWidth,
                    strokeDashArray=self.strokeDashArray))

class LineSwatch(Widget):
    """basically a Line with properties added so it can be used in a LineLegend"""
    _attrMap = AttrMap(
        x = AttrMapValue(isNumber, desc="x-coordinate for swatch line start point"),
        y = AttrMapValue(isNumber, desc="y-coordinate for swatch line start point"),
        width = AttrMapValue(isNumber, desc="length of swatch line"),
        height = AttrMapValue(isNumber, desc="used for line strokeWidth"),
        strokeColor = AttrMapValue(isColorOrNone, desc="color of swatch line"),
        strokeDashArray = AttrMapValue(isListOfNumbersOrNone, desc="dash array for swatch line"),
    )

    def __init__(self):
        from reportlab.lib.colors import red
        from reportlab.graphics.shapes import Line
        self.x = 0
        self.y = 0
        self.width  = 20
        self.height = 1
        self.strokeColor = red
        self.strokeDashArray = None

    def draw(self):
        l = Line(self.x,self.y,self.x+self.width,self.y)
        l.strokeColor = self.strokeColor
        l.strokeDashArray  = self.strokeDashArray
        l.strokeWidth = self.height
        return l

class LineLegend(Legend):
    """A subclass of Legend for drawing legends with lines as the
    swatches rather than rectangles. Useful for lineCharts and
    linePlots. Should be similar in all other ways the the standard
    Legend class.
    """

    def __init__(self):
        Legend.__init__(self)

        # Size of swatch rectangle.
        self.dx = 10
        self.dy = 2

    def _defaultSwatch(self,x,thisy,dx,dy,fillColor,strokeWidth,strokeColor):
        l =  LineSwatch()
        l.x = x
        l.y = thisy
        l.width = dx
        l.height = dy
        l.strokeColor = fillColor
        return l

def sample1c():
    "Make sample legend."

    d = Drawing(200, 100)

    legend = Legend()
    legend.alignment = 'right'
    legend.x = 0
    legend.y = 100
    legend.dxTextSpace = 5
    items = 'red green blue yellow pink black white'.split()
    items = map(lambda i:(getattr(colors, i), i), items)
    legend.colorNamePairs = items

    d.add(legend, 'legend')

    return d


def sample2c():
    "Make sample legend."

    d = Drawing(200, 100)

    legend = Legend()
    legend.alignment = 'right'
    legend.x = 20
    legend.y = 90
    legend.deltax = 60
    legend.dxTextSpace = 10
    legend.columnMaximum = 4
    items = 'red green blue yellow pink black white'.split()
    items = map(lambda i:(getattr(colors, i), i), items)
    legend.colorNamePairs = items

    d.add(legend, 'legend')

    return d

def sample3():
    "Make sample legend with line swatches."

    d = Drawing(200, 100)

    legend = LineLegend()
    legend.alignment = 'right'
    legend.x = 20
    legend.y = 90
    legend.deltax = 60
    legend.dxTextSpace = 10
    legend.columnMaximum = 4
    items = 'red green blue yellow pink black white'.split()
    items = map(lambda i:(getattr(colors, i), i), items)
    legend.colorNamePairs = items
    d.add(legend, 'legend')

    return d


def sample3a():
    "Make sample legend with line swatches and dasharrays on the lines."

    d = Drawing(200, 100)

    legend = LineLegend()
    legend.alignment = 'right'
    legend.x = 20
    legend.y = 90
    legend.deltax = 60
    legend.dxTextSpace = 10
    legend.columnMaximum = 4
    items = 'red green blue yellow pink black white'.split()
    darrays = ([2,1], [2,5], [2,2,5,5], [1,2,3,4], [4,2,3,4], [1,2,3,4,5,6], [1])
    cnp = []
    for i in range(0, len(items)):
        l =  LineSwatch()
        l.strokeColor = getattr(colors, items[i])
        l.strokeDashArray = darrays[i]
        cnp.append((l, items[i]))
    legend.colorNamePairs = cnp
    d.add(legend, 'legend')

    return d
