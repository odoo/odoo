#!/bin/env python
#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
__version__=''' $Id: test_pdfgen_pycanvas.py 2619 2005-06-24 14:49:15Z rgbecker $ '''
__doc__='testscript for reportlab.pdfgen'
#tests and documents new low-level canvas and the pycanvas module to output Python source code.

import string, os

from reportlab.test import unittest
from reportlab.test.utils import makeSuiteForClasses, outputfile, printLocation

from reportlab.pdfgen import pycanvas   # gmcm 2000/10/13, pdfgen now a package
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.lib.utils import haveImages, _RL_DIR, rl_isfile

#################################################################
#
#  first some drawing utilities
#
#
################################################################

BASEFONT = ('Times-Roman', 10)
def framePageForm(c):
    c.beginForm("frame")
    c.saveState()
    # forms can't do non-constant operations
    #canvas.setFont('Times-BoldItalic',20)
    #canvas.drawString(inch, 10.5 * inch, title)

    #c.setFont('Times-Roman',10)
    #c.drawCentredString(4.135 * inch, 0.75 * inch,
    #                        'Page %d' % c.getPageNumber())

    #draw a border
    c.setFillColor(colors.ReportLabBlue)
    c.rect(0.3*inch, inch, 0.5*inch, 10*inch, fill=1)
    from reportlab.lib import corp
    c.translate(0.8*inch, 9.6*inch)
    c.rotate(90)
    logo = corp.ReportLabLogo(width=1.3*inch, height=0.5*inch, powered_by=1)
    c.setFillColorRGB(1,1,1)
    c.setStrokeColorRGB(1,1,1)
    logo.draw(c)
    #c.setStrokeColorRGB(1,0,0)
    #c.setLineWidth(5)
    #c.line(0.8 * inch, inch, 0.8 * inch, 10.75 * inch)
    #reset carefully afterwards
    #canvas.setLineWidth(1)
    #canvas.setStrokeColorRGB(0,0,0)\
    c.restoreState()
    c.endForm()

titlelist = []
closeit = 0


def framePage(canvas, title):
    global closeit
    titlelist.append(title)
    #canvas._inPage0()  # do we need this at all?  would be good to eliminate it
    canvas.saveState()
    canvas.setFont('Times-BoldItalic',20)

    canvas.drawString(inch, 10.5 * inch, title)
    canvas.bookmarkHorizontalAbsolute(title, 10.8*inch)
    #newsection(title)
    canvas.addOutlineEntry(title+" section", title, level=0, closed=closeit)
    closeit = not closeit # close every other one
    canvas.setFont('Times-Roman',10)
    canvas.drawCentredString(4.135 * inch, 0.75 * inch,
                            'Page %d' % canvas.getPageNumber())
    canvas.restoreState()
    canvas.doForm("frame")


def makesubsection(canvas, title, horizontal):
    canvas.bookmarkHorizontalAbsolute(title, horizontal)
    #newsubsection(title)
    canvas.addOutlineEntry(title+" subsection", title, level=1)


# outline helpers
#outlinenametree = []
#def newsection(name):
#    outlinenametree.append(name)


#def newsubsection(name):
#    from types import TupleType
#    thissection = outlinenametree[-1]
#    if type(thissection) is not TupleType:
#        subsectionlist = []
#        thissection = outlinenametree[-1] = (thissection, subsectionlist)
#    else:
#        (sectionname, subsectionlist) = thissection
#    subsectionlist.append(name)


class DocBlock:
    """A DocBlock has a chunk of commentary and a chunk of code.
    It prints the code and commentary, then executes the code,
    which is presumed to draw in a region reserved for it.
    """
    def __init__(self):
        self.comment1 = "A doc block"
        self.code = "canvas.setTextOrigin(cm, cm)\ncanvas.textOut('Hello World')"
        self.comment2 = "That was a doc block"
        self.drawHeight = 0

    def _getHeight(self):
        "splits into lines"
        self.comment1lines = string.split(self.comment1, '\n')
        self.codelines = string.split(self.code, '\n')
        self.comment2lines = string.split(self.comment2, '\n')
        textheight = (len(self.comment1lines) +
                len(self.code) +
                len(self.comment2lines) +
                18)
        return max(textheight, self.drawHeight)

    def draw(self, canvas, x, y):
        #specifies top left corner
        canvas.saveState()
        height = self._getHeight()
        canvas.rect(x, y-height, 6*inch, height)
        #first draw the text
        canvas.setTextOrigin(x + 3 * inch, y - 12)
        canvas.setFont('Times-Roman',10)
        canvas.textLines(self.comment1)
        drawCode(canvas, self.code)
        canvas.textLines(self.comment2)

        #now a box for the drawing, slightly within rect
        canvas.rect(x + 9, y - height + 9, 198, height - 18)
        #boundary:
        self.namespace = {'canvas':canvas,'cm': cm,'inch':inch}
        canvas.translate(x+9, y - height + 9)
        codeObj = compile(self.code, '<sample>','exec')
        exec codeObj in self.namespace

        canvas.restoreState()


