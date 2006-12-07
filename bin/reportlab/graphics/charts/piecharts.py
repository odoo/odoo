#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/graphics/charts/piecharts.py
# experimental pie chart script.  Two types of pie - one is a monolithic
#widget with all top-level properties, the other delegates most stuff to
#a wedges collection whic lets you customize the group or every individual
#wedge.

"""Basic Pie Chart class.

This permits you to customize and pop out individual wedges;
supports elliptical and circular pies.
"""
__version__=''' $Id$ '''

import copy
from math import sin, cos, pi

from reportlab.lib import colors
from reportlab.lib.validators import isColor, isNumber, isListOfNumbersOrNone,\
                                    isListOfNumbers, isColorOrNone, isString,\
                                    isListOfStringsOrNone, OneOf, SequenceOf,\
                                    isBoolean, isListOfColors, isNumberOrNone,\
                                    isNoneOrListOfNoneOrStrings, isTextAnchor,\
                                    isNoneOrListOfNoneOrNumbers, isBoxAnchor,\
                                    isStringOrNone
from reportlab.lib.attrmap import *
from reportlab.pdfgen.canvas import Canvas
from reportlab.graphics.shapes import Group, Drawing, Ellipse, Wedge, String, STATE_DEFAULTS, ArcPath, Polygon
from reportlab.graphics.widgetbase import Widget, TypedPropertyCollection, PropHolder
from textlabels import Label

_ANGLE2BOXANCHOR={0:'w', 45:'sw', 90:'s', 135:'se', 180:'e', 225:'ne', 270:'n', 315: 'nw', -45: 'nw'}
class WedgeLabel(Label):
    def _checkDXY(self,ba):
        pass
    def _getBoxAnchor(self):
        na = (int((self._pmv%360)/45.)*45)%360
        if not (na % 90): # we have a right angle case
            da = (self._pmv - na) % 360
            if abs(da)>5:
                na = na + (da>0 and 45 or -45)
        ba = _ANGLE2BOXANCHOR[na]
        self._checkDXY(ba)
        return ba

class WedgeProperties(PropHolder):
    """This holds descriptive information about the wedges in a pie chart.

    It is not to be confused with the 'wedge itself'; this just holds
    a recipe for how to format one, and does not allow you to hack the
    angles.  It can format a genuine Wedge object for you with its
    format method.
    """

    _attrMap = AttrMap(
        strokeWidth = AttrMapValue(isNumber),
        fillColor = AttrMapValue(isColorOrNone),
        strokeColor = AttrMapValue(isColorOrNone),
        strokeDashArray = AttrMapValue(isListOfNumbersOrNone),
        popout = AttrMapValue(isNumber),
        fontName = AttrMapValue(isString),
        fontSize = AttrMapValue(isNumber),
        fontColor = AttrMapValue(isColorOrNone),
        labelRadius = AttrMapValue(isNumber),
        label_dx = AttrMapValue(isNumber),
        label_dy = AttrMapValue(isNumber),
        label_angle = AttrMapValue(isNumber),
        label_boxAnchor = AttrMapValue(isBoxAnchor),
        label_boxStrokeColor = AttrMapValue(isColorOrNone),
        label_boxStrokeWidth = AttrMapValue(isNumber),
        label_boxFillColor = AttrMapValue(isColorOrNone),
        label_strokeColor = AttrMapValue(isColorOrNone),
        label_strokeWidth = AttrMapValue(isNumber),
        label_text = AttrMapValue(isStringOrNone),
        label_leading = AttrMapValue(isNumberOrNone),
        label_width = AttrMapValue(isNumberOrNone),
        label_maxWidth = AttrMapValue(isNumberOrNone),
        label_height = AttrMapValue(isNumberOrNone),
        label_textAnchor = AttrMapValue(isTextAnchor),
        label_visible = AttrMapValue(isBoolean,desc="True if the label is to be drawn"),
        label_topPadding = AttrMapValue(isNumber,'padding at top of box'),
        label_leftPadding = AttrMapValue(isNumber,'padding at left of box'),
        label_rightPadding = AttrMapValue(isNumber,'padding at right of box'),
        label_bottomPadding = AttrMapValue(isNumber,'padding at bottom of box'),
        )

    def __init__(self):
        self.strokeWidth = 0
        self.fillColor = None
        self.strokeColor = STATE_DEFAULTS["strokeColor"]
        self.strokeDashArray = STATE_DEFAULTS["strokeDashArray"]
        self.popout = 0
        self.fontName = STATE_DEFAULTS["fontName"]
        self.fontSize = STATE_DEFAULTS["fontSize"]
        self.fontColor = STATE_DEFAULTS["fillColor"]
        self.labelRadius = 1.2
        self.label_dx = self.label_dy = self.label_angle = 0
        self.label_text = None
        self.label_topPadding = self.label_leftPadding = self.label_rightPadding = self.label_bottomPadding = 0
        self.label_boxAnchor = 'c'
        self.label_boxStrokeColor = None    #boxStroke
        self.label_boxStrokeWidth = 0.5 #boxStrokeWidth
        self.label_boxFillColor = None
        self.label_strokeColor = None
        self.label_strokeWidth = 0.1
        self.label_leading =    self.label_width = self.label_maxWidth = self.label_height = None
        self.label_textAnchor = 'start'
        self.label_visible = 1

