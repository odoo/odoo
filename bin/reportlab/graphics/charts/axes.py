#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/graphics/charts/axes.py
"""Collection of axes for charts.

The current collection comprises axes for charts using cartesian
coordinate systems. All axes might have tick marks and labels.
There are two dichotomies for axes: one of X and Y flavours and
another of category and value flavours.

Category axes have an ordering but no metric. They are divided
into a number of equal-sized buckets. Their tick marks or labels,
if available, go BETWEEN the buckets, and the labels are placed
below to/left of the X/Y-axis, respectively.

  Value axes have an ordering AND metric. They correspond to a nu-
  meric quantity. Value axis have a real number quantity associated
  with it. The chart tells it where to go.
  The most basic axis divides the number line into equal spaces
  and has tickmarks and labels associated with each; later we
  will add variants where you can specify the sampling
  interval.

The charts using axis tell them where the labels should be placed.

Axes of complementary X/Y flavours can be connected to each other
in various ways, i.e. with a specific reference point, like an
x/value axis to a y/value (or category) axis. In this case the
connection can be either at the top or bottom of the former or
at any absolute value (specified in points) or at some value of
the former axes in its own coordinate system.
"""
__version__=''' $Id: axes.py 2838 2006-04-18 17:47:54Z rgbecker $ '''

import string
from types import FunctionType, StringType, TupleType, ListType

from reportlab.lib.validators import    isNumber, isNumberOrNone, isListOfStringsOrNone, isListOfNumbers, \
                                        isListOfNumbersOrNone, isColorOrNone, OneOf, isBoolean, SequenceOf, \
                                        isString, EitherOr
from reportlab.lib.attrmap import *
from reportlab.lib import normalDate
from reportlab.graphics.shapes import Drawing, Line, PolyLine, Group, STATE_DEFAULTS, _textBoxLimits, _rotatedBoxLimits
from reportlab.graphics.widgetbase import Widget, TypedPropertyCollection
from reportlab.graphics.charts.textlabels import Label
from reportlab.graphics.charts.utils import nextRoundNumber


# Helpers.

def _findMinMaxValue(V, x, default, func, special=None):
    if type(V[0][0]) in (TupleType,ListType):
        if special:
            f=lambda T,x=x,special=special,func=func: special(T,x,func)
        else:
            f=lambda T,x=x: T[x]
        V=map(lambda e,f=f: map(f,e),V)
    V = filter(len,map(lambda x: filter(lambda x: x is not None,x),V))
    if len(V)==0: return default
    return func(map(func,V))

def _findMin(V, x, default,special=None):
    '''find minimum over V[i][x]'''
    return _findMinMaxValue(V,x,default,min,special=special)

def _findMax(V, x, default,special=None):
    '''find maximum over V[i][x]'''
    return _findMinMaxValue(V,x,default,max,special=special)

def _allInt(values):
    '''true if all values are int'''
    for v in values:
        try:
            if int(v)!=v: return 0
        except:
            return 0
    return 1

class _AxisG(Widget):
    def _get_line_pos(self,v):
        v = self.scale(v)
        try:
            v = v[0]
        except:
            pass
        return v

    def _cxLine(self,x,start,end):
        x = self._get_line_pos(x)
        return Line(x, self._y + start, x, self._y + end)

    def _cyLine(self,y,start,end):
        y = self._get_line_pos(y)
        return Line(self._x + start, y, self._x + end, y)

    def _cxLine3d(self,x,start,end,_3d_dx,_3d_dy):
        x = self._get_line_pos(x)
        y0 = self._y + start
        y1 = self._y + end
        y0, y1 = min(y0,y1),max(y0,y1)
        x1 = x + _3d_dx
        return PolyLine([x,y0,x1,y0+_3d_dy,x1,y1+_3d_dy],strokeLineJoin=1)

    def _cyLine3d(self,y,start,end,_3d_dx,_3d_dy):
        y = self._get_line_pos(y)
        x0 = self._x + start
        x1 = self._x + end
        x0, x1 = min(x0,x1),max(x0,x1)
        y1 = y + _3d_dy
        return PolyLine([x0,y,x0+_3d_dx,y1,x1+_3d_dx,y1],strokeLineJoin=1)

    def _getLineFunc(self, start, end, parent=None):
        _3d_dx = getattr(parent,'_3d_dx',None)
        if _3d_dx is not None:
            _3d_dy = getattr(parent,'_3d_dy',None)
            f = self._dataIndex and self._cyLine3d or self._cxLine3d
            return lambda v, s=start, e=end, f=f,_3d_dx=_3d_dx,_3d_dy=_3d_dy: f(v,s,e,_3d_dx=_3d_dx,_3d_dy=_3d_dy)
        else:
            f = self._dataIndex and self._cyLine or self._cxLine
            return lambda v, s=start, e=end, f=f: f(v,s,e)

    def _makeLines(self,g,start,end,strokeColor,strokeWidth,strokeDashArray,parent=None):
        func = self._getLineFunc(start,end,parent)
        for t in self._tickValues:
                L = func(t)
                L.strokeColor = strokeColor
                L.strokeWidth = strokeWidth
                L.strokeDashArray = strokeDashArray
                g.add(L)

    def makeGrid(self,g,dim=None,parent=None):
        '''this is only called by a container object'''
        s = self.gridStart
        e = self.gridEnd
        if dim:
            s = s is None and dim[0]
            e = e is None and dim[0]+dim[1]
        c = self.gridStrokeColor
        if self.visibleGrid and (s or e) and c is not None:
            if self._dataIndex: offs = self._x
            else: offs = self._y
            self._makeLines(g,s-offs,e-offs,c,self.gridStrokeWidth,self.gridStrokeDashArray,parent=parent)

# Category axes.
class CategoryAxis(_AxisG):
    "Abstract category axis, unusable in itself."
    _nodoc = 1
    _attrMap = AttrMap(
        visible = AttrMapValue(isBoolean, desc='Display entire object, if true.'),
        visibleAxis = AttrMapValue(isBoolean, desc='Display axis line, if true.'),
        visibleTicks = AttrMapValue(isBoolean, desc='Display axis ticks, if true.'),
        visibleLabels = AttrMapValue(isBoolean, desc='Display axis labels, if true.'),
        visibleGrid = AttrMapValue(isBoolean, desc='Display axis grid, if true.'),
        strokeWidth = AttrMapValue(isNumber, desc='Width of axis line and ticks.'),
        strokeColor = AttrMapValue(isColorOrNone, desc='Color of axis line and ticks.'),
        strokeDashArray = AttrMapValue(isListOfNumbersOrNone, desc='Dash array used for axis line.'),
        gridStrokeWidth = AttrMapValue(isNumber, desc='Width of grid lines.'),
        gridStrokeColor = AttrMapValue(isColorOrNone, desc='Color of grid lines.'),
        gridStrokeDashArray = AttrMapValue(isListOfNumbersOrNone, desc='Dash array used for grid lines.'),
        gridStart = AttrMapValue(isNumberOrNone, desc='Start of grid lines wrt axis origin'),
        gridEnd = AttrMapValue(isNumberOrNone, desc='End of grid lines wrt axis origin'),
        labels = AttrMapValue(None, desc='Handle of the axis labels.'),
        categoryNames = AttrMapValue(isListOfStringsOrNone, desc='List of category names.'),
        joinAxis = AttrMapValue(None, desc='Join both axes if true.'),
        joinAxisPos = AttrMapValue(isNumberOrNone, desc='Position at which to join with other axis.'),
        reverseDirection = AttrMapValue(isBoolean, desc='If true reverse category direction.'),
        style = AttrMapValue(OneOf('parallel','stacked','parallel_3d'),"How common category bars are plotted"),
        labelAxisMode = AttrMapValue(OneOf('high','low','axis'), desc="Like joinAxisMode, but for the axis labels"),
        tickShift = AttrMapValue(isBoolean, desc='Tick shift typically'),
        )

    def __init__(self):
        assert self.__class__.__name__!='CategoryAxis', "Abstract Class CategoryAxis Instantiated"
        # private properties set by methods.  The initial values
        # here are to make demos easy; they would always be
        # overridden in real life.
        self._x = 50
        self._y = 50
        self._length = 100
        self._catCount = 0

        # public properties
        self.visible = 1
        self.visibleAxis = 1
        self.visibleTicks = 1
        self.visibleLabels = 1
        self.visibleGrid = 0

        self.strokeWidth = 1
        self.strokeColor = STATE_DEFAULTS['strokeColor']
        self.strokeDashArray = STATE_DEFAULTS['strokeDashArray']
        self.gridStrokeWidth = 0.25
        self.gridStrokeColor = STATE_DEFAULTS['strokeColor']
        self.gridStrokeDashArray = STATE_DEFAULTS['strokeDashArray']
        self.gridStart = self.gridEnd = 0
        self.labels = TypedPropertyCollection(Label)
        # if None, they don't get labels. If provided,
        # you need one name per data point and they are
        # used for label text.
        self.categoryNames = None
        self.joinAxis = None
        self.joinAxisPos = None
        self.joinAxisMode = None
        self.labelAxisMode = 'axis'
        self.reverseDirection = 0
        self.style = 'parallel'

        #various private things which need to be initialized
        self._labelTextFormat = None
        self.tickShift = 0

    def setPosition(self, x, y, length):
        # ensure floating point
        self._x = x
        self._y = y
        self._length = length


    def configure(self, multiSeries,barWidth=None):
        self._catCount = max(map(len,multiSeries))
        self._barWidth = barWidth or (self._length/float(self._catCount or 1))
        self._calcTickmarkPositions()

    def _calcTickmarkPositions(self):
        n = self._catCount
        if self.tickShift:
            self._tickValues = [t+0.5 for t in xrange(n)]
        else:
            self._tickValues = range(n+1)

    def draw(self):
        g = Group()

        if not self.visible:
            return g

        g.add(self.makeAxis())
        g.add(self.makeTicks())
        g.add(self.makeTickLabels())

        return g

    def _scale(self,idx):
        if self.reverseDirection: idx = self._catCount-idx-1
        return idx

