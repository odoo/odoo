#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/test/test_pdfbase_pdfutils.py
"""Tests for utility functions in reportlab.pdfbase.pdfutils.
"""


import os

from reportlab.test import unittest
from reportlab.test.utils import makeSuiteForClasses, printLocation

from reportlab.pdfbase.pdfutils import _AsciiHexEncode, _AsciiHexDecode
from reportlab.pdfbase.pdfutils import _AsciiBase85Encode, _AsciiBase85Decode


class PdfEncodingTestCase(unittest.TestCase):
    "Test various encodings used in PDF files."

    def testAsciiHex(self):
        "Test if the obvious test for whether ASCII-Hex encoding works."

        plainText = 'What is the average velocity of a sparrow?'
        encoded = _AsciiHexEncode(plainText)
        decoded = _AsciiHexDecode(encoded)

        msg = "Round-trip AsciiHex encoding failed."
        assert decoded == plainText, msg


    def testAsciiBase85(self):
        "Test if the obvious test for whether ASCII-Base85 encoding works."

        msg = "Round-trip AsciiBase85 encoding failed."
        plain = 'What is the average velocity of a sparrow?'

        #the remainder block can be absent or from 1 to 4 bytes
        for i in xrange(55):
            encoded = _AsciiBase85Encode(plain)
            decoded = _AsciiBase85Decode(encoded)
            assert decoded == plain, msg
            plain = plain + chr(i)


def makeSuite():
    return makeSuiteForClasses(PdfEncodingTestCase)


#noruntests
if __name__ == "__main__":
    unittest.TextTestRunner().run(makeSuite())
    printLocation()
