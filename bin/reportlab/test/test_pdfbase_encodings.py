from reportlab.test import unittest
from reportlab.test.utils import makeSuiteForClasses, outputfile, printLocation

from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfutils

from reportlab.platypus.paragraph import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.graphics.shapes import Drawing, String, Ellipse
import re
import codecs
textPat = re.compile(r'\([^(]*\)')

#test sentences
testCp1252 = 'copyright %s trademark %s registered %s ReportLab! Ol%s!' % (chr(169), chr(153),chr(174), chr(0xe9))
testUni = unicode(testCp1252, 'cp1252')
testUTF8 = testUni.encode('utf-8')
# expected result is octal-escaped text in the PDF
expectedCp1252 = pdfutils._escape(testCp1252)

def extractText(pdfOps):
    """Utility to rip out the PDF text within a block of PDF operators.

    PDF will show a string draw as something like "(Hello World) Tj"
    i.e. text is in curved brackets. Crude and dirty, probably fails
    on escaped brackets.
    """
    found = textPat.findall(pdfOps)
    #chop off '(' and ')'
    return map(lambda x:x[1:-1], found)

def subsetToUnicode(ttf, subsetCodeStr):
    """Return unicode string represented by given subsetCode string
    as found when TrueType font rendered to PDF, ttf must be the font
    object that was used."""
    # This relies on TTFont internals and uses the first document
    # and subset it finds
    subset = ttf.state.values()[0].subsets[0]
    chrs = []
    for codeStr in subsetCodeStr.split('\\'):
        if codeStr:
            chrs.append(unichr(subset[int(codeStr[1:], 8)]))
    return u''.join(chrs)

