#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/platypus/figures.py
"""This includes some demos of platypus for use in the API proposal"""
__version__='3.3.0'

import os

from reportlab.lib import colors
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import recursiveImport, strTypes
from reportlab.platypus import Frame
from reportlab.platypus import Flowable
from reportlab.platypus import Paragraph
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.lib.validators import isColor
from reportlab.lib.colors import toColor
from reportlab.lib.styles import _baseFontName, _baseFontNameI

captionStyle = ParagraphStyle('Caption', fontName=_baseFontNameI, fontSize=10, alignment=TA_CENTER)

class Figure(Flowable):
    def __init__(self, width, height, caption="",
                 captionFont=_baseFontNameI, captionSize=12,
                 background=None,
                 captionTextColor=toColor('black'),
                 captionBackColor=None,
                 border=None,
                 spaceBefore=12,
                 spaceAfter=12,
                 captionGap=None,
                 captionAlign='centre',
                 captionPosition='bottom',
                 hAlign='CENTER',
                 ):
        Flowable.__init__(self)
        self.width = width
        self.figureHeight = height
        self.caption = caption
        self.captionFont = captionFont
        self.captionSize = captionSize
        self.captionTextColor = captionTextColor
        self.captionBackColor = captionBackColor
        self.captionGap = captionGap or 0.5*captionSize
        self.captionAlign = captionAlign
        self.captionPosition = captionPosition
        self._captionData = None
        self.captionHeight = 0  # work out later
        self.background = background
        self.border = border
        self.spaceBefore = spaceBefore
        self.spaceAfter = spaceAfter
        self.hAlign=hAlign
        self._getCaptionPara()  #Larry Meyn's fix - otherwise they all get the number of the last chapter.

    def _getCaptionPara(self):
        caption = self.caption
        captionFont = self.captionFont
        captionSize = self.captionSize
        captionTextColor = self.captionTextColor
        captionBackColor = self.captionBackColor
        captionAlign = self.captionAlign
        captionPosition = self.captionPosition
        if self._captionData!=(caption,captionFont,captionSize,captionTextColor,captionBackColor,captionAlign,captionPosition):
            self._captionData = (caption,captionFont,captionSize,captionTextColor,captionBackColor,captionAlign,captionPosition)
            if isinstance(caption,Paragraph):
                self.captionPara = caption
            elif isinstance(caption,strTypes):
                self.captionStyle = ParagraphStyle(
                    'Caption',
                    fontName=captionFont,
                    fontSize=captionSize,
                    leading=1.2*captionSize,
                    textColor = captionTextColor,
                    backColor = captionBackColor,
                    #seems to be getting ignored
                    spaceBefore=self.captionGap,
                    alignment=TA_LEFT if captionAlign=='left' else TA_RIGHT if captionAlign=='right' else TA_CENTER,
                    )
                #must build paragraph now to get sequencing in synch with rest of story
                self.captionPara = Paragraph(self.caption, self.captionStyle)
            else:
                raise ValueError('Figure caption of type %r is not a string or Paragraph' % type(caption))

    def wrap(self, availWidth, availHeight):
        # try to get the caption aligned
        if self.caption:
            self._getCaptionPara()
            w, h = self.captionPara.wrap(self.width, availHeight - self.figureHeight)
            self.captionHeight = h + self.captionGap
            self.height = self.captionHeight + self.figureHeight
            if w>self.width: self.width = w
        else:
            self.height = self.figureHeight
        if self.hAlign in ('CENTER','CENTRE',TA_CENTER):
            self.dx = 0.5 * (availWidth - self.width)
        elif self.hAlign in ('RIGHT',TA_RIGHT):
            self.dx = availWidth - self.width
        else:
            self.dx = 0
        return (self.width, self.height)

    def draw(self):
        self.canv.translate(self.dx, 0)
        if self.caption and self.captionPosition=='bottom':
            self.canv.translate(0, self.captionHeight)
        if self.background:
            self.drawBackground()
        if self.border:
            self.drawBorder()
        self.canv.saveState()
        self.drawFigure()
        self.canv.restoreState()
        if self.caption:
            if self.captionPosition=='bottom':
                self.canv.translate(0, -self.captionHeight)
            else:
                self.canv.translate(0, self.figureHeight+self.captionGap)
            self._getCaptionPara()
            self.drawCaption()

    def drawBorder(self):
        self.canv.drawBoundary(self.border,0,0,self.width, self.figureHeight)

    def _doBackground(self, color):
        self.canv.saveState()
        self.canv.setFillColor(self.background)
        self.canv.rect(0, 0, self.width, self.figureHeight, fill=1)
        self.canv.restoreState()

    def drawBackground(self):
        """For use when using a figure on a differently coloured background.
        Allows you to specify a colour to be used as a background for the figure."""
        if isColor(self.background):
            self._doBackground(self.background)
        else:
            try:
                c = toColor(self.background)
                self._doBackground(c)
            except:
                pass

    def drawCaption(self):
        self.captionPara.drawOn(self.canv, 0, 0)

    def drawFigure(self):
        pass