def _addWedgeLabel(self,text,add,angle,labelX,labelY,wedgeStyle,labelClass=WedgeLabel):
    # now draw a label
    if self.simpleLabels:
        theLabel = String(labelX, labelY, text)
        theLabel.textAnchor = "middle"
    else:
        theLabel = labelClass()
        theLabel._pmv = angle
        theLabel.x = labelX
        theLabel.y = labelY
        theLabel.dx = wedgeStyle.label_dx
        theLabel.dy = wedgeStyle.label_dy
        theLabel.angle = wedgeStyle.label_angle
        theLabel.boxAnchor = wedgeStyle.label_boxAnchor
        theLabel.boxStrokeColor = wedgeStyle.label_boxStrokeColor
        theLabel.boxStrokeWidth = wedgeStyle.label_boxStrokeWidth
        theLabel.boxFillColor = wedgeStyle.label_boxFillColor
        theLabel.strokeColor = wedgeStyle.label_strokeColor
        theLabel.strokeWidth = wedgeStyle.label_strokeWidth
        _text = wedgeStyle.label_text
        if _text is None: _text = text
        theLabel._text = _text
        theLabel.leading = wedgeStyle.label_leading
        theLabel.width = wedgeStyle.label_width
        theLabel.maxWidth = wedgeStyle.label_maxWidth
        theLabel.height = wedgeStyle.label_height
        theLabel.textAnchor = wedgeStyle.label_textAnchor
        theLabel.visible = wedgeStyle.label_visible
        theLabel.topPadding = wedgeStyle.label_topPadding
        theLabel.leftPadding = wedgeStyle.label_leftPadding
        theLabel.rightPadding = wedgeStyle.label_rightPadding
        theLabel.bottomPadding = wedgeStyle.label_bottomPadding
    theLabel.fontSize = wedgeStyle.fontSize
    theLabel.fontName = wedgeStyle.fontName
    theLabel.fillColor = wedgeStyle.fontColor
    add(theLabel)

def _fixLabels(labels,n):
    if labels is None:
        labels = [''] * n
    else:
        i = n-len(labels)
        if i>0: labels = labels + ['']*i
    return labels

