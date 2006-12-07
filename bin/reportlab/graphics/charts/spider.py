    #Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/graphics/charts/spider.py
# spider chart, also known as radar chart

"""Spider Chart

Normal use shows variation of 5-10 parameters against some 'norm' or target.
When there is more than one series, place the series with the largest
numbers first, as it will be overdrawn by each successive one.
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
from reportlab.graphics.shapes import Group, Drawing, Line, Rect, Polygon, Ellipse, \
    Wedge, String, STATE_DEFAULTS
from reportlab.graphics.widgetbase import Widget, TypedPropertyCollection, PropHolder
from reportlab.graphics.charts.areas import PlotArea
from piecharts import WedgeLabel
from reportlab.graphics.widgets.markers import makeMarker, uSymbol2Symbol

class StrandProperties(PropHolder):
    """This holds descriptive information about concentric 'strands'.

    Line style, whether filled etc.
    """

    _attrMap = AttrMap(
        strokeWidth = AttrMapValue(isNumber),
        fillColor = AttrMapValue(isColorOrNone),
        strokeColor = AttrMapValue(isColorOrNone),
        strokeDashArray = AttrMapValue(isListOfNumbersOrNone),
        fontName = AttrMapValue(isString),
        fontSize = AttrMapValue(isNumber),
        fontColor = AttrMapValue(isColorOrNone),
        labelRadius = AttrMapValue(isNumber),
        markers = AttrMapValue(isBoolean),
        markerType = AttrMapValue(isAnything),
        markerSize = AttrMapValue(isNumber),
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
        self.fontName = STATE_DEFAULTS["fontName"]
        self.fontSize = STATE_DEFAULTS["fontSize"]
        self.fontColor = STATE_DEFAULTS["fillColor"]
        self.labelRadius = 1.2
        self.markers = 0
        self.markerType = None
        self.markerSize = 0
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

class SpiderChart(PlotArea):
    _attrMap = AttrMap(BASE=PlotArea,
        data = AttrMapValue(None, desc='Data to be plotted, list of (lists of) numbers.'),
        labels = AttrMapValue(isListOfStringsOrNone, desc="optional list of labels to use for each data point"),
        startAngle = AttrMapValue(isNumber, desc="angle of first slice; like the compass, 0 is due North"),
        direction = AttrMapValue( OneOf('clockwise', 'anticlockwise'), desc="'clockwise' or 'anticlockwise'"),
        strands = AttrMapValue(None, desc="collection of strand descriptor objects"),
        )

    def __init__(self):
        PlotArea.__init__(self)

        self.data = [[10,12,14,16,14,12], [6,8,10,12,9,11]]
        self.labels = None  # or list of strings
        self.startAngle = 90
        self.direction = "clockwise"

        self.strands = TypedPropertyCollection(StrandProperties)
        self.strands[0].fillColor = colors.cornsilk
        self.strands[1].fillColor = colors.cyan


    def demo(self):
        d = Drawing(200, 100)

        sp = SpiderChart()
        sp.x = 50
        sp.y = 10
        sp.width = 100
        sp.height = 80
        sp.data = [[10,12,14,16,18,20],[6,8,4,6,8,10]]
        sp.labels = ['a','b','c','d','e','f']

        d.add(sp)
        return d

    def normalizeData(self, outer = 0.0):
        """Turns data into normalized ones where each datum is < 1.0,
        and 1.0 = maximum radius.  Adds 10% at outside edge by default"""
        data = self.data
        theMax = 0.0
        for row in data:
            for element in row:
                assert element >=0, "Cannot do spider plots of negative numbers!"
                if element > theMax:
                    theMax = element
        theMax = theMax * (1.0+outer)

        scaled = []
        for row in data:
            scaledRow = []
            for element in row:
                scaledRow.append(element / theMax)
            scaled.append(scaledRow)
        return scaled


    def draw(self):
        # normalize slice data
        g = self.makeBackground() or Group()

        xradius = self.width/2.0
        yradius = self.height/2.0
        self._radius = radius = min(xradius, yradius)
        centerx = self.x + xradius
        centery = self.y + yradius

        data = self.normalizeData()

        n = len(data[0])

        #labels
        if self.labels is None:
            labels = [''] * n
        else:
            labels = self.labels
            #there's no point in raising errors for less than enough errors if
            #we silently create all for the extreme case of no labels.
            i = n-len(labels)
            if i>0:
                labels = labels + ['']*i

        spokes = []
        csa = []
        angle = self.startAngle*pi/180
        direction = self.direction == "clockwise" and -1 or 1
        angleBetween = direction*(2 * pi)/n
        markers = self.strands.markers
        for i in xrange(n):
            car = cos(angle)*radius
            sar = sin(angle)*radius
            csa.append((car,sar,angle))
            spoke = Line(centerx, centery, centerx + car, centery + sar, strokeWidth = 0.5)
            #print 'added spoke (%0.2f, %0.2f) -> (%0.2f, %0.2f)' % (spoke.x1, spoke.y1, spoke.x2, spoke.y2)
            spokes.append(spoke)
            if labels:
                si = self.strands[i]
                text = si.label_text
                if text is None: text = labels[i]
                if text:
                    labelRadius = si.labelRadius
                    L = WedgeLabel()
                    L.x = centerx + labelRadius*car
                    L.y = centery + labelRadius*sar
                    L.boxAnchor = si.label_boxAnchor
                    L._pmv = angle*180/pi
                    L.dx = si.label_dx
                    L.dy = si.label_dy
                    L.angle = si.label_angle
                    L.boxAnchor = si.label_boxAnchor
                    L.boxStrokeColor = si.label_boxStrokeColor
                    L.boxStrokeWidth = si.label_boxStrokeWidth
                    L.boxFillColor = si.label_boxFillColor
                    L.strokeColor = si.label_strokeColor
                    L.strokeWidth = si.label_strokeWidth
                    L._text = text
                    L.leading = si.label_leading
                    L.width = si.label_width
                    L.maxWidth = si.label_maxWidth
                    L.height = si.label_height
                    L.textAnchor = si.label_textAnchor
                    L.visible = si.label_visible
                    L.topPadding = si.label_topPadding
                    L.leftPadding = si.label_leftPadding
                    L.rightPadding = si.label_rightPadding
                    L.bottomPadding = si.label_bottomPadding
                    L.fontName = si.fontName
                    L.fontSize = si.fontSize
                    L.fillColor = si.fontColor
                    spokes.append(L)
            angle = angle + angleBetween

        # now plot the polygons

        rowIdx = 0
        for row in data:
            # series plot
            points = []
            car, sar = csa[-1][:2]
            r = row[-1]
            points.append(centerx+car*r)
            points.append(centery+sar*r)
            for i in xrange(n):
                car, sar = csa[i][:2]
                r = row[i]
                points.append(centerx+car*r)
                points.append(centery+sar*r)

                # make up the 'strand'
                strand = Polygon(points)
                strand.fillColor = self.strands[rowIdx].fillColor
                strand.strokeColor = self.strands[rowIdx].strokeColor
                strand.strokeWidth = self.strands[rowIdx].strokeWidth
                strand.strokeDashArray = self.strands[rowIdx].strokeDashArray

                g.add(strand)

                # put in a marker, if it needs one
                if markers:
                    if hasattr(self.strands[rowIdx], 'markerType'):
                        uSymbol = self.strands[rowIdx].markerType
                    elif hasattr(self.strands, 'markerType'):
                        uSymbol = self.strands.markerType
                    else:
                        uSymbol = None
                    m_x =  centerx+car*r
                    m_y = centery+sar*r
                    m_size = self.strands[rowIdx].markerSize
                    m_fillColor = self.strands[rowIdx].fillColor
                    m_strokeColor = self.strands[rowIdx].strokeColor
                    m_strokeWidth = self.strands[rowIdx].strokeWidth
                    m_angle = 0
                    if type(uSymbol) is type(''):
                        symbol = makeMarker(uSymbol,
                                    size = m_size,
                                    x =  m_x,
                                    y = m_y,
                                    fillColor = m_fillColor,
                                    strokeColor = m_strokeColor,
                                    strokeWidth = m_strokeWidth,
                                    angle = m_angle,
                                    )
                    else:
                        symbol = uSymbol2Symbol(uSymbol,m_x,m_y,m_fillColor)
                        for k,v in (('size', m_size), ('fillColor', m_fillColor),
                                    ('x', m_x), ('y', m_y),
                                    ('strokeColor',m_strokeColor), ('strokeWidth',m_strokeWidth),
                                    ('angle',m_angle),):
                            try:
                                setattr(uSymbol,k,v)
                            except:
                                pass
                    g.add(symbol)

            rowIdx = rowIdx + 1

        # spokes go over strands
        for spoke in spokes:
            g.add(spoke)
        return g

def sample1():
    "Make a simple spider chart"

    d = Drawing(400, 400)

    pc = SpiderChart()
    pc.x = 50
    pc.y = 50
    pc.width = 300
    pc.height = 300
    pc.data = [[10,12,14,16,14,12], [6,8,10,12,9,15],[7,8,17,4,12,8,3]]
    pc.labels = ['a','b','c','d','e','f']
    pc.strands[2].fillColor=colors.palegreen

    d.add(pc)

    return d


def sample2():
    "Make a spider chart with markers, but no fill"

    d = Drawing(400, 400)

    pc = SpiderChart()
    pc.x = 50
    pc.y = 50
    pc.width = 300
    pc.height = 300
    pc.data = [[10,12,14,16,14,12], [6,8,10,12,9,15],[7,8,17,4,12,8,3]]
    pc.labels = ['U','V','W','X','Y','Z']
    pc.strands.strokeWidth = 2
    pc.strands[0].fillColor = None
    pc.strands[1].fillColor = None
    pc.strands[2].fillColor = None
    pc.strands[0].strokeColor = colors.red
    pc.strands[1].strokeColor = colors.blue
    pc.strands[2].strokeColor = colors.green
    pc.strands.markers = 1
    pc.strands.markerType = "FilledDiamond"
    pc.strands.markerSize = 6

    d.add(pc)

    return d


if __name__=='__main__':
    d = sample1()
    from reportlab.graphics.renderPDF import drawToFile
    drawToFile(d, 'spider.pdf')
    d = sample2()
    drawToFile(d, 'spider2.pdf')
    #print 'saved spider.pdf'
