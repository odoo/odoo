#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/graphics/charts/linecharts.py

__version__='3.3.0'
__doc__="""This modules defines a very preliminary Line Chart example."""

from reportlab.lib import colors
from reportlab.lib.validators import isNumber, isNumberOrNone, isColorOrNone, \
                                    isListOfStringsOrNone, isBoolean, NoneOr, \
                                    isListOfNumbersOrNone, isStringOrNone, OneOf, Percentage
from reportlab.lib.attrmap import *
from reportlab.lib.utils import flatten
from reportlab.graphics.widgetbase import TypedPropertyCollection, PropHolder, tpcGetItem
from reportlab.graphics.shapes import Line, Rect, Group, Drawing, Polygon, PolyLine
from reportlab.graphics.widgets.signsandsymbols import NoEntry
from reportlab.graphics.charts.axes import XCategoryAxis, YValueAxis
from reportlab.graphics.charts.textlabels import Label
from reportlab.graphics.widgets.markers import uSymbol2Symbol, isSymbol, makeMarker
from reportlab.graphics.charts.areas import PlotArea
from reportlab.graphics.charts.legends import _objStr
from .utils import FillPairedData

class LineChartProperties(PropHolder):
    _attrMap = AttrMap(
        strokeWidth = AttrMapValue(isNumber, desc='Width of a line.'),
        strokeColor = AttrMapValue(isColorOrNone, desc='Color of a line or border.'),
        fillColor = AttrMapValue(isColorOrNone, desc='fill color of a bar.'),
        strokeDashArray = AttrMapValue(isListOfNumbersOrNone, desc='Dash array of a line.'),
        symbol = AttrMapValue(NoneOr(isSymbol), desc='Widget placed at data points.',advancedUsage=1),
        shader = AttrMapValue(None, desc='Shader Class.',advancedUsage=1),
        filler = AttrMapValue(None, desc='Filler Class.',advancedUsage=1),
        name = AttrMapValue(isStringOrNone, desc='Name of the line.'),
        lineStyle = AttrMapValue(NoneOr(OneOf('line','joinedLine','bar')), desc="What kind of plot this line is",advancedUsage=1),
        barWidth = AttrMapValue(isNumberOrNone,desc="Percentage of available width to be used for a bar",advancedUsage=1),
        inFill = AttrMapValue(isBoolean, desc='If true flood fill to x axis',advancedUsage=1),
        )

