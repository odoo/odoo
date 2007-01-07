#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/test/test_platypus_general.py
__version__=''' $Id: test_platypus_general.py 2619 2005-06-24 14:49:15Z rgbecker $ '''

#tests and documents Page Layout API
__doc__="""This is not obvious so here's a brief explanation.  This module is both
the test script and user guide for layout.  Each page has two frames on it:
one for commentary, and one for demonstration objects which may be drawn in
various esoteric ways.  The two functions getCommentary() and getExamples()
return the 'story' for each.  The run() function gets the stories, then
builds a special "document model" in which the frames are added to each page
and drawn into.
"""

import string, copy, sys, os

from reportlab.test import unittest
from reportlab.test.utils import makeSuiteForClasses, outputfile, printLocation

from reportlab.pdfgen import canvas
from reportlab import platypus
from reportlab.platypus import BaseDocTemplate, PageTemplate, Flowable, FrameBreak
from reportlab.platypus import Paragraph, Preformatted
from reportlab.lib.units import inch, cm
from reportlab.lib.styles import PropertySet, getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.rl_config import defaultPageSize
from reportlab.lib.utils import haveImages, _RL_DIR, rl_isfile, open_for_read
if haveImages:
    _GIF = os.path.join(_RL_DIR,'test','pythonpowered.gif')
    if not rl_isfile(_GIF): _GIF = None
else:
    _GIF = None
_JPG = os.path.join(_RL_DIR,'docs','images','lj8100.jpg')
if not rl_isfile(_JPG): _JPG = None

def getFurl(fn):
    furl = fn.replace(os.sep,'/')
    if sys.platform=='win32' and furl[1]==':': furl = furl[0]+'|'+furl[2:]
    if furl[0]!='/': furl = '/'+furl
    return 'file://'+furl

PAGE_HEIGHT = defaultPageSize[1]

#################################################################
#
#  first some drawing utilities
#
#
################################################################

BASEFONT = ('Times-Roman', 10)

def framePage(canvas,doc):
    #canvas.drawImage("snkanim.gif", 36, 36)
    canvas.saveState()
    canvas.setStrokeColorRGB(1,0,0)
    canvas.setLineWidth(5)
    canvas.line(66,72,66,PAGE_HEIGHT-72)

    canvas.setFont('Times-Italic',12)
    canvas.drawRightString(523, PAGE_HEIGHT - 56, "Platypus User Guide and Test Script")

    canvas.setFont('Times-Roman',12)
    canvas.drawString(4 * inch, 0.75 * inch,
                        "Page %d" % canvas.getPageNumber())
    canvas.restoreState()

def getParagraphs(textBlock):
    """Within the script, it is useful to whack out a page in triple
    quotes containing separate paragraphs. This breaks one into its
    constituent paragraphs, using blank lines as the delimiter."""
    lines = string.split(textBlock, '\n')
    paras = []
    currentPara = []
    for line in lines:
        if len(string.strip(line)) == 0:
            #blank, add it
            if currentPara <> []:
                paras.append(string.join(currentPara, '\n'))
                currentPara = []
        else:
            currentPara.append(line)
    #...and the last one
    if currentPara <> []:
        paras.append(string.join(currentPara, '\n'))

    return paras

