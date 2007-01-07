#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/graphics/charts/doughnut.py
# doughnut chart

"""Doughnut chart

Produces a circular chart like the doughnut charts produced by Excel.
Can handle multiple series (which produce concentric 'rings' in the chart).

"""
__version__=''' $Id: doughnut.py 2499 2004-12-29 17:12:34Z rgbecker $ '''

import copy
from math import sin, cos, pi
from types import ListType, TupleType
from reportlab.lib import colors
from reportlab.lib.validators import isColor, isNumber, isListOfNumbersOrNone,\
                                    isListOfNumbers, isColorOrNone, isString,\
                                    isListOfStringsOrNone, OneOf, SequenceOf,\
                                    isBoolean, isListOfColors,\
                                    isNoneOrListOfNoneOrStrings,\
                                    isNoneOrListOfNoneOrNumbers,\
                                    isNumberOrNone
from reportlab.lib.attrmap import *
from reportlab.pdfgen.canvas import Canvas
from reportlab.graphics.shapes import Group, Drawing, Line, Rect, Polygon, Ellipse, \
    Wedge, String, SolidShape, UserNode, STATE_DEFAULTS
from reportlab.graphics.widgetbase import Widget, TypedPropertyCollection, PropHolder
from reportlab.graphics.charts.piecharts import AbstractPieChart, WedgeProperties, _addWedgeLabel
from reportlab.graphics.charts.textlabels import Label
from reportlab.graphics.widgets.markers import Marker

class SectorProperties(WedgeProperties):
    """This holds descriptive information about the sectors in a doughnut chart.

    It is not to be confused with the 'sector itself'; this just holds
    a recipe for how to format one, and does not allow you to hack the
    angles.  It can format a genuine Sector object for you with its
    format method.
    """
    _attrMap = AttrMap(BASE=WedgeProperties,
            )

