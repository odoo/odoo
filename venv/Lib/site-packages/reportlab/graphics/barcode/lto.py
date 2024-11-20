# (c) 2008 Jerome Alet - <alet@librelogiciel.com>
# Licensing terms : ReportLab's license.

from reportlab.graphics.barcode.code39 import Standard39
from reportlab.lib import colors
from reportlab.lib.units import cm
from string import ascii_uppercase, digits as string_digits

class BaseLTOLabel(Standard39) :
    """
    Base class for LTO labels.

    Specification taken from "IBM LTO Ultrium Cartridge Label Specification, Revision 3"
    available on  May 14th 2008 from :
    http://www-1.ibm.com/support/docview.wss?rs=543&context=STCVQ6R&q1=ssg1*&uid=ssg1S7000429&loc=en_US&cs=utf-8&lang=en+en
    """
    LABELWIDTH = 7.9 * cm
    LABELHEIGHT = 1.7 * cm
    LABELROUND = 0.15 * cm
    CODERATIO = 2.75
    CODENOMINALWIDTH = 7.4088 * cm
    CODEBARHEIGHT = 1.11 * cm
    CODEBARWIDTH = 0.0432 * cm
    CODEGAP = CODEBARWIDTH
    CODELQUIET = 10 * CODEBARWIDTH
    CODERQUIET = 10 * CODEBARWIDTH
    def __init__(self, prefix="",
                       number=None,
                       subtype="1",
                       border=None,
                       checksum=False,
                       availheight=None) :
        """
           Initializes an LTO label.

           prefix : Up to six characters from [A-Z][0-9]. Defaults to "".
           number : Label's number or None. Defaults to None.
           subtype : LTO subtype string , e.g. "1" for LTO1. Defaults to "1".
           border : None, or the width of the label's border. Defaults to None.
           checksum : Boolean indicates if checksum char has to be printed. Defaults to False.
           availheight : Available height on the label, or None for automatic. Defaults to None.
        """
        self.height = max(availheight, self.CODEBARHEIGHT)
        self.border = border
        if (len(subtype) != 1) \
            or (subtype not in ascii_uppercase + string_digits) :
            raise ValueError("Invalid subtype '%s'" % subtype)
        if ((not number) and (len(prefix) > 6)) \
           or not prefix.isalnum() :
            raise ValueError("Invalid prefix '%s'" % prefix)
        label = "%sL%s" % ((prefix + str(number or 0).zfill(6 - len(prefix)))[:6],
                           subtype)
        if len(label) != 8 :
            raise ValueError("Invalid set of parameters (%s, %s, %s)" \
                                % (prefix, number, subtype))
        self.label = label
        Standard39.__init__(self,
                            label,
                            ratio=self.CODERATIO,
                            barHeight=self.height,
                            barWidth=self.CODEBARWIDTH,
                            gap=self.CODEGAP,
                            lquiet=self.CODELQUIET,
                            rquiet=self.CODERQUIET,
                            quiet=True,
                            checksum=checksum)

    def drawOn(self, canvas, x, y) :
        """Draws the LTO label onto the canvas."""
        canvas.saveState()
        canvas.translate(x, y)
        if self.border :
            canvas.setLineWidth(self.border)
            canvas.roundRect(0, 0,
                        self.LABELWIDTH,
                        self.LABELHEIGHT,
                        self.LABELROUND)
        Standard39.drawOn(self,
                          canvas,
                          (self.LABELWIDTH-self.CODENOMINALWIDTH)/2.0,
                          self.LABELHEIGHT-self.height)
        canvas.restoreState()

