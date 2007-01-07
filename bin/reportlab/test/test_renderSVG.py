#!/usr/bin/env python

import sys, string
from xml.dom import minidom
from xml.sax._exceptions import SAXReaderNotAvailable

from reportlab.test import unittest
from reportlab.test.utils import makeSuiteForClasses, outputfile, printLocation

from reportlab.graphics.shapes import *
from reportlab.graphics import renderSVG




def warnIgnoredRestofTest():
    "Raise a warning (if possible) about a not fully completed test."

    version = sys.version_info[:2]
    msg = "XML parser not found - consider installing expat! Rest of test(s) ignored!"
    if version >= (2, 1):
        import warnings
        warnings.warn(msg)
    else:
        # should better also be printed only once...
        print msg




# Check if we have a default XML parser available or not.

try:
    import xml
    from xml.sax import make_parser
    p = xml.sax.make_parser()
    HAVE_XML_PARSER = 1
except SAXReaderNotAvailable:
    HAVE_XML_PARSER = 0




def load(path):
    "Helper function to read the generated SVG again."

    doc = minidom.parse(path)
    doc.normalize()
    return doc.documentElement




class RenderSvgSimpleTestCase(unittest.TestCase):
    "Testing renderSVG module."

    def test0(self):
        "Test two strings in drawing."

        path = outputfile("test_renderSVG_simple_test0.svg")

        d = Drawing(200, 100)
        d.add(String(0, 0, "foo"))
        d.add(String(100, 0, "bar"))
        renderSVG.drawToFile(d, path)

        if not HAVE_XML_PARSER:
            warnIgnoredRestofTest()
            return

        svg = load(path)
        fg = svg.getElementsByTagName('g')[0]           # flipping group
        dg = fg.getElementsByTagName('g')[0]            # diagram group
        textChildren = dg.getElementsByTagName('text')  # text nodes
        t0 = string.strip(textChildren[0].childNodes[0].nodeValue)
        t1 = string.strip(textChildren[1].childNodes[0].nodeValue)
        assert t0 == 'foo'
        assert t1 == 'bar'


    def test1(self):
        "Test two strings in group in drawing."

        path = outputfile("test_renderSVG_simple_test1.svg")

        d = Drawing(200, 100)
        g = Group()
        g.add(String(0, 0, "foo"))
        g.add(String(100, 0, "bar"))
        d.add(g)
        renderSVG.drawToFile(d, path)

        if not HAVE_XML_PARSER:
            warnIgnoredRestofTest()
            return

        svg = load(path)
        fg = svg.getElementsByTagName('g')[0]           # flipping group
        dg = fg.getElementsByTagName('g')[0]            # diagram group
        g = dg.getElementsByTagName('g')[0]             # custom group
        textChildren = g.getElementsByTagName('text')   # text nodes
        t0 = string.strip(textChildren[0].childNodes[0].nodeValue)
        t1 = string.strip(textChildren[1].childNodes[0].nodeValue)

        assert t0 == 'foo'
        assert t1 == 'bar'


    def test2(self):
        "Test two strings in transformed group in drawing."

        path = outputfile("test_renderSVG_simple_test2.svg")

        d = Drawing(200, 100)
        g = Group()
        g.add(String(0, 0, "foo"))
        g.add(String(100, 0, "bar"))
        g.scale(1.5, 1.2)
        g.translate(50, 0)
        d.add(g)
        renderSVG.drawToFile(d, path)

        if not HAVE_XML_PARSER:
            warnIgnoredRestofTest()
            return

        svg = load(path)
        fg = svg.getElementsByTagName('g')[0]           # flipping group
        dg = fg.getElementsByTagName('g')[0]            # diagram group
        g = dg.getElementsByTagName('g')[0]             # custom group
        textChildren = g.getElementsByTagName('text')   # text nodes
        t0 = string.strip(textChildren[0].childNodes[0].nodeValue)
        t1 = string.strip(textChildren[1].childNodes[0].nodeValue)

        assert t0 == 'foo'
        assert t1 == 'bar'




class RenderSvgAxesTestCase(unittest.TestCase):
    "Testing renderSVG module on Axes widgets."

    def test0(self):
        "Test two strings in drawing."

        path = outputfile("axestest0.svg")
        from reportlab.graphics.charts.axes import XCategoryAxis

        d = XCategoryAxis().demo()
        renderSVG.drawToFile(d, path)




def makeSuite():
    return makeSuiteForClasses(RenderSvgSimpleTestCase, RenderSvgAxesTestCase)




#noruntests
if __name__ == "__main__":
    unittest.TextTestRunner().run(makeSuite())
    printLocation()
