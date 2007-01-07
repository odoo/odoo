#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
"""
Tests for RLG Image shapes.
"""

import os

from reportlab.test import unittest
from reportlab.test.utils import makeSuiteForClasses, outputfile, printLocation

from reportlab.graphics.shapes import Image, Drawing
from reportlab.graphics import renderPDF
from reportlab.lib.pagesizes import A4


IMAGES = []
IMAGENAME = 'cs_logo.gif'
IMAGENAME = 'pythonpowered.gif'


class ImageTestCase(unittest.TestCase):
    "Test RLG Image shape."

    def __del__(self):
        if IMAGES[-1] != None:
            return
        else:
            del IMAGES[-1]

        d = Drawing(A4[0], A4[1])
        for img in IMAGES:
            d.add(img)
        outPath = outputfile("test_graphics_images.pdf")
        renderPDF.drawToFile(d, outPath) #, '')
        assert os.path.exists(outPath) == 1


    def test0(self):
        "Test convert a bitmap file as Image shape into a tmp. PDF file."

        d = Drawing(110, 44)
        inPath = IMAGENAME
        img = Image(0, 0, 110, 44, inPath)
        d.add(img)
        IMAGES.append(img)


    def test1(self):
        "Test Image shape, adding it to a PDF page."

        inPath = IMAGENAME
        img = Image(0, 0, 110, 44, inPath)
        IMAGES.append(img)


    def test2(self):
        "Test scaled Image shape adding it to a PDF page."

        inPath = IMAGENAME
        img = Image(0, 0, 110, 44, inPath)
        d = Drawing(110, 44)
        d.add(img)
        d.translate(120, 0)
        d.scale(2, 2)
        IMAGES.append(d)


    def test3(self):
        "Test rotated Image shape adding it to a PDF page."

        inPath = IMAGENAME
        img = Image(0, 0, 110, 44, inPath)
        d = Drawing(110, 44)
        d.add(img)
        d.translate(420, 0)
        d.scale(2, 2)
        d.rotate(45)
        IMAGES.append(d)

        IMAGES.append(None) # used to indicate last test


def makeSuite():
    return makeSuiteForClasses(ImageTestCase)


#noruntests
if __name__ == "__main__":
    unittest.TextTestRunner().run(makeSuite())
    printLocation()
