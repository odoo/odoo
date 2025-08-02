#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/graphics/charts/textlabels.py
__version__='3.3.0'

from reportlab.lib import colors
from reportlab.lib.utils import simpleSplit
from reportlab.lib.validators import isNumber, isNumberOrNone, OneOf, isColorOrNone, isString, \
        isTextAnchor, isBoxAnchor, isBoolean, NoneOr, isInstanceOf, isNoneOrString, isNoneOrCallable, \
        isSubclassOf
from reportlab.lib.attrmap import *
from reportlab.pdfbase.pdfmetrics import stringWidth, getAscentDescent
from reportlab.graphics.shapes import Drawing, Group, Circle, Rect, String, STATE_DEFAULTS
from reportlab.graphics.widgetbase import Widget, PropHolder
from reportlab.graphics.shapes import DirectDraw
from reportlab.platypus import XPreformatted, Flowable
from reportlab.lib.styles import ParagraphStyle, PropertySet
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
_ta2al = dict(start=TA_LEFT,end=TA_RIGHT,middle=TA_CENTER)
from ..utils import text2Path as _text2Path   #here for continuity

_A2BA=  {
        'x': {0:'n', 45:'ne', 90:'e', 135:'se', 180:'s', 225:'sw', 270:'w', 315: 'nw', -45: 'nw'},
        'y': {0:'e', 45:'se', 90:'s', 135:'sw', 180:'w', 225:'nw', 270:'n', 315: 'ne', -45: 'ne'},
        }

try:
    from rlextra.graphics.canvasadapter import DirectDrawFlowable
except ImportError:
    DirectDrawFlowable = None

