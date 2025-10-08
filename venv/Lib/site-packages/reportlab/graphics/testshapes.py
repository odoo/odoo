#!/bin/env python
#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/graphics/testshapes.py

# testshapes.py - draws shapes onto a PDF canvas.


__version__ = ''' $Id $ '''
__doc__='''Execute this script to see some test drawings.

This contains a number of routines to generate test drawings
for reportlab/graphics.  For now many of them are contrived,
but we will expand them to try and trip up any parser.
Feel free to add more.
'''

import os, sys
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.utils import asNative, base64_decodebytes
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.graphics.shapes import *
import unittest

_FONTS = ['Times-Roman','Vera','Times-BoldItalic',]

def _setup():
    from reportlab.pdfbase import pdfmetrics, ttfonts
    pdfmetrics.registerFont(ttfonts.TTFont("Vera", "Vera.ttf"))
    pdfmetrics.registerFont(ttfonts.TTFont("VeraBd", "VeraBd.ttf"))
    pdfmetrics.registerFont(ttfonts.TTFont("VeraIt", "VeraIt.ttf"))
    pdfmetrics.registerFont(ttfonts.TTFont("VeraBI", "VeraBI.ttf"))
    F = ['Times-Roman','Courier','Helvetica','Vera', 'VeraBd', 'VeraIt', 'VeraBI']
    if sys.platform=='win32':
        for name, ttf in [
            ('Adventurer Light SF','Advlit.ttf'),('ArialMS','ARIAL.TTF'),
            ('Arial Unicode MS', 'ARIALUNI.TTF'),
            ('Book Antiqua','BKANT.TTF'),
            ('Century Gothic','GOTHIC.TTF'),
            ('Comic Sans MS', 'COMIC.TTF'),
            ('Elementary Heavy SF Bold','Vwagh.ttf'),
            ('Firenze SF','flot.ttf'),
            ('Garamond','GARA.TTF'),
            ('Jagger','Rols.ttf'),
            ('Monotype Corsiva','MTCORSVA.TTF'),
            ('Seabird SF','seag.ttf'),
            ('Tahoma','TAHOMA.TTF'),
            ('VerdanaMS','VERDANA.TTF'),
            ]:
            for D in (r'c:\WINNT',r'c:\Windows'):
                fn = os.path.join(D,'Fonts',ttf)
                if os.path.isfile(fn):
                    try:
                        f = ttfonts.TTFont(name, fn)
                        pdfmetrics.registerFont(f)
                        F.append(name)
                    except:
                        pass
    return F

def resetFonts():
    for f in _setup():
        if f not in _FONTS:
            _FONTS.append(f)
from reportlab.rl_config import register_reset
register_reset(resetFonts)
resetFonts()

#########################################################
#
#   Collections of shape drawings.
#
#########################################################
def getFailedDrawing(funcName):
    """Generate a drawing in case something goes really wrong.

    This will create a drawing to be displayed whenever some
    other drawing could not be executed, because the generating
    function does something terribly wrong! The box contains
    an attention triangle, plus some error message.
    """

    D = Drawing(400, 200)

    points = [200,170, 140,80, 260,80]
    D.add(Polygon(points,
                  strokeWidth=0.5*cm,
                  strokeColor=colors.red,
                  fillColor=colors.yellow))

    s = String(200, 40,
               "Error in generating function '%s'!" % funcName,
               textAnchor='middle')
    D.add(s)

    return D


# These are the real drawings to be eye-balled.

def getDrawing01():
    """Hello World, on a rectangular background.

    The rectangle's fillColor is yellow.
    The string's fillColor is red.
    """

    D = Drawing(400, 200)
    D.add(Rect(50, 50, 300, 100, fillColor=colors.yellow))
    D.add(String(180,100, 'Hello World', fillColor=colors.red))
    D.add(String(180,86, b'Special characters \xc2\xa2\xc2\xa9\xc2\xae\xc2\xa3\xce\xb1\xce\xb2', fillColor=colors.red))

    return D


def getDrawing02():
    """Various Line shapes.

    The lines are blue and their strokeWidth is 5 mm.
    One line has a strokeDashArray set to [5, 10, 15].
    """

    D = Drawing(400, 200)
    D.add(Line(50,50, 300,100,
               strokeColor=colors.blue,
               strokeWidth=0.5*cm,
               ))
    D.add(Line(50,100, 300,50,
               strokeColor=colors.blue,
               strokeWidth=0.5*cm,
               strokeDashArray=[5, 10, 15],
               ))

    #x = 1/0 # Comment this to see the actual drawing!

    return D


