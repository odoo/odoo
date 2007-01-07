#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/graphics/charts/barcharts.py
"""This module defines a variety of Bar Chart components.

The basic flavors are Side-by-side, available in horizontal and
vertical versions.

Stacked and percentile bar charts to follow...
"""
__version__=''' $Id: barcharts.py 2647 2005-07-26 13:47:51Z rgbecker $ '''

import string, copy
from types import FunctionType, StringType

from reportlab.lib import colors
from reportlab.lib.validators import isNumber, isColor, isColorOrNone, isString,\
            isListOfStrings, SequenceOf, isBoolean, isNoneOrShape, isStringOrNone,\
            NoneOr
from reportlab.graphics.widgets.markers import uSymbol2Symbol, isSymbol
from reportlab.lib.formatters import Formatter
from reportlab.lib.attrmap import AttrMap, AttrMapValue
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.graphics.widgetbase import Widget, TypedPropertyCollection, PropHolder
from reportlab.graphics.shapes import Line, Rect, Group, Drawing, NotImplementedError
from reportlab.graphics.charts.axes import XCategoryAxis, YValueAxis, YCategoryAxis, XValueAxis
from reportlab.graphics.charts.textlabels import BarChartLabel, NA_Label, NoneOrInstanceOfNA_Label
from reportlab.graphics.charts.areas import PlotArea

class BarChartProperties(PropHolder):
    _attrMap = AttrMap(
        strokeColor = AttrMapValue(isColorOrNone, desc='Color of the bar border.'),
        fillColor = AttrMapValue(isColorOrNone, desc='Color of the bar interior area.'),
        strokeWidth = AttrMapValue(isNumber, desc='Width of the bar border.'),
        symbol = AttrMapValue(None, desc='A widget to be used instead of a normal bar.'),
        name = AttrMapValue(isString, desc='Text to be associated with a bar (eg seriesname)'),
        swatchMarker = AttrMapValue(NoneOr(isSymbol), desc="None or makeMarker('Diamond') ..."),
        )

    def __init__(self):
        self.strokeColor = None
        self.fillColor = colors.blue
        self.strokeWidth = 0.5
        self.symbol = None

# Bar chart classes.
class BarChart(PlotArea):
    "Abstract base class, unusable by itself."

    _attrMap = AttrMap(BASE=PlotArea,
        useAbsolute = AttrMapValue(isNumber, desc='Flag to use absolute spacing values.'),
        barWidth = AttrMapValue(isNumber, desc='The width of an individual bar.'),
        groupSpacing = AttrMapValue(isNumber, desc='Width between groups of bars.'),
        barSpacing = AttrMapValue(isNumber, desc='Width between individual bars.'),
        bars = AttrMapValue(None, desc='Handle of the individual bars.'),
        valueAxis = AttrMapValue(None, desc='Handle of the value axis.'),
        categoryAxis = AttrMapValue(None, desc='Handle of the category axis.'),
        data = AttrMapValue(None, desc='Data to be plotted, list of (lists of) numbers.'),
        barLabels = AttrMapValue(None, desc='Handle to the list of bar labels.'),
        barLabelFormat = AttrMapValue(None, desc='Formatting string or function used for bar labels.'),
        barLabelCallOut = AttrMapValue(None, desc='Callout function(label)\nlabel._callOutInfo = (self,g,rowNo,colNo,x,y,width,height,x00,y00,x0,y0)'),
        barLabelArray = AttrMapValue(None, desc='explicit array of bar label values, must match size of data if present.'),
        reversePlotOrder = AttrMapValue(isBoolean, desc='If true, reverse common category plot order.'),
        naLabel = AttrMapValue(NoneOrInstanceOfNA_Label, desc='Label to use for N/A values.'),
        annotations = AttrMapValue(None, desc='list of callables, will be called with self, xscale, yscale.'),
        )

    def makeSwatchSample(self, rowNo, x, y, width, height):
        baseStyle = self.bars
        styleIdx = rowNo % len(baseStyle)
        style = baseStyle[styleIdx]
        strokeColor = getattr(style, 'strokeColor', getattr(baseStyle,'strokeColor',None))
        fillColor = getattr(style, 'fillColor', getattr(baseStyle,'fillColor',None))
        strokeDashArray = getattr(style, 'strokeDashArray', getattr(baseStyle,'strokeDashArray',None))
        strokeWidth = getattr(style, 'strokeWidth', getattr(style, 'strokeWidth',None))
        swatchMarker = getattr(style, 'swatchMarker', getattr(baseStyle, 'swatchMarker',None))
        if swatchMarker:
            return uSymbol2Symbol(swatchMarker,x+width/2.,y+height/2.,fillColor)
        return Rect(x,y,width,height,strokeWidth=strokeWidth,strokeColor=strokeColor,
                    strokeDashArray=strokeDashArray,fillColor=fillColor)

    def getSeriesName(self,i,default=None):
        '''return series name i or default'''
        return getattr(self.bars[i],'name',default)

    def __init__(self):
        assert self.__class__.__name__ not in ('BarChart','BarChart3D'), 'Abstract Class %s Instantiated' % self.__class__.__name__

        if self._flipXY:
            self.categoryAxis = YCategoryAxis()
            self.valueAxis = XValueAxis()
        else:
            self.categoryAxis = XCategoryAxis()
            self.valueAxis = YValueAxis()

        PlotArea.__init__(self)
        self.barSpacing = 0
        self.reversePlotOrder = 0


        # this defines two series of 3 points.  Just an example.
        self.data = [(100,110,120,130),
                    (70, 80, 85, 90)]

        # control bar spacing. is useAbsolute = 1 then
        # the next parameters are in points; otherwise
        # they are 'proportions' and are normalized to
        # fit the available space.  Half a barSpacing
        # is allocated at the beginning and end of the
        # chart.
        self.useAbsolute = 0   #- not done yet
        self.barWidth = 10
        self.groupSpacing = 5
        self.barSpacing = 0

        self.barLabels = TypedPropertyCollection(BarChartLabel)
        self.barLabels.boxAnchor = 'c'
        self.barLabels.textAnchor = 'middle'
        self.barLabelFormat = None
        self.barLabelArray = None
        # this says whether the origin is inside or outside
        # the bar - +10 means put the origin ten points
        # above the tip of the bar if value > 0, or ten
        # points inside if bar value < 0.  This is different
        # to label dx/dy which are not dependent on the
        # sign of the data.
        self.barLabels.nudge = 0

        # if you have multiple series, by default they butt
        # together.

        # we really need some well-designed default lists of
        # colors e.g. from Tufte.  These will be used in a
        # cycle to set the fill color of each series.
        self.bars = TypedPropertyCollection(BarChartProperties)