def drawPage(canvas,x, y, width, height):
    #draws something which looks like a page
    pth = canvas.beginPath()
    corner = 0.05*width

    # shaded backdrop offset a little
    canvas.setFillColorRGB(0.5,0.5,0.5)
    canvas.rect(x + corner, y - corner, width, height, stroke=0, fill=1)

    #'sheet of paper' in light yellow
    canvas.setFillColorRGB(1,1,0.9)
    canvas.setLineWidth(0)
    canvas.rect(x, y, width, height, stroke=1, fill=1)

    #reset
    canvas.setFillColorRGB(0,0,0)
    canvas.setStrokeColorRGB(0,0,0)

class PageFigure(Figure):
    """Shows a blank page in a frame, and draws on that.  Used in
    illustrations of how PLATYPUS works."""
    def __init__(self, background=None):
        Figure.__init__(self, 3*inch, 3*inch)
        self.caption = 'Figure 1 - a blank page'
        self.captionStyle = captionStyle
        self.background = background

    def drawVirtualPage(self):
        pass

    def drawFigure(self):
        drawPage(self.canv, 0.625*inch, 0.25*inch, 1.75*inch, 2.5*inch)
        self.canv.translate(0.625*inch, 0.25*inch)
        self.canv.scale(1.75/8.27, 2.5/11.69)
        self.drawVirtualPage()

class PlatPropFigure1(PageFigure):
    """This shows a page with a frame on it"""
    def __init__(self):
        PageFigure.__init__(self)
        self.caption = "Figure 1 - a page with a simple frame"
    def drawVirtualPage(self):
        demo1(self.canv)

class FlexFigure(Figure):
    """Base for a figure class with a caption. Can grow or shrink in proportion"""
    def __init__(self, width, height, caption, background=None,
                        captionFont='Helvetica-Oblique',captionSize=8,
                        captionTextColor=colors.black,
                        shrinkToFit=1,
                        growToFit=1,
                        spaceBefore=12,
                        spaceAfter=12,
                        captionGap=9,
                        captionAlign='centre',
                        captionPosition='top',
                        scaleFactor=None,
                        hAlign='CENTER',
                        border=1,
                        ):
        Figure.__init__(self, width, height, caption,
                        captionFont=captionFont,
                        captionSize=captionSize,
                        background=None,
                        captionTextColor=captionTextColor,
                        spaceBefore = spaceBefore,
                        spaceAfter = spaceAfter,
                        captionGap=captionGap,
                        captionAlign=captionAlign,
                        captionPosition=captionPosition,
                        hAlign=hAlign,
                        border=border,
                        )
        self.shrinkToFit = shrinkToFit  #if set and wrap is too tight, shrinks
        self.growToFit = growToFit      #if set and wrap is too small, grows
        self.scaleFactor = scaleFactor
        self._scaleFactor = None
        self.background = background

    def _scale(self,availWidth,availHeight):
        "Rescale to fit according to the rules, but only once"
        if self._scaleFactor is None or self.width>availWidth or self.height>availHeight:
            w, h = Figure.wrap(self, availWidth, availHeight)
            captionHeight = h - self.figureHeight
            if self.scaleFactor is None:
                #scale factor None means auto
                self._scaleFactor = min(availWidth/self.width,(availHeight-captionHeight)/self.figureHeight)
            else: #they provided a factor
                self._scaleFactor = self.scaleFactor
            if self._scaleFactor<1 and self.shrinkToFit:
                self.width = self.width * self._scaleFactor - 0.0001
                self.figureHeight = self.figureHeight * self._scaleFactor
            elif self._scaleFactor>1 and self.growToFit:
                self.width = self.width*self._scaleFactor - 0.0001
                self.figureHeight = self.figureHeight * self._scaleFactor

    def wrap(self, availWidth, availHeight):
        self._scale(availWidth,availHeight)
        return Figure.wrap(self, availWidth, availHeight)

    def split(self, availWidth, availHeight):
        self._scale(availWidth,availHeight)
        return Figure.split(self, availWidth, availHeight)