def drawAxes(canvas, label):
    """draws a couple of little rulers showing the coords -
    uses points as units so you get an imperial ruler
    one inch on each side"""
    #y axis
    canvas.line(0,0,0,72)
    for y in range(9):
        tenths = (y+1) * 7.2
        canvas.line(-6,tenths,0,tenths)
    canvas.line(-6, 66, 0, 72)  #arrow...
    canvas.line(6, 66, 0, 72)  #arrow...

    canvas.line(0,0,72,0)
    for x in range(9):
        tenths = (x+1) * 7.2
        canvas.line(tenths,-6,tenths, 0)
    canvas.line(66, -6, 72, 0)  #arrow...
    canvas.line(66, +6, 72, 0)  #arrow...

    canvas.drawString(18, 30, label)


def drawCrossHairs(canvas, x, y):
    """just a marker for checking text metrics - blue for fun"""

    canvas.saveState()
    canvas.setStrokeColorRGB(0,1,0)
    canvas.line(x-6,y,x+6,y)
    canvas.line(x,y-6,x,y+6)
    canvas.restoreState()


def drawCode(canvas, code):
    """Draws a block of text at current point, indented and in Courier"""
    canvas.addLiteral('36 0 Td')
    canvas.setFillColor(colors.blue)
    canvas.setFont('Courier',10)

    t = canvas.beginText()
    t.textLines(code)
    c.drawText(t)

    canvas.setFillColor(colors.black)
    canvas.addLiteral('-36 0 Td')
    canvas.setFont('Times-Roman',10)


