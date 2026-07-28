#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/graphics/widgets/signsandsymbols.py
# signsandsymbols.py
# A collection of new widgets
# author: John Precedo (johnp@reportlab.com)

__version__='3.3.0'
__doc__="""This file is a collection of widgets to produce some common signs and symbols.

Widgets include:

- ETriangle (an equilateral triangle),
- RTriangle (a right angled triangle),
- Octagon,
- Crossbox,
- Tickbox,
- SmileyFace,
- StopSign,
- NoEntry,
- NotAllowed (the red roundel from 'no smoking' signs),
- NoSmoking,
- DangerSign (a black exclamation point in a yellow triangle),
- YesNo (returns a tickbox or a crossbox depending on a testvalue),
- FloppyDisk,
- ArrowOne, and
- ArrowTwo
- CrossHair
"""

from reportlab.lib import colors
from reportlab.lib.validators import *
from reportlab.lib.attrmap import *
from reportlab.lib.utils import isStr, asUnicode
from reportlab.graphics import shapes
from reportlab.graphics.widgetbase import Widget
from reportlab.graphics import renderPDF


class _Symbol(Widget):
    """Abstract base widget
    possible attributes:
    'x', 'y', 'size', 'fillColor', 'strokeColor'
    """
    _nodoc = 1
    _attrMap = AttrMap(
        x = AttrMapValue(isNumber,desc='symbol x coordinate'),
        y = AttrMapValue(isNumber,desc='symbol y coordinate'),
        dx = AttrMapValue(isNumber,desc='symbol x coordinate adjustment'),
        dy = AttrMapValue(isNumber,desc='symbol x coordinate adjustment'),
        size = AttrMapValue(isNumber),
        fillColor = AttrMapValue(isColorOrNone),
        strokeColor = AttrMapValue(isColorOrNone),
        strokeWidth = AttrMapValue(isNumber),
        )
    def __init__(self):
        assert self.__class__.__name__!='_Symbol', 'Abstract class _Symbol instantiated'
        self.x = self.y = self.dx = self.dy = 0
        self.size = 100
        self.fillColor = colors.red
        self.strokeColor = None
        self.strokeWidth = 0.1

    def demo(self):
        D = shapes.Drawing(200, 100)
        s = float(self.size)
        ob = self.__class__()
        ob.x=50
        ob.y=0
        ob.draw()
        D.add(ob)
        D.add(shapes.String(ob.x+(s/2),(ob.y-12),
                            ob.__class__.__name__, fillColor=colors.black, textAnchor='middle',
                            fontSize=10))
        return D

class ETriangle(_Symbol):
    """This draws an equilateral triangle."""

    def __init__(self):
        _Symbol.__init__(self)

    def draw(self):
        # general widget bits
        s = float(self.size)  # abbreviate as we will use this a lot
        g = shapes.Group()

        # Triangle specific bits
        ae = s*0.125            #(ae = 'an eighth')
        triangle = shapes.Polygon(points = [
            self.x, self.y,
            self.x+s, self.y,
            self.x+(s/2),self.y+s],
               fillColor = self.fillColor,
               strokeColor = self.strokeColor,
               strokeWidth=s/50.)
        g.add(triangle)
        return g

class RTriangle(_Symbol):
    """This draws a right-angled triangle.

        possible attributes:
        'x', 'y', 'size', 'fillColor', 'strokeColor'

        """

    def __init__(self):
        self.x = 0
        self.y = 0
        self.size = 100
        self.fillColor = colors.green
        self.strokeColor = None

    def draw(self):
        # general widget bits
        s = float(self.size)  # abbreviate as we will use this a lot
        g = shapes.Group()

        # Triangle specific bits
        ae = s*0.125            #(ae = 'an eighth')
        triangle = shapes.Polygon(points = [
            self.x, self.y,
            self.x+s, self.y,
            self.x,self.y+s],
               fillColor = self.fillColor,
               strokeColor = self.strokeColor,
               strokeWidth=s/50.)
        g.add(triangle)
        return g

