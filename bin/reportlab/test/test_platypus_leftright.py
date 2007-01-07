#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/test/test_platypus_breaking.py
"""Tests ability to cycle through multiple page templates
"""

import sys, os, time
from string import split, strip, join, whitespace
from operator import truth
from types import StringType, ListType

from reportlab.test import unittest
from reportlab.test.utils import makeSuiteForClasses, outputfile, printLocation

from reportlab.platypus.flowables import Flowable
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus.paragraph import Paragraph
from reportlab.platypus.frames import Frame
from reportlab.lib.randomtext import randomText, PYTHON
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate, NextPageTemplate
from reportlab.platypus.paragraph import *


def myMainPageFrame(canvas, doc):
    "The page frame used for all PDF documents."

    canvas.saveState()
    canvas.setFont('Times-Roman', 12)
    pageNumber = canvas.getPageNumber()
    canvas.drawString(10*cm, cm, str(pageNumber))
    canvas.restoreState()



class LeftPageTemplate(PageTemplate):
    def __init__(self):
        #allow a bigger margin on the right for the staples
        frame = Frame(1.5*cm, 2.5*cm, 16*cm, 25*cm, id='F1')

        PageTemplate.__init__(self,
                              id='left',
                              frames=[frame],
                              pagesize=A4)
    def beforeDrawPage(self, canv, doc):
        "Decorate the page with an asymetric design"
        canv.setFillColor(colors.cyan)
                          
        canv.rect(0.5*cm, 2.5*cm, 1*cm, 25*cm, stroke=1, fill=1)
        canv.circle(19*cm, 10*cm, 0.5*cm, stroke=1, fill=1)
        canv.circle(19*cm, 20*cm, 0.5*cm, stroke=1, fill=1)
        canv.setFillColor(colors.black)
        

class RightPageTemplate(PageTemplate):
    def __init__(self):
        #allow a bigger margin on the right for the staples
        frame = Frame(3.5*cm, 2.5*cm, 16*cm, 25*cm, id='F1')

        PageTemplate.__init__(self,
                              id='right',
                              frames=[frame],
                              pagesize=A4)
    def beforeDrawPage(self, canv, doc):
        "Decorate the page with an asymetric design"
        canv.setFillColor(colors.cyan)
        canv.rect(19.5*cm, 2.5*cm, 1*cm, 25*cm, stroke=1, fill=1)
        canv.circle(2*cm, 10*cm, 0.5*cm, stroke=1, fill=1)
        canv.circle(2*cm, 20*cm, 0.5*cm, stroke=1, fill=1)
        canv.setFillColor(colors.black)


class MyDocTemplate(BaseDocTemplate):
    _invalidInitArgs = ('pageTemplates',)

    def __init__(self, filename, **kw):
        apply(BaseDocTemplate.__init__, (self, filename), kw)
        self.addPageTemplates(
            [
             PageTemplate(id='plain',
                          frames=[Frame(2.5*cm, 2.5*cm, 16*cm, 25*cm, id='F1')]
                          ),
             LeftPageTemplate(),
             RightPageTemplate()
            ]
            )


class LeftRightTestCase(unittest.TestCase):
    "Test multi-page splitting of paragraphs (eyeball-test)."
    def testIt(self):
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
            This tests ability to alternate left and right templates.  We start on
            a plain one. The next page should display a left-side template,
            with a big inner margin and staple-like holes on the right.""",style=bt))

        story.append(NextPageTemplate(['left','right']))


        story.append(Paragraph("""
            One can specify a list of templates instead of a single one in
            order to sequence through them.""",style=bt))
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

        story.append(NextPageTemplate('plain'))
        story.append(Paragraph('Back to plain old page template',h1))
        story.append(Paragraph('Back to plain old formatting', bt))


        #doc = MyDocTemplate(outputfile('test_platypus_leftright.pdf'))
        doc = MyDocTemplate(outputfile('test_platypus_leftright.pdf'))
        doc.multiBuild(story)


def makeSuite():
    return makeSuiteForClasses(LeftRightTestCase)


#noruntests
if __name__ == "__main__": #NORUNTESTS
    unittest.TextTestRunner().run(makeSuite())
    printLocation()