class AbstractLineChart(PlotArea):

    def makeSwatchSample(self,rowNo, x, y, width, height):
        baseStyle = self.lines
        styleIdx = rowNo % len(baseStyle)
        style = baseStyle[styleIdx]
        color = style.strokeColor
        yh2 = y+height/2.
        lineStyle = getattr(style,'lineStyle',None)
        if lineStyle=='bar':
            dash = getattr(style, 'strokeDashArray', getattr(baseStyle,'strokeDashArray',None))
            strokeWidth= getattr(style, 'strokeWidth', getattr(style, 'strokeWidth',None))
            L = Rect(x,y,width,height,strokeWidth=strokeWidth,strokeColor=color,strokeLineCap=0,strokeDashArray=dash,fillColor=getattr(style,'fillColor',color))
        elif self.joinedLines or lineStyle=='joinedLine':
            dash = getattr(style, 'strokeDashArray', getattr(baseStyle,'strokeDashArray',None))
            strokeWidth= getattr(style, 'strokeWidth', getattr(style, 'strokeWidth',None))
            L = Line(x,yh2,x+width,yh2,strokeColor=color,strokeLineCap=0)
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

        if S: S = uSymbol2Symbol(S,x+width/2.,yh2,color)
        if S and L:
            g = Group()
            g.add(L)
            g.add(S)
            return g
        return S or L

    def getSeriesName(self,i,default=None):
        '''return series name i or default'''
        return _objStr(getattr(self.lines[i],'name',default))

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
        useAbsolute = AttrMapValue(isNumber, desc='Flag to use absolute spacing values.',advancedUsage=1),
        lineLabelNudge = AttrMapValue(isNumber, desc='Distance between a data point and its label.',advancedUsage=1),
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
        inFill = AttrMapValue(isBoolean, desc='Whether infilling should be done.',advancedUsage=1),
        reversePlotOrder = AttrMapValue(isBoolean, desc='If true reverse plot order.',advancedUsage=1),
        annotations = AttrMapValue(None, desc='list of callables, will be called with self, xscale, yscale.',advancedUsage=1),
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
        self._rowLength = max(list(map(len,self.data)))

        if self.useAbsolute:
            # Dimensions are absolute.
            normFactor = 1.0
        else:
            # Dimensions are normalized to fit.
            normWidth = self.groupSpacing
            availWidth = self.categoryAxis.scale(0)[1]
            normFactor = availWidth / normWidth
        self._normFactor = normFactor
        self._yzero = yzero = self.valueAxis.scale(0)
        self._hngs = hngs = 0.5 * self.groupSpacing * normFactor

        pairs = set()
        P = [].append
        cscale = self.categoryAxis.scale
        vscale = self.valueAxis.scale
        data = self.data
        n = len(data)
        for rowNo,row in enumerate(data):
            if isinstance(row, FillPairedData):
                other = row.other
                if 0<=other<n:
                    if other==rowNo:
                        raise ValueError('data row %r may not be paired with itself' % rowNo)
                    t = (rowNo,other)
                    pairs.add((min(t),max(t)))
                else:
                    raise ValueError('data row %r is paired with invalid data row %r' % (rowNo, other))
            line = [].append
            for colNo,datum in enumerate(row):
                if datum is not None:
                    groupX, groupWidth = cscale(colNo)
                    x = groupX + hngs
                    y = yzero
                    height = vscale(datum) - y
                    line((x, y+height))
            P(line.__self__)
        P = P.__self__

        #if there are some paired lines we ensure only one is created
        for rowNo, other in pairs:
            P[rowNo] = FillPairedData(P[rowNo],other)
        self._pairInFills = len(pairs)
        self._positions = P

    def _innerDrawLabel(self, rowNo, colNo, x, y):
        "Draw a label for a given item in the list."

        labelFmt = self.lineLabelFormat
        labelValue = self.data[rowNo][colNo]

        if labelFmt is None:
            labelText = None
        elif type(labelFmt) is str:
            if labelFmt == 'values':
                try:
                    labelText = self.lineLabelArray[rowNo][colNo]
                except:
                    labelText = None
            else:
                labelText = labelFmt % labelValue
        elif hasattr(labelFmt,'__call__'):
            labelText = labelFmt(labelValue)
        else:
            raise ValueError("Unknown formatter type %s, expected string or function"%labelFmt)

        if labelText:
            label = self.lineLabels[(rowNo, colNo)]
            if not label.visible: return
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
        P = self._positions
        if self.reversePlotOrder: P.reverse()
        lines = self.lines
        styleCount = len(lines)
        _inFill = self.inFill
        if (_inFill or self._pairInFills or
                [rowNo for rowNo in range(len(P))
                        if getattr(lines[rowNo%styleCount],'inFill',False)]
                ):
            inFillY = self.categoryAxis._y
            inFillX0 = self.valueAxis._x
            inFillX1 = inFillX0 + self.categoryAxis._length
            inFillG = getattr(self,'_inFillG',g)
        yzero = self._yzero

        # Iterate over data rows.
        for rowNo, row in enumerate(reversed(P) if self.reversePlotOrder else P):
            styleIdx = rowNo % styleCount
            rowStyle = lines[styleIdx]
            strokeColor = rowStyle.strokeColor
            fillColor = getattr(rowStyle,'fillColor',strokeColor)
            inFill = getattr(rowStyle,'inFill',_inFill)
            dash = getattr(rowStyle, 'strokeDashArray', None)
            lineStyle = getattr(rowStyle,'lineStyle',None)

            if hasattr(rowStyle, 'strokeWidth'):
                strokeWidth = rowStyle.strokeWidth
            elif hasattr(lines, 'strokeWidth'):
                strokeWidth = lines.strokeWidth
            else:
                strokeWidth = None

            # Iterate over data columns.
            if lineStyle=='bar':
                barWidth = getattr(rowStyle,'barWidth',Percentage(50))
                if isinstance(barWidth,Percentage):
                    hbw = self._hngs*barWidth*0.01
                else:
                    hbw = barWidth*0.5
                for x, y in row:
                    g.add(Rect(x-hbw,min(y,yzero),2*hbw,abs(y-yzero),strokeWidth=strokeWidth,strokeColor=strokeColor,fillColor=fillColor))
            elif self.joinedLines or lineStyle=='joinedLine':
                points = flatten(row)
                if inFill or isinstance(row,FillPairedData):
                    filler = getattr(rowStyle, 'filler', None)
                    if isinstance(row,FillPairedData):
                        fpoints = points + flatten(reversed(P[row.other]))
                    else:
                        fpoints = [inFillX0,inFillY] + points + [inFillX1,inFillY]
                    if filler:
                        filler.fill(self,inFillG,rowNo,fillColor,fpoints)
                    else:
                        inFillG.add(Polygon(fpoints,fillColor=fillColor,strokeColor=strokeColor if strokeColor==fillColor else None,strokeWidth=strokeWidth or 0.1))
                if not inFill or inFill==2 or strokeColor!=fillColor:
                    line = PolyLine(points,strokeColor=strokeColor,strokeLineCap=0,strokeLineJoin=1)
                    if strokeWidth:
                        line.strokeWidth = strokeWidth
                    if dash:
                        line.strokeDashArray = dash
                    g.add(line)

            if hasattr(rowStyle, 'symbol'):
                uSymbol = rowStyle.symbol
            elif hasattr(lines, 'symbol'):
                uSymbol = lines.symbol
            else:
                uSymbol = None

            if uSymbol:
                for colNo,(x,y) in enumerate(row):
                    symbol = uSymbol2Symbol(tpcGetItem(uSymbol,colNo),x,y,rowStyle.strokeColor)
                    if symbol: g.add(symbol)

            # Draw item labels.
            for colNo, (x, y) in enumerate(row):
                self.drawLabel(g, rowNo, colNo, x, y)

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
        cAdgl = getattr(cA,'drawGridLast',False)
        vAdgl = getattr(vA,'drawGridLast',False)
        if not cAdgl: cA.makeGrid(g,parent=self,dim=vA.getGridDims)
        if not vAdgl: vA.makeGrid(g,parent=self,dim=cA.getGridDims)
        g.add(self.makeLines())
        if cAdgl: cA.makeGrid(g,parent=self,dim=vA.getGridDims)
        if vAdgl: vA.makeGrid(g,parent=self,dim=cA.getGridDims)
        for a in getattr(self,'annotations',()): g.add(a(self,cA.scale,vA.scale))
        return g