def getDrawing03():
    """Text strings in various sizes and different fonts.

    Font size increases from 12 to 36 and from bottom left
    to upper right corner.  The first ones should be in
    Times-Roman.  Finally, a solitary Courier string at
    the top right corner.
    """

    D = Drawing(400, 200)
    for size in range(12, 36, 4):
        D.add(String(10+size*2,
                     10+size*2,
                     'Hello World',
                     fontName=_FONTS[0],
                     fontSize=size))

    D.add(String(150, 150,
                 'Hello World',
                 fontName=_FONTS[1],
                 fontSize=36))
    return D


def getDrawing04():
    """Text strings in various colours.

    Colours are blue, yellow and red from bottom left
    to upper right.
    """

    D = Drawing(400, 200)
    i = 0
    for color in (colors.blue, colors.yellow, colors.red):
        D.add(String(50+i*30, 50+i*30,
                     'Hello World', fillColor=color))
        i = i + 1

    return D


def getDrawing05():
    """Text strings with various anchors (alignments).

    Text alignment conforms to the anchors in the left column.
    """

    D = Drawing(400, 200)

    lineX = 250
    D.add(Line(lineX,10, lineX,190, strokeColor=colors.gray))

    y = 130
    for anchor in ('start', 'middle', 'end'):
        D.add(String(lineX, y, 'Hello World', textAnchor=anchor))
        D.add(String(50, y, anchor + ':'))
        y = y - 30

    return D


def getDrawing06():
    """This demonstrates all the basic shapes at once.

    There are no groups or references.
    Each solid shape should have a green fill.
    """

    green = colors.green

    D = Drawing(400, 200) #, fillColor=green)

    D.add(Line(10,10, 390,190))

    D.add(Circle(100,100,20, fillColor=green))
    D.add(Circle(200,100,40, fillColor=green))
    D.add(Circle(300,100,30, fillColor=green))

    D.add(Wedge(330,100,40, -10,40, fillColor=green))

    D.add(PolyLine([120,10, 130,20, 140,10, 150,20, 160,10,
                    170,20, 180,10, 190,20, 200,10], fillColor=green))

    D.add(Polygon([300,20, 350,20, 390,80, 300,75, 330,40], fillColor=green))

    D.add(Ellipse(50,150, 40, 20, fillColor=green))

    D.add(Rect(120,150, 60,30,
               strokeWidth=10,
               strokeColor=colors.yellow,
               fillColor=green))  #square corners
    D.add(Rect(220, 150, 60, 30, 10, 10, fillColor=green))  #round corners

    D.add(String(10,50, 'Basic Shapes', fillColor=colors.black, fontName='Helvetica'))

    return D

def getDrawing07():
    """This tests the ability to translate and rotate groups.  The first set of axes should be
    near the bottom left of the drawing.  The second should be rotated counterclockwise
    by 15 degrees.  The third should be rotated by 30 degrees."""
    D = Drawing(400, 200)

    Axis = Group(
        Line(0,0,100,0), #x axis
        Line(0,0,0,50),   # y axis
        Line(0,10,10,10), #ticks on y axis
        Line(0,20,10,20),
        Line(0,30,10,30),
        Line(0,40,10,40),
        Line(10,0,10,10), #ticks on x axis
        Line(20,0,20,10),
        Line(30,0,30,10),
        Line(40,0,40,10),
        Line(50,0,50,10),
        Line(60,0,60,10),
        Line(70,0,70,10),
        Line(80,0,80,10),
        Line(90,0,90,10),
        String(20, 35, 'Axes', fill=colors.black)
        )

    firstAxisGroup = Group(Axis)
    firstAxisGroup.translate(10,10)
    D.add(firstAxisGroup)

    secondAxisGroup = Group(Axis)
    secondAxisGroup.translate(150,10)
    secondAxisGroup.rotate(15)

    D.add(secondAxisGroup)


    thirdAxisGroup = Group(Axis, transform=mmult(translate(300,10), rotate(30)))
    D.add(thirdAxisGroup)

    return D