##        self.bars.symbol = None
        self.bars.strokeWidth = 1
        self.bars.strokeColor = colors.black

        self.bars[0].fillColor = colors.red
        self.bars[1].fillColor = colors.green
        self.bars[2].fillColor = colors.blue
        self.naLabel = None#NA_Label()


    def demo(self):
        """Shows basic use of a bar chart"""
        if self.__class__.__name__=='BarChart':
            raise NotImplementedError, 'Abstract Class BarChart has no demo'
        drawing = Drawing(200, 100)
        bc = self.__class__()
        drawing.add(bc)
        return drawing

    def _getConfigureData(self):
        cA = self.categoryAxis
        data = self.data
        if cA.style not in ('parallel','parallel_3d'):
            _data = data
            data = max(map(len,_data))*[0]
            for d in _data:
                for i in xrange(len(d)):
                    data[i] = data[i] + (d[i] or 0)
            data = list(_data) + [data]
        self._configureData = data

    def _getMinMax(self):
        '''Attempt to return the data range'''
        self._getConfigureData()
        self.valueAxis._setRange(self._configureData)
        return self.valueAxis._valueMin, self.valueAxis._valueMax

    def _drawBegin(self,org,length):
        '''Position and configure value axis, return crossing value'''
        vA = self.valueAxis
        vA.setPosition(self.x, self.y, length)
        self._getConfigureData()
        vA.configure(self._configureData)

        # if zero is in chart, put the other axis there, otherwise use low
        crossesAt = vA.scale(0)
        if crossesAt > org+length or crossesAt<org:
            crossesAt = org
        return crossesAt

    def _drawFinish(self):
        '''finalize the drawing of a barchart'''
        cA = self.categoryAxis
        vA = self.valueAxis
        cA.configure(self._configureData)
        self.calcBarPositions()
        g = Group()
        g.add(self.makeBackground())

        # ensure any axes have correct spacing set
        # for grids. It sucks that we have to do
        # this here.
        if self._flipXY == 0:
            vA.gridStart = cA._x
            vA.gridEnd = cA._x+cA._length
            cA.gridStart = vA._y
            cA.gridEnd = vA._y+vA._length
        else:
            cA.gridStart = vA._x
            cA.gridEnd = vA._x+vA._length
            vA.gridStart = cA._y
            vA.gridEnd = cA._y+cA._length

        cA.makeGrid(g,parent=self)
        vA.makeGrid(g,parent=self)
        g.add(self.makeBars())
        g.add(cA)
        g.add(vA)
        for a in getattr(self,'annotations',()): g.add(a(self,cA.scale,vA.scale))
        del self._configureData
        return g


    def calcBarPositions(self):
        """Works out where they go. default vertical.

        Sets an attribute _barPositions which is a list of
        lists of (x, y, width, height) matching the data.
        """

        flipXY = self._flipXY
        if flipXY:
            org = self.y
        else:
            org = self.x
        cA = self.categoryAxis
        cScale = cA.scale

        data = self.data
        seriesCount = self._seriesCount = len(data)
        self._rowLength = rowLength = max(map(len,data))
        groupSpacing, barSpacing, barWidth = self.groupSpacing, self.barSpacing, self.barWidth
        style = self.categoryAxis.style
        if style=='parallel':
            groupWidth = groupSpacing+(seriesCount*barWidth)+(seriesCount-1)*barSpacing
            bGap = barWidth+barSpacing
        else:
            accum = rowLength*[0]
            groupWidth = groupSpacing+barWidth
            bGap = 0
        self._groupWidth = groupWidth
        useAbsolute = self.useAbsolute

        if useAbsolute:
            # bar dimensions are absolute
            normFactor = 1.0
        else:
            # bar dimensions are normalized to fit.  How wide
            # notionally is one group of bars?
            availWidth = cScale(0)[1]
            normFactor = availWidth/float(groupWidth)
            if self.debug:
                print '%d series, %d points per series' % (seriesCount, self._rowLength)
                print 'width = %d group + (%d bars * %d barWidth) + (%d gaps * %d interBar) = %d total' % (
                    groupSpacing, seriesCount, barWidth,
                    seriesCount-1, barSpacing, groupWidth)

        # 'Baseline' correction...
        vA = self.valueAxis
        vScale = vA.scale
        vm, vM = vA._valueMin, vA._valueMax
        if vm <= 0 <= vM:
            baseLine = vScale(0)
        elif 0 < vm:
            baseLine = vScale(vm)
        elif vM < 0:
            baseLine = vScale(vM)
        self._baseLine = baseLine

        COLUMNS = range(max(map(len,data)))
        if useAbsolute:
            _cScale = cA._scale

        self._normFactor = normFactor
        width = self.barWidth*normFactor
        self._barPositions = []
        reversePlotOrder = self.reversePlotOrder
        for rowNo in range(seriesCount):
            barRow = []
            if reversePlotOrder:
                xVal = seriesCount-1 - rowNo
            else:
                xVal = rowNo
            xVal = 0.5*groupSpacing+xVal*bGap
            for colNo in COLUMNS:
                datum = data[rowNo][colNo]

                # Ufff...
                if useAbsolute:
                    x = groupWidth*_cScale(colNo) + xVal + org
                else:
                    (g, gW) = cScale(colNo)
                    x = g + normFactor*xVal

                if datum is None:
                    height = None
                    y = baseLine
                else:
                    if style not in ('parallel','parallel_3d'):
                        y = vScale(accum[colNo])
                        if y<baseLine: y = baseLine
                        accum[colNo] = accum[colNo] + datum
                        datum = accum[colNo]
                    else:
                        y = baseLine
                    height = vScale(datum) - y
                    if -1e-8<height<=1e-8:
                        height = 1e-8
                        if datum<-1e-8: height = -1e-8
                barRow.append(flipXY and (y,x,height,width) or (x, y, width, height))

            self._barPositions.append(barRow)


    def _getLabelText(self, rowNo, colNo):
        '''return formatted label text'''
        labelFmt = self.barLabelFormat
        if labelFmt is None:
            labelText = None
        elif labelFmt == 'values':
            labelText = self.barLabelArray[rowNo][colNo]
        elif type(labelFmt) is StringType:
            labelText = labelFmt % self.data[rowNo][colNo]
        elif callable(labelFmt):
            labelText = labelFmt(self.data[rowNo][colNo])
        else:
            msg = "Unknown formatter type %s, expected string or function" % labelFmt
            raise Exception, msg
        return labelText

    def _labelXY(self,label,x,y,width,height):
        'Compute x, y for a label'
        nudge = label.nudge
        anti = getattr(label,'boxTarget','normal')=='anti'
        if anti: nudge = -nudge
        if self._flipXY:
            value = width
            if anti: value = 0
            return x + value + (width>=0 and 1 or -1)*nudge, y + 0.5*height
        else:
            value = height
            if anti: value = 0
            return x + 0.5*width, y + value + (height>=0 and 1 or -1)*nudge

    def _addBarLabel(self, g, rowNo, colNo, x, y, width, height):
        text = self._getLabelText(rowNo,colNo)
        if text:
            self._addLabel(text, self.barLabels[(rowNo, colNo)], g, rowNo, colNo, x, y, width, height)

    def _addNABarLabel(self, g, rowNo, colNo, x, y, width, height):
        na = self.naLabel
        if na and na.text:
            na = copy.copy(na)
            v = self.valueAxis._valueMax<=0 and -1e-8 or 1e-8
            if width is None: width = v
            if height is None: height = v
            self._addLabel(na.text, na, g, rowNo, colNo, x, y, width, height)

    def _addLabel(self, text, label, g, rowNo, colNo, x, y, width, height):
        if label.visible:
            labelWidth = stringWidth(text, label.fontName, label.fontSize)
            x0, y0 = self._labelXY(label,x,y,width,height)
            flipXY = self._flipXY
            if flipXY:
                pm = width
            else:
                pm = height
            label._pmv = pm #the plus minus val
            fixedEnd = getattr(label,'fixedEnd', None)
            if fixedEnd is not None:
                v = fixedEnd._getValue(self,pm)
                x00, y00 = x0, y0
                if flipXY:
                    x0 = v
                else:
                    y0 = v
            else:
                if flipXY:
                    x00 = x0
                    y00 = y+height/2.0
                else:
                    x00 = x+width/2.0
                    y00 = y0
            fixedStart = getattr(label,'fixedStart', None)
            if fixedStart is not None:
                v = fixedStart._getValue(self,pm)
                if flipXY:
                    x00 = v
                else:
                    y00 = v

            if pm<0:
                if flipXY:
                    dx = -2*label.dx
                    dy = 0
                else:
                    dy = -2*label.dy
                    dx = 0
            else:
                dy = dx = 0
            label.setOrigin(x0+dx, y0+dy)
            label.setText(text)
            sC, sW = label.lineStrokeColor, label.lineStrokeWidth
            if sC and sW: g.insert(0,Line(x00,y00,x0,y0, strokeColor=sC, strokeWidth=sW))
            g.add(label)
            alx = getattr(self,'barLabelCallOut',None)
            if alx:
                label._callOutInfo = (self,g,rowNo,colNo,x,y,width,height,x00,y00,x0,y0)
                alx(label)
                del label._callOutInfo

    def _makeBar(self,g,x,y,width,height,rowNo,style):
        r = Rect(x, y, width, height)
        r.strokeWidth = style.strokeWidth
        r.fillColor = style.fillColor
        r.strokeColor = style.strokeColor
        g.add(r)

    def _makeBars(self,g,lg):
        lenData = len(self.data)
        bars = self.bars
        for rowNo in range(lenData):
            row = self._barPositions[rowNo]
            styleCount = len(bars)
            styleIdx = rowNo % styleCount
            rowStyle = bars[styleIdx]
            for colNo in range(len(row)):
                barPos = row[colNo]
                style = bars.has_key((styleIdx,colNo)) and bars[(styleIdx,colNo)] or rowStyle
                (x, y, width, height) = barPos
                if None in (width,height):
                    self._addNABarLabel(lg,rowNo,colNo,x,y,width,height)
                    continue

                # Draw a rectangular symbol for each data item,
                # or a normal colored rectangle.
                symbol = None
                if hasattr(style, 'symbol'):
                    symbol = copy.deepcopy(style.symbol)
                elif hasattr(self.bars, 'symbol'):
                    symbol = self.bars.symbol

                if symbol:
                    symbol.x = x
                    symbol.y = y
                    symbol.width = width
                    symbol.height = height
                    g.add(symbol)
                elif abs(width)>1e-7 and abs(height)>=1e-7 and (style.fillColor is not None or style.strokeColor is not None):
                    self._makeBar(g,x,y,width,height,rowNo,style)

                self._addBarLabel(lg,rowNo,colNo,x,y,width,height)

    def makeBars(self):
        g = Group()
        lg = Group()
        self._makeBars(g,lg)
        g.add(lg)
        return g

    def _desiredCategoryAxisLength(self):
        '''for dynamically computing the desired category axis length'''
        style = self.categoryAxis.style
        data = self.data
        n = len(data)
        m = max(map(len,data))
        if style=='parallel':
            groupWidth = (n-1)*self.barSpacing+n*self.barWidth
        else:
            groupWidth = self.barWidth
        return m*(self.groupSpacing+groupWidth)

    def draw(self):
        cA, vA = self.categoryAxis, self.valueAxis
        if vA: ovAjA, vA.joinAxis = vA.joinAxis, cA
        if cA: ocAjA, cA.joinAxis = cA.joinAxis, vA
        if self._flipXY:
            cA.setPosition(self._drawBegin(self.x,self.width), self.y, self.height)
        else:
            cA.setPosition(self.x, self._drawBegin(self.y,self.height), self.width)
        return self._drawFinish()