class ImageFigure(FlexFigure):
    """Image with a caption below it"""
    def __init__(self, filename, caption, background=None,scaleFactor=None,hAlign='CENTER',border=None):
        assert os.path.isfile(filename), 'image file %s not found' % filename
        from reportlab.lib.utils import ImageReader
        w, h = ImageReader(filename).getSize()
        self.filename = filename
        FlexFigure.__init__(self, w, h, caption, background,scaleFactor=scaleFactor,hAlign=hAlign,border=border)

    def drawFigure(self):
        self.canv.drawImage(self.filename,
                                  0, 0,self.width, self.figureHeight)

class DrawingFigure(FlexFigure):
    """Drawing with a caption below it.  Clunky, scaling fails."""
    def __init__(self, modulename, classname, caption, baseDir=None, background=None):
        module = recursiveImport(modulename, baseDir)
        klass = getattr(module, classname)
        self.drawing = klass()
        FlexFigure.__init__(self,
                            self.drawing.width,
                            self.drawing.height,
                            caption,
                            background)
        self.growToFit = 1

    def drawFigure(self):
        self.canv.scale(self._scaleFactor, self._scaleFactor)
        self.drawing.drawOn(self.canv, 0, 0)

try:
    from rlextra.pageCatcher.pageCatcher import restoreForms, storeForms, storeFormsInMemory, restoreFormsInMemory
    _hasPageCatcher = 1
except ImportError:
    _hasPageCatcher = 0
