#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/graphics/charts/textlabels.py
__version__=''' $Id: textlabels.py 2647 2005-07-26 13:47:51Z rgbecker $ '''
import string

from reportlab.lib import colors
from reportlab.lib.validators import isNumber, isNumberOrNone, OneOf, isColorOrNone, isString, \
        isTextAnchor, isBoxAnchor, isBoolean, NoneOr, isInstanceOf, isNoneOrString
from reportlab.lib.attrmap import *
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.graphics.shapes import Drawing, Group, Circle, Rect, String, STATE_DEFAULTS
from reportlab.graphics.shapes import _PATH_OP_ARG_COUNT, _PATH_OP_NAMES, definePath
from reportlab.graphics.widgetbase import Widget, PropHolder

_gs = None
_A2BA=  {
        'x': {0:'n', 45:'ne', 90:'e', 135:'se', 180:'s', 225:'sw', 270:'w', 315: 'nw', -45: 'nw'},
        'y': {0:'e', 45:'se', 90:'s', 135:'sw', 180:'w', 225:'nw', 270:'n', 315: 'ne', -45: 'ne'},
        }
def _simpleSplit(txt,mW,SW):
    L = []
    ws = SW(' ')
    O = []
    w = -ws
    for t in string.split(txt):
        lt = SW(t)
        if w+ws+lt<=mW or O==[]:
            O.append(t)
            w = w + ws + lt
        else:
            L.append(string.join(O,' '))
            O = [t]
            w = lt
    if O!=[]: L.append(string.join(O,' '))
    return L

def _pathNumTrunc(n):
    if int(n)==n: return int(n)
    return round(n,5)

def _processGlyph(G, truncate=1, pathReverse=0):
    O = []
    P = []
    R = []
    for g in G+(('end',),):
        op = g[0]
        if O and op in ['moveTo', 'moveToClosed','end']:
            if O[0]=='moveToClosed':
                O = O[1:]
                if pathReverse:
                    for i in xrange(0,len(P),2):
                        P[i+1], P[i] = P[i:i+2]
                    P.reverse()
                    O.reverse()
                O.insert(0,'moveTo')
                O.append('closePath')
            i = 0
            if truncate: P = map(_pathNumTrunc,P)
            for o in O:
                j = i + _PATH_OP_ARG_COUNT[_PATH_OP_NAMES.index(o)]
                if o=='closePath':
                    R.append(o)
                else:
                    R.append((o,)+ tuple(P[i:j]))
                i = j
            O = []
            P = []
        O.append(op)
        P.extend(g[1:])
    return R

def _text2PathDescription(text, x=0, y=0, fontName='Times-Roman', fontSize=1000,
                            anchor='start', truncate=1, pathReverse=0):
    global _gs
    if not _gs:
        import _renderPM
        _gs = _renderPM.gstate(1,1)
    from reportlab.graphics import renderPM
    renderPM._setFont(_gs,fontName,fontSize)
    P = []
    if not anchor =='start':
        textLen = stringWidth(text, fontName,fontSize)
        if text_anchor=='end':
            x = x-textLen
        elif text_anchor=='middle':
            x = x - textLen/2.
    for g in _gs._stringPath(text,x,y):
        P.extend(_processGlyph(g,truncate=truncate,pathReverse=pathReverse))
    return P