def makeDocument(filename, pageCallBack=None):
    #the extra arg is a hack added later, so other
    #tests can get hold of the canvas just before it is
    #saved

    c = pycanvas.Canvas(filename)
    c.setPageCompression(0)
    c.setPageCallBack(pageCallBack)
    framePageForm(c) # define the frame form
    c.showOutline()

    framePage(c, 'PDFgen graphics API test script')
    makesubsection(c, "PDFgen and PIDDLE", 10*inch)

    t = c.beginText(inch, 10*inch)
    t.setFont('Times-Roman', 10)
    drawCrossHairs(c, t.getX(),t.getY())
    t.textLines("""
The ReportLab library permits you to create PDF documents directly from
your Python code. The "pdfgen" subpackage is the lowest level exposed
to the user and lets you directly position test and graphics on the
page, with access to almost the full range of PDF features.
  The API is intended to closely mirror the PDF / Postscript imaging
model.  There is an almost one to one correspondence between commands
and PDF operators.  However, where PDF provides several ways to do a job,
we have generally only picked one.
  The test script attempts to use all of the methods exposed by the Canvas
class, defined in reportlab/pdfgen/canvas.py
  First, let's look at text output.  There are some basic commands
to draw strings:
-    canvas.setFont(fontname, fontsize [, leading])
-    canvas.drawString(x, y, text)
-    canvas.drawRightString(x, y, text)
-    canvas.drawCentredString(x, y, text)

The coordinates are in points starting at the bottom left corner of the
page.  When setting a font, the leading (i.e. inter-line spacing)
defaults to 1.2 * fontsize if the fontsize is not provided.

For more sophisticated operations, you can create a Text Object, defined
in reportlab/pdfgen/testobject.py.  Text objects produce tighter PDF, run
faster and have many methods for precise control of spacing and position.
Basic usage goes as follows:
-   tx = canvas.beginText(x, y)
-   tx.textOut('Hello')    # this moves the cursor to the right
-   tx.textLine('Hello again') # prints a line and moves down
-   y = tx.getY()       # getX, getY and getCursor track position
-   canvas.drawText(tx)  # all gets drawn at the end

The green crosshairs below test whether the text cursor is working
properly.  They should appear at the bottom left of each relevant
substring.
""")

    t.setFillColorRGB(1,0,0)
    t.setTextOrigin(inch, 4*inch)
    drawCrossHairs(c, t.getX(),t.getY())
    t.textOut('textOut moves across:')
    drawCrossHairs(c, t.getX(),t.getY())
    t.textOut('textOut moves across:')
    drawCrossHairs(c, t.getX(),t.getY())
    t.textOut('textOut moves across:')
    drawCrossHairs(c, t.getX(),t.getY())
    t.textLine('')
    drawCrossHairs(c, t.getX(),t.getY())
    t.textLine('textLine moves down')
    drawCrossHairs(c, t.getX(),t.getY())
    t.textLine('textLine moves down')
    drawCrossHairs(c, t.getX(),t.getY())
    t.textLine('textLine moves down')
    drawCrossHairs(c, t.getX(),t.getY())

    t.setTextOrigin(4*inch,3.25*inch)
    drawCrossHairs(c, t.getX(),t.getY())
    t.textLines('This is a multi-line\nstring with embedded newlines\ndrawn with textLines().\n')
    drawCrossHairs(c, t.getX(),t.getY())
    t.textLines(['This is a list of strings',
                'drawn with textLines().'])
    c.drawText(t)

    t = c.beginText(2*inch,2*inch)
    t.setFont('Times-Roman',10)
    drawCrossHairs(c, t.getX(),t.getY())
    t.textOut('Small text.')
    drawCrossHairs(c, t.getX(),t.getY())
    t.setFont('Courier',14)
    t.textOut('Bigger fixed width text.')
    drawCrossHairs(c, t.getX(),t.getY())
    t.setFont('Times-Roman',10)
    t.textOut('Small text again.')
    drawCrossHairs(c, t.getX(),t.getY())
    c.drawText(t)

    #mark the cursor where it stopped
    c.showPage()


    ##############################################################
    #
    # page 2 - line styles
    #
    ###############################################################

    #page 2 - lines and styles
    framePage(c, 'Line Drawing Styles')



    # three line ends, lines drawn the hard way
    #firt make some vertical end markers
    c.setDash(4,4)
    c.setLineWidth(0)
    c.line(inch,9.2*inch,inch, 7.8*inch)
    c.line(3*inch,9.2*inch,3*inch, 7.8*inch)
    c.setDash() #clears it

    c.setLineWidth(5)
    c.setLineCap(0)
    p = c.beginPath()
    p.moveTo(inch, 9*inch)
    p.lineTo(3*inch, 9*inch)
    c.drawPath(p)
    c.drawString(4*inch, 9*inch, 'the default - butt caps project half a width')
    makesubsection(c, "caps and joins", 8.5*inch)

    c.setLineCap(1)
    p = c.beginPath()
    p.moveTo(inch, 8.5*inch)
    p.lineTo(3*inch, 8.5*inch)
    c.drawPath(p)
    c.drawString(4*inch, 8.5*inch, 'round caps')

    c.setLineCap(2)
    p = c.beginPath()
    p.moveTo(inch, 8*inch)
    p.lineTo(3*inch, 8*inch)
    c.drawPath(p)
    c.drawString(4*inch, 8*inch, 'square caps')

    c.setLineCap(0)

    # three line joins
    c.setLineJoin(0)
    p = c.beginPath()
    p.moveTo(inch, 7*inch)
    p.lineTo(2*inch, 7*inch)
    p.lineTo(inch, 6.7*inch)
    c.drawPath(p)
    c.drawString(4*inch, 6.8*inch, 'Default - mitered join')

    c.setLineJoin(1)
    p = c.beginPath()
    p.moveTo(inch, 6.5*inch)
    p.lineTo(2*inch, 6.5*inch)
    p.lineTo(inch, 6.2*inch)
    c.drawPath(p)
    c.drawString(4*inch, 6.3*inch, 'round join')

    c.setLineJoin(2)
    p = c.beginPath()
    p.moveTo(inch, 6*inch)
    p.lineTo(2*inch, 6*inch)
    p.lineTo(inch, 5.7*inch)
    c.drawPath(p)
    c.drawString(4*inch, 5.8*inch, 'bevel join')

    c.setDash(6,6)
    p = c.beginPath()
    p.moveTo(inch, 5*inch)
    p.lineTo(3*inch, 5*inch)
    c.drawPath(p)
    c.drawString(4*inch, 5*inch, 'dash 6 points on, 6 off- setDash(6,6) setLineCap(0)')
    makesubsection(c, "dash patterns", 5*inch)

    c.setLineCap(1)
    p = c.beginPath()
    p.moveTo(inch, 4.5*inch)
    p.lineTo(3*inch, 4.5*inch)
    c.drawPath(p)
    c.drawString(4*inch, 4.5*inch, 'dash 6 points on, 6 off- setDash(6,6) setLineCap(1)')

    c.setLineCap(0)
    c.setDash([1,2,3,4,5,6],0)
    p = c.beginPath()
    p.moveTo(inch, 4.0*inch)
    p.lineTo(3*inch, 4.0*inch)
    c.drawPath(p)
    c.drawString(4*inch, 4*inch, 'dash growing - setDash([1,2,3,4,5,6],0) setLineCap(0)')

    c.setLineCap(1)
    c.setLineJoin(1)
    c.setDash(32,12)
    p = c.beginPath()
    p.moveTo(inch, 3.0*inch)
    p.lineTo(2.5*inch, 3.0*inch)
    p.lineTo(inch, 2*inch)
    c.drawPath(p)
    c.drawString(4*inch, 3*inch, 'dash pattern, join and cap style interacting - ')
    c.drawString(4*inch, 3*inch - 12, 'round join & miter results in sausages')

    c.showPage()