def getCommentary():
    """Returns the story for the commentary - all the paragraphs."""

    styleSheet = getSampleStyleSheet()

    story = []
    story.append(Paragraph("""
        PLATYPUS User Guide and Test Script
        """, styleSheet['Heading1']))


    spam = """
    Welcome to PLATYPUS!

    Platypus stands for "Page Layout and Typography Using Scripts".  It is a high
    level page layout library which lets you programmatically create complex
    documents with a minimum of effort.

    This document is both the user guide &amp; the output of the test script.
    In other words, a script used platypus to create the document you are now
    reading, and the fact that you are reading it proves that it works.  Or
    rather, that it worked for this script anyway.  It is a first release!

    Platypus is built 'on top of' PDFgen, the Python library for creating PDF
    documents.  To learn about PDFgen, read the document testpdfgen.pdf.

    """

    for text in getParagraphs(spam):
        story.append(Paragraph(text, styleSheet['BodyText']))

    story.append(Paragraph("""
        What concepts does PLATYPUS deal with?
        """, styleSheet['Heading2']))
    story.append(Paragraph("""
        The central concepts in PLATYPUS are Flowable Objects, Frames, Flow
        Management, Styles and Style Sheets, Paragraphs and Tables.  This is
        best explained in contrast to PDFgen, the layer underneath PLATYPUS.
        PDFgen is a graphics library, and has primitive commans to draw lines
        and strings.  There is nothing in it to manage the flow of text down
        the page.  PLATYPUS works at the conceptual level fo a desktop publishing
        package; you can write programs which deal intelligently with graphic
        objects and fit them onto the page.
        """, styleSheet['BodyText']))

    story.append(Paragraph("""
        How is this document organized?
        """, styleSheet['Heading2']))

    story.append(Paragraph("""
        Since this is a test script, we'll just note how it is organized.
        the top of each page contains commentary.  The bottom half contains
        example drawings and graphic elements to whicht he commentary will
        relate.  Down below, you can see the outline of a text frame, and
        various bits and pieces within it.  We'll explain how they work
        on the next page.
        """, styleSheet['BodyText']))

    story.append(FrameBreak())
    #######################################################################
    #     Commentary Page 2
    #######################################################################

    story.append(Paragraph("""
        Flowable Objects
        """, styleSheet['Heading2']))
    spam = """
        The first and most fundamental concept is that of a 'Flowable Object'.
        In PDFgen, you draw stuff by calling methods of the canvas to set up
        the colors, fonts and line styles, and draw the graphics primitives.
        If you set the pen color to blue, everything you draw after will be
        blue until you change it again.  And you have to handle all of the X-Y
        coordinates yourself.

        A 'Flowable object' is exactly what it says.  It knows how to draw itself
        on the canvas, and the way it does so is totally independent of what
        you drew before or after.  Furthermore, it draws itself at the location
        on the page you specify.

        The most fundamental Flowable Objects in most documents are likely to be
        paragraphs, tables, diagrams/charts and images - but there is no
        restriction.  You can write your own easily, and I hope that people
        will start to contribute them.  PINGO users - we provide a "PINGO flowable" object to let
        you insert platform-independent graphics into the flow of a document.

        When you write a flowable object, you inherit from Flowable and
        must implement two methods.  object.wrap(availWidth, availHeight) will be called by other parts of
        the system, and tells you how much space you have.  You should return
        how much space you are going to use.  For a fixed-size object, this
        is trivial, but it is critical - PLATYPUS needs to figure out if things
        will fit on the page before drawing them.  For other objects such as paragraphs,
        the height is obviously determined by the available width.


        The second method is object.draw().  Here, you do whatever you want.
        The Flowable base class sets things up so that you have an origin of
        (0,0) for your drawing, and everything will fit nicely if you got the
        height and width right.  It also saves and restores the graphics state
        around your calls, so you don;t have to reset all the properties you
        changed.

        Programs which actually draw a Flowable don't
        call draw() this directly - they call object.drawOn(canvas, x, y).
        So you can write code in your own coordinate system, and things
        can be drawn anywhere on the page (possibly even scaled or rotated).
        """
    for text in getParagraphs(spam):
        story.append(Paragraph(text, styleSheet['BodyText']))

    story.append(FrameBreak())
    #######################################################################
    #     Commentary Page 3
    #######################################################################

    story.append(Paragraph("""
        Available Flowable Objects
        """, styleSheet['Heading2']))

    story.append(Paragraph("""
        Platypus comes with a basic set of flowable objects.  Here we list their
        class names and tell you what they do:
        """, styleSheet['BodyText']))
    #we can use the bullet feature to do a definition list
    story.append(Paragraph("""
        <para color=green bcolor=red bg=pink>This is a contrived object to give an example of a Flowable -
        just a fixed-size box with an X through it and a centred string.</para>""",
            styleSheet['Definition'],
            bulletText='XBox  '  #hack - spot the extra space after
            ))

    story.append(Paragraph("""
        This is the basic unit of a document.  Paragraphs can be finely
        tuned and offer a host of properties through their associated
        ParagraphStyle.""",
            styleSheet['Definition'],
            bulletText='Paragraph  '  #hack - spot the extra space after
            ))

    story.append(Paragraph("""
        This is used for printing code and other preformatted text.
        There is no wrapping, and line breaks are taken where they occur.
        Many paragraph style properties do not apply.  You may supply
        an optional 'dedent' parameter to trim a number of characters
        off the front of each line.""",
            styleSheet['Definition'],
            bulletText='Preformatted  '  #hack - spot the extra space after
            ))
    story.append(Paragraph("""
        This is a straight wrapper around an external image file.  By default
        the image will be drawn at a scale of one pixel equals one point, and
        centred in the frame.  You may supply an optional width and height.""",
            styleSheet['Definition'],
            bulletText='Image  '  #hack - spot the extra space after
            ))

    story.append(Paragraph("""
        This is a table drawing class; it is intended to be simpler
        than a full HTML table model yet be able to draw attractive output,
        and behave intelligently when the numbers of rows and columns vary.
        Still need to add the cell properties (shading, alignment, font etc.)""",
            styleSheet['Definition'],
            bulletText='Table  '  #hack - spot the extra space after
            ))

    story.append(Paragraph("""
        This is a 'null object' which merely takes up space on the page.
        Use it when you want some extra padding betweene elements.""",
            styleSheet['Definition'],
            bulletText='Spacer '  #hack - spot the extra space after
            ))

    story.append(Paragraph("""
        A FrameBreak causes the document to call its handle_frameEnd method.""",
            styleSheet['Definition'],
            bulletText='FrameBreak  '  #hack - spot the extra space after
            ))

    story.append(Paragraph("""
        This is in progress, but a macro is basically a chunk of Python code to
        be evaluated when it is drawn.  It could do lots of neat things.""",
            styleSheet['Definition'],
            bulletText='Macro  '  #hack - spot the extra space after
            ))

    story.append(FrameBreak())

    story.append(Paragraph(
                "The next example uses a custom font",
                styleSheet['Italic']))
    def code(txt,story=story,styleSheet=styleSheet):
        story.append(Preformatted(txt,styleSheet['Code']))
    code('''import reportlab.rl_config
    reportlab.rl_config.warnOnMissingFontGlyphs = 0

    from reportlab.pdfbase import pdfmetrics
    fontDir = os.path.join(os.path.dirname(reportlab.__file__),'fonts')
    face = pdfmetrics.EmbeddedType1Face(os.path.join(fontDir,'LeERC___.AFM'),
            os.path.join(fontDir,'LeERC___.PFB'))
    faceName = face.name  # should be 'LettErrorRobot-Chrome'
    pdfmetrics.registerTypeFace(face)
    font = pdfmetrics.Font(faceName, faceName, 'WinAnsiEncoding')
    pdfmetrics.registerFont(font)


    # put it inside a paragraph.
    story.append(Paragraph(
        """This is an ordinary paragraph, which happens to contain
        text in an embedded font:
        <font name="LettErrorRobot-Chrome">LettErrorRobot-Chrome</font>.
        Now for the real challenge...""", styleSheet['Normal']))


    styRobot = ParagraphStyle('Robot', styleSheet['Normal'])
    styRobot.fontSize = 16
    styRobot.leading = 20
    styRobot.fontName = 'LettErrorRobot-Chrome'

    story.append(Paragraph(
                "This whole paragraph is 16-point Letterror-Robot-Chrome.",
                styRobot))''')

    story.append(FrameBreak())
    if _GIF:
        story.append(Paragraph("""We can use images via the file name""", styleSheet['BodyText']))
        code('''    story.append(platypus.Image('%s'))'''%_GIF)
        code('''    story.append(platypus.Image('%s'.encode('utf8')))''' % _GIF)
        story.append(Paragraph("""They can also be used with a file URI or from an open python file!""", styleSheet['BodyText']))
        code('''    story.append(platypus.Image('%s'))'''% getFurl(_GIF))
        code('''    story.append(platypus.Image(open_for_read('%s','b')))''' % _GIF)
        story.append(FrameBreak())
        story.append(Paragraph("""Images can even be obtained from the internet.""", styleSheet['BodyText']))
        code('''    img = platypus.Image('http://www.reportlab.com/rsrc/encryption.gif')
    story.append(img)''')
        story.append(FrameBreak())

    if _JPG:
        story.append(Paragraph("""JPEGs are a native PDF image format. They should be available even if PIL cannot be used.""", styleSheet['BodyText']))
        story.append(FrameBreak())
    return story