class TextEncodingTestCase(unittest.TestCase):
    """Tests of expected Unicode and encoding behaviour
    """
    def setUp(self):
        self.luxi = TTFont("Luxi", "luxiserif.ttf")
        pdfmetrics.registerFont(self.luxi)
        self.styNormal = ParagraphStyle(name='Helvetica',  fontName='Helvetica-Oblique')
        self.styTrueType = ParagraphStyle(name='TrueType',  fontName='luxi')

    def testStringWidth(self):
        msg = 'Hello World'
        assert abs(pdfmetrics.stringWidth(msg, 'Courier', 10) - 66.0) < 0.01
        assert abs(pdfmetrics.stringWidth(msg, 'Helvetica', 10) - 51.67) < 0.01
        assert abs(pdfmetrics.stringWidth(msg, 'Times-Roman', 10) - 50.27) < 0.01
        assert abs(pdfmetrics.stringWidth(msg, 'Luxi', 10) - 50.22) < 0.01

        uniMsg1 = u"Hello World"
        assert abs(pdfmetrics.stringWidth(uniMsg1, 'Courier', 10) - 66.0) < 0.01
        assert abs(pdfmetrics.stringWidth(uniMsg1, 'Helvetica', 10) - 51.67) < 0.01
        assert abs(pdfmetrics.stringWidth(uniMsg1, 'Times-Roman', 10) - 50.27) < 0.01
        assert abs(pdfmetrics.stringWidth(uniMsg1, 'Luxi', 10) - 50.22) < 0.01


        # Courier are all 600 ems wide.  So if one 'measures as utf8' one will
        # get a wrong width as extra characters are seen
        assert len(testCp1252) == 52
        assert abs(pdfmetrics.stringWidth(testCp1252, 'Courier', 10, 'cp1252') - 312.0) < 0.01
        # the test string has 5 more bytes and so "measures too long" if passed to
        # a single-byte font which treats it as a single-byte string.
        assert len(testUTF8)==57
        assert abs(pdfmetrics.stringWidth(testUTF8, 'Courier', 10) - 312.0) < 0.01

        assert len(testUni)==52
        assert abs(pdfmetrics.stringWidth(testUni, 'Courier', 10) - 312.0) < 0.01


        # now try a TrueType font.  Should be able to accept Unicode or UTF8
        assert abs(pdfmetrics.stringWidth(testUTF8, 'Luxi', 10) - 224.44) < 0.01
        assert abs(pdfmetrics.stringWidth(testUni, 'Luxi', 10) - 224.44) < 0.01

    def testUtf8Canvas(self):
        """Verify canvas declared as utf8 autoconverts.

        This assumes utf8 input. It converts to the encoding of the
        underlying font, so both text lines APPEAR the same."""


        c = Canvas(outputfile('test_pdfbase_encodings_utf8.pdf'))

        c.drawString(100,700, testUTF8)

        # Set a font with UTF8 encoding
        c.setFont('Luxi', 12)

        # This should pass the UTF8 through unchanged
        c.drawString(100,600, testUTF8)
        # and this should convert from Unicode to UTF8
        c.drawString(100,500, testUni)


        # now add a paragraph in Latin-1 in the latin-1 style
        p = Paragraph(testUTF8, style=self.styNormal, encoding="utf-8")
        w, h = p.wrap(150, 100)
        p.drawOn(c, 100, 400)  #3
        c.rect(100,300,w,h)

        # now add a paragraph in UTF-8 in the UTF-8 style
        p2 = Paragraph(testUTF8, style=self.styTrueType, encoding="utf-8")
        w, h = p2.wrap(150, 100)
        p2.drawOn(c, 300, 400) #4
        c.rect(100,300,w,h)

        # now add a paragraph in Unicode in the latin-1 style
        p3 = Paragraph(testUni, style=self.styNormal)
        w, h = p3.wrap(150, 100)
        p3.drawOn(c, 100, 300)
        c.rect(100,300,w,h)

        # now add a paragraph in Unicode in the UTF-8 style
        p4 = Paragraph(testUni, style=self.styTrueType)
        p4.wrap(150, 100)
        p4.drawOn(c, 300, 300)
        c.rect(300,300,w,h)

        # now a graphic
        d1 = Drawing(400,50)
        d1.add(Ellipse(200,25,200,12.5, fillColor=None))
        d1.add(String(200,25,testUTF8, textAnchor='middle', encoding='utf-8'))
        d1.drawOn(c, 100, 150)

        # now a graphic in utf8
        d2 = Drawing(400,50)
        d2.add(Ellipse(200,25,200,12.5, fillColor=None))
        d2.add(String(200,25,testUTF8, fontName='Luxi', textAnchor='middle', encoding='utf-8'))
        d2.drawOn(c, 100, 100)

        # now a graphic in Unicode with T1 font
        d3 = Drawing(400,50)
        d3.add(Ellipse(200,25,200,12.5, fillColor=None))
        d3.add(String(200,25,testUni, textAnchor='middle'))
        d3.drawOn(c, 100, 50)

        # now a graphic in Unicode with TT font
        d4 = Drawing(400,50)
        d4.add(Ellipse(200,25,200,12.5, fillColor=None))
        d4.add(String(200,25,testUni, fontName='Luxi', textAnchor='middle'))
        d4.drawOn(c, 100, 0)

        extracted = extractText(c.getCurrentPageContent())
        self.assertEquals(extracted[0], expectedCp1252)
        self.assertEquals(extracted[1], extracted[2])
        #self.assertEquals(subsetToUnicode(self.luxi, extracted[1]), testUni)
        c.save()

