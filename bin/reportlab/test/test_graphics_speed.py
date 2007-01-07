#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/test/test_graphics_speed.py
"""
This does a test drawing with lots of things in it, running
with and without attribute checking.
"""

__version__ = ''' $Id $ '''


import os, sys, time, profile

import reportlab.rl_config
from reportlab.test import unittest
from reportlab.test.utils import makeSuiteForClasses, outputfile, printLocation
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable
from reportlab.graphics.shapes import *
from reportlab.graphics.charts.piecharts import Pie


class GraphicsSpeedTestCase(unittest.TestCase):
    "Test speed of the graphics rendering process."

    def test0(self, isFast=0):
        """Hello World, on a rectangular background.

        The rectangle's fillColor is yellow.
        The string's fillColor is red.
        """
        reportlab.rl_config.shapeChecking = not isFast

        pdfPath = outputfile('test_graphics_speed_fast.pdf')
        c = Canvas(pdfPath)
        t0 = time.time()

        d = Drawing(400, 200)
        num = 100
        for i in range(num):
            pc = Pie()
            pc.x = 150
            pc.y = 50
            pc.data = [10,20,30,40,50,60]
            pc.labels = ['a','b','c','d','e','f']
            pc.slices.strokeWidth=0.5
            pc.slices[3].popout = 20
            pc.slices[3].strokeWidth = 2
            pc.slices[3].strokeDashArray = [2,2]
            pc.slices[3].labelRadius = 1.75
            pc.slices[3].fontColor = colors.red
            d.add(pc)
        d.drawOn(c, 80, 500)

        t1 = time.time()

        result = 'drew %d pie charts in %0.4f' % (num, t1 - t0)
        open(outputfile('test_graphics_speed_test%s.log' % (isFast+1)), 'w').write(result)


    def test1(self, isFast=1):
        "Same as test1(), but with shape checking turned on."

        self.test0(isFast)


    def test2(self):
        "This is a profiled version of test1()."

        fileName = outputfile('test_graphics_speed_profile.log')
        # This runs ok, when only this test script is executed,
        # but fails, when imported from runAll.py...
##        profile.run("t = GraphicsSpeedTestCase('test2')", fileName)


def makeSuite():
    return makeSuiteForClasses(GraphicsSpeedTestCase)


#noruntests
if __name__ == "__main__":
    unittest.TextTestRunner().run(makeSuite())
    printLocation()