class Pie(Widget):
    _attrMap = AttrMap(
        x = AttrMapValue(isNumber, desc='X position of the chart within its container.'),
        y = AttrMapValue(isNumber, desc='Y position of the chart within its container.'),
        width = AttrMapValue(isNumber, desc='width of pie bounding box. Need not be same as width.'),
        height = AttrMapValue(isNumber, desc='height of pie bounding box.  Need not be same as height.'),
        data = AttrMapValue(isListOfNumbers, desc='list of numbers defining wedge sizes; need not sum to 1'),
        labels = AttrMapValue(isListOfStringsOrNone, desc="optional list of labels to use for each data point"),
        startAngle = AttrMapValue(isNumber, desc="angle of first slice; like the compass, 0 is due North"),
        direction = AttrMapValue( OneOf('clockwise', 'anticlockwise'), desc="'clockwise' or 'anticlockwise'"),
        slices = AttrMapValue(None, desc="collection of wedge descriptor objects"),
        simpleLabels = AttrMapValue(isBoolean, desc="If true(default) use String not super duper WedgeLabel"),
        other_threshold = AttrMapValue(isNumber, desc='A value for doing thresh holding, not used yet.'),
        )
    other_threshold=None

    def __init__(self):
        self.x = 0
        self.y = 0
        self.width = 100
        self.height = 100
        self.data = [1]
        self.labels = None  # or list of strings
        self.startAngle = 90
        self.direction = "clockwise"
        self.simpleLabels = 1

        self.slices = TypedPropertyCollection(WedgeProperties)
        self.slices[0].fillColor = colors.darkcyan
        self.slices[1].fillColor = colors.blueviolet
        self.slices[2].fillColor = colors.blue
        self.slices[3].fillColor = colors.cyan

    def demo(self):
        d = Drawing(200, 100)

        pc = Pie()
        pc.x = 50
        pc.y = 10
        pc.width = 100
        pc.height = 80
        pc.data = [10,20,30,40,50,60]
        pc.labels = ['a','b','c','d','e','f']

        pc.slices.strokeWidth=0.5
        pc.slices[3].popout = 10
        pc.slices[3].strokeWidth = 2
        pc.slices[3].strokeDashArray = [2,2]
        pc.slices[3].labelRadius = 1.75
        pc.slices[3].fontColor = colors.red
        pc.slices[0].fillColor = colors.darkcyan
        pc.slices[1].fillColor = colors.blueviolet
        pc.slices[2].fillColor = colors.blue
        pc.slices[3].fillColor = colors.cyan
        pc.slices[4].fillColor = colors.aquamarine
        pc.slices[5].fillColor = colors.cadetblue
        pc.slices[6].fillColor = colors.lightcoral

        d.add(pc)
        return d

    def normalizeData(self):
        from operator import add
        data = self.data
        self._sum = sum = float(reduce(add,data,0))
        return abs(sum)>=1e-8 and map(lambda x,f=360./sum: f*x, data) or len(data)*[0]

    def makeWedges(self):
        # normalize slice data
        normData = self.normalizeData()
        n = len(normData)
        labels = _fixLabels(self.labels,n)

        xradius = self.width/2.0
        yradius = self.height/2.0
        centerx = self.x + xradius
        centery = self.y + yradius

        if self.direction == "anticlockwise":
            whichWay = 1
        else:
            whichWay = -1

        g = Group()
        i = 0
        styleCount = len(self.slices)

        startAngle = self.startAngle #% 360
        for angle in normData:
            endAngle = (startAngle + (angle * whichWay)) #% 360
            if abs(startAngle-endAngle)>=1e-5:
                if startAngle < endAngle:
                    a1 = startAngle
                    a2 = endAngle
                else:
                    a1 = endAngle
                    a2 = startAngle

                #if we didn't use %stylecount here we'd end up with the later wedges
                #all having the default style
                wedgeStyle = self.slices[i%styleCount]

                # is it a popout?
                cx, cy = centerx, centery
                if wedgeStyle.popout <> 0:
                    # pop out the wedge
                    averageAngle = (a1+a2)/2.0
                    aveAngleRadians = averageAngle * pi/180.0
                    popdistance = wedgeStyle.popout
                    cx = centerx + popdistance * cos(aveAngleRadians)
                    cy = centery + popdistance * sin(aveAngleRadians)

                if n > 1:
                    theWedge = Wedge(cx, cy, xradius, a1, a2, yradius=yradius)
                elif n==1:
                    theWedge = Ellipse(cx, cy, xradius, yradius)

                theWedge.fillColor = wedgeStyle.fillColor
                theWedge.strokeColor = wedgeStyle.strokeColor
                theWedge.strokeWidth = wedgeStyle.strokeWidth
                theWedge.strokeDashArray = wedgeStyle.strokeDashArray

                g.add(theWedge)
                text = labels[i]
                if text:
                    averageAngle = (a1+a2)/2.0
                    aveAngleRadians = averageAngle*pi/180.0
                    labelRadius = wedgeStyle.labelRadius
                    labelX = cx + (0.5 * self.width * cos(aveAngleRadians) * labelRadius)
                    labelY = cy + (0.5 * self.height * sin(aveAngleRadians) * labelRadius)
                    _addWedgeLabel(self,text,g.add,averageAngle,labelX,labelY,wedgeStyle)

            startAngle = endAngle
            i = i + 1

        return g

    def draw(self):
        g = Group()
        g.add(self.makeWedges())
        return g

