
import string, os

from reportlab.test import unittest
from reportlab.test.utils import makeSuiteForClasses, outputfile, printLocation

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib import colors
from reportlab.lib.codecharts import KutenRowCodeChart, hBoxText
from reportlab.pdfbase.cidfonts import UnicodeCIDFont, findCMapFile
global VERBOSE
VERBOSE = 0



class KoreanFontTests(unittest.TestCase):

    def test0(self):

        # if they do not have the font files or encoding, go away quietly
##        try:
##            from reportlab.pdfbase.cidfonts import CIDFont, findCMapFile
##            findCMapFile('KSCms-UHC-H')
##        except:
##            #don't have the font pack.  return silently
##            print 'CMap not found'
##            return

        localFontName = 'HYSMyeongJo-Medium'
        c = Canvas(outputfile('test_multibyte_kor.pdf'))
        c.setFont('Helvetica', 30)
        c.drawString(100,700, 'Korean Font Support')
        c.setFont('Helvetica', 10)
        c.drawString(100,680, 'Short sample in Unicode; grey area should outline the text with correct width.')


        hBoxText(u'\ub300\ud55c\ubbfc\uad6d = Korea',
                 c, 100, 660, 'HYSMyeongJo-Medium')
        hBoxText(u'\uc548\uc131\uae30 = AHN Sung-Gi (Actor)',
                 c, 100, 640, 'HYGothic-Medium')