if _hasPageCatcher:
    ####################################################################
    #
    #    PageCatcher plugins
    # These let you use our PageCatcher product to add figures
    # to other documents easily.
    ####################################################################
    class PageCatcherCachingMixIn:
        "Helper functions to cache pages for figures"

        def getFormName(self, pdfFileName, pageNo):
            #naming scheme works within a directory only
            dirname, filename = os.path.split(pdfFileName)
            root, ext = os.path.splitext(filename)
            return '%s_page%d' % (root, pageNo)

        def needsProcessing(self, pdfFileName, pageNo):
            "returns 1 if no forms or form is older"
            formName = self.getFormName(pdfFileName, pageNo)
            if os.path.exists(formName + '.frm'):
                formModTime = os.stat(formName + '.frm')[8]
                pdfModTime = os.stat(pdfFileName)[8]
                return (pdfModTime > formModTime)
            else:
                return 1

        def processPDF(self, pdfFileName, pageNo):
            formName = self.getFormName(pdfFileName, pageNo)
            storeForms(pdfFileName, formName + '.frm',
                                    prefix= formName + '_',
                                    pagenumbers=[pageNo])
            #print 'stored %s.frm' % formName
            return formName + '.frm'

    class cachePageCatcherFigureNonA4(FlexFigure, PageCatcherCachingMixIn):
        """PageCatcher page with a caption below it.  Size to be supplied."""
        # This should merge with PageFigure into one class that reuses
        # form information to determine the page orientation...
        def __init__(self, filename, pageNo, caption, width, height, background=None):
            self.dirname, self.filename = os.path.split(filename)
            if self.dirname == '':
                self.dirname = os.curdir
            self.pageNo = pageNo
            self.formName = self.getFormName(self.filename, self.pageNo) + '_' + str(pageNo)
            FlexFigure.__init__(self, width, height, caption, background)

        def drawFigure(self):
            self.canv.saveState()
            if not self.canv.hasForm(self.formName):
                restorePath = self.dirname + os.sep + self.filename
                #does the form file exist?  if not, generate it.
                formFileName = self.getFormName(restorePath, self.pageNo) + '.frm'
                if self.needsProcessing(restorePath, self.pageNo):
                    #print 'preprocessing PDF %s page %s' % (restorePath, self.pageNo)
                    self.processPDF(restorePath, self.pageNo)
                names = restoreForms(formFileName, self.canv)
            self.canv.scale(self._scaleFactor, self._scaleFactor)
            self.canv.doForm(self.formName)
            self.canv.restoreState()

    class cachePageCatcherFigure(cachePageCatcherFigureNonA4):
        """PageCatcher page with a caption below it.  Presumes A4, Portrait.
        This needs our commercial PageCatcher product, or you'll get a blank."""
        def __init__(self, filename, pageNo, caption, width=595, height=842, background=None):
            cachePageCatcherFigureNonA4.__init__(self, filename, pageNo, caption, width, height, background=background)

    class PageCatcherFigureNonA4(FlexFigure):
        """PageCatcher page with a caption below it.  Size to be supplied."""
        # This should merge with PageFigure into one class that reuses
        # form information to determine the page orientation...
        _cache = {}
        def __init__(self, filename, pageNo, caption, width, height, background=None, caching=None):
            fn = self.filename = filename
            self.pageNo = pageNo
            fn = fn.replace(os.sep,'_').replace('/','_').replace('\\','_').replace('-','_').replace(':','_')
            self.prefix = fn.replace('.','_')+'_'+str(pageNo)+'_'
            self.formName = self.prefix + str(pageNo)
            self.caching = caching
            FlexFigure.__init__(self, width, height, caption, background)

        def drawFigure(self):
            if not self.canv.hasForm(self.formName):
                if self.filename in self._cache:
                    f,data = self._cache[self.filename]
                else:
                    f = open(self.filename,'rb')
                    pdf = f.read()
                    f.close()
                    f, data = storeFormsInMemory(pdf, pagenumbers=[self.pageNo], prefix=self.prefix)
                    if self.caching=='memory':
                        self._cache[self.filename] = f, data
                f = restoreFormsInMemory(data, self.canv)
            self.canv.saveState()
            self.canv.scale(self._scaleFactor, self._scaleFactor)
            self.canv.doForm(self.formName)
            self.canv.restoreState()

    class PageCatcherFigure(PageCatcherFigureNonA4):
        """PageCatcher page with a caption below it.  Presumes A4, Portrait.
        This needs our commercial PageCatcher product, or you'll get a blank."""
        def __init__(self, filename, pageNo, caption, width=595, height=842, background=None, caching=None):
            PageCatcherFigureNonA4.__init__(self, filename, pageNo, caption, width, height, background=background, caching=caching)

def demo1(canvas):
    frame = Frame(
                    2*inch,     # x
                    4*inch,     # y at bottom
                    4*inch,     # width
                    5*inch,     # height
                    showBoundary = 1  # helps us see what's going on
                    )
    bodyStyle = ParagraphStyle('Body', fontName=_baseFontName, fontSize=24, leading=28, spaceBefore=6)
    para1 = Paragraph('Spam spam spam spam. ' * 5, bodyStyle)
    para2 = Paragraph('Eggs eggs eggs. ' * 5, bodyStyle)
    mydata = [para1, para2]

    #this does the packing and drawing.  The frame will consume
    #items from the front of the list as it prints them
    frame.addFromList(mydata,canvas)

def test1():
    c  = Canvas('figures.pdf')
    f = Frame(inch, inch, 6*inch, 9*inch, showBoundary=1)
    v = PlatPropFigure1()
    v.captionTextColor = toColor('blue')
    v.captionBackColor = toColor('lightyellow')
    f.addFromList([v],c)
    c.save()

if __name__ == '__main__':
    test1()
