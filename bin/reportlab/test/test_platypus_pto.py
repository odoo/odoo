#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/test/test_platypus_breaking.py
"""Tests pageBreakBefore, frameBreakBefore, keepWithNext...
"""

import sys

from reportlab.test import unittest
from reportlab.test.utils import makeSuiteForClasses, outputfile, printLocation
from reportlab.platypus.flowables import Flowable, PTOContainer, KeepInFrame
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import toColor, black
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus.paragraph import Paragraph
from reportlab.platypus.tables import Table
from reportlab.platypus.frames import Frame
from reportlab.lib.randomtext import randomText
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate, FrameBreak

def myMainPageFrame(canvas, doc):
    "The page frame used for all PDF documents."

    canvas.saveState()
    canvas.setFont('Times-Roman', 12)
    pageNumber = canvas.getPageNumber()
    canvas.drawString(10*cm, cm, str(pageNumber))
    canvas.restoreState()

def _showDoc(fn,story):
    pageTemplate = PageTemplate('normal', [Frame(72, 440, 170, 284, id='F1'),
                            Frame(326, 440, 170, 284, id='F2'),
                            Frame(72, 72, 170, 284, id='F3'),
                            Frame(326, 72, 170, 284, id='F4'),
                            ], myMainPageFrame)
    doc = BaseDocTemplate(outputfile(fn),
            pageTemplates = pageTemplate,
            showBoundary = 1,
            )
    doc.multiBuild(story)

text2 ='''We have already seen that the natural general principle that will
subsume this case cannot be arbitrary in the requirement that branching
is not tolerated within the dominance scope of a complex symbol.
Notice, incidentally, that the speaker-hearer's linguistic intuition is
to be regarded as the strong generative capacity of the theory.  A
consequence of the approach just outlined is that the descriptive power
of the base component does not affect the structure of the levels of
acceptability from fairly high (e.g. (99a)) to virtual gibberish (e.g.
(98d)).  By combining adjunctions and certain deformations, a
descriptively adequate grammar cannot be arbitrary in the strong
generative capacity of the theory.'''

text1='''
On our assumptions, a descriptively adequate grammar delimits the strong
generative capacity of the theory.  For one thing, the fundamental error
of regarding functional notions as categorial is to be regarded as a
corpus of utterance tokens upon which conformity has been defined by the
paired utterance test.  A majority  of informed linguistic specialists
agree that the appearance of parasitic gaps in domains relatively
inaccessible to ordinary extraction is necessary to impose an
interpretation on the requirement that branching is not tolerated within
the dominance scope of a complex symbol.  It may be, then, that the
speaker-hearer's linguistic intuition appears to correlate rather
closely with the ultimate standard that determines the accuracy of any
proposed grammar.  Analogously, the notion of level of grammaticalness
may remedy and, at the same time, eliminate a general convention
regarding the forms of the grammar.'''
    
text0 = '''To characterize a linguistic level L,
this selectionally introduced contextual
feature delimits the requirement that
branching is not tolerated within the
dominance scope of a complex
symbol. Notice, incidentally, that the
notion of level of grammaticalness
does not affect the structure of the
levels of acceptability from fairly high
(e.g. (99a)) to virtual gibberish (e.g.
(98d)). Suppose, for instance, that a
subset of English sentences interesting
on quite independent grounds appears
to correlate rather closely with an
important distinction in language use.
Presumably, this analysis of a
formative as a pair of sets of features is
not quite equivalent to the system of
base rules exclusive of the lexicon. We
have already seen that the appearance
of parasitic gaps in domains relatively
inaccessible to ordinary extraction
does not readily tolerate the strong
generative capacity of the theory.'''

