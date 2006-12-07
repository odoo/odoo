#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/graphics/charts/legends.py
"""This will be a collection of legends to be used with charts.
"""
__version__=''' $Id$ '''

import string, copy

from reportlab.lib import colors
from reportlab.lib.validators import isNumber, OneOf, isString, isColorOrNone, isNumberOrNone, isListOfNumbersOrNone
from reportlab.lib.attrmap import *
from reportlab.pdfbase.pdfmetrics import stringWidth, getFont
from reportlab.graphics.widgetbase import Widget
from reportlab.graphics.shapes import Drawing, Group, String, Rect, Line, STATE_DEFAULTS


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
        callout = AttrMapValue(None, desc="a user callout(self,g,x,y,(color,text))"),
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

    def _calculateMaxWidth(self, colorNamePairs):
        "Calculate the maximum width of some given strings."
        m = 0
        for t in map(lambda p:str(p[1]),colorNamePairs):
            if t:
                for s in string.split(t,'\n'):
                    m = max(m,stringWidth(s, self.fontName, self.fontSize))
        return m


    def _calcHeight(self):
        deltay = self.deltay
        dy = self.dy
        thisy = upperlefty = self.y - dy
        ascent=getFont(self.fontName).face.ascent/1000.
        if ascent==0: ascent=0.718 # default (from helvetica)
        leading = self.fontSize*1.2
        columnCount = 0
        count = 0
        lowy = upperlefty
        for unused, name in colorNamePairs:
            T = string.split(name and str(name) or '','\n')
            S = []
            # thisy+dy/2 = y+leading/2
            y = thisy+(dy-ascent)*0.5-leading
            newy = thisy-max(deltay,len(S)*leading)
            lowy = min(y,newy)
            if count == columnMaximum-1:
                count = 0
                thisy = upperlefty
                columnCount = columnCount + 1
            else:
                thisy = newy
                count = count+1
        return upperlefty - lowy

    def draw(self):
        g = Group()
        colorNamePairs = self.colorNamePairs
        thisx = upperleftx = self.x
        thisy = upperlefty = self.y - self.dy
        dx, dy, alignment, columnMaximum = self.dx, self.dy, self.alignment, self.columnMaximum
        deltax, deltay, dxTextSpace = self.deltax, self.deltay, self.dxTextSpace
        fontName, fontSize, fillColor = self.fontName, self.fontSize, self.fillColor
        strokeWidth, strokeColor = self.strokeWidth, self.strokeColor
        leading = fontSize*1.2
        if not deltay:
            deltay = max(dy,leading)+self.autoYPadding
        if not deltax:
            maxWidth = self._calculateMaxWidth(colorNamePairs)
            deltax = maxWidth+dx+dxTextSpace+self.autoXPadding
        else:
            if alignment=='left': maxWidth = self._calculateMaxWidth(colorNamePairs)

        def gAdd(t,g=g,fontName=fontName,fontSize=fontSize,fillColor=fillColor):
            t.fontName = fontName
            t.fontSize = fontSize
            t.fillColor = fillColor
            return g.add(t)

        ascent=getFont(fontName).face.ascent/1000.
        if ascent==0: ascent=0.718 # default (from helvetica)
        ascent=ascent*fontSize # normalize

        columnCount = 0
        count = 0
        callout = getattr(self,'callout',None)
        for col, name in colorNamePairs:
            T = string.split(name and str(name) or '','\n')
            S = []
            # thisy+dy/2 = y+leading/2
            y = thisy+(dy-ascent)*0.5
            if callout: callout(self,g,thisx,y,colorNamePairs[count])
            if alignment == "left":
                for t in T:
                    # align text to left
                    s = String(thisx+maxWidth,y,t)
                    s.textAnchor = "end"
                    S.append(s)
                    y = y-leading
                x = thisx+maxWidth+dxTextSpace
            elif alignment == "right":
                for t in T:
                    # align text to right
                    s = String(thisx+dx+dxTextSpace, y, t)
                    s.textAnchor = "start"
                    S.append(s)
                    y = y-leading
                x = thisx
            else:
                raise ValueError, "bad alignment"

            # Make a 'normal' color swatch...
            if isinstance(col, colors.Color):
                r = Rect(x, thisy, dx, dy)
                r.fillColor = col
                r.strokeColor = strokeColor
                r.strokeWidth = strokeWidth
                g.add(r)
            else:
                #try and see if we should do better.
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

            if count%columnMaximum == columnMaximum-1:
                thisx = thisx+deltax
                thisy = upperlefty
                columnCount = columnCount + 1
            else:
                thisy = thisy-max(deltay,len(S)*leading)
            count = count+1

        return g


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

    _attrMap = AttrMap(
        x = AttrMapValue(isNumber, desc="x-coordinate of upper-left reference point"),
        y = AttrMapValue(isNumber, desc="y-coordinate of upper-left reference point"),
        deltax = AttrMapValue(isNumberOrNone, desc="x-distance between neighbouring line-swatches"),
        deltay = AttrMapValue(isNumberOrNone, desc="y-distance between neighbouring line-swatches"),
        dxTextSpace = AttrMapValue(isNumber, desc="Distance between line-swatches and text"),
        autoXPadding = AttrMapValue(isNumber, desc="x Padding between columns if deltax=None"),
        autoYPadding = AttrMapValue(isNumber, desc="y Padding between rows if deltay=None"),
        dx = AttrMapValue(isNumber, desc="Width of line-swatch - ie length of the line"),
        dy = AttrMapValue(isNumber, desc="Height of line-swatch - ie strokeWidth to be used for the line"),
        columnMaximum = AttrMapValue(isNumber, desc="Max. number of items per column"),
        alignment = AttrMapValue(OneOf("left", "right"), desc="Alignment of text with respect to line-swatches"),
        colorNamePairs = AttrMapValue(None, desc="List of color/name tuples (color can also be widget)"),
        fontName = AttrMapValue(isString, desc="Font name of the strings"),
        fontSize = AttrMapValue(isNumber, desc="Font size of the strings"),
        fillColor = AttrMapValue(isColorOrNone, desc=""),
        strokeColor = AttrMapValue(isColorOrNone, desc="Stroke color of the line-swatches"),
        strokeWidth = AttrMapValue(isNumber, desc="Width of the line-swatches"),
        callout = AttrMapValue(None, desc="a user callout(self,g,x,y,(color,text))"),
       )

    def __init__(self):
        Legend.__init__(self)

        # Size of swatch rectangle.
        self.dx = 10 #width of line
        self.dy = 2  #strokeWidth for line

        # Color/name pairs.
        self.colorNamePairs = []
        for col, colName in [ (colors.red, "red"),
                                (colors.blue, "blue"),
                                (colors.green, "green"),
                                (colors.pink, "pink"),
                                (colors.yellow, "yellow") ]:
            l =  LineSwatch()
            l.strokeColor = col
            self.colorNamePairs.append((l, colName))

        # Font name and size of the labels.
        self.fillColor = STATE_DEFAULTS['fillColor']
        self.strokeColor = STATE_DEFAULTS['strokeColor']
        self.strokeWidth = STATE_DEFAULTS['strokeWidth']

    def draw(self):
        g = Group()
        colorNamePairs = self.colorNamePairs
        thisx = upperleftx = self.x
        thisy = upperlefty = self.y - self.dy
        dx, dy, alignment, columnMaximum = self.dx, self.dy, self.alignment, self.columnMaximum
        deltax, deltay, dxTextSpace = self.deltax, self.deltay, self.dxTextSpace
        fontName, fontSize, fillColor = self.fontName, self.fontSize, self.fillColor
        strokeWidth, strokeColor = self.strokeWidth, self.strokeColor
        leading = fontSize*1.2
        if not deltay:
            deltay = max(dy,leading)+self.autoYPadding
        if not deltax:
            maxWidth = self._calculateMaxWidth(colorNamePairs)
            deltax = maxWidth+dx+dxTextSpace+self.autoXPadding
        else:
            if alignment=='left': maxWidth = self._calculateMaxWidth(colorNamePairs)

        def gAdd(t,g=g,fontName=fontName,fontSize=fontSize,fillColor=fillColor):
            t.fontName = fontName
            t.fontSize = fontSize
            t.fillColor = fillColor
            return g.add(t)

        ascent=getFont(fontName).face.ascent/1000.
        if ascent==0: ascent=0.718 # default (from helvetica)
        ascent=ascent*fontSize # normalize

        columnCount = 0
        count = 0
        callout = getattr(self,'callout',None)
        for col, name in colorNamePairs:
            T = string.split(name and str(name) or '','\n')
            S = []
            # thisy+dy/2 = y+leading/2
            y = thisy+(dy-ascent)*0.5
            if callout: callout(self,g,thisx,y,colorNamePairs[count])
            if alignment == "left":
                for t in T:
                    # align text to left
                    s = String(thisx+maxWidth,y,t)
                    s.textAnchor = "end"
                    S.append(s)
                    y = y-leading
                x = thisx+maxWidth+dxTextSpace
            elif alignment == "right":
                for t in T:
                    # align text to right
                    s = String(thisx+dx+dxTextSpace, y, t)
                    s.textAnchor = "start"
                    S.append(s)
                    y = y-leading
                x = thisx
            else:
                raise ValueError, "bad alignment"

            # Make a 'normal' color line-swatch...
            if isinstance(col, colors.Color):
                l =  LineSwatch()
                l.x = x
                l.y = thisy
                l.width = dx
                l.height = dy
                l.strokeColor = col
                g.add(l)
            else:
                #try and see if we should do better.
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

            if count%columnMaximum == columnMaximum-1:
                thisx = thisx+deltax
                thisy = upperlefty
                columnCount = columnCount + 1
            else:
                thisy = thisy-max(deltay,len(S)*leading)
            count = count+1

        return g



    def demo(self):
        "Make sample legend."

        d = Drawing(200, 100)

        legend = Legend()
        legend.alignment = 'left'
        legend.x = 0
        legend.y = 100
        legend.dxTextSpace = 5
        items = string.split('red green blue yellow pink black white', ' ')
        items = map(lambda i:(getattr(colors, i), i), items)
        legend.colorNamePairs = items

        d.add(legend, 'legend')

        return d


def sample1c():
    "Make sample legend."

    d = Drawing(200, 100)

    legend = Legend()
    legend.alignment = 'right'
    legend.x = 0
    legend.y = 100
    legend.dxTextSpace = 5
    items = string.split('red green blue yellow pink black white', ' ')
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
    items = string.split('red green blue yellow pink black white', ' ')
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
    items = string.split('red green blue yellow pink black white', ' ')
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
    items = string.split('red green blue yellow pink black white', ' ')
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