def _text2Path(text, x=0, y=0, fontName='Times-Roman', fontSize=1000,
                anchor='start', truncate=1, pathReverse=0):
    return definePath(_text2PathDescription(text,x=x,y=y,fontName=fontName,
                    fontSize=fontSize,anchor=anchor,truncate=truncate,pathReverse=pathReverse))

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
        x = AttrMapValue(isNumber),
        y = AttrMapValue(isNumber),
        dx = AttrMapValue(isNumber),
        dy = AttrMapValue(isNumber),
        angle = AttrMapValue(isNumber),
        boxAnchor = AttrMapValue(isBoxAnchor),
        boxStrokeColor = AttrMapValue(isColorOrNone),
        boxStrokeWidth = AttrMapValue(isNumber),
        boxFillColor = AttrMapValue(isColorOrNone),
        boxTarget = AttrMapValue(isString),
        fillColor = AttrMapValue(isColorOrNone),
        strokeColor = AttrMapValue(isColorOrNone),
        strokeWidth = AttrMapValue(isNumber),
        text = AttrMapValue(isString),
        fontName = AttrMapValue(isString),
        fontSize = AttrMapValue(isNumber),
        leading = AttrMapValue(isNumberOrNone),
        width = AttrMapValue(isNumberOrNone),
        maxWidth = AttrMapValue(isNumberOrNone),
        height = AttrMapValue(isNumberOrNone),
        textAnchor = AttrMapValue(isTextAnchor),
        visible = AttrMapValue(isBoolean,desc="True if the label is to be drawn"),
        topPadding = AttrMapValue(isNumber,'padding at top of box'),
        leftPadding = AttrMapValue(isNumber,'padding at left of box'),
        rightPadding = AttrMapValue(isNumber,'padding at right of box'),
        bottomPadding = AttrMapValue(isNumber,'padding at bottom of box'),
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

    def computeSize(self):
        # the thing will draw in its own coordinate system
        self._lines = string.split(self._text, '\n')
        self._lineWidths = []
        topPadding = self.topPadding
        leftPadding = self.leftPadding
        rightPadding = self.rightPadding
        bottomPadding = self.bottomPadding
        SW = lambda text, fN=self.fontName, fS=self.fontSize: stringWidth(text, fN, fS)
        if self.maxWidth:
            L = []
            for l in self._lines:
                L[-1:-1] = _simpleSplit(l,self.maxWidth,SW)
            self._lines = L
        if not self.width:
            w = 0
            for line in self._lines:
                thisWidth = SW(line)
                self._lineWidths.append(thisWidth)
                w = max(w,thisWidth)
            self._width = w+leftPadding+rightPadding
        else:
            self._width = self.width
        self._height = self.height or ((self.leading or 1.2*self.fontSize) * len(self._lines)+topPadding+bottomPadding)
        self._ewidth = (self._width-leftPadding-rightPadding)
        self._eheight = (self._height-topPadding-bottomPadding)
        boxAnchor = self._getBoxAnchor()
        if boxAnchor in ['n','ne','nw']:
            self._top = -topPadding
        elif boxAnchor in ['s','sw','se']:
            self._top = self._height-topPadding
        else:
            self._top = 0.5*self._eheight
        self._bottom = self._top - self._eheight

        if boxAnchor in ['ne','e','se']:
            self._left = leftPadding - self._width
        elif boxAnchor in ['nw','w','sw']:
            self._left = leftPadding
        else:
            self._left = -self._ewidth*0.5
        self._right = self._left+self._ewidth

    def _getTextAnchor(self):
        '''This can be overridden to allow special effects'''
        ta = self.textAnchor
        if ta=='boxauto': ta = _BA2TA[self._getBoxAnchor()]
        return ta

    def draw(self):
        _text = self._text
        self._text = _text or ''
        self.computeSize()
        self._text = _text
        g = Group()
        g.translate(self.x + self.dx, self.y + self.dy)
        g.rotate(self.angle)

        y = self._top - self.fontSize
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

        fillColor, fontName, fontSize = self.fillColor, self.fontName, self.fontSize
        strokeColor, strokeWidth, leading = self.strokeColor, self.strokeWidth, (self.leading or 1.2*fontSize)
        if strokeColor:
            for line in self._lines:
                s = _text2Path(line, x, y, fontName, fontSize, textAnchor)
                s.fillColor = fillColor
                s.strokeColor = strokeColor
                s.strokeWidth = strokeWidth
                g.add(s)
                y = y - leading
        else:
            for line in self._lines:
                s = String(x, y, line)
                s.textAnchor = textAnchor
                s.fontName = fontName
                s.fontSize = fontSize
                s.fillColor = fillColor
                g.add(s)
                y = y - leading

        return g

class LabelDecorator:
    _attrMap = AttrMap(
        x = AttrMapValue(isNumberOrNone),
        y = AttrMapValue(isNumberOrNone),
        dx = AttrMapValue(isNumberOrNone),
        dy = AttrMapValue(isNumberOrNone),
        angle = AttrMapValue(isNumberOrNone),
        boxAnchor = AttrMapValue(isBoxAnchor),
        boxStrokeColor = AttrMapValue(isColorOrNone),
        boxStrokeWidth = AttrMapValue(isNumberOrNone),
        boxFillColor = AttrMapValue(isColorOrNone),
        fillColor = AttrMapValue(isColorOrNone),
        strokeColor = AttrMapValue(isColorOrNone),
        strokeWidth = AttrMapValue(isNumberOrNone),
        fontName = AttrMapValue(isNoneOrString),
        fontSize = AttrMapValue(isNumberOrNone),
        leading = AttrMapValue(isNumberOrNone),
        width = AttrMapValue(isNumberOrNone),
        maxWidth = AttrMapValue(isNumberOrNone),
        height = AttrMapValue(isNumberOrNone),
        textAnchor = AttrMapValue(isTextAnchor),
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
        from copy import deepcopy
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

class BarChartLabel(Label):
    """
    An extended Label allowing for nudging, lines visibility etc
    """
    _attrMap = AttrMap(
        BASE=Label,
        lineStrokeWidth = AttrMapValue(isNumberOrNone, desc="Non-zero for a drawn line"),
        lineStrokeColor = AttrMapValue(isColorOrNone, desc="Color for a drawn line"),
        fixedEnd = AttrMapValue(NoneOrInstanceOfLabelOffset, desc="None or fixed draw ends +/-"),
        fixedStart = AttrMapValue(NoneOrInstanceOfLabelOffset, desc="None or fixed draw starts +/-"),
        nudge = AttrMapValue(isNumber, desc="Non-zero sign dependent nudge"),
        )

    def __init__(self):
        Label.__init__(self)
        self.lineStrokeWidth = 0
        self.lineStrokeColor = None
        self.nudge = 0
        self.fixedStart = self.fixedEnd = None
        self._pmv = 0

    def _getBoxAnchor(self):
        a = self.boxAnchor
        if self._pmv<0: a = {'nw':'se','n':'s','ne':'sw','w':'e','c':'c','e':'w','sw':'ne','s':'n','se':'nw'}[a]
        return a

    def _getTextAnchor(self):
        a = self.textAnchor
        if self._pmv<0: a = {'start':'end', 'middle':'middle', 'end':'start'}[a]
        return a

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
