#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/test/test_graphics_charts.py
"""
Tests for chart class.
"""

import os, sys, copy
from os.path import join, basename, splitext

from reportlab.test import unittest
from reportlab.test.utils import makeSuiteForClasses, outputfile, printLocation
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.validators import Auto
from reportlab.pdfgen.canvas import Canvas
from reportlab.graphics.shapes import *
from reportlab.graphics.charts.textlabels import Label
from reportlab.platypus.flowables import Spacer, PageBreak
from reportlab.platypus.paragraph import Paragraph
from reportlab.platypus.xpreformatted import XPreformatted
from reportlab.platypus.frames import Frame
from reportlab.platypus.doctemplate \
     import PageTemplate, BaseDocTemplate

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.spider import SpiderChart
from reportlab.graphics.widgets.markers import makeMarker



def myMainPageFrame(canvas, doc):
    "The page frame used for all PDF documents."

    canvas.saveState()

    #canvas.rect(2.5*cm, 2.5*cm, 15*cm, 25*cm)
    canvas.setFont('Times-Roman', 12)
    pageNumber = canvas.getPageNumber()
    canvas.drawString(10*cm, cm, str(pageNumber))

    canvas.restoreState()


class MyDocTemplate(BaseDocTemplate):
    "The document template used for all PDF documents."

    _invalidInitArgs = ('pageTemplates',)

    def __init__(self, filename, **kw):
        frame1 = Frame(2.5*cm, 2.5*cm, 15*cm, 25*cm, id='F1')
        self.allowSplitting = 0
        apply(BaseDocTemplate.__init__, (self, filename), kw)
        template = PageTemplate('normal', [frame1], myMainPageFrame)
        self.addPageTemplates(template)


def sample1bar(data=[(13, 5, 20, 22, 37, 45, 19, 4)]):
    drawing = Drawing(400, 200)

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


def sample2bar(data=[(13, 5, 20, 22, 37, 45, 19, 4),
                  (14, 6, 21, 23, 38, 46, 20, 5)]):
    return sample1bar(data)


def sample1line(data=[(13, 5, 20, 22, 37, 45, 19, 4)]):
    drawing = Drawing(400, 200)

    bc = HorizontalLineChart()
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


def sample2line(data=[(13, 5, 20, 22, 37, 45, 19, 4),
                  (14, 6, 21, 23, 38, 46, 20, 5)]):
    return sample1line(data)


def sample3(drawing=None):
    "Add sample swatches to a diagram."

    d = drawing or Drawing(400, 200)

    swatches = Legend()
    swatches.alignment = 'right'
    swatches.x = 80
    swatches.y = 160
    swatches.deltax = 60
    swatches.dxTextSpace = 10
    swatches.columnMaximum = 4
    items = [(colors.red, 'before'), (colors.green, 'after')]
    swatches.colorNamePairs = items

    d.add(swatches, 'legend')

    return d


def sample4pie():
    width = 300
    height = 150
    d = Drawing(width, height)
    pc = Pie()
    pc.x = 150
    pc.y = 50
    pc.data = [1, 50, 100, 100, 100, 100, 100, 100, 100, 50]
    pc.labels = ['0','a','b','c','d','e','f','g','h','i']
    pc.slices.strokeWidth=0.5
    pc.slices[3].popout = 20
    pc.slices[3].strokeWidth = 2
    pc.slices[3].strokeDashArray = [2,2]
    pc.slices[3].labelRadius = 1.75
    pc.slices[3].fontColor = colors.red
    d.add(pc)
    legend = Legend()
    legend.x = width-5
    legend.y = height-5
    legend.dx = 20
    legend.dy = 5
    legend.deltax = 0
    legend.boxAnchor = 'nw'
    legend.colorNamePairs=Auto(chart=pc)
    d.add(legend)
    return d

def autoLegender(i,chart,styleObj,sym='symbol'):
    if sym:
        setattr(styleObj[0],sym, makeMarker('Diamond',size=6))
        setattr(styleObj[1],sym,makeMarker('Square'))
    width = 300
    height = 150
    legend = Legend()
    legend.x = width-5
    legend.y = 5
    legend.dx = 20
    legend.dy = 5
    legend.deltay = 0
    legend.boxAnchor = 'se'
    if i=='col auto':
        legend.colorNamePairs[0]=(Auto(chart=chart),'auto chart=self.chart')
        legend.colorNamePairs[1]=(Auto(obj=chart,index=1),'auto  chart=self.chart index=1')
    elif i=='full auto':
        legend.colorNamePairs=Auto(chart=chart)
    elif i=='swatch set':
        legend.swatchMarker=makeMarker('Circle')
        legend.swatchMarker.size = 10
    elif i=='swatch auto':
        legend.swatchMarker=Auto(chart=chart)
    d = Drawing(width,height)
    d.background = Rect(0,0,width,height,strokeWidth=1,strokeColor=colors.red,fillColor=None)
    m = makeMarker('Cross')
    m.x = width-5
    m.y = 5
    m.fillColor = colors.red
    m.strokeColor = colors.yellow
    d.add(chart)
    d.add(legend)
    d.add(m)
    return d

def lpleg(i=None):
    chart = LinePlot()
    return autoLegender(i,chart,chart.lines)

def hlcleg(i=None):
    chart = HorizontalLineChart()
    return autoLegender(i,chart,chart.lines)

def bcleg(i=None):
    chart = VerticalBarChart()
    return autoLegender(i,chart,chart.bars,None)

def pcleg(i=None):
    chart = Pie()
    return autoLegender(i,chart,chart.slices,None)

def scleg(i=None):
    chart = SpiderChart()
    return autoLegender(i,chart,chart.strands,None)