class VerticalBarChart(BarChart):
    "Vertical bar chart with multiple side-by-side bars."
    _flipXY = 0

class HorizontalBarChart(BarChart):
    "Horizontal bar chart with multiple side-by-side bars."
    _flipXY = 1

class _FakeGroup:
    def __init__(self, cmp=None):
        self._data = []
        self._cmp = cmp

    def add(self,what):
        self._data.append(what)

    def value(self):
        return self._data

    def sort(self):
        self._data.sort(self._cmp)

class BarChart3D(BarChart):
    _attrMap = AttrMap(BASE=BarChart,
        theta_x = AttrMapValue(isNumber, desc='dx/dz'),
        theta_y = AttrMapValue(isNumber, desc='dy/dz'),
        zDepth = AttrMapValue(isNumber, desc='depth of an individual series'),
        zSpace = AttrMapValue(isNumber, desc='z gap around series'),
        )
    theta_x = .5
    theta_y = .5
    zDepth = None
    zSpace = None

    def calcBarPositions(self):
        BarChart.calcBarPositions(self)
        seriesCount = self._seriesCount
        zDepth = self.zDepth
        if zDepth is None: zDepth = self.barWidth
        zSpace = self.zSpace
        if zSpace is None: zSpace = self.barSpacing
        if self.categoryAxis.style=='parallel_3d':
            _3d_depth = seriesCount*zDepth+(seriesCount+1)*zSpace
        else:
            _3d_depth = zDepth + 2*zSpace
        _3d_depth *= self._normFactor
        self._3d_dx = self.theta_x*_3d_depth
        self._3d_dy = self.theta_y*_3d_depth

    def _calc_z0(self,rowNo):
        zDepth = self.zDepth
        if zDepth is None: zDepth = self.barWidth
        zSpace = self.zSpace
        if zSpace is None: zSpace = self.barSpacing
        if self.categoryAxis.style=='parallel_3d':
            z0 = self._normFactor*(rowNo*(zDepth+zSpace)+zSpace)
        else:
            z0 = self._normFactor*zSpace
        return z0

    def _makeBar(self,g,x,y,width,height,rowNo,style):
        zDepth = self.zDepth
        if zDepth is None: zDepth = self.barWidth
        zSpace = self.zSpace
        if zSpace is None: zSpace = self.barSpacing
        z0 = self._calc_z0(rowNo)
        z1 = z0 + zDepth*self._normFactor
        if width<0:
            x += width
            width = -width
        x += z0*self.theta_x
        y += z0*self.theta_y
        if self._flipXY:
            y += zSpace
        else:
            x += zSpace
        g.add((0,z0,z1,x,y,width,height,rowNo,style))

    def _addBarLabel(self, g, rowNo, colNo, x, y, width, height):
        z0 = self._calc_z0(rowNo)
        zSpace = self.zSpace
        if zSpace is None: zSpace = self.barSpacing
        z1 = z0
        x += z0*self.theta_x
        y += z0*self.theta_y
        if self._flipXY:
            y += zSpace
        else:
            x += zSpace
        g.add((1,z0,z1,x,y,width,height,rowNo,colNo))

    def makeBars(self):
        from utils3d import _draw_3d_bar
        fg = _FakeGroup(cmp=self._cmpZ)
        self._makeBars(fg,fg)
        fg.sort()
        g = Group()
        theta_x = self.theta_x
        theta_y = self.theta_y
        for t in fg.value():
            if t[0]==1:
                z0,z1,x,y,width,height,rowNo,colNo = t[1:]
                BarChart._addBarLabel(self,g,rowNo,colNo,x,y,width,height)
            elif t[0]==0:
                z0,z1,x,y,width,height,rowNo,style = t[1:]
                dz = z1 - z0
                _draw_3d_bar(g, x, x+width, y, y+height, dz*theta_x, dz*theta_y,
                            fillColor=style.fillColor, fillColorShaded=None,
                            strokeColor=style.strokeColor, strokeWidth=style.strokeWidth,
                            shading=0.45)
        return g

