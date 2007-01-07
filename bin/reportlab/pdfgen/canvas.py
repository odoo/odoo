#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/pdfgen/canvas.py
__version__=''' $Id: canvas.py 2854 2006-05-10 12:57:21Z rgbecker $ '''
__doc__="""
The Canvas object is the primary interface for creating PDF files. See
doc/userguide.pdf for copious examples.
"""
ENABLE_TRACKING = 1 # turn this off to do profile testing w/o tracking

import os
import sys
import re
from string import join, split, strip, atoi, replace, upper, digits
import tempfile
from types import *
from math import sin, cos, tan, pi, ceil
import md5

from reportlab import rl_config
from reportlab.pdfbase import pdfutils
from reportlab.pdfbase import pdfdoc
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen  import pdfgeom, pathobject, textobject
from reportlab.lib.utils import import_zlib
from reportlab.lib.utils import fp_str


digitPat = re.compile('\d')  #used in decimal alignment

zlib = import_zlib()
_SeqTypes=(TupleType,ListType)

# Robert Kern
# Constants for closing paths.
# May be useful if one changes 'arc' and 'rect' to take a
# default argument that tells how to close the path.
# That way we can draw filled shapes.

FILL_EVEN_ODD = 0
FILL_NON_ZERO = 1
    #this is used by path-closing routines.
    #map stroke, fill, fillmode -> operator
    # fillmode: 1 = non-Zero (obviously), 0 = evenOdd
PATH_OPS = {(0, 0, FILL_EVEN_ODD) : 'n',  #no op
            (0, 0, FILL_NON_ZERO) : 'n',  #no op
            (1, 0, FILL_EVEN_ODD) : 'S',  #stroke only
            (1, 0, FILL_NON_ZERO) : 'S',  #stroke only
            (0, 1, FILL_EVEN_ODD) : 'f*',  #Fill only
            (0, 1, FILL_NON_ZERO) : 'f',  #Fill only
            (1, 1, FILL_EVEN_ODD) : 'B*',  #Stroke and Fill
            (1, 1, FILL_NON_ZERO) : 'B',  #Stroke and Fill
            }

_escapePDF = pdfutils._escape
_instanceEscapePDF = pdfutils._instanceEscapePDF

if sys.hexversion >= 0x02000000:
    def _digester(s):
        return md5.md5(s).hexdigest()
else:
    # hexdigest not available in 1.5
    def _digester(s):
        return join(map(lambda x : "%02x" % ord(x), md5.md5(s).digest()), '')

def _annFormat(D,color,thickness,dashArray):
    from reportlab.pdfbase.pdfdoc import PDFArray
    if color:
        D["C"] = PDFArray([color.red, color.green, color.blue])
    border = [0,0,0]
    if thickness:
        border[2] = thickness
    if dashArray:
        border.append(PDFArray(dashArray))
    D["Border"] = PDFArray(border)

