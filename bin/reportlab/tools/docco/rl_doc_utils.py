#!/bin/env python
#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/tools/docco/rl_doc_utils.py
__version__=''' $Id: rl_doc_utils.py 2830 2006-04-05 15:18:32Z rgbecker $ '''


__doc__ = """
This module contains utilities for generating guides
"""

import os, sys, glob
import string

from rltemplate import RLDocTemplate
from stylesheet import getStyleSheet
styleSheet = getStyleSheet()

#from reportlab.platypus.doctemplate import SimpleDocTemplate
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter, A4, A5, A3  # latter two for testing
from reportlab.rl_config import defaultPageSize
from reportlab.platypus import figures
from reportlab.platypus import Paragraph, Spacer, Preformatted,\
            PageBreak, CondPageBreak, Flowable, Table, TableStyle, \
            NextPageTemplate, KeepTogether, Image, XPreformatted
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.sequencer import getSequencer

import examples

appmode=0


from t_parse import Template
QFcodetemplate = Template("X$X$", "X")
QFreptemplate = Template("X^X^", "X")
codesubst = "%s<font name=Courier>%s</font>"
QFsubst = "%s<font name=Courier><i>%s</i></font>"


def quickfix(text):
    """inside text find any subsequence of form $subsequence$.
       Format the subsequence as code.  If similarly if text contains ^arg^
       format the arg as replaceable.  The escape sequence for literal
       $ is $\\$ (^ is ^\\^.
    """
    from string import join
    for (template,subst) in [(QFcodetemplate, codesubst), (QFreptemplate, QFsubst)]:
        fragment = text
        parts = []
        try:
            while fragment:
                try:
                    (matches, index) = template.PARSE(fragment)
                except: raise ValueError
                else:
                    [prefix, code] = matches
                    if code == "\\":
                        part = fragment[:index]
                    else:
                        part = subst % (prefix, code)
                    parts.append(part)
                    fragment = fragment[index:]
        except ValueError:
            parts.append(fragment)
        text = join(parts, "")
    return text
#print quickfix("$testing$ testing $one$ ^two^ $three(^four^)$")



H1 = styleSheet['Heading1']
H2 = styleSheet['Heading2']
H3 = styleSheet['Heading3']
H4 = styleSheet['Heading4']
B = styleSheet['BodyText']
BU = styleSheet['Bullet']
Comment = styleSheet['Comment']
Centred = styleSheet['Centred']
Caption = styleSheet['Caption']

#set up numbering
seq = getSequencer()
seq.setFormat('Chapter','1')
seq.setFormat('Section','1')
seq.setFormat('Appendix','A')
seq.setFormat('Figure', '1')
seq.chain('Chapter','Section')
seq.chain('Chapter','Figure')

lessonnamestyle = H2
discussiontextstyle = B
exampletextstyle = styleSheet['Code']
# size for every example
examplefunctionxinches = 5.5
examplefunctionyinches = 3
examplefunctiondisplaysizes = (examplefunctionxinches*inch, examplefunctionyinches*inch)

def getJustFontPaths():
    '''return afm and pfb for Just's files'''
    import reportlab
    folder = os.path.dirname(reportlab.__file__) + os.sep + 'fonts'
    return os.path.join(folder, 'LeERC___.AFM'), os.path.join(folder, 'LeERC___.PFB')

# for testing
def NOP(*x,**y):
    return None

def CPage(inches):
    getStory().append(CondPageBreak(inches*inch))

def newPage():
    getStory().append(PageBreak())

def nextTemplate(templName):
    f = NextPageTemplate(templName)
    getStory().append(f)

def disc(text, klass=Paragraph, style=discussiontextstyle):
    text = quickfix(text)
    P = klass(text, style)
    getStory().append(P)

def restartList():
    getSequencer().reset('list1')

def list(text, doBullet=1):
    text=quickfix(text)
    if doBullet:
        text='<bullet><seq id="list1"/>.</bullet>'+text
    P = Paragraph(text, BU)
    getStory().append(P)

def bullet(text):
    text='<bullet><font name="Symbol">\xe2\x80\xa2</font></bullet>' + quickfix(text)
    P = Paragraph(text, BU)
    getStory().append(P)

def eg(text,before=0.1,after=0):
    space(before)
    disc(text, klass=Preformatted, style=exampletextstyle)
    space(after)

def space(inches=1./6):
    if inches: getStory().append(Spacer(0,inches*inch))

def EmbeddedCode(code,name='t'):
    eg(code)
    disc("produces")
    exec code+("\ngetStory().append(%s)\n"%name)

