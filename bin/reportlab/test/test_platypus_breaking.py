#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/test/test_platypus_breaking.py
"""Tests pageBreakBefore, frameBreakBefore, keepWithNext...
"""

import sys, os, time
from string import split, strip, join, whitespace
from operator import truth
from types import StringType, ListType

from reportlab.test import unittest
from reportlab.test.utils import makeSuiteForClasses, outputfile, printLocation

from reportlab.platypus.flowables import Flowable
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus.paragraph import Paragraph
from reportlab.platypus.frames import Frame
from reportlab.lib.randomtext import randomText, PYTHON
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
from reportlab.platypus.paragraph import *


def myMainPageFrame(canvas, doc):
    "The page frame used for all PDF documents."

    canvas.saveState()
    canvas.setFont('Times-Roman', 12)
    pageNumber = canvas.getPageNumber()
    canvas.drawString(10*cm, cm, str(pageNumber))
    canvas.restoreState()


class MyDocTemplate(BaseDocTemplate):
    _invalidInitArgs = ('pageTemplates',)

    def __init__(self, filename, **kw):
        frame1 = Frame(2.5*cm, 15.5*cm, 6*cm, 10*cm, id='F1')
        frame2 = Frame(11.5*cm, 15.5*cm, 6*cm, 10*cm, id='F2')
        frame3 = Frame(2.5*cm, 2.5*cm, 6*cm, 10*cm, id='F3')
        frame4 = Frame(11.5*cm, 2.5*cm, 6*cm, 10*cm, id='F4')
        self.allowSplitting = 0
        self.showBoundary = 1
        apply(BaseDocTemplate.__init__, (self, filename), kw)
        template = PageTemplate('normal', [frame1, frame2, frame3, frame4], myMainPageFrame)
        self.addPageTemplates(template)


def _test0(self):
    "This makes one long multi-page paragraph."

    # Build story.
    story = []

    styleSheet = getSampleStyleSheet()
    h1 = styleSheet['Heading1']
    h1.pageBreakBefore = 1
    h1.keepWithNext = 1

    h2 = styleSheet['Heading2']
    h2.frameBreakBefore = 1
    h2.keepWithNext = 1

    h3 = styleSheet['Heading3']
    h3.backColor = colors.cyan
    h3.keepWithNext = 1

    bt = styleSheet['BodyText']

    story.append(Paragraph("""
        Subsequent pages test pageBreakBefore, frameBreakBefore and
        keepTogether attributes.  Generated at %s.  The number in brackets
        at the end of each paragraph is its position in the story. (%d)""" % (
            time.ctime(time.time()), len(story)), bt))

    for i in range(10):
        story.append(Paragraph('Heading 1 always starts a new page (%d)' % len(story), h1))
        for j in range(3):
            story.append(Paragraph('Heading1 paragraphs should always'
                            'have a page break before.  Heading 2 on the other hand'
                            'should always have a FRAME break before (%d)' % len(story), bt))
            story.append(Paragraph('Heading 2 always starts a new frame (%d)' % len(story), h2))
            story.append(Paragraph('Heading1 paragraphs should always'
                            'have a page break before.  Heading 2 on the other hand'
                            'should always have a FRAME break before (%d)' % len(story), bt))
            for j in range(3):
                story.append(Paragraph(randomText(theme=PYTHON, sentences=2)+' (%d)' % len(story), bt))
                story.append(Paragraph('I should never be at the bottom of a frame (%d)' % len(story), h3))
                story.append(Paragraph(randomText(theme=PYTHON, sentences=1)+' (%d)' % len(story), bt))

    doc = MyDocTemplate(outputfile('test_platypus_breaking.pdf'))
    doc.multiBuild(story)


class BreakingTestCase(unittest.TestCase):
    "Test multi-page splitting of paragraphs (eyeball-test)."
    def test0(self):
        _test0(self)


def makeSuite():
    return makeSuiteForClasses(BreakingTestCase)


#noruntests
if __name__ == "__main__": #NORUNTESTS
    if 'debug' in sys.argv:
        _test0(None)
    else:
        unittest.TextTestRunner().run(makeSuite())
        printLocation()
