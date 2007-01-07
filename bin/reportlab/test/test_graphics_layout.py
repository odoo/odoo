#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/test/test_graphics_layout.py
"""
Tests for getBounds methods of various graphical widgets
"""

from reportlab.test import unittest
from reportlab.test.utils import makeSuiteForClasses, printLocation

from reportlab.graphics import shapes
##from reportlab.graphics.charts.barcharts import VerticalBarChart
##from reportlab.graphics.charts.linecharts import HorizontalLineChart
##from reportlab.graphics.charts.piecharts import Pie
##from reportlab.graphics.charts.legends import Legend

class BoundsTestCase(unittest.TestCase):
    def testLine(self):
        s = shapes.Line(10,20,30,40)
        assert s.getBounds() == (10,20,30,40)

    def testRect(self):
        s = shapes.Rect(10,20,30,40)  #width, height
        assert s.getBounds() == (10,20,40,60)

    def testCircle(self):
        s = shapes.Circle(100, 50, 10)
        assert s.getBounds() == (90,40,110,60)

    def testEllipse(self):
        s = shapes.Ellipse(100, 50, 10, 5)
        assert s.getBounds() == (90,45,110,55)

    def testWedge(self):
        s = shapes.Wedge(0,0,10,0,90)
        assert s.getBounds() == (0,0,10,10), 'expected (0,0,10,10) got %s' % repr(s.getBounds())

    def testPolygon(self):
        points = [0,0,10,30,25,15]
        s = shapes.Polygon(points)
        assert s.getBounds() == (0,0,25,30)

        s = shapes.PolyLine(points)
        assert s.getBounds() == (0,0,25,30)

    def testString(self):
        s = shapes.String(0,0,'Hello World', fontName='Courier',fontSize=10)
        assert s.getBounds() == (0, -2.0, 66.0, 10)

    def testGroup(self):
        g = shapes.Group()
        g.add(shapes.Rect(0,0,10,10))
        g.add(shapes.Rect(50,50,10,10))
        assert g.getBounds() == (0,0,60,60)

        g.translate(40,40)
        assert g.getBounds() == (40,40,100,100)

        g.translate(-40,-40)
        g.rotate(90)
        #approx bounds needed, trig functions create an error of 3e-15
        assert map(int, g.getBounds()) == [-60,0,0,60]

    def testWidget(self):
        from reportlab.graphics.charts.barcharts import VerticalBarChart
        vbc = VerticalBarChart()
        vbc.x = 50
        vbc.y = 50
        from reportlab.graphics.widgetbase import Sizer
        siz = Sizer()
        siz.add(vbc, 'vbc')
        assert siz.getBounds()[0:2] <> (0,0)


def makeSuite():
    return makeSuiteForClasses(BoundsTestCase)


#noruntests
if __name__ == "__main__":
    unittest.TextTestRunner().run(makeSuite())
    printLocation()