_BA2TA={'w':'start','nw':'start','sw':'start','e':'end', 'ne': 'end', 'se':'end', 'n':'middle','s':'middle','c':'middle'}
class Label(Widget):
    """A text label to attach to something else, such as a chart axis.

    This allows you to specify an offset, angle and many anchor
    properties relative to the label's origin.  It allows, for example,
    angled multiline axis labels.
    """
    # fairly straight port of Robin Becker's textbox.py to new widgets
    # framework.

    _attrMap = AttrMap(
        x = AttrMapValue(isNumber,desc=''),
        y = AttrMapValue(isNumber,desc=''),
        dx = AttrMapValue(isNumber,desc='delta x - offset'),
        dy = AttrMapValue(isNumber,desc='delta y - offset'),
        angle = AttrMapValue(isNumber,desc='angle of label: default (0), 90 is vertical, 180 is upside down, etc'),
        boxAnchor = AttrMapValue(isBoxAnchor,desc='anchoring point of the label'),
        boxStrokeColor = AttrMapValue(isColorOrNone,desc='border color of the box'),
        boxStrokeWidth = AttrMapValue(isNumber,desc='border width'),
        boxFillColor = AttrMapValue(isColorOrNone,desc='the filling color of the box'),
        boxTarget = AttrMapValue(OneOf('normal','anti','lo','hi'),desc="one of ('normal','anti','lo','hi')"),
        fillColor = AttrMapValue(isColorOrNone,desc='label text color'),
        strokeColor = AttrMapValue(isColorOrNone,desc='label text border color'),
        strokeWidth = AttrMapValue(isNumber,desc='label text border width'),
        text = AttrMapValue(isString,desc='the actual text to display'),
        fontName = AttrMapValue(isString,desc='the name of the font used'),
        fontSize = AttrMapValue(isNumber,desc='the size of the font'),
        leading = AttrMapValue(isNumberOrNone,desc=''),
        width = AttrMapValue(isNumberOrNone,desc='the width of the label'),
        maxWidth = AttrMapValue(isNumberOrNone,desc='maximum width the label can grow to'),
        height = AttrMapValue(isNumberOrNone,desc='the height of the text'),
        textAnchor = AttrMapValue(isTextAnchor,desc='the anchoring point of the text inside the label'),
        visible = AttrMapValue(isBoolean,desc="True if the label is to be drawn"),
        topPadding = AttrMapValue(isNumber,desc='padding at top of box'),
        leftPadding = AttrMapValue(isNumber,desc='padding at left of box'),
        rightPadding = AttrMapValue(isNumber,desc='padding at right of box'),
        bottomPadding = AttrMapValue(isNumber,desc='padding at bottom of box'),
        useAscentDescent = AttrMapValue(isBoolean,desc="If True then the font's Ascent & Descent will be used to compute default heights and baseline."),
        customDrawChanger = AttrMapValue(isNoneOrCallable,desc="An instance of CustomDrawChanger to modify the behavior at draw time", _advancedUsage=1),
        ddf = AttrMapValue(NoneOr(isSubclassOf(DirectDraw),'NoneOrDirectDraw'),desc="A DirectDrawFlowable instance", _advancedUsage=1),
        ddfKlass = AttrMapValue(NoneOr(isSubclassOf(Flowable),'NoneOrDirectDraw'),desc="A Flowable class for direct drawing (default is XPreformatted", _advancedUsage=1),
        ddfStyle = AttrMapValue(NoneOr((isSubclassOf(PropertySet),isInstanceOf(PropertySet))),desc="A style or style class for a ddfKlass or None", _advancedUsage=1),
        )

    def __init__(self,**kw):
        self._setKeywords(**kw)
        self._setKeywords(
                _text = 'Multi-Line\nString',
                boxAnchor = 'c',
                angle = 0,
                x = 0,
                y = 0,
                dx = 0,
                dy = 0,
                topPadding = 0,
                leftPadding = 0,
                rightPadding = 0,
                bottomPadding = 0,
                boxStrokeWidth = 0.5,
                boxStrokeColor = None,
                boxTarget = 'normal',
                strokeColor = None,
                boxFillColor = None,
                leading = None,
                width = None,
                maxWidth = None,
                height = None,
                fillColor = STATE_DEFAULTS['fillColor'],
                fontName = STATE_DEFAULTS['fontName'],
                fontSize = STATE_DEFAULTS['fontSize'],
                strokeWidth = 0.1,
                textAnchor = 'start',
                visible = 1,
                useAscentDescent = False,
                ddf = DirectDrawFlowable,
                ddfKlass = None,
                ddfStyle = None,
                )

    def setText(self, text):
        """Set the text property.  May contain embedded newline characters.
        Called by the containing chart or axis."""
        self._text = text


    def setOrigin(self, x, y):
        """Set the origin.  This would be the tick mark or bar top relative to
        which it is defined.  Called by the containing chart or axis."""
        self.x = x
        self.y = y


    def demo(self):
        """This shows a label positioned with its top right corner
        at the top centre of the drawing, and rotated 45 degrees."""

        d = Drawing(200, 100)

        # mark the origin of the label
        d.add(Circle(100,90, 5, fillColor=colors.green))

        lab = Label()
        lab.setOrigin(100,90)
        lab.boxAnchor = 'ne'
        lab.angle = 45
        lab.dx = 0
        lab.dy = -20
        lab.boxStrokeColor = colors.green
        lab.setText('Another\nMulti-Line\nString')
        d.add(lab)

        return d

    def _getBoxAnchor(self):
        '''hook for allowing special box anchor effects'''
        ba = self.boxAnchor
        if ba in ('autox', 'autoy'):
            angle = self.angle
            na = (int((angle%360)/45.)*45)%360
            if not (na % 90): # we have a right angle case
                da = (angle - na) % 360
                if abs(da)>5:
                    na = na + (da>0 and 45 or -45)
            ba = _A2BA[ba[-1]][na]
        return ba

    def _getBaseLineRatio(self):
        if self.useAscentDescent:
            self._ascent, self._descent = getAscentDescent(self.fontName,self.fontSize)
            self._baselineRatio = self._ascent/(self._ascent-self._descent)
        else:
            self._baselineRatio = 1/1.2

    def _computeSizeEnd(self,objH):
        self._height = self.height or (objH + self.topPadding + self.bottomPadding)
        self._ewidth = (self._width-self.leftPadding-self.rightPadding)
        self._eheight = (self._height-self.topPadding-self.bottomPadding)
        boxAnchor = self._getBoxAnchor()
        if boxAnchor in ['n','ne','nw']:
            self._top = -self.topPadding
        elif boxAnchor in ['s','sw','se']:
            self._top = self._height-self.topPadding
        else:
            self._top = 0.5*self._eheight
        self._bottom = self._top - self._eheight

        if boxAnchor in ['ne','e','se']:
            self._left = self.leftPadding - self._width
        elif boxAnchor in ['nw','w','sw']:
            self._left = self.leftPadding
        else:
            self._left = -self._ewidth*0.5
        self._right = self._left+self._ewidth

    def computeSize(self):
        # the thing will draw in its own coordinate system
        ddfKlass = getattr(self,'ddfKlass',None)
        if not ddfKlass:
            self._lineWidths = []
            self._lines = simpleSplit(self._text,self.fontName,self.fontSize,self.maxWidth)
            if not self.width:
                self._width = self.leftPadding+self.rightPadding
                if self._lines:
                    self._lineWidths = [stringWidth(line,self.fontName,self.fontSize) for line in self._lines]
                    self._width += max(self._lineWidths)
            else:
                self._width = self.width
            self._getBaseLineRatio()
            if self.leading:
                self._leading = self.leading
            elif self.useAscentDescent:
                self._leading = self._ascent - self._descent
            else:
                self._leading = self.fontSize*1.2
            objH = self._leading*len(self._lines)
        else:
            if self.ddf is None:
                raise RuntimeError('DirectDrawFlowable class is not available you need the rlextra package as well as reportlab')
            sty = dict(
                    name='xlabel-generated',
                    fontName=self.fontName,
                    fontSize=self.fontSize,
                    fillColor=self.fillColor,
                    strokeColor=self.strokeColor,
                    )

            if not self.ddfStyle:
                sty = ParagraphStyle(**sty)
            elif issubclass(self.ddfStyle,PropertySet):
                sty = self.ddfStyle(**sty)
            else:
                sty = self.ddfStyle.clone()

            self._style = sty
            self._getBaseLineRatio()
            if self.useAscentDescent:
                sty.autoLeading = True
                sty.leading = self._ascent - self._descent
            else:
                sty.leading = self.leading if self.leading else self.fontSize*1.2
            self._leading = sty.leading
            ta = self._getTextAnchor()
            aW = self.maxWidth or 0x7fffffff
            if ta!='start':
                sty.alignment = TA_LEFT
                obj = ddfKlass(self._text,style=sty)
                _, objH = obj.wrap(aW,0x7fffffff)
                aW = self.maxWidth or obj._width_max
            sty.alignment = _ta2al[ta]
            self._ddfObj = obj = ddfKlass(self._text,style=sty)
            _, objH = obj.wrap(aW,0x7fffffff)

            if not self.width:
                self._width = self.leftPadding+self.rightPadding
                self._width += obj._width_max
            else:
                self._width = self.width
        self._computeSizeEnd(objH)

    def _getTextAnchor(self):
        '''This can be overridden to allow special effects'''
        ta = self.textAnchor
        if ta=='boxauto': ta = _BA2TA[self._getBoxAnchor()]
        return ta

    def _rawDraw(self):
        _text = self._text
        self._text = _text or ''
        self.computeSize()
        self._text = _text
        g = Group()
        g.translate(self.x + self.dx, self.y + self.dy)
        g.rotate(self.angle)

        ddfKlass = getattr(self,'ddfKlass',None)
        if ddfKlass:
            x = self._left
        else:
            y = self._top - self._leading*self._baselineRatio
            textAnchor = self._getTextAnchor()
            if textAnchor == 'start':
                x = self._left
            elif textAnchor == 'middle':
                x = self._left + self._ewidth*0.5
            else:
                x = self._right

        # paint box behind text just in case they
        # fill it
        if self.boxFillColor or (self.boxStrokeColor and self.boxStrokeWidth):
            g.add(Rect( self._left-self.leftPadding,
                        self._bottom-self.bottomPadding,
                        self._width,
                        self._height,
                        strokeColor=self.boxStrokeColor,
                        strokeWidth=self.boxStrokeWidth,
                        fillColor=self.boxFillColor)
                        )

        if ddfKlass:
            g1 = Group()
            g1.translate(x,self._top-self._eheight)
            g1.add(self.ddf(self._ddfObj))
            g.add(g1)
        else:
            fillColor, fontName, fontSize = self.fillColor, self.fontName, self.fontSize
            strokeColor, strokeWidth, leading = self.strokeColor, self.strokeWidth, self._leading
            svgAttrs=getattr(self,'_svgAttrs',{})
            if strokeColor:
                for line in self._lines:
                    s = _text2Path(line, x, y, fontName, fontSize, textAnchor)
                    s.fillColor = fillColor
                    s.strokeColor = strokeColor
                    s.strokeWidth = strokeWidth
                    g.add(s)
                    y -= leading
            else:
                for line in self._lines:
                    s = String(x, y, line, _svgAttrs=svgAttrs)
                    s.textAnchor = textAnchor
                    s.fontName = fontName
                    s.fontSize = fontSize
                    s.fillColor = fillColor
                    g.add(s)
                    y -= leading

        return g

    def draw(self):
        customDrawChanger = getattr(self,'customDrawChanger',None)
        if customDrawChanger:
            customDrawChanger(True,self)
            try:
                return self._rawDraw()
            finally:
                customDrawChanger(False,self)
        else:
            return self._rawDraw()

