#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/graphics/charts/lineplots.py

__version__='3.3.0'
__doc__="""This module defines a very preliminary Line Plot example."""

from reportlab.lib import colors
from reportlab.lib.validators import *
from reportlab.lib.attrmap import *
from reportlab.lib.utils import flatten, isStr
from reportlab.graphics.shapes import Drawing, Group, Rect, PolyLine, Polygon, _SetKeyWordArgs
from reportlab.graphics.widgetbase import TypedPropertyCollection, PropHolder, tpcGetItem
from reportlab.graphics.charts.textlabels import Label
from reportlab.graphics.charts.axes import XValueAxis, YValueAxis, AdjYValueAxis, NormalDateXValueAxis
from reportlab.graphics.charts.utils import *
from reportlab.graphics.widgets.markers import uSymbol2Symbol, makeMarker
from reportlab.graphics.widgets.grids import Grid, DoubleGrid, ShadedPolygon
from reportlab.pdfbase.pdfmetrics import stringWidth, getFont
from reportlab.graphics.charts.areas import PlotArea
from .utils import FillPairedData

# This might be moved again from here...
class LinePlotProperties(PropHolder):
    _attrMap = AttrMap(
        strokeWidth = AttrMapValue(isNumber, desc='Width of a line.'),
        strokeColor = AttrMapValue(isColorOrNone, desc='Color of a line.'),
        strokeDashArray = AttrMapValue(isListOfNumbersOrNone, desc='Dash array of a line.'),
        fillColor = AttrMapValue(isColorOrNone, desc='Color of infill defaults to the strokeColor.'),
        symbol = AttrMapValue(None, desc='Widget placed at data points.',advancedUsage=1),
        shader = AttrMapValue(None, desc='Shader Class.',advancedUsage=1),
        filler = AttrMapValue(None, desc='Filler Class.',advancedUsage=1),
        name = AttrMapValue(isStringOrNone, desc='Name of the line.'),
        lineStyle = AttrMapValue(NoneOr(OneOf('line','joinedLine','bar')), desc="What kind of plot this line is",advancedUsage=1),
        barWidth = AttrMapValue(isNumberOrNone,desc="Percentage of available width to be used for a bar",advancedUsage=1),
        inFill = AttrMapValue(isBoolean, desc='If true flood fill to x axis',advancedUsage=1),
        )

class InFillValue(int):
    def __new__(cls,v,yValue=None):
        self = int.__new__(cls,v)
        self.yValue = yValue
        return self

class Shader(_SetKeyWordArgs):
    _attrMap = AttrMap(BASE=PlotArea,
        vertical = AttrMapValue(isBoolean, desc='If true shade to x axis'),
        colors = AttrMapValue(SequenceOf(isColorOrNone,lo=2,hi=2), desc='(AxisColor, LineColor)'),
        )

    def shade(self, lp, g, rowNo, rowColor, row):
        c = [None,None]
        c = getattr(self,'colors',c) or c
        if not c[0]: c[0] = getattr(lp,'fillColor',colors.white)
        if not c[1]: c[1] = rowColor

class NoFiller:
    def fill(self, lp, g, rowNo, rowColor, points):
        pass

class Filler:
    '''mixin providing simple polygon fill'''
    _attrMap = AttrMap(
        fillColor = AttrMapValue(isColorOrNone, desc='filler interior color'),
        strokeColor = AttrMapValue(isColorOrNone, desc='filler edge color'),
        strokeWidth = AttrMapValue(isNumberOrNone, desc='filler edge width'),
        )
    def __init__(self,**kw):
        self.__dict__ = kw

    def fill(self, lp, g, rowNo, rowColor, points):
        g.add(Polygon(points,
            fillColor=getattr(self,'fillColor',rowColor),
            strokeColor=getattr(self,'strokeColor',rowColor),
            strokeWidth=getattr(self,'strokeWidth',0.1)))

class ShadedPolyFiller(Filler,ShadedPolygon):
    pass

class PolyFiller(Filler,Polygon):
    pass

