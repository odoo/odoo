#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/lib/codecharts.py
#$Header $
__version__='3.3.0'
__doc__="""Routines to print code page (character set) drawings. Predates unicode.

To be sure we can accurately represent characters in various encodings
and fonts, we need some routines to display all those characters.
These are defined herein.  The idea is to include flowable, drawable
and graphic objects for single and multi-byte fonts. """
import codecs

from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Flowable
from reportlab.pdfbase import pdfmetrics, cidfonts
from reportlab.graphics.shapes import Group, String, Rect
from reportlab.graphics.widgetbase import Widget
from reportlab.lib import colors
from reportlab.lib.utils import int2Byte

adobe2codec = {
    'WinAnsiEncoding':'winansi',
    'MacRomanEncoding':'macroman',
    'MacExpert':'macexpert',
    'PDFDoc':'pdfdoc',
    
    }

class CodeChartBase(Flowable):
    """Basic bits of drawing furniture used by
    single and multi-byte versions: ability to put letters
    into boxes."""

    def calcLayout(self):
        "Work out x and y positions for drawing"


        rows = self.codePoints * 1.0 / self.charsPerRow
        if rows == int(rows):
            self.rows = int(rows)
        else:
            self.rows = int(rows) + 1
        # size allows for a gray column of labels
        self.width = self.boxSize * (1+self.charsPerRow)
        self.height = self.boxSize * (1+self.rows)

        #handy lists
        self.ylist = []
        for row in range(self.rows + 2):
            self.ylist.append(row * self.boxSize)
        self.xlist = []
        for col in range(self.charsPerRow + 2):
            self.xlist.append(col * self.boxSize)

    def formatByte(self, byt):
        if self.hex:
            return '%02X' % byt
        else:
            return '%d' % byt

    def drawChars(self, charList):
        """Fills boxes in order.  None means skip a box.
        Empty boxes at end get filled with gray"""
        extraNeeded = (self.rows * self.charsPerRow - len(charList))
        for i in range(extraNeeded):
            charList.append(None)
        #charList.extend([None] * extraNeeded)
        row = 0
        col = 0
        self.canv.setFont(self.fontName, self.boxSize * 0.75)
        for ch in charList:  # may be 2 bytes or 1
            if ch is None:
                self.canv.setFillGray(0.9)
                self.canv.rect((1+col) * self.boxSize, (self.rows - row - 1) * self.boxSize,
                    self.boxSize, self.boxSize, stroke=0, fill=1)
                self.canv.setFillGray(0.0)
            else:
                try:
                    self.canv.drawCentredString(
                            (col+1.5) * self.boxSize,
                            (self.rows - row - 0.875) * self.boxSize,
                            ch,
                            )
                except:
                    self.canv.setFillGray(0.9)
                    self.canv.rect((1+col) * self.boxSize, (self.rows - row - 1) * self.boxSize,
                        self.boxSize, self.boxSize, stroke=0, fill=1)
                    self.canv.drawCentredString(
                            (col+1.5) * self.boxSize,
                            (self.rows - row - 0.875) * self.boxSize,
                            '?',
                            )
                    self.canv.setFillGray(0.0)
            col = col + 1
            if col == self.charsPerRow:
                row = row + 1
                col = 0

    def drawLabels(self, topLeft = ''):
        """Writes little labels in the top row and first column"""
        self.canv.setFillGray(0.8)
        self.canv.rect(0, self.ylist[-2], self.width, self.boxSize, fill=1, stroke=0)
        self.canv.rect(0, 0, self.boxSize, self.ylist[-2], fill=1, stroke=0)
        self.canv.setFillGray(0.0)

        #label each row and column
        self.canv.setFont('Helvetica-Oblique',0.375 * self.boxSize)
        byt = 0
        for row in range(self.rows):
            if self.rowLabels:
                label = self.rowLabels[row]
            else: # format start bytes as hex or decimal
                label = self.formatByte(row * self.charsPerRow)
            self.canv.drawCentredString(0.5 * self.boxSize,
                                        (self.rows - row - 0.75) * self.boxSize,
                                        label
                                        )
        for col in range(self.charsPerRow):
            self.canv.drawCentredString((col + 1.5) * self.boxSize,
                                        (self.rows + 0.25) * self.boxSize,
                                        self.formatByte(col)
                                        )

        if topLeft:
            self.canv.setFont('Helvetica-BoldOblique',0.5 * self.boxSize)
            self.canv.drawCentredString(0.5 * self.boxSize,
                                        (self.rows + 0.25) * self.boxSize,
                                        topLeft
                                        )