class Octagon(_Symbol):
    """This widget draws an Octagon.

        possible attributes:
        'x', 'y', 'size', 'fillColor', 'strokeColor'

    """

    def __init__(self):
        self.x = 0
        self.y = 0
        self.size = 100
        self.fillColor = colors.yellow
        self.strokeColor = None

    def draw(self):
        # general widget bits
        s = float(self.size)  # abbreviate as we will use this a lot
        g = shapes.Group()

        # Octagon specific bits
        athird=s/3

        octagon = shapes.Polygon(points=[self.x+athird, self.y,
                                              self.x, self.y+athird,
                                              self.x, self.y+(athird*2),
                                              self.x+athird, self.y+s,
                                              self.x+(athird*2), self.y+s,
                                              self.x+s, self.y+(athird*2),
                                              self.x+s, self.y+athird,
                                              self.x+(athird*2), self.y],
                                      strokeColor = self.strokeColor,
                                      fillColor = self.fillColor,
                                      strokeWidth=10)
        g.add(octagon)
        return g

class Crossbox(_Symbol):
    """This draws a black box with a red cross in it - a 'checkbox'.

        possible attributes:
        'x', 'y', 'size', 'crossColor', 'strokeColor', 'crosswidth'

    """

    _attrMap = AttrMap(BASE=_Symbol,
        crossColor = AttrMapValue(isColorOrNone),
        crosswidth = AttrMapValue(isNumber),
        )

    def __init__(self):
        self.x = 0
        self.y = 0
        self.size = 100
        self.fillColor = colors.white
        self.crossColor = colors.red
        self.strokeColor = colors.black
        self.crosswidth = 10

    def draw(self):
        # general widget bits
        s = float(self.size)  # abbreviate as we will use this a lot
        g = shapes.Group()

        # crossbox specific bits
        box = shapes.Rect(self.x+1, self.y+1, s-2, s-2,
               fillColor = self.fillColor,
               strokeColor = self.strokeColor,
               strokeWidth=2)
        g.add(box)

        crossLine1 = shapes.Line(self.x+(s*0.15), self.y+(s*0.15), self.x+(s*0.85), self.y+(s*0.85),
               fillColor = self.crossColor,
               strokeColor = self.crossColor,
               strokeWidth = self.crosswidth)
        g.add(crossLine1)

        crossLine2 = shapes.Line(self.x+(s*0.15), self.y+(s*0.85), self.x+(s*0.85) ,self.y+(s*0.15),
               fillColor = self.crossColor,
               strokeColor = self.crossColor,
               strokeWidth = self.crosswidth)
        g.add(crossLine2)

        return g


class Tickbox(_Symbol):
    """This draws a black box with a red tick in it - another 'checkbox'.

        possible attributes:
        'x', 'y', 'size', 'tickColor', 'strokeColor', 'tickwidth'

"""

    _attrMap = AttrMap(BASE=_Symbol,
        tickColor = AttrMapValue(isColorOrNone),
        tickwidth = AttrMapValue(isNumber),
        )

    def __init__(self):
        self.x = 0
        self.y = 0
        self.size = 100
        self.tickColor = colors.red
        self.strokeColor = colors.black
        self.fillColor = colors.white
        self.tickwidth = 10

    def draw(self):
        # general widget bits
        s = float(self.size)  # abbreviate as we will use this a lot
        g = shapes.Group()

        # tickbox specific bits
        box = shapes.Rect(self.x+1, self.y+1, s-2, s-2,
               fillColor = self.fillColor,
               strokeColor = self.strokeColor,
               strokeWidth=2)
        g.add(box)

        tickLine = shapes.PolyLine(points = [self.x+(s*0.15), self.y+(s*0.35), self.x+(s*0.35), self.y+(s*0.15),
                                             self.x+(s*0.35), self.y+(s*0.15), self.x+(s*0.85) ,self.y+(s*0.85)],
               fillColor = self.tickColor,
               strokeColor = self.tickColor,
               strokeWidth = self.tickwidth)
        g.add(tickLine)

        return g