def plpleg(i=None):
    from reportlab.lib.colors import pink, red, green
    pie = Pie()
    pie.x = 0
    pie.y = 0
    pie.pointerLabelMode='LeftAndRight'
    pie.slices.label_boxStrokeColor      = red
    pie.simpleLabels = 0
    pie.sameRadii = 1
    pie.data = [1, 0.1, 1.7, 4.2,0,0]
    pie.labels = ['abcdef', 'b', 'c', 'd','e','fedcba']
    pie.strokeWidth=1
    pie.strokeColor=green
    pie.slices.label_pointer_piePad      = 6
    pie.width = 160
    pie.direction = 'clockwise'
    pie.pointerLabelMode  = 'LeftRight'
    return autoLegender(i,pie,pie.slices,None)

def notFail(d):
    try:
        return d.getContents()
    except:
        import traceback
        traceback.print_exc()
        return None

STORY = []
styleSheet = getSampleStyleSheet()
bt = styleSheet['BodyText']
h1 = styleSheet['Heading1']
h2 = styleSheet['Heading2']
h3 = styleSheet['Heading3']
FINISHED = 0


class ChartTestCase(unittest.TestCase):
    "Test chart classes."

    def setUp(self):
        "Hook method for setting up the test fixture before exercising it."

        global STORY
        self.story = STORY

        if self.story == []:
            self.story.append(Paragraph('Tests for chart classes', h1))

    def tearDown(self):
        "Hook method for deconstructing the test fixture after testing it."

        if FINISHED:
            path=outputfile('test_graphics_charts.pdf')
            doc = MyDocTemplate(path)
            doc.build(self.story)

    def test0(self):
        "Test bar charts."

        story = self.story
        story.append(Paragraph('Single data row', h2))

        story.append(Spacer(0, 0.5*cm))
        drawing = sample1bar()
        story.append(drawing)
        story.append(Spacer(0, 1*cm))


    def test1(self):
        "Test bar charts."

        story = self.story
        story.append(Paragraph('Double data row', h2))

        story.append(Spacer(0, 0.5*cm))
        drawing = sample2bar()
        story.append(drawing)
        story.append(Spacer(0, 1*cm))


    def test2(self):
        "Test bar charts."

        story = self.story
        story.append(Paragraph('Double data row with legend', h2))

        story.append(Spacer(0, 0.5*cm))
        drawing = sample2bar()
        drawing = sample3(drawing)
        story.append(drawing)
        story.append(Spacer(0, 1*cm))


    def test3(self):
        "Test line charts."

        story = self.story
        story.append(Paragraph('Single data row', h2))

        story.append(Spacer(0, 0.5*cm))
        drawing = sample1line()
        story.append(drawing)
        story.append(Spacer(0, 1*cm))


    def test4(self):
        "Test line charts."

        story = self.story
        story.append(Paragraph('Single data row', h2))

        story.append(Spacer(0, 0.5*cm))
        drawing = sample2line()
        story.append(drawing)
        story.append(Spacer(0, 1*cm))

    def test4b(self):
        story = self.story
        for code in (lpleg, hlcleg, bcleg, pcleg, scleg, plpleg):
            code_name = code.func_code.co_name
            for i in ('standard', 'col auto', 'full auto', 'swatch set', 'swatch auto'):
                d = code(i)
                assert notFail(d),'getContents failed for %s %s' % (code_name,i)
                story.append(Paragraph('%s %s' % (i,code_name), h2))
                story.append(Spacer(0, 0.5*cm))
                story.append(code(i))
                story.append(Spacer(0, 1*cm))

    def test5(self):
        "Test pie charts."

        story = self.story
        story.append(Paragraph('Pie', h2))

        story.append(Spacer(0, 0.5*cm))
        drawing = sample4pie()
        story.append(drawing)
        story.append(Spacer(0, 1*cm))

    def test6(self):
        from reportlab.graphics.charts.piecharts import Pie, _makeSideArcDefs, intervalIntersection
        L = []

        def intSum(arcs,A):
            s = 0
            for a in A:
                for arc in arcs:
                    i = intervalIntersection(arc[1:],a)
                    if i: s += i[1] - i[0]
            return s

        def subtest(sa,d):
            pc = Pie()
            pc.direction=d
            pc.startAngle=sa
            arcs = _makeSideArcDefs(sa,d)
            A = [x[1] for x in pc.makeAngles()]
            arcsum = sum([a[2]-a[1] for a in arcs])
            isum = intSum(arcs,A)
            mi = max([a[2]-a[1] for a in arcs])
            ni = min([a[2]-a[1] for a in arcs])
            l = []
            s = (arcsum-360)
            if s>1e-8: l.append('Arc length=%s != 360' % s)
            s = abs(isum-360)
            if s>1e-8: l.append('interval intersection length=%s != 360' % s)
            if mi>360: l.append('max interval intersection length=%s >360' % mi)
            if ni<0: l.append('min interval intersection length=%s <0' % ni)
            if l:
                l.append('sa: %s d: %s' % (sa,d))
                l.append('sidearcs: %s' % str(arcs))
                l.append('Angles: %s' % A)
                raise ValueError('piecharts._makeSideArcDefs failure\n%s' % '\n'.join(l))

        for d in ('anticlockwise','clockwise'):
            for sa in (225, 180, 135, 90, 45, 0, -45, -90):
                subtest(sa,d)

        # This triggers the document build operation (hackish).
        global FINISHED
        FINISHED = 1

def makeSuite():
    return makeSuiteForClasses(ChartTestCase)


#noruntests
if __name__ == "__main__":
    unittest.TextTestRunner().run(makeSuite())
    printLocation()