def _assertYAxis(axis):
    acn = axis.__class__.__name__
    assert acn[0]=='Y' or acn[:4]=='AdjY', "Cannot connect to other axes (%s), but Y- ones." % acn
def _assertXAxis(axis):
    acn = axis.__class__.__name__
    assert acn[0]=='X' or acn[:11]=='NormalDateX', "Cannot connect to other axes (%s), but X- ones." % acn

class XCategoryAxis(CategoryAxis):
    "X/category axis"

    _attrMap = AttrMap(BASE=CategoryAxis,
        tickUp = AttrMapValue(isNumber,
            desc='Tick length up the axis.'),
        tickDown = AttrMapValue(isNumber,
            desc='Tick length down the axis.'),
        joinAxisMode = AttrMapValue(OneOf('bottom', 'top', 'value', 'points', None),
            desc="Mode used for connecting axis ('bottom', 'top', 'value', 'points', None)."),
        )

    _dataIndex = 0

    def __init__(self):
        CategoryAxis.__init__(self)
        self.labels.boxAnchor = 'n' #north - top edge
        self.labels.dy = -5
        # ultra-simple tick marks for now go between categories
        # and have same line style as axis - need more
        self.tickUp = 0  # how far into chart does tick go?
        self.tickDown = 5  # how far below axis does tick go?


    def demo(self):
        self.setPosition(30, 70, 140)
        self.configure([(10,20,30,40,50)])

        self.categoryNames = ['One','Two','Three','Four','Five']
        # all labels top-centre aligned apart from the last
        self.labels.boxAnchor = 'n'
        self.labels[4].boxAnchor = 'e'
        self.labels[4].angle = 90

        d = Drawing(200, 100)
        d.add(self)
        return d


    def joinToAxis(self, yAxis, mode='bottom', pos=None):
        "Join with y-axis using some mode."

        _assertYAxis(yAxis)
        if mode == 'bottom':
            self._x = yAxis._x
            self._y = yAxis._y
        elif mode == 'top':
            self._x = yAxis._x
            self._y = yAxis._y + yAxis._length
        elif mode == 'value':
            self._x = yAxis._x
            self._y = yAxis.scale(pos)
        elif mode == 'points':
            self._x = yAxis._x
            self._y = pos

    def _joinToAxis(self):
        ja = self.joinAxis
        if ja:
            jam = self.joinAxisMode
            jap = self.joinAxisPos
            jta = self.joinToAxis
            if jam in ('bottom', 'top'):
                jta(ja, mode=jam)
            elif jam in ('value', 'points'):
                jta(ja, mode=jam, pos=jap)

    def scale(self, idx):
        """returns the x position and width in drawing units of the slice"""
        return (self._x + self._scale(idx)*self._barWidth, self._barWidth)

    def makeAxis(self):
        g = Group()
        self._joinToAxis()
        if not self.visibleAxis: return g

        axis = Line(self._x, self._y, self._x + self._length, self._y)
        axis.strokeColor = self.strokeColor
        axis.strokeWidth = self.strokeWidth
        axis.strokeDashArray = self.strokeDashArray
        g.add(axis)

        return g

    def makeTicks(self):
        g = Group()
        if not self.visibleTicks: return g
        if self.tickUp or self.tickDown:
            self._makeLines(g,self.tickUp,-self.tickDown,self.strokeColor,self.strokeWidth,self.strokeDashArray)
        return g

    def _labelAxisPos(self):
        axis = self.joinAxis
        if axis:
            mode = self.labelAxisMode
            if mode == 'low':
                return axis._y
            elif mode == 'high':
                return axis._y + axis._length
        return self._y

    def makeTickLabels(self):
        g = Group()

        if not self.visibleLabels: return g

        categoryNames = self.categoryNames
        if categoryNames is not None:
            catCount = self._catCount
            n = len(categoryNames)
            reverseDirection = self.reverseDirection
            barWidth = self._barWidth
            _y = self._labelAxisPos()
            _x = self._x

            for i in xrange(catCount):
                if reverseDirection: ic = catCount-i-1
                else: ic = i
                if ic>=n: continue
                x = _x + (i+0.5) * barWidth
                label = self.labels[i]
                label.setOrigin(x, _y)
                label.setText(categoryNames[ic] or '')
                g.add(label)

        return g


class YCategoryAxis(CategoryAxis):
    "Y/category axis"

    _attrMap = AttrMap(BASE=CategoryAxis,
        tickLeft = AttrMapValue(isNumber,
            desc='Tick length left of the axis.'),
        tickRight = AttrMapValue(isNumber,
            desc='Tick length right of the axis.'),
        joinAxisMode = AttrMapValue(OneOf(('left', 'right', 'value', 'points', None)),
            desc="Mode used for connecting axis ('left', 'right', 'value', 'points', None)."),
        )

    _dataIndex = 1


    def __init__(self):
        CategoryAxis.__init__(self)
        self.labels.boxAnchor = 'e' #east - right edge
        self.labels.dx = -5
        # ultra-simple tick marks for now go between categories
        # and have same line style as axis - need more
        self.tickLeft = 5  # how far left of axis does tick go?
        self.tickRight = 0  # how far right of axis does tick go?


    def demo(self):
        self.setPosition(50, 10, 80)
        self.configure([(10,20,30)])
        self.categoryNames = ['One','Two','Three']
        # all labels top-centre aligned apart from the last
        self.labels.boxAnchor = 'e'
        self.labels[2].boxAnchor = 's'
        self.labels[2].angle = 90

        d = Drawing(200, 100)
        d.add(self)
        return d


    def joinToAxis(self, xAxis, mode='left', pos=None):
        "Join with x-axis using some mode."

        _assertXAxis(xAxis)

        if mode == 'left':
            self._x = xAxis._x * 1.0
            self._y = xAxis._y * 1.0
        elif mode == 'right':
            self._x = (xAxis._x + xAxis._length) * 1.0
            self._y = xAxis._y * 1.0
        elif mode == 'value':
            self._x = xAxis.scale(pos) * 1.0
            self._y = xAxis._y * 1.0
        elif mode == 'points':
            self._x = pos * 1.0
            self._y = xAxis._y * 1.0

    def _joinToAxis(self):
        ja = self.joinAxis
        if ja:
            jam = self.joinAxisMode
            jap = self.joinAxisPos
            jta = self.joinToAxis
            if jam in ('left', 'right'):
                jta(ja, mode=jam)
            elif jam in ('value', 'points'):
                jta(ja, mode=jam, pos=jap)

    def scale(self, idx):
        "Returns the y position and width in drawing units of the slice."
        return (self._y + self._scale(idx)*self._barWidth, self._barWidth)

    def makeAxis(self):
        g = Group()
        self._joinToAxis()
        if not self.visibleAxis: return g

        axis = Line(self._x, self._y, self._x, self._y + self._length)
        axis.strokeColor = self.strokeColor
        axis.strokeWidth = self.strokeWidth
        axis.strokeDashArray = self.strokeDashArray
        g.add(axis)

        return g

    def makeTicks(self):
        g = Group()
        if not self.visibleTicks: return g
        if self.tickLeft or self.tickRight:
            self._makeLines(g,-self.tickLeft,self.tickRight,self.strokeColor,self.strokeWidth,self.strokeDashArray)
        return g

    def _labelAxisPos(self):
        axis = self.joinAxis
        if axis:
            mode = self.labelAxisMode
            if mode == 'low':
                return axis._x
            elif mode == 'high':
                return axis._x + axis._length
        return self._x

    def makeTickLabels(self):
        g = Group()

        if not self.visibleTicks: return g

        categoryNames = self.categoryNames
        if categoryNames is not None:
            catCount = self._catCount
            n = len(categoryNames)
            reverseDirection = self.reverseDirection
            barWidth = self._barWidth
            labels = self.labels
            _x = self._labelAxisPos()
            _y = self._y
            for i in xrange(catCount):
                if reverseDirection: ic = catCount-i-1
                else: ic = i
                if ic>=n: continue
                y = _y + (i+0.5) * barWidth
                label = labels[i]
                label.setOrigin(_x, y)
                label.setText(categoryNames[ic] or '')
                g.add(label)
        return g