class SingleByteEncodingChart(CodeChartBase):
    def __init__(self, faceName='Helvetica', encodingName='WinAnsiEncoding',
                 charsPerRow=16, boxSize=14, hex=1):
        self.codePoints = 256
        self.faceName = faceName
        self.encodingName = encodingName
        self.fontName = self.faceName + '-' + self.encodingName
        self.charsPerRow = charsPerRow
        self.boxSize = boxSize
        self.hex = hex
        self.rowLabels = None
        pdfmetrics.registerFont(pdfmetrics.Font(self.fontName,
                                                self.faceName,
                                                self.encodingName)
                                )

        self.calcLayout()


    def draw(self):
        self.drawLabels()
        charList = [None] * 32 + list(map(int2Byte, list(range(32, 256))))

        #we need to convert these to Unicode, since ReportLab
        #2.0 can only draw in Unicode.

        encName = self.encodingName
        #apply some common translations
        encName = adobe2codec.get(encName, encName)
        decoder = codecs.lookup(encName)[1]
        def decodeFunc(txt):
            if txt is None:
                return None
            else:
                return decoder(txt, errors='replace')[0]
            
        charList = [decodeFunc(ch) for ch in charList]


        
        self.drawChars(charList)
        self.canv.grid(self.xlist, self.ylist)


class KutenRowCodeChart(CodeChartBase):
    """Formats one 'row' of the 94x94 space used in many Asian encodings.aliases

    These deliberately resemble the code charts in Ken Lunde's "Understanding
    CJKV Information Processing", to enable manual checking.  Due to the large
    numbers of characters, we don't try to make one graphic with 10,000 characters,
    but rather output a sequence of these."""
    #would be cleaner if both shared one base class whose job
    #was to draw the boxes, but never mind...
    def __init__(self, row, faceName, encodingName):
        self.row = row
        self.codePoints = 94
        self.boxSize = 18
        self.charsPerRow = 20
        self.rows = 5
        self.rowLabels = ['00','20','40','60','80']
        self.hex = 0
        self.faceName = faceName
        self.encodingName = encodingName

        try:
            # the dependent files might not be available
            font = cidfonts.CIDFont(self.faceName, self.encodingName)
            pdfmetrics.registerFont(font)
        except:
            # fall back to English and at least shwo we can draw the boxes
            self.faceName = 'Helvetica'
            self.encodingName = 'WinAnsiEncoding'
        self.fontName = self.faceName + '-' + self.encodingName
        self.calcLayout()

    def makeRow(self, row):
        """Works out the character values for this kuten row"""
        cells = []
        if self.encodingName.find('EUC') > -1:
            # it is an EUC family encoding.
            for col in range(1, 95):
                ch = int2Byte(row + 160) + int2Byte(col+160)
                cells.append(ch)
##        elif self.encodingName.find('GB') > -1:
##            # it is an EUC family encoding.
##            for col in range(1, 95):
##                ch = int2Byte(row + 160) + int2Byte(col+160)
        else:
            cells.append([None] * 94)
        return cells

    def draw(self):
        self.drawLabels(topLeft= 'R%d' % self.row)

        # work out which characters we need for the row
        #assert self.encodingName.find('EUC') > -1, 'Only handles EUC encoding today, you gave me %s!' % self.encodingName

        # pad out by 1 to match Ken Lunde's tables
        charList = [None] + self.makeRow(self.row)
        self.drawChars(charList)
        self.canv.grid(self.xlist, self.ylist)


