
from reportlab.test import unittest
from reportlab.test.utils import makeSuiteForClasses, outputfile, printLocation

from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, Group, Line, Rect
from reportlab.graphics.widgetbase import Widget
from reportlab.graphics.widgets.grids import *
from reportlab.graphics import renderPDF
from reportlab.graphics import renderSVG


class GridTestCase(unittest.TestCase):
    "Testing diagrams containing grid widgets."

    def _test0(self):
        "Create color ranges."

        c0, c1 = colors.Color(0, 0, 0), colors.Color(1, 1, 1)
        for c in colorRange(c0, c1, 4):
            print c
        print

        c0, c1 = colors.CMYKColor(0, 0, 0, 0), colors.CMYKColor(0, 0, 0, 1)
        for c in colorRange(c0, c1, 4):
            print c
        print

        c0, c1 = colors.PCMYKColor(0, 0, 0, 0), colors.PCMYKColor(0, 0, 0, 100)
        for c in colorRange(c0, c1, 4):
            print c
        print


    def makeDrawing0(self):
        "Generate a RLG drawing with some uncommented grid samples."

        D = Drawing(450, 650)

        d = 80
        s = 50

        for row in range(10):
            y = 530 - row*d
            if row == 0:
                for col in range(4):
                    x = 20 + col*d
                    g = Grid()
                    g.x = x
                    g.y = y
                    g.width = s
                    g.height = s
                    g.useRects = 0
                    g.useLines = 1
                    if col == 0:
                        pass
                    elif col == 1:
                        g.delta0 = 10
                    elif col == 2:
                        g.orientation = 'horizontal'
                    elif col == 3:
                        g.deltaSteps = [5, 10, 20, 30]
                    g.demo()
                    D.add(g)
            elif row == 1:
                for col in range(4):
                    x = 20 + col*d
                    g = Grid()
                    g.y = y
                    g.x = x
                    g.width = s
                    g.height = s
                    if col == 0:
                        pass
                    elif col == 1:
                        g.delta0 = 10
                    elif col == 2:
                        g.orientation = 'horizontal'
                    elif col == 3:
                        g.deltaSteps = [5, 10, 20, 30]
                        g.useRects = 1
                        g.useLines = 0
                    g.demo()
                    D.add(g)
            elif row == 2:
                for col in range(3):
                    x = 20 + col*d
                    g = Grid()
                    g.x = x
                    g.y = y
                    g.width = s
                    g.height = s
                    g.useLines = 1
                    g.useRects = 1
                    if col == 0:
                        pass
                    elif col == 1:
                        g.delta0 = 10
                    elif col == 2:
                        g.orientation = 'horizontal'
                    g.demo()
                    D.add(g)
            elif row == 3:
                for col in range(3):
                    x = 20 + col*d
                    sr = ShadedRect()
                    sr.x = x
                    sr.y = y
                    sr.width = s
                    sr.height = s
                    sr.fillColorStart = colors.Color(0, 0, 0)
                    sr.fillColorEnd = colors.Color(1, 1, 1)
                    if col == 0:
                        sr.numShades = 5
                    elif col == 1:
                        sr.numShades = 2
                    elif col == 2:
                        sr.numShades = 1
                    sr.demo()
                    D.add(sr)
            elif row == 4:
                for col in range(3):
                    x = 20 + col*d
                    sr = ShadedRect()
                    sr.x = x
                    sr.y = y
                    sr.width = s
                    sr.height = s
                    sr.fillColorStart = colors.red
                    sr.fillColorEnd = colors.blue
                    sr.orientation = 'horizontal'
                    if col == 0:
                        sr.numShades = 10
                    elif col == 1:
                        sr.numShades = 20
                    elif col == 2:
                        sr.numShades = 50
                    sr.demo()
                    D.add(sr)
            elif row == 5:
                for col in range(3):
                    x = 20 + col*d
                    sr = ShadedRect()
                    sr.x = x
                    sr.y = y
                    sr.width = s
                    sr.height = s
                    sr.fillColorStart = colors.white
                    sr.fillColorEnd = colors.green
                    sr.orientation = 'horizontal'
                    if col == 0:
                        sr.numShades = 10
                    elif col == 1:
                        sr.numShades = 20
                        sr.orientation = 'vertical'
                    elif col == 2:
                        sr.numShades = 50
                    sr.demo()
                    D.add(sr)
            elif row == 6:
                for col in range(3):
                    x = 20 + col*d
                    sr = ShadedRect()
                    sr.x = x
                    sr.y = y+s
                    sr.width = s
                    sr.height = -s
                    sr.fillColorStart = colors.white
                    sr.fillColorEnd = colors.green
                    sr.orientation = 'horizontal'
                    if col == 0:
                        sr.numShades = 10
                    elif col == 1:
                        sr.numShades = 20
                        sr.orientation = 'vertical'
                    elif col == 2:
                        sr.numShades = 50
                    sr.demo()
                    D.add(sr)

        return D


    def makeDrawing1(self):
        "Generate a RLG drawing with some uncommented grid samples."

        D = Drawing(450, 650)

        d = 80
        s = 50

        for row in range(2):
            y = 530 - row*d
            if row == 0:
                for col in range(4):
                    x = 20 + col*d
                    g = DoubleGrid()
                    g.x = x
                    g.y = y
                    g.width = s
                    g.height = s

                    # This should be done implicitely...
                    g.grid0.x = x
                    g.grid0.y = y
                    g.grid1.x = x
                    g.grid1.y = y
                    g.grid0.width = s
                    g.grid0.height = s
                    g.grid1.width = s
                    g.grid1.height = s

                    if col == 0:
                        pass
                    elif col == 1:
                        g.grid0.delta0 = 10
                    elif col == 2:
                        g.grid0.delta0 = 5
                    elif col == 3:
                        g.grid0.deltaSteps = [5, 10, 20, 30]
                    g.demo()
                    D.add(g)
            elif row == 1:
                for col in range(4):
                    x = 20 + col*d
                    g = DoubleGrid()
                    g.x = x
                    g.y = y
                    g.width = s
                    g.height = s

                    # This should be done implicitely...
                    g.grid0.x = x
                    g.grid0.y = y
                    g.grid1.x = x
                    g.grid1.y = y
                    g.grid0.width = s
                    g.grid0.height = s
                    g.grid1.width = s
                    g.grid1.height = s

                    if col == 0:
                        g.grid0.useRects = 0
                        g.grid0.useLines = 1
                        g.grid1.useRects = 0
                        g.grid1.useLines = 1
                    elif col == 1:
                        g.grid0.useRects = 1
                        g.grid0.useLines = 1
                        g.grid1.useRects = 0
                        g.grid1.useLines = 1
                    elif col == 2:
                        g.grid0.useRects = 1
                        g.grid0.useLines = 0
                        g.grid1.useRects = 0
                        g.grid1.useLines = 1
                    elif col == 3:
                        g.grid0.useRects = 1
                        g.grid0.useLines = 0
                        g.grid1.useRects = 1
                        g.grid1.useLines = 0
                    g.demo()
                    D.add(g)

        return D


    def makeDrawing2(self):
        "Generate a RLG drawing with some uncommented grid samples."

        D = Drawing(450, 650)

        d = 80
        s = 50

        for row in range(10):
            y = 530 - row*d
            if row == 0:
                for col in range(4):
                    x = 20 + col*d
                    g = Grid()
                    g.x = x
                    g.y = y
                    g.width = s
                    g.height = s
                    g.useRects = 0
                    g.useLines = 1
                    if col == 0:
                        pass
                    elif col == 1:
                        g.delta0 = 10
                    elif col == 2:
                        g.orientation = 'horizontal'
                    elif col == 3:
                        g.deltaSteps = [5, 10, 20, 30]
                    g.demo()
                    D.add(g)
            elif row == 1:
                for col in range(4):
                    x = 20 + col*d
                    g = Grid()
                    g.y = y
                    g.x = x
                    g.width = s
                    g.height = s
                    if col == 0:
                        pass
                    elif col == 1:
                        g.delta0 = 10
                    elif col == 2:
                        g.orientation = 'horizontal'
                    elif col == 3:
                        g.deltaSteps = [5, 10, 20, 30]
                        g.useRects = 1
                        g.useLines = 0
                    g.demo()
                    D.add(g)
            elif row == 2:
                for col in range(3):
                    x = 20 + col*d
                    g = Grid()
                    g.x = x
                    g.y = y
                    g.width = s
                    g.height = s
                    g.useLines = 1
                    g.useRects = 1
                    if col == 0:
                        pass
                    elif col == 1:
                        g.delta0 = 10
                    elif col == 2:
                        g.orientation = 'horizontal'
                    g.demo()
                    D.add(g)
            elif row == 3:
                for col in range(3):
                    x = 20 + col*d
                    sr = ShadedRect()
                    sr.x = x
                    sr.y = y
                    sr.width = s
                    sr.height = s
    ##                  sr.fillColorStart = colors.Color(0, 0, 0)
    ##                  sr.fillColorEnd = colors.Color(1, 1, 1)
                    sr.fillColorStart = colors.CMYKColor(0, 0, 0, 0)
                    sr.fillColorEnd = colors.CMYKColor(1, 1, 1, 1)
                    if col == 0:
                        sr.numShades = 5
                    elif col == 1:
                        sr.numShades = 2
                    elif col == 2:
                        sr.numShades = 1
                    sr.demo()
                    D.add(sr)
            elif row == 4:
                for col in range(3):
                    x = 20 + col*d
                    sr = ShadedRect()
                    sr.x = x
                    sr.y = y
                    sr.width = s
                    sr.height = s
    ##                  sr.fillColorStart = colors.red
    ##                  sr.fillColorEnd = colors.blue
                    sr.fillColorStart = colors.CMYKColor(1, 0, 0, 0)
                    sr.fillColorEnd = colors.CMYKColor(0, 0, 1, 0)
                    sr.orientation = 'horizontal'
                    if col == 0:
                        sr.numShades = 10
                    elif col == 1:
                        sr.numShades = 20
                    elif col == 2:
                        sr.numShades = 50
                    sr.demo()
                    D.add(sr)
            elif row == 5:
                for col in range(3):
                    x = 20 + col*d
                    sr = ShadedRect()
                    sr.x = x
                    sr.y = y
                    sr.width = s
                    sr.height = s
    ##                  sr.fillColorStart = colors.white
    ##                  sr.fillColorEnd = colors.green
                    sr.fillColorStart = colors.PCMYKColor(11.0,11.0,72.0,0.0,    spotName='PANTONE 458 CV',density=1.00)
                    sr.fillColorEnd = colors.PCMYKColor(100.0,65.0,0.0,30.0,    spotName='PANTONE 288 CV',density=1.00)
                    sr.orientation = 'horizontal'
                    if col == 0:
                        sr.numShades = 10
                    elif col == 1:
                        sr.numShades = 20
                        sr.orientation = 'vertical'
                    elif col == 2:
                        sr.numShades = 50
                    sr.demo()
                    D.add(sr)
            elif row == 6:
                for col in range(3):
                    x = 20 + col*d
                    sr = ShadedRect()
                    sr.x = x
                    sr.y = y+s
                    sr.width = s
                    sr.height = -s
                    sr.fillColorStart = colors.white
                    sr.fillColorEnd = colors.green
                    sr.orientation = 'horizontal'
                    if col == 0:
                        sr.numShades = 10
                    elif col == 1:
                        sr.numShades = 20
                        sr.orientation = 'vertical'
                    elif col == 2:
                        sr.numShades = 50
                    sr.demo()
                    D.add(sr)

        return D


    def test0(self):
        "Generate PDF and SVG documents of first sample drawing."

        d = self.makeDrawing0()
        renderPDF.drawToFile(d, outputfile('test_widgets_grids0.pdf'))
        renderSVG.drawToFile(d, outputfile('test_widgets_grids0.svg'))


    def test1(self):
        "Generate PDF and SVG documents of second sample drawing."

        d = self.makeDrawing1()
        renderPDF.drawToFile(d, outputfile('test_widgets_grids1.pdf'))
        renderSVG.drawToFile(d, outputfile('test_widgets_grids1.svg'))


    def test2(self):
        "Generate PDF and SVG documents of third sample drawing."

        d = self.makeDrawing2()
        renderPDF.drawToFile(d, outputfile('test_widgets_grids2.pdf'))
        renderSVG.drawToFile(d, outputfile('test_widgets_grids2.svg'))


def makeSuite():
    return makeSuiteForClasses(GridTestCase)


#noruntests
if __name__ == "__main__":
    unittest.TextTestRunner().run(makeSuite())
    printLocation()