# Value axes.
class ValueAxis(_AxisG):
    "Abstract value axis, unusable in itself."

    _attrMap = AttrMap(
        forceZero = AttrMapValue(EitherOr((isBoolean,OneOf('near'))), desc='Ensure zero in range if true.'),
        visible = AttrMapValue(isBoolean, desc='Display entire object, if true.'),
        visibleAxis = AttrMapValue(isBoolean, desc='Display axis line, if true.'),
        visibleLabels = AttrMapValue(isBoolean, desc='Display axis labels, if true.'),
        visibleTicks = AttrMapValue(isBoolean, desc='Display axis ticks, if true.'),
        visibleGrid = AttrMapValue(isBoolean, desc='Display axis grid, if true.'),
        strokeWidth = AttrMapValue(isNumber, desc='Width of axis line and ticks.'),
        strokeColor = AttrMapValue(isColorOrNone, desc='Color of axis line and ticks.'),
        strokeDashArray = AttrMapValue(isListOfNumbersOrNone, desc='Dash array used for axis line.'),
        gridStrokeWidth = AttrMapValue(isNumber, desc='Width of grid lines.'),
        gridStrokeColor = AttrMapValue(isColorOrNone, desc='Color of grid lines.'),
        gridStrokeDashArray = AttrMapValue(isListOfNumbersOrNone, desc='Dash array used for grid lines.'),
        gridStart = AttrMapValue(isNumberOrNone, desc='Start of grid lines wrt axis origin'),
        gridEnd = AttrMapValue(isNumberOrNone, desc='End of grid lines wrt axis origin'),
        minimumTickSpacing = AttrMapValue(isNumber, desc='Minimum value for distance between ticks.'),
        maximumTicks = AttrMapValue(isNumber, desc='Maximum number of ticks.'),
        labels = AttrMapValue(None, desc='Handle of the axis labels.'),
        labelTextFormat = AttrMapValue(None, desc='Formatting string or function used for axis labels.'),
        labelTextPostFormat = AttrMapValue(None, desc='Extra Formatting string.'),
        labelTextScale = AttrMapValue(isNumberOrNone, desc='Scaling for label tick values.'),
        valueMin = AttrMapValue(isNumberOrNone, desc='Minimum value on axis.'),
        valueMax = AttrMapValue(isNumberOrNone, desc='Maximum value on axis.'),
        valueStep = AttrMapValue(isNumberOrNone, desc='Step size used between ticks.'),
        valueSteps = AttrMapValue(isListOfNumbersOrNone, desc='List of step sizes used between ticks.'),
        avoidBoundFrac = AttrMapValue(EitherOr((isNumberOrNone,SequenceOf(isNumber,emptyOK=0,lo=2,hi=2))), desc='Fraction of interval to allow above and below.'),
        rangeRound=AttrMapValue(OneOf('none','both','ceiling','floor'),'How to round the axis limits'),
        zrangePref = AttrMapValue(isNumberOrNone, desc='Zero range axis limit preference.'),
        style = AttrMapValue(OneOf('normal','stacked','parallel_3d'),"How values are plotted!"),
        )

    def __init__(self):
        assert self.__class__.__name__!='ValueAxis', 'Abstract Class ValueAxis Instantiated'
        self._configured = 0
        # private properties set by methods.  The initial values
        # here are to make demos easy; they would always be
        # overridden in real life.
        self._x = 50
        self._y = 50
        self._length = 100

        # public properties
        self.visible = 1
        self.visibleAxis = 1
        self.visibleLabels = 1
        self.visibleTicks = 1
        self.visibleGrid = 0
        self.forceZero = 0

        self.strokeWidth = 1
        self.strokeColor = STATE_DEFAULTS['strokeColor']
        self.strokeDashArray = STATE_DEFAULTS['strokeDashArray']
        self.gridStrokeWidth = 0.25
        self.gridStrokeColor = STATE_DEFAULTS['strokeColor']
        self.gridStrokeDashArray = STATE_DEFAULTS['strokeDashArray']
        self.gridStart = self.gridEnd = 0

        self.labels = TypedPropertyCollection(Label)
        self.labels.angle = 0

        # how close can the ticks be?
        self.minimumTickSpacing = 10
        self.maximumTicks = 7

        # a format string like '%0.2f'
        # or a function which takes the value as an argument and returns a string
        self._labelTextFormat = self.labelTextFormat = self.labelTextPostFormat = self.labelTextScale = None

        # if set to None, these will be worked out for you.
        # if you override any or all of them, your values
        # will be used.
        self.valueMin = None
        self.valueMax = None
        self.valueStep = None
        self.avoidBoundFrac = None
        self.rangeRound = 'none'
        self.zrangePref = 0
        self.style = 'normal'

    def setPosition(self, x, y, length):
        # ensure floating point
        self._x = x * 1.0
        self._y = y * 1.0
        self._length = length * 1.0

    def configure(self, dataSeries):
        """Let the axis configure its scale and range based on the data.

        Called after setPosition. Let it look at a list of lists of
        numbers determine the tick mark intervals.  If valueMin,
        valueMax and valueStep are configured then it
        will use them; if any of them are set to None it
        will look at the data and make some sensible decision.
        You may override this to build custom axes with
        irregular intervals.  It creates an internal
        variable self._values, which is a list of numbers
        to use in plotting.
        """
        self._setRange(dataSeries)
        self._calcTickmarkPositions()
        self._calcScaleFactor()
        self._configured = 1

    def _getValueStepAndTicks(self, valueMin, valueMax,cache={}):
        try:
            K = (valueMin,valueMax)
            r = cache[K]
        except:
            self._valueMin = valueMin
            self._valueMax = valueMax
            T = self._calcTickPositions()
            if len(T)>1:
                valueStep = T[1]-T[0]
            else:
                oVS = self.valueStep
                self.valueStep = None
                T = self._calcTickPositions()
                self.valueStep = oVS
                if len(T)>1:
                    valueStep = T[1]-T[0]
                else:
                    valueStep = self._valueStep
            r = cache[K] = valueStep, T, valueStep*1e-8
        return r

    def _setRange(self, dataSeries):
        """Set minimum and maximum axis values.

        The dataSeries argument is assumed to be a list of data
        vectors. Each vector is itself a list or tuple of numbers.

        Returns a min, max tuple.
        """

        oMin = valueMin = self.valueMin
        oMax = valueMax = self.valueMax
        rangeRound = self.rangeRound
        if valueMin is None: valueMin = self._cValueMin = _findMin(dataSeries,self._dataIndex,0)
        if valueMax is None: valueMax = self._cValueMax = _findMax(dataSeries,self._dataIndex,0)
        if valueMin == valueMax:
            if valueMax==0:
                if oMin is None and oMax is None:
                    zrp = getattr(self,'zrangePref',0)
                    if zrp>0:
                        valueMax = zrp
                        valueMin = 0
                    elif zrp<0:
                        valueMax = 0
                        valueMin = zrp
                    else:
                        valueMax = 0.01
                        valueMin = -0.01
                elif self.valueMin is None:
                    valueMin = -0.01
                else:
                    valueMax = 0.01
            else:
                if valueMax>0:
                    valueMax = 1.2*valueMax
                    valueMin = 0.0
                else:
                    valueMax = 0.0
                    valueMin = 1.2*valueMin

        if getattr(self,'_bubblePlot',None):
            bubbleMax = float(_findMax(dataSeries,2,0))
            frac=.25
            bubbleV=frac*(valueMax-valueMin)
            self._bubbleV = bubbleV
            self._bubbleMax = bubbleMax
            self._bubbleRadius = frac*self._length
            def special(T,x,func,bubbleV=bubbleV,bubbleMax=bubbleMax):
                try:
                    v = T[2]
                except IndexError:
                    v = bubbleMAx*0.1
                bubbleV *= (v/bubbleMax)**0.5
                return func(T[x]+bubbleV,T[x]-bubbleV)
            if oMin is None: valueMin = self._cValueMin = _findMin(dataSeries,self._dataIndex,0,special=special)
            if oMax is None: valueMax = self._cValueMax = _findMax(dataSeries,self._dataIndex,0,special=special)

        forceZero = self.forceZero
        if forceZero:
            if forceZero=='near':
                forceZero = min(abs(valueMin),abs(valueMax)) <= 5*(valueMax-valueMin)
            if forceZero:
                if valueMax<0: valueMax=0
                elif valueMin>0: valueMin = 0

        abf = self.avoidBoundFrac
        do_rr = not getattr(self,'valueSteps',None)
        do_abf = abf and do_rr
        if type(abf) not in (TupleType,ListType):
            abf = abf, abf
        do_rr = rangeRound is not 'none' and do_rr
        if do_rr:
            rrn = rangeRound in ['both','floor']
            rrx = rangeRound in ['both','ceiling']
        else:
            rrn = rrx = 0

        go = do_rr or do_abf
        cache = {}
        cMin = valueMin
        cMax = valueMax
        iter = 0
        while go and iter<=10:
            iter += 1
            go = 0
            if do_abf:
                valueStep, T, fuzz = self._getValueStepAndTicks(valueMin, valueMax, cache)
                i0 = valueStep*abf[0]
                i1 = valueStep*abf[1]
                if rrn: v = T[0]
                else: v = valueMin
                u = cMin-i0
                if abs(v)>fuzz and v>=u+fuzz:
                    valueMin = u
                    go = 1
                if rrx: v = T[-1]
                else: v = valueMax
                u = cMax+i1
                if abs(v)>fuzz and v<=u-fuzz:
                    valueMax = u
                    go = 1

            if do_rr:
                valueStep, T, fuzz = self._getValueStepAndTicks(valueMin, valueMax, cache)
                if rrn:
                    if valueMin<T[0]-fuzz:
                        valueMin = T[0]-valueStep
                        go = 1
                    else:
                        go = valueMin>=T[0]+fuzz
                        valueMin = T[0]
                if rrx:
                    if valueMax>T[-1]+fuzz:
                        valueMax = T[-1]+valueStep
                        go = 1
                    else:
                        go = valueMax<=T[-1]-fuzz
                        valueMax = T[-1]

        self._valueMin, self._valueMax = valueMin, valueMax
        self._rangeAdjust()

    def _rangeAdjust(self):
        """Override this if you want to alter the calculated range.

        E.g. if want a minumamum range of 30% or don't want 100%
        as the first point.
        """
        pass

    def _adjustAxisTicks(self):
        '''Override if you want to put slack at the ends of the axis
        eg if you don't want the last tick to be at the bottom etc
        '''
        pass

    def _calcScaleFactor(self):
        """Calculate the axis' scale factor.
        This should be called only *after* the axis' range is set.
        Returns a number.
        """
        self._scaleFactor = self._length / float(self._valueMax - self._valueMin)
        return self._scaleFactor

    def _calcTickPositions(self):
        self._calcValueStep()
        valueMin, valueMax, valueStep = self._valueMin, self._valueMax, self._valueStep
        fuzz = 1e-8*valueStep
        rangeRound = self.rangeRound
        i0 = int(float(valueMin)/valueStep)
        v = i0*valueStep
        if rangeRound in ('both','floor'):
            if v>valueMin+fuzz: i0 -= 1
        elif v<valueMin-fuzz: i0 += 1
        i1 = int(float(valueMax)/valueStep)
        v = i1*valueStep
        if rangeRound in ('both','ceiling'):
            if v<valueMax-fuzz: i1 += 1
        elif v>valueMax+fuzz: i1 -= 1
        return [i*valueStep for i in xrange(i0,i1+1)]

    def _calcTickmarkPositions(self):
        """Calculate a list of tick positions on the axis.  Returns a list of numbers."""
        self._tickValues = getattr(self,'valueSteps',None)
        if self._tickValues: return self._tickValues
        self._tickValues = self._calcTickPositions()
        self._adjustAxisTicks()
        return self._tickValues

    def _calcValueStep(self):
        '''Calculate _valueStep for the axis or get from valueStep.'''
        if self.valueStep is None:
            rawRange = self._valueMax - self._valueMin
            rawInterval = rawRange / min(float(self.maximumTicks-1),(float(self._length)/self.minimumTickSpacing))
            self._valueStep = nextRoundNumber(rawInterval)
        else:
            self._valueStep = self.valueStep

    def _allIntTicks(self):
        return _allInt(self._tickValues)

    def makeTickLabels(self):
        g = Group()
        if not self.visibleLabels: return g

        f = self._labelTextFormat       # perhaps someone already set it
        if f is None:
            f = self.labelTextFormat or (self._allIntTicks() and '%.0f' or str)
        elif f is str and self._allIntTicks(): f = '%.0f'
        post = self.labelTextPostFormat
        scl = self.labelTextScale
        pos = [self._x, self._y]
        d = self._dataIndex
        labels = self.labels

        i = 0
        for tick in self._tickValues:
            if f and labels[i].visible:
                v = self.scale(tick)
                if scl is not None:
                    t = tick*scl
                else:
                    t = tick
                if type(f) is StringType: txt = f % t
                elif type(f) in (TupleType,ListType):
                    #it's a list, use as many items as we get
                    if i < len(f):
                        txt = f[i]
                    else:
                        txt = ''
                elif callable(f):
                    txt = f(t)
                else:
                    raise ValueError, 'Invalid labelTextFormat %s' % f
                if post: txt = post % txt
                label = labels[i]
                pos[d] = v
                apply(label.setOrigin,pos)
                label.setText(txt)
                g.add(label)
            i = i + 1

        return g

    def draw(self):
        g = Group()

        if not self.visible:
            return g

        g.add(self.makeAxis())
        g.add(self.makeTicks())
        g.add(self.makeTickLabels())

        return g