from reportlab.graphics.charts.linecharts import AbstractLineChart
class LinePlot(AbstractLineChart):
    """Line plot with multiple lines.

    Both x- and y-axis are value axis (so there are no seperate
    X and Y versions of this class).
    """
    _attrMap = AttrMap(BASE=PlotArea,
        reversePlotOrder = AttrMapValue(isBoolean, desc='If true reverse plot order.',advancedUsage=1),
        lineLabelNudge = AttrMapValue(isNumber, desc='Distance between a data point and its label.',advancedUsage=1),
        lineLabels = AttrMapValue(None, desc='Handle to the list of data point labels.'),
        lineLabelFormat = AttrMapValue(None, desc='Formatting string or function used for data point labels.'),
        lineLabelArray = AttrMapValue(None, desc='explicit array of line label values, must match size of data if present.'),
        #joinedLines = AttrMapValue(isNumber, desc='Display data points joined with lines if true.'),
        strokeColor = AttrMapValue(isColorOrNone, desc='Color used for background border of plot area.'),
        fillColor = AttrMapValue(isColorOrNone, desc='Color used for background interior of plot area.'),
        lines = AttrMapValue(None, desc='Handle of the lines.'),
        xValueAxis = AttrMapValue(None, desc='Handle of the x axis.'),
        yValueAxis = AttrMapValue(None, desc='Handle of the y axis.'),
        data = AttrMapValue(None, desc='Data to be plotted, list of (lists of) x/y tuples.'),
        annotations = AttrMapValue(None, desc='list of callables, will be called with self, xscale, yscale.',advancedUsage=1),
        behindAxes = AttrMapValue(isBoolean, desc='If true use separate line group.',advancedUsage=1),
        gridFirst = AttrMapValue(isBoolean, desc='If true use draw grids before axes.',advancedUsage=1),
        )

    def __init__(self):
        PlotArea.__init__(self)
        self.reversePlotOrder = 0

        self.xValueAxis = XValueAxis()
        self.yValueAxis = YValueAxis()

        # this defines two series of 3 points.  Just an example.
        self.data = [
            ((1,1), (2,2), (2.5,1), (3,3), (4,5)),
            ((1,2), (2,3), (2.5,2), (3,4), (4,6))
            ]

        self.lines = TypedPropertyCollection(LinePlotProperties)
        self.lines.strokeWidth = 1
        self.joinedLines = 1 # Connect items with straight lines.
        self.lines[0].strokeColor = colors.red
        self.lines[1].strokeColor = colors.blue

        self.lineLabels = TypedPropertyCollection(Label)
        self.lineLabelFormat = None
        self.lineLabelArray = None

        # this says whether the origin is inside or outside
        # the bar - +10 means put the origin ten points
        # above the tip of the bar if value > 0, or ten
        # points inside if bar value < 0.  This is different
        # to label dx/dy which are not dependent on the
        # sign of the data.
        self.lineLabelNudge = 10
        # if you have multiple series, by default they butt
        # together.

        #private attributes
        self._inFill = None
        self.annotations = []
        self.behindAxes = 0
        self.gridFirst = 0

    @property
    def joinedLines(self):
        return self.lines.lineStyle=='joinedLine'

    @joinedLines.setter
    def joinedLines(self,v):
        self.lines.lineStyle = 'joinedLine' if v else 'line'

    def demo(self):
        """Shows basic use of a line chart."""

        drawing = Drawing(400, 200)

        data = [
            ((1,1), (2,2), (2.5,1), (3,3), (4,5)),
            ((1,2), (2,3), (2.5,2), (3.5,5), (4,6))
            ]

        lp = LinePlot()

        lp.x = 50
        lp.y = 50
        lp.height = 125
        lp.width = 300
        lp.data = data
        lp.joinedLines = 1
        lp.lineLabelFormat = '%2.0f'
        lp.strokeColor = colors.black

        lp.lines[0].strokeColor = colors.red
        lp.lines[0].symbol = makeMarker('FilledCircle')
        lp.lines[1].strokeColor = colors.blue
        lp.lines[1].symbol = makeMarker('FilledDiamond')

        lp.xValueAxis.valueMin = 0
        lp.xValueAxis.valueMax = 5
        lp.xValueAxis.valueStep = 1

        lp.yValueAxis.valueMin = 0
        lp.yValueAxis.valueMax = 7
        lp.yValueAxis.valueStep = 1

        drawing.add(lp)

        return drawing


    def calcPositions(self):
        """Works out where they go.

        Sets an attribute _positions which is a list of
        lists of (x, y) matching the data.
        """

        self._seriesCount = len(self.data)
        self._rowLength = max(list(map(len,self.data)))

        pairs = set()
        P = [].append
        xscale = self.xValueAxis.scale
        yscale = self.yValueAxis.scale
        data = self.data
        n = len(data)
        for rowNo, row in enumerate(data):
            if isinstance(row, FillPairedData):
                other = row.other
                if 0<=other<n:
                    if other==rowNo:
                        raise ValueError('data row %r may not be paired with itself' % rowNo)
                    pairs.add((rowNo,other))
                else:
                    raise ValueError('data row %r is paired with invalid data row %r' % (rowNo, other))
            line = [].append
            for colNo, datum in enumerate(row):
                xv = datum[0]
                line(
                    (
                    xscale(mktime(mkTimeTuple(xv))) if isStr(xv) else xscale(xv),
                    yscale(datum[1])
                    )
                    )
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
        labelValue = self.data[rowNo][colNo][1] ###

        if labelFmt is None:
            labelText = None
        elif isinstance(labelFmt,str):
            if labelFmt == 'values':
                labelText = self.lineLabelArray[rowNo][colNo]
            else:
                labelText = labelFmt % labelValue
        elif hasattr(labelFmt,'__call__'):
            if not hasattr(labelFmt,'__labelFmtEX__'):
                labelText = labelFmt(labelValue)
            else:
                labelText = labelFmt(self,rowNo,colNo,x,y)
        else:
            raise ValueError("Unknown formatter type %s, expected string or function"% labelFmt)

        if labelText:
            label = self.lineLabels[(rowNo, colNo)]
            if not label.visible: return
            #hack to make sure labels are outside the bar
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
        yA = self.yValueAxis
        xA = self.xValueAxis
        bubblePlot = getattr(self,'_bubblePlot',None)
        if bubblePlot:
            bubbleR = min(yA._bubbleRadius,xA._bubbleRadius)
            bubbleMax = xA._bubbleMax

        labelFmt = self.lineLabelFormat

        P = self._positions
        _inFill = getattr(self,'_inFill',None)
        lines = self.lines
        styleCount = len(lines)
        if (_inFill or self._pairInFills or
                [rowNo for rowNo in range(len(P))
                        if getattr(lines[rowNo%styleCount],'inFill',False)]
                ):
            inFillY = getattr(_inFill,'yValue',None)
            if inFillY is None:
                inFillY = xA._y
            else:
                inFillY = yA.scale(inFillY)
            inFillX0 = yA._x
            inFillX1 = inFillX0 + xA._length
            inFillG = getattr(self,'_inFillG',g)
        bw = None
        lG = getattr(self,'_lineG',g)
        # Iterate over data rows.
        R = range(len(P))
        if self.reversePlotOrder: R = reversed(R)
        for rowNo in R:
            row = P[rowNo]
            styleRowNo = rowNo % styleCount
            rowStyle = lines[styleRowNo]
            strokeColor = getattr(rowStyle,'strokeColor',None)
            strokeWidth = getattr(rowStyle,'strokeWidth',None)
            fillColor = getattr(rowStyle, 'fillColor', strokeColor)
            inFill = getattr(rowStyle,'inFill',_inFill)
            dash = getattr(rowStyle, 'strokeDashArray', None)
            lineStyle = getattr(rowStyle,'lineStyle',None)

            if hasattr(rowStyle, 'strokeWidth'):
                width = rowStyle.strokeWidth
            elif hasattr(lines, 'strokeWidth'):
                width = lines.strokeWidth
            else:
                width = None

            # Iterate over data columns.
            if lineStyle=='bar':
                if bw is None:
                    x = max(map(len,P)) - 1 #the number of gaps
                    bw = (self.width/x - 1) if x>0 else self.width
                    barWidth = getattr(rowStyle,'barWidth',Percentage(50))
                    x = self.yValueAxis
                    y0 = x.scale(0)
                    bypos = max(x._y,y0)
                    byneg = min(x._y+x._length,y0)
                    xmin = self.xValueAxis._x
                    xmax = xmin + self.xValueAxis._length
                    if isinstance(barWidth,Percentage):
                        bw *= barWidth*0.005
                    else:
                        bw = barWidth*0.5
                for x, y in row:
                    w = bw
                    #print(f'{x=} {y=} {y0=} {byneg=} {bypos=}')
                    _y0 = byneg if y<y0 else bypos
                    x -= w/2
                    if x<xmin:
                        w -= xmin - x
                        x = xmin
                    elif x+w > xmax:
                        w -= xmax - x
                    g.add(Rect(x,_y0,w,y-_y0,strokeWidth=strokeWidth,strokeColor=strokeColor,fillColor=fillColor))
            elif lineStyle=='joinedLine':
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
                        inFillG.add(Polygon(fpoints,fillColor=fillColor,strokeColor=strokeColor if strokeColor==fillColor else None,strokeWidth=width or 0.1))
                if not inFill or inFill==2 or strokeColor!=fillColor:
                    line = PolyLine(points,strokeColor=strokeColor,strokeLineCap=0,strokeLineJoin=1)
                    if width:
                        line.strokeWidth = width
                    if dash:
                        line.strokeDashArray = dash
                    lG.add(line)

            if hasattr(rowStyle, 'symbol'):
                uSymbol = rowStyle.symbol
            elif hasattr(lines, 'symbol'):
                uSymbol = lines.symbol
            else:
                uSymbol = None

            if uSymbol:
                if bubblePlot: drow = self.data[rowNo]
                for j,xy in enumerate(row):
                    if (styleRowNo,j) in lines:
                        juSymbol = getattr(lines[styleRowNo,j],'symbol',uSymbol)
                    else:
                        juSymbol = uSymbol
                    if juSymbol is uSymbol:
                        symbol = uSymbol
                        symColor = strokeColor
                    else:
                        symbol = juSymbol
                        symColor = getattr(symbol,'fillColor',strokeColor)
                    symbol = uSymbol2Symbol(tpcGetItem(symbol,j),xy[0],xy[1],symColor)
                    if symbol:
                        if bubblePlot:
                            symbol.size = bubbleR*(drow[j][2]/bubbleMax)**0.5
                        g.add(symbol)
            else:
                if bubblePlot: drow = self.data[rowNo]
                for j,xy in enumerate(row):
                    juSymbol = getattr(lines[styleRowNo,j],'symbol',None)
                    if not juSymbol: continue
                    symColor = getattr(juSymbol,'fillColor',getattr(juSymbol,'strokeColor',strokeColor))
                    symbol = uSymbol2Symbol(juSymbol,xy[0],xy[1],symColor)
                    if symbol:
                        if bubblePlot:
                            symbol.size = bubbleR*(drow[j][2]/bubbleMax)**0.5
                        g.add(symbol)

            # Draw data labels.
            for colNo,datum in enumerate(row):
                x1, y1 = datum
                self.drawLabel(g, rowNo, colNo, x1, y1)

            shader = getattr(rowStyle, 'shader', None)
            if shader: shader.shade(self,g,rowNo,strokeColor,row)

        return g

    def draw(self):
        yA = self.yValueAxis
        xA = self.xValueAxis
        if getattr(self,'_bubblePlot',None):
            yA._bubblePlot = xA._bubblePlot = 1
        yA.setPosition(self.x, self.y, self.height)
        if yA: yA.joinAxis = xA
        if xA: xA.joinAxis = yA
        yA.configure(self.data)

        # if zero is in chart, put x axis there, otherwise use bottom.
        xAxisCrossesAt = yA.scale(0)
        if ((xAxisCrossesAt > self.y + self.height) or (xAxisCrossesAt < self.y)):
            y = self.y
        else:
            y = xAxisCrossesAt

        xA.setPosition(self.x, y, self.width)
        xA.configure(self.data)
        self.calcPositions()
        g = Group()
        g.add(self.makeBackground())
        if self._inFill or self.behindAxes:
            xA._joinToAxis()
            if self._inFill:
                self._inFillG = Group()
                g.add(self._inFillG)
            if self.behindAxes:
                self._lineG = Group()
                g.add(self._lineG)
        xA._joinToAxis()
        yA._joinToAxis()
        xAex = xA.visibleAxis and [xA._y] or []
        yAex = yA.visibleAxis and [yA._x] or []
        skipGrid = getattr(xA,'skipGrid','none')
        if skipGrid!=None:
            if skipGrid in ('both','top'):
                yAex.append(xA._x+xA._length)
            if skipGrid in ('both','bottom'):
                yAex.append(xA._x)
        skipGrid = getattr(yA,'skipGrid','none')
        if skipGrid!=None:
            if skipGrid in ('both','top'):
                xAex.append(yA._y+yA._length)
            if skipGrid in ('both','bottom'):
                xAex.append(yA._y)
        if self.gridFirst:
            xA.makeGrid(g,parent=self,dim=yA.getGridDims,exclude=yAex)
            yA.makeGrid(g,parent=self,dim=xA.getGridDims,exclude=xAex)
        g.add(xA.draw())
        g.add(yA.draw())
        if not self.gridFirst:
            xAdgl = getattr(xA,'drawGridLast',False)
            yAdgl = getattr(yA,'drawGridLast',False)
            if not xAdgl: xA.makeGrid(g,parent=self,dim=yA.getGridDims,exclude=yAex)
            if not yAdgl: yA.makeGrid(g,parent=self,dim=xA.getGridDims,exclude=xAex)
        annotations = getattr(self,'annotations',[])
        for a in annotations:
            if getattr(a,'beforeLines',None):
                g.add(a(self,xA.scale,yA.scale))
        g.add(self.makeLines())
        if not self.gridFirst:
            if xAdgl: xA.makeGrid(g,parent=self,dim=yA.getGridDims,exclude=yAex)
            if yAdgl: yA.makeGrid(g,parent=self,dim=xA.getGridDims,exclude=xAex)
        for a in annotations:
            if not getattr(a,'beforeLines',None):
                g.add(a(self,xA.scale,yA.scale))
        return g

    def addCrossHair(self,name,xv,yv,strokeColor=colors.black,strokeWidth=1,beforeLines=True):
        from reportlab.graphics.shapes import Group, Line
        annotations = [a for a in getattr(self,'annotations',[]) if getattr(a,'name',None)!=name]
        def annotation(self,xScale,yScale):
            x = xScale(xv)
            y = yScale(yv)
            g = Group()
            xA = xScale.__self__ #the x axis
            g.add(Line(xA._x,y,xA._x+xA._length,y,strokeColor=strokeColor,strokeWidth=strokeWidth))
            yA = yScale.__self__ #the y axis
            g.add(Line(x,yA._y,x,yA._y+yA._length,strokeColor=strokeColor,strokeWidth=strokeWidth))
            return g
        annotation.beforeLines = beforeLines
        annotations.append(annotation)
        self.annotations = annotations