class VerticalBarChart3D(BarChart3D,VerticalBarChart):
    _cmpZ=lambda self,a,b:cmp((-a[1],a[3],a[0],-a[4]),(-b[1],b[3],b[0],-b[4]))

class HorizontalBarChart3D(BarChart3D,HorizontalBarChart):
    _cmpZ = lambda self,a,b: cmp((-a[1],a[4],a[0],-a[3]),(-b[1],b[4],b[0],-b[3]))   #t, z0, z1, x, y = a[:5]

# Vertical samples.
def sampleV0a():
    "A slightly pathologic bar chart with only TWO data items."

    drawing = Drawing(400, 200)

    data = [(13, 20)]

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data

    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'ne'
    bc.categoryAxis.labels.dx = 8
    bc.categoryAxis.labels.dy = -2
    bc.categoryAxis.labels.angle = 30
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleV0b():
    "A pathologic bar chart with only ONE data item."

    drawing = Drawing(400, 200)

    data = [(42,)]

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 50
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'ne'
    bc.categoryAxis.labels.dx = 8
    bc.categoryAxis.labels.dy = -2
    bc.categoryAxis.labels.angle = 30
    bc.categoryAxis.categoryNames = ['Jan-99']

    drawing.add(bc)

    return drawing


def sampleV0c():
    "A really pathologic bar chart with NO data items at all!"

    drawing = Drawing(400, 200)

    data = [()]

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'ne'
    bc.categoryAxis.labels.dx = 8
    bc.categoryAxis.labels.dy = -2
    bc.categoryAxis.categoryNames = []

    drawing.add(bc)

    return drawing


