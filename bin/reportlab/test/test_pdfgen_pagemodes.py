#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/test/test_pdfgen_pagemodes.py
# full screen test

"""Tests for PDF page modes support in reportlab.pdfgen.
"""


import os

from reportlab.test import unittest
from reportlab.test.utils import makeSuiteForClasses, outputfile, printLocation

from reportlab.pdfgen.canvas import Canvas


def fileDoesExist(path):
    "Check if a file does exist."
    return os.path.exists(path)


class PdfPageModeTestCase(unittest.TestCase):
    "Testing different page modes for opening a file in Acrobat Reader."

    baseFileName = 'test_pagemodes_'

    def _doTest(self, filename, mode, desc):
        "A generic method called by all test real methods."

        filename = outputfile(self.baseFileName + filename)
        c = Canvas(filename)

        # Handle different modes.
        if mode == 'FullScreen':
            c.showFullScreen0()
        elif mode == 'Outline':
            c.bookmarkPage('page1')
            c.addOutlineEntry('Token Outline Entry', 'page1')
            c.showOutline()
        elif mode == 'UseNone':
            pass

        c.setFont('Helvetica', 20)
        c.drawString(100, 700, desc)
        c.save()

        assert fileDoesExist(filename)


    def test0(self):
        "This should open in full screen mode."
        self._doTest('FullScreen.pdf', 'FullScreen', self.test0.__doc__)

    def test1(self):
        "This should open with outline visible."
        self._doTest('Outline.pdf', 'Outline', self.test1.__doc__)

    def test2(self):
        "This should open in the user's default mode."
        self._doTest('UseNone.pdf', 'UseNone', self.test2.__doc__)

def makeSuite():
    return makeSuiteForClasses(PdfPageModeTestCase)


#noruntests
if __name__ == "__main__":
    unittest.TextTestRunner().run(makeSuite())
    printLocation()