class Canvas(textobject._PDFColorSetter):
    """This class is the programmer's interface to the PDF file format.  Methods
    are (or will be) provided here to do just about everything PDF can do.

    The underlying model to the canvas concept is that of a graphics state machine
    that at any given point in time has a current font, fill color (for figure
    interiors), stroke color (for figure borders), line width and geometric transform, among
    many other characteristics.

    Canvas methods generally either draw something (like canvas.line) using the
    current state of the canvas or change some component of the canvas
    state (like canvas.setFont).  The current state can be saved and restored
    using the saveState/restoreState methods.

    Objects are "painted" in the order they are drawn so if, for example
    two rectangles overlap the last draw will appear "on top".  PDF form
    objects (supported here) are used to draw complex drawings only once,
    for possible repeated use.

    There are other features of canvas which are not visible when printed,
    such as outlines and bookmarks which are used for navigating a document
    in a viewer.

    Here is a very silly example usage which generates a Hello World pdf document.

    from reportlab.pdfgen import canvas
    c = canvas.Canvas("hello.pdf")
    from reportlab.lib.units import inch
    # move the origin up and to the left
    c.translate(inch,inch)
    # define a large font
    c.setFont("Helvetica", 80)
    # choose some colors
    c.setStrokeColorRGB(0.2,0.5,0.3)
    c.setFillColorRGB(1,0,1)
    # draw a rectangle
    c.rect(inch,inch,6*inch,9*inch, fill=1)
    # make text go straight up
    c.rotate(90)
    # change color
    c.setFillColorRGB(0,0,0.77)
    # say hello (note after rotate the y coord needs to be negative!)
    c.drawString(3*inch, -3*inch, "Hello World")
    c.showPage()
    c.save()
    """

    def __init__(self,filename,
                 pagesize=None,
                 bottomup = 1,
                 pageCompression=None,
                 invariant = None,
                 verbosity=0):
        """Create a canvas of a given size. etc.

        You may pass a file-like object to filename as an alternative to
        a string.
        
        Most of the attributes are private - we will use set/get methods
        as the preferred interface.  Default page size is A4."""
        if pagesize is None: pagesize = rl_config.defaultPageSize
        if invariant is None: invariant = rl_config.invariant
        self._filename = filename

        self._doc = pdfdoc.PDFDocument(compression=pageCompression,
                                       invariant=invariant, filename=filename)


        #this only controls whether it prints 'saved ...' - 0 disables
        self._verbosity = verbosity

        #this is called each time a page is output if non-null
        self._onPage = None

        self._pagesize = pagesize
        self._pageRotation = 0
        #self._currentPageHasImages = 0
        self._pageTransition = None
        self._pageDuration = None
        self._destinations = {} # dictionary of destinations for cross indexing.

        self.setPageCompression(pageCompression)
        self._pageNumber = 1   # keep a count
        #self3 = []    #where the current page's marking operators accumulate
        # when we create a form we need to save operations not in the form
        self._codeStack = []
        self._restartAccumulators()  # restart all accumulation state (generalized, arw)
        self._annotationCount = 0

        self._outlines = [] # list for a name tree
        self._psCommandsBeforePage = [] #for postscript tray/font commands
        self._psCommandsAfterPage = [] #for postscript tray/font commands

        #PostScript has the origin at bottom left. It is easy to achieve a top-
        #down coord system by translating to the top of the page and setting y
        #scale to -1, but then text is inverted.  So self.bottomup is used
        #to also set the text matrix accordingly.  You can now choose your
        #drawing coordinates.
        self.bottomup = bottomup
        self.imageCaching = rl_config.defaultImageCaching
        self._make_preamble()
        self.init_graphics_state()
        self.state_stack = []

    def init_graphics_state(self):
        #initial graphics state, never modify any of these in place
        self._x = 0
        self._y = 0
        self._fontname = 'Times-Roman'
        self._fontsize = 12

        self._dynamicFont = 0
        self._textMode = 0  #track if between BT/ET
        self._leading = 14.4
        self._currentMatrix = (1., 0., 0., 1., 0., 0.)
        self._fillMode = 0   #even-odd

        #text state
        self._charSpace = 0
        self._wordSpace = 0
        self._horizScale = 100
        self._textRenderMode = 0
        self._rise = 0
        self._textLineMatrix = (1., 0., 0., 1., 0., 0.)
        self._textMatrix = (1., 0., 0., 1., 0., 0.)

        # line drawing
        self._lineCap = 0
        self._lineJoin = 0
        self._lineDash = None  #not done
        self._lineWidth = 0
        self._mitreLimit = 0

        self._fillColorRGB = (0,0,0)
        self._strokeColorRGB = (0,0,0)

    def push_state_stack(self):
        state = {}
        d = self.__dict__
        for name in self.STATE_ATTRIBUTES:
            state[name] = d[name] #getattr(self, name)
        self.state_stack.append(state)

    def pop_state_stack(self):
        state = self.state_stack[-1]
        del self.state_stack[-1]
        d = self.__dict__
        d.update(state)

    STATE_ATTRIBUTES = split("""
     _x _y _fontname _fontsize _dynamicFont _textMode _leading _currentMatrix _fillMode
     _fillMode _charSpace _wordSpace _horizScale _textRenderMode _rise _textLineMatrix
     _textMatrix _lineCap _lineJoin _lineDash _lineWidth _mitreLimit _fillColorRGB
     _strokeColorRGB""")
    STATE_RANGE = range(len(STATE_ATTRIBUTES))

        #self._addStandardFonts()

    def _make_preamble(self):
        # yuk
        iName = self._doc.getInternalFontName('Helvetica')
        if self.bottomup:
            #must set an initial font
            self._preamble = '1 0 0 1 0 0 cm BT %s 12 Tf 14.4 TL ET' % iName
        else:
            #switch coordinates, flip text and set font
            self._preamble = '1 0 0 -1 0 %s cm BT %s 12 Tf 14.4 TL ET' % (fp_str(self._pagesize[1]), iName)

    if not _instanceEscapePDF:
        def _escape(self, s):
            return _escapePDF(s)

    #info functions - non-standard
    def setAuthor(self, author):
        """identify the author for invisible embedding inside the PDF document.
           the author annotation will appear in the the text of the file but will
           not automatically be seen when the document is viewed, but is visible
           in document properties etc etc."""
        self._doc.setAuthor(author)

    def setDateFormatter(self, dateFormatter):
        """accepts a func(yyyy,mm,dd,hh,m,s) used to create embedded formatted date"""
        self._doc.setDateFormatter(dateFormatter)

    def addOutlineEntry(self, title, key, level=0, closed=None):
        """Adds a new entry to the outline at given level.  If LEVEL not specified,
        entry goes at the top level.  If level specified, it must be
        no more than 1 greater than the outline level in the last call.

        The key must be the (unique) name of a bookmark.
        the title is the (non-unique) name to be displayed for the entry.

        If closed is set then the entry should show no subsections by default
        when displayed.

        Example
           c.addOutlineEntry("first section", "section1")
           c.addOutlineEntry("introduction", "s1s1", 1, closed=1)
           c.addOutlineEntry("body", "s1s2", 1)
           c.addOutlineEntry("detail1", "s1s2s1", 2)
           c.addOutlineEntry("detail2", "s1s2s2", 2)
           c.addOutlineEntry("conclusion", "s1s3", 1)
           c.addOutlineEntry("further reading", "s1s3s1", 2)
           c.addOutlineEntry("second section", "section1")
           c.addOutlineEntry("introduction", "s2s1", 1)
           c.addOutlineEntry("body", "s2s2", 1, closed=1)
           c.addOutlineEntry("detail1", "s2s2s1", 2)
           c.addOutlineEntry("detail2", "s2s2s2", 2)
           c.addOutlineEntry("conclusion", "s2s3", 1)
           c.addOutlineEntry("further reading", "s2s3s1", 2)

        generated outline looks like
            - first section
            |- introduction
            |- body
            |  |- detail1
            |  |- detail2
            |- conclusion
            |  |- further reading
            - second section
            |- introduction
            |+ body
            |- conclusion
            |  |- further reading

        Note that the second "body" is closed.

        Note that you can jump from level 5 to level 3 but not
        from 3 to 5: instead you need to provide all intervening
        levels going down (4 in this case).  Note that titles can
        collide but keys cannot.
        """
        #to be completed
        #self._outlines.append(title)
        self._doc.outline.addOutlineEntry(key, level, title, closed=closed)

    def setOutlineNames0(self, *nametree):   # keep this for now (?)
        """nametree should can be a recursive tree like so
           c.setOutlineNames(
             "chapter1dest",
             ("chapter2dest",
              ["chapter2section1dest",
               "chapter2section2dest",
               "chapter2conclusiondest"]
             ), # end of chapter2 description
             "chapter3dest",
             ("chapter4dest", ["c4s1", "c4s2"])
             )
          each of the string names inside must be bound to a bookmark
          before the document is generated.
        """
        self._doc.outline.setNames(*((self,)+nametree))

    def setTitle(self, title):
        """write a title into the PDF file that won't automatically display
           in the document itself."""
        self._doc.setTitle(title)

    def setSubject(self, subject):
        """write a subject into the PDF file that won't automatically display
           in the document itself."""
        self._doc.setSubject(subject)

    def pageHasData(self):
        "Info function - app can call it after showPage to see if it needs a save"
        return len(self._code) == 0

    def showOutline(self):
        """Specify that Acrobat Reader should start with the outline tree visible.
        showFullScreen() and showOutline() conflict; the one called last
        wins."""
        self._doc._catalog.showOutline()

    def showFullScreen0(self):
        """Specify that Acrobat Reader should start in full screen mode.
        showFullScreen() and showOutline() conflict; the one called last
        wins."""
        self._doc._catalog.showFullScreen()

    def showPage(self):
        """Close the current page and possibly start on a new page."""

        # ensure a space at the end of the stream - Acrobat does
        # not mind, but Ghostscript dislikes 'Qendstream' even if
        # the length marker finishes after 'Q'
        self._code.append(' ')
        page = pdfdoc.PDFPage()
        page.pagewidth = self._pagesize[0]
        page.pageheight = self._pagesize[1]
        page.Rotate = self._pageRotation
        page.hasImages = self._currentPageHasImages
        page.setPageTransition(self._pageTransition)
        page.setCompression(self._pageCompression)
        if self._pageDuration is not None:
            page.Dur = self._pageDuration

        strm =  self._psCommandsBeforePage + [self._preamble] + self._code + self._psCommandsAfterPage
        page.setStream(strm)
        self._setXObjects(page)
        self._setAnnotations(page)
        self._doc.addPage(page)

        if self._onPage: self._onPage(self._pageNumber)
        self._startPage()

    def _startPage(self):
        #now get ready for the next one
        self._pageNumber = self._pageNumber+1
        self._restartAccumulators()
        self.init_graphics_state()
        self.state_stack = []

    def setPageCallBack(self, func):
        """func(pageNum) will be called on each page end.

       This is mainly a hook for progress monitoring.
        Call setPageCallback(None) to clear a callback."""
        self._onPage = func

    def _setAnnotations(self,page):
        page.Annots = self._annotationrefs

    def _setXObjects(self, thing):
        """for pages and forms, define the XObject dictionary for resources, if needed"""
        forms = self._formsinuse
        if forms:
            xobjectsdict = self._doc.xobjDict(forms)
            thing.XObjects = xobjectsdict
        else:
            thing.XObjects = None

    def _bookmarkReference(self, name):
        """get a reference to a (possibly undefined, possibly unbound) bookmark"""
        d = self._destinations
        try:
            return d[name]
        except:
            result = d[name] = pdfdoc.Destination(name) # newly defined, unbound
        return result

    def bookmarkPage(self, key,
                      fit="Fit",
                      left=None,
                      top=None,
                      bottom=None,
                      right=None,
                      zoom=None
                      ):
        """
        This creates a bookmark to the current page which can
        be referred to with the given key elsewhere.

        PDF offers very fine grained control over how Acrobat
        reader is zoomed when people link to this. The default
        is to keep the user's current zoom settings. the last
        arguments may or may not be needed depending on the
        choice of 'fitType'.

        Fit types and the other arguments they use are:
        /XYZ left top zoom - fine grained control.  null
          or zero for any of the parameters means 'leave
          as is', so "0,0,0" will keep the reader's settings.
          NB. Adobe Reader appears to prefer "null" to 0's.

        /Fit - entire page fits in window

        /FitH top - top coord at top of window, width scaled
                    to fit.

        /FitV left - left coord at left of window, height
                     scaled to fit

        /FitR left bottom right top - scale window to fit
                                  the specified rectangle

        (question: do we support /FitB, FitBH and /FitBV
        which are hangovers from version 1.1 / Acrobat 3.0?)"""
        dest = self._bookmarkReference(key)
        self._doc.inPage() # try to enable page-only features
        pageref = self._doc.thisPageRef()

        #None = "null" for PDF
        if left is None:
            left = "null"
        if top is None:
            top = "null"
        if bottom is None:
            bottom = "null"
        if right is None:
            right = "null"
        if zoom is None:
            zoom = "null"

        if fit == "XYZ":
            dest.xyz(left,top,zoom)
        elif fit == "Fit":
            dest.fit()
        elif fit == "FitH":
            dest.fith(top)
        elif fit == "FitV":
            dest.fitv(left)
        elif fit == "FitR":
            dest.fitr(left,bottom,right,top)
        #Do we need these (version 1.1 / Acrobat 3 versions)?
        elif fit == "FitB":
            dest.fitb()
        elif fit == "FitBH":
            dest.fitbh(top)
        elif fit == "FitBV":
            dest.fitbv(left)
        else:
            raise "Unknown Fit type %s" % (fit,)

        dest.setPage(pageref)
        return dest

    def bookmarkHorizontalAbsolute(self, key, top, left=0, fit='XYZ', **kw):
        """Bind a bookmark (destination) to the current page at a horizontal position.
           Note that the yhorizontal of the book mark is with respect to the default
           user space (where the origin is at the lower left corner of the page)
           and completely ignores any transform (translation, scale, skew, rotation,
           etcetera) in effect for the current graphics state.  The programmer is
           responsible for making sure the bookmark matches an appropriate item on
           the page."""
        #This method should probably be deprecated since it is just a sub-set of bookmarkPage
        return self.bookmarkPage(key, fit=fit, top=top, left=left, zoom=0)

    def bookmarkHorizontal(self, key, relativeX, relativeY, **kw):
        """w.r.t. the current transformation, bookmark this horizontal."""
        (left, top) = self.absolutePosition(relativeX,relativeY)
        self.bookmarkHorizontalAbsolute(key, top, left=left, **kw)

    #def _inPage0(self):  disallowed!
    #    """declare a page, enable page features"""
    #    self._doc.inPage()

    #def _inForm0(self):
    #    "deprecated in favore of beginForm...endForm"
    #    self._doc.inForm()

    def doForm(self, name):
        """use a form XObj in current operation stream.

        The form should either have been defined previously using
        beginForm ... endForm, or may be defined later.  If it is not
        defined at save time, an exception will be raised. The form
        will be drawn within the context of the current graphics
        state."""
        self._code.append("/%s Do" % self._doc.getXObjectName(name))
        self._formsinuse.append(name)

    def hasForm(self, name):
        """Query whether form XObj really exists yet."""
        return self._doc.hasForm(name)


        ######################################################
        #
        #   Image routines
        #
        ######################################################

    def drawInlineImage(self, image, x,y, width=None,height=None):
        """Draw an Image into the specified rectangle.  If width and
        height are omitted, they are calculated from the image size.
        Also allow file names as well as images.  The size in pixels
        of the image is returned."""

        self._currentPageHasImages = 1
        from pdfimages import PDFImage
        img_obj = PDFImage(image, x,y, width, height)
        img_obj.drawInlineImage(self)
        return (img_obj.width, img_obj.height)

    def drawImage(self, image, x, y, width=None, height=None, mask=None):
        """Draws the image (ImageReader object or filename) as specified.

        "image" may be an image filename or a ImageReader object.  If width
        and height are not given, the "natural" width and height in pixels
        is used at a scale of 1 point to 1 pixel.

        The mask parameter takes 6 numbers and defines the range of
        RGB values which will be masked out or treated as transparent.
        For example with [0,2,40,42,136,139], it will mask out any
        pixels with a Red value from 0-2, Green from 40-42 and
        Blue from 136-139  (on a scale of 0-255)

        The method returns the width and height of the underlying image since
        this is often useful for layout algorithms.

        Unlike drawInlineImage, this creates 'external images' which
        are only stored once in the PDF file but can be drawn many times.
        If you give it the same filename twice, even at different locations
        and sizes, it will reuse the first occurrence.  If you use ImageReader
        objects, it tests whether the image content has changed before deciding
        whether to reuse it.

        In general you should use drawImage in preference to drawInlineImage
        unless you have read the PDF Spec and understand the tradeoffs."""
        self._currentPageHasImages = 1

        # first, generate a unique name/signature for the image.  If ANYTHING
        # is different, even the mask, this should be different.
        if type(image) == type(''):
            #filename, use it
            name = _digester('%s%s' % (image, mask))
        else:
            rawdata = image.getRGBData()
            name = _digester(rawdata+str(mask))

        # in the pdf document, this will be prefixed with something to
        # say it is an XObject.  Does it exist yet?
        regName = self._doc.getXObjectName(name)
        imgObj = self._doc.idToObject.get(regName, None)
        if not imgObj:
            #first time seen, create and register the PDFImageXobject
            imgObj = pdfdoc.PDFImageXObject(name, image, mask=mask)
            imgObj.name = name
            self._setXObjects(imgObj)
            self._doc.Reference(imgObj, regName)
            self._doc.addForm(name, imgObj)

        # ensure we have a size, as PDF will make it 1x1 pixel otherwise!
        if width is None:
            width = imgObj.width
        if height is None:
            height = imgObj.height

        # scale and draw
        self.saveState()
        self.translate(x, y)
        self.scale(width, height)
        self._code.append("/%s Do" % regName)
        self.restoreState()

        # track what's been used on this page
        self._formsinuse.append(name)

        return (imgObj.width, imgObj.height)

    def _restartAccumulators(self):
        if self._codeStack:
            # restore the saved code
            saved = self._codeStack[-1]
            del self._codeStack[-1]
            (self._code, self._formsinuse, self._annotationrefs, self._formData) = saved
        else:
            self._code = []    # ready for more...
            self._psCommandsAfterPage = []
            self._currentPageHasImages = 1 # for safety...
            self._formsinuse = []
            self._annotationrefs = []
            self._formData = None

    def _pushAccumulators(self):
        "when you enter a form, save accumulator info not related to the form for page (if any)"
        saved = (self._code, self._formsinuse, self._annotationrefs, self._formData)
        self._codeStack.append(saved)
        self._code = []    # ready for more...
        self._currentPageHasImages = 1 # for safety...
        self._formsinuse = []
        self._annotationrefs = []
        self._formData = None

    def beginForm(self, name, lowerx=0, lowery=0, upperx=None, uppery=None):
        """declare the current graphics stream to be a named form.
           A graphics stream can either be a page or a form, not both.
           Some operations (like bookmarking) are permitted for pages
           but not forms.  The form will not automatically be shown in the
           document but must be explicitly referenced using doForm in pages
           that require the form."""
        self.push_state_stack()
        self.init_graphics_state()
        if self._code:
            # save the code that is not in the formf
            self._pushAccumulators()
            #self._codeStack.append(self._code)
            #self._code = []
        self._formData = (name, lowerx, lowery, upperx, uppery)
        self._doc.inForm()
        #self._inForm0()

    def endForm(self):
        """emit the current collection of graphics operations as a Form
           as declared previously in beginForm."""
        (name, lowerx, lowery, upperx, uppery) = self._formData
        #self.makeForm0(name, lowerx, lowery, upperx, uppery)
        # fall through!  makeForm0 disallowed
        #def makeForm0(self, name, lowerx=0, lowery=0, upperx=None, uppery=None):
        """Like showpage, but make a form using accumulated operations instead"""
        # deprecated in favor or beginForm(...)... endForm()
        (w,h) = self._pagesize
        if upperx is None: upperx=w
        if uppery is None: uppery=h
        form = pdfdoc.PDFFormXObject(lowerx=lowerx, lowery=lowery, upperx=upperx, uppery=uppery)
        form.compression = self._pageCompression
        form.setStreamList([self._preamble] + self._code) # ??? minus preamble (seems to be needed!)
        self._setXObjects(form)
        self._setAnnotations(form)
        self._doc.addForm(name, form)
        self._restartAccumulators()
        self.pop_state_stack()


    def addPostScriptCommand(self, command, position=1):
        """Embed literal Postscript in the document.

        With position=0, it goes at very beginning of page stream;
        with position=1, at current point; and
        with position=2, at very end of page stream.  What that does
        to the resulting Postscript depends on Adobe's header :-)

        Use with extreme caution, but sometimes needed for printer tray commands.
        Acrobat 4.0 will export Postscript to a printer or file containing
        the given commands.  Adobe Reader 6.0 no longer does as this feature is
        deprecated.  5.0, I don't know about (please let us know!). This was
        funded by Bob Marshall of Vector.co.uk and tested on a Lexmark 750.
        See test_pdfbase_postscript.py for 2 test cases - one will work on
        any Postscript device, the other uses a 'setpapertray' command which
        will error in Distiller but work on printers supporting it.
        """
        #check if we've done this one already...
        rawName = 'PS' + md5.md5(command).hexdigest()
        regName = self._doc.getXObjectName(rawName)
        psObj = self._doc.idToObject.get(regName, None)
        if not psObj:
            #first use of this chunk of Postscript, make an object
            psObj = pdfdoc.PDFPostScriptXObject(command + '\r\n')
            self._setXObjects(psObj)
            self._doc.Reference(psObj, regName)
            self._doc.addForm(rawName, psObj)
        if position == 0:
            self._psCommandsBeforePage.append("/%s Do" % regName)
        elif position==1:
            self._code.append("/%s Do" % regName)
        else:
            self._psCommandsAfterPage.append("/%s Do" % regName)

        self._formsinuse.append(rawName)

    def _absRect(self,rect,relative=0):
        if not rect:
            w,h = self._pagesize
            rect = (0,0,w,h)
        elif relative:
            lx, ly, ux, uy = rect
            xll,yll = self.absolutePosition(lx,ly)
            xur,yur = self.absolutePosition(ux, uy)
            xul,yul = self.absolutePosition(lx, uy)
            xlr,ylr = self.absolutePosition(ux, ly)
            xs = xll, xur, xul, xlr
            ys = yll, yur, yul, ylr
            xmin, ymin = min(xs), min(ys)
            xmax, ymax = max(xs), max(ys)
            rect = xmin, ymin, xmax, ymax
        return rect

    def freeTextAnnotation(self, contents, DA, Rect=None, addtopage=1, name=None, relative=0, **kw):
        """DA is the default appearance string???"""
        Rect = self._absRect(Rect,relative)
        self._addAnnotation(pdfdoc.FreeTextAnnotation(Rect, contents, DA, **kw), name, addtopage)

    def textAnnotation(self, contents, Rect=None, addtopage=1, name=None, relative=0, **kw):
        """Experimental, but works.
        """
        Rect = self._absRect(Rect,relative)
        self._addAnnotation(pdfdoc.TextAnnotation(Rect, contents, **kw), name, addtopage)
    textAnnotation0 = textAnnotation    #deprecated

    def inkAnnotation(self, contents, InkList=None, Rect=None, addtopage=1, name=None, relative=0, **kw):
        raise NotImplementedError
        "Experimental"
        Rect = self._absRect(Rect,relative)
        if not InkList:
            InkList = ((100,100,100,h-100,w-100,h-100,w-100,100),)
        self._addAnnotation(pdfdoc.InkAnnotation(Rect, contents, InkList, **kw), name, addtopage)
    inkAnnotation0 = inkAnnotation  #deprecated

    def linkAbsolute(self, contents, destinationname, Rect=None, addtopage=1, name=None,
            thickness=0, color=None, dashArray=None, **kw):
        """rectangular link annotation positioned wrt the default user space.
           The identified rectangle on the page becomes a "hot link" which
           when clicked will send the viewer to the page and position identified
           by the destination.

           Rect identifies (lowerx, lowery, upperx, uppery) for lower left
           and upperright points of the rectangle.  Translations and other transforms
           are IGNORED (the rectangular position is given with respect
           to the default user space.
           destinationname should be the name of a bookmark (which may be defined later
           but must be defined before the document is generated).

           You may want to use the keyword argument Border='[0 0 0]' to
           suppress the visible rectangle around the during viewing link."""
        return self.linkRect(contents, destinationname, Rect, addtopage, name, relative=0,
                thickness=thickness, color=color, dashArray=dashArray, **kw)

    def linkRect(self, contents, destinationname, Rect=None, addtopage=1, name=None, relative=0,
            thickness=0, color=None, dashArray=None, **kw):
        """rectangular link annotation w.r.t the current user transform.
           if the transform is skewed/rotated the absolute rectangle will use the max/min x/y
        """
        destination = self._bookmarkReference(destinationname) # permitted to be undefined... must bind later...
        Rect = self._absRect(Rect,relative)
        kw["Rect"] = Rect
        kw["Contents"] = contents
        kw["Destination"] = destination
        _annFormat(kw,color,thickness,dashArray)
        return self._addAnnotation(pdfdoc.LinkAnnotation(**kw), name, addtopage)

    def linkURL(self, url, rect, relative=0, thickness=0, color=None, dashArray=None, kind="URI", **kw):
        """Create a rectangular URL 'hotspot' in the given rectangle.

        if relative=1, this is in the current coord system, otherwise
        in absolute page space.
        The remaining options affect the border appearance; the border is
        drawn by Acrobat, not us.  Set thickness to zero to hide it.
        Any border drawn this way is NOT part of the page stream and
        will not show when printed to a Postscript printer or distilled;
        it is safest to draw your own."""
        from reportlab.pdfbase.pdfdoc import PDFDictionary, PDFName, PDFArray, PDFString
        #tried the documented BS element in the pdf spec but it
        #does not work, and Acrobat itself does not appear to use it!

        ann = PDFDictionary(dict=kw)
        ann["Type"] = PDFName("Annot")
        ann["Subtype"] = PDFName("Link")
        ann["Rect"] = PDFArray(self._absRect(rect,relative)) # the whole page for testing

        # the action is a separate dictionary
        A = PDFDictionary()
        A["Type"] = PDFName("Action") # not needed?
        uri = PDFString(url)
        A['S'] = PDFName(kind)
        if kind=="URI":
            A["URI"] = uri
        elif kind=='GoToR':
            A["F"] = uri
            A["D"] = "[ 0 /XYZ null null null ]"
        else:
            raise ValueError("Unknown linkURI kind '%s'" % kind)

        ann["A"] = A
        _annFormat(ann,color,thickness,dashArray)
        self._addAnnotation(ann)

    def _addAnnotation(self, annotation, name=None, addtopage=1):
        count = self._annotationCount = self._annotationCount+1
        if not name: name="NUMBER"+repr(count)
        self._doc.addAnnotation(name, annotation)
        if addtopage:
            self._annotatePage(name)

    def _annotatePage(self, name):
        ref = self._doc.refAnnotation(name)
        self._annotationrefs.append(ref)

    def getPageNumber(self):
        "get the page number for the current page being generated."
        return self._pageNumber

    def save(self):
        """Saves and close the PDF document in the file.
           If there is current data a ShowPage is executed automatically.
           After this operation the canvas must not be used further."""
        if len(self._code): self.showPage()
        self._doc.SaveToFile(self._filename, self)

    def getpdfdata(self):
        """Returns the PDF data that would normally be written to a file.
        If there is current data a ShowPage is executed automatically.
        After this operation the canvas must not be used further."""
        if len(self._code): self.showPage()
        return self._doc.GetPDFData(self)

    def setPageSize(self, size):
        """accepts a 2-tuple in points for paper size for this
        and subsequent pages"""
        self._pagesize = size
        self._make_preamble()

    def setPageRotation(self, rot):
        """Instruct display device that this page is to be rotated"""
        assert rot % 90.0 == 0.0, "Rotation must be a multiple of 90 degrees"
        self._pageRotation = rot

    def addLiteral(self, s, escaped=1):
        """introduce the literal text of PDF operations s into the current stream.
           Only use this if you are an expert in the PDF file format."""
        s = str(s) # make sure its a string
        if escaped==0:
            s = self._escape(s) # convert to string for safety
        self._code.append(s)

        ######################################################################
        #
        #      coordinate transformations
        #
        ######################################################################
    def resetTransforms(self):
        """I want to draw something (eg, string underlines) w.r.t. the default user space.
           Reset the matrix! This should be used usually as follows:
              canv.saveState()
              canv.resetTransforms()
              ...draw some stuff in default space coords...
              canv.restoreState() # go back!
        """
        # we have to adjoin the inverse, since reset is not a basic operation (without save/restore)
        (selfa, selfb, selfc, selfd, selfe, selff) = self._currentMatrix
        det = selfa*selfd - selfc*selfb
        resulta = selfd/det
        resultc = -selfc/det
        resulte = (selfc*selff - selfd*selfe)/det
        resultd = selfa/det
        resultb = -selfb/det
        resultf = (selfe*selfb - selff*selfa)/det
        self.transform(resulta, resultb, resultc, resultd, resulte, resultf)

    def transform(self, a,b,c,d,e,f):
        """adjoin a mathematical transform to the current graphics state matrix.
           Not recommended for beginners."""
        #"""How can Python track this?"""
        if ENABLE_TRACKING:
            a0,b0,c0,d0,e0,f0 = self._currentMatrix
            self._currentMatrix = (a0*a+c0*b,    b0*a+d0*b,
                                   a0*c+c0*d,    b0*c+d0*d,
                                   a0*e+c0*f+e0, b0*e+d0*f+f0)
        if self._code and self._code[-1][-3:]==' cm':
            L = split(self._code[-1])
            a0, b0, c0, d0, e0, f0 = map(float,L[-7:-1])
            s = len(L)>7 and join(L)+ ' %s cm' or '%s cm'
            self._code[-1] = s % fp_str(a0*a+c0*b,b0*a+d0*b,a0*c+c0*d,b0*c+d0*d,a0*e+c0*f+e0,b0*e+d0*f+f0)
        else:
            self._code.append('%s cm' % fp_str(a,b,c,d,e,f))
        ### debug