class LegendedPie(Pie):
    """Pie with a two part legend (one editable with swatches, one hidden without swatches)."""

    _attrMap = AttrMap(BASE=Pie,
        drawLegend = AttrMapValue(isBoolean, desc="If true then create and draw legend"),
        legend1 = AttrMapValue(None, desc="Handle to legend for pie"),
        legendNumberFormat = AttrMapValue(None, desc="Formatting routine for number on right hand side of legend."),
        legendNumberOffset = AttrMapValue(isNumber, desc="Horizontal space between legend and numbers on r/hand side"),
        pieAndLegend_colors = AttrMapValue(isListOfColors, desc="Colours used for both swatches and pie"),
        legend_names = AttrMapValue(isNoneOrListOfNoneOrStrings, desc="Names used in legend (or None)"),
        legend_data = AttrMapValue(isNoneOrListOfNoneOrNumbers, desc="Numbers used on r/hand side of legend (or None)"),
        leftPadding = AttrMapValue(isNumber, desc='Padding on left of drawing'),
        rightPadding = AttrMapValue(isNumber, desc='Padding on right of drawing'),
        topPadding = AttrMapValue(isNumber, desc='Padding at top of drawing'),
        bottomPadding = AttrMapValue(isNumber, desc='Padding at bottom of drawing'),
        )

    def __init__(self):
        Pie.__init__(self)
        self.x = 0
        self.y = 0
        self.height = 100
        self.width = 100
        self.data = [38.4, 20.7, 18.9, 15.4, 6.6]
        self.labels = None
        self.direction = 'clockwise'
        PCMYKColor, black = colors.PCMYKColor, colors.black
        self.pieAndLegend_colors = [PCMYKColor(11,11,72,0,spotName='PANTONE 458 CV'),
                                    PCMYKColor(100,65,0,30,spotName='PANTONE 288 CV'),
                                    PCMYKColor(11,11,72,0,spotName='PANTONE 458 CV',density=75),
                                    PCMYKColor(100,65,0,30,spotName='PANTONE 288 CV',density=75),
                                    PCMYKColor(11,11,72,0,spotName='PANTONE 458 CV',density=50),
                                    PCMYKColor(100,65,0,30,spotName='PANTONE 288 CV',density=50)]

        #Allows us up to six 'wedges' to be coloured
        self.slices[0].fillColor=self.pieAndLegend_colors[0]
        self.slices[1].fillColor=self.pieAndLegend_colors[1]
        self.slices[2].fillColor=self.pieAndLegend_colors[2]
        self.slices[3].fillColor=self.pieAndLegend_colors[3]
        self.slices[4].fillColor=self.pieAndLegend_colors[4]
        self.slices[5].fillColor=self.pieAndLegend_colors[5]

        self.slices.strokeWidth = 0.75
        self.slices.strokeColor = black

        legendOffset = 17
        self.legendNumberOffset = 51
        self.legendNumberFormat = '%.1f%%'
        self.legend_data = self.data

        #set up the legends
        from reportlab.graphics.charts.legends import Legend
        self.legend1 = Legend()
        self.legend1.x = self.width+legendOffset
        self.legend1.y = self.height
        self.legend1.deltax = 5.67
        self.legend1.deltay = 14.17
        self.legend1.dxTextSpace = 11.39
        self.legend1.dx = 5.67
        self.legend1.dy = 5.67
        self.legend1.columnMaximum = 7
        self.legend1.alignment = 'right'
        self.legend_names = ['AAA:','AA:','A:','BBB:','NR:']
        for f in range(0,len(self.data)):
            self.legend1.colorNamePairs.append((self.pieAndLegend_colors[f], self.legend_names[f]))
        self.legend1.fontName = "Helvetica-Bold"
        self.legend1.fontSize = 6
        self.legend1.strokeColor = black
        self.legend1.strokeWidth = 0.5

        self._legend2 = Legend()
        self._legend2.dxTextSpace = 0
        self._legend2.dx = 0
        self._legend2.alignment = 'right'
        self._legend2.fontName = "Helvetica-Oblique"
        self._legend2.fontSize = 6
        self._legend2.strokeColor = self.legend1.strokeColor

        self.leftPadding = 5
        self.rightPadding = 5
        self.topPadding = 5
        self.bottomPadding = 5
        self.drawLegend = 1

    def draw(self):
        if self.drawLegend:
            self.legend1.colorNamePairs = []
            self._legend2.colorNamePairs = []
        for f in range(0,len(self.data)):
            if self.legend_names == None:
                self.slices[f].fillColor = self.pieAndLegend_colors[f]
                self.legend1.colorNamePairs.append((self.pieAndLegend_colors[f], None))
            else:
                try:
                    self.slices[f].fillColor = self.pieAndLegend_colors[f]
                    self.legend1.colorNamePairs.append((self.pieAndLegend_colors[f], self.legend_names[f]))
                except IndexError:
                    self.slices[f].fillColor = self.pieAndLegend_colors[f%len(self.pieAndLegend_colors)]
                    self.legend1.colorNamePairs.append((self.pieAndLegend_colors[f%len(self.pieAndLegend_colors)], self.legend_names[f]))
            if self.legend_data != None:
                ldf = self.legend_data[f]
                lNF = self.legendNumberFormat
                from types import StringType
                if ldf is None or lNF is None:
                    pass
                elif type(lNF) is StringType:
                    ldf = lNF % ldf
                elif callable(lNF):
                    ldf = lNF(ldf)
                else:
                    p = self.legend_names[f]
                if self.legend_data != None:
                    ldf = self.legend_data[f]
                    lNF = self.legendNumberFormat
                    if ldf is None or lNF is None:
                        pass
                    elif type(lNF) is StringType:
                        ldf = lNF % ldf
                    elif callable(lNF):
                        ldf = lNF(ldf)
                    else:
                        msg = "Unknown formatter type %s, expected string or function" % self.legendNumberFormat
                        raise Exception, msg
                    self._legend2.colorNamePairs.append((None,ldf))
        p = Pie.draw(self)
        if self.drawLegend:
            p.add(self.legend1)
            #hide from user - keeps both sides lined up!
            self._legend2.x = self.legend1.x+self.legendNumberOffset
            self._legend2.y = self.legend1.y
            self._legend2.deltax = self.legend1.deltax
            self._legend2.deltay = self.legend1.deltay
            self._legend2.dy = self.legend1.dy
            self._legend2.columnMaximum = self.legend1.columnMaximum
            p.add(self._legend2)
        p.shift(self.leftPadding, self.bottomPadding)
        return p

    def _getDrawingDimensions(self):
        tx = self.rightPadding
        if self.drawLegend:
            tx = tx+self.legend1.x+self.legendNumberOffset #self._legend2.x
            tx = tx + self._legend2._calculateMaxWidth(self._legend2.colorNamePairs)
        ty = self.bottomPadding+self.height+self.topPadding
        return (tx,ty)

    def demo(self, drawing=None):
        if not drawing:
            tx,ty = self._getDrawingDimensions()
            drawing = Drawing(tx, ty)
        drawing.add(self.draw())
        return drawing