class LabelDecorator:
    _attrMap = AttrMap(
        x = AttrMapValue(isNumberOrNone,desc=''),
        y = AttrMapValue(isNumberOrNone,desc=''),
        dx = AttrMapValue(isNumberOrNone,desc=''),
        dy = AttrMapValue(isNumberOrNone,desc=''),
        angle = AttrMapValue(isNumberOrNone,desc=''),
        boxAnchor = AttrMapValue(isBoxAnchor,desc=''),
        boxStrokeColor = AttrMapValue(isColorOrNone,desc=''),
        boxStrokeWidth = AttrMapValue(isNumberOrNone,desc=''),
        boxFillColor = AttrMapValue(isColorOrNone,desc=''),
        fillColor = AttrMapValue(isColorOrNone,desc=''),
        strokeColor = AttrMapValue(isColorOrNone,desc=''),
        strokeWidth = AttrMapValue(isNumberOrNone),desc='',
        fontName = AttrMapValue(isNoneOrString,desc=''),
        fontSize = AttrMapValue(isNumberOrNone,desc=''),
        leading = AttrMapValue(isNumberOrNone,desc=''),
        width = AttrMapValue(isNumberOrNone,desc=''),
        maxWidth = AttrMapValue(isNumberOrNone,desc=''),
        height = AttrMapValue(isNumberOrNone,desc=''),
        textAnchor = AttrMapValue(isTextAnchor,desc=''),
        visible = AttrMapValue(isBoolean,desc="True if the label is to be drawn"),
        )

    def __init__(self):
        self.textAnchor = 'start'
        self.boxAnchor = 'w'
        for a in self._attrMap.keys():
            if not hasattr(self,a): setattr(self,a,None)

    def decorate(self,l,L):
        chart,g,rowNo,colNo,x,y,width,height,x00,y00,x0,y0 = l._callOutInfo
        L.setText(chart.categoryAxis.categoryNames[colNo])
        g.add(L)

    def __call__(self,l):
        L = Label()
        for a,v in self.__dict__.items():
            if v is None: v = getattr(l,a,None)
            setattr(L,a,v)
        self.decorate(l,L)

