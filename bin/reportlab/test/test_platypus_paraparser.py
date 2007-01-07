#!/bin/env python
#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history TBC
#$Header$
__version__=''' $Id'''
__doc__="""Tests of intra-paragraph parsing behaviour in Platypus."""

from types import TupleType, ListType, StringType, UnicodeType
from pprint import pprint as pp

from reportlab.test import unittest
from reportlab.test.utils import makeSuiteForClasses, outputfile
from reportlab.platypus import cleanBlockQuotedText
from reportlab.platypus.paraparser import ParaParser, ParaFrag
from reportlab.lib.colors import black

class ParaParserTestCase(unittest.TestCase):
    """Tests of data structures created by paragraph parser.  Esp. ability
    to accept unicode and preserve it"""

    def setUp(self):
        style=ParaFrag()
        style.fontName='Times-Roman'
        style.fontSize = 12
        style.textColor = black
        style.bulletFontName = black
        style.bulletFontName='Times-Roman'
        style.bulletFontSize=12
        self.style = style        

    def testPlain(self):
        txt = "Hello World"
        stuff = ParaParser().parse(txt, self.style)
        assert type(stuff) is TupleType
        assert len(stuff) == 3
        assert  stuff[1][0].text == 'Hello World'
        
    def testBold(self):
        txt = "Hello <b>Bold</b> World"
        fragList = ParaParser().parse(txt, self.style)[1]
        self.assertEquals(map(lambda x:x.text, fragList), ['Hello ','Bold',' World'])
        self.assertEquals(fragList[1].fontName, 'Times-Bold')

    def testEntity(self):
        "Numeric entities should be unescaped by parser"
        txt = "Hello &#169; copyright"
        fragList = ParaParser().parse(txt, self.style)[1]
        self.assertEquals(map(lambda x:x.text, fragList), ['Hello ','\xc2\xa9',' copyright'])

    def testEscaped(self):
        "Escaped high-bit stuff should go straight through"
        txt = "Hello \xc2\xa9 copyright"
        fragList = ParaParser().parse(txt, self.style)[1]
        assert fragList[0].text == txt

    def testPlainUnicode(self):
        "See if simple unicode goes through"
        txt = u"Hello World"
        stuff = ParaParser().parse(txt, self.style)
        assert type(stuff) is TupleType
        assert len(stuff) == 3
        assert  stuff[1][0].text == u'Hello World'

    def testBoldUnicode(self):
        txt = u"Hello <b>Bold</b> World"
        fragList = ParaParser().parse(txt, self.style)[1]
        self.assertEquals(map(lambda x:x.text, fragList), [u'Hello ',u'Bold',u' World'])
        self.assertEquals(fragList[1].fontName, 'Times-Bold')

    def testEntityUnicode(self):
        "Numeric entities should be unescaped by parser"
        txt = u"Hello &#169; copyright"
        fragList = ParaParser().parse(txt, self.style)[1]
        self.assertEquals(map(lambda x:x.text, fragList), [u'Hello ',u'\xc2\xa9',u' copyright'])

    def testEscapedUnicode(self):
        "Escaped high-bit stuff should go straight through"
        txt = u"Hello \xa9 copyright"
        fragList = ParaParser().parse(txt, self.style)[1]
        assert fragList[0].text == txt



def makeSuite():
    return makeSuiteForClasses(ParaParserTestCase)


#noruntests
if __name__ == "__main__":
    unittest.TextTestRunner().run(makeSuite())