def _ptoTestCase(self):
    "This makes one long multi-page paragraph."

    # Build story.
    story = []
    def fbreak(story=story):
        story.append(FrameBreak())

    styleSheet = getSampleStyleSheet()
    H1 = styleSheet['Heading1']
    H1.pageBreakBefore = 0
    H1.keepWithNext = 0

    bt = styleSheet['BodyText']
    pto = ParagraphStyle('pto',parent=bt)
    pto.alignment = TA_RIGHT
    pto.fontSize -= 1
    def ColorParagraph(c,text,style):
        return Paragraph('<para color=%s>%s</para>' % (c,text),style)

    def ptoblob(blurb,content,trailer=None,header=None, story=story, H1=H1):
        if type(content) not in (type([]),type(())): content = [content]
        story.append(PTOContainer([Paragraph(blurb,H1)]+list(content),trailer,header))

    t0 = [ColorParagraph('blue','Please turn over', pto )]
    h0 = [ColorParagraph('blue','continued from previous page', pto )]
    t1 = [ColorParagraph('red','Please turn over(inner)', pto )]
    h1 = [ColorParagraph('red','continued from previous page(inner)', pto )]
    ptoblob('First Try at a PTO',[Paragraph(text0,bt)],t0,h0)
    fbreak()
    c1 = Table([('alignment', 'align\012alignment'),
                ('bulletColor', 'bulletcolor\012bcolor'),
                ('bulletFontName', 'bfont\012bulletfontname'),
                ('bulletFontSize', 'bfontsize\012bulletfontsize'),
                ('bulletIndent', 'bindent\012bulletindent'),
                ('firstLineIndent', 'findent\012firstlineindent'),
                ('fontName', 'face\012fontname\012font'),
                ('fontSize', 'size\012fontsize'),
                ('leading', 'leading'),
                ('leftIndent', 'leftindent\012lindent'),
                ('rightIndent', 'rightindent\012rindent'),
                ('spaceAfter', 'spaceafter\012spacea'),
                ('spaceBefore', 'spacebefore\012spaceb'),
                ('textColor', 'fg\012textcolor\012color')],
            style = [
                ('VALIGN',(0,0),(-1,-1),'TOP'),
                ('INNERGRID', (0,0), (-1,-1), 0.25, black),
                ('BOX', (0,0), (-1,-1), 0.25, black),
                ],
            )
    ptoblob('PTO with a table inside',c1,t0,h0)
    fbreak()
    ptoblob('A long PTO',[Paragraph(text0+' '+text1,bt)],t0,h0)
    fbreak()
    ptoblob('2 PTO (inner split)',[ColorParagraph('pink',text0,bt),PTOContainer([ColorParagraph(black,'Inner Starts',H1),ColorParagraph('yellow',text2,bt),ColorParagraph('black','Inner Ends',H1)],t1,h1),ColorParagraph('magenta',text1,bt)],t0,h0)
    _showDoc('test_platypus_pto.pdf',story)

def _KeepInFrameTestCase(self,mode,offset=12):
    story = []
    def fbreak(story=story):
        story.append(FrameBreak())
    styleSheet = getSampleStyleSheet()
    H1 = styleSheet['Heading1']
    H1.pageBreakBefore = 0
    H1.keepWithNext = 0
    bt = styleSheet['BodyText']
    story.append(KeepInFrame(170-offset,284-offset,[Paragraph(text0,bt)],mode=mode))
    fbreak()
    story.append(KeepInFrame(170-offset,284-offset,[Paragraph(text0,bt),Paragraph(text1,bt)],mode=mode))
    fbreak()
    story.append(KeepInFrame(170-offset,284-offset,[Paragraph(text0,bt),Paragraph(text1,bt),Paragraph(text2,bt)],mode=mode))
    _showDoc('test_platypus_KeepInFrame%s.pdf'%mode,story)

class TestCases(unittest.TestCase):
    "Test multi-page splitting of paragraphs (eyeball-test)."
    def test0(self):
        _ptoTestCase(self)
    def test1(self):
        _KeepInFrameTestCase(self,mode="shrink")
    def test2(self):
        _KeepInFrameTestCase(self,mode="overflow")
    def test3(self):
        _KeepInFrameTestCase(self,mode="truncate")
    def test4(self):
        from reportlab.platypus.doctemplate import LayoutError
        self.assertRaises(LayoutError, _KeepInFrameTestCase,*(self,"error"))
    def test5(self):
        from reportlab.platypus.doctemplate import LayoutError
        self.assertRaises(LayoutError, _KeepInFrameTestCase,*(self,"shrink",0))

def makeSuite():
    return makeSuiteForClasses(TestCases)

#noruntests
if __name__ == "__main__": #NORUNTESTS
    if 'debug' in sys.argv:
        _KeepInFrameTestCase(None)
    else:
        unittest.TextTestRunner().run(makeSuite())
        printLocation()