from utils3d import _getShaded, _2rad, _360, _pi_2, _2pi
class Wedge3dProperties(PropHolder):
    """This holds descriptive information about the wedges in a pie chart.

    It is not to be confused with the 'wedge itself'; this just holds
    a recipe for how to format one, and does not allow you to hack the
    angles.  It can format a genuine Wedge object for you with its
    format method.
    """
    _attrMap = AttrMap(
        fillColor = AttrMapValue(isColorOrNone),
        fillColorShaded = AttrMapValue(isColorOrNone),
        fontColor = AttrMapValue(isColorOrNone),
        fontName = AttrMapValue(isString),
        fontSize = AttrMapValue(isNumber),
        label_angle = AttrMapValue(isNumber),
        label_bottomPadding = AttrMapValue(isNumber,'padding at bottom of box'),
        label_boxAnchor = AttrMapValue(isBoxAnchor),
        label_boxFillColor = AttrMapValue(isColorOrNone),
        label_boxStrokeColor = AttrMapValue(isColorOrNone),
        label_boxStrokeWidth = AttrMapValue(isNumber),
        label_dx = AttrMapValue(isNumber),
        label_dy = AttrMapValue(isNumber),
        label_height = AttrMapValue(isNumberOrNone),
        label_leading = AttrMapValue(isNumberOrNone),
        label_leftPadding = AttrMapValue(isNumber,'padding at left of box'),
        label_maxWidth = AttrMapValue(isNumberOrNone),
        label_rightPadding = AttrMapValue(isNumber,'padding at right of box'),
        label_strokeColor = AttrMapValue(isColorOrNone),
        label_strokeWidth = AttrMapValue(isNumber),
        label_text = AttrMapValue(isStringOrNone),
        label_textAnchor = AttrMapValue(isTextAnchor),
        label_topPadding = AttrMapValue(isNumber,'padding at top of box'),
        label_visible = AttrMapValue(isBoolean,desc="True if the label is to be drawn"),
        label_width = AttrMapValue(isNumberOrNone),
        labelRadius = AttrMapValue(isNumber),
        popout = AttrMapValue(isNumber),
        shading = AttrMapValue(isNumber),
        strokeColor = AttrMapValue(isColorOrNone),
        strokeColorShaded = AttrMapValue(isColorOrNone),
        strokeDashArray = AttrMapValue(isListOfNumbersOrNone),
        strokeWidth = AttrMapValue(isNumber),
        visible = AttrMapValue(isBoolean,'set to false to skip displaying'),
        )

    def __init__(self):
        self.strokeWidth = 0
        self.shading = 0.3
        self.visible = 1
        self.strokeColorShaded = self.fillColorShaded = self.fillColor = None
        self.strokeColor = STATE_DEFAULTS["strokeColor"]
        self.strokeDashArray = STATE_DEFAULTS["strokeDashArray"]
        self.popout = 0
        self.fontName = STATE_DEFAULTS["fontName"]
        self.fontSize = STATE_DEFAULTS["fontSize"]
        self.fontColor = STATE_DEFAULTS["fillColor"]
        self.labelRadius = 1.2
        self.label_dx = self.label_dy = self.label_angle = 0
        self.label_text = None
        self.label_topPadding = self.label_leftPadding = self.label_rightPadding = self.label_bottomPadding = 0
        self.label_boxAnchor = 'c'
        self.label_boxStrokeColor = None    #boxStroke
        self.label_boxStrokeWidth = 0.5 #boxStrokeWidth
        self.label_boxFillColor = None
        self.label_strokeColor = None
        self.label_strokeWidth = 0.1
        self.label_leading =    self.label_width = self.label_maxWidth = self.label_height = None
        self.label_textAnchor = 'start'
        self.label_visible = 1