def sampleV1():
    "Sample of multi-series bar chart."

    drawing = Drawing(400, 200)

    data = [
            (13, 5, 20, 22, 37, 45, 19, 4),
            (14, 6, 21, 23, 38, 46, 20, 5)
            ]

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'ne'
    bc.categoryAxis.labels.dx = 8
    bc.categoryAxis.labels.dy = -2
    bc.categoryAxis.labels.angle = 30

    catNames = string.split('Jan Feb Mar Apr May Jun Jul Aug', ' ')
    catNames = map(lambda n:n+'-99', catNames)
    bc.categoryAxis.categoryNames = catNames
    drawing.add(bc)

    return drawing


def sampleV2a():
    "Sample of multi-series bar chart."

    data = [(2.4, -5.7, 2, 5, 9.2),
            (0.6, -4.9, -3, 4, 6.8)
            ]

    labels = ("Q3 2000", "Year to Date", "12 months",
              "Annualised\n3 years", "Since 07.10.99")

    drawing = Drawing(400, 200)

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 120
    bc.width = 300
    bc.data = data

    bc.barSpacing = 0
    bc.groupSpacing = 10
    bc.barWidth = 10

    bc.valueAxis.valueMin = -15
    bc.valueAxis.valueMax = +15
    bc.valueAxis.valueStep = 5
    bc.valueAxis.labels.fontName = 'Helvetica'
    bc.valueAxis.labels.fontSize = 8
    bc.valueAxis.labels.boxAnchor = 'n'   # irrelevant (becomes 'c')
    bc.valueAxis.labels.textAnchor = 'middle'

    bc.categoryAxis.categoryNames = labels
    bc.categoryAxis.labels.fontName = 'Helvetica'
    bc.categoryAxis.labels.fontSize = 8
    bc.categoryAxis.labels.dy = -60

    drawing.add(bc)

    return drawing


def sampleV2b():
    "Sample of multi-series bar chart."

    data = [(2.4, -5.7, 2, 5, 9.2),
            (0.6, -4.9, -3, 4, 6.8)
            ]

    labels = ("Q3 2000", "Year to Date", "12 months",
              "Annualised\n3 years", "Since 07.10.99")

    drawing = Drawing(400, 200)

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 120
    bc.width = 300
    bc.data = data

    bc.barSpacing = 5
    bc.groupSpacing = 10
    bc.barWidth = 10

    bc.valueAxis.valueMin = -15
    bc.valueAxis.valueMax = +15
    bc.valueAxis.valueStep = 5
    bc.valueAxis.labels.fontName = 'Helvetica'
    bc.valueAxis.labels.fontSize = 8
    bc.valueAxis.labels.boxAnchor = 'n'   # irrelevant (becomes 'c')
    bc.valueAxis.labels.textAnchor = 'middle'

    bc.categoryAxis.categoryNames = labels
    bc.categoryAxis.labels.fontName = 'Helvetica'
    bc.categoryAxis.labels.fontSize = 8
    bc.categoryAxis.labels.dy = -60

    drawing.add(bc)

    return drawing


def sampleV2c():
    "Sample of multi-series bar chart."

    data = [(2.4, -5.7, 2, 5, 9.99),
            (0.6, -4.9, -3, 4, 9.99)
            ]

    labels = ("Q3 2000", "Year to Date", "12 months",
              "Annualised\n3 years", "Since 07.10.99")

    drawing = Drawing(400, 200)

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 120
    bc.width = 300
    bc.data = data

    bc.barSpacing = 2
    bc.groupSpacing = 10
    bc.barWidth = 10

    bc.valueAxis.valueMin = -15
    bc.valueAxis.valueMax = +15
    bc.valueAxis.valueStep = 5
    bc.valueAxis.labels.fontName = 'Helvetica'
    bc.valueAxis.labels.fontSize = 8

    bc.categoryAxis.categoryNames = labels
    bc.categoryAxis.labels.fontName = 'Helvetica'
    bc.categoryAxis.labels.fontSize = 8
    bc.valueAxis.labels.boxAnchor = 'n'
    bc.valueAxis.labels.textAnchor = 'middle'
    bc.categoryAxis.labels.dy = -60

    bc.barLabels.nudge = 10

    bc.barLabelFormat = '%0.2f'
    bc.barLabels.dx = 0
    bc.barLabels.dy = 0
    bc.barLabels.boxAnchor = 'n'  # irrelevant (becomes 'c')
    bc.barLabels.fontName = 'Helvetica'
    bc.barLabels.fontSize = 6

    drawing.add(bc)

    return drawing


