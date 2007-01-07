#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/graphics/charts/linecharts.py
"""
This modules defines a very preliminary Line Chart example.
"""
__version__=''' $Id: linecharts.py 2493 2004-12-22 16:14:25Z rgbecker $ '''

import string
from types import FunctionType, StringType

from reportlab.lib import colors
from reportlab.lib.validators import isNumber, isColor, isColorOrNone, isListOfStrings, \
                                    isListOfStringsOrNone, SequenceOf, isBoolean, NoneOr, \
                                    isListOfNumbersOrNone, isStringOrNone
from reportlab.lib.attrmap import *
from reportlab.lib.formatters import Formatter
from reportlab.graphics.widgetbase import Widget, TypedPropertyCollection, PropHolder
from reportlab.graphics.shapes import Line, Rect, Group, Drawing, Polygon, PolyLine
from reportlab.graphics.widgets.signsandsymbols import NoEntry
from reportlab.graphics.charts.axes import XCategoryAxis, YValueAxis
from reportlab.graphics.charts.textlabels import Label
from reportlab.graphics.widgets.markers import uSymbol2Symbol, isSymbol, makeMarker
from reportlab.graphics.charts.areas import PlotArea

class LineChartProperties(PropHolder):
    _attrMap = AttrMap(
        strokeWidth = AttrMapValue(isNumber, desc='Width of a line.'),
        strokeColor = AttrMapValue(isColorOrNone, desc='Color of a line.'),
        strokeDashArray = AttrMapValue(isListOfNumbersOrNone, desc='Dash array of a line.'),
        symbol = AttrMapValue(NoneOr(isSymbol), desc='Widget placed at data points.'),
        shader = AttrMapValue(None, desc='Shader Class.'),
        filler = AttrMapValue(None, desc='Filler Class.'),
        name = AttrMapValue(isStringOrNone, desc='Name of the line.'),
        )

class AbstractLineChart(PlotArea):

    def makeSwatchSample(self,rowNo, x, y, width, height):
        baseStyle = self.lines
        styleIdx = rowNo % len(baseStyle)
        style = baseStyle[styleIdx]
        color = style.strokeColor
        y = y+height/2.
        if self.joinedLines:
            dash = getattr(style, 'strokeDashArray', getattr(baseStyle,'strokeDashArray',None))
            strokeWidth= getattr(style, 'strokeWidth', getattr(style, 'strokeWidth',None))
            L = Line(x,y,x+width,y,strokeColor=color,strokeLineCap=0)
            if strokeWidth: L.strokeWidth = strokeWidth
            if dash: L.strokeDashArray = dash
        else:
            L = None

        if hasattr(style, 'symbol'):
            S = style.symbol
        elif hasattr(baseStyle, 'symbol'):
            S = baseStyle.symbol
        else:
            S = None

        if S: S = uSymbol2Symbol(S,x+width/2.,y,color)
        if S and L:
            g = Group()
            g.add(L)
            g.add(S)
            return g
        return S or L

    def getSeriesName(self,i,default=None):
        '''return series name i or default'''
        return getattr(self.lines[i],'name',default)

class LineChart(AbstractLineChart):
    pass

# This is conceptually similar to the VerticalBarChart.
# Still it is better named HorizontalLineChart... :-/