class XValueAxis(ValueAxis):
    "X/value axis"

    _attrMap = AttrMap(BASE=ValueAxis,
        tickUp = AttrMapValue(isNumber,
            desc='Tick length up the axis.'),
        tickDown = AttrMapValue(isNumber,
            desc='Tick length down the axis.'),
        joinAxis = AttrMapValue(None,
            desc='Join both axes if true.'),
        joinAxisMode = AttrMapValue(OneOf('bottom', 'top', 'value', 'points', None),
            desc="Mode used for connecting axis ('bottom', 'top', 'value', 'points', None)."),
        joinAxisPos = AttrMapValue(isNumberOrNone,
            desc='Position at which to join with other axis.'),
        )

    # Indicate the dimension of the data we're interested in.
    _dataIndex = 0

    def __init__(self):
        ValueAxis.__init__(self)

        self.labels.boxAnchor = 'n'
        self.labels.dx = 0
        self.labels.dy = -5

        self.tickUp = 0
        self.tickDown = 5

        self.joinAxis = None
        self.joinAxisMode = None
        self.joinAxisPos = None


    def demo(self):
        self.setPosition(20, 50, 150)
        self.configure([(10,20,30,40,50)])

        d = Drawing(200, 100)
        d.add(self)
        return d


    def joinToAxis(self, yAxis, mode='bottom', pos=None):
        "Join with y-axis using some mode."
        _assertYAxis(yAxis)
        if mode == 'bottom':
            self._x = yAxis._x * 1.0
            self._y = yAxis._y * 1.0
        elif mode == 'top':
            self._x = yAxis._x * 1.0
            self._y = (yAxis._y + yAxis._length) * 1.0
        elif mode == 'value':
            self._x = yAxis._x * 1.0
            self._y = yAxis.scale(pos) * 1.0
        elif mode == 'points':
            self._x = yAxis._x * 1.0
            self._y = pos * 1.0

    def _joinToAxis(self):
        ja = self.joinAxis
        if ja:
            jam = self.joinAxisMode
            jap = self.joinAxisPos
            jta = self.joinToAxis
            if jam in ('bottom', 'top'):
                jta(ja, mode=jam)
            elif jam in ('value', 'points'):
                jta(ja, mode=jam, pos=jap)

    def scale(self, value):
        """Converts a numeric value to a Y position.

        The chart first configures the axis, then asks it to
        work out the x value for each point when plotting
        lines or bars.  You could override this to do
        logarithmic axes.
        """

        msg = "Axis cannot scale numbers before it is configured"
        assert self._configured, msg
        if value is None:
            value = 0
        return self._x + self._scaleFactor * (value - self._valueMin)


    def makeAxis(self):
        g = Group()
        self._joinToAxis()
        if not self.visibleAxis: return g

        axis = Line(self._x, self._y, self._x + self._length, self._y)
        axis.strokeColor = self.strokeColor
        axis.strokeWidth = self.strokeWidth
        axis.strokeDashArray = self.strokeDashArray
        g.add(axis)

        return g

    def makeTicks(self):
        g = Group()
        if self.visibleTicks and (self.tickUp or self.tickDown):
            self._makeLines(g,-self.tickDown,self.tickUp,self.strokeColor,self.strokeWidth,self.strokeDashArray)
        return g