def sampleV3():
    "Faked horizontal bar chart using a vertical real one (deprecated)."

    names = ("UK Equities", "US Equities", "European Equities", "Japanese Equities",
              "Pacific (ex Japan) Equities", "Emerging Markets Equities",
              "UK Bonds", "Overseas Bonds", "UK Index-Linked", "Cash")

    series1 = (-1.5, 0.3, 0.5, 1.0, 0.8, 0.7, 0.4, 0.1, 1.0, 0.3)
    series2 = (0.0, 0.33, 0.55, 1.1, 0.88, 0.77, 0.44, 0.11, 1.10, 0.33)

    assert len(names) == len(series1), "bad data"
    assert len(names) == len(series2), "bad data"

    drawing = Drawing(400, 200)

    bc = VerticalBarChart()
    bc.x = 0
    bc.y = 0
    bc.height = 100
    bc.width = 150
    bc.data = (series1,)
    bc.bars.fillColor = colors.green

    bc.barLabelFormat = '%0.2f'
    bc.barLabels.dx = 0
    bc.barLabels.dy = 0
    bc.barLabels.boxAnchor = 'w' # irrelevant (becomes 'c')
    bc.barLabels.angle = 90
    bc.barLabels.fontName = 'Helvetica'
    bc.barLabels.fontSize = 6
    bc.barLabels.nudge = 10

    bc.valueAxis.visible = 0
    bc.valueAxis.valueMin = -2
    bc.valueAxis.valueMax = +2
    bc.valueAxis.valueStep = 1

    bc.categoryAxis.tickUp = 0
    bc.categoryAxis.tickDown = 0
    bc.categoryAxis.categoryNames = names
    bc.categoryAxis.labels.angle = 90
    bc.categoryAxis.labels.boxAnchor = 'w'
    bc.categoryAxis.labels.dx = 0
    bc.categoryAxis.labels.dy = -125
    bc.categoryAxis.labels.fontName = 'Helvetica'
    bc.categoryAxis.labels.fontSize = 6

    g = Group(bc)
    g.translate(100, 175)
    g.rotate(-90)

    drawing.add(g)

    return drawing


def sampleV4a():
    "A bar chart showing value axis region starting at *exactly* zero."

    drawing = Drawing(400, 200)

    data = [(13, 20)]

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data

    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'n'
    bc.categoryAxis.labels.dy = -5
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleV4b():
    "A bar chart showing value axis region starting *below* zero."

    drawing = Drawing(400, 200)

    data = [(13, 20)]

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data

    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = -10
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'n'
    bc.categoryAxis.labels.dy = -5
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleV4c():
    "A bar chart showing value axis region staring *above* zero."

    drawing = Drawing(400, 200)

    data = [(13, 20)]

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data

    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 10
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'n'
    bc.categoryAxis.labels.dy = -5
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleV4d():
    "A bar chart showing value axis region entirely *below* zero."

    drawing = Drawing(400, 200)

    data = [(-13, -20)]

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data

    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = -30
    bc.valueAxis.valueMax = -10
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'n'
    bc.categoryAxis.labels.dy = -5
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


###

##dataSample5 = [(10, 20), (20, 30), (30, 40), (40, 50), (50, 60)]
##dataSample5 = [(10, 60), (20, 50), (30, 40), (40, 30), (50, 20)]
dataSample5 = [(10, 60), (20, 50), (30, 40), (40, 30)]

def sampleV5a():
    "A simple bar chart with no expressed spacing attributes."

    drawing = Drawing(400, 200)

    data = dataSample5

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'n'
    bc.categoryAxis.labels.dy = -5
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleV5b():
    "A simple bar chart with proportional spacing."

    drawing = Drawing(400, 200)

    data = dataSample5

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.useAbsolute = 0
    bc.barWidth = 40
    bc.groupSpacing = 20
    bc.barSpacing = 10

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'n'
    bc.categoryAxis.labels.dy = -5
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleV5c1():
    "Make sampe simple bar chart but with absolute spacing."

    drawing = Drawing(400, 200)

    data = dataSample5

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.useAbsolute = 1
    bc.barWidth = 40
    bc.groupSpacing = 0
    bc.barSpacing = 0

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'n'
    bc.categoryAxis.labels.dy = -5
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleV5c2():
    "Make sampe simple bar chart but with absolute spacing."

    drawing = Drawing(400, 200)

    data = dataSample5

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.useAbsolute = 1
    bc.barWidth = 40
    bc.groupSpacing = 20
    bc.barSpacing = 0

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'n'
    bc.categoryAxis.labels.dy = -5
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleV5c3():
    "Make sampe simple bar chart but with absolute spacing."

    drawing = Drawing(400, 200)

    data = dataSample5

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.useAbsolute = 1
    bc.barWidth = 40
    bc.groupSpacing = 0
    bc.barSpacing = 10

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'n'
    bc.categoryAxis.labels.dy = -5
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleV5c4():
    "Make sampe simple bar chart but with absolute spacing."

    drawing = Drawing(400, 200)

    data = dataSample5

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.useAbsolute = 1
    bc.barWidth = 40
    bc.groupSpacing = 20
    bc.barSpacing = 10

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'n'
    bc.categoryAxis.labels.dy = -5
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


# Horizontal samples

def sampleH0a():
    "Make a slightly pathologic bar chart with only TWO data items."

    drawing = Drawing(400, 200)

    data = [(13, 20)]

    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data

    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'se'
    bc.categoryAxis.labels.angle = 30
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleH0b():
    "Make a pathologic bar chart with only ONE data item."

    drawing = Drawing(400, 200)

    data = [(42,)]

    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 50
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'se'
    bc.categoryAxis.labels.angle = 30
    bc.categoryAxis.categoryNames = ['Jan-99']

    drawing.add(bc)

    return drawing


def sampleH0c():
    "Make a really pathologic bar chart with NO data items at all!"

    drawing = Drawing(400, 200)

    data = [()]

    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'se'
    bc.categoryAxis.labels.angle = 30
    bc.categoryAxis.categoryNames = []

    drawing.add(bc)

    return drawing


def sampleH1():
    "Sample of multi-series bar chart."

    drawing = Drawing(400, 200)

    data = [
            (13, 5, 20, 22, 37, 45, 19, 4),
            (14, 6, 21, 23, 38, 46, 20, 5)
            ]

    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'e'
    catNames = string.split('Jan Feb Mar Apr May Jun Jul Aug', ' ')
    catNames = map(lambda n:n+'-99', catNames)
    bc.categoryAxis.categoryNames = catNames
    drawing.add(bc, 'barchart')

    return drawing