class _SL3D:
    def __init__(self,lo,hi):
        if lo<0:
            lo += 360
            hi += 360
        self.lo = lo
        self.hi = hi
        self.mid = (lo+hi)*0.5

    def __str__(self):
        return '_SL3D(%.2f,%.2f)' % (self.lo,self.hi)

_270r = _2rad(270)
class Pie3d(Pie):
    _attrMap = AttrMap(BASE=Pie,
        perspective = AttrMapValue(isNumber, desc='A flattening parameter.'),
        depth_3d = AttrMapValue(isNumber, desc='depth of the pie.'),
        angle_3d = AttrMapValue(isNumber, desc='The view angle.'),
        )
    perspective = 70
    depth_3d = 25
    angle_3d = 180

    def _popout(self,i):
        return self.slices[i].popout or 0

    def CX(self, i,d ):
        return self._cx+(d and self._xdepth_3d or 0)+self._popout(i)*cos(_2rad(self._sl3d[i].mid))
    def CY(self,i,d):
        return self._cy+(d and self._ydepth_3d or 0)+self._popout(i)*sin(_2rad(self._sl3d[i].mid))
    def OX(self,i,o,d):
        return self.CX(i,d)+self._radiusx*cos(_2rad(o))
    def OY(self,i,o,d):
        return self.CY(i,d)+self._radiusy*sin(_2rad(o))

    def rad_dist(self,a):
        _3dva = self._3dva
        return min(abs(a-_3dva),abs(a-_3dva+360))

    def __init__(self):
        self.x = 0
        self.y = 0
        self.width = 300
        self.height = 200
        self.data = [12.50,20.10,2.00,22.00,5.00,18.00,13.00]
        self.labels = None  # or list of strings
        self.startAngle = 90
        self.direction = "clockwise"
        self.simpleLabels = 1
        self.slices = TypedPropertyCollection(Wedge3dProperties)
        self.slices[0].fillColor = colors.darkcyan
        self.slices[1].fillColor = colors.blueviolet
        self.slices[2].fillColor = colors.blue
        self.slices[3].fillColor = colors.cyan
        self.slices[4].fillColor = colors.azure
        self.slices[5].fillColor = colors.crimson
        self.slices[6].fillColor = colors.darkviolet

    def _fillSide(self,L,i,angle,strokeColor,strokeWidth,fillColor):
        rd = self.rad_dist(angle)
        if rd<self.rad_dist(self._sl3d[i].mid):
            p = [self.CX(i,0),self.CY(i,0),
                self.CX(i,1),self.CY(i,1),
                self.OX(i,angle,1),self.OY(i,angle,1),
                self.OX(i,angle,0),self.OY(i,angle,0)]
            L.append((rd,Polygon(p, strokeColor=strokeColor, fillColor=fillColor,strokeWidth=strokeWidth,strokeLineJoin=1)))

    def draw(self):
        slices = self.slices
        _3d_angle = self.angle_3d
        _3dva = self._3dva = _360(_3d_angle+90)
        a0 = _2rad(_3dva)
        self._xdepth_3d = cos(a0)*self.depth_3d
        self._ydepth_3d = sin(a0)*self.depth_3d
        self._cx = self.x+self.width/2.0
        self._cy = self.y+(self.height - self._ydepth_3d)/2.0
        radius = self._radius = self._cx-self.x
        self._radiusx = radiusx = radius
        self._radiusy = radiusy = (1.0 - self.perspective/100.0)*radius
        data = self.normalizeData()
        sum = self._sum

        CX = self.CX
        CY = self.CY
        OX = self.OX
        OY = self.OY
        rad_dist = self.rad_dist
        _fillSide = self._fillSide
        n = len(data)
        _sl3d = self._sl3d = []
        g = Group()
        last = _360(self.startAngle)
        a0 = self.direction=='clockwise' and -1 or 1
        for v in data:
            v *= a0
            angle1, angle0 = last, v+last
            last = angle0
            if a0>0: angle0, angle1 = angle1, angle0
            _sl3d.append(_SL3D(angle0,angle1))
            #print '%d: %.2f %.2f --> %s' %(len(_sl3d)-1,angle0,angle1,_sl3d[-1])

        labels = _fixLabels(self.labels,n)
        a0 = _3d_angle
        a1 = _3d_angle+180
        T = []
        S = []
        L = []

        class WedgeLabel3d(WedgeLabel):
            def _checkDXY(self,ba):
                if ba[0]=='n':
                    if not hasattr(self,'_ody'):
                        self._ody = self.dy
                        self.dy = -self._ody + self._ydepth_3d
        WedgeLabel3d._ydepth_3d = self._ydepth_3d

        for i in xrange(n):
            style = slices[i]
            if not style.visible: continue
            sl = _sl3d[i]
            lo = angle0 = sl.lo
            hi = angle1 = sl.hi
            if abs(hi-lo)<=1e-7: continue
            fillColor = _getShaded(style.fillColor,style.fillColorShaded,style.shading)
            strokeColor = _getShaded(style.strokeColor,style.strokeColorShaded,style.shading) or fillColor
            strokeWidth = style.strokeWidth
            cx0 = CX(i,0)
            cy0 = CY(i,0)
            cx1 = CX(i,1)
            cy1 = CY(i,1)
            #background shaded pie bottom
            g.add(Wedge(cx1,cy1,radiusx, lo, hi,yradius=radiusy,
                            strokeColor=strokeColor,strokeWidth=strokeWidth,fillColor=fillColor,
                            strokeLineJoin=1))
            #connect to top
            if lo < a0 < hi: angle0 = a0
            if lo < a1 < hi: angle1 = a1
            if 1:
                p = ArcPath(strokeColor=strokeColor, fillColor=fillColor,strokeWidth=strokeWidth,strokeLineJoin=1)
                p.addArc(cx1,cy1,radiusx,angle0,angle1,yradius=radiusy,moveTo=1)
                p.lineTo(OX(i,angle1,0),OY(i,angle1,0))
                p.addArc(cx0,cy0,radiusx,angle0,angle1,yradius=radiusy,reverse=1)
                p.closePath()
                if angle0<=_3dva and angle1>=_3dva:
                    rd = 0
                else:
                    rd = min(rad_dist(angle0),rad_dist(angle1))
                S.append((rd,p))
            _fillSide(S,i,lo,strokeColor,strokeWidth,fillColor)
            _fillSide(S,i,hi,strokeColor,strokeWidth,fillColor)

            #bright shaded top
            fillColor = style.fillColor
            strokeColor = style.strokeColor or fillColor
            T.append(Wedge(cx0,cy0,radiusx,lo,hi,yradius=radiusy,
                            strokeColor=strokeColor,strokeWidth=strokeWidth,fillColor=fillColor,strokeLineJoin=1))

            text = labels[i]
            if text:
                rat = style.labelRadius
                self._radiusx *= rat
                self._radiusy *= rat
                mid = sl.mid
                _addWedgeLabel(self,text,L.append,mid,OX(i,mid,0),OY(i,mid,0),style,labelClass=WedgeLabel3d)
                self._radiusx = radiusx
                self._radiusy = radiusy

        S.sort(lambda a,b: -cmp(a[0],b[0]))
        map(g.add,map(lambda x:x[1],S)+T+L)
        return g

    def demo(self):
        d = Drawing(200, 100)

        pc = Pie()
        pc.x = 50
        pc.y = 10
        pc.width = 100
        pc.height = 80
        pc.data = [10,20,30,40,50,60]
        pc.labels = ['a','b','c','d','e','f']

        pc.slices.strokeWidth=0.5
        pc.slices[3].popout = 10
        pc.slices[3].strokeWidth = 2
        pc.slices[3].strokeDashArray = [2,2]
        pc.slices[3].labelRadius = 1.75
        pc.slices[3].fontColor = colors.red
        pc.slices[0].fillColor = colors.darkcyan
        pc.slices[1].fillColor = colors.blueviolet
        pc.slices[2].fillColor = colors.blue
        pc.slices[3].fillColor = colors.cyan
        pc.slices[4].fillColor = colors.aquamarine
        pc.slices[5].fillColor = colors.cadetblue
        pc.slices[6].fillColor = colors.lightcoral
        self.slices[1].visible = 0
        self.slices[3].visible = 1
        self.slices[4].visible = 1
        self.slices[5].visible = 1
        self.slices[6].visible = 0

        d.add(pc)
        return d