class SmileyFace(_Symbol):
    """This draws a classic smiley face.

        possible attributes:
        'x', 'y', 'size', 'fillColor'

    """

    def __init__(self):
        _Symbol.__init__(self)
        self.x = 0
        self.y = 0
        self.size = 100
        self.fillColor = colors.yellow
        self.strokeColor = colors.black

    def draw(self):
        # general widget bits
        s = float(self.size)  # abbreviate as we will use this a lot
        g = shapes.Group()

        # SmileyFace specific bits
        g.add(shapes.Circle(cx=self.x+(s/2), cy=self.y+(s/2), r=s/2,
                fillColor=self.fillColor, strokeColor=self.strokeColor,
                strokeWidth=max(s/38.,self.strokeWidth)))

        for i in (1,2):
            g.add(shapes.Ellipse(self.x+(s/3)*i,self.y+(s/3)*2, s/30, s/10,
                    fillColor=self.strokeColor, strokeColor = self.strokeColor,
                    strokeWidth=max(s/38.,self.strokeWidth)))

        # calculate a pointslist for the mouth
        # THIS IS A HACK! - don't use if there is a 'shapes.Arc'
        centerx=self.x+(s/2)
        centery=self.y+(s/2)
        radius=s/3
        yradius = radius
        xradius = radius
        startangledegrees=200
        endangledegrees=340
        degreedelta = 1
        pointslist = []
        a = pointslist.append
        from math import sin, cos, pi
        degreestoradians = pi/180.0
        radiansdelta = degreedelta*degreestoradians
        startangle = startangledegrees*degreestoradians
        endangle = endangledegrees*degreestoradians
        while endangle<startangle:
              endangle = endangle+2*pi
        angle = startangle
        while angle<endangle:
            x = centerx + cos(angle)*radius
            y = centery + sin(angle)*yradius
            a(x); a(y)
            angle = angle+radiansdelta

        # make the mouth
        smile = shapes.PolyLine(pointslist,
               fillColor = self.strokeColor,
               strokeColor = self.strokeColor,
               strokeWidth = max(s/38.,self.strokeWidth))
        g.add(smile)

        return g

class StopSign(_Symbol):
    """This draws a (British) stop sign.

        possible attributes:
        'x', 'y', 'size'

        """
    _attrMap = AttrMap(BASE=_Symbol,
        stopColor = AttrMapValue(isColorOrNone,desc='color of the word stop'),
        )

    def __init__(self):
        self.x = 0
        self.y = 0
        self.size = 100
        self.strokeColor = colors.black
        self.fillColor = colors.orangered
        self.stopColor = colors.ghostwhite

    def draw(self):
        # general widget bits
        s = float(self.size)  # abbreviate as we will use this a lot
        g = shapes.Group()

        # stop-sign specific bits
        athird=s/3

        outerOctagon = shapes.Polygon(points=[self.x+athird, self.y,
                                              self.x, self.y+athird,
                                              self.x, self.y+(athird*2),
                                              self.x+athird, self.y+s,
                                              self.x+(athird*2), self.y+s,
                                              self.x+s, self.y+(athird*2),
                                              self.x+s, self.y+athird,
                                              self.x+(athird*2), self.y],
                                      strokeColor = self.strokeColor,
                                      fillColor = None,
                                      strokeWidth=1)
        g.add(outerOctagon)

        innerOctagon = shapes.Polygon(points=[self.x+athird+(s/75), self.y+(s/75),
                                              self.x+(s/75), self.y+athird+(s/75),
                                              self.x+(s/75), self.y+(athird*2)-(s/75),
                                              self.x+athird+(s/75), self.y+s-(s/75),
                                              self.x+(athird*2)-(s/75), (self.y+s)-(s/75),
                                              (self.x+s)-(s/75), self.y+(athird*2)-(s/75),
                                              (self.x+s)-(s/75), self.y+athird+(s/75),
                                              self.x+(athird*2)-(s/75), self.y+(s/75)],
                                      strokeColor = None,
                                      fillColor = self.fillColor,
                                      strokeWidth=0)
        g.add(innerOctagon)

        if self.stopColor:
            g.add(shapes.String(self.x+(s*0.5),self.y+(s*0.4),
                            'STOP', fillColor=self.stopColor, textAnchor='middle',
                            fontSize=s/3, fontName="Helvetica-Bold"))

        return g