def sampleH2a():
    "Sample of multi-series bar chart."

    data = [(2.4, -5.7, 2, 5, 9.2),
            (0.6, -4.9, -3, 4, 6.8)
            ]

    labels = ("Q3 2000", "Year to Date", "12 months",
              "Annualised\n3 years", "Since 07.10.99")

    drawing = Drawing(400, 200)

    bc = HorizontalBarChart()
    bc.x = 80
    bc.y = 50
    bc.height = 120
    bc.width = 300
    bc.data = data

    bc.barSpacing = 0
    bc.groupSpacing = 10
    bc.barWidth = 10

    bc.valueAxis.valueMin = -15
    bc.valueAxis.valueMax = +15
    bc.valueAxis.valueStep = 5
    bc.valueAxis.labels.fontName = 'Helvetica'
    bc.valueAxis.labels.fontSize = 8
    bc.valueAxis.labels.boxAnchor = 'n'   # irrelevant (becomes 'c')
    bc.valueAxis.labels.textAnchor = 'middle'
    bc.valueAxis.configure(bc.data)

    bc.categoryAxis.categoryNames = labels
    bc.categoryAxis.labels.fontName = 'Helvetica'
    bc.categoryAxis.labels.fontSize = 8
    bc.categoryAxis.labels.dx = -150

    drawing.add(bc)

    return drawing


def sampleH2b():
    "Sample of multi-series bar chart."

    data = [(2.4, -5.7, 2, 5, 9.2),
            (0.6, -4.9, -3, 4, 6.8)
            ]

    labels = ("Q3 2000", "Year to Date", "12 months",
              "Annualised\n3 years", "Since 07.10.99")

    drawing = Drawing(400, 200)

    bc = HorizontalBarChart()
    bc.x = 80
    bc.y = 50
    bc.height = 120
    bc.width = 300
    bc.data = data

    bc.barSpacing = 5
    bc.groupSpacing = 10
    bc.barWidth = 10

    bc.valueAxis.valueMin = -15
    bc.valueAxis.valueMax = +15
    bc.valueAxis.valueStep = 5
    bc.valueAxis.labels.fontName = 'Helvetica'
    bc.valueAxis.labels.fontSize = 8
    bc.valueAxis.labels.boxAnchor = 'n'   # irrelevant (becomes 'c')
    bc.valueAxis.labels.textAnchor = 'middle'

    bc.categoryAxis.categoryNames = labels
    bc.categoryAxis.labels.fontName = 'Helvetica'
    bc.categoryAxis.labels.fontSize = 8
    bc.categoryAxis.labels.dx = -150

    drawing.add(bc)

    return drawing


def sampleH2c():
    "Sample of multi-series bar chart."

    data = [(2.4, -5.7, 2, 5, 9.99),
            (0.6, -4.9, -3, 4, 9.99)
            ]

    labels = ("Q3 2000", "Year to Date", "12 months",
              "Annualised\n3 years", "Since 07.10.99")

    drawing = Drawing(400, 200)

    bc = HorizontalBarChart()
    bc.x = 80
    bc.y = 50
    bc.height = 120
    bc.width = 300
    bc.data = data

    bc.barSpacing = 2
    bc.groupSpacing = 10
    bc.barWidth = 10

    bc.valueAxis.valueMin = -15
    bc.valueAxis.valueMax = +15
    bc.valueAxis.valueStep = 5
    bc.valueAxis.labels.fontName = 'Helvetica'
    bc.valueAxis.labels.fontSize = 8
    bc.valueAxis.labels.boxAnchor = 'n'
    bc.valueAxis.labels.textAnchor = 'middle'

    bc.categoryAxis.categoryNames = labels
    bc.categoryAxis.labels.fontName = 'Helvetica'
    bc.categoryAxis.labels.fontSize = 8
    bc.categoryAxis.labels.dx = -150

    bc.barLabels.nudge = 10

    bc.barLabelFormat = '%0.2f'
    bc.barLabels.dx = 0
    bc.barLabels.dy = 0
    bc.barLabels.boxAnchor = 'n'  # irrelevant (becomes 'c')
    bc.barLabels.fontName = 'Helvetica'
    bc.barLabels.fontSize = 6

    drawing.add(bc)

    return drawing


def sampleH3():
    "A really horizontal bar chart (compared to the equivalent faked one)."

    names = ("UK Equities", "US Equities", "European Equities", "Japanese Equities",
              "Pacific (ex Japan) Equities", "Emerging Markets Equities",
              "UK Bonds", "Overseas Bonds", "UK Index-Linked", "Cash")

    series1 = (-1.5, 0.3, 0.5, 1.0, 0.8, 0.7, 0.4, 0.1, 1.0, 0.3)
    series2 = (0.0, 0.33, 0.55, 1.1, 0.88, 0.77, 0.44, 0.11, 1.10, 0.33)

    assert len(names) == len(series1), "bad data"
    assert len(names) == len(series2), "bad data"

    drawing = Drawing(400, 200)

    bc = HorizontalBarChart()
    bc.x = 100
    bc.y = 20
    bc.height = 150
    bc.width = 250
    bc.data = (series1,)
    bc.bars.fillColor = colors.green

    bc.barLabelFormat = '%0.2f'
    bc.barLabels.dx = 0
    bc.barLabels.dy = 0
    bc.barLabels.boxAnchor = 'w' # irrelevant (becomes 'c')
    bc.barLabels.fontName = 'Helvetica'
    bc.barLabels.fontSize = 6
    bc.barLabels.nudge = 10

    bc.valueAxis.visible = 0
    bc.valueAxis.valueMin = -2
    bc.valueAxis.valueMax = +2
    bc.valueAxis.valueStep = 1

    bc.categoryAxis.tickLeft = 0
    bc.categoryAxis.tickRight = 0
    bc.categoryAxis.categoryNames = names
    bc.categoryAxis.labels.boxAnchor = 'w'
    bc.categoryAxis.labels.dx = -170
    bc.categoryAxis.labels.fontName = 'Helvetica'
    bc.categoryAxis.labels.fontSize = 6

    g = Group(bc)
    drawing.add(g)

    return drawing


