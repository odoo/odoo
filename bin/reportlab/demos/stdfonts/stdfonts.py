#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/demos/stdfonts/stdfonts.py
__version__=''' $Id: stdfonts.py 2830 2006-04-05 15:18:32Z rgbecker $ '''
__doc__="""
This generates tables showing the 14 standard fonts in both
WinAnsi and MacRoman encodings, and their character codes.
Supply an argument of 'hex' or 'oct' to get code charts
in those encodings; octal is what you need for \\n escape
sequences in Python literals.

usage: standardfonts.py [dec|hex|oct]
"""
import sys
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas
import string

label_formats = {'dec':('%d=', 'Decimal'),
                 'oct':('%o=','Octal'),
                 'hex':('0x%x=', 'Hexadecimal')}

def run(mode):

    label_formatter, caption = label_formats[mode]

    for enc in ['MacRoman', 'WinAnsi']:
        canv = canvas.Canvas(
                'StandardFonts_%s.pdf' % enc,
                )
        canv.setPageCompression(0)

        for faceName in pdfmetrics.standardFonts:
            if faceName in ['Symbol', 'ZapfDingbats']:
                encLabel = faceName+'Encoding'
            else:
                encLabel = enc + 'Encoding'

            fontName = faceName + '-' + encLabel
            pdfmetrics.registerFont(pdfmetrics.Font(fontName,
                                        faceName,
                                        encLabel)
                        )

            canv.setFont('Times-Bold', 18)
            canv.drawString(80, 744, fontName)
            canv.setFont('Times-BoldItalic', 12)
            canv.drawRightString(515, 744, 'Labels in ' + caption)


            #for dingbats, we need to use another font for the numbers.
            #do two parallel text objects.
            for byt in range(32, 256):
                col, row = divmod(byt - 32, 32)
                x = 72 + (66*col)
                y = 720 - (18*row)
                canv.setFont('Helvetica', 14)
                canv.drawString(x, y, label_formatter % byt)
                canv.setFont(fontName, 14)
                canv.drawString(x+44, y, chr(byt).decode(encLabel,'ignore').encode('utf8'))
            canv.showPage()
        canv.save()

if __name__ == '__main__':
    if len(sys.argv)==2:
        mode = string.lower(sys.argv[1])
        if mode not in ['dec','oct','hex']:
            print __doc__

    elif len(sys.argv) == 1:
        mode = 'dec'
        run(mode)
    else:
        print __doc__