def sample0a():
    "Make a degenerated pie chart with only one slice."

    d = Drawing(400, 200)

    pc = Pie()
    pc.x = 150
    pc.y = 50
    pc.data = [10]
    pc.labels = ['a']
    pc.slices.strokeWidth=1#0.5

    d.add(pc)

    return d


def sample0b():
    "Make a degenerated pie chart with only one slice."

    d = Drawing(400, 200)

    pc = Pie()
    pc.x = 150
    pc.y = 50
    pc.width = 120
    pc.height = 100
    pc.data = [10]
    pc.labels = ['a']
    pc.slices.strokeWidth=1#0.5

    d.add(pc)

    return d


def sample1():
    "Make a typical pie chart with with one slice treated in a special way."

    d = Drawing(400, 200)

    pc = Pie()
    pc.x = 150
    pc.y = 50
    pc.data = [10, 20, 30, 40, 50, 60]
    pc.labels = ['a', 'b', 'c', 'd', 'e', 'f']

    pc.slices.strokeWidth=1#0.5
    pc.slices[3].popout = 20
    pc.slices[3].strokeWidth = 2
    pc.slices[3].strokeDashArray = [2,2]
    pc.slices[3].labelRadius = 1.75
    pc.slices[3].fontColor = colors.red

    d.add(pc)

    return d