def sampleH4a():
    "A bar chart showing value axis region starting at *exactly* zero."

    drawing = Drawing(400, 200)

    data = [(13, 20)]

    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data

    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleH4b():
    "A bar chart showing value axis region starting *below* zero."

    drawing = Drawing(400, 200)

    data = [(13, 20)]

    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data

    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = -10
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleH4c():
    "A bar chart showing value axis region starting *above* zero."

    drawing = Drawing(400, 200)

    data = [(13, 20)]

    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data

    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 10
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleH4d():
    "A bar chart showing value axis region entirely *below* zero."

    drawing = Drawing(400, 200)

    data = [(-13, -20)]

    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data

    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = -30
    bc.valueAxis.valueMax = -10
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


dataSample5 = [(10, 60), (20, 50), (30, 40), (40, 30)]

def sampleH5a():
    "A simple bar chart with no expressed spacing attributes."

    drawing = Drawing(400, 200)

    data = dataSample5

    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleH5b():
    "A simple bar chart with proportional spacing."

    drawing = Drawing(400, 200)

    data = dataSample5

    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.useAbsolute = 0
    bc.barWidth = 40
    bc.groupSpacing = 20
    bc.barSpacing = 10

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleH5c1():
    "A simple bar chart with absolute spacing."

    drawing = Drawing(400, 200)

    data = dataSample5

    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.useAbsolute = 1
    bc.barWidth = 10
    bc.groupSpacing = 0
    bc.barSpacing = 0

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleH5c2():
    "Simple bar chart with absolute spacing."

    drawing = Drawing(400, 200)

    data = dataSample5

    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.useAbsolute = 1
    bc.barWidth = 10
    bc.groupSpacing = 20
    bc.barSpacing = 0

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleH5c3():
    "Simple bar chart with absolute spacing."

    drawing = Drawing(400, 200)

    data = dataSample5

    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 20
    bc.height = 155
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.useAbsolute = 1
    bc.barWidth = 10
    bc.groupSpacing = 0
    bc.barSpacing = 2

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleH5c4():
    "Simple bar chart with absolute spacing."

    drawing = Drawing(400, 200)

    data = dataSample5

    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.useAbsolute = 1
    bc.barWidth = 10
    bc.groupSpacing = 20
    bc.barSpacing = 10

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing

def sampleSymbol1():
    "Simple bar chart using symbol attribute."

    drawing = Drawing(400, 200)

    data = dataSample5

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.barWidth = 10
    bc.groupSpacing = 15
    bc.barSpacing = 3

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    from reportlab.graphics.widgets.grids import ShadedRect
    sym1 = ShadedRect()
    sym1.fillColorStart = colors.black
    sym1.fillColorEnd = colors.blue
    sym1.orientation = 'horizontal'
    sym1.strokeWidth = 0

    sym2 = ShadedRect()
    sym2.fillColorStart = colors.black
    sym2.fillColorEnd = colors.pink
    sym2.orientation = 'horizontal'
    sym2.strokeWidth = 0

    sym3 = ShadedRect()
    sym3.fillColorStart = colors.blue
    sym3.fillColorEnd = colors.white
    sym3.orientation = 'vertical'
    sym3.cylinderMode = 1
    sym3.strokeWidth = 0

    bc.bars.symbol = sym1
    bc.bars[2].symbol = sym2
    bc.bars[3].symbol = sym3

    drawing.add(bc)

    return drawing

def sampleStacked1():
    "Simple bar chart using symbol attribute."

    drawing = Drawing(400, 200)

    data = dataSample5

    bc = VerticalBarChart()
    bc.categoryAxis.style = 'stacked'
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.barWidth = 10
    bc.groupSpacing = 15
    bc.valueAxis.valueMin = 0

    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    from reportlab.graphics.widgets.grids import ShadedRect
    bc.bars.symbol = ShadedRect()
    bc.bars.symbol.fillColorStart = colors.red
    bc.bars.symbol.fillColorEnd = colors.white
    bc.bars.symbol.orientation = 'vertical'
    bc.bars.symbol.cylinderMode = 1
    bc.bars.symbol.strokeWidth = 0

    bc.bars[1].symbol = ShadedRect()
    bc.bars[1].symbol.fillColorStart = colors.magenta
    bc.bars[1].symbol.fillColorEnd = colors.white
    bc.bars[1].symbol.orientation = 'vertical'
    bc.bars[1].symbol.cylinderMode = 1
    bc.bars[1].symbol.strokeWidth = 0

    bc.bars[2].symbol = ShadedRect()
    bc.bars[2].symbol.fillColorStart = colors.green
    bc.bars[2].symbol.fillColorEnd = colors.white
    bc.bars[2].symbol.orientation = 'vertical'
    bc.bars[2].symbol.cylinderMode = 1
    bc.bars[2].symbol.strokeWidth = 0

    bc.bars[3].symbol = ShadedRect()
    bc.bars[3].symbol.fillColorStart = colors.blue
    bc.bars[3].symbol.fillColorEnd = colors.white
    bc.bars[3].symbol.orientation = 'vertical'
    bc.bars[3].symbol.cylinderMode = 1
    bc.bars[3].symbol.strokeWidth = 0

    drawing.add(bc)

    return drawing

#class version of function sampleH5c4 above
class SampleH5c4(Drawing):
    "Simple bar chart with absolute spacing."

    def __init__(self,width=400,height=200,*args,**kw):
        apply(Drawing.__init__,(self,width,height)+args,kw)
        bc = HorizontalBarChart()
        bc.x = 50
        bc.y = 50
        bc.height = 125
        bc.width = 300
        bc.data = dataSample5
        bc.strokeColor = colors.black

        bc.useAbsolute = 1
        bc.barWidth = 10
        bc.groupSpacing = 20
        bc.barSpacing = 10

        bc.valueAxis.valueMin = 0
        bc.valueAxis.valueMax = 60
        bc.valueAxis.valueStep = 15

        bc.categoryAxis.labels.boxAnchor = 'e'
        bc.categoryAxis.categoryNames = ['Ying', 'Yang']

        self.add(bc,name='HBC')