class NoEntry(_Symbol):
    """This draws a (British) No Entry sign - a red circle with a white line on it.

        possible attributes:
        'x', 'y', 'size'

        """

    _attrMap = AttrMap(BASE=_Symbol,
        innerBarColor = AttrMapValue(isColorOrNone,desc='color of the inner bar'),
        )

    def __init__(self):
        self.x = 0
        self.y = 0
        self.size = 100
        self.strokeColor = colors.black
        self.fillColor = colors.orangered
        self.innerBarColor = colors.ghostwhite

    def draw(self):
        # general widget bits
        s = float(self.size)  # abbreviate as we will use this a lot
        g = shapes.Group()

        # no-entry-sign specific bits
        if self.strokeColor:
            g.add(shapes.Circle(cx = (self.x+(s/2)), cy = (self.y+(s/2)), r = s/2, fillColor = None, strokeColor = self.strokeColor, strokeWidth=1))

        if self.fillColor:
            g.add(shapes.Circle(cx = (self.x+(s/2)), cy =(self.y+(s/2)), r = ((s/2)-(s/50)), fillColor = self.fillColor, strokeColor = None, strokeWidth=0))

        innerBarColor = self.innerBarColor
        if innerBarColor:
            g.add(shapes.Rect(self.x+(s*0.1), self.y+(s*0.4), width=s*0.8, height=s*0.2, fillColor = innerBarColor, strokeColor = innerBarColor, strokeLineCap = 1, strokeWidth = 0))
        return g

class NotAllowed(_Symbol):
    """This draws a 'forbidden' roundel (as used in the no-smoking sign).

        possible attributes:
        'x', 'y', 'size'

        """

    _attrMap = AttrMap(BASE=_Symbol,
        )

    def __init__(self):
        self.x = 0
        self.y = 0
        self.size = 100
        self.strokeColor = colors.red
        self.fillColor = colors.white

    def draw(self):
        # general widget bits
        s = float(self.size)  # abbreviate as we will use this a lot
        g = shapes.Group()
        strokeColor = self.strokeColor

        # not=allowed specific bits
        outerCircle = shapes.Circle(cx = (self.x+(s/2)), cy = (self.y+(s/2)), r = (s/2)-(s/10), fillColor = self.fillColor, strokeColor = strokeColor, strokeWidth=s/10.)
        g.add(outerCircle)

        centerx=self.x+s
        centery=self.y+(s/2)-(s/6)
        radius=s-(s/6)
        yradius = radius/2
        xradius = radius/2
        startangledegrees=100
        endangledegrees=-80
        degreedelta = 90
        pointslist = []
        a = pointslist.append
        from math import sin, cos, pi
        degreestoradians = pi/180.0
        radiansdelta = degreedelta*degreestoradians
        startangle = startangledegrees*degreestoradians
        endangle = endangledegrees*degreestoradians
        while endangle<startangle:
            endangle = endangle+2*pi
        angle = startangle
        while angle<endangle:
            x = centerx + cos(angle)*radius
            y = centery + sin(angle)*yradius
            a(x); a(y)
            angle = angle+radiansdelta
        crossbar = shapes.PolyLine(pointslist, fillColor = strokeColor, strokeColor = strokeColor, strokeWidth = s/10.)
        g.add(crossbar)
        return g