class HorizontalLineChart(LineChart):
    """Line chart with multiple lines.

    A line chart is assumed to have one category and one value axis.
    Despite its generic name this particular line chart class has
    a vertical value axis and a horizontal category one. It may
    evolve into individual horizontal and vertical variants (like
    with the existing bar charts).

    Available attributes are:

        x: x-position of lower-left chart origin
        y: y-position of lower-left chart origin
        width: chart width
        height: chart height

        useAbsolute: disables auto-scaling of chart elements (?)
        lineLabelNudge: distance of data labels to data points
        lineLabels: labels associated with data values
        lineLabelFormat: format string or callback function
        groupSpacing: space between categories

        joinedLines: enables drawing of lines

        strokeColor: color of chart lines (?)
        fillColor: color for chart background (?)
        lines: style list, used cyclically for data series

        valueAxis: value axis object
        categoryAxis: category axis object
        categoryNames: category names

        data: chart data, a list of data series of equal length
    """

    _attrMap = AttrMap(BASE=LineChart,
        useAbsolute = AttrMapValue(isNumber, desc='Flag to use absolute spacing values.'),
        lineLabelNudge = AttrMapValue(isNumber, desc='Distance between a data point and its label.'),
        lineLabels = AttrMapValue(None, desc='Handle to the list of data point labels.'),
        lineLabelFormat = AttrMapValue(None, desc='Formatting string or function used for data point labels.'),
        lineLabelArray = AttrMapValue(None, desc='explicit array of line label values, must match size of data if present.'),
        groupSpacing = AttrMapValue(isNumber, desc='? - Likely to disappear.'),
        joinedLines = AttrMapValue(isNumber, desc='Display data points joined with lines if true.'),
        lines = AttrMapValue(None, desc='Handle of the lines.'),
        valueAxis = AttrMapValue(None, desc='Handle of the value axis.'),
        categoryAxis = AttrMapValue(None, desc='Handle of the category axis.'),
        categoryNames = AttrMapValue(isListOfStringsOrNone, desc='List of category names.'),
        data = AttrMapValue(None, desc='Data to be plotted, list of (lists of) numbers.'),
        inFill = AttrMapValue(isBoolean, desc='Whether infilling should be done.'),
        reversePlotOrder = AttrMapValue(isBoolean, desc='If true reverse plot order.'),
        annotations = AttrMapValue(None, desc='list of callables, will be called with self, xscale, yscale.'),
        )

    def __init__(self):
        LineChart.__init__(self)

        # Allow for a bounding rectangle.
        self.strokeColor = None
        self.fillColor = None

        # Named so we have less recoding for the horizontal one :-)
        self.categoryAxis = XCategoryAxis()
        self.valueAxis = YValueAxis()

        # This defines two series of 3 points.  Just an example.
        self.data = [(100,110,120,130),
                     (70, 80, 80, 90)]
        self.categoryNames = ('North','South','East','West')

        self.lines = TypedPropertyCollection(LineChartProperties)
        self.lines.strokeWidth = 1
        self.lines[0].strokeColor = colors.red
        self.lines[1].strokeColor = colors.green
        self.lines[2].strokeColor = colors.blue

        # control spacing. if useAbsolute = 1 then
        # the next parameters are in points; otherwise
        # they are 'proportions' and are normalized to
        # fit the available space.
        self.useAbsolute = 0   #- not done yet
        self.groupSpacing = 1 #5

        self.lineLabels = TypedPropertyCollection(Label)
        self.lineLabelFormat = None
        self.lineLabelArray = None

        # This says whether the origin is above or below
        # the data point. +10 means put the origin ten points
        # above the data point if value > 0, or ten
        # points below if data value < 0.  This is different
        # to label dx/dy which are not dependent on the
        # sign of the data.
        self.lineLabelNudge = 10
        # If you have multiple series, by default they butt
        # together.

        # New line chart attributes.
        self.joinedLines = 1 # Connect items with straight lines.
        self.inFill = 0
        self.reversePlotOrder = 0


    def demo(self):
        """Shows basic use of a line chart."""

        drawing = Drawing(200, 100)

        data = [
                (13, 5, 20, 22, 37, 45, 19, 4),
                (14, 10, 21, 28, 38, 46, 25, 5)
                ]

        lc = HorizontalLineChart()

        lc.x = 20
        lc.y = 10
        lc.height = 85
        lc.width = 170
        lc.data = data
        lc.lines.symbol = makeMarker('Circle')

        drawing.add(lc)

        return drawing


    def calcPositions(self):
        """Works out where they go.

        Sets an attribute _positions which is a list of
        lists of (x, y) matching the data.
        """

        self._seriesCount = len(self.data)
        self._rowLength = max(map(len,self.data))

        if self.useAbsolute:
            # Dimensions are absolute.
            normFactor = 1.0
        else:
            # Dimensions are normalized to fit.
            normWidth = self.groupSpacing
            availWidth = self.categoryAxis.scale(0)[1]
            normFactor = availWidth / normWidth

        self._positions = []
        for rowNo in range(len(self.data)):
            lineRow = []
            for colNo in range(len(self.data[rowNo])):
                datum = self.data[rowNo][colNo]
                if datum is not None:
                    (groupX, groupWidth) = self.categoryAxis.scale(colNo)
                    x = groupX + (0.5 * self.groupSpacing * normFactor)
                    y = self.valueAxis.scale(0)
                    height = self.valueAxis.scale(datum) - y
                    lineRow.append((x, y+height))
            self._positions.append(lineRow)


    def _innerDrawLabel(self, rowNo, colNo, x, y):
        "Draw a label for a given item in the list."

        labelFmt = self.lineLabelFormat
        labelValue = self.data[rowNo][colNo]

        if labelFmt is None:
            labelText = None
        elif type(labelFmt) is StringType:
            if labelFmt == 'values':
                labelText = self.lineLabelArray[rowNo][colNo]
            else:
                labelText = labelFmt % labelValue
        elif type(labelFmt) is FunctionType:
            labelText = labelFmt(labelValue)
        elif isinstance(labelFmt, Formatter):
            labelText = labelFmt(labelValue)
        else:
            msg = "Unknown formatter type %s, expected string or function"
            raise Exception, msg % labelFmt

        if labelText:
            label = self.lineLabels[(rowNo, colNo)]
            # Make sure labels are some distance off the data point.
            if y > 0:
                label.setOrigin(x, y + self.lineLabelNudge)
            else:
                label.setOrigin(x, y - self.lineLabelNudge)
            label.setText(labelText)
        else:
            label = None
        return label

    def drawLabel(self, G, rowNo, colNo, x, y):
        '''Draw a label for a given item in the list.
        G must have an add method'''
        G.add(self._innerDrawLabel(rowNo,colNo,x,y))

    def makeLines(self):
        g = Group()

        labelFmt = self.lineLabelFormat
        P = range(len(self._positions))
        if self.reversePlotOrder: P.reverse()
        inFill = self.inFill
        if inFill:
            inFillY = self.categoryAxis._y
            inFillX0 = self.valueAxis._x
            inFillX1 = inFillX0 + self.categoryAxis._length
            inFillG = getattr(self,'_inFillG',g)

        # Iterate over data rows.
        for rowNo in P:
            row = self._positions[rowNo]
            styleCount = len(self.lines)
            styleIdx = rowNo % styleCount
            rowStyle = self.lines[styleIdx]
            rowColor = rowStyle.strokeColor
            dash = getattr(rowStyle, 'strokeDashArray', None)

            if hasattr(self.lines[styleIdx], 'strokeWidth'):
                strokeWidth = self.lines[styleIdx].strokeWidth
            elif hasattr(self.lines, 'strokeWidth'):
                strokeWidth = self.lines.strokeWidth
            else:
                strokeWidth = None

            # Iterate over data columns.
            if self.joinedLines:
                points = []
                for colNo in range(len(row)):
                    points += row[colNo]
                if inFill:
                    points = points + [inFillX1,inFillY,inFillX0,inFillY]
                    inFillG.add(Polygon(points,fillColor=rowColor,strokeColor=rowColor,strokeWidth=0.1))
                else:
                    line = PolyLine(points,strokeColor=rowColor,strokeLineCap=0,strokeLineJoin=1)
                    if strokeWidth:
                        line.strokeWidth = strokeWidth
                    if dash:
                        line.strokeDashArray = dash
                    g.add(line)

            if hasattr(self.lines[styleIdx], 'symbol'):
                uSymbol = self.lines[styleIdx].symbol
            elif hasattr(self.lines, 'symbol'):
                uSymbol = self.lines.symbol
            else:
                uSymbol = None

            if uSymbol:
                for colNo in range(len(row)):
                    x1, y1 = row[colNo]
                    symbol = uSymbol2Symbol(uSymbol,x1,y1,rowStyle.strokeColor)
                    if symbol: g.add(symbol)

            # Draw item labels.
            for colNo in range(len(row)):
                x1, y1 = row[colNo]
                self.drawLabel(g, rowNo, colNo, x1, y1)

        return g

    def draw(self):
        "Draws itself."

        vA, cA = self.valueAxis, self.categoryAxis
        vA.setPosition(self.x, self.y, self.height)
        if vA: vA.joinAxis = cA
        if cA: cA.joinAxis = vA
        vA.configure(self.data)

        # If zero is in chart, put x axis there, otherwise
        # use bottom.
        xAxisCrossesAt = vA.scale(0)
        if ((xAxisCrossesAt > self.y + self.height) or (xAxisCrossesAt < self.y)):
            y = self.y
        else:
            y = xAxisCrossesAt

        cA.setPosition(self.x, y, self.width)
        cA.configure(self.data)

        self.calcPositions()

        g = Group()
        g.add(self.makeBackground())
        if self.inFill:
            self._inFillG = Group()
            g.add(self._inFillG)

        g.add(cA)
        g.add(vA)
        vA.gridStart = cA._x
        vA.gridEnd = cA._x+cA._length
        cA.gridStart = vA._y
        cA.gridEnd = vA._y+vA._length
        cA.makeGrid(g,parent=self)
        vA.makeGrid(g,parent=self)
        g.add(self.makeLines())
        for a in getattr(self,'annotations',()): g.add(a(self,cA.scale,vA.scale))
        return g

