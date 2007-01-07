import os

from reportlab.test import unittest
from reportlab.test.utils import makeSuiteForClasses, outputfile, printLocation

from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.test.test_pdfbase_pdfmetrics import makeWidthTestForAllGlyphs


class EmbeddingTestCase(unittest.TestCase):
    "Make documents with embedded fonts"

    def test0(self):
        """Make documents with embedded fonts.

        Just vam Rossum has kindly donated a font which we may use
        for testing purposes.  You need to contact him at just@letterror.com
        if you want to use it for real."""

        #LettError fonts should always be there.  The others are voluntary.

        ok = 1

        c = Canvas(outputfile('test_pdfbase_fontembed.pdf'))
        c.setPageCompression(0)
        c.setFont('Helvetica', 12)
        c.drawString(100, 700, 'This is Helvetica.  The text below should be different fonts...')

        if os.path.isfile('GDB_____.AFM') and os.path.isfile('GDB_____.PFB'):
            # a normal text font
            garaFace = pdfmetrics.EmbeddedType1Face('GDB_____.AFM','GDB_____.PFB')
            faceName = 'AGaramond-Bold'  # pulled from AFM file
            pdfmetrics.registerTypeFace(garaFace)

            garaFont = pdfmetrics.Font('MyGaramondBold', faceName, 'WinAnsiEncoding')
            pdfmetrics.registerFont(garaFont)

            c.setFont('AGaramond-Bold', 12)
            c.drawString(100, 650, 'This should be in AGaramond-Bold')

        if os.path.isfile('CR______.AFM') and os.path.isfile('CR______.PFB'):

            # one with a custom encoding
            cartaFace = pdfmetrics.EmbeddedType1Face('CR______.AFM','CR______.PFB')
            faceName = 'Carta'  # pulled from AFM file
            pdfmetrics.registerTypeFace(cartaFace)

            cartaFont = pdfmetrics.Font('Carta', 'Carta', 'CartaEncoding')
            pdfmetrics.registerFont(cartaFont)

            text = 'This should be in Carta, a map symbol font:'
            c.setFont('Helvetica', 12)
            c.drawString(100, 600, text)
            w = c.stringWidth(text, 'Helvetica', 12)

            c.setFont('Carta', 12)
            c.drawString(100+w, 600, ' Hello World')

        # LettError sample - creates on demand, we hope
        y = 550
##        justFace = pdfmetrics.EmbeddedType1Face('LeERC___.AFM','LeERC___.PFB')
##
##        faceName = 'LettErrorRobot-Chrome'  # pulled from AFM file
##        pdfmetrics.registerTypeFace(justFace)
##
##        justFont = pdfmetrics.Font('LettErrorRobot-Chrome', faceName, 'WinAnsiEncoding')
##        pdfmetrics.registerFont(justFont)

        c.setFont('LettErrorRobot-Chrome', 12)
        c.drawString(100, y, 'This should be in LettErrorRobot-Chrome')

        def testNamedFont(canv, fontName):
            canv.showPage()
            makeWidthTestForAllGlyphs(canv, fontName, outlining=0)

        testNamedFont(c, 'LettErrorRobot-Chrome')

        c.save()



def makeSuite():
    return makeSuiteForClasses(EmbeddingTestCase)


#noruntests
if __name__ == "__main__":
    unittest.TextTestRunner().run(makeSuite())
    printLocation()