def getDrawing08():
    """This tests the ability to scale coordinates. The bottom left set of axes should be
    near the bottom left of the drawing.  The bottom right should be stretched vertically
    by a factor of 2.  The top left one should be stretched horizontally by a factor of 2.
    The top right should have the vertical axiss leaning over to the right by 30 degrees."""
    D = Drawing(400, 200)

    Axis = Group(
        Line(0,0,100,0), #x axis
        Line(0,0,0,50),   # y axis
        Line(0,10,10,10), #ticks on y axis
        Line(0,20,10,20),
        Line(0,30,10,30),
        Line(0,40,10,40),
        Line(10,0,10,10), #ticks on x axis
        Line(20,0,20,10),
        Line(30,0,30,10),
        Line(40,0,40,10),
        Line(50,0,50,10),
        Line(60,0,60,10),
        Line(70,0,70,10),
        Line(80,0,80,10),
        Line(90,0,90,10),
        String(20, 35, 'Axes', fill=colors.black)
        )

    firstAxisGroup = Group(Axis)
    firstAxisGroup.translate(10,10)
    D.add(firstAxisGroup)

    secondAxisGroup = Group(Axis)
    secondAxisGroup.translate(150,10)
    secondAxisGroup.scale(1,2)
    D.add(secondAxisGroup)

    thirdAxisGroup = Group(Axis)
    thirdAxisGroup.translate(10,125)
    thirdAxisGroup.scale(2,1)
    D.add(thirdAxisGroup)

    fourthAxisGroup = Group(Axis)
    fourthAxisGroup.translate(250,125)
    fourthAxisGroup.skew(30,0)
    D.add(fourthAxisGroup)


    return D

def getDrawing09():
    """This tests rotated strings

    Some renderers will have a separate mechanism for font drawing.  This test
    just makes sure strings get transformed the same way as regular graphics."""
    D = Drawing(400, 200)

    fontName = _FONTS[0]
    fontSize = 12
    text = "I should be totally horizontal and enclosed in a box"
    textWidth = stringWidth(text, fontName, fontSize)


    g1 = Group(
            String(20, 20, text, fontName=fontName, fontSize = fontSize),
            Rect(18, 18, textWidth + 4, fontSize + 4, fillColor=None)
            )
    D.add(g1)

    text = "I should slope up by 15 degrees, so my right end is higher than my left"
    textWidth = stringWidth(text, fontName, fontSize)
    g2 = Group(
            String(20, 20, text, fontName=fontName, fontSize = fontSize),
            Rect(18, 18, textWidth + 4, fontSize + 4, fillColor=None)
            )
    g2.translate(0, 50)
    g2.rotate(15)
    D.add(g2)

    return D

def getDrawing10():
    """This tests nested groups with multiple levels of coordinate transformation.
    Each box should be staggered up and to the right, moving by 25 points each time."""
    D = Drawing(400, 200)

    fontName = _FONTS[0]
    fontSize = 12

    g1 = Group(
            Rect(0, 0, 100, 20, fillColor=colors.yellow),
            String(5, 5, 'Text in the box', fontName=fontName, fontSize = fontSize)
            )
    D.add(g1)

    g2 = Group(g1, transform = translate(25,25))
    D.add(g2)

    g3 = Group(g2, transform = translate(25,25))
    D.add(g3)

    g4 = Group(g3, transform = translate(25,25))
    D.add(g4)


    return D

from reportlab.graphics.widgets.signsandsymbols import SmileyFace
def getDrawing11():
    '''test of anchoring'''
    def makeSmiley(x, y, size, color):
        "Make a smiley data item representation."
        d = size
        s = SmileyFace()
        s.fillColor = color
        s.x = x-d
        s.y = y-d
        s.size = d*2
        return s

    D = Drawing(400, 200) #, fillColor=colors.purple)
    g = Group(transform=(1,0,0,1,0,0))
    g.add(makeSmiley(100,100,10,colors.red))
    g.add(Line(90,100,110,100,strokeColor=colors.green))
    g.add(Line(100,90,100,110,strokeColor=colors.green))
    D.add(g)
    g = Group(transform=(2,0,0,2,100,-100))
    g.add(makeSmiley(100,100,10,colors.blue))
    g.add(Line(90,100,110,100,strokeColor=colors.green))
    g.add(Line(100,90,100,110,strokeColor=colors.green))
    D.add(g)
    g = Group(transform=(2,0,0,2,0,0))
    return D


def getDrawing12():
    """Text strings in a non-standard font.
    All that is required is to place the .afm and .pfb files
    on the font path given in rl_config.py,
    for example in reportlab/fonts/.
    """
    faceName = "DarkGardenMK"
    D = Drawing(400, 200)
    for size in range(12, 36, 4):
        D.add(String(10+size*2,
                     10+size*2,
                     'Hello World',
                     fontName=faceName,
                     fontSize=size))
    return D