def _fakeItemKey(a):
    '''t, z0, z1, x, y = a[:5]'''
    return (-a[1],a[3],a[0],-a[4])

class _FakeGroup:
    def __init__(self):
        self._data = []

    def add(self,what):
        if what: self._data.append(what)

    def value(self):
        return self._data

    def sort(self):
        self._data.sort(key=_fakeItemKey)
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
        P = list(range(len(self._positions)))
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
        from reportlab.graphics.charts.utils3d import _make_3d_line_info
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
                    for colNo in range(1,n):
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
                for colNo in range(n):
                    x1, y1 = row[colNo]
                    x1, y1 = _zadjust(x1,y1,z0)
                    symbol = uSymbol2Symbol(uSymbol,x1,y1,rowColor)
                    if symbol: F.add((2,z0,z0,x1,y1,symbol))

            # Draw item labels.
            for colNo in range(n):
                x1, y1 = row[colNo]
                x1, y1 = _zadjust(x1,y1,z0)
                L = self._innerDrawLabel(rowNo, colNo, x1, y1)
                if L: F.add((2,z0,z0,x1,y1,L))

        F.sort()
        g = Group()
        for v in F.value(): g.add(v[-1])
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

    catNames = 'Jan Feb Mar Apr May Jun Jul Aug'.split(' ')
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

    catNames = 'Jan Feb Mar Apr May Jun Jul Aug'.split(' ')
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

    catNames = 'Jan Feb Mar Apr May Jun Jul Aug'.split(' ')
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

    catNames = 'Jan Feb Mar Apr May Jun Jul Aug'.split(' ')
    lc.categoryAxis.categoryNames = catNames
    lc.categoryAxis.labels.boxAnchor = 'n'

    lc.valueAxis.valueMin = 0
    lc.valueAxis.valueMax = 60
    lc.valueAxis.valueStep = 15

    drawing.add(lc)

    return drawing

def sampleCandleStick():
    from reportlab.graphics.widgetbase import CandleSticks
    d = Drawing(400, 200)
    chart = HorizontalLineChart()
    d.add(chart)
    chart.y = 20
    boxMid = (100, 110, 120, 130)
    hi = [m+10 for m in boxMid]
    lo = [m-10 for m in boxMid]
    boxHi = [m+6 for m in boxMid]
    boxLo = [m-4 for m in boxMid]
    boxFillColor = colors.pink
    boxWidth = 20
    crossWidth = 10
    candleStrokeWidth = 0.5
    candleStrokeColor = colors.black
    chart.valueAxis.avoidBoundSpace = 5

    chart.valueAxis.valueMin = min(min(boxMid),min(hi),min(lo),min(boxLo),min(boxHi))
    chart.valueAxis.valueMax = max(max(boxMid),max(hi),max(lo),max(boxLo),max(boxHi))
    lines = chart.lines
    lines[0].strokeColor = None
    I = range(len(boxMid))
    chart.data = [boxMid]
    lines[0].symbol = candles = CandleSticks(chart=chart, boxFillColor=boxFillColor, boxWidth=boxWidth, crossWidth=crossWidth, strokeWidth=candleStrokeWidth, strokeColor=candleStrokeColor)
    for i in I: candles[i].setProperties(dict(position=i,boxMid=boxMid[i],crossLo=lo[i],crossHi=hi[i],boxLo=boxLo[i],boxHi=boxHi[i]))
    return d
