#!/bin/env python
#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/test/test_pdfbase_postscript.py
__version__=''' $Id'''
__doc__="""Tests Postscript XObjects.

Nothing visiblke in Acrobat, but the resulting files
contain graphics and tray commands if exported to
a Postscript device in Acrobat 4.0"""

from reportlab.test import unittest
from reportlab.test.utils import makeSuiteForClasses, outputfile, printLocation
from reportlab.pdfgen.canvas import Canvas


class PostScriptTestCase(unittest.TestCase):
    "Simplest test that makes PDF"

    def testVisible(self):
        "Makes a document with extra text - should export and distill"
        c = Canvas(outputfile('test_pdfbase_postscript_visible.pdf'))
        c.setPageCompression(0)

        c.setFont('Helvetica-Bold', 18)
        c.drawString(100,700, 'Hello World. This is page 1 of a 2 page document.')
        c.showPage()

        c.setFont('Helvetica-Bold', 16)
        c.drawString(100,700, 'Page 2. This has some postscript drawing code.')
        c.drawString(100,680, 'If you print it using a PS device and Acrobat 4/5,')
        c.drawString(100,660, 'or export to Postscript, you should see the word')
        c.drawString(100,640, '"Hello PostScript" below.  In ordinary Acrobat Reader')
        c.drawString(100,620, 'we expect to see nothing.')
        c.addPostScriptCommand('/Helvetica findfont 48 scalefont setfont 100 400 moveto (Hello PostScript) show')


        c.drawString(100,500, 'This document also inserts two postscript')
        c.drawString(100,480, ' comments at beginning and endof the stream;')
        c.drawString(100,460, 'search files for "%PS_BEFORE" and "%PS_AFTER".')
        c.addPostScriptCommand('%PS_BEFORE', position=0)
        c.addPostScriptCommand('%PS_AFTER', position=2)

        c.save()

    def testTray(self):
        "Makes a document with tray command - only works on printers supporting it"
        c = Canvas(outputfile('test_pdfbase_postscript_tray.pdf'))
        c.setPageCompression(0)

        c.setFont('Helvetica-Bold', 18)
        c.drawString(100,700, 'Hello World. This is page 1 of a 2 page document.')
        c.drawString(100,680, 'This also has a tray command ("5 setpapertray").')
        c.addPostScriptCommand('5 setpapertray')
        c.showPage()

        c.setFont('Helvetica-Bold', 16)
        c.drawString(100,700, 'Page 2. This should come from a different tray.')
        c.drawString(100,680, 'Also, if you print it using a PS device and Acrobat 4/5,')
        c.drawString(100,660, 'or export to Postscript, you should see the word')
        c.drawString(100,640, '"Hello PostScript" below.  In ordinary Acrobat Reader')
        c.drawString(100,620, 'we expect to see nothing.')
        c.addPostScriptCommand('/Helvetica findfont 48 scalefont setfont 100 400 moveto (Hello PostScript) show')


        c.save()

def makeSuite():
    return makeSuiteForClasses(PostScriptTestCase)


#noruntests
if __name__ == "__main__":
    unittest.TextTestRunner().run(makeSuite())
    print 'saved '+outputfile('test_pdfgen_postscript_visible.pdf')
    print 'saved '+outputfile('test_pdfgen_postscript_tray.pdf')
    printLocation()