##############################################################
#
# higher level shapes
#
###############################################################
    framePage(c, 'Shape Drawing Routines')

    t = c.beginText(inch, 10*inch)
    t.textLines("""
Rather than making your own paths, you have access to a range of shape routines.
These are built in pdfgen out of lines and bezier curves, but use the most compact
set of operators possible.  We can add any new ones that are of general use at no
cost to performance.""")
    t.textLine()

    #line demo
    makesubsection(c, "lines", 10*inch)
    c.line(inch, 8*inch, 3*inch, 8*inch)
    t.setTextOrigin(4*inch, 8*inch)
    t.textLine('canvas.line(x1, y1, x2, y2)')

    #bezier demo - show control points
    makesubsection(c, "bezier curves", 7.5*inch)
    (x1, y1, x2, y2, x3, y3, x4, y4) = (
                        inch, 6.5*inch,
                        1.2*inch, 7.5 * inch,
                        3*inch, 7.5 * inch,
                        3.5*inch, 6.75 * inch
                        )
    c.bezier(x1, y1, x2, y2, x3, y3, x4, y4)
    c.setDash(3,3)
    c.line(x1,y1,x2,y2)
    c.line(x3,y3,x4,y4)
    c.setDash()
    t.setTextOrigin(4*inch, 7 * inch)
    t.textLine('canvas.bezier(x1, y1, x2, y2, x3, y3, x4, y4)')

    #rectangle
    makesubsection(c, "rectangles", 7*inch)
    c.rect(inch, 5.25 * inch, 2 * inch, 0.75 * inch)
    t.setTextOrigin(4*inch, 5.5 * inch)
    t.textLine('canvas.rect(x, y, width, height) - x,y is lower left')

    #wedge
    makesubsection(c, "wedges", 5*inch)
    c.wedge(inch, 5*inch, 3*inch, 4*inch, 0, 315)
    t.setTextOrigin(4*inch, 4.5 * inch)
    t.textLine('canvas.wedge(x1, y1, x2, y2, startDeg, extentDeg)')
    t.textLine('Note that this is an elliptical arc, not just circular!')

    #wedge the other way
    c.wedge(inch, 4*inch, 3*inch, 3*inch, 0, -45)
    t.setTextOrigin(4*inch, 3.5 * inch)
    t.textLine('Use a negative extent to go clockwise')

    #circle
    makesubsection(c, "circles", 3.5*inch)
    c.circle(1.5*inch, 2*inch, 0.5 * inch)
    c.circle(3*inch, 2*inch, 0.5 * inch)
    t.setTextOrigin(4*inch, 2 * inch)
    t.textLine('canvas.circle(x, y, radius)')
    c.drawText(t)

    c.showPage()