def startKeep():
    return len(getStory())

def endKeep(s):
    S = getStory()
    k = KeepTogether(S[s:])
    S[s:] = [k]

def title(text):
    """Use this for the document title only"""
    disc(text,style=styleSheet['Title'])

#AR 3/7/2000 - defining three new levels of headings; code
#should be swapped over to using them.

def heading1(text):
    """Use this for chapters.  Lessons within a big chapter
    should now use heading2 instead.  Chapters get numbered."""
    getStory().append(PageBreak())
    p = Paragraph('Chapter <seq id="Chapter"/> ' + quickfix(text), H1)
    getStory().append(p)

def Appendix1(text,):
    global appmode
    getStory().append(PageBreak())
    if not appmode:
        seq.setFormat('Chapter','A')
        seq.reset('Chapter')
        appmode = 1
    p = Paragraph('Appendix <seq id="Chapter"/> ' + quickfix(text), H1)
    getStory().append(p)

def heading2(text):
    """Used to be 'lesson'"""
    getStory().append(CondPageBreak(inch))
    p = Paragraph('<seq template="%(Chapter)s.%(Section+)s "/>' + quickfix(text), H2)
    getStory().append(p)

def heading3(text):
    """Used to be most of the plain old 'head' sections"""
    getStory().append(CondPageBreak(inch))
    p = Paragraph(quickfix(text), H3)
    getStory().append(p)

def image(path, width=None, height=None ):
    s = startKeep()
    space(.2)
    import reportlab
    rlDocImageDir = os.path.join(os.path.dirname(reportlab.__file__), 'docs','images')
    getStory().append(Image(os.path.join(rlDocImageDir,path),width,height))
    space(.2)
    endKeep(s)

def heading4(text):
    """Used to be most of the plain old 'head' sections"""
    getStory().append(CondPageBreak(inch))
    p = Paragraph(quickfix(text), H4)
    getStory().append(p)

def todo(text):
    """Used for notes to ourselves"""
    getStory().append(Paragraph(quickfix(text), Comment))

def centred(text):
    getStory().append(Paragraph(quickfix(text), Centred))

def caption(text):
    getStory().append(Paragraph(quickfix(text), Caption))

class Illustration(figures.Figure):
    """The examples are all presented as functions which do
    something to a canvas, with a constant height and width
    used.  This puts them inside a figure box with a caption."""

    def __init__(self, operation, caption, width=None, height=None):
        stdwidth, stdheight = examplefunctiondisplaysizes
        if not width:
            width = stdwidth
        if not height:
            height = stdheight
        #figures.Figure.__init__(self, stdwidth * 0.75, stdheight * 0.75)
        figures.Figure.__init__(self, width, height,
                    'Figure <seq template="%(Chapter)s-%(Figure+)s"/>: ' + quickfix(caption))
        self.operation = operation

    def drawFigure(self):
        #shrink it a little...
        #self.canv.scale(0.75, 0.75)
        self.operation(self.canv)


def illust(operation, caption, width=None, height=None):
    i = Illustration(operation, caption, width=width, height=height)
    getStory().append(i)


class GraphicsDrawing(Illustration):
    """Lets you include reportlab/graphics drawings seamlessly,
    with the right numbering."""
    def __init__(self, drawing, caption):
        figures.Figure.__init__(self,
                                  drawing.width,
                                  drawing.height,
                    'Figure <seq template="%(Chapter)s-%(Figure+)s"/>: ' + quickfix(caption)
                                  )
        self.drawing = drawing

    def drawFigure(self):
        d = self.drawing
        d.wrap(d.width, d.height)
        d.drawOn(self.canv, 0, 0)

def draw(drawing, caption):
    d = GraphicsDrawing(drawing, caption)
    getStory().append(d)