class NoSmoking(NotAllowed):
    """This draws a no-smoking sign.

        possible attributes:
        'x', 'y', 'size'

        """

    def __init__(self):
        NotAllowed.__init__(self)

    def draw(self):
        # general widget bits
        s = float(self.size)  # abbreviate as we will use this a lot
        g = NotAllowed.draw(self)

        # no-smoking-sign specific bits
        newx = self.x+(s/2)-(s/3.5)
        newy = self.y+(s/2)-(s/32)
        cigarrette1 = shapes.Rect(x = newx, y = newy, width = (s/2), height =(s/16),
                fillColor = colors.ghostwhite, strokeColor = colors.gray, strokeWidth=0)
        newx=newx+(s/2)+(s/64)
        g.insert(-1,cigarrette1)

        cigarrette2 = shapes.Rect(x = newx, y = newy, width = (s/80), height =(s/16),
                fillColor = colors.orangered, strokeColor = None, strokeWidth=0)
        newx= newx+(s/35)
        g.insert(-1,cigarrette2)

        cigarrette3 = shapes.Rect(x = newx, y = newy, width = (s/80), height =(s/16),
                fillColor = colors.orangered, strokeColor = None, strokeWidth=0)
        newx= newx+(s/35)
        g.insert(-1,cigarrette3)

        cigarrette4 = shapes.Rect(x = newx, y = newy, width = (s/80), height =(s/16),
                fillColor = colors.orangered, strokeColor = None, strokeWidth=0)
        newx= newx+(s/35)
        g.insert(-1,cigarrette4)

        return g


class DangerSign(_Symbol):
    """This draws a 'danger' sign: a yellow box with a black exclamation point.

        possible attributes:
        'x', 'y', 'size', 'strokeColor', 'fillColor', 'strokeWidth'

        """

    def __init__(self):
        self.x = 0
        self.y = 0
        self.size = 100
        self.strokeColor = colors.black
        self.fillColor = colors.gold
        self.strokeWidth = self.size*0.125

    def draw(self):
        # general widget bits
        s = float(self.size)  # abbreviate as we will use this a lot
        g = shapes.Group()
        ew = self.strokeWidth
        ae = s*0.125            #(ae = 'an eighth')


        # danger sign specific bits

        ew = self.strokeWidth
        ae = s*0.125            #(ae = 'an eighth')

        outerTriangle = shapes.Polygon(points = [
            self.x, self.y,
            self.x+s, self.y,
            self.x+(s/2),self.y+s],
               fillColor = None,
               strokeColor = self.strokeColor,
               strokeWidth=0)
        g.add(outerTriangle)

        innerTriangle = shapes.Polygon(points = [
            self.x+(s/50), self.y+(s/75),
            (self.x+s)-(s/50), self.y+(s/75),
            self.x+(s/2),(self.y+s)-(s/50)],
               fillColor = self.fillColor,
               strokeColor = None,
               strokeWidth=0)
        g.add(innerTriangle)

        exmark = shapes.Polygon(points=[
            ((self.x+s/2)-ew/2), self.y+ae*2.5,
            ((self.x+s/2)+ew/2), self.y+ae*2.5,
            ((self.x+s/2)+((ew/2))+(ew/6)), self.y+ae*5.5,
            ((self.x+s/2)-((ew/2))-(ew/6)), self.y+ae*5.5],
               fillColor = self.strokeColor,
               strokeColor = None)
        g.add(exmark)

        exdot = shapes.Polygon(points=[
            ((self.x+s/2)-ew/2), self.y+ae,
            ((self.x+s/2)+ew/2), self.y+ae,
            ((self.x+s/2)+ew/2), self.y+ae*2,
            ((self.x+s/2)-ew/2), self.y+ae*2],
               fillColor = self.strokeColor,
               strokeColor = None)
        g.add(exdot)

        return g


