#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/test/test_platypus_indents.py
"""Tests for context-dependent indentation
"""

import sys, os, random
from string import split, strip, join, whitespace
from operator import truth
from types import StringType, ListType

from reportlab.test import unittest
from reportlab.test.utils import makeSuiteForClasses, outputfile, printLocation

from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus.paraparser import ParaParser
from reportlab.platypus.flowables import Flowable
from reportlab.lib.colors import Color
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.utils import _className
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus.paragraph import Paragraph
from reportlab.platypus.frames import Frame
from reportlab.platypus.doctemplate \
     import PageTemplate, BaseDocTemplate, Indenter, FrameBreak, NextPageTemplate
from reportlab.platypus import tableofcontents
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.platypus.tables import TableStyle, Table
from reportlab.platypus.paragraph import *
from reportlab.platypus.paragraph import _getFragWords
from reportlab.platypus.flowables import Spacer


def myMainPageFrame(canvas, doc):
    "The page frame used for all PDF documents."

    canvas.saveState()

    canvas.rect(2.5*cm, 2.5*cm, 15*cm, 25*cm)
    canvas.setFont('Times-Roman', 12)
    pageNumber = canvas.getPageNumber()
    canvas.drawString(10*cm, cm, str(pageNumber))

    canvas.restoreState()


class MyDocTemplate(BaseDocTemplate):
    _invalidInitArgs = ('pageTemplates',)

    def __init__(self, filename, **kw):
        frame1 = Frame(2.5*cm, 2.5*cm, 15*cm, 25*cm, id='F1')
        self.allowSplitting = 0
        apply(BaseDocTemplate.__init__, (self, filename), kw)
        template1 = PageTemplate('normal', [frame1], myMainPageFrame)

        frame2 = Frame(2.5*cm, 16*cm, 15*cm, 10*cm, id='F2', showBoundary=1)
        frame3 = Frame(2.5*cm, 2.5*cm, 15*cm, 10*cm, id='F3', showBoundary=1)

        template2 = PageTemplate('updown', [frame2, frame3])
        self.addPageTemplates([template1, template2])


class IndentTestCase(unittest.TestCase):
    "Test multi-page splitting of paragraphs (eyeball-test)."

    def test0(self):
        "This makes one long multi-page paragraph."

        # Build story.
        story = []

        styleSheet = getSampleStyleSheet()
        h1 = styleSheet['Heading1']
        h1.spaceBefore = 18
        bt = styleSheet['BodyText']
        bt.spaceBefore = 6

        story.append(Paragraph('Test of context-relative indentation',h1))

        story.append(Spacer(18,18))

        story.append(Indenter(0,0))
        story.append(Paragraph("This should be indented 0 points at each edge. " + ("spam " * 25),bt))
        story.append(Indenter(0,0))

        story.append(Indenter(36,0))
        story.append(Paragraph("This should be indented 36 points at the left. " + ("spam " * 25),bt))
        story.append(Indenter(-36,0))

        story.append(Indenter(0,36))
        story.append(Paragraph("This should be indented 36 points at the right. " + ("spam " * 25),bt))
        story.append(Indenter(0,-36))

        story.append(Indenter(36,36))
        story.append(Paragraph("This should be indented 36 points at each edge. " + ("spam " * 25),bt))
        story.append(Indenter(36,36))
        story.append(Paragraph("This should be indented a FURTHER 36 points at each edge. " + ("spam " * 25),bt))
        story.append(Indenter(-72,-72))

        story.append(Paragraph("This should be back to normal at each edge. " + ("spam " * 25),bt))


        story.append(Indenter(36,36))
        story.append(Paragraph(("""This should be indented 36 points at the left
        and right.  It should run over more than one page and the indent should
        continue on the next page. """ + (random.randint(0,10) * 'x') + ' ') * 20 ,bt))
        story.append(Indenter(-36,-36))

        story.append(NextPageTemplate('updown'))
        story.append(FrameBreak())
        story.append(Paragraph('Another test of context-relative indentation',h1))
        story.append(NextPageTemplate('normal'))  # so NEXT page is different template...
        story.append(Paragraph("""This time we see if the indent level is continued across
            frames...this page has 2 frames, let's see if it carries top to bottom. Then
            onto a totally different template.""",bt))

        story.append(Indenter(0,0))
        story.append(Paragraph("This should be indented 0 points at each edge. " + ("spam " * 25),bt))
        story.append(Indenter(0,0))
        story.append(Indenter(36,72))
        story.append(Paragraph(("""This should be indented 36 points at the left
        and 72 at the right.  It should run over more than one frame and one page, and the indent should
        continue on the next page. """ + (random.randint(0,10) * 'x') + ' ') * 35 ,bt))

        story.append(Indenter(-36,-72))
        story.append(Paragraph("This should be back to normal at each edge. " + ("spam " * 25),bt))
        doc = MyDocTemplate(outputfile('test_platypus_indents.pdf'))
        doc.multiBuild(story)


#noruntests
def makeSuite():
    return makeSuiteForClasses(IndentTestCase)


#noruntests
if __name__ == "__main__":
    unittest.TextTestRunner().run(makeSuite())
    printLocation()