class ParaBox(figures.Figure):
    """Illustrates paragraph examples, with style attributes on the left"""
    descrStyle = ParagraphStyle('description',
                                fontName='Courier',
                                fontSize=8,
                                leading=9.6)

    def __init__(self, text, style, caption):
        figures.Figure.__init__(self, 0, 0, caption)
        self.text = text
        self.style = style
        self.para = Paragraph(text, style)

        styleText = self.getStyleText(style)
        self.pre = Preformatted(styleText, self.descrStyle)

    def wrap(self, availWidth, availHeight):
        """Left 30% is for attributes, right 50% for sample,
        10% gutter each side."""
        self.x0 = availWidth * 0.05  #left of box
        self.x1 = availWidth * 0.1   #left of descriptive text
        self.x2 = availWidth * 0.5   #left of para itself
        self.x3 = availWidth * 0.9   #right of para itself
        self.x4 = availWidth * 0.95  #right of box
        self.width = self.x4 - self.x0
        self.dx = 0.5 * (availWidth - self.width)

        paw, self.pah = self.para.wrap(self.x3 - self.x2, availHeight)
        self.pah = self.pah + self.style.spaceBefore + self.style.spaceAfter
        prw, self.prh = self.pre.wrap(self.x2 - self.x1, availHeight)
        self.figureHeight = max(self.prh, self.pah) * 10.0/9.0
        return figures.Figure.wrap(self, availWidth, availHeight)

    def getStyleText(self, style):
        """Converts style to preformatted block of text"""
        lines = []
        for (key, value) in style.__dict__.items():
            lines.append('%s = %s' % (key, value))
        lines.sort()
        return string.join(lines, '\n')

    def drawFigure(self):

        #now we fill in the bounding box and before/after boxes
        self.canv.saveState()
        self.canv.setFillGray(0.95)
        self.canv.setDash(1,3)
        self.canv.rect(self.x2 - self.x0,
                       self.figureHeight * 0.95 - self.pah,
                       self.x3-self.x2, self.para.height,
                       fill=1,stroke=1)

        self.canv.setFillGray(0.90)
        self.canv.rect(self.x2 - self.x0, #spaceBefore
                       self.figureHeight * 0.95 - self.pah + self.para.height,
                       self.x3-self.x2, self.style.spaceBefore,
                       fill=1,stroke=1)

        self.canv.rect(self.x2 - self.x0, #spaceBefore
                       self.figureHeight * 0.95 - self.pah - self.style.spaceAfter,
                       self.x3-self.x2, self.style.spaceAfter,
                       fill=1,stroke=1)

        self.canv.restoreState()
        #self.canv.setFillColor(colors.yellow)
        self.para.drawOn(self.canv, self.x2 - self.x0,
                         self.figureHeight * 0.95 - self.pah)
        self.pre.drawOn(self.canv, self.x1 - self.x0,
                         self.figureHeight * 0.95 - self.prh)


    def getStyleText(self, style):
        """Converts style to preformatted block of text"""
        lines = []
        for (key, value) in style.__dict__.items():
            if key not in ('name','parent'):
                lines.append('%s = %s' % (key, value))
        return string.join(lines, '\n')


class ParaBox2(figures.Figure):
    """Illustrates a paragraph side-by-side with the raw
    text, to show how the XML works."""
    def __init__(self, text, caption):
        figures.Figure.__init__(self, 0, 0, caption)
        descrStyle = ParagraphStyle('description',
                                fontName='Courier',
                                fontSize=8,
                                leading=9.6)
        textStyle = B
        self.text = text
        self.left = Paragraph('<![CDATA[' + text + ']]>', descrStyle)
        self.right = Paragraph(text, B)


    def wrap(self, availWidth, availHeight):
        self.width = availWidth * 0.9
        colWidth = 0.4 * self.width
        lw, self.lh = self.left.wrap(colWidth, availHeight)
        rw, self.rh = self.right.wrap(colWidth, availHeight)
        self.figureHeight = max(self.lh, self.rh) * 10.0/9.0
        return figures.Figure.wrap(self, availWidth, availHeight)

    def drawFigure(self):
        self.left.drawOn(self.canv,
                         self.width * 0.05,
                         self.figureHeight * 0.95 - self.lh
                         )
        self.right.drawOn(self.canv,
                         self.width * 0.55,
                         self.figureHeight * 0.95 - self.rh
                         )

def parabox(text, style, caption):
    p = ParaBox(text, style,
                'Figure <seq template="%(Chapter)s-%(Figure+)s"/>: ' + quickfix(caption)
                )
    getStory().append(p)

def parabox2(text, caption):
    p = ParaBox2(text,
                'Figure <seq template="%(Chapter)s-%(Figure+)s"/>: ' + quickfix(caption)
                )
    getStory().append(p)

def pencilnote():
    getStory().append(examples.NoteAnnotation())


from reportlab.lib.colors import tan, green
def handnote(xoffset=0, size=None, fillcolor=tan, strokecolor=green):
    getStory().append(examples.HandAnnotation(xoffset,size,fillcolor,strokecolor))


#make a singleton, created when requested rather
#than each time a chapter imports it.
_story = []
def setStory(story=[]):
    global _story
    _story = story
def getStory():
    return _story