class YesNo(_Symbol):
    """This widget draw a tickbox or crossbox depending on 'testValue'.

        If this widget is supplied with a 'True' or 1 as a value for
        testValue, it will use the tickbox widget. Otherwise, it will
        produce a crossbox.

        possible attributes:
        'x', 'y', 'size', 'tickcolor', 'crosscolor', 'testValue'

"""

    _attrMap = AttrMap(BASE=_Symbol,
        tickcolor = AttrMapValue(isColor),
        crosscolor = AttrMapValue(isColor),
        testValue = AttrMapValue(isBoolean),
        )

    def __init__(self):
        self.x = 0
        self.y = 0
        self.size = 100
        self.tickcolor = colors.green
        self.crosscolor = colors.red
        self.testValue = 1

    def draw(self):
        if self.testValue:
            yn=Tickbox()
            yn.tickColor=self.tickcolor
        else:
            yn=Crossbox()
            yn.crossColor=self.crosscolor
        yn.x=self.x
        yn.y=self.y
        yn.size=self.size
        yn.draw()
        return yn


    def demo(self):
        D = shapes.Drawing(200, 100)
        yn = YesNo()
        yn.x = 15
        yn.y = 25
        yn.size = 70
        yn.testValue = 0
        yn.draw()
        D.add(yn)
        yn2 = YesNo()
        yn2.x = 120
        yn2.y = 25
        yn2.size = 70
        yn2.testValue = 1
        yn2.draw()
        D.add(yn2)
        labelFontSize = 8
        D.add(shapes.String(yn.x+(yn.size/2),(yn.y-(1.2*labelFontSize)),
                            'testValue=0', fillColor=colors.black, textAnchor='middle',
                            fontSize=labelFontSize))
        D.add(shapes.String(yn2.x+(yn2.size/2),(yn2.y-(1.2*labelFontSize)),
                            'testValue=1', fillColor=colors.black, textAnchor='middle',
                            fontSize=labelFontSize))
        labelFontSize = 10
        D.add(shapes.String(yn.x+85,(yn.y-20),
                            self.__class__.__name__, fillColor=colors.black, textAnchor='middle',
                            fontSize=labelFontSize))
        return D

class FloppyDisk(_Symbol):
    """This widget draws an icon of a floppy disk.

        possible attributes:
        'x', 'y', 'size', 'diskcolor'

        """

    _attrMap = AttrMap(BASE=_Symbol,
        diskColor = AttrMapValue(isColor),
        )

    def __init__(self):
        self.x = 0
        self.y = 0
        self.size = 100
        self.diskColor = colors.black

    def draw(self):
        # general widget bits
        s = float(self.size)  # abbreviate as we will use this a lot
        g = shapes.Group()


        # floppy disk specific bits
        diskBody = shapes.Rect(x=self.x, y=self.y+(s/100), width=s, height=s-(s/100),
               fillColor = self.diskColor,
               strokeColor = None,
               strokeWidth=0)
        g.add(diskBody)

        label = shapes.Rect(x=self.x+(s*0.1), y=(self.y+s)-(s*0.5), width=s*0.8, height=s*0.48,
               fillColor = colors.whitesmoke,
               strokeColor = None,
               strokeWidth=0)
        g.add(label)

        labelsplash = shapes.Rect(x=self.x+(s*0.1), y=(self.y+s)-(s*0.1), width=s*0.8, height=s*0.08,
               fillColor = colors.royalblue,
               strokeColor = None,
               strokeWidth=0)
        g.add(labelsplash)


        line1 = shapes.Line(x1=self.x+(s*0.15), y1=self.y+(0.6*s), x2=self.x+(s*0.85), y2=self.y+(0.6*s),
               fillColor = colors.black,
               strokeColor = colors.black,
               strokeWidth=0)
        g.add(line1)

        line2 = shapes.Line(x1=self.x+(s*0.15), y1=self.y+(0.7*s), x2=self.x+(s*0.85), y2=self.y+(0.7*s),
               fillColor = colors.black,
               strokeColor = colors.black,
               strokeWidth=0)
        g.add(line2)

        line3 = shapes.Line(x1=self.x+(s*0.15), y1=self.y+(0.8*s), x2=self.x+(s*0.85), y2=self.y+(0.8*s),
               fillColor = colors.black,
               strokeColor = colors.black,
               strokeWidth=0)
        g.add(line3)

        metalcover = shapes.Rect(x=self.x+(s*0.2), y=(self.y), width=s*0.5, height=s*0.35,
               fillColor = colors.silver,
               strokeColor = None,
               strokeWidth=0)
        g.add(metalcover)

        coverslot = shapes.Rect(x=self.x+(s*0.28), y=(self.y)+(s*0.035), width=s*0.12, height=s*0.28,
               fillColor = self.diskColor,
               strokeColor = None,
               strokeWidth=0)
        g.add(coverslot)

        return g