def getDrawing13():
    'Test Various TTF Fonts'

    def drawit(F,w=400,h=200,fontSize=12,slack=2,gap=5):
        D = Drawing(w,h)
        th = 2*gap + fontSize*1.2
        gh = gap + .2*fontSize
        y = h
        maxx = 0
        for fontName in F:
            y -= th
            text = fontName+asNative(b': I should be totally horizontal and enclosed in a box and end in alphabetagamma \xc2\xa2\xc2\xa9\xc2\xae\xc2\xa3\xca\xa5\xd0\x96\xd6\x83\xd7\x90\xd9\x82\xe0\xa6\x95\xce\xb1\xce\xb2\xce\xb3')
            textWidth = stringWidth(text, fontName, fontSize)
            maxx = max(maxx,textWidth+20)
            D.add(
                Group(Rect(8, y-gh, textWidth + 4, th, strokeColor=colors.red, strokeWidth=.5, fillColor=colors.lightgrey),
                    String(10, y, text, fontName=fontName, fontSize = fontSize)))
            y -= 5
        return maxx, h-y+gap, D
    maxx, maxy, D = drawit(_FONTS)
    if maxx>400 or maxy>200: _,_,D = drawit(_FONTS,maxx,maxy)
    return D

def smallArrow():
    '''create a small PIL image'''
    from reportlab.graphics.renderPM import _getImage
    b = base64_decodebytes(b'''R0lGODdhCgAHAIMAAP/////29v/d3f+ysv9/f/9VVf9MTP8iIv8ICP8AAAAAAAAAAAAAAAAAAAAA
AAAAACwAAAAACgAHAAAIMwABCBxIsKABAQASFli4MAECAgEAJJhIceKBAQkyasx4YECBjx8TICAQ
AIDJkwYEAFgZEAA7''')
    return _getImage().open(BytesIO(b))

def getDrawing14():
    '''test shapes.Image'''
    from reportlab.graphics.shapes import Image
    D = Drawing(400, 200)
    im0 = smallArrow()
    D.add(Image(x=0,y=0,width=None,height=None,path=im0))
    im1 = smallArrow()
    D.add(Image(x=400-20,y=200-14,width=20,height=14,path=im1))
    return D

def getAllFunctionDrawingNames(doTTF=1):
    "Get a list of drawing function names from somewhere."

    funcNames = []

    # Here we get the names from the global name space.
    symbols = list(globals().keys())
    symbols.sort()
    for funcName in symbols:
        if funcName[0:10] == 'getDrawing':
            if doTTF or funcName!='getDrawing13':
                funcNames.append(funcName)

    return funcNames

def _evalFuncDrawing(name, D, l=None, g=None):
    if g is None: g = globals()
    if l is None: l = locals()
    func = l.get(name,g.get(name,None))
    try:
        d = func()
    except:
        d = getFailedDrawing(name)
    D.append((d, getattr(func,'.__doc__',''), name[3:]))

def getAllTestDrawings(doTTF=1):
    D = []
    for f in getAllFunctionDrawingNames(doTTF=doTTF):
        _evalFuncDrawing(f,D)
    return D

def writePDF(drawings):
    "Create and save a PDF file containing some drawings."

    pdfPath = os.path.splitext(sys.argv[0])[0] + '.pdf'
    c = Canvas(pdfPath)
    c.setFont(_FONTS[0], 32)
    c.drawString(80, 750, 'ReportLab Graphics-Shapes Test')

    # Print drawings in a loop, with their doc strings.
    c.setFont(_FONTS[0], 12)
    y = 740
    i = 1
    for (drawing, docstring, funcname) in drawings:
        if y < 300:  # Allows 5-6 lines of text.
            c.showPage()
            y = 740
        # Draw a title.
        y = y - 30
        c.setFont(_FONTS[2],12)
        c.drawString(80, y, '%s (#%d)' % (funcname, i))
        c.setFont(_FONTS[0],12)
        y = y - 14
        textObj = c.beginText(80, y)
        textObj.textLines(docstring)
        c.drawText(textObj)
        y = textObj.getY()
        y = y - drawing.height
        drawing.drawOn(c, 80, y)
        i = i + 1

    c.save()
    print('wrote %s ' % pdfPath)


class ShapesTestCase(unittest.TestCase):
    "Test generating all kinds of shapes."

    def setUp(self):
        "Prepare some things before the tests start."

        self.funcNames = getAllFunctionDrawingNames()
        self.drawings = []


    def tearDown(self):
        "Do what has to be done after the tests are over."

        writePDF(self.drawings)


    # This should always succeed. If each drawing would be
    # wrapped in a dedicated test method like this one, it
    # would be possible to have a count for wrong tests
    # as well... Something like this is left for later...
    def testAllDrawings(self):
        "Make a list of drawings."

        for f in self.funcNames:
            if f[0:10] == 'getDrawing':
                # Make an instance and get its doc string.
                # If that fails, use a default error drawing.
                _evalFuncDrawing(f,self.drawings)


def makeSuite():
    "Make a test suite for unit testing."

    suite = unittest.TestSuite()
    suite.addTest(ShapesTestCase('testAllDrawings'))
    return suite


if __name__ == "__main__":
    unittest.TextTestRunner().run(makeSuite())