class NormalDateXValueAxis(XValueAxis):
    """An X axis applying additional rules.

    Depending on the data and some built-in rules, the axis
    displays normalDate values as nicely formatted dates.

    The client chart should have NormalDate X values.
    """

    _attrMap = AttrMap(BASE = XValueAxis,
        bottomAxisLabelSlack = AttrMapValue(isNumber, desc="Fractional amount used to adjust label spacing"),
        niceMonth = AttrMapValue(isBoolean, desc="Flag for displaying months 'nicely'."),
        forceEndDate = AttrMapValue(isBoolean, desc='Flag for enforced displaying of last date value.'),
        forceFirstDate = AttrMapValue(isBoolean, desc='Flag for enforced displaying of first date value.'),
        xLabelFormat = AttrMapValue(None, desc="Label format string (e.g. '{mm}/{yy}') or function."),
        dayOfWeekName = AttrMapValue(SequenceOf(isString,emptyOK=0,lo=7,hi=7), desc='Weekday names.'),
        monthName = AttrMapValue(SequenceOf(isString,emptyOK=0,lo=12,hi=12), desc='Month names.'),
        dailyFreq = AttrMapValue(isBoolean, desc='True if we are to assume daily data to be ticked at end of month.'),
        )

    _valueClass = normalDate.ND

    def __init__(self, **kw):
        apply(XValueAxis.__init__, (self,))

        # some global variables still used...
        self.bottomAxisLabelSlack = 0.1
        self.niceMonth = 1
        self.forceEndDate = 0
        self.forceFirstDate = 0
        self.dailyFreq = 0
        self.xLabelFormat = "{mm}/{yy}"
        self.dayOfWeekName = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        self.monthName = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
                            'August', 'September', 'October', 'November', 'December']
        self.valueSteps = None

    def _scalar2ND(self, x):
        "Convert a scalar to a NormalDate value."
        d = self._valueClass()
        d.normalize(x)
        return d

    def _dateFormatter(self, v):
        "Create a formatted label for some value."
        if not isinstance(v,normalDate.NormalDate):
            v = self._scalar2ND(v)
        d, m = normalDate._dayOfWeekName, normalDate._monthName
        try:
            normalDate._dayOfWeekName, normalDate._monthName = self.dayOfWeekName, self.monthName
            return v.formatMS(self.xLabelFormat)
        finally:
            normalDate._dayOfWeekName, normalDate._monthName = d, m

    def _xAxisTicker(self, xVals):
        """Complex stuff...

        Needs explanation...
        """
        axisLength = self._length
        formatter = self._dateFormatter
        labels = self.labels
        fontName, fontSize, leading = labels.fontName, labels.fontSize, labels.leading
        textAnchor, boxAnchor, angle = labels.textAnchor, labels.boxAnchor, labels.angle
        RBL = _textBoxLimits(string.split(formatter(xVals[0]),'\n'),fontName,
                    fontSize,leading or 1.2*fontSize,textAnchor,boxAnchor)
        RBL = _rotatedBoxLimits(RBL[0],RBL[1],RBL[2],RBL[3], angle)
        xLabelW = RBL[1]-RBL[0]
        xLabelH = RBL[3]-RBL[2]
        w = max(xLabelW,labels.width,self.minimumTickSpacing)

        W = w+w*self.bottomAxisLabelSlack
        n = len(xVals)
        ticks = []
        labels = []
        maximumTicks = self.maximumTicks

        def addTick(i, xVals=xVals, formatter=formatter, ticks=ticks, labels=labels):
            ticks.insert(0,xVals[i])
            labels.insert(0,formatter(xVals[i]))

        for d in (1,2,3,6,12,24,60,120):
            k = n/d
            if k<=maximumTicks and k*W <= axisLength:
                i = n-1
                if self.niceMonth:
                    j = xVals[-1].month() % (d<=12 and d or 12)
                    if j:
                        if self.forceEndDate: addTick(i)
                        i = i - j

                #weird first date ie not at end of month
                try:
                    wfd = xVals[0].month() == xVals[1].month()
                except:
                    wfd = 0

                while i>=wfd:
                    addTick(i)
                    i = i - d

                if self.forceFirstDate and ticks[0] != xVals[0]:
                    addTick(0)
                    if (axisLength/(ticks[-1]-ticks[0]))*(ticks[1]-ticks[0])<=w:
                        del ticks[1], labels[1]
                if self.forceEndDate and self.niceMonth and j:
                    if (axisLength/(ticks[-1]-ticks[0]))*(ticks[-1]-ticks[-2])<=w:
                        del ticks[-2], labels[-2]
                try:
                    if labels[0] and labels[0]==labels[1]:
                        del ticks[1], labels[1]
                except IndexError:
                    pass

                return ticks, labels

    def _convertXV(self,data):
        '''Convert all XValues to a standard normalDate type'''

        VC = self._valueClass
        for D in data:
            for i in xrange(len(D)):
                x, y = D[i]
                if not isinstance(x,VC):
                    D[i] = (VC(x),y)

    def _getStepsAndLabels(self,xVals):
        if self.dailyFreq:
            xEOM = []
            pm = 0
            px = xVals[0]
            for x in xVals:
                m = x.month()
                if pm!=m:
                    if pm: xEOM.append(px)
                    pm = m
                px = x
            px = xVals[-1]
            if xEOM[-1]!=x: xEOM.append(px)
            steps, labels = self._xAxisTicker(xEOM)
        else:
            steps, labels = self._xAxisTicker(xVals)
        return steps, labels

    def configure(self, data):
        self._convertXV(data)
        from reportlab.lib.set_ops import union
        xVals = reduce(union,map(lambda x: map(lambda dv: dv[0],x),data),[])
        xVals.sort()
        steps,labels = self._getStepsAndLabels(xVals)
        valueMin, valueMax = self.valueMin, self.valueMax
        if valueMin is None: valueMin = xVals[0]
        if valueMax is None: valueMax = xVals[-1]
        self._valueMin, self._valueMax = valueMin, valueMax
        self._tickValues = steps
        self._labelTextFormat = labels

        self._scaleFactor = self._length / float(valueMax - valueMin)
        self._tickValues = steps
        self._configured = 1