def sample2():
    "Make a pie chart with nine slices."

    d = Drawing(400, 200)

    pc = Pie()
    pc.x = 125
    pc.y = 25
    pc.data = [0.31, 0.148, 0.108,
               0.076, 0.033, 0.03,
               0.019, 0.126, 0.15]
    pc.labels = ['1', '2', '3', '4', '5', '6', '7', '8', 'X']

    pc.width = 150
    pc.height = 150
    pc.slices.strokeWidth=1#0.5

    pc.slices[0].fillColor = colors.steelblue
    pc.slices[1].fillColor = colors.thistle
    pc.slices[2].fillColor = colors.cornflower
    pc.slices[3].fillColor = colors.lightsteelblue
    pc.slices[4].fillColor = colors.aquamarine
    pc.slices[5].fillColor = colors.cadetblue
    pc.slices[6].fillColor = colors.lightcoral
    pc.slices[7].fillColor = colors.tan
    pc.slices[8].fillColor = colors.darkseagreen

    d.add(pc)

    return d


def sample3():
    "Make a pie chart with a very slim slice."

    d = Drawing(400, 200)

    pc = Pie()
    pc.x = 125
    pc.y = 25

    pc.data = [74, 1, 25]

    pc.width = 150
    pc.height = 150
    pc.slices.strokeWidth=1#0.5
    pc.slices[0].fillColor = colors.steelblue
    pc.slices[1].fillColor = colors.thistle
    pc.slices[2].fillColor = colors.cornflower

    d.add(pc)

    return d


def sample4():
    "Make a pie chart with several very slim slices."

    d = Drawing(400, 200)

    pc = Pie()
    pc.x = 125
    pc.y = 25

    pc.data = [74, 1, 1, 1, 1, 22]

    pc.width = 150
    pc.height = 150
    pc.slices.strokeWidth=1#0.5
    pc.slices[0].fillColor = colors.steelblue
    pc.slices[1].fillColor = colors.thistle
    pc.slices[2].fillColor = colors.cornflower
    pc.slices[3].fillColor = colors.lightsteelblue
    pc.slices[4].fillColor = colors.aquamarine
    pc.slices[5].fillColor = colors.cadetblue

    d.add(pc)

    return d