##############################################################
#
# Page 4 - fonts
#
###############################################################
    framePage(c, "Font Control")

    c.drawString(inch, 10*inch, 'Listing available fonts...')

    y = 9.5*inch
    for fontname in c.getAvailableFonts():
        c.setFont(fontname,24)
        c.drawString(inch, y, 'This should be %s' % fontname)
        y = y - 28
    makesubsection(c, "fonts and colors", 4*inch)

    c.setFont('Times-Roman', 12)
    t = c.beginText(inch, 4*inch)
    t.textLines("""Now we'll look at the color functions and how they interact
    with the text.  In theory, a word is just a shape; so setFillColorRGB()
    determines most of what you see.  If you specify other text rendering
    modes, an outline color could be defined by setStrokeColorRGB() too""")
    c.drawText(t)

    t = c.beginText(inch, 2.75 * inch)
    t.setFont('Times-Bold',36)
    t.setFillColor(colors.green)  #green
    t.textLine('Green fill, no stroke')

    #t.setStrokeColorRGB(1,0,0)  #ou can do this in a text object, or the canvas.
    t.setStrokeColor(colors.red)  #ou can do this in a text object, or the canvas.
    t.setTextRenderMode(2)   # fill and stroke
    t.textLine('Green fill, red stroke - yuk!')

    t.setTextRenderMode(0)   # back to default - fill only
    t.setFillColorRGB(0,0,0)   #back to default
    t.setStrokeColorRGB(0,0,0) #ditto
    c.drawText(t)
    c.showPage()

#########################################################################
#
#  Page 5 - coord transforms
#
#########################################################################
    framePage(c, "Coordinate Transforms")
    c.setFont('Times-Roman', 12)
    t = c.beginText(inch, 10 * inch)
    t.textLines("""This shows coordinate transformations.  We draw a set of axes,
    moving down the page and transforming space before each one.
    You can use saveState() and restoreState() to unroll transformations.
    Note that functions which track the text cursor give the cursor position
    in the current coordinate system; so if you set up a 6 inch high frame
    2 inches down the page to draw text in, and move the origin to its top
    left, you should stop writing text after six inches and not eight.""")
    c.drawText(t)

    drawAxes(c, "0.  at origin")
    c.addLiteral('%about to translate space')
    c.translate(2*inch, 7 * inch)
    drawAxes(c, '1. translate near top of page')

    c.saveState()
    c.translate(1*inch, -2 * inch)
    drawAxes(c, '2. down 2 inches, across 1')
    c.restoreState()

    c.saveState()
    c.translate(0, -3 * inch)
    c.scale(2, -1)
    drawAxes(c, '3. down 3 from top, scale (2, -1)')
    c.restoreState()

    c.saveState()
    c.translate(0, -5 * inch)
    c.rotate(-30)
    drawAxes(c, "4. down 5, rotate 30' anticlockwise")
    c.restoreState()

    c.saveState()
    c.translate(3 * inch, -5 * inch)
    c.skew(0,30)
    drawAxes(c, "5. down 5, 3 across, skew beta 30")
    c.restoreState()

    c.showPage()