class FontEncodingTestCase(unittest.TestCase):
    """Make documents with custom encodings of Type 1 built-in fonts.

    Nothing really to do with character encodings; this is about hacking the font itself"""

    def test0(self):
        "Make custom encodings of standard fonts"

        # make a custom encoded font.
        c = Canvas(outputfile('test_pdfbase_encodings.pdf'))
        c.setPageCompression(0)
        c.setFont('Helvetica', 12)
        c.drawString(100, 700, 'The text below should be in a custom encoding in which all vowels become "z"')

        # invent a new language where vowels are replaced with letter 'z'
        zenc = pdfmetrics.Encoding('EncodingWithoutVowels', 'WinAnsiEncoding')
        for ch in 'aeiou':
            zenc[ord(ch)] = 'z'
        for ch in 'AEIOU':
            zenc[ord(ch)] = 'Z'
        pdfmetrics.registerEncoding(zenc)

        # now we can make a font based on this encoding
        # AR hack/workaround: the name of the encoding must be a Python codec!
        f = pdfmetrics.Font('FontWithoutVowels', 'Helvetica-Oblique', 'EncodingWithoutVowels')
        pdfmetrics.registerFont(f)

        c.setFont('FontWithoutVowels', 12)
        c.drawString(125, 675, "The magic word is squamish ossifrage")

        # now demonstrate adding a Euro to MacRoman, which lacks one
        c.setFont('Helvetica', 12)
        c.drawString(100, 650, "MacRoman encoding lacks a Euro.  We'll make a Mac font with the Euro at #219:")

        # WinAnsi Helvetica
        pdfmetrics.registerFont(pdfmetrics.Font('Helvetica-WinAnsi', 'Helvetica-Oblique', 'WinAnsiEncoding'))
        c.setFont('Helvetica-WinAnsi', 12)
        c.drawString(125, 625, 'WinAnsi with Euro: character 128 = "\200"')

        pdfmetrics.registerFont(pdfmetrics.Font('MacHelvNoEuro', 'Helvetica-Oblique', 'MacRomanEncoding'))
        c.setFont('MacHelvNoEuro', 12)
        c.drawString(125, 600, 'Standard MacRoman, no Euro: Character 219 = "\333"') # oct(219)=0333

        # now make our hacked encoding
        euroMac = pdfmetrics.Encoding('MacWithEuro', 'MacRomanEncoding')
        euroMac[219] = 'Euro'
        pdfmetrics.registerEncoding(euroMac)

        pdfmetrics.registerFont(pdfmetrics.Font('MacHelvWithEuro', 'Helvetica-Oblique', 'MacWithEuro'))

        c.setFont('MacHelvWithEuro', 12)
        c.drawString(125, 575, 'Hacked MacRoman with Euro: Character 219 = "\333"') # oct(219)=0333

        # now test width setting with and without _rl_accel - harder
        # make an encoding where 'm' becomes 'i'
        c.setFont('Helvetica', 12)
        c.drawString(100, 500, "Recode 'm' to 'i' and check we can measure widths. Boxes should surround letters.")
        sample = 'Mmmmm. ' * 6 + 'Mmmm'

        c.setFont('Helvetica-Oblique',12)
        c.drawString(125, 475, sample)
        w = c.stringWidth(sample, 'Helvetica-Oblique', 12)
        c.rect(125, 475, w, 12)

        narrowEnc = pdfmetrics.Encoding('m-to-i')
        narrowEnc[ord('m')] = 'i'
        narrowEnc[ord('M')] = 'I'
        pdfmetrics.registerEncoding(narrowEnc)

        pdfmetrics.registerFont(pdfmetrics.Font('narrow', 'Helvetica-Oblique', 'm-to-i'))
        c.setFont('narrow', 12)
        c.drawString(125, 450, sample)
        w = c.stringWidth(sample, 'narrow', 12)
        c.rect(125, 450, w, 12)

        c.setFont('Helvetica', 12)
        c.drawString(100, 400, "Symbol & Dingbats fonts - check we still get valid PDF in StandardEncoding")
        c.setFont('Symbol', 12)
        c.drawString(100, 375, 'abcdefghijklmn')
        c.setFont('ZapfDingbats', 12)
        c.drawString(300, 375, 'abcdefghijklmn')

        c.save()

def makeSuite():
    return makeSuiteForClasses(
        TextEncodingTestCase,

        #FontEncodingTestCase - nobbled for now due to old stuff which needs removing.
        )

#noruntests
if __name__ == "__main__":
    unittest.TextTestRunner().run(makeSuite())
    printLocation()