isOffsetMode=OneOf('high','low','bar','axis')
class LabelOffset(PropHolder):
    _attrMap = AttrMap(
                posMode = AttrMapValue(isOffsetMode,desc="Where to base +ve offset"),
                pos = AttrMapValue(isNumber,desc='Value for positive elements'),
                negMode = AttrMapValue(isOffsetMode,desc="Where to base -ve offset"),
                neg = AttrMapValue(isNumber,desc='Value for negative elements'),
                )
    def __init__(self):
        self.posMode=self.negMode='axis'
        self.pos = self.neg = 0

    def _getValue(self, chart, val):
        flipXY = chart._flipXY
        A = chart.categoryAxis
        jA = A.joinAxis
        if val>=0:
            mode = self.posMode
            delta = self.pos
        else:
            mode = self.negMode
            delta = self.neg
        if flipXY:
            v = A._x
        else:
            v = A._y
        if jA:
            if flipXY:
                _v = jA._x
            else:
                _v = jA._y
            if mode=='high':
                v = _v + jA._length
            elif mode=='low':
                v = _v
            elif mode=='bar':
                v = _v+val
        return v+delta

NoneOrInstanceOfLabelOffset=NoneOr(isInstanceOf(LabelOffset))

class PMVLabel(Label):
    _attrMap = AttrMap(
        BASE=Label,
        )

    def __init__(self, **kwds):
        Label.__init__(self, **kwds)
        self._pmv = 0

    def _getBoxAnchor(self):
        a = Label._getBoxAnchor(self)
        if self._pmv<0: a = {'nw':'se','n':'s','ne':'sw','w':'e','c':'c','e':'w','sw':'ne','s':'n','se':'nw'}[a]
        return a

    def _getTextAnchor(self):
        a = Label._getTextAnchor(self)
        if self._pmv<0: a = {'start':'end', 'middle':'middle', 'end':'start'}[a]
        return a