class YValueAxis(ValueAxis):
    "Y/value axis"

    _attrMap = AttrMap(BASE=ValueAxis,
        tickLeft = AttrMapValue(isNumber,
            desc='Tick length left of the axis.'),
        tickRight = AttrMapValue(isNumber,
            desc='Tick length right of the axis.'),
        joinAxis = AttrMapValue(None,
            desc='Join both axes if true.'),
        joinAxisMode = AttrMapValue(OneOf(('left', 'right', 'value', 'points', None)),
            desc="Mode used for connecting axis ('left', 'right', 'value', 'points', None)."),
        joinAxisPos = AttrMapValue(isNumberOrNone,
            desc='Position at which to join with other axis.'),
        )

    # Indicate the dimension of the data we're interested in.
    _dataIndex = 1

    def __init__(self):
        ValueAxis.__init__(self)

        self.labels.boxAnchor = 'e'
        self.labels.dx = -5
        self.labels.dy = 0

        self.tickRight = 0
        self.tickLeft = 5

        self.joinAxis = None
        self.joinAxisMode = None
        self.joinAxisPos = None


    def demo(self):
        data = [(10, 20, 30, 42)]
        self.setPosition(100, 10, 80)
        self.configure(data)

        drawing = Drawing(200, 100)
        drawing.add(self)
        return drawing



    def joinToAxis(self, xAxis, mode='left', pos=None):
        "Join with x-axis using some mode."
        _assertXAxis(xAxis)
        if mode == 'left':
            self._x = xAxis._x * 1.0
            self._y = xAxis._y * 1.0
        elif mode == 'right':
            self._x = (xAxis._x + xAxis._length) * 1.0
            self._y = xAxis._y * 1.0
        elif mode == 'value':
            self._x = xAxis.scale(pos) * 1.0
            self._y = xAxis._y * 1.0
        elif mode == 'points':
            self._x = pos * 1.0
            self._y = xAxis._y * 1.0

    def _joinToAxis(self):
        ja = self.joinAxis
        if ja:
            jam = self.joinAxisMode
            jap = self.joinAxisPos
            jta = self.joinToAxis
            if jam in ('left', 'right'):
                jta(ja, mode=jam)
            elif jam in ('value', 'points'):
                jta(ja, mode=jam, pos=jap)

    def scale(self, value):
        """Converts a numeric value to a Y position.

        The chart first configures the axis, then asks it to
        work out the x value for each point when plotting
        lines or bars.  You could override this to do
        logarithmic axes.
        """

        msg = "Axis cannot scale numbers before it is configured"
        assert self._configured, msg

        if value is None:
            value = 0
        return self._y + self._scaleFactor * (value - self._valueMin)


    def makeAxis(self):
        g = Group()
        self._joinToAxis()
        if not self.visibleAxis: return g

        axis = Line(self._x, self._y, self._x, self._y + self._length)
        axis.strokeColor = self.strokeColor
        axis.strokeWidth = self.strokeWidth
        axis.strokeDashArray = self.strokeDashArray
        g.add(axis)

        return g

    def makeTicks(self):
        g = Group()
        if self.visibleTicks and (self.tickLeft or self.tickRight):
            self._makeLines(g,-self.tickLeft,self.tickRight,self.strokeColor,self.strokeWidth,self.strokeDashArray)
        return g

class AdjYValueAxis(YValueAxis):
    """A Y-axis applying additional rules.

    Depending on the data and some built-in rules, the axis
    may choose to adjust its range and origin.
    """
    _attrMap = AttrMap(BASE = YValueAxis,
        requiredRange = AttrMapValue(isNumberOrNone, desc='Minimum required value range.'),
        leftAxisPercent = AttrMapValue(isBoolean, desc='When true add percent sign to label values.'),
        leftAxisOrigShiftIPC = AttrMapValue(isNumber, desc='Lowest label shift interval ratio.'),
        leftAxisOrigShiftMin = AttrMapValue(isNumber, desc='Minimum amount to shift.'),
        leftAxisSkipLL0 = AttrMapValue(EitherOr((isBoolean,isListOfNumbers)), desc='Skip/Keep lowest tick label when true/false.\nOr skiplist')
        )

    def __init__(self):
        apply(YValueAxis.__init__, (self,))
        self.requiredRange = 30
        self.leftAxisPercent = 1
        self.leftAxisOrigShiftIPC = 0.15
        self.leftAxisOrigShiftMin = 12
        self.leftAxisSkipLL0 = 0
        self.valueSteps = None

    def _rangeAdjust(self):
        "Adjusts the value range of the axis."

        from reportlab.graphics.charts.utils import find_good_grid, ticks
        y_min, y_max = self._valueMin, self._valueMax
        m = self.maximumTicks
        n = filter(lambda x,m=m: x<=m,[4,5,6,7,8,9])
        if not n: n = [m]

        valueStep, requiredRange = self.valueStep, self.requiredRange
        if requiredRange and y_max - y_min < requiredRange:
            y1, y2 = find_good_grid(y_min, y_max,n=n,grid=valueStep)[:2]
            if y2 - y1 < requiredRange:
                ym = (y1+y2)*0.5
                y1 = min(ym-requiredRange*0.5,y_min)
                y2 = max(ym+requiredRange*0.5,y_max)
                if y_min>=100 and y1<100:
                    y2 = y2 + 100 - y1
                    y1 = 100
                elif y_min>=0 and y1<0:
                    y2 = y2 - y1
                    y1 = 0
            self._valueMin, self._valueMax = y1, y2

        T, L = ticks(self._valueMin, self._valueMax, split=1, n=n, percent=self.leftAxisPercent,grid=valueStep)
        abf = self.avoidBoundFrac
        if abf:
            i1 = (T[1]-T[0])
            if type(abf) not in (TupleType,ListType):
                i0 = i1 = i1*abf
            else:
                i0 = i1*abf[0]
                i1 = i1*abf[1]
            _n = getattr(self,'_cValueMin',T[0])
            _x = getattr(self,'_cValueMax',T[-1])
            if _n - T[0] < i0: self._valueMin = self._valueMin - i0
            if T[-1]-_x < i1: self._valueMax = self._valueMax + i1
            T, L = ticks(self._valueMin, self._valueMax, split=1, n=n, percent=self.leftAxisPercent,grid=valueStep)

        self._valueMin = T[0]
        self._valueMax = T[-1]
        self._tickValues = self.valueSteps = T
        if self.labelTextFormat is None:
            self._labelTextFormat = L
        else:
            self._labelTextFormat = self.labelTextFormat

        if abs(self._valueMin-100)<1e-6:
            self._calcValueStep()
            vMax, vMin = self._valueMax, self._valueMin
            m = max(self.leftAxisOrigShiftIPC*self._valueStep,
                    (vMax-vMin)*self.leftAxisOrigShiftMin/self._length)
            self._valueMin = self._valueMin - m

        if self.leftAxisSkipLL0:
            if type(self.leftAxisSkipLL0) in (ListType,TupleType):
                for x in self.leftAxisSkipLL0:
                    try:
                        L[x] = ''
                    except IndexError:
                        pass
            L[0] = ''

# Sample functions.
def sample0a():
    "Sample drawing with one xcat axis and two buckets."

    drawing = Drawing(400, 200)

    data = [(10, 20)]

    xAxis = XCategoryAxis()
    xAxis.setPosition(75, 75, 300)
    xAxis.configure(data)
    xAxis.categoryNames = ['Ying', 'Yang']
    xAxis.labels.boxAnchor = 'n'

    drawing.add(xAxis)

    return drawing


def sample0b():
    "Sample drawing with one xcat axis and one bucket only."

    drawing = Drawing(400, 200)

    data = [(10,)]

    xAxis = XCategoryAxis()
    xAxis.setPosition(75, 75, 300)
    xAxis.configure(data)
    xAxis.categoryNames = ['Ying']
    xAxis.labels.boxAnchor = 'n'

    drawing.add(xAxis)

    return drawing


def sample1():
    "Sample drawing containing two unconnected axes."

    drawing = Drawing(400, 200)

    data = [(10, 20, 30, 42)]

    xAxis = XCategoryAxis()
    xAxis.setPosition(75, 75, 300)
    xAxis.configure(data)
    xAxis.categoryNames = ['Beer','Wine','Meat','Cannelloni']
    xAxis.labels.boxAnchor = 'n'
    xAxis.labels[3].dy = -15
    xAxis.labels[3].angle = 30
    xAxis.labels[3].fontName = 'Times-Bold'

    yAxis = YValueAxis()
    yAxis.setPosition(50, 50, 125)
    yAxis.configure(data)
    drawing.add(xAxis)
    drawing.add(yAxis)

    return drawing


