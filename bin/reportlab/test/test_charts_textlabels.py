#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/test/test_charts_textlabels.py
"""
Tests for the text Label class.
"""

import os, sys, copy
from os.path import join, basename, splitext

from reportlab.test import unittest
from reportlab.test.utils import makeSuiteForClasses, outputfile, printLocation
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen.canvas import Canvas
from reportlab.graphics.shapes import *
from reportlab.graphics.charts.textlabels import Label
from reportlab.platypus.flowables import Spacer, PageBreak
from reportlab.platypus.paragraph import Paragraph
from reportlab.platypus.xpreformatted import XPreformatted
from reportlab.platypus.frames import Frame
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate


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


class LabelTestCase(unittest.TestCase):
    "Test Label class."

    def _test0(self):
        "Perform original test function."

        pdfPath = outputfile('test_charts_textlabels.pdf')
        c = Canvas(pdfPath)

        label = Label()
        demoLabel = label.demo()
        demoLabel.drawOn(c, 0, 0)

        c.save()


    def _makeProtoLabel(self):
        "Return a label prototype for further modification."

        protoLabel = Label()
        protoLabel.dx = 0
        protoLabel.dy = 0
        protoLabel.boxStrokeWidth = 0.1
        protoLabel.boxStrokeColor = colors.black
        protoLabel.boxFillColor = colors.yellow
        # protoLabel.text = 'Hello World!' # Does not work as expected.

        return protoLabel


    def _makeDrawings(self, protoLabel, text=None):
        # Set drawing dimensions.
        w, h = drawWidth, drawHeight = 400, 100

        drawings = []

        for boxAnchors in ('sw se nw ne', 'w e n s', 'c'):
            boxAnchors = string.split(boxAnchors, ' ')

            # Create drawing.
            d = Drawing(w, h)
            d.add(Line(0,h/2, w, h/2, strokeColor=colors.gray, strokeWidth=0.5))
            d.add(Line(w/2,0, w/2, h, strokeColor=colors.gray, strokeWidth=0.5))

            labels = []
            for boxAnchor in boxAnchors:
                # Modify label, put it on a drawing.
                label = copy.deepcopy(protoLabel)
                label.boxAnchor = boxAnchor
                args = {'ba':boxAnchor, 'text':text or 'Hello World!'}
                label.setText('(%(ba)s) %(text)s (%(ba)s)' % args)
                labels.append(label)

            for label in labels:
                d.add(label)

            drawings.append(d)

        return drawings


    def test1(self):
        "Test all different box anchors."

        # Build story.
        story = []
        styleSheet = getSampleStyleSheet()
        bt = styleSheet['BodyText']
        h1 = styleSheet['Heading1']
        h2 = styleSheet['Heading2']
        h3 = styleSheet['Heading3']

        story.append(Paragraph('Tests for class <i>Label</i>', h1))
        story.append(Paragraph('Testing box anchors', h2))
        story.append(Paragraph("""This should display "Hello World" labels
written as black text on a yellow box relative to the origin of the crosshair
axes. The labels indicate their relative position being one of the nine
canonical points of a box: sw, se, nw, ne, w, e, n, s or c (standing for
<i>southwest</i>, <i>southeast</i>... and <i>center</i>).""", bt))
        story.append(Spacer(0, 0.5*cm))

        # Round 1a
        story.append(Paragraph('Helvetica 10pt', h3))
        story.append(Spacer(0, 0.5*cm))

        w, h = drawWidth, drawHeight = 400, 100
        protoLabel = self._makeProtoLabel()
        protoLabel.setOrigin(drawWidth/2, drawHeight/2)
        protoLabel.textAnchor = 'start'
        protoLabel.fontName = 'Helvetica'
        protoLabel.fontSize = 10
        drawings = self._makeDrawings(protoLabel)
        for d in drawings:
            story.append(d)
            story.append(Spacer(0, 1*cm))

        story.append(PageBreak())

        # Round 1b
        story.append(Paragraph('Helvetica 18pt', h3))
        story.append(Spacer(0, 0.5*cm))

        w, h = drawWidth, drawHeight = 400, 100
        protoLabel = self._makeProtoLabel()
        protoLabel.setOrigin(drawWidth/2, drawHeight/2)
        protoLabel.textAnchor = 'start'
        protoLabel.fontName = 'Helvetica'
        protoLabel.fontSize = 18
        drawings = self._makeDrawings(protoLabel)
        for d in drawings:
            story.append(d)
            story.append(Spacer(0, 1*cm))

        story.append(PageBreak())

        # Round 1c
        story.append(Paragraph('Helvetica 18pt, multi-line', h3))
        story.append(Spacer(0, 0.5*cm))

        w, h = drawWidth, drawHeight = 400, 100
        protoLabel = self._makeProtoLabel()
        protoLabel.setOrigin(drawWidth/2, drawHeight/2)
        protoLabel.textAnchor = 'start'
        protoLabel.fontName = 'Helvetica'
        protoLabel.fontSize = 18
        drawings = self._makeDrawings(protoLabel, text='Hello\nWorld!')
        for d in drawings:
            story.append(d)
            story.append(Spacer(0, 1*cm))

        story.append(PageBreak())

        story.append(Paragraph('Testing text (and box) anchors', h2))
        story.append(Paragraph("""This should display labels as before,
but now with a fixes size and showing some effect of setting the
textAnchor attribute.""", bt))
        story.append(Spacer(0, 0.5*cm))

        # Round 2a
        story.append(Paragraph("Helvetica 10pt, textAnchor='start'", h3))
        story.append(Spacer(0, 0.5*cm))

        w, h = drawWidth, drawHeight = 400, 100
        protoLabel = self._makeProtoLabel()
        protoLabel.setOrigin(drawWidth/2, drawHeight/2)
        protoLabel.width = 4*cm
        protoLabel.height = 1.5*cm
        protoLabel.textAnchor = 'start'
        protoLabel.fontName = 'Helvetica'
        protoLabel.fontSize = 10
        drawings = self._makeDrawings(protoLabel)
        for d in drawings:
            story.append(d)
            story.append(Spacer(0, 1*cm))

        story.append(PageBreak())

        # Round 2b
        story.append(Paragraph("Helvetica 10pt, textAnchor='middle'", h3))
        story.append(Spacer(0, 0.5*cm))

        w, h = drawWidth, drawHeight = 400, 100
        protoLabel = self._makeProtoLabel()
        protoLabel.setOrigin(drawWidth/2, drawHeight/2)
        protoLabel.width = 4*cm
        protoLabel.height = 1.5*cm
        protoLabel.textAnchor = 'middle'
        protoLabel.fontName = 'Helvetica'
        protoLabel.fontSize = 10
        drawings = self._makeDrawings(protoLabel)
        for d in drawings:
            story.append(d)
            story.append(Spacer(0, 1*cm))

        story.append(PageBreak())

        # Round 2c
        story.append(Paragraph("Helvetica 10pt, textAnchor='end'", h3))
        story.append(Spacer(0, 0.5*cm))

        w, h = drawWidth, drawHeight = 400, 100
        protoLabel = self._makeProtoLabel()
        protoLabel.setOrigin(drawWidth/2, drawHeight/2)
        protoLabel.width = 4*cm
        protoLabel.height = 1.5*cm
        protoLabel.textAnchor = 'end'
        protoLabel.fontName = 'Helvetica'
        protoLabel.fontSize = 10
        drawings = self._makeDrawings(protoLabel)
        for d in drawings:
            story.append(d)
            story.append(Spacer(0, 1*cm))

        story.append(PageBreak())

        # Round 2d
        story.append(Paragraph("Helvetica 10pt, multi-line, textAnchor='start'", h3))
        story.append(Spacer(0, 0.5*cm))

        w, h = drawWidth, drawHeight = 400, 100
        protoLabel = self._makeProtoLabel()
        protoLabel.setOrigin(drawWidth/2, drawHeight/2)
        protoLabel.width = 4*cm
        protoLabel.height = 1.5*cm
        protoLabel.textAnchor = 'start'
        protoLabel.fontName = 'Helvetica'
        protoLabel.fontSize = 10
        drawings = self._makeDrawings(protoLabel, text='Hello\nWorld!')
        for d in drawings:
            story.append(d)
            story.append(Spacer(0, 1*cm))

        story.append(PageBreak())

        path = outputfile('test_charts_textlabels.pdf')
        doc = MyDocTemplate(path)
        doc.multiBuild(story)


def makeSuite():
    return makeSuiteForClasses(LabelTestCase)


#noruntests
if __name__ == "__main__":
    unittest.TextTestRunner().run(makeSuite())
    printLocation()