class LinePlot3D(LinePlot):
    _attrMap = AttrMap(BASE=LinePlot,
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
        LinePlot.calcPositions(self)
        nSeries = self._seriesCount
        zSpace = self.zSpace
        zDepth = self.zDepth
        if self.xValueAxis.style=='parallel_3d':
            _3d_depth = nSeries*zDepth+(nSeries+1)*zSpace
        else:
            _3d_depth = zDepth + 2*zSpace
        self._3d_dx = self.theta_x*_3d_depth
        self._3d_dy = self.theta_y*_3d_depth

    def _calc_z0(self,rowNo):
        zSpace = self.zSpace
        if self.xValueAxis.style=='parallel_3d':
            z0 = rowNo*(self.zDepth+zSpace)+zSpace
        else:
            z0 = zSpace
        return z0

    def _zadjust(self,x,y,z):
        return x+z*self.theta_x, y+z*self.theta_y

    def makeLines(self):
        bubblePlot = getattr(self,'_bubblePlot',None)
        assert not bubblePlot, "_bubblePlot not supported for 3d yet"
        #if bubblePlot:
        #   yA = self.yValueAxis
        #   xA = self.xValueAxis
        #   bubbleR = min(yA._bubbleRadius,xA._bubbleRadius)
        #   bubbleMax = xA._bubbleMax

        labelFmt = self.lineLabelFormat
        positions = self._positions

        P = list(range(len(positions)))
        if self.reversePlotOrder: P.reverse()
        inFill = getattr(self,'_inFill',None)
        assert not inFill, "inFill not supported for 3d yet"
        #if inFill:
        #   inFillY = self.xValueAxis._y
        #   inFillX0 = self.yValueAxis._x
        #   inFillX1 = inFillX0 + self.xValueAxis._length
        #   inFillG = getattr(self,'_inFillG',g)
        zDepth = self.zDepth
        _zadjust = self._zadjust
        theta_x = self.theta_x
        theta_y = self.theta_y
        from reportlab.graphics.charts.linecharts import _FakeGroup
        F = _FakeGroup()

        from reportlab.graphics.charts.utils3d import _make_3d_line_info, find_intersections
        if self.xValueAxis.style!='parallel_3d':
            tileWidth = getattr(self,'_3d_tilewidth',1)
            if getattr(self,'_find_intersections',None):
                from copy import copy
                fpositions = list(map(copy,positions))
                I = find_intersections(fpositions,small=tileWidth)
                ic = None
                for i,j,x,y in I:
                    if ic!=i:
                        ic = i
                        jc = 0
                    else:
                        jc+=1
                    fpositions[i].insert(j+jc,(x,y))
                tileWidth = None
            else:
                fpositions = positions
        else:
            tileWidth = None
            fpositions = positions

        # Iterate over data rows.
        styleCount = len(self.lines)
        for rowNo in P:
            row = positions[rowNo]
            n = len(row)
            rowStyle = self.lines[rowNo % styleCount]
            rowColor = rowStyle.strokeColor
            dash = getattr(rowStyle, 'strokeDashArray', None)
            z0 = self._calc_z0(rowNo)
            z1 = z0 + zDepth

            if hasattr(rowStyle, 'strokeWidth'):
                width = rowStyle.strokeWidth
            elif hasattr(self.lines, 'strokeWidth'):
                width = self.lines.strokeWidth
            else:
                width = None

            # Iterate over data columns.
            if self.joinedLines:
                if n:
                    frow = fpositions[rowNo]
                    x0, y0 = frow[0]
                    for colNo in range(1,len(frow)):
                        x1, y1 = frow[colNo]
                        _make_3d_line_info( F, x0, x1, y0, y1, z0, z1,
                                theta_x, theta_y,
                                rowColor, fillColorShaded=None, tileWidth=tileWidth,
                                strokeColor=None, strokeWidth=None, strokeDashArray=None,
                                shading=0.1)
                        x0, y0 = x1, y1

            if hasattr(rowStyle, 'symbol'):
                uSymbol = rowStyle.symbol
            elif hasattr(self.lines, 'symbol'):
                uSymbol = self.lines.symbol
            else:
                uSymbol = None

            if uSymbol:
                for xy in row:
                    x1, y1 = row[colNo]
                    x1, y1 = _zadjust(x1,y1,z0)
                    symbol = uSymbol2Symbol(uSymbol,xy[0],xy[1],rowColor)
                    if symbol: F.add((1,z0,z0,x1,y1,symbol))

            # Draw data labels.
            for colNo in range(n):
                x1, y1 = row[colNo]
                x1, y1 = _zadjust(x1,y1,z0)
                L = self._innerDrawLabel(rowNo, colNo, x1, y1)
                if L: F.add((2,z0,z0,x1,y1,L))

        F.sort()
        g = Group()
        for v in F.value(): g.add(v[-1])
        return g

_monthlyIndexData = [[(19971202, 100.0),
  (19971231, 100.1704367),
  (19980131, 101.5639577),
  (19980228, 102.1879927),
  (19980331, 101.6337257),
  (19980430, 102.7640446),
  (19980531, 102.9198038),
  (19980630, 103.25938789999999),
  (19980731, 103.2516421),
  (19980831, 105.4744329),
  (19980930, 109.3242705),
  (19981031, 111.9859291),
  (19981130, 110.9184642),
  (19981231, 110.9184642),
  (19990131, 111.9882532),
  (19990228, 109.7912614),
  (19990331, 110.24189629999999),
  (19990430, 110.4279321),
  (19990531, 109.33955469999999),
  (19990630, 108.2341748),
  (19990731, 110.21294469999999),
  (19990831, 110.9683062),
  (19990930, 112.4425371),
  (19991031, 112.7314032),
  (19991130, 112.3509645),
  (19991231, 112.3660659),
  (20000131, 110.9255248),
  (20000229, 110.5266306),
  (20000331, 113.3116101),
  (20000430, 111.0449133),
  (20000531, 111.702717),
  (20000630, 113.5832178)],
 [(19971202, 100.0),
  (19971231, 100.0),
  (19980131, 100.8),
  (19980228, 102.0),
  (19980331, 101.9),
  (19980430, 103.0),
  (19980531, 103.0),
  (19980630, 103.1),
  (19980731, 103.1),
  (19980831, 102.8),
  (19980930, 105.6),
  (19981031, 108.3),
  (19981130, 108.1),
  (19981231, 111.9),
  (19990131, 113.1),
  (19990228, 110.2),
  (19990331, 111.8),
  (19990430, 112.3),
  (19990531, 110.1),
  (19990630, 109.3),
  (19990731, 111.2),
  (19990831, 111.7),
  (19990930, 112.6),
  (19991031, 113.2),
  (19991130, 113.9),
  (19991231, 115.4),
  (20000131, 112.7),
  (20000229, 113.9),
  (20000331, 115.8),
  (20000430, 112.2),
  (20000531, 112.6),
  (20000630, 114.6)]]

class SimpleTimeSeriesPlot(LinePlot):
    """A customized version of LinePlot.
    It uses NormalDateXValueAxis() and AdjYValueAxis() for the X and Y axes.
    """
    def __init__(self):
        LinePlot.__init__(self)
        self.xValueAxis = NormalDateXValueAxis()
        self.yValueAxis = YValueAxis()
        self.data = _monthlyIndexData

class GridLinePlot(SimpleTimeSeriesPlot):
    """A customized version of SimpleTimeSeriesSPlot.
    It uses NormalDateXValueAxis() and AdjYValueAxis() for the X and Y axes.
    The chart has a default grid background with thin horizontal lines
    aligned with the tickmarks (and labels). You can change the back-
    ground to be any Grid or ShadedRect, or scale the whole chart.
    If you do provide a background, you can specify the colours of the
    stripes with 'background.stripeColors'.
    """

    _attrMap = AttrMap(BASE=LinePlot,
        background = AttrMapValue(None, desc='Background for chart area (now Grid or ShadedRect).'),
        scaleFactor = AttrMapValue(isNumberOrNone, desc='Scalefactor to apply to whole drawing.'),
        )

    def __init__(self):
        from reportlab.lib import colors
        SimpleTimeSeriesPlot.__init__(self)
        self.scaleFactor = None
        self.background = Grid()
        self.background.orientation = 'horizontal'
        self.background.useRects = 0
        self.background.useLines = 1
        self.background.strokeWidth = 0.5
        self.background.strokeColor = colors.black

    def demo(self,drawing=None):
        from reportlab.lib import colors
        if not drawing:
            drawing = Drawing(400, 200)
        lp = GridLinePlot()
        lp.x = 50
        lp.y = 50
        lp.height = 125
        lp.width = 300
        lp.data = _monthlyIndexData
        lp.joinedLines = 1
        lp.strokeColor = colors.black
        c0 = colors.PCMYKColor(100,65,0,30, spotName='PANTONE 288 CV', density=100)
        lp.lines[0].strokeColor = c0
        lp.lines[0].strokeWidth = 2
        lp.lines[0].strokeDashArray = None
        c1 = colors.PCMYKColor(0,79,91,0, spotName='PANTONE Wm Red CV', density=100)
        lp.lines[1].strokeColor = c1
        lp.lines[1].strokeWidth = 1
        lp.lines[1].strokeDashArray = [3,1]
        lp.xValueAxis.labels.fontSize = 10
        lp.xValueAxis.labels.textAnchor = 'start'
        lp.xValueAxis.labels.boxAnchor = 'w'
        lp.xValueAxis.labels.angle = -45
        lp.xValueAxis.labels.dx = 0
        lp.xValueAxis.labels.dy = -8
        lp.xValueAxis.xLabelFormat = '{mm}/{yy}'
        lp.yValueAxis.labelTextFormat = '%5d%% '
        lp.yValueAxis.tickLeft = 5
        lp.yValueAxis.labels.fontSize = 10
        lp.background = Grid()
        lp.background.stripeColors = [colors.pink, colors.lightblue]
        lp.background.orientation = 'vertical'
        drawing.add(lp,'plot')
        return drawing

    def draw(self):
        xva, yva = self.xValueAxis, self.yValueAxis
        if xva: xva.joinAxis = yva
        if yva: yva.joinAxis = xva

        yva.setPosition(self.x, self.y, self.height)
        yva.configure(self.data)

        # if zero is in chart, put x axis there, otherwise
        # use bottom.
        xAxisCrossesAt = yva.scale(0)
        if ((xAxisCrossesAt > self.y + self.height) or (xAxisCrossesAt < self.y)):
            y = self.y
        else:
            y = xAxisCrossesAt

        xva.setPosition(self.x, y, self.width)
        xva.configure(self.data)

        back = self.background
        if isinstance(back, Grid):
            if back.orientation == 'vertical' and xva._tickValues:
                xpos = list(map(xva.scale, [xva._valueMin] + xva._tickValues))
                steps = []
                for i in range(len(xpos)-1):
                    steps.append(xpos[i+1] - xpos[i])
                back.deltaSteps = steps
            elif back.orientation == 'horizontal' and yva._tickValues:
                ypos = list(map(yva.scale, [yva._valueMin] + yva._tickValues))
                steps = []
                for i in range(len(ypos)-1):
                    steps.append(ypos[i+1] - ypos[i])
                back.deltaSteps = steps
        elif isinstance(back, DoubleGrid):
            # Ideally, these lines would not be needed...
            back.grid0.x = self.x
            back.grid0.y = self.y
            back.grid0.width = self.width
            back.grid0.height = self.height
            back.grid1.x = self.x
            back.grid1.y = self.y
            back.grid1.width = self.width
            back.grid1.height = self.height

            # some room left for optimization...
            if back.grid0.orientation == 'vertical' and xva._tickValues:
                xpos = list(map(xva.scale, [xva._valueMin] + xva._tickValues))
                steps = []
                for i in range(len(xpos)-1):
                    steps.append(xpos[i+1] - xpos[i])
                back.grid0.deltaSteps = steps
            elif back.grid0.orientation == 'horizontal' and yva._tickValues:
                ypos = list(map(yva.scale, [yva._valueMin] + yva._tickValues))
                steps = []
                for i in range(len(ypos)-1):
                    steps.append(ypos[i+1] - ypos[i])
                back.grid0.deltaSteps = steps
            if back.grid1.orientation == 'vertical' and xva._tickValues:
                xpos = list(map(xva.scale, [xva._valueMin] + xva._tickValues))
                steps = []
                for i in range(len(xpos)-1):
                    steps.append(xpos[i+1] - xpos[i])
                back.grid1.deltaSteps = steps
            elif back.grid1.orientation == 'horizontal' and yva._tickValues:
                ypos = list(map(yva.scale, [yva._valueMin] + yva._tickValues))
                steps = []
                for i in range(len(ypos)-1):
                    steps.append(ypos[i+1] - ypos[i])
                back.grid1.deltaSteps = steps

        self.calcPositions()

        width, height, scaleFactor = self.width, self.height, self.scaleFactor
        if scaleFactor and scaleFactor!=1:
            #g = Drawing(scaleFactor*width, scaleFactor*height)
            g.transform = (scaleFactor, 0, 0, scaleFactor,0,0)
        else:
            g = Group()

        g.add(self.makeBackground())
        g.add(self.xValueAxis)
        g.add(self.yValueAxis)
        g.add(self.makeLines())

        return g

class AreaLinePlot(LinePlot):
    '''we're given data in the form [(X1,Y11,..Y1M)....(Xn,Yn1,...YnM)]'''#'
    def __init__(self):
        LinePlot.__init__(self)
        self._inFill = 1
        self.reversePlotOrder = 1
        self.data = [(1,20,100,30),(2,11,50,15),(3,15,70,40)]

    def draw(self):
        try:
            odata = self.data
            n = len(odata)
            m = len(odata[0])
            S = n*[0]
            self.data = []
            for i in range(1,m):
                D = []
                for j in range(n):
                    S[j] = S[j] + odata[j][i]
                    D.append((odata[j][0],S[j]))
                self.data.append(D)
            return LinePlot.draw(self)
        finally:
            self.data = odata

class SplitLinePlot(AreaLinePlot):
    def __init__(self):
        AreaLinePlot.__init__(self)
        self.xValueAxis = NormalDateXValueAxis()
        self.yValueAxis = AdjYValueAxis()
        self.data=[(20030601,0.95,0.05,0.0),(20030701,0.95,0.05,0.0),(20030801,0.95,0.05,0.0),(20030901,0.95,0.05,0.0),(20031001,0.95,0.05,0.0),(20031101,0.95,0.05,0.0),(20031201,0.95,0.05,0.0),(20040101,0.95,0.05,0.0),(20040201,0.95,0.05,0.0),(20040301,0.95,0.05,0.0),(20040401,0.95,0.05,0.0),(20040501,0.95,0.05,0.0),(20040601,0.95,0.05,0.0),(20040701,0.95,0.05,0.0),(20040801,0.95,0.05,0.0),(20040901,0.95,0.05,0.0),(20041001,0.95,0.05,0.0),(20041101,0.95,0.05,0.0),(20041201,0.95,0.05,0.0),(20050101,0.95,0.05,0.0),(20050201,0.95,0.05,0.0),(20050301,0.95,0.05,0.0),(20050401,0.95,0.05,0.0),(20050501,0.95,0.05,0.0),(20050601,0.95,0.05,0.0),(20050701,0.95,0.05,0.0),(20050801,0.95,0.05,0.0),(20050901,0.95,0.05,0.0),(20051001,0.95,0.05,0.0),(20051101,0.95,0.05,0.0),(20051201,0.95,0.05,0.0),(20060101,0.95,0.05,0.0),(20060201,0.95,0.05,0.0),(20060301,0.95,0.05,0.0),(20060401,0.95,0.05,0.0),(20060501,0.95,0.05,0.0),(20060601,0.95,0.05,0.0),(20060701,0.95,0.05,0.0),(20060801,0.95,0.05,0.0),(20060901,0.95,0.05,0.0),(20061001,0.95,0.05,0.0),(20061101,0.95,0.05,0.0),(20061201,0.95,0.05,0.0),(20070101,0.95,0.05,0.0),(20070201,0.95,0.05,0.0),(20070301,0.95,0.05,0.0),(20070401,0.95,0.05,0.0),(20070501,0.95,0.05,0.0),(20070601,0.95,0.05,0.0),(20070701,0.95,0.05,0.0),(20070801,0.95,0.05,0.0),(20070901,0.95,0.05,0.0),(20071001,0.95,0.05,0.0),(20071101,0.95,0.05,0.0),(20071201,0.95,0.05,0.0),(20080101,0.95,0.05,0.0),(20080201,0.95,0.05,0.0),(20080301,0.95,0.05,0.0),(20080401,0.95,0.05,0.0),(20080501,0.95,0.05,0.0),(20080601,0.95,0.05,0.0),(20080701,0.95,0.05,0.0),(20080801,0.95,0.05,0.0),(20080901,0.95,0.05,0.0),(20081001,0.95,0.05,0.0),(20081101,0.95,0.05,0.0),(20081201,0.95,0.05,0.0),(20090101,0.95,0.05,0.0),(20090201,0.91,0.09,0.0),(20090301,0.91,0.09,0.0),(20090401,0.91,0.09,0.0),(20090501,0.91,0.09,0.0),(20090601,0.91,0.09,0.0),(20090701,0.91,0.09,0.0),(20090801,0.91,0.09,0.0),(20090901,0.91,0.09,0.0),(20091001,0.91,0.09,0.0),(20091101,0.91,0.09,0.0),(20091201,0.91,0.09,0.0),(20100101,0.91,0.09,0.0),(20100201,0.81,0.19,0.0),(20100301,0.81,0.19,0.0),(20100401,0.81,0.19,0.0),(20100501,0.81,0.19,0.0),(20100601,0.81,0.19,0.0),(20100701,0.81,0.19,0.0),(20100801,0.81,0.19,0.0),(20100901,0.81,0.19,0.0),(20101001,0.81,0.19,0.0),(20101101,0.81,0.19,0.0),(20101201,0.81,0.19,0.0),(20110101,0.81,0.19,0.0),(20110201,0.72,0.28,0.0),(20110301,0.72,0.28,0.0),(20110401,0.72,0.28,0.0),(20110501,0.72,0.28,0.0),(20110601,0.72,0.28,0.0),(20110701,0.72,0.28,0.0),(20110801,0.72,0.28,0.0),(20110901,0.72,0.28,0.0),(20111001,0.72,0.28,0.0),(20111101,0.72,0.28,0.0),(20111201,0.72,0.28,0.0),(20120101,0.72,0.28,0.0),(20120201,0.53,0.47,0.0),(20120301,0.53,0.47,0.0),(20120401,0.53,0.47,0.0),(20120501,0.53,0.47,0.0),(20120601,0.53,0.47,0.0),(20120701,0.53,0.47,0.0),(20120801,0.53,0.47,0.0),(20120901,0.53,0.47,0.0),(20121001,0.53,0.47,0.0),(20121101,0.53,0.47,0.0),(20121201,0.53,0.47,0.0),(20130101,0.53,0.47,0.0),(20130201,0.44,0.56,0.0),(20130301,0.44,0.56,0.0),(20130401,0.44,0.56,0.0),(20130501,0.44,0.56,0.0),(20130601,0.44,0.56,0.0),(20130701,0.44,0.56,0.0),(20130801,0.44,0.56,0.0),(20130901,0.44,0.56,0.0),(20131001,0.44,0.56,0.0),(20131101,0.44,0.56,0.0),(20131201,0.44,0.56,0.0),(20140101,0.44,0.56,0.0),(20140201,0.36,0.5,0.14),(20140301,0.36,0.5,0.14),(20140401,0.36,0.5,0.14),(20140501,0.36,0.5,0.14),(20140601,0.36,0.5,0.14),(20140701,0.36,0.5,0.14),(20140801,0.36,0.5,0.14),(20140901,0.36,0.5,0.14),(20141001,0.36,0.5,0.14),(20141101,0.36,0.5,0.14),(20141201,0.36,0.5,0.14),(20150101,0.36,0.5,0.14),(20150201,0.3,0.41,0.29),(20150301,0.3,0.41,0.29),(20150401,0.3,0.41,0.29),(20150501,0.3,0.41,0.29),(20150601,0.3,0.41,0.29),(20150701,0.3,0.41,0.29),(20150801,0.3,0.41,0.29),(20150901,0.3,0.41,0.29),(20151001,0.3,0.41,0.29),(20151101,0.3,0.41,0.29),(20151201,0.3,0.41,0.29),(20160101,0.3,0.41,0.29),(20160201,0.26,0.36,0.38),(20160301,0.26,0.36,0.38),(20160401,0.26,0.36,0.38),(20160501,0.26,0.36,0.38),(20160601,0.26,0.36,0.38),(20160701,0.26,0.36,0.38),(20160801,0.26,0.36,0.38),(20160901,0.26,0.36,0.38),(20161001,0.26,0.36,0.38),(20161101,0.26,0.36,0.38),(20161201,0.26,0.36,0.38),(20170101,0.26,0.36,0.38),(20170201,0.2,0.3,0.5),(20170301,0.2,0.3,0.5),(20170401,0.2,0.3,0.5),(20170501,0.2,0.3,0.5),(20170601,0.2,0.3,0.5),(20170701,0.2,0.3,0.5),(20170801,0.2,0.3,0.5),(20170901,0.2,0.3,0.5),(20171001,0.2,0.3,0.5),(20171101,0.2,0.3,0.5),(20171201,0.2,0.3,0.5),(20180101,0.2,0.3,0.5),(20180201,0.13,0.37,0.5),(20180301,0.13,0.37,0.5),(20180401,0.13,0.37,0.5),(20180501,0.13,0.37,0.5),(20180601,0.13,0.37,0.5),(20180701,0.13,0.37,0.5),(20180801,0.13,0.37,0.5),(20180901,0.13,0.37,0.5),(20181001,0.13,0.37,0.5),(20181101,0.13,0.37,0.5),(20181201,0.13,0.37,0.5),(20190101,0.13,0.37,0.5),(20190201,0.1,0.4,0.5),(20190301,0.1,0.4,0.5),(20190401,0.1,0.4,0.5),(20190501,0.1,0.4,0.5),(20190601,0.1,0.4,0.5),(20190701,0.1,0.4,0.5),(20190801,0.1,0.4,0.5),(20190901,0.1,0.4,0.5),(20191001,0.1,0.4,0.5),(20191101,0.1,0.4,0.5),(20191201,0.1,0.4,0.5),(20200101,0.1,0.4,0.5)]
        self.yValueAxis.requiredRange = None
        self.yValueAxis.leftAxisPercent = 0
        self.yValueAxis.leftAxisOrigShiftMin = 0
        self.yValueAxis.leftAxisOrigShiftIPC = 0
        self.lines[0].strokeColor = colors.toColor(0x0033cc)
        self.lines[1].strokeColor = colors.toColor(0x99c3ff)
        self.lines[2].strokeColor = colors.toColor(0xCC0033)

def _maxWidth(T, fontName, fontSize):
    '''return max stringWidth for the list of strings T'''
    if not isinstance(T,(tuple,list)): T = (T,)
    T = [_f for _f in T if _f]
    return T and max(list(map(lambda t,sW=stringWidth,fN=fontName, fS=fontSize: sW(t,fN,fS),T))) or 0

class ScatterPlot(LinePlot):
    """A scatter plot widget"""

    _attrMap = AttrMap(BASE=LinePlot,
                    width = AttrMapValue(isNumber, desc="Width of the area inside the axes"),
                    height = AttrMapValue(isNumber, desc="Height of the area inside the axes"),
                    outerBorderOn = AttrMapValue(isBoolean, desc="Is there an outer border (continuation of axes)"),
                    outerBorderColor = AttrMapValue(isColorOrNone, desc="Color of outer border (if any)"),
                    labelOffset = AttrMapValue(isNumber, desc="Space between label and Axis (or other labels)",advancedUsage=1),
                    axisTickLengths = AttrMapValue(isNumber, desc="Lenth of the ticks on both axes"),
                    axisStrokeWidth = AttrMapValue(isNumber, desc="Stroke width for both axes"),
                    xLabel = AttrMapValue(isString, desc="Label for the whole X-Axis"),
                    yLabel = AttrMapValue(isString, desc="Label for the whole Y-Axis"),
                    data = AttrMapValue(isAnything, desc='Data points - a list of x/y tuples.'),
                    strokeColor = AttrMapValue(isColorOrNone, desc='Color used for border of plot area.'),
                    fillColor = AttrMapValue(isColorOrNone, desc='Color used for background interior of plot area.'),
                    leftPadding = AttrMapValue(isNumber, desc='Padding on left of drawing'),
                    rightPadding = AttrMapValue(isNumber, desc='Padding on right of drawing'),
                    topPadding = AttrMapValue(isNumber, desc='Padding at top of drawing'),
                    bottomPadding = AttrMapValue(isNumber, desc='Padding at bottom of drawing'),
                    )

    def __init__(self):
        LinePlot.__init__(self)
        self.width = 142
        self.height = 77
        self.outerBorderOn = 1
        self.outerBorderColor = colors.black
        self.background = None

        _labelOffset = 3
        _axisTickLengths = 2
        _axisStrokeWidth = 0.5

        self.yValueAxis.valueMin = None
        self.yValueAxis.valueMax = None
        self.yValueAxis.valueStep = None
        self.yValueAxis.labelTextFormat  = '%s'

        self.xLabel="X Lable"
        self.xValueAxis.labels.fontSize = 6

        self.yLabel="Y Lable"
        self.yValueAxis.labels.fontSize = 6

        self.data =[((0.030, 62.73),
                     (0.074, 54.363),
                     (1.216, 17.964)),

                     ((1.360, 11.621),
                     (1.387, 50.011),
                     (1.428, 68.953)),

                     ((1.444, 86.888),
                     (1.754, 35.58),
                     (1.766, 36.05))]

        #values for lineplot
        self.joinedLines = 0

        self.leftPadding=5
        self.rightPadding=10
        self.topPadding=5
        self.bottomPadding=5

        self.x = self.leftPadding+_axisTickLengths+(_labelOffset*2)
        self.x=self.x+_maxWidth(str(self.yValueAxis.valueMax), self.yValueAxis.labels.fontName, self.yValueAxis.labels.fontSize)
        self.y = self.bottomPadding+_axisTickLengths+_labelOffset+self.xValueAxis.labels.fontSize

        self.xValueAxis.labels.dy = -_labelOffset
        self.xValueAxis.tickDown = _axisTickLengths
        self.xValueAxis.strokeWidth = _axisStrokeWidth
        self.xValueAxis.rangeRound='both'
        self.yValueAxis.labels.dx = -_labelOffset
        self.yValueAxis.tickLeft = _axisTickLengths
        self.yValueAxis.strokeWidth = _axisStrokeWidth
        self.yValueAxis.rangeRound='both'

        self.lineLabelFormat="%.2f"
        self.lineLabels.fontSize = 5
        self.lineLabels.boxAnchor = 'e'
        self.lineLabels.dx             = -2
        self.lineLabelNudge = 0
        self.lines.symbol=makeMarker('FilledCircle',size=3)
        self.lines[1].symbol=makeMarker('FilledDiamond',size=3)
        self.lines[2].symbol=makeMarker('FilledSquare',size=3)
        self.lines[2].strokeColor = colors.green

    def _getDrawingDimensions(self):
        tx = self.leftPadding+self.yValueAxis.tickLeft+(self.yValueAxis.labels.dx*2)+self.xValueAxis.labels.fontSize
        tx=tx+(5*_maxWidth(str(self.yValueAxis.valueMax), self.yValueAxis.labels.fontName, self.yValueAxis.labels.fontSize))
        tx=tx+self.width+self.rightPadding
        t=('%.2f%%'%self.xValueAxis.valueMax)
        tx=tx+(_maxWidth(t, self.yValueAxis.labels.fontName, self.yValueAxis.labels.fontSize))
        ty = self.bottomPadding+self.xValueAxis.tickDown+(self.xValueAxis.labels.dy*2)+(self.xValueAxis.labels.fontSize*2)
        ty=ty+self.yValueAxis.labels.fontSize+self.height+self.topPadding
        #print (tx, ty)
        return (tx,ty)

    def demo(self,drawing=None):
        if not drawing:
            tx,ty=self._getDrawingDimensions()
            drawing = Drawing(tx,ty)
        drawing.add(self.draw())
        return drawing

    def draw(self):
        ascent=getFont(self.xValueAxis.labels.fontName).face.ascent
        if ascent==0:
            ascent=0.718 # default (from helvetica)
        ascent=ascent*self.xValueAxis.labels.fontSize # normalize

        #basic LinePlot - does the Axes, Ticks etc
        lp = LinePlot.draw(self)

        xLabel = self.xLabel
        if xLabel: #Overall label for the X-axis
            xl=Label()
            xl.x = (self.x+self.width)/2.0
            xl.y = 0
            xl.fontName = self.xValueAxis.labels.fontName
            xl.fontSize = self.xValueAxis.labels.fontSize
            xl.setText(xLabel)
            lp.add(xl)

        yLabel = self.yLabel
        if yLabel: #Overall label for the Y-axis
            yl=Label()
            yl.angle = 90
            yl.x = 0
            yl.y = (self.y+self.height/2.0)
            yl.fontName = self.yValueAxis.labels.fontName
            yl.fontSize = self.yValueAxis.labels.fontSize
            yl.setText(yLabel)
            lp.add(yl)

        # do a bounding box - in the same style as the axes
        if self.outerBorderOn:
            lp.add(Rect(self.x, self.y, self.width, self.height,
                       strokeColor = self.outerBorderColor,
                       strokeWidth = self.yValueAxis.strokeWidth,
                       fillColor = None))

        lp.shift(self.leftPadding, self.bottomPadding)

        return lp

def sample1a():
    "A line plot with non-equidistant points in x-axis."

    drawing = Drawing(400, 200)

    data = [
            ((1,1), (2,2), (2.5,1), (3,3), (4,5)),
            ((1,2), (2,3), (2.5,2), (3.5,5), (4,6))
        ]

    lp = LinePlot()

    lp.x = 50
    lp.y = 50
    lp.height = 125
    lp.width = 300
    lp.data = data
    lp.joinedLines = 1
    lp.strokeColor = colors.black

    lp.lines.symbol = makeMarker('UK_Flag')

    lp.lines[0].strokeWidth = 2
    lp.lines[1].strokeWidth = 4

    lp.xValueAxis.valueMin = 0
    lp.xValueAxis.valueMax = 5
    lp.xValueAxis.valueStep = 1

    lp.yValueAxis.valueMin = 0
    lp.yValueAxis.valueMax = 7
    lp.yValueAxis.valueStep = 1

    drawing.add(lp)

    return drawing


def sample1b():
    "A line plot with non-equidistant points in x-axis."

    drawing = Drawing(400, 200)

    data = [
            ((1,1), (2,2), (2.5,1), (3,3), (4,5)),
            ((1,2), (2,3), (2.5,2), (3.5,5), (4,6))
        ]

    lp = LinePlot()

    lp.x = 50
    lp.y = 50
    lp.height = 125
    lp.width = 300
    lp.data = data
    lp.joinedLines = 1
    lp.lines.symbol = makeMarker('Circle')
    lp.lineLabelFormat = '%2.0f'
    lp.strokeColor = colors.black

    lp.xValueAxis.valueMin = 0
    lp.xValueAxis.valueMax = 5
    lp.xValueAxis.valueSteps = [1, 2, 2.5, 3, 4, 5]
    lp.xValueAxis.labelTextFormat = '%2.1f'

    lp.yValueAxis.valueMin = 0
    lp.yValueAxis.valueMax = 7
    lp.yValueAxis.valueStep = 1

    drawing.add(lp)

    return drawing


def sample1c():
    "A line plot with non-equidistant points in x-axis."

    drawing = Drawing(400, 200)

    data = [
            ((1,1), (2,2), (2.5,1), (3,3), (4,5)),
            ((1,2), (2,3), (2.5,2), (3.5,5), (4,6))
        ]

    lp = LinePlot()

    lp.x = 50
    lp.y = 50
    lp.height = 125
    lp.width = 300
    lp.data = data
    lp.joinedLines = 1
    lp.lines[0].symbol = makeMarker('FilledCircle')
    lp.lines[1].symbol = makeMarker('Circle')
    lp.lineLabelFormat = '%2.0f'
    lp.strokeColor = colors.black

    lp.xValueAxis.valueMin = 0
    lp.xValueAxis.valueMax = 5
    lp.xValueAxis.valueSteps = [1, 2, 2.5, 3, 4, 5]
    lp.xValueAxis.labelTextFormat = '%2.1f'

    lp.yValueAxis.valueMin = 0
    lp.yValueAxis.valueMax = 7
    lp.yValueAxis.valueSteps = [1, 2, 3, 5, 6]

    drawing.add(lp)

    return drawing


def preprocessData(series):
    "Convert date strings into seconds and multiply values by 100."

    return [(str2seconds(x[0]), x[1]*100) for x in series]


def sample2():
    "A line plot with non-equidistant points in x-axis."

    drawing = Drawing(400, 200)

    data = [
        (('25/11/1991',1),
         ('30/11/1991',1.000933333),
         ('31/12/1991',1.0062),
         ('31/01/1992',1.0112),
         ('29/02/1992',1.0158),
         ('31/03/1992',1.020733333),
         ('30/04/1992',1.026133333),
         ('31/05/1992',1.030266667),
         ('30/06/1992',1.034466667),
         ('31/07/1992',1.038733333),
         ('31/08/1992',1.0422),
         ('30/09/1992',1.045533333),
         ('31/10/1992',1.049866667),
         ('30/11/1992',1.054733333),
         ('31/12/1992',1.061),
         ),
        ]

    data[0] = preprocessData(data[0])

    lp = LinePlot()

    lp.x = 50
    lp.y = 50
    lp.height = 125
    lp.width = 300
    lp.data = data
    lp.joinedLines = 1
    lp.lines.symbol = makeMarker('FilledDiamond')
    lp.strokeColor = colors.black

    start = mktime(mkTimeTuple('25/11/1991'))
    t0 = mktime(mkTimeTuple('30/11/1991'))
    t1 = mktime(mkTimeTuple('31/12/1991'))
    t2 = mktime(mkTimeTuple('31/03/1992'))
    t3 = mktime(mkTimeTuple('30/06/1992'))
    t4 = mktime(mkTimeTuple('30/09/1992'))
    end = mktime(mkTimeTuple('31/12/1992'))
    lp.xValueAxis.valueMin = start
    lp.xValueAxis.valueMax = end
    lp.xValueAxis.valueSteps = [start, t0, t1, t2, t3, t4, end]
    lp.xValueAxis.labelTextFormat = seconds2str
    lp.xValueAxis.labels[1].dy = -20
    lp.xValueAxis.labels[2].dy = -35

    lp.yValueAxis.labelTextFormat = '%4.2f'
    lp.yValueAxis.valueMin = 100
    lp.yValueAxis.valueMax = 110
    lp.yValueAxis.valueStep = 2

    drawing.add(lp)

    return drawing

def sampleFillPairedData():
    d = Drawing(400,200)
    chart = SimpleTimeSeriesPlot()
    d.add(chart)
    chart.data = [FillPairedData(chart.data[0],1),chart.data[1]]
    chart.lines[0].filler= Filler(fillColor=colors.toColor('#9f9f9f'),strokeWidth=0,strokeColor=None)
    chart.lines[0].strokeColor = None
    chart.lines[1].strokeColor = None
    return d