class Doughnut(AbstractPieChart):
    _attrMap = AttrMap(
        x = AttrMapValue(isNumber, desc='X position of the chart within its container.'),
        y = AttrMapValue(isNumber, desc='Y position of the chart within its container.'),
        width = AttrMapValue(isNumber, desc='width of doughnut bounding box. Need not be same as width.'),
        height = AttrMapValue(isNumber, desc='height of doughnut bounding box.  Need not be same as height.'),
        data = AttrMapValue(None, desc='list of numbers defining sector sizes; need not sum to 1'),
        labels = AttrMapValue(isListOfStringsOrNone, desc="optional list of labels to use for each data point"),
        startAngle = AttrMapValue(isNumber, desc="angle of first slice; like the compass, 0 is due North"),
        direction = AttrMapValue(OneOf('clockwise', 'anticlockwise'), desc="'clockwise' or 'anticlockwise'"),
        slices = AttrMapValue(None, desc="collection of sector descriptor objects"),
        simpleLabels = AttrMapValue(isBoolean, desc="If true(default) use String not super duper WedgeLabel"),
        )

    def __init__(self):
        self.x = 0
        self.y = 0
        self.width = 100
        self.height = 100
        self.data = [1,1]
        self.labels = None  # or list of strings
        self.startAngle = 90
        self.direction = "clockwise"
        self.simpleLabels = 1

        self.slices = TypedPropertyCollection(SectorProperties)
        self.slices[0].fillColor = colors.darkcyan
        self.slices[1].fillColor = colors.blueviolet
        self.slices[2].fillColor = colors.blue
        self.slices[3].fillColor = colors.cyan

    def demo(self):
        d = Drawing(200, 100)

        dn = Doughnut()
        dn.x = 50
        dn.y = 10
        dn.width = 100
        dn.height = 80
        dn.data = [10,20,30,40,50,60]
        dn.labels = ['a','b','c','d','e','f']

        dn.slices.strokeWidth=0.5
        dn.slices[3].popout = 10
        dn.slices[3].strokeWidth = 2
        dn.slices[3].strokeDashArray = [2,2]
        dn.slices[3].labelRadius = 1.75
        dn.slices[3].fontColor = colors.red
        dn.slices[0].fillColor = colors.darkcyan
        dn.slices[1].fillColor = colors.blueviolet
        dn.slices[2].fillColor = colors.blue
        dn.slices[3].fillColor = colors.cyan
        dn.slices[4].fillColor = colors.aquamarine
        dn.slices[5].fillColor = colors.cadetblue
        dn.slices[6].fillColor = colors.lightcoral

        d.add(dn)
        return d

    def normalizeData(self, data=None):
        from operator import add
        sum = float(reduce(add,data,0))
        return abs(sum)>=1e-8 and map(lambda x,f=360./sum: f*x, data) or len(data)*[0]

    def makeSectors(self):
        # normalize slice data
        if type(self.data) in (ListType, TupleType) and type(self.data[0]) in (ListType, TupleType):
            #it's a nested list, more than one sequence
            normData = []
            n = []
            for l in self.data:
                t = self.normalizeData(l)
                normData.append(t)
                n.append(len(t))
            self._seriesCount = max(n)
        else:
            normData = self.normalizeData(self.data)
            n = len(normData)
            self._seriesCount = n

        #labels
        if self.labels is None:
            labels = []
            if type(n) not in (ListType,TupleType):
                labels = [''] * n
            else:
                for m in n:
                    labels = list(labels) + [''] * m
        else:
            labels = self.labels
            #there's no point in raising errors for less than enough labels if
            #we silently create all for the extreme case of no labels.
            if type(n) not in (ListType,TupleType):
                i = n-len(labels)
                if i>0:
                    labels = list(labels) + [''] * i
            else:
                tlab = 0
                for m in n:
                    tlab = tlab+m
                i = tlab-len(labels)
                if i>0:
                    labels = list(labels) + [''] * i

        xradius = self.width/2.0
        yradius = self.height/2.0
        centerx = self.x + xradius
        centery = self.y + yradius

        if self.direction == "anticlockwise":
            whichWay = 1
        else:
            whichWay = -1

        g  = Group()
        sn = 0

        startAngle = self.startAngle #% 360
        styleCount = len(self.slices)
        if type(self.data[0]) in (ListType, TupleType):
            #multi-series doughnut
            iradius = (self.height/5.0)/len(self.data)
            for series in normData:
                i = 0
                for angle in series:
                    endAngle = (startAngle + (angle * whichWay)) #% 360
                    if abs(startAngle-endAngle)>=1e-5:
                        if startAngle < endAngle:
                            a1 = startAngle
                            a2 = endAngle
                        else:
                            a1 = endAngle
                            a2 = startAngle

                    #if we didn't use %stylecount here we'd end up with the later sectors
                    #all having the default style
                    sectorStyle = self.slices[i%styleCount]

                    # is it a popout?
                    cx, cy = centerx, centery
                    if sectorStyle.popout != 0:
                        # pop out the sector
                        averageAngle = (a1+a2)/2.0
                        aveAngleRadians = averageAngle * pi/180.0
                        popdistance = sectorStyle.popout
                        cx = centerx + popdistance * cos(aveAngleRadians)
                        cy = centery + popdistance * sin(aveAngleRadians)

                    if type(n) in (ListType,TupleType):
                        theSector = Wedge(cx, cy, xradius+(sn*iradius)-iradius, a1, a2, yradius=yradius+(sn*iradius)-iradius, radius1=yradius+(sn*iradius)-(2*iradius))
                    else:
                        theSector = Wedge(cx, cy, xradius, a1, a2, yradius=yradius, radius1=iradius)

                    theSector.fillColor = sectorStyle.fillColor
                    theSector.strokeColor = sectorStyle.strokeColor
                    theSector.strokeWidth = sectorStyle.strokeWidth
                    theSector.strokeDashArray = sectorStyle.strokeDashArray

                    g.add(theSector)
                    startAngle = endAngle

                    text = self.getSeriesName(i,'')
                    if text:
                        averageAngle = (a1+a2)/2.0
                        aveAngleRadians = averageAngle*pi/180.0
                        labelRadius = sectorStyle.labelRadius
                        labelX = centerx + (0.5 * self.width * cos(aveAngleRadians) * labelRadius)
                        labelY = centery + (0.5 * self.height * sin(aveAngleRadians) * labelRadius)
                        _addWedgeLabel(self,text,g.add,averageAngle,labelX,labelY,sectorStyle)
                    i = i + 1
                sn = sn + 1

        else:
            i = 0
            #single series doughnut
            iradius = self.height/5.0
            for angle in normData:
                endAngle = (startAngle + (angle * whichWay)) #% 360
                if abs(startAngle-endAngle)>=1e-5:
                    if startAngle < endAngle:
                        a1 = startAngle
                        a2 = endAngle
                    else:
                        a1 = endAngle
                        a2 = startAngle

                #if we didn't use %stylecount here we'd end up with the later sectors
                #all having the default style
                sectorStyle = self.slices[i%styleCount]

                # is it a popout?
                cx, cy = centerx, centery
                if sectorStyle.popout != 0:
                    # pop out the sector
                    averageAngle = (a1+a2)/2.0
                    aveAngleRadians = averageAngle * pi/180.0
                    popdistance = sectorStyle.popout
                    cx = centerx + popdistance * cos(aveAngleRadians)
                    cy = centery + popdistance * sin(aveAngleRadians)

                if n > 1:
                    theSector = Wedge(cx, cy, xradius, a1, a2, yradius=yradius, radius1=iradius)
                elif n==1:
                    theSector = Wedge(cx, cy, xradius, a1, a2, yradius=yradius, iradius=iradius)

                theSector.fillColor = sectorStyle.fillColor
                theSector.strokeColor = sectorStyle.strokeColor
                theSector.strokeWidth = sectorStyle.strokeWidth
                theSector.strokeDashArray = sectorStyle.strokeDashArray

                g.add(theSector)

                # now draw a label
                if labels[i] != "":
                    averageAngle = (a1+a2)/2.0
                    aveAngleRadians = averageAngle*pi/180.0
                    labelRadius = sectorStyle.labelRadius
                    labelX = centerx + (0.5 * self.width * cos(aveAngleRadians) * labelRadius)
                    labelY = centery + (0.5 * self.height * sin(aveAngleRadians) * labelRadius)

                    theLabel = String(labelX, labelY, labels[i])
                    theLabel.textAnchor = "middle"
                    theLabel.fontSize = sectorStyle.fontSize
                    theLabel.fontName = sectorStyle.fontName
                    theLabel.fillColor = sectorStyle.fontColor

                    g.add(theLabel)

                startAngle = endAngle
                i = i + 1

        return g

    def draw(self):
        g = Group()
        g.add(self.makeSectors())
        return g