##def sample2a():
##  "Make sample drawing with two axes, x connected at top of y."
##
##    drawing = Drawing(400, 200)
##
##    data = [(10, 20, 30, 42)]
##
##    yAxis = YValueAxis()
##    yAxis.setPosition(50, 50, 125)
##    yAxis.configure(data)
##
##    xAxis = XCategoryAxis()
##    xAxis._length = 300
##    xAxis.configure(data)
##    xAxis.joinToAxis(yAxis, mode='top')
##    xAxis.categoryNames = ['Beer', 'Wine', 'Meat', 'Cannelloni']
##    xAxis.labels.boxAnchor = 'n'
##
##    drawing.add(xAxis)
##    drawing.add(yAxis)
##
##    return drawing
##
##
##def sample2b():
##    "Make two axes, x connected at bottom of y."
##
##    drawing = Drawing(400, 200)
##
##    data = [(10, 20, 30, 42)]
##
##    yAxis = YValueAxis()
##    yAxis.setPosition(50, 50, 125)
##    yAxis.configure(data)
##
##    xAxis = XCategoryAxis()
##    xAxis._length = 300
##    xAxis.configure(data)
##    xAxis.joinToAxis(yAxis, mode='bottom')
##    xAxis.categoryNames = ['Beer', 'Wine', 'Meat', 'Cannelloni']
##    xAxis.labels.boxAnchor = 'n'
##
##    drawing.add(xAxis)
##    drawing.add(yAxis)
##
##    return drawing
##
##
##def sample2c():
##    "Make two axes, x connected at fixed value (in points) of y."
##
##    drawing = Drawing(400, 200)
##
##    data = [(10, 20, 30, 42)]
##
##    yAxis = YValueAxis()
##    yAxis.setPosition(50, 50, 125)
##    yAxis.configure(data)
##
##    xAxis = XCategoryAxis()
##    xAxis._length = 300
##    xAxis.configure(data)
##    xAxis.joinToAxis(yAxis, mode='points', pos=100)
##    xAxis.categoryNames = ['Beer', 'Wine', 'Meat', 'Cannelloni']
##    xAxis.labels.boxAnchor = 'n'
##
##    drawing.add(xAxis)
##    drawing.add(yAxis)
##
##    return drawing
##
##
##def sample2d():
##    "Make two axes, x connected at fixed value (of y-axes) of y."
##
##    drawing = Drawing(400, 200)
##
##    data = [(10, 20, 30, 42)]
##
##    yAxis = YValueAxis()
##    yAxis.setPosition(50, 50, 125)
##    yAxis.configure(data)
##
##    xAxis = XCategoryAxis()
##    xAxis._length = 300
##    xAxis.configure(data)
##    xAxis.joinToAxis(yAxis, mode='value', pos=20)
##    xAxis.categoryNames = ['Beer', 'Wine', 'Meat', 'Cannelloni']
##    xAxis.labels.boxAnchor = 'n'
##
##    drawing.add(xAxis)
##    drawing.add(yAxis)
##
##    return drawing
##
##
##def sample3a():
##    "Make sample drawing with two axes, y connected at left of x."
##
##    drawing = Drawing(400, 200)
##
##    data = [(10, 20, 30, 42)]
##
##    xAxis = XCategoryAxis()
##    xAxis._length = 300
##    xAxis.configure(data)
##    xAxis.categoryNames = ['Beer', 'Wine', 'Meat', 'Cannelloni']
##    xAxis.labels.boxAnchor = 'n'
##
##    yAxis = YValueAxis()
##    yAxis.setPosition(50, 50, 125)
##    yAxis.configure(data)
##    yAxis.joinToAxis(xAxis, mode='left')
##
##    drawing.add(xAxis)
##    drawing.add(yAxis)
##
##    return drawing
##
##
##def sample3b():
##    "Make sample drawing with two axes, y connected at right of x."
##
##    drawing = Drawing(400, 200)
##
##    data = [(10, 20, 30, 42)]
##
##    xAxis = XCategoryAxis()
##    xAxis._length = 300
##    xAxis.configure(data)
##    xAxis.categoryNames = ['Beer', 'Wine', 'Meat', 'Cannelloni']
##    xAxis.labels.boxAnchor = 'n'
##
##    yAxis = YValueAxis()
##    yAxis.setPosition(50, 50, 125)
##    yAxis.configure(data)
##    yAxis.joinToAxis(xAxis, mode='right')
##
##    drawing.add(xAxis)
##    drawing.add(yAxis)
##
##    return drawing
##
##
##def sample3c():
##    "Make two axes, y connected at fixed value (in points) of x."
##
##    drawing = Drawing(400, 200)
##
##    data = [(10, 20, 30, 42)]
##
##    yAxis = YValueAxis()
##    yAxis.setPosition(50, 50, 125)
##    yAxis.configure(data)
##
##    xAxis = XValueAxis()
##    xAxis._length = 300
##    xAxis.configure(data)
##    xAxis.joinToAxis(yAxis, mode='points', pos=100)
##
##    drawing.add(xAxis)
##    drawing.add(yAxis)
##
##    return drawing


def sample4a():
    "Sample drawing, xvalue/yvalue axes, y connected at 100 pts to x."

    drawing = Drawing(400, 200)

    data = [(10, 20, 30, 42)]

    yAxis = YValueAxis()
    yAxis.setPosition(50, 50, 125)
    yAxis.configure(data)

    xAxis = XValueAxis()
    xAxis._length = 300
    xAxis.joinAxis = yAxis
    xAxis.joinAxisMode = 'points'
    xAxis.joinAxisPos = 100
    xAxis.configure(data)

    drawing.add(xAxis)
    drawing.add(yAxis)

    return drawing


def sample4b():
    "Sample drawing, xvalue/yvalue axes, y connected at value 35 of x."

    drawing = Drawing(400, 200)

    data = [(10, 20, 30, 42)]

    yAxis = YValueAxis()
    yAxis.setPosition(50, 50, 125)
    yAxis.configure(data)

    xAxis = XValueAxis()
    xAxis._length = 300
    xAxis.joinAxis = yAxis
    xAxis.joinAxisMode = 'value'
    xAxis.joinAxisPos = 35
    xAxis.configure(data)

    drawing.add(xAxis)
    drawing.add(yAxis)

    return drawing


def sample4c():
    "Sample drawing, xvalue/yvalue axes, y connected to bottom of x."

    drawing = Drawing(400, 200)

    data = [(10, 20, 30, 42)]

    yAxis = YValueAxis()
    yAxis.setPosition(50, 50, 125)
    yAxis.configure(data)

    xAxis = XValueAxis()
    xAxis._length = 300
    xAxis.joinAxis = yAxis
    xAxis.joinAxisMode = 'bottom'
    xAxis.configure(data)

    drawing.add(xAxis)
    drawing.add(yAxis)

    return drawing


def sample4c1():
    "xvalue/yvalue axes, without drawing axis lines/ticks."

    drawing = Drawing(400, 200)

    data = [(10, 20, 30, 42)]

    yAxis = YValueAxis()
    yAxis.setPosition(50, 50, 125)
    yAxis.configure(data)
    yAxis.visibleAxis = 0
    yAxis.visibleTicks = 0

    xAxis = XValueAxis()
    xAxis._length = 300
    xAxis.joinAxis = yAxis
    xAxis.joinAxisMode = 'bottom'
    xAxis.configure(data)
    xAxis.visibleAxis = 0
    xAxis.visibleTicks = 0

    drawing.add(xAxis)
    drawing.add(yAxis)

    return drawing


def sample4d():
    "Sample drawing, xvalue/yvalue axes, y connected to top of x."

    drawing = Drawing(400, 200)

    data = [(10, 20, 30, 42)]

    yAxis = YValueAxis()
    yAxis.setPosition(50, 50, 125)
    yAxis.configure(data)

    xAxis = XValueAxis()
    xAxis._length = 300
    xAxis.joinAxis = yAxis
    xAxis.joinAxisMode = 'top'
    xAxis.configure(data)

    drawing.add(xAxis)
    drawing.add(yAxis)

    return drawing