class ArrowOne(_Symbol):
    """This widget draws an arrow (style one).

        possible attributes:
        'x', 'y', 'size', 'fillColor'

        """
    def __init__(self):
        self.x = 0
        self.y = 0
        self.size = 100
        self.fillColor = colors.red
        self.strokeWidth = 0
        self.strokeColor = None

    def draw(self):
        # general widget bits
        s = float(self.size)  # abbreviate as we will use this a lot
        g = shapes.Group()

        x = self.x
        y = self.y
        s2 = s/2
        s3 = s/3
        s5 = s/5
        g.add(shapes.Polygon(points = [
                                        x,y+s3,
                                        x,y+2*s3,
                                        x+s2,y+2*s3,
                                        x+s2,y+4*s5,
                                        x+s,y+s2,
                                        x+s2,y+s5,
                                        x+s2,y+s3,
                                       ],
                fillColor = self.fillColor,
                strokeColor = self.strokeColor,
                strokeWidth = self.strokeWidth,
                )
            )
        return g

class ArrowTwo(ArrowOne):
    """This widget draws an arrow (style two).

        possible attributes:
        'x', 'y', 'size', 'fillColor'

        """

    def __init__(self):
        self.x = 0
        self.y = 0
        self.size = 100
        self.fillColor = colors.blue
        self.strokeWidth = 0
        self.strokeColor = None

    def draw(self):
        # general widget bits
        s = float(self.size)  # abbreviate as we will use this a lot
        g = shapes.Group()

        # arrow specific bits
        x = self.x
        y = self.y
        s2 = s/2
        s3 = s/3
        s5 = s/5
        s24 = s/24

        g.add(shapes.Polygon(
            points = [
                    x,y+11*s24,
                    x,y+13*s24,
                    x+18.75*s24, y+13*s24,
                    x+2*s3, y+2*s3,
                    x+s, y+s2,
                    x+2*s3, y+s3,
                    x+18.75*s24, y+11*s24,
                    ],
            fillColor = self.fillColor,
            strokeColor = self.strokeColor,
            strokeWidth = self.strokeWidth)
            )

        return g

class CrossHair(_Symbol):
    """This draws an equilateral triangle."""
    _attrMap = AttrMap(BASE=_Symbol,
            innerGap = AttrMapValue(EitherOr((isString,isNumberOrNone)),desc=' gap at centre as "x%" or points or None'),
        )

    def __init__(self):
        self.x = self.y = self.dx = self.dy = 0
        self.size = 10
        self.fillColor = None
        self.strokeColor = colors.black
        self.strokeWidth = 0.5
        self.innerGap = '20%'

    def draw(self):
        # general widget bits
        s = float(self.size)  # abbreviate as we will use this a lot
        g = shapes.Group()
        ig = self.innerGap

        x = self.x+self.dx
        y = self.y+self.dy
        hsize = 0.5*self.size
        if not ig:
            L = [(x-hsize,y,x+hsize,y), (x,y-hsize,x,y+hsize)]
        else:
            if isStr(ig):
                ig = asUnicode(ig)
                if ig.endswith(u'%'):
                    gs = hsize*float(ig[:-1])/100.0
                else:
                    gs = float(ig)*0.5
            else:
                gs = ig*0.5
            L = [(x-hsize,y,x-gs,y), (x+gs,y,x+hsize,y), (x,y-hsize,x,y-gs), (x,y+gs,x,y+hsize)]
        P = shapes.Path(strokeWidth=self.strokeWidth,strokeColor=self.strokeColor)
        for x0,y0,x1,y1 in L:
            P.moveTo(x0,y0)
            P.lineTo(x1,y1)
        g.add(P)
        return g


