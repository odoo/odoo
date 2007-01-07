#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history www.reportlab.co.uk/rl-cgi/viewcvs.cgi/rlextra/rlj/jpsupport.py
# Temporary japanese support for ReportLab.
"""
The code in this module will disappear any day now and be replaced
by classes in reportlab.pdfbase.cidfonts
"""


import string, os
import codecs
from reportlab.test import unittest
from reportlab.test.utils import makeSuiteForClasses, outputfile, printLocation

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib import colors
from reportlab.lib.codecharts import KutenRowCodeChart, hBoxText

global VERBOSE
VERBOSE = 0


class CHSFontTests(unittest.TestCase):

    def test0(self):
        "A basic document drawing some strings"

        # if they do not have the Japanese font files, go away quietly
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont, findCMapFile


        pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))

        c = Canvas(outputfile('test_multibyte_chs.pdf'))
        c.setFont('Helvetica', 30)
        c.drawString(100,700, 'Simplified Chinese Font Support')


        c.setFont('Helvetica', 10)
        c.drawString(100,680, 'Short sample: "China - Zhang Ziyi"  (famous actress)')
        # the two typefaces

        hBoxText(u'\u4e2d\u56fd - \u7ae0\u5b50\u6021',
                 c,
                 100,
                 660,
                 'STSong-Light',
                 )


        c.setFont('Helvetica',10)
        c.drawCentredString(297, 36, 'Page %d' % c.getPageNumber())
        c.showPage()

##        # full kuten chart in EUC
##        c.setFont('Helvetica', 18)
##        c.drawString(72,750, 'Characters available in GB 2312-80, EUC encoding')
##        y = 600
##        enc = 'GB_EUC_H'
##        for row in range(1, 95):
##            KutenRowCodeChart(row, 'STSong-Light',enc).drawOn(c, 72, y)
##            y = y - 125
##            if y < 50:
##                c.setFont('Helvetica',10)
##                c.drawCentredString(297, 36, 'Page %d' % c.getPageNumber())
##                c.showPage()
##                y = 700
##
        c.save()
        if VERBOSE:
            print 'saved '+outputfile('test_multibyte_chs.pdf')


def makeSuite():
    return makeSuiteForClasses(CHSFontTests)


#noruntests
if __name__ == "__main__":
    VERBOSE = 1
    unittest.TextTestRunner().run(makeSuite())
    printLocation()