class VerticalLTOLabel(BaseLTOLabel) :
    """
    A class for LTO labels with rectangular blocks around the tape identifier.
    """
    LABELFONT = ("Helvetica-Bold", 14)
    BLOCKWIDTH = 1*cm
    BLOCKHEIGHT = 0.45*cm
    LINEWIDTH = 0.0125
    NBBLOCKS = 7
    COLORSCHEME = ("red",
                   "yellow",
                   "lightgreen",
                   "lightblue",
                   "grey",
                   "orangered",
                   "pink",
                   "darkgreen",
                   "orange",
                   "purple")

    def __init__(self, *args, **kwargs) :
        """
        Initializes the label.

        colored : boolean to determine if blocks have to be colorized.
        """
        if "colored" in kwargs:
            self.colored = kwargs["colored"]
            del kwargs["colored"]
        else :
            self.colored = False
        kwargs["availheight"] = self.LABELHEIGHT-self.BLOCKHEIGHT
        BaseLTOLabel.__init__(self, *args, **kwargs)

    def drawOn(self, canvas, x, y) :
        """Draws some blocks around the identifier's characters."""
        BaseLTOLabel.drawOn(self,
                            canvas,
                            x,
                            y)
        canvas.saveState()
        canvas.setLineWidth(self.LINEWIDTH)
        canvas.setStrokeColorRGB(0, 0, 0)
        canvas.translate(x, y)
        xblocks = (self.LABELWIDTH-(self.NBBLOCKS*self.BLOCKWIDTH))/2.0
        for i in range(self.NBBLOCKS) :
            (font, size) = self.LABELFONT
            newfont = self.LABELFONT
            if i == (self.NBBLOCKS - 1) :
                part = self.label[i:]
                (font, size) = newfont
                size /= 2.0
                newfont = (font, size)
            else :
                part = self.label[i]
            canvas.saveState()
            canvas.translate(xblocks+(i*self.BLOCKWIDTH), 0)
            if self.colored and part.isdigit() :
                canvas.setFillColorRGB(*getattr(colors,
                                                self.COLORSCHEME[int(part)],
                                                colors.Color(1, 1, 1)).rgb())
            else:
                canvas.setFillColorRGB(1, 1, 1)
            canvas.rect(0, 0, self.BLOCKWIDTH, self.BLOCKHEIGHT, fill=True)
            canvas.translate((self.BLOCKWIDTH+canvas.stringWidth(part, *newfont))/2.0,
                             (self.BLOCKHEIGHT/2.0))
            canvas.rotate(90.0)
            canvas.setFont(*newfont)
            canvas.setFillColorRGB(0, 0, 0)
            canvas.drawCentredString(0, 0, part)
            canvas.restoreState()
        canvas.restoreState()

def test() :
    """Test this."""
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.lib import pagesizes

    canvas = Canvas("labels.pdf", pagesize=pagesizes.A4)
    canvas.setFont("Helvetica", 30)
    (width, height) = pagesizes.A4
    canvas.drawCentredString(width/2.0, height-4*cm, "Sample LTO labels")
    xpos = xorig = 2 * cm
    ypos = yorig = 2 * cm
    colwidth = 10 * cm
    lineheight = 3.9 * cm
    count = 1234
    BaseLTOLabel("RL", count, "3").drawOn(canvas, xpos, ypos)
    ypos += lineheight
    count += 1
    BaseLTOLabel("RL", count, "3",
                 border=0.0125).drawOn(canvas, xpos, ypos)
    ypos += lineheight
    count += 1
    VerticalLTOLabel("RL", count, "3").drawOn(canvas, xpos, ypos)
    ypos += lineheight
    count += 1
    VerticalLTOLabel("RL", count, "3",
                    border=0.0125).drawOn(canvas, xpos, ypos)
    ypos += lineheight
    count += 1
    VerticalLTOLabel("RL", count, "3",
                    colored=True).drawOn(canvas, xpos, ypos)
    ypos += lineheight
    count += 1
    VerticalLTOLabel("RL", count, "3",
                    border=0.0125, colored=True).drawOn(canvas, xpos, ypos)
    canvas.showPage()
    canvas.save()

if __name__ == "__main__" :
    test()