def test():
    """This function produces a pdf with examples of all the signs and symbols from this file.
    """
    labelFontSize = 10
    D = shapes.Drawing(450,650)
    cb = Crossbox()
    cb.x = 20
    cb.y = 530
    D.add(cb)
    D.add(shapes.String(cb.x+(cb.size/2),(cb.y-(1.2*labelFontSize)),
                           cb.__class__.__name__, fillColor=colors.black, textAnchor='middle',
                           fontSize=labelFontSize))

    tb = Tickbox()
    tb.x = 170
    tb.y = 530
    D.add(tb)
    D.add(shapes.String(tb.x+(tb.size/2),(tb.y-(1.2*labelFontSize)),
                            tb.__class__.__name__, fillColor=colors.black, textAnchor='middle',
                            fontSize=labelFontSize))


    yn = YesNo()
    yn.x = 320
    yn.y = 530
    D.add(yn)
    tempstring = yn.__class__.__name__ + '*'
    D.add(shapes.String(yn.x+(tb.size/2),(yn.y-(1.2*labelFontSize)),
                            tempstring, fillColor=colors.black, textAnchor='middle',
                            fontSize=labelFontSize))
    D.add(shapes.String(130,6,
                            "(The 'YesNo' widget returns a tickbox if testvalue=1, and a crossbox if testvalue=0)", fillColor=colors.black, textAnchor='middle',
                            fontSize=labelFontSize*0.75))


    ss = StopSign()
    ss.x = 20
    ss.y = 400
    D.add(ss)
    D.add(shapes.String(ss.x+(ss.size/2), ss.y-(1.2*labelFontSize),
                            ss.__class__.__name__, fillColor=colors.black, textAnchor='middle',
                            fontSize=labelFontSize))

    ne = NoEntry()
    ne.x = 170
    ne.y = 400
    D.add(ne)
    D.add(shapes.String(ne.x+(ne.size/2),(ne.y-(1.2*labelFontSize)),
                            ne.__class__.__name__, fillColor=colors.black, textAnchor='middle',
                            fontSize=labelFontSize))

    sf = SmileyFace()
    sf.x = 320
    sf.y = 400
    D.add(sf)
    D.add(shapes.String(sf.x+(sf.size/2),(sf.y-(1.2*labelFontSize)),
                            sf.__class__.__name__, fillColor=colors.black, textAnchor='middle',
                            fontSize=labelFontSize))

    ds = DangerSign()
    ds.x = 20
    ds.y = 270
    D.add(ds)
    D.add(shapes.String(ds.x+(ds.size/2),(ds.y-(1.2*labelFontSize)),
                            ds.__class__.__name__, fillColor=colors.black, textAnchor='middle',
                            fontSize=labelFontSize))

    na = NotAllowed()
    na.x = 170
    na.y = 270
    D.add(na)
    D.add(shapes.String(na.x+(na.size/2),(na.y-(1.2*labelFontSize)),
                            na.__class__.__name__, fillColor=colors.black, textAnchor='middle',
                            fontSize=labelFontSize))

    ns = NoSmoking()
    ns.x = 320
    ns.y = 270
    D.add(ns)
    D.add(shapes.String(ns.x+(ns.size/2),(ns.y-(1.2*labelFontSize)),
                            ns.__class__.__name__, fillColor=colors.black, textAnchor='middle',
                            fontSize=labelFontSize))

    a1 = ArrowOne()
    a1.x = 20
    a1.y = 140
    D.add(a1)
    D.add(shapes.String(a1.x+(a1.size/2),(a1.y-(1.2*labelFontSize)),
                            a1.__class__.__name__, fillColor=colors.black, textAnchor='middle',
                            fontSize=labelFontSize))

    a2 = ArrowTwo()
    a2.x = 170
    a2.y = 140
    D.add(a2)
    D.add(shapes.String(a2.x+(a2.size/2),(a2.y-(1.2*labelFontSize)),
                            a2.__class__.__name__, fillColor=colors.black, textAnchor='middle',
                            fontSize=labelFontSize))

    fd = FloppyDisk()
    fd.x = 320
    fd.y = 140
    D.add(fd)
    D.add(shapes.String(fd.x+(fd.size/2),(fd.y-(1.2*labelFontSize)),
                            fd.__class__.__name__, fillColor=colors.black, textAnchor='middle',
                            fontSize=labelFontSize))

    renderPDF.drawToFile(D, 'signsandsymbols.pdf', 'signsandsymbols.py')
    print('wrote file: signsandsymbols.pdf')

if __name__=='__main__':
    test()