##        (a,b,c,d,e,f) = self.Kolor
##        self.Kolor = (f,a,b,c,d,e)
##        self.setStrokeColorRGB(f,a,b)
##        self.setFillColorRGB(f,a,b)
##        self.line(-90,-1000,1,1); self.line(1000,-90,-1,1)
##        self.drawString(0,0,"here")
##    Kolor = (0, 0.5, 1, 0.25, 0.7, 0.3)

    def absolutePosition(self, x, y):
        """return the absolute position of x,y in user space w.r.t. default user space"""
        if not ENABLE_TRACKING:
            raise ValueError, "tracking not enabled! (canvas.ENABLE_TRACKING=0)"
        (a,b,c,d,e,f) = self._currentMatrix
        xp = a*x + c*y + e
        yp = b*x + d*y + f
        return (xp, yp)

    def translate(self, dx, dy):
        """move the origin from the current (0,0) point to the (dx,dy) point
           (with respect to the current graphics state)."""
        self.transform(1,0,0,1,dx,dy)

    def scale(self, x, y):
        """Scale the horizontal dimension by x and the vertical by y
           (with respect to the current graphics state).
           For example canvas.scale(2.0, 0.5) will make everything short and fat."""
        self.transform(x,0,0,y,0,0)

    def rotate(self, theta):
        """Canvas.rotate(theta)

        Rotate the canvas by the angle theta (in degrees)."""
        c = cos(theta * pi / 180)
        s = sin(theta * pi / 180)
        self.transform(c, s, -s, c, 0, 0)

    def skew(self, alpha, beta):
        tanAlpha = tan(alpha * pi / 180)
        tanBeta  = tan(beta  * pi / 180)
        self.transform(1, tanAlpha, tanBeta, 1, 0, 0)

        ######################################################################
        #
        #      graphics state management
        #
        ######################################################################

    def saveState(self):
        """Save the current graphics state to be restored later by restoreState.

        For example:
            canvas.setFont("Helvetica", 20)
            canvas.saveState()
            ...
            canvas.setFont("Courier", 9)
            ...
            canvas.restoreState()
            # if the save/restore pairs match then font is Helvetica 20 again.
        """
        self.push_state_stack()
        self._code.append('q')

    def restoreState(self):
        """restore the graphics state to the matching saved state (see saveState)."""
        self._code.append('Q')
        self.pop_state_stack()

        ###############################################################
        #
        #   Drawing methods.  These draw things directly without
        #   fiddling around with Path objects.  We can add any geometry
        #   methods we wish as long as their meaning is precise and
        #   they are of general use.
        #
        #   In general there are two patterns.  Closed shapes
        #   have the pattern shape(self, args, stroke=1, fill=0);
        #   by default they draw an outline only. Line segments come
        #   in three flavours: line, bezier, arc (which is a segment
        #   of an elliptical arc, approximated by up to four bezier
        #   curves, one for each quadrant.
        #
        #   In the case of lines, we provide a 'plural' to unroll
        #   the inner loop; it is useful for drawing big grids
        ################################################################

        #--------first the line drawing methods-----------------------

    def line(self, x1,y1, x2,y2):
        """draw a line segment from (x1,y1) to (x2,y2) (with color, thickness and
        other attributes determined by the current graphics state)."""
        self._code.append('n %s m %s l S' % (fp_str(x1, y1), fp_str(x2, y2)))

    def lines(self, linelist):
        """Like line(), permits many lines to be drawn in one call.
           for example for the figure
               |
             -- --
               |

             crosshairs = [(20,0,20,10), (20,30,20,40), (0,20,10,20), (30,20,40,20)]
             canvas.lines(crosshairs)
        """
        self._code.append('n')
        for (x1,y1,x2,y2) in linelist:
            self._code.append('%s m %s l' % (fp_str(x1, y1), fp_str(x2, y2)))
        self._code.append('S')

    def grid(self, xlist, ylist):
        """Lays out a grid in current line style.  Supply list of
        x an y positions."""
        assert len(xlist) > 1, "x coordinate list must have 2+ items"
        assert len(ylist) > 1, "y coordinate list must have 2+ items"
        lines = []
        y0, y1 = ylist[0], ylist[-1]
        x0, x1 = xlist[0], xlist[-1]
        for x in xlist:
            lines.append((x,y0,x,y1))
        for y in ylist:
            lines.append((x0,y,x1,y))
        self.lines(lines)

    def bezier(self, x1, y1, x2, y2, x3, y3, x4, y4):
        "Bezier curve with the four given control points"
        self._code.append('n %s m %s c S' %
                          (fp_str(x1, y1), fp_str(x2, y2, x3, y3, x4, y4))
                          )
    def arc(self, x1,y1, x2,y2, startAng=0, extent=90):
        """Draw a partial ellipse inscribed within the rectangle x1,y1,x2,y2,
        starting at startAng degrees and covering extent degrees.   Angles
        start with 0 to the right (+x) and increase counter-clockwise.
        These should have x1<x2 and y1<y2.

        Contributed to piddlePDF by Robert Kern, 28/7/99.
        Trimmed down by AR to remove color stuff for pdfgen.canvas and
        revert to positive coordinates.

        The algorithm is an elliptical generalization of the formulae in
        Jim Fitzsimmon's TeX tutorial <URL: http://www.tinaja.com/bezarc1.pdf>."""

        pointList = pdfgeom.bezierArc(x1,y1, x2,y2, startAng, extent)
        #move to first point
        self._code.append('n %s m' % fp_str(pointList[0][:2]))
        for curve in pointList:
            self._code.append('%s c' % fp_str(curve[2:]))
        # stroke
        self._code.append('S')

        #--------now the shape drawing methods-----------------------

    def rect(self, x, y, width, height, stroke=1, fill=0):
        "draws a rectangle with lower left corner at (x,y) and width and height as given."
        self._code.append('n %s re ' % fp_str(x, y, width, height)
                          + PATH_OPS[stroke, fill, self._fillMode])

    def ellipse(self, x1, y1, x2, y2, stroke=1, fill=0):
        """Draw an ellipse defined by an enclosing rectangle.

        Note that (x1,y1) and (x2,y2) are the corner points of
        the enclosing rectangle.

        Uses bezierArc, which conveniently handles 360 degrees.
        Special thanks to Robert Kern."""

        pointList = pdfgeom.bezierArc(x1,y1, x2,y2, 0, 360)
        #move to first point
        self._code.append('n %s m' % fp_str(pointList[0][:2]))
        for curve in pointList:
            self._code.append('%s c' % fp_str(curve[2:]))
        #finish
        self._code.append(PATH_OPS[stroke, fill, self._fillMode])

    def wedge(self, x1,y1, x2,y2, startAng, extent, stroke=1, fill=0):
        """Like arc, but connects to the centre of the ellipse.
        Most useful for pie charts and PacMan!"""

        x_cen  = (x1+x2)/2.
        y_cen  = (y1+y2)/2.
        pointList = pdfgeom.bezierArc(x1,y1, x2,y2, startAng, extent)

        self._code.append('n %s m' % fp_str(x_cen, y_cen))
        # Move the pen to the center of the rectangle
        self._code.append('%s l' % fp_str(pointList[0][:2]))
        for curve in pointList:
            self._code.append('%s c' % fp_str(curve[2:]))
        # finish the wedge
        self._code.append('%s l ' % fp_str(x_cen, y_cen))
        # final operator
        self._code.append(PATH_OPS[stroke, fill, self._fillMode])

    def circle(self, x_cen, y_cen, r, stroke=1, fill=0):
        """draw a cirle centered at (x_cen,y_cen) with radius r (special case of ellipse)"""

        x1 = x_cen - r
        x2 = x_cen + r
        y1 = y_cen - r
        y2 = y_cen + r
        self.ellipse(x1, y1, x2, y2, stroke, fill)

    def roundRect(self, x, y, width, height, radius, stroke=1, fill=0):
        """Draws a rectangle with rounded corners.  The corners are
        approximately quadrants of a circle, with the given radius."""
        #use a precomputed set of factors for the bezier approximation
        #to a circle. There are six relevant points on the x axis and y axis.
        #sketch them and it should all make sense!
        t = 0.4472 * radius

        x0 = x
        x1 = x0 + t
        x2 = x0 + radius
        x3 = x0 + width - radius
        x4 = x0 + width - t
        x5 = x0 + width

        y0 = y
        y1 = y0 + t
        y2 = y0 + radius
        y3 = y0 + height - radius
        y4 = y0 + height - t
        y5 = y0 + height

        self._code.append('n %s m' % fp_str(x2, y0))
        self._code.append('%s l' % fp_str(x3, y0))  # bottom row
        self._code.append('%s c'
                         % fp_str(x4, y0, x5, y1, x5, y2)) # bottom right

        self._code.append('%s l' % fp_str(x5, y3))  # right edge
        self._code.append('%s c'
                         % fp_str(x5, y4, x4, y5, x3, y5)) # top right

        self._code.append('%s l' % fp_str(x2, y5))  # top row
        self._code.append('%s c'
                         % fp_str(x1, y5, x0, y4, x0, y3)) # top left

        self._code.append('%s l' % fp_str(x0, y2))  # left edge
        self._code.append('%s c'
                         % fp_str(x0, y1, x1, y0, x2, y0)) # bottom left

        self._code.append('h')  #close off, although it should be where it started anyway

        self._code.append(PATH_OPS[stroke, fill, self._fillMode])

        ##################################################
        #
        #  Text methods
        #
        # As with graphics, a separate object ensures that
        # everything is bracketed between  text operators.
        # The methods below are a high-level convenience.
        # use PDFTextObject for multi-line text.
        ##################################################

    def drawString(self, x, y, text):
        """Draws a string in the current text styles."""
        #we could inline this for speed if needed
        t = self.beginText(x, y)
        t.textLine(text)
        self.drawText(t)

    def drawRightString(self, x, y, text):
        """Draws a string right-aligned with the x coordinate"""
        width = self.stringWidth(text, self._fontname, self._fontsize)
        t = self.beginText(x - width, y)
        t.textLine(text)
        self.drawText(t)

    def drawCentredString(self, x, y, text):
        """Draws a string centred on the x coordinate."""
        width = self.stringWidth(text, self._fontname, self._fontsize)
        t = self.beginText(x - 0.5*width, y)
        t.textLine(text)
        self.drawText(t)

    def drawAlignedString(self, x, y, text, pivotChar="."):
        """Draws a string aligned on the first '.' (or other pivot character).

        The centre position of the pivot character will be used as x.
        So, you could draw a straight line down through all the decimals in a
        column of numbers, and anything without a decimal should be
        optically aligned with those that have.

        There is one special rule to help with accounting formatting.  Here's
        how normal numbers should be aligned on the 'dot'. Look at the
        LAST two:
           12,345,67
              987.15
               42
           -1,234.56
             (456.78)
             (456)
               27 inches
               13cm
        Since the last three do not contain a dot, a crude dot-finding
        rule would place them wrong. So we test for the special case
        where no pivot is found, digits are present, but the last character
        is not a digit.  We then work back from the end of the string
        This case is a tad slower but hopefully rare.
        
        """
        parts = text.split(pivotChar,1)
        pivW = self.stringWidth(pivotChar, self._fontname, self._fontsize)
        
        if len(parts) == 1 and digitPat.search(text) is not None and text[-1] not in digits:
            #we have no decimal but it ends in a bracket, or 'in' or something.
            #the cut should be after the last digit.
            leftText = parts[0][0:-1]
            rightText = parts[0][-1]
            #any more?
            while leftText[-1] not in digits:
                rightText = leftText[-1] + rightText
                leftText = leftText[0:-1]

            self.drawRightString(x-0.5*pivW, y, leftText)
            self.drawString(x-0.5*pivW, y, rightText)

        else:
            #normal case
            leftText = parts[0]
            self.drawRightString(x-0.5*pivW, y, leftText)
            if len(parts) > 1:
                rightText = pivotChar + parts[1]
                self.drawString(x-0.5*pivW, y, rightText)

    def getAvailableFonts(self):
        """Returns the list of PostScript font names available.

        Standard set now, but may grow in future with font embedding."""
        fontnames = self._doc.getAvailableFonts()
        fontnames.sort()
        return fontnames

    def addFont(self, fontObj):
        "add a new font for subsequent use."
        self._doc.addFont(fontObj)

    def _addStandardFonts(self):
        """Ensures the standard 14 fonts are available in the system encoding.
        Called by canvas on initialization"""
        for fontName in pdfmetrics.standardFonts:
            self.addFont(pdfmetrics.fontsByName[fontName])

    def listLoadedFonts0(self):
        "Convenience function to list all loaded fonts"
        names = pdfmetrics.widths.keys()
        names.sort()
        return names

    def setFont(self, psfontname, size, leading = None):
        """Sets the font.  If leading not specified, defaults to 1.2 x
        font size. Raises a readable exception if an illegal font
        is supplied.  Font names are case-sensitive! Keeps track
        of font name and size for metrics."""
        self._fontname = psfontname
        self._fontsize = size
        if leading is None:
            leading = size * 1.2
        self._leading = leading
        font = pdfmetrics.getFont(self._fontname)

        self._dynamicFont = getattr(font, '_dynamicFont', 0)
        if not self._dynamicFont:
            pdffontname = self._doc.getInternalFontName(psfontname)
            self._code.append('BT %s %s Tf %s TL ET' % (pdffontname, fp_str(size), fp_str(leading)))

    def setFontSize(self, size=None, leading=None):
        '''Sets font size or leading without knowing the font face'''
        if size is None: size = self._fontsize
        if leading is None: leading = self._leading
        self.setFont(self._fontname, size, leading)

    def stringWidth(self, text, fontName, fontSize):
        "gets width of a string in the given font and size"
        return pdfmetrics.stringWidth(text, fontName, fontSize)

    # basic graphics modes

    def setLineWidth(self, width):
        self._lineWidth = width
        self._code.append('%s w' % fp_str(width))

    def setLineCap(self, mode):
        """0=butt,1=round,2=square"""
        assert mode in (0,1,2), "Line caps allowed: 0=butt,1=round,2=square"
        self._lineCap = mode
        self._code.append('%d J' % mode)

    def setLineJoin(self, mode):
        """0=mitre, 1=round, 2=bevel"""
        assert mode in (0,1,2), "Line Joins allowed: 0=mitre, 1=round, 2=bevel"
        self._lineJoin = mode
        self._code.append('%d j' % mode)

    def setMiterLimit(self, limit):
        self._miterLimit = limit
        self._code.append('%s M' % fp_str(limit))

    def setDash(self, array=[], phase=0):
        """Two notations.  pass two numbers, or an array and phase"""
        if type(array) == IntType or type(array) == FloatType:
            self._code.append('[%s %s] 0 d' % (array, phase))
        elif type(array) == ListType or type(array) == TupleType:
            assert phase >= 0, "phase is a length in user space"
            textarray = ' '.join(map(str, array))
            self._code.append('[%s] %s d' % (textarray, phase))

    # path stuff - the separate path object builds it

    def beginPath(self):
        """Returns a fresh path object.  Paths are used to draw
        complex figures.  The object returned follows the protocol
        for a pathobject.PDFPathObject instance"""
        return pathobject.PDFPathObject()

    def drawPath(self, aPath, stroke=1, fill=0):
        "Draw the path object in the mode indicated"
        gc = aPath.getCode(); pathops = PATH_OPS[stroke, fill, self._fillMode]
        item = "%s %s" % (gc, pathops) # ENSURE STRING CONVERSION
        self._code.append(item)
        #self._code.append(aPath.getCode() + ' ' + PATH_OPS[stroke, fill, self._fillMode])

    def clipPath(self, aPath, stroke=1, fill=0):
        "clip as well as drawing"
        gc = aPath.getCode(); pathops = PATH_OPS[stroke, fill, self._fillMode]
        clip = (self._fillMode == FILL_EVEN_ODD and ' W* ' or ' W ')
        item = "%s%s%s" % (gc, clip, pathops) # ensure string conversion
        self._code.append(item)
        #self._code.append(  aPath.getCode()
        #                   + (self._fillMode == FILL_EVEN_ODD and ' W* ' or ' W ')
        #                   + PATH_OPS[stroke,fill,self._fillMode])

    def beginText(self, x=0, y=0):
        """Returns a fresh text object.  Text objects are used
           to add large amounts of text.  See textobject.PDFTextObject"""
        return textobject.PDFTextObject(self, x, y)

    def drawText(self, aTextObject):
        """Draws a text object"""
        self._code.append(str(aTextObject.getCode()))

    def setPageCompression(self, pageCompression=1):
        """Possible values None, 1 or 0
        If None the value from rl_config will be used.
        If on, the page data will be compressed, leading to much
        smaller files, but takes a little longer to create the files.
        This applies to all subsequent pages, or until setPageCompression()
        is next called."""
        if pageCompression is None: pageCompression = rl_config.pageCompression
        if pageCompression and not zlib:
            self._pageCompression = 0
        else:
            self._pageCompression = pageCompression
        self._doc.setCompression(self._pageCompression)

    def setPageDuration(self, duration=None):
        """Allows hands-off animation of presentations :-)

        If this is set to a number, in full screen mode, Acrobat Reader
        will advance to the next page after this many seconds. The
        duration of the transition itself (fade/flicker etc.) is controlled
        by the 'duration' argument to setPageTransition; this controls
        the time spent looking at the page.  This is effective for all
        subsequent pages."""

        self._pageDuration = duration

    def setPageTransition(self, effectname=None, duration=1,
                        direction=0,dimension='H',motion='I'):
        """PDF allows page transition effects for use when giving
        presentations.  There are six possible effects.  You can
        just guive the effect name, or supply more advanced options
        to refine the way it works.  There are three types of extra
        argument permitted, and here are the allowed values:
            direction_arg = [0,90,180,270]
            dimension_arg = ['H', 'V']
            motion_arg = ['I','O'] (start at inside or outside)

        This table says which ones take which arguments:

        PageTransitionEffects = {
            'Split': [direction_arg, motion_arg],
            'Blinds': [dimension_arg],
            'Box': [motion_arg],
            'Wipe' : [direction_arg],
            'Dissolve' : [],
            'Glitter':[direction_arg]
            }
        Have fun!
        """
        # This builds a Python dictionary with the right arguments
        # for the Trans dictionary in the PDFPage object,
        # and stores it in the variable _pageTransition.
        # showPage later passes this to the setPageTransition method
        # of the PDFPage object, which turns it to a PDFDictionary.
        self._pageTransition = {}
        if not effectname:
            return

        #first check each optional argument has an allowed value
        if direction in [0,90,180,270]:
            direction_arg = ('Di', '/%d' % direction)
        else:
            raise 'PDFError', ' directions allowed are 0,90,180,270'

        if dimension in ['H', 'V']:
            dimension_arg = ('Dm', '/' + dimension)
        else:
            raise'PDFError','dimension values allowed are H and V'

        if motion in ['I','O']:
            motion_arg = ('M', '/' + motion)
        else:
            raise'PDFError','motion values allowed are I and O'

        # this says which effects require which argument types from above
        PageTransitionEffects = {
            'Split': [direction_arg, motion_arg],
            'Blinds': [dimension_arg],
            'Box': [motion_arg],
            'Wipe' : [direction_arg],
            'Dissolve' : [],
            'Glitter':[direction_arg]
            }

        try:
            args = PageTransitionEffects[effectname]
        except KeyError:
            raise 'PDFError', 'Unknown Effect Name "%s"' % effectname

        # now build the dictionary
        transDict = {}
        transDict['Type'] = '/Trans'
        transDict['D'] = '%d' % duration
        transDict['S'] = '/' + effectname
        for (key, value) in args:
            transDict[key] = value
        self._pageTransition = transDict

    def getCurrentPageContent(self):
        """Return uncompressed contents of current page buffer.

        This is useful in creating test cases and assertions of what
        got drawn, without necessarily saving pages to disk"""
        return '\n'.join(self._code)



if _instanceEscapePDF:
    import new
    Canvas._escape = new.instancemethod(_instanceEscapePDF,None,Canvas)

if __name__ == '__main__':
    print 'For test scripts, look in reportlab/test'