def sample5a():
    "Sample drawing, xvalue/yvalue axes, y connected at 100 pts to x."

    drawing = Drawing(400, 200)

    data = [(10, 20, 30, 42)]

    xAxis = XValueAxis()
    xAxis.setPosition(50, 50, 300)
    xAxis.configure(data)

    yAxis = YValueAxis()
    yAxis.setPosition(50, 50, 125)
    yAxis.joinAxis = xAxis
    yAxis.joinAxisMode = 'points'
    yAxis.joinAxisPos = 100
    yAxis.configure(data)

    drawing.add(xAxis)
    drawing.add(yAxis)

    return drawing


def sample5b():
    "Sample drawing, xvalue/yvalue axes, y connected at value 35 of x."

    drawing = Drawing(400, 200)

    data = [(10, 20, 30, 42)]

    xAxis = XValueAxis()
    xAxis.setPosition(50, 50, 300)
    xAxis.configure(data)

    yAxis = YValueAxis()
    yAxis.setPosition(50, 50, 125)
    yAxis.joinAxis = xAxis
    yAxis.joinAxisMode = 'value'
    yAxis.joinAxisPos = 35
    yAxis.configure(data)

    drawing.add(xAxis)
    drawing.add(yAxis)

    return drawing


def sample5c():
    "Sample drawing, xvalue/yvalue axes, y connected at right of x."

    drawing = Drawing(400, 200)

    data = [(10, 20, 30, 42)]

    xAxis = XValueAxis()
    xAxis.setPosition(50, 50, 300)
    xAxis.configure(data)

    yAxis = YValueAxis()
    yAxis.setPosition(50, 50, 125)
    yAxis.joinAxis = xAxis
    yAxis.joinAxisMode = 'right'
    yAxis.configure(data)

    drawing.add(xAxis)
    drawing.add(yAxis)

    return drawing


def sample5d():
    "Sample drawing, xvalue/yvalue axes, y connected at left of x."

    drawing = Drawing(400, 200)

    data = [(10, 20, 30, 42)]

    xAxis = XValueAxis()
    xAxis.setPosition(50, 50, 300)
    xAxis.configure(data)

    yAxis = YValueAxis()
    yAxis.setPosition(50, 50, 125)
    yAxis.joinAxis = xAxis
    yAxis.joinAxisMode = 'left'
    yAxis.configure(data)

    drawing.add(xAxis)
    drawing.add(yAxis)

    return drawing


def sample6a():
    "Sample drawing, xcat/yvalue axes, x connected at top of y."

    drawing = Drawing(400, 200)

    data = [(10, 20, 30, 42)]

    yAxis = YValueAxis()
    yAxis.setPosition(50, 50, 125)
    yAxis.configure(data)

    xAxis = XCategoryAxis()
    xAxis._length = 300
    xAxis.configure(data)
    xAxis.joinAxis = yAxis
    xAxis.joinAxisMode = 'top'
    xAxis.categoryNames = ['Beer', 'Wine', 'Meat', 'Cannelloni']
    xAxis.labels.boxAnchor = 'n'

    drawing.add(xAxis)
    drawing.add(yAxis)

    return drawing


def sample6b():
    "Sample drawing, xcat/yvalue axes, x connected at bottom of y."

    drawing = Drawing(400, 200)

    data = [(10, 20, 30, 42)]

    yAxis = YValueAxis()
    yAxis.setPosition(50, 50, 125)
    yAxis.configure(data)

    xAxis = XCategoryAxis()
    xAxis._length = 300
    xAxis.configure(data)
    xAxis.joinAxis = yAxis
    xAxis.joinAxisMode = 'bottom'
    xAxis.categoryNames = ['Beer', 'Wine', 'Meat', 'Cannelloni']
    xAxis.labels.boxAnchor = 'n'

    drawing.add(xAxis)
    drawing.add(yAxis)

    return drawing


def sample6c():
    "Sample drawing, xcat/yvalue axes, x connected at 100 pts to y."

    drawing = Drawing(400, 200)

    data = [(10, 20, 30, 42)]

    yAxis = YValueAxis()
    yAxis.setPosition(50, 50, 125)
    yAxis.configure(data)

    xAxis = XCategoryAxis()
    xAxis._length = 300
    xAxis.configure(data)
    xAxis.joinAxis = yAxis
    xAxis.joinAxisMode = 'points'
    xAxis.joinAxisPos = 100
    xAxis.categoryNames = ['Beer', 'Wine', 'Meat', 'Cannelloni']
    xAxis.labels.boxAnchor = 'n'

    drawing.add(xAxis)
    drawing.add(yAxis)

    return drawing


def sample6d():
    "Sample drawing, xcat/yvalue axes, x connected at value 20 of y."

    drawing = Drawing(400, 200)

    data = [(10, 20, 30, 42)]

    yAxis = YValueAxis()
    yAxis.setPosition(50, 50, 125)
    yAxis.configure(data)

    xAxis = XCategoryAxis()
    xAxis._length = 300
    xAxis.configure(data)
    xAxis.joinAxis = yAxis
    xAxis.joinAxisMode = 'value'
    xAxis.joinAxisPos = 20
    xAxis.categoryNames = ['Beer', 'Wine', 'Meat', 'Cannelloni']
    xAxis.labels.boxAnchor = 'n'

    drawing.add(xAxis)
    drawing.add(yAxis)

    return drawing


def sample7a():
    "Sample drawing, xvalue/ycat axes, y connected at right of x."

    drawing = Drawing(400, 200)

    data = [(10, 20, 30, 42)]

    xAxis = XValueAxis()
    xAxis._length = 300
    xAxis.configure(data)

    yAxis = YCategoryAxis()
    yAxis.setPosition(50, 50, 125)
    yAxis.joinAxis = xAxis
    yAxis.joinAxisMode = 'right'
    yAxis.categoryNames = ['Beer', 'Wine', 'Meat', 'Cannelloni']
    yAxis.labels.boxAnchor = 'e'
    yAxis.configure(data)

    drawing.add(xAxis)
    drawing.add(yAxis)

    return drawing


def sample7b():
    "Sample drawing, xvalue/ycat axes, y connected at left of x."

    drawing = Drawing(400, 200)

    data = [(10, 20, 30, 42)]

    xAxis = XValueAxis()
    xAxis._length = 300
    xAxis.configure(data)

    yAxis = YCategoryAxis()
    yAxis.setPosition(50, 50, 125)
    yAxis.joinAxis = xAxis
    yAxis.joinAxisMode = 'left'
    yAxis.categoryNames = ['Beer', 'Wine', 'Meat', 'Cannelloni']
    yAxis.labels.boxAnchor = 'e'
    yAxis.configure(data)

    drawing.add(xAxis)
    drawing.add(yAxis)

    return drawing


def sample7c():
    "Sample drawing, xvalue/ycat axes, y connected at value 30 of x."

    drawing = Drawing(400, 200)

    data = [(10, 20, 30, 42)]

    xAxis = XValueAxis()
    xAxis._length = 300
    xAxis.configure(data)

    yAxis = YCategoryAxis()
    yAxis.setPosition(50, 50, 125)
    yAxis.joinAxis = xAxis
    yAxis.joinAxisMode = 'value'
    yAxis.joinAxisPos = 30
    yAxis.categoryNames = ['Beer', 'Wine', 'Meat', 'Cannelloni']
    yAxis.labels.boxAnchor = 'e'
    yAxis.configure(data)

    drawing.add(xAxis)
    drawing.add(yAxis)

    return drawing


def sample7d():
    "Sample drawing, xvalue/ycat axes, y connected at 200 pts to x."

    drawing = Drawing(400, 200)

    data = [(10, 20, 30, 42)]

    xAxis = XValueAxis()
    xAxis._length = 300
    xAxis.configure(data)

    yAxis = YCategoryAxis()
    yAxis.setPosition(50, 50, 125)
    yAxis.joinAxis = xAxis
    yAxis.joinAxisMode = 'points'
    yAxis.joinAxisPos = 200
    yAxis.categoryNames = ['Beer', 'Wine', 'Meat', 'Cannelloni']
    yAxis.labels.boxAnchor = 'e'
    yAxis.configure(data)

    drawing.add(xAxis)
    drawing.add(yAxis)

    return drawing