def _cmpFakeItem(a,b):
    '''t, z0, z1, x, y = a[:5]'''
    return cmp((-a[1],a[3],a[0],-a[4]),(-b[1],b[3],b[0],-b[4]))

class _FakeGroup:
    def __init__(self):
        self._data = []

    def add(self,what):
        if what: self._data.append(what)

    def value(self):
        return self._data

    def sort(self):
        self._data.sort(_cmpFakeItem)
        #for t in self._data: print t

class HorizontalLineChart3D(HorizontalLineChart):
    _attrMap = AttrMap(BASE=HorizontalLineChart,
        theta_x = AttrMapValue(isNumber, desc='dx/dz'),
        theta_y = AttrMapValue(isNumber, desc='dy/dz'),
        zDepth = AttrMapValue(isNumber, desc='depth of an individual series'),
        zSpace = AttrMapValue(isNumber, desc='z gap around series'),
        )
    theta_x = .5
    theta_y = .5
    zDepth = 10
    zSpace = 3

    def calcPositions(self):
        HorizontalLineChart.calcPositions(self)
        nSeries = self._seriesCount
        zSpace = self.zSpace
        zDepth = self.zDepth
        if self.categoryAxis.style=='parallel_3d':
            _3d_depth = nSeries*zDepth+(nSeries+1)*zSpace
        else:
            _3d_depth = zDepth + 2*zSpace
        self._3d_dx = self.theta_x*_3d_depth
        self._3d_dy = self.theta_y*_3d_depth

    def _calc_z0(self,rowNo):
        zSpace = self.zSpace
        if self.categoryAxis.style=='parallel_3d':
            z0 = rowNo*(self.zDepth+zSpace)+zSpace
        else:
            z0 = zSpace
        return z0

    def _zadjust(self,x,y,z):
        return x+z*self.theta_x, y+z*self.theta_y

    def makeLines(self):
        labelFmt = self.lineLabelFormat
        P = range(len(self._positions))
        if self.reversePlotOrder: P.reverse()
        inFill = self.inFill
        assert not inFill, "inFill not supported for 3d yet"
        #if inFill:
            #inFillY = self.categoryAxis._y
            #inFillX0 = self.valueAxis._x
            #inFillX1 = inFillX0 + self.categoryAxis._length
            #inFillG = getattr(self,'_inFillG',g)
        zDepth = self.zDepth
        _zadjust = self._zadjust
        theta_x = self.theta_x
        theta_y = self.theta_y
        F = _FakeGroup()
        from utils3d import _make_3d_line_info
        tileWidth = getattr(self,'_3d_tilewidth',None)
        if not tileWidth and self.categoryAxis.style!='parallel_3d': tileWidth = 1

        # Iterate over data rows.
        for rowNo in P:
            row = self._positions[rowNo]
            n = len(row)
            styleCount = len(self.lines)
            styleIdx = rowNo % styleCount
            rowStyle = self.lines[styleIdx]
            rowColor = rowStyle.strokeColor
            dash = getattr(rowStyle, 'strokeDashArray', None)
            z0 = self._calc_z0(rowNo)
            z1 = z0 + zDepth

            if hasattr(self.lines[styleIdx], 'strokeWidth'):
                strokeWidth = self.lines[styleIdx].strokeWidth
            elif hasattr(self.lines, 'strokeWidth'):
                strokeWidth = self.lines.strokeWidth
            else:
                strokeWidth = None

            # Iterate over data columns.
            if self.joinedLines:
                if n:
                    x0, y0 = row[0]
                    for colNo in xrange(1,n):
                        x1, y1 = row[colNo]
                        _make_3d_line_info( F, x0, x1, y0, y1, z0, z1,
                                theta_x, theta_y,
                                rowColor, fillColorShaded=None, tileWidth=tileWidth,
                                strokeColor=None, strokeWidth=None, strokeDashArray=None,
                                shading=0.1)
                        x0, y0 = x1, y1

            if hasattr(self.lines[styleIdx], 'symbol'):
                uSymbol = self.lines[styleIdx].symbol
            elif hasattr(self.lines, 'symbol'):
                uSymbol = self.lines.symbol
            else:
                uSymbol = None

            if uSymbol:
                for colNo in xrange(n):
                    x1, y1 = row[colNo]
                    x1, y1 = _zadjust(x1,y1,z0)
                    symbol = uSymbol2Symbol(uSymbol,x1,y1,rowColor)
                    if symbol: F.add((2,z0,z0,x1,y1,symbol))

            # Draw item labels.
            for colNo in xrange(n):
                x1, y1 = row[colNo]
                x1, y1 = _zadjust(x1,y1,z0)
                L = self._innerDrawLabel(rowNo, colNo, x1, y1)
                if L: F.add((2,z0,z0,x1,y1,L))

        F.sort()
        g = Group()
        map(lambda x,a=g.add: a(x[-1]),F.value())
        return g