class Big5CodeChart(CodeChartBase):
    """Formats one 'row' of the 94x160 space used in Big 5

    These deliberately resemble the code charts in Ken Lunde's "Understanding
    CJKV Information Processing", to enable manual checking."""
    def __init__(self, row, faceName, encodingName):
        self.row = row
        self.codePoints = 160
        self.boxSize = 18
        self.charsPerRow = 16
        self.rows = 10
        self.hex = 1
        self.faceName = faceName
        self.encodingName = encodingName
        self.rowLabels = ['4','5','6','7','A','B','C','D','E','F']
        try:
            # the dependent files might not be available
            font = cidfonts.CIDFont(self.faceName, self.encodingName)
            pdfmetrics.registerFont(font)
        except:
            # fall back to English and at least shwo we can draw the boxes
            self.faceName = 'Helvetica'
            self.encodingName = 'WinAnsiEncoding'
        self.fontName = self.faceName + '-' + self.encodingName
        self.calcLayout()

    def makeRow(self, row):
        """Works out the character values for this Big5 row.
        Rows start at 0xA1"""
        cells = []
        if self.encodingName.find('B5') > -1:
            # big 5, different row size
            for y in [4,5,6,7,10,11,12,13,14,15]:
                for x in range(16):
                    col = y*16+x
                    ch = int2Byte(row) + int2Byte(col)
                    cells.append(ch)

        else:
            cells.append([None] * 160)
        return cells

    def draw(self):
        self.drawLabels(topLeft='%02X' % self.row)

        charList = self.makeRow(self.row)
        self.drawChars(charList)
        self.canv.grid(self.xlist, self.ylist)


def hBoxText(msg, canvas, x, y, fontName):
    """Helper for stringwidth tests on Asian fonts.

    Registers font if needed.  Then draws the string,
    and a box around it derived from the stringWidth function"""
    canvas.saveState()
    try:
        font = pdfmetrics.getFont(fontName)
    except KeyError:
        font = cidfonts.UnicodeCIDFont(fontName)
        pdfmetrics.registerFont(font)

    canvas.setFillGray(0.8)
    canvas.rect(x,y,pdfmetrics.stringWidth(msg, fontName, 16),16,stroke=0,fill=1)
    canvas.setFillGray(0)
    canvas.setFont(fontName, 16,16)
    canvas.drawString(x,y,msg)
    canvas.restoreState()


class CodeWidget(Widget):
    """Block showing all the characters"""
    def __init__(self):
        self.x = 0
        self.y = 0
        self.width = 160
        self.height = 160

    def draw(self):
        dx = self.width / 16.0
        dy = self.height / 16.0
        g = Group()
        g.add(Rect(self.x, self.y, self.width, self.height,
                   fillColor=None, strokeColor=colors.black))
        for x in range(16):
            for y in range(16):
                charValue = y * 16 + x
                if charValue > 32:
                    s = String(self.x + x * dx,
                               self.y + (self.height - y*dy), int2Byte(charValue))
                    g.add(s)
        return g






def test():
    c = Canvas('codecharts.pdf')
    c.setFont('Helvetica-Bold', 24)
    c.drawString(72, 750, 'Testing code page charts')
    cc1 = SingleByteEncodingChart()
    cc1.drawOn(c, 72, 500)

    cc2 = SingleByteEncodingChart(charsPerRow=32)
    cc2.drawOn(c, 72, 300)

    cc3 = SingleByteEncodingChart(charsPerRow=25, hex=0)
    cc3.drawOn(c, 72, 100)

##    c.showPage()
##
##    c.setFont('Helvetica-Bold', 24)
##    c.drawString(72, 750, 'Multi-byte Kuten code chart examples')
##    KutenRowCodeChart(1, 'HeiseiMin-W3','EUC-H').drawOn(c, 72, 600)
##    KutenRowCodeChart(16, 'HeiseiMin-W3','EUC-H').drawOn(c, 72, 450)
##    KutenRowCodeChart(84, 'HeiseiMin-W3','EUC-H').drawOn(c, 72, 300)
##
##    c.showPage()
##    c.setFont('Helvetica-Bold', 24)
##    c.drawString(72, 750, 'Big5 Code Chart Examples')
##    #Big5CodeChart(0xA1, 'MSungStd-Light-Acro','ETenms-B5-H').drawOn(c, 72, 500)

    c.save()
    print('saved codecharts.pdf')

if __name__=='__main__':
    test()