def getExamples():
    """Returns all the example flowable objects"""
    styleSheet = getSampleStyleSheet()

    story = []

    #make a style with indents and spacing
    sty = ParagraphStyle('obvious', None)
    sty.leftIndent = 18
    sty.rightIndent = 18
    sty.firstLineIndent = 18
    sty.spaceBefore = 6
    sty.spaceAfter = 6
    story.append(Paragraph("""Now for some demo stuff - we need some on this page,
        even before we explain the concepts fully""", styleSheet['BodyText']))
    p = Paragraph("""
        Platypus is all about fitting objects into frames on the page.  You
        are looking at a fairly simple Platypus paragraph in Debug mode.
        It has some gridlines drawn around it to show the left and right indents,
        and the space before and after, all of which are attributes set in
        the style sheet.  To be specific, this paragraph has left and
        right indents of 18 points, a first line indent of 36 points,
        and 6 points of space before and after itself.  A paragraph
        object fills the width of the enclosing frame, as you would expect.""", sty)

    p.debug = 1   #show me the borders
    story.append(p)

    story.append(Paragraph("""Same but with justification 1.5 extra leading and green text.""", styleSheet['BodyText']))
    p = Paragraph("""
        <para align=justify leading=+1.5 fg=green><font color=red>Platypus</font> is all about fitting objects into frames on the page.  You
        are looking at a fairly simple Platypus paragraph in Debug mode.
        It has some gridlines drawn around it to show the left and right indents,
        and the space before and after, all of which are attributes set in
        the style sheet.  To be specific, this paragraph has left and
        right indents of 18 points, a first line indent of 36 points,
        and 6 points of space before and after itself.  A paragraph
        object fills the width of the enclosing frame, as you would expect.</para>""", sty)

    p.debug = 1   #show me the borders
    story.append(p)

    story.append(platypus.XBox(4*inch, 0.75*inch,
            'This is a box with a fixed size'))

    story.append(Paragraph("""
        All of this is being drawn within a text frame which was defined
        on the page.  This frame is in 'debug' mode so you can see the border,
        and also see the margins which it reserves.  A frame does not have
        to have margins, but they have been set to 6 points each to create
        a little space around the contents.
        """, styleSheet['BodyText']))

    story.append(FrameBreak())

    #######################################################################
    #     Examples Page 2
    #######################################################################

    story.append(Paragraph("""
        Here's the base class for Flowable...
        """, styleSheet['Italic']))

    code = '''class Flowable:
        """Abstract base class for things to be drawn.  Key concepts:
    1. It knows its size
    2. It draws in its own coordinate system (this requires the
        base API to provide a translate() function.
        """
    def __init__(self):
        self.width = 0
        self.height = 0
        self.wrapped = 0

    def drawOn(self, canvas, x, y):
        "Tell it to draw itself on the canvas.  Do not override"
        self.canv = canvas
        self.canv.saveState()
        self.canv.translate(x, y)

        self.draw()   #this is the bit you overload

        self.canv.restoreState()
        del self.canv

    def wrap(self, availWidth, availHeight):
        """This will be called by the enclosing frame before objects
        are asked their size, drawn or whatever.  It returns the
        size actually used."""
        return (self.width, self.height)
    '''

    story.append(Preformatted(code, styleSheet['Code'], dedent=4))
    story.append(FrameBreak())
    #######################################################################
    #     Examples Page 3
    #######################################################################

    story.append(Paragraph(
                "Here are some examples of the remaining objects above.",
                styleSheet['Italic']))

    story.append(Paragraph("This is a bullet point", styleSheet['Bullet'], bulletText='O'))
    story.append(Paragraph("Another bullet point", styleSheet['Bullet'], bulletText='O'))


    story.append(Paragraph("""Here is a Table, which takes all kinds of formatting options...""",
                styleSheet['Italic']))
    story.append(platypus.Spacer(0, 12))

    g = platypus.Table(
            (('','North','South','East','West'),
             ('Quarter 1',100,200,300,400),
             ('Quarter 2',100,200,300,400),
             ('Total',200,400,600,800)),
            (72,36,36,36,36),
            (24, 16,16,18)
            )
    style = platypus.TableStyle([('ALIGN', (1,1), (-1,-1), 'RIGHT'),
                               ('ALIGN', (0,0), (-1,0), 'CENTRE'),
                               ('GRID', (0,0), (-1,-1), 0.25, colors.black),
                               ('LINEBELOW', (0,0), (-1,0), 2, colors.black),
                               ('LINEBELOW',(1,-1), (-1, -1), 2, (0.5, 0.5, 0.5)),
                               ('TEXTCOLOR', (0,1), (0,-1), colors.black),
                               ('BACKGROUND', (0,0), (-1,0), (0,0.7,0.7))
                               ])
    g.setStyle(style)
    story.append(g)
    story.append(FrameBreak())

    #######################################################################
    #     Examples Page 4 - custom fonts
    #######################################################################
    # custom font with LettError-Robot font
    import reportlab.rl_config
    reportlab.rl_config.warnOnMissingFontGlyphs = 0

    from reportlab.pdfbase import pdfmetrics
    fontDir = os.path.join(os.path.dirname(reportlab.__file__),'fonts')
    face = pdfmetrics.EmbeddedType1Face(os.path.join(fontDir,'LeERC___.AFM'),os.path.join(fontDir,'LeERC___.PFB'))
    faceName = face.name  # should be 'LettErrorRobot-Chrome'
    pdfmetrics.registerTypeFace(face)
    font = pdfmetrics.Font(faceName, faceName, 'WinAnsiEncoding')
    pdfmetrics.registerFont(font)


    # put it inside a paragraph.
    story.append(Paragraph(
        """This is an ordinary paragraph, which happens to contain
        text in an embedded font:
        <font name="LettErrorRobot-Chrome">LettErrorRobot-Chrome</font>.
        Now for the real challenge...""", styleSheet['Normal']))


    styRobot = ParagraphStyle('Robot', styleSheet['Normal'])
    styRobot.fontSize = 16
    styRobot.leading = 20
    styRobot.fontName = 'LettErrorRobot-Chrome'

    story.append(Paragraph(
                "This whole paragraph is 16-point Letterror-Robot-Chrome.",
                styRobot))
    story.append(FrameBreak())

    if _GIF:
        story.append(Paragraph("Here is an Image flowable obtained from a string filename.",styleSheet['Italic']))
        story.append(platypus.Image(_GIF))
        story.append(Paragraph( "Here is an Image flowable obtained from a utf8 filename.", styleSheet['Italic']))
        story.append(platypus.Image(_GIF.encode('utf8')))
        story.append(Paragraph("Here is an Image flowable obtained from a string file url.",styleSheet['Italic']))
        story.append(platypus.Image(getFurl(_GIF)))
        story.append(Paragraph("Here is an Image flowable obtained from an open file.",styleSheet['Italic']))
        story.append(platypus.Image(open_for_read(_GIF,'b')))
        story.append(FrameBreak())
        try:
            img = platypus.Image('http://www.reportlab.com/rsrc/encryption.gif')
            story.append(Paragraph("Here is an Image flowable obtained from a string http url.",styleSheet['Italic']))
            story.append(img)
        except:
            story.append(Paragraph("The image could not be obtained from a string http url.",styleSheet['Italic']))
        story.append(FrameBreak())

    if _JPG:
        img = platypus.Image(_JPG)
        story.append(Paragraph("Here is an JPEG Image flowable obtained from a filename.",styleSheet['Italic']))
        story.append(img)
        story.append(Paragraph("Here is an JPEG Image flowable obtained from an open file.",styleSheet['Italic']))
        img = platypus.Image(open_for_read(_JPG,'b'))
        story.append(img)
        story.append(FrameBreak())


    return story