def sample1():
    "Make up something from the individual Sectors"

    d = Drawing(400, 400)
    g = Group()

    s1 = Wedge(centerx=200, centery=200, radius=150, startangledegrees=0, endangledegrees=120, radius1=100)
    s1.fillColor=colors.red
    s1.strokeColor=None
    d.add(s1)
    s2 = Wedge(centerx=200, centery=200, radius=150, startangledegrees=120, endangledegrees=240, radius1=100)
    s2.fillColor=colors.green
    s2.strokeColor=None
    d.add(s2)
    s3 = Wedge(centerx=200, centery=200, radius=150, startangledegrees=240, endangledegrees=260, radius1=100)
    s3.fillColor=colors.blue
    s3.strokeColor=None
    d.add(s3)
    s4 = Wedge(centerx=200, centery=200, radius=150, startangledegrees=260, endangledegrees=360, radius1=100)
    s4.fillColor=colors.gray
    s4.strokeColor=None
    d.add(s4)

    return d

def sample2():
    "Make a simple demo"

    d = Drawing(400, 400)

    dn = Doughnut()
    dn.x = 50
    dn.y = 50
    dn.width = 300
    dn.height = 300
    dn.data = [10,20,30,40,50,60]

    d.add(dn)

    return d

def sample3():
    "Make a more complex demo"

    d = Drawing(400, 400)
    dn = Doughnut()
    dn.x = 50
    dn.y = 50
    dn.width = 300
    dn.height = 300
    dn.data = [[10,20,30,40,50,60], [10,20,30,40]]
    dn.labels = ['a','b','c','d','e','f']

    d.add(dn)

    return d

if __name__=='__main__':

    from reportlab.graphics.renderPDF import drawToFile
    d = sample1()
    drawToFile(d, 'doughnut1.pdf')
    d = sample2()
    drawToFile(d, 'doughnut2.pdf')
    d = sample3()
    drawToFile(d, 'doughnut3.pdf')