#########################################################################
#
#  Page 6 - clipping
#
#########################################################################
    framePage(c, "Clipping")
    c.setFont('Times-Roman', 12)
    t = c.beginText(inch, 10 * inch)
    t.textLines("""This shows clipping at work. We draw a chequerboard of rectangles
    into a path object, and clip it.  This then forms a mask which limits the region of
    the page on which one can draw.  This paragraph was drawn after setting the clipping
    path, and so you should only see part of the text.""")
    c.drawText(t)

    c.saveState()
    #c.setFillColorRGB(0,0,1)
    p = c.beginPath()
    #make a chesboard effect, 1 cm squares
    for i in range(14):
        x0 = (3 + i) * cm
        for j in range(7):
            y0 = (16 + j) * cm
            p.rect(x0, y0, 0.85*cm, 0.85*cm)
    c.addLiteral('%Begin clip path')
    c.clipPath(p)
    c.addLiteral('%End clip path')
    t = c.beginText(3 * cm, 22.5 * cm)
    t.textLines("""This shows clipping at work.  We draw a chequerboard of rectangles
    into a path object, and clip it.  This then forms a mask which limits the region of
    the page on which one can draw.  This paragraph was drawn after setting the clipping
    path, and so you should only see part of the text.
        This shows clipping at work.  We draw a chequerboard of rectangles
    into a path object, and clip it.  This then forms a mask which limits the region of
    the page on which one can draw.  This paragraph was drawn after setting the clipping
    path, and so you should only see part of the text.
        This shows clipping at work.  We draw a chequerboard of rectangles
    into a path object, and clip it.  This then forms a mask which limits the region of
    the page on which one can draw.  This paragraph was drawn after setting the clipping
    path, and so you should only see part of the text.""")
    c.drawText(t)

    c.restoreState()

    t = c.beginText(inch, 5 * inch)
    t.textLines("""You can also use text as an outline for clipping with the text render mode.
        The API is not particularly clean on this and one has to follow the right sequence;
        this can be optimized shortly.""")
    c.drawText(t)

    #first the outline
    c.saveState()
    t = c.beginText(inch, 3.0 * inch)
    t.setFont('Helvetica-BoldOblique',108)
    t.setTextRenderMode(5)  #stroke and add to path
    t.textLine('Python!')
    t.setTextRenderMode(0)
    c.drawText(t)    #this will make a clipping mask

    #now some small stuff which wil be drawn into the current clip mask
    t = c.beginText(inch, 4 * inch)
    t.setFont('Times-Roman',6)
    t.textLines((('spam ' * 40) + '\n') * 15)
    c.drawText(t)

    #now reset canvas to get rid of the clipping mask
    c.restoreState()

    c.showPage()


#########################################################################
#
#  Page 7 - images
#
#########################################################################
    framePage(c, "Images")
    c.setFont('Times-Roman', 12)
    t = c.beginText(inch, 10 * inch)
    if not haveImages:
        c.drawString(inch, 11*inch,
                     "Python Imaging Library not found! Below you see rectangles instead of images.")

    t.textLines("""PDFgen uses the Python Imaging Library to process a very wide variety of image formats.
        This page shows image capabilities.  If I've done things right, the bitmap should have
        its bottom left corner aligned with the crosshairs.
        There are two methods for drawing images.  The recommended use is to call drawImage.
        This produces the smallest PDFs and the fastest generation times as each image's binary data is
        only embedded once in the file.  Also you can use advanced features like transparency masks.
        You can also use drawInlineImage, which puts images in the page stream directly.
        This is slightly faster for Acrobat to render or for very small images, but wastes
        space if you use images more than once.""")

    c.drawText(t)

    gif = os.path.join(_RL_DIR,'test','pythonpowered.gif')
    if haveImages and rl_isfile(gif):
        c.drawInlineImage(gif,2*inch, 7*inch)
    else:
        c.rect(2*inch, 7*inch, 110, 44)

    c.line(1.5*inch, 7*inch, 4*inch, 7*inch)
    c.line(2*inch, 6.5*inch, 2*inch, 8*inch)
    c.drawString(4.5 * inch, 7.25*inch, 'inline image drawn at natural size')

    if haveImages and rl_isfile(gif):
        c.drawInlineImage(gif,2*inch, 5*inch, inch, inch)
    else:
        c.rect(2*inch, 5*inch, inch, inch)

    c.line(1.5*inch, 5*inch, 4*inch, 5*inch)
    c.line(2*inch, 4.5*inch, 2*inch, 6*inch)
    c.drawString(4.5 * inch, 5.25*inch, 'inline image distorted to fit box')

    c.drawString(1.5 * inch, 4*inch, 'Image XObjects can be defined once in the file and drawn many times.')
    c.drawString(1.5 * inch, 3.75*inch, 'This results in faster generation and much smaller files.')

    for i in range(5):
        if haveImages:
            (w, h) = c.drawImage(gif, (1.5 + i)*inch, 3*inch)
        else:
            c.rect((1.5 + i)*inch, 3*inch, 110, 44)

    myMask = [254,255,222,223,0,1]
    c.drawString(1.5 * inch, 2.5*inch, "The optional 'mask' parameter lets you define transparent colors. We used a color picker")
    c.drawString(1.5 * inch, 2.3*inch, "to determine that the yellow in the image above is RGB=(225,223,0).  We then define a mask")
    c.drawString(1.5 * inch, 2.1*inch, "spanning these RGB values:  %s.  The background vanishes!!" % myMask)
    c.drawString(2.5*inch, 1.2*inch, 'This would normally be obscured')
    if haveImages:
        c.drawImage(gif, 3*inch, 1.2*inch, w, h, mask=myMask)
    else:
        c.rect(3*inch, 1.2*inch, 110, 44)

    c.showPage()