class VerticalLineChart(LineChart):
    pass


def sample1():
    drawing = Drawing(400, 200)

    data = [
            (13, 5, 20, 22, 37, 45, 19, 4),
            (5, 20, 46, 38, 23, 21, 6, 14)
            ]

    lc = HorizontalLineChart()

    lc.x = 50
    lc.y = 50
    lc.height = 125
    lc.width = 300
    lc.data = data
    lc.joinedLines = 1
    lc.lines.symbol = makeMarker('FilledDiamond')
    lc.lineLabelFormat = '%2.0f'

    catNames = string.split('Jan Feb Mar Apr May Jun Jul Aug', ' ')
    lc.categoryAxis.categoryNames = catNames
    lc.categoryAxis.labels.boxAnchor = 'n'

    lc.valueAxis.valueMin = 0
    lc.valueAxis.valueMax = 60
    lc.valueAxis.valueStep = 15

    drawing.add(lc)

    return drawing


class SampleHorizontalLineChart(HorizontalLineChart):
    "Sample class overwriting one method to draw additional horizontal lines."

    def demo(self):
        """Shows basic use of a line chart."""

        drawing = Drawing(200, 100)

        data = [
                (13, 5, 20, 22, 37, 45, 19, 4),
                (14, 10, 21, 28, 38, 46, 25, 5)
                ]

        lc = SampleHorizontalLineChart()

        lc.x = 20
        lc.y = 10
        lc.height = 85
        lc.width = 170
        lc.data = data
        lc.strokeColor = colors.white
        lc.fillColor = colors.HexColor(0xCCCCCC)

        drawing.add(lc)

        return drawing


    def makeBackground(self):
        g = Group()

        g.add(HorizontalLineChart.makeBackground(self))

        valAxis = self.valueAxis
        valTickPositions = valAxis._tickValues

        for y in valTickPositions:
            y = valAxis.scale(y)
            g.add(Line(self.x, y, self.x+self.width, y,
                       strokeColor = self.strokeColor))

        return g



