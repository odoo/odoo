#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/test/test_platypus_xref.py
"""Test long documents with indexes, tables and cross-references
"""

import sys, os, time
from string import split, strip, join, whitespace, find
from operator import truth
from types import StringType, ListType

from reportlab.test import unittest
from reportlab.test.utils import makeSuiteForClasses, outputfile, printLocation

from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Flowable, Frame, PageTemplate, BaseDocTemplate
from reportlab.platypus.frames import Frame
from reportlab.lib.randomtext import randomText, PYTHON
from reportlab.platypus.tableofcontents import TableOfContents, SimpleIndex


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
        frame1 = Frame(2.5*cm, 2.5*cm, 16*cm, 25*cm, id='Frame1')
        self.allowSplitting = 0
        self.showBoundary = 1
        apply(BaseDocTemplate.__init__, (self, filename), kw)
        template = PageTemplate('normal', [frame1], myMainPageFrame)
        self.addPageTemplates(template)

    def afterFlowable(self, flowable):
        "Registers TOC and Index entries and makes outline entries."
        if flowable.__class__.__name__ == 'Paragraph':
            styleName = flowable.style.name
            if styleName == 'Heading1':
                level = 0
                text = flowable.getPlainText()
                pageNum = self.page
                self.notify('TOCEntry', (level, text, pageNum))

                # Add PDF outline entries (not really needed/tested here).
                key = str(hash(flowable))
                c = self.canv
                c.bookmarkPage(key)
                c.addOutlineEntry(text, key, level=level, closed=0)

            # index a bunch of pythonic buzzwords.  In real life this
            # would be driven by markup.
            try:
                text = flowable.getPlainText()
            except:
                return
            for phrase in ['uniform','depraved','finger', 'Fraudulin']:
                if find(text, phrase) > -1:
                    self.notify('IndexEntry', (phrase, self.page))
                    #print 'IndexEntry:',phrase, self.page


def _test0(self):
    "This makes one long multi-page paragraph."

    # Build story.
    story = []

    styleSheet = getSampleStyleSheet()
    h1 = styleSheet['Heading1']
    h1.pageBreakBefore = 1
    h1.keepWithNext = 1
    h1.outlineLevel = 0

    h2 = styleSheet['Heading2']
    h2.backColor = colors.cyan
    h2.keepWithNext = 1
    h2.outlineLevel = 1

    bt = styleSheet['BodyText']

    story.append(Paragraph("""Cross-Referencing Test""", styleSheet["Title"]))
    story.append(Paragraph("""
        Subsequent pages test cross-references: indexes, tables and individual
        cross references.  The number in brackets at the end of each paragraph
        is its position in the story. (%d)""" % len(story), bt))

    story.append(Paragraph("""Table of Contents:""", styleSheet["Title"]))
    toc = TableOfContents()
    story.append(toc)

    chapterNum = 1
    for i in range(10):
        story.append(Paragraph('Chapter %d: Chapters always starts a new page' % chapterNum, h1))
        chapterNum = chapterNum + 1
        for j in range(3):
            story.append(Paragraph('Heading1 paragraphs should always'
                            'have a page break before.  Heading 2 on the other hand'
                            'should always have a FRAME break before (%d)' % len(story), bt))
            story.append(Paragraph('Heading 2 should always be kept with the next thing (%d)' % len(story), h2))
            for j in range(3):
                story.append(Paragraph(randomText(theme=PYTHON, sentences=2)+' (%d)' % len(story), bt))
                story.append(Paragraph('I should never be at the bottom of a frame (%d)' % len(story), h2))
                story.append(Paragraph(randomText(theme=PYTHON, sentences=1)+' (%d)' % len(story), bt))

    story.append(Paragraph('The Index which goes at the back', h1))
    story.append(SimpleIndex())

    doc = MyDocTemplate(outputfile('test_platypus_xref.pdf'))
    doc.multiBuild(story)


class BreakingTestCase(unittest.TestCase):
    "Test multi-page splitting of paragraphs (eyeball-test)."
    def test0(self):
        _test0(self)


def makeSuite():
    return makeSuiteForClasses(BreakingTestCase)


#noruntests
if __name__ == "__main__":
    if 'debug' in sys.argv:
        _test1(None)
    else:
        unittest.TextTestRunner().run(makeSuite())
        printLocation()