class AndyTemplate(BaseDocTemplate):
    _invalidInitArgs = ('pageTemplates',)
    def __init__(self, filename, **kw):
        frame1 = platypus.Frame(inch, 5.6*inch, 6*inch, 5.2*inch,id='F1')
        frame2 = platypus.Frame(inch, inch, 6*inch, 4.5*inch, showBoundary=1,id='F2')
        self.allowSplitting = 0
        apply(BaseDocTemplate.__init__,(self,filename),kw)
        self.addPageTemplates(PageTemplate('normal',[frame1,frame2],framePage))

    def fillFrame(self,flowables):
        f = self.frame
        while len(flowables)>0 and f is self.frame:
            self.handle_flowable(flowables)

    def build(self, flowables1, flowables2):
        assert filter(lambda x: not isinstance(x,Flowable), flowables1)==[], "flowables1 argument error"
        assert filter(lambda x: not isinstance(x,Flowable), flowables2)==[], "flowables2 argument error"
        self._startBuild()
        while (len(flowables1) > 0 or len(flowables1) > 0):
            self.clean_hanging()
            self.fillFrame(flowables1)
            self.fillFrame(flowables2)

        self._endBuild()


def showProgress(pageNo):
    print 'CALLBACK SAYS: page %d' % pageNo


def run():
    doc = AndyTemplate(outputfile('test_platypus_general.pdf'))
    #doc.setPageCallBack(showProgress)
    commentary = getCommentary()
    examples = getExamples()
    doc.build(commentary,examples)


class PlatypusTestCase(unittest.TestCase):
    "Make documents with lots of Platypus features"

    def test0(self):
        "Make a platypus document"
        run()


def makeSuite():
    return makeSuiteForClasses(PlatypusTestCase)


#noruntests
if __name__ == "__main__":
    if '-debug' in sys.argv:
        run()
    else:
        unittest.TextTestRunner().run(makeSuite())
        printLocation()