def sample1a():
    drawing = Drawing(400, 200)

    data = [
            (13, 5, 20, 22, 37, 45, 19, 4),
            (5, 20, 46, 38, 23, 21, 6, 14)
            ]

    lc = SampleHorizontalLineChart()

    lc.x = 50
    lc.y = 50
    lc.height = 125
    lc.width = 300
    lc.data = data
    lc.joinedLines = 1
    lc.strokeColor = colors.white
    lc.fillColor = colors.HexColor(0xCCCCCC)
    lc.lines.symbol = makeMarker('FilledDiamond')
    lc.lineLabelFormat = '%2.0f'

    catNames = string.split('Jan Feb Mar Apr May Jun Jul Aug', ' ')
    lc.categoryAxis.categoryNames = catNames
    lc.categoryAxis.labels.boxAnchor = 'n'

    lc.valueAxis.valueMin = 0
    lc.valueAxis.valueMax = 60
    lc.valueAxis.valueStep = 15

    drawing.add(lc)

    return drawing


def sample2():
    drawing = Drawing(400, 200)

    data = [
            (13, 5, 20, 22, 37, 45, 19, 4),
            (5, 20, 46, 38, 23, 21, 6, 14)
            ]

    lc = HorizontalLineChart()

    lc.x = 50
    lc.y = 50
    lc.height = 125
    lc.width = 300
    lc.data = data
    lc.joinedLines = 1
    lc.lines.symbol = makeMarker('Smiley')
    lc.lineLabelFormat = '%2.0f'
    lc.strokeColor = colors.black
    lc.fillColor = colors.lightblue

    catNames = string.split('Jan Feb Mar Apr May Jun Jul Aug', ' ')
    lc.categoryAxis.categoryNames = catNames
    lc.categoryAxis.labels.boxAnchor = 'n'

    lc.valueAxis.valueMin = 0
    lc.valueAxis.valueMax = 60
    lc.valueAxis.valueStep = 15

    drawing.add(lc)

    return drawing


def sample3():
    drawing = Drawing(400, 200)

    data = [
            (13, 5, 20, 22, 37, 45, 19, 4),
            (5, 20, 46, 38, 23, 21, 6, 14)
            ]

    lc = HorizontalLineChart()

    lc.x = 50
    lc.y = 50
    lc.height = 125
    lc.width = 300
    lc.data = data
    lc.joinedLines = 1
    lc.lineLabelFormat = '%2.0f'
    lc.strokeColor = colors.black

    lc.lines[0].symbol = makeMarker('Smiley')
    lc.lines[1].symbol = NoEntry
    lc.lines[0].strokeWidth = 2
    lc.lines[1].strokeWidth = 4

    catNames = string.split('Jan Feb Mar Apr May Jun Jul Aug', ' ')
    lc.categoryAxis.categoryNames = catNames
    lc.categoryAxis.labels.boxAnchor = 'n'

    lc.valueAxis.valueMin = 0
    lc.valueAxis.valueMax = 60
    lc.valueAxis.valueStep = 15

    drawing.add(lc)

    return drawing