##        pdfmetrics.registerFont(UnicodeCIDFont('HYSMyeongJo-Medium'))
##        c.setFont('Helvetica', 10)
##        c.drawString(100,610, "Longer sample From Adobe's Acrobat web page in EUC:")
##
##        sample = """\xbf\xad \xbc\xf6 \xbe\xf8\xb4\xc2 \xb9\xae\xbc\xad\xb4\xc2 \xbe\xc6\xb9\xab\xb7\xb1 \xbc\xd2\xbf\xeb\xc0\xcc \xbe\xf8\xbd\xc0\xb4\xcf\xb4\xd9. \xbb\xe7\xbe\xf7 \xb0\xe8\xc8\xb9\xbc\xad, \xbd\xba\xc7\xc1\xb7\xb9\xb5\xe5\xbd\xc3\xc6\xae, \xb1\xd7\xb7\xa1\xc7\xc8\xc0\xcc \xb8\xb9\xc0\xcc \xc6\xf7\xc7\xd4\xb5\xc8 \xbc\xd2\xc3\xa5\xc0\xda \xb6\xc7\xb4\xc2 \xc0\xa5
##\xbb\xe7\xc0\xcc\xc6\xae\xb8\xa6 \xc0\xdb\xbc\xba\xc7\xcf\xb4\xc2 \xb0\xe6\xbf\xec Adobe\xa2\xe7 Acrobat\xa2\xe7 5.0 \xbc\xd2\xc7\xc1\xc6\xae\xbf\xfe\xbe\xee\xb8\xa6 \xbb\xe7\xbf\xeb\xc7\xd8\xbc\xad \xc7\xd8\xb4\xe7 \xb9\xae\xbc\xad\xb8\xa6 Adobe
##Portable Document Format (PDF) \xc6\xc4\xc0\xcf\xb7\xce \xba\xaf\xc8\xaf\xc7\xd2 \xbc\xf6 \xc0\xd6\xbd\xc0\xb4\xcf\xb4\xd9. \xb4\xa9\xb1\xb8\xb3\xaa \xb1\xa4\xb9\xfc\xc0\xa7\xc7\xd1 \xc1\xbe\xb7\xf9\xc0\xc7
##\xc7\xcf\xb5\xe5\xbf\xfe\xbe\xee\xbf\xcd \xbc\xd2\xc7\xc1\xc6\xae\xbf\xfe\xbe\xee\xbf\xa1\xbc\xad \xb9\xae\xbc\xad\xb8\xa6 \xbf\xad \xbc\xf6 \xc0\xd6\xc0\xb8\xb8\xe7 \xb7\xb9\xc0\xcc\xbe\xc6\xbf\xf4, \xc6\xf9\xc6\xae, \xb8\xb5\xc5\xa9, \xc0\xcc\xb9\xcc\xc1\xf6 \xb5\xee\xc0\xbb \xbf\xf8\xba\xbb \xb1\xd7\xb4\xeb\xb7\xce \xc0\xc7\xb5\xb5\xc7\xd1 \xb9\xd9 \xb4\xeb\xb7\xce
##\xc7\xa5\xbd\xc3\xc7\xd2 \xbc\xf6 \xc0\xd6\xbd\xc0\xb4\xcf\xb4\xd9. Acrobat 5.0\xc0\xbb \xbb\xe7\xbf\xeb\xc7\xcf\xbf\xa9 \xc0\xa5 \xba\xea\xb6\xf3\xbf\xec\xc0\xfa\xbf\xa1\xbc\xad \xb9\xae\xbc\xad\xb8\xa6 \xbd\xc2\xc0\xce\xc7\xcf\xb0\xed \xc1\xd6\xbc\xae\xc0\xbb \xc3\xdf\xb0\xa1\xc7\xcf\xb4\xc2 \xb9\xe6\xbd\xc4\xc0\xb8\xb7\xce
##\xb1\xe2\xbe\xf7\xc0\xc7 \xbb\xfd\xbb\xea\xbc\xba\xc0\xbb \xc7\xe2\xbb\xf3\xbd\xc3\xc5\xb3 \xbc\xf6 \xc0\xd6\xbd\xc0\xb4\xcf\xb4\xd9.
##
##\xc0\xfa\xc0\xdb\xb1\xc7 &copy; 2001 Adobe Systems Incorporated. \xb8\xf0\xb5\xe7 \xb1\xc7\xb8\xae\xb0\xa1 \xba\xb8\xc8\xa3\xb5\xcb\xb4\xcf\xb4\xd9.
##\xbb\xe7\xbf\xeb\xc0\xda \xbe\xe0\xb0\xfc
##\xbf\xc2\xb6\xf3\xc0\xce \xbb\xe7\xbf\xeb\xc0\xda \xba\xb8\xc8\xa3 \xb1\xd4\xc1\xa4
##Adobe\xc0\xc7 \xc0\xe5\xbe\xd6\xc0\xda \xc1\xf6\xbf\xf8
##\xbc\xd2\xc7\xc1\xc6\xae\xbf\xfe\xbe\xee \xba\xd2\xb9\xfd \xc0\xcc\xbf\xeb \xb9\xe6\xc1\xf6
##"""
##        tx = c.beginText(100,600)
##        tx.setFont('HYSMyeongJo-Medium-KSC-EUC-H', 7, 8)
##        tx.textLines(sample)
##        tx.setFont('Helvetica', 10, 12)
##        tx.textLine()
##        tx.textLines("""This test document shows Korean output from the Reportlab PDF Library.
##            You may use one Korean font, HYSMyeongJo-Medium, and a number of different
##            encodings.
##
##            The available encoding names (with comments from the PDF specification) are:
##            encodings_kor = [
##                'KSC-EUC-H',        # KS X 1001:1992 character set, EUC-KR encoding
##                'KSC-EUC-V',        # Vertical version of KSC-EUC-H
##                'KSCms-UHC-H',      # Microsoft Code Page 949 (lfCharSet 0x81), KS X 1001:1992
##                                    #character set plus 8,822 additional hangul, Unified Hangul
##                                    #Code (UHC) encoding
##                'KSCms-UHC-V',      #Vertical version of KSCms-UHC-H
##                'KSCms-UHC-HW-H',   #Same as KSCms-UHC-H, but replaces proportional Latin
##                                    # characters with halfwidth forms
##                'KSCms-UHC-HW-V',   #Vertical version of KSCms-UHC-HW-H
##                'KSCpc-EUC-H',      #Macintosh, KS X 1001:1992 character set with MacOS-KH
##                                    #extensions, Script Manager Code 3
##                'UniKS-UCS2-H',     #Unicode (UCS-2) encoding for the Adobe-Korea1 character collection
##                'UniKS-UCS2-V'      #Vertical version of UniKS-UCS2-H
##                ]
##
##            The following pages show all characters in the KS X 1001:1992 standard, using the
##            encoding 'KSC-EUC-H' above.  More characters (a LOT more) are available if you
##            use UHC encoding or the Korean Unicode subset, for which the correct encoding
##            names are also listed above.
##            """)
##
##        c.drawText(tx)
##
##        c.setFont('Helvetica',10)
##        c.drawCentredString(297, 36, 'Page %d' % c.getPageNumber())
##        c.showPage()
##
##        # full kuten chart in EUC
##        c.setFont('Helvetica', 18)
##        c.drawString(72,750, 'Characters available in KS X 1001:1992, EUC encoding')
##        y = 600
##        for row in range(1, 95):
##            KutenRowCodeChart(row, 'HYSMyeongJo-Medium','KSC-EUC-H').drawOn(c, 72, y)
##            y = y - 125
##            if y < 50:
##                c.setFont('Helvetica',10)
##                c.drawCentredString(297, 36, 'Page %d' % c.getPageNumber())
##                c.showPage()
##                y = 700

        c.save()

        if VERBOSE:
            print 'saved '+outputfile('test_multibyte_kor.pdf')


def makeSuite():
    return makeSuiteForClasses(KoreanFontTests)


#noruntests
if __name__ == "__main__":
    VERBOSE = 1
    unittest.TextTestRunner().run(makeSuite())
    printLocation()