class BarChartLabel(PMVLabel):
    """
    An extended Label allowing for nudging, lines visibility etc
    """
    _attrMap = AttrMap(
        BASE=PMVLabel,
        lineStrokeWidth = AttrMapValue(isNumberOrNone, desc="Non-zero for a drawn line"),
        lineStrokeColor = AttrMapValue(isColorOrNone, desc="Color for a drawn line"),
        fixedEnd = AttrMapValue(NoneOrInstanceOfLabelOffset, desc="None or fixed draw ends +/-"),
        fixedStart = AttrMapValue(NoneOrInstanceOfLabelOffset, desc="None or fixed draw starts +/-"),
        nudge = AttrMapValue(isNumber, desc="Non-zero sign dependent nudge"),
        boxTarget = AttrMapValue(OneOf('normal','anti','lo','hi','mid'),desc="one of ('normal','anti','lo','hi','mid')"),
        )

    def __init__(self, **kwds):
        PMVLabel.__init__(self, **kwds)
        self.lineStrokeWidth = 0
        self.lineStrokeColor = None
        self.fixedStart = self.fixedEnd = None
        self.nudge = 0

class NA_Label(BarChartLabel):
    """
    An extended Label allowing for nudging, lines visibility etc
    """
    _attrMap = AttrMap(
        BASE=BarChartLabel,
        text = AttrMapValue(isNoneOrString, desc="Text to be used for N/A values"),
        )
    def __init__(self):
        BarChartLabel.__init__(self)
        self.text = 'n/a'
NoneOrInstanceOfNA_Label=NoneOr(isInstanceOf(NA_Label))

from reportlab.graphics.charts.utils import CustomDrawChanger
class RedNegativeChanger(CustomDrawChanger):
    def __init__(self,fillColor=colors.red):
        CustomDrawChanger.__init__(self)
        self.fillColor = fillColor
    def _changer(self,obj):
        R = {}
        if obj._text.startswith('-'):
            R['fillColor'] = obj.fillColor
            obj.fillColor = self.fillColor
        return R

class XLabel(Label):
    '''like label but uses XPreFormatted/Paragraph to draw the _text'''
    _attrMap = AttrMap(BASE=Label,
            )
    def __init__(self,*args,**kwds):
        Label.__init__(self,*args,**kwds)
        self.ddfKlass = kwds.pop('ddfKlass',XPreformatted)
        self.ddf = kwds.pop('directDrawClass',self.ddf)

    if False:
        def __init__(self,*args,**kwds):
            self._flowableClass = kwds.pop('flowableClass',XPreformatted)
            ddf = kwds.pop('directDrawClass',DirectDrawFlowable)
            if ddf is None:
                raise RuntimeError('DirectDrawFlowable class is not available you need the rlextra package as well as reportlab')
            self._ddf = ddf
            Label.__init__(self,*args,**kwds)
        def computeSize(self):
            # the thing will draw in its own coordinate system
            self._lineWidths = []
            sty = self._style = ParagraphStyle('xlabel-generated',
                    fontName=self.fontName,
                    fontSize=self.fontSize,
                    fillColor=self.fillColor,
                    strokeColor=self.strokeColor,
                    )
            self._getBaseLineRatio()
            if self.useAscentDescent:
                sty.autoLeading = True
                sty.leading = self._ascent - self._descent
            else:
                sty.leading = self.leading if self.leading else self.fontSize*1.2
            self._leading = sty.leading
            ta = self._getTextAnchor()
            aW = self.maxWidth or 0x7fffffff
            if ta!='start':
                sty.alignment = TA_LEFT
                obj = self._flowableClass(self._text,style=sty)
                _, objH = obj.wrap(aW,0x7fffffff)
                aW = self.maxWidth or obj._width_max
            sty.alignment = _ta2al[ta]
            self._obj = obj = self._flowableClass(self._text,style=sty)
            _, objH = obj.wrap(aW,0x7fffffff)

            if not self.width:
                self._width = self.leftPadding+self.rightPadding
                self._width += self._obj._width_max
            else:
                self._width = self.width
            self._computeSizeEnd(objH)

        def _rawDraw(self):
            _text = self._text
            self._text = _text or ''
            self.computeSize()
            self._text = _text
            g = Group()
            g.translate(self.x + self.dx, self.y + self.dy)
            g.rotate(self.angle)

            x = self._left

            # paint box behind text just in case they
            # fill it
            if self.boxFillColor or (self.boxStrokeColor and self.boxStrokeWidth):
                g.add(Rect( self._left-self.leftPadding,
                            self._bottom-self.bottomPadding,
                            self._width,
                            self._height,
                            strokeColor=self.boxStrokeColor,
                            strokeWidth=self.boxStrokeWidth,
                            fillColor=self.boxFillColor)
                            )
            g1 = Group()
            g1.translate(x,self._top-self._eheight)
            g1.add(self._ddf(self._obj))
            g.add(g1)
            return g