#########################################################################
#
#  Page 8 - Forms and simple links
#
#########################################################################
    framePage(c, "Forms and Links")
    c.setFont('Times-Roman', 12)
    t = c.beginText(inch, 10 * inch)
    t.textLines("""Forms are sequences of text or graphics operations
      which are stored only once in a PDF file and used as many times
      as desired.  The blue logo bar to the left is an example of a form
      in this document.  See the function framePageForm in this demo script
      for an example of how to use canvas.beginForm(name, ...) ... canvas.endForm().

      Documents can also contain cross references where (for example) a rectangle
      on a page may be bound to a position on another page.  If the user clicks
      on the rectangle the PDF viewer moves to the bound position on the other
      page.  There are many other types of annotations and links supported by PDF.

      For example, there is a bookmark to each page in this document and below
      is a browsable index that jumps to those pages. In addition we show two
      URL hyperlinks; for these, you specify a rectangle but must draw the contents
      or any surrounding rectangle yourself.
      """)
    c.drawText(t)

    nentries = len(titlelist)
    xmargin = 3*inch
    xmax = 7*inch
    ystart = 6.54*inch
    ydelta = 0.4*inch
    for i in range(nentries):
        yposition = ystart - i*ydelta
        title = titlelist[i]
        c.drawString(xmargin, yposition, title)
        c.linkAbsolute(title, title, (xmargin-ydelta/4, yposition-ydelta/4, xmax, yposition+ydelta/2))


    # test URLs
    r1 = (inch, 3*inch, 5*inch, 3.25*inch) # this is x1,y1,x2,y2
    c.linkURL('http://www.reportlab.com/', r1, thickness=1, color=colors.green)
    c.drawString(inch+3, 3*inch+6, 'Hyperlink to www.reportlab.com, with green border')

    r1 = (inch, 2.5*inch, 5*inch, 2.75*inch) # this is x1,y1,x2,y2
    c.linkURL('mailto:reportlab-users@egroups.com', r1) #, border=0)
    c.drawString(inch+3, 2.5*inch+6, 'mailto: hyperlink, without border')

    r1 = (inch, 2*inch, 5*inch, 2.25*inch) # this is x1,y1,x2,y2
    c.linkURL('http://www.reportlab.com/', r1,
                      thickness=2,
                      dashArray=[2,4],
                      color=colors.magenta)
    c.drawString(inch+3, 2*inch+6, 'Hyperlink with custom border style')

    ### now do stuff for the outline
    #for x in outlinenametree: print x
    #stop
    #apply(c.setOutlineNames0, tuple(outlinenametree))
    return c


def run(filename):
    c = makeDocument(filename)
    c.save()
    source = str(c)
    open(outputfile("test_pdfgen_pycanvas_out.txt"),"w").write(source)
    import reportlab.rl_config
    if reportlab.rl_config.verbose:
        print source


def pageShapes(c):
    """Demonstrates the basic lines and shapes"""

    c.showPage()
    framePage(c, "Basic line and shape routines""")
    c.setTextOrigin(inch, 10 * inch)
    c.setFont('Times-Roman', 12)
    c.textLines("""pdfgen provides some basic routines for drawing straight and curved lines,
    and also for solid shapes.""")

    y = 9 * inch
    d = DocBlock()
    d.comment1 = 'Lesson one'
    d.code = "canvas.textOut('hello, world')"
    print d.code

    d.comment2 = 'Lesson two'

    d.draw(c, inch, 9 * inch)


class PdfgenTestCase(unittest.TestCase):
    "Make documents with lots of Pdfgen features"

    def test0(self):
        "Make a PDFgen document with most graphics features"
        run(outputfile('test_pdfgen_pycanvas.pdf'))

def makeSuite():
    return makeSuiteForClasses(PdfgenTestCase)


#noruntests
if __name__ == "__main__":
    unittest.TextTestRunner().run(makeSuite())
    printLocation()
