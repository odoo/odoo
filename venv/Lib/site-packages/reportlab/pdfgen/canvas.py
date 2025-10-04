#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
__version__='3.3.0'
__doc__="""
The Canvas object is the primary interface for creating PDF files. See
doc/reportlab-userguide.pdf for copious examples.
"""

__all__ = ['Canvas']
ENABLE_TRACKING = 1 # turn this off to do profile testing w/o tracking

import re
import hashlib
from string import digits
from math import sin, cos, tan, pi
from reportlab import rl_config
from reportlab.pdfbase import pdfdoc
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen  import pathobject
from reportlab.pdfgen.textobject import PDFTextObject, _PDFColorSetter
from reportlab.lib.colors import black, _chooseEnforceColorSpace, Color, CMYKColor, toColor
from reportlab.lib.utils import ImageReader, isSeq, isStr, isUnicode, _digester, asUnicode
from reportlab.lib.rl_accel import fp_str, escapePDF
from reportlab.lib.boxstuff import aspectRatioFix

digitPat = re.compile(r'\d')  #used in decimal alignment

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

def _annFormat(D,color,thickness,dashArray,hradius=0,vradius=0):
    from reportlab.pdfbase.pdfdoc import PDFArray, PDFDictionary
    if color and 'C' not in D:
        D["C"] = PDFArray([color.red, color.green, color.blue])
    if 'Border' not in D:
        border = [hradius,vradius,thickness or 0]
        if dashArray:
            border.append(PDFArray(dashArray))
        D["Border"] = PDFArray(border)
#   BS = PDFDictionary()
#   bss = 'S'
#   if dashArray:
#       BS['D'] = PDFArray(dashArray)
#       bss = 'D'
#   BS['W'] = thickness or 0
#   BS['S'] = bss
#   D['BS'] = BS

# helpers to guess color space for gradients
def _normalizeColor(aColor):
    if isinstance(aColor, CMYKColor):
        d = aColor.density
        return "DeviceCMYK", tuple(c*d for c in aColor.cmyk())
    elif isinstance(aColor, Color):
        return "DeviceRGB", aColor.rgb()
    elif isinstance(aColor, (tuple, list)):
        l = len(aColor)
        if l == 3:
            return "DeviceRGB", aColor
        elif l == 4:
            return "DeviceCMYK", aColor
    elif isinstance(aColor, str):
        return _normalizeColor(toColor(aColor))
    raise ValueError("Unknown color %r" % aColor)

def _normalizeColors(colors):
    space = None
    outcolors = []
    for aColor in colors:
        nspace, outcolor = _normalizeColor(aColor)
        if space is not None and space != nspace:
            raise ValueError("Mismatch in color spaces: %s and %s" % (space, nspace))
        space = nspace
        outcolors.append(outcolor)
    return space, outcolors

def _buildColorFunction(colors, positions):
    from reportlab.pdfbase.pdfdoc import PDFExponentialFunction, PDFStitchingFunction
    if positions is not None and len(positions) != len(colors):
        raise ValueError("need to have the same number of colors and positions")
    # simplified functions for edge cases
    if len(colors) == 1:
        # for completeness
        return PDFExponentialFunction(N=1, C0=colors[0], C1=colors[0])
    if len(colors) == 2:
        if positions is None or (positions[0] == 0 and positions[1] == 1):
            return PDFExponentialFunction(N=1, C0=colors[0], C1=colors[1])
    # equally distribute if positions not specified
    if positions is None:
        nc = len(colors)
        positions = [float(x)/(nc-1) for x in range(nc)]
    else:
        # sort positions and colors in increasing order
        poscolors = list(zip(positions, colors))
        poscolors.sort(key=lambda x: x[0])
        # add endpoint positions if not already present
        if poscolors[0][0] != 0:
            poscolors.insert(0, (0.0, poscolors[0][1]))
        if poscolors[-1][0] != 1:
            poscolors.append((1.0, poscolors[-1][1]))
        positions, colors = list(zip(*poscolors)) # unzip
    # build stitching function
    functions = []
    bounds = [pos for pos in positions[1:-1]]
    encode = []
    lastcolor = colors[0]
    for color in colors[1:]:
        functions.append(PDFExponentialFunction(N=1, C0=lastcolor, C1=color))
        lastcolor = color
        encode.append(0.0)
        encode.append(1.0)
    return PDFStitchingFunction(functions, bounds, encode, Domain="[0.0 1.0]")

class   ExtGState:
    defaults = dict(
                CA=1,
                ca=1,
                OP=False,
                op=False,
                OPM=0,
                BM='Normal',
                )
    allowed = dict(
                BM = {
                    'Normal', 'Multiply', 'Screen', 'Overlay',
                    'Darken', 'Lighten', 'ColorDodge', 'ColorBurn',
                    'HardLight', 'SoftLight', 'Difference', 'Exclusion',
                    'Hue', 'Saturation', 'Color', 'Luminosity',
                    },
                )
    pdfNameValues = {'BM'}

    @staticmethod
    def _boolTransform(v):
        return str(v).lower()

    @staticmethod
    def _identityTransform(v):
        return v

    @staticmethod
    def _pdfNameTransform(v):
        return '/'+v

    def __init__(self):
        self._d = {}
        self._c = {}

    def set(self,canv,a,v):
        d = self.defaults[a]
        if isinstance(d,bool):
            v=bool(v)
            vTransform = self._boolTransform
        elif a in self.pdfNameValues:
            if v not in self.allowed[a]:
                raise ValueError('ExtGstate[%r] = %r not in allowed values %r' % (
                    a,v,self.allowed[a]))
            vTransform = self._pdfNameTransform
        else:
            vTransform = self._identityTransform
        if v!=self._d.get(a,d) or (a=='op' and self.getValue('OP')!=d):
            self._d[a] = v
            t = a,vTransform(v)
            if t in self._c:
                name = self._c[t]
            else:
                name = 'gRLs'+str(len(self._c))
                self._c[t] = name
            canv._code.append('/%s gs' % name)

    def getValue(self,a):
        return self._d.get(a,self.defaults[a])

    def getState(self):
        S = {}
        for t,name in self._c.items():
            S[name] = pdfdoc.PDFDictionary(dict((t,)))
        return S and pdfdoc.PDFDictionary(S) or None

    def pushCopy(self):
        '''the states must be shared across push/pop, but the values not'''
        x = self.__class__()
        x._d = self._d.copy()
        x._c = self._c
        return x

class Canvas(_PDFColorSetter):
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

    Example:: 
    
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
                 verbosity=0,
                 encrypt=None,
                 cropMarks=None,
                 pdfVersion=None,
                 enforceColorSpace=None,
                 initialFontName=None,
                 initialFontSize=None,
                 initialLeading=None,
                 cropBox=None,
                 artBox=None,
                 trimBox=None,
                 bleedBox=None,
                 lang=None,
                 ):
        """Create a canvas of a given size. etc.

        You may pass a file-like object to filename as an alternative to
        a string.
        For more information about the encrypt parameter refer to the setEncrypt method.
        
        Most of the attributes are private - we will use set/get methods
        as the preferred interface.  Default page size is A4.
        cropMarks may be True/False or an object with parameters borderWidth, markColor, markWidth
        and markLength
    
        if enforceColorSpace is in ('cmyk', 'rgb', 'sep','sep_black','sep_cmyk') then one of
        the standard _PDFColorSetter callables will be used to enforce appropriate color settings.
        If it is a callable then that will be used.
        """
        if pagesize is None: pagesize = rl_config.defaultPageSize
        if invariant is None: invariant = rl_config.invariant

        self._initialFontName = initialFontName if initialFontName else rl_config.canvas_basefontname
        self._initialFontSize = initialFontSize if initialFontSize is not None else 12
        self._initialLeading = initialLeading if initialLeading is not None else self._initialFontSize*1.2

        self._filename = filename

        self._doc = pdfdoc.PDFDocument(compression=pageCompression,
                                       invariant=invariant, filename=filename,
                                       pdfVersion=pdfVersion or pdfdoc.PDF_VERSION_DEFAULT,
                                       lang=lang
                                       )

        self._enforceColorSpace = _chooseEnforceColorSpace(enforceColorSpace)

        #this only controls whether it prints 'saved ...' - 0 disables
        self._verbosity = verbosity

        #this is called each time a page is output if non-null
        self._onPage = None
        self._cropMarks = cropMarks

        self._pagesize = pagesize
        self._hanging_pagesize = None
        self._pageRotation = 0
        #self._currentPageHasImages = 0
        self._pageTransition = None
        self._pageDuration = None
        self._destinations = {} # dictionary of destinations for cross indexing.

        self.setPageCompression(pageCompression)
        self._pageNumber = 1   # keep a count
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

        self._cropBox = cropBox     #we don't do semantics for these at all
        self._artBox = artBox
        self._trimBox = trimBox
        self._bleedBox = bleedBox

        self.init_graphics_state()
        self._make_preamble()
        self.state_stack = []

        self.setEncrypt(encrypt)

    def setEncrypt(self, encrypt):
        '''
        Set the encryption used for the pdf generated by this canvas.
        If encrypt is a string object, it is used as the user password for the pdf.
        If encrypt is an instance of reportlab.lib.pdfencrypt.StandardEncryption, this object is
        used to encrypt the pdf. This allows more finegrained control over the encryption settings.
        '''
        if encrypt:
            from reportlab.lib import pdfencrypt
            if isStr(encrypt): #encrypt is the password itself
                if isUnicode(encrypt):
                    encrypt = encrypt.encode('utf-8')
                encrypt = pdfencrypt.StandardEncryption(encrypt)    #now it's the encrypt object
                encrypt.setAllPermissions(1)
            elif not isinstance(encrypt, pdfencrypt.StandardEncryption):
                raise TypeError('Expected string or instance of reportlab.lib.pdfencrypt.StandardEncryption as encrypt parameter but got %r' % encrypt)
            self._doc.encrypt = encrypt
        else:
            try:
                del self._doc.encrypt
            except AttributeError:
                pass

    def init_graphics_state(self):
        #initial graphics state, never modify any of these in place
        self._x = 0
        self._y = 0
        self._fontname = self._initialFontName
        self._fontsize = self._initialFontSize

        self._textMode = 0  #track if between BT/ET
        self._leading = self._initialLeading
        self._currentMatrix = (1., 0., 0., 1., 0., 0.)
        self._fillMode = FILL_EVEN_ODD

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
        self._lineWidth = 1
        self._mitreLimit = 0

        self._fillColorObj = self._strokeColorObj = rl_config.canvas_baseColor or (0,0,0)
        self._extgstate = ExtGState()

    def push_state_stack(self):
        state = {}
        d = self.__dict__
        for name in self.STATE_ATTRIBUTES:
            state[name] = d[name] #getattr(self, name)
        self.state_stack.append(state)
        self._extgstate = self._extgstate.pushCopy()

    def pop_state_stack(self):
        self.__dict__.update(self.state_stack.pop())

    STATE_ATTRIBUTES = """_x _y _fontname _fontsize _textMode _leading _currentMatrix _fillMode
     _charSpace _wordSpace _horizScale _textRenderMode _rise _textLineMatrix
     _textMatrix _lineCap _lineJoin _lineDash _lineWidth _mitreLimit _fillColorObj
     _strokeColorObj _extgstate""".split()
    STATE_RANGE = list(range(len(STATE_ATTRIBUTES)))

        #self._addStandardFonts()

    def _make_preamble(self):
        P = [].append
        if self.bottomup:
            P('1 0 0 1 0 0 cm')
        else:
            P('1 0 0 -1 0 %s cm' % fp_str(self._pagesize[1]))
        C = self._code
        n = len(C)
        if self._fillColorObj != (0,0,0):
            self.setFillColor(self._fillColorObj)
        if self._strokeColorObj != (0,0,0):
            self.setStrokeColor(self._strokeColorObj)
        P(' '.join(C[n:]))
        del C[n:]
        font = pdfmetrics.getFont(self._fontname)
        if not font._dynamicFont:
            #set an initial font
            if font.face.builtIn or not getattr(self,'_drawTextAsPath',False):
                P('BT %s 12 Tf 14.4 TL ET' % self._doc.getInternalFontName(self._fontname))
        self._preamble = ' '.join(P.__self__)

    def _escape(self, s):
        return escapePDF(s)

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

        Example::
        
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

        generated outline looks like::
        
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
        """nametree should can be a recursive tree like so::
            
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

    def setCreator(self, creator):
        """write a creator into the PDF file that won't automatically display
           in the document itself. This should be used to name the original app
           which is passing data into ReportLab, if you wish to name it."""
        self._doc.setCreator(creator)

    def setProducer(self, producer):
        """change the default producer value"""
        self._doc.setProducer(producer)

    def setKeywords(self, keywords):
        """write a list of keywords into the PDF file which shows in document properties.
        Either submit a single string or a list/tuple"""
        if isinstance(keywords,(list,tuple)):
            keywords = ', '.join(keywords)
        self._doc.setKeywords(keywords)

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

    def _setStrokeAlpha(self,v):
        """
        Define the transparency/opacity of strokes. 0 is fully
        transparent, 1 is fully opaque.

        Note that calling this function will cause a version 1.4 PDF
        to be generated (rather than 1.3).
        """
        self._doc.ensureMinPdfVersion('transparency')
        self._extgstate.set(self,'CA',v)

    def _setFillAlpha(self,v):
        """
        Define the transparency/opacity of non-strokes. 0 is fully
        transparent, 1 is fully opaque.

        Note that calling this function will cause a version 1.4 PDF
        to be generated (rather than 1.3).
        """
        self._doc.ensureMinPdfVersion('transparency')
        self._extgstate.set(self,'ca',v)

    def _setStrokeOverprint(self,v):
        self._extgstate.set(self,'OP',v)

    def _setFillOverprint(self,v):
        self._extgstate.set(self,'op',v)

    def _setOverprintMask(self,v):
        self._extgstate.set(self,'OPM',v and 1 or 0)

    def setBlendMode(self, v):
        self._extgstate.set(self,'BM',v)

    def _getCmShift(self):
        cM = self._cropMarks
        if cM:
            bleedW = max(0,getattr(cM,'bleedWidth',0))
            bw = max(0,getattr(cM,'borderWidth',36))
            if bleedW:
                bw -= bleedW
            return bw

    def showPage(self):
        """Close the current page and possibly start on a new page."""
        # ensure a space at the end of the stream - Acrobat does
        # not mind, but Ghostscript dislikes 'Qendstream' even if
        # the length marker finishes after 'Q'

        pageWidth = self._pagesize[0]
        pageHeight = self._pagesize[1]
        cM = self._cropMarks
        code = self._code
        if cM:
            bw = max(0,getattr(cM,'borderWidth',36))
            if bw:
                markLast = getattr(cM,'markLast',1)
                ml = min(bw,max(0,getattr(cM,'markLength',18)))
                mw = getattr(cM,'markWidth',0.5)
                mc = getattr(cM,'markColor',black)
                mg = 2*bw-ml
                cx0 = len(code)
                if ml and mc:
                    self.saveState()
                    self.setStrokeColor(mc)
                    self.setLineWidth(mw)
                    self.lines([
                        (bw,0,bw,ml),
                        (pageWidth+bw,0,pageWidth+bw,ml),
                        (bw,pageHeight+mg,bw,pageHeight+2*bw),
                        (pageWidth+bw,pageHeight+mg,pageWidth+bw,pageHeight+2*bw),
                        (0,bw,ml,bw),
                        (pageWidth+mg,bw,pageWidth+2*bw,bw),
                        (0,pageHeight+bw,ml,pageHeight+bw),
                        (pageWidth+mg,pageHeight+bw,pageWidth+2*bw,pageHeight+bw),
                        ])
                    self.restoreState()
                    if markLast:
                        #if the marks are to be drawn after the content
                        #save the code we just drew for later use
                        L = code[cx0:]
                        del code[cx0:]
                        cx0 = len(code)

                bleedW = max(0,getattr(cM,'bleedWidth',0))
                self.saveState()
                self.translate(bw-bleedW,bw-bleedW)
                if bleedW:
                    #scale everything
                    self.scale(1+(2.0*bleedW)/pageWidth,1+(2.0*bleedW)/pageHeight)

                #move our translation/expansion code to the beginning
                C = code[cx0:]
                del code[cx0:]
                code[0:0] = C
                self.restoreState()
                if markLast:
                    code.extend(L)
                pageWidth = 2*bw + pageWidth
                pageHeight = 2*bw + pageHeight

        code.append(' ')
        page = pdfdoc.PDFPage()
        page.pagewidth = pageWidth
        page.pageheight = pageHeight
        page.Rotate = self._pageRotation
        page.hasImages = self._currentPageHasImages
        page.setPageTransition(self._pageTransition)
        page.setCompression(self._pageCompression)
        for box in ('crop','art','bleed','trim'):
            size = getattr(self,'_%sBox'%box,None)
            if size:
                setattr(page,box.capitalize()+'Box',pdfdoc.PDFArray(size))
        if self._pageDuration is not None:
            page.Dur = self._pageDuration

        strm =  self._psCommandsBeforePage + [self._preamble] + code + self._psCommandsAfterPage
        page.setStream(strm)
        self._setColorSpace(page)
        self._setExtGState(page)
        self._setXObjects(page)
        self._setShadingUsed(page)
        self._setAnnotations(page)
        self._doc.addPage(page)

        if self._onPage: self._onPage(self._pageNumber)
        self._startPage()

    def _startPage(self):
        #now get ready for the next one
        if self._hanging_pagesize:
            self.setPageSize(self._hanging_pagesize)
            self._hanging_pagesize = None
        self._pageNumber += 1
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

    def _setColorSpace(self,obj):
        obj._colorsUsed = self._colorsUsed

    def _setShadingUsed(self, page):
        page._shadingUsed = self._shadingUsed

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
        
        - XYZ left top zoom - fine grained control.  null
          or zero for any of the parameters means 'leave
          as is', so "0,0,0" will keep the reader's settings.
          NB. Adobe Reader appears to prefer "null" to 0's.

        - Fit - entire page fits in window

        - FitH top - top coord at top of window, width scaled
          to fit.

        - FitV left - left coord at left of window, height
          scaled to fit

        - FitR left bottom right top - scale window to fit
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
            raise ValueError("Unknown Fit type %s" % ascii(fit))

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
    def drawInlineImage(self, image, x,y, width=None,height=None,
            preserveAspectRatio=False,anchor='c', anchorAtXY=False, showBoundary=False):
        """See drawImage, which should normally be used instead... 
        
        drawInlineImage behaves like drawImage, but stores the image content
        within the graphics stream for the page.  This means that the mask
        parameter for transparency is not available.  It also means that there 
        is no saving in file size or time if the same image is reused.  
        
        In theory it allows images to be displayed slightly faster; however, 
        we doubt if the difference is noticeable to any human user these days.
        Only use this if you have studied the PDF specification and know the
        implications.
        """
    
        self._currentPageHasImages = 1
        from reportlab.pdfgen.pdfimages import PDFImage
        img_obj = PDFImage(image, x,y, width, height)
        img_obj.drawInlineImage(self,
            preserveAspectRatio=preserveAspectRatio, 
            anchor=anchor,anchorAtXY=anchorAtXY,showBoundary=showBoundary)
        return (img_obj.width, img_obj.height)

    def drawImage(self, image, x, y, width=None, height=None, mask=None, 
            preserveAspectRatio=False, anchor='c', anchorAtXY=False, showBoundary=False):
        """Draws the image (ImageReader object or filename) as specified.

        "image" may be an image filename or an ImageReader object. 
 
        x and y define the lower left corner of the image you wish to
        draw (or of its bounding box, if using preserveAspectRation below).
         
        If width and height are not given, the width and height of the
        image in pixels is used at a scale of 1 point to 1 pixel.  
       
        If width and height are given, the image will be stretched to fill 
        the given rectangle bounded by (x, y, x+width, y-height).  
        
        If you supply negative widths and/or heights, it inverts them and adjusts
        x and y accordingly.

        The method returns the width and height of the underlying image, since
        this is often useful for layout algorithms and saves you work if you have
        not specified them yourself.

        The mask parameter supports transparent backgrounds. It takes 6 numbers
        and defines the range of RGB values which will be masked out or treated
        as transparent.  For example with [0,2,40,42,136,139], it will mask out
        any pixels with a Red value from 0-2, Green from 40-42 and
        Blue from 136-139  (on a scale of 0-255).

        New post version 2.0:  drawImage can center an image in a box you
        provide, while preserving its aspect ratio.  For example, you might
        have a fixed square box in your design, and a collection of photos
        which might be landscape or portrait that you want to appear within 
        the box.  If preserveAspectRatio is true, your image will appear within
        the box specified.

        
        If preserveAspectRatio is True, the anchor property can be used to
        specify how images should fit into the given box.  It should 
        be set to one of the following values, taken from the points of
        the compass (plus 'c' for 'centre'):

                nw   n   ne
                w    c    e
                sw   s   se

        The default value is 'c' for 'centre'.  Thus, if you want your
        bitmaps to always be centred and appear at the top of the given box,
        set anchor='n'.      There are good examples of this in the output
        of test_pdfgen_general.py

        Unlike drawInlineImage, this creates 'external images' which
        are only stored once in the PDF file but can be drawn many times.
        If you give it the same filename twice, even at different locations
        and sizes, it will reuse the first occurrence, resulting in a saving
        in file size and generation time.  If you use ImageReader objects,
        it tests whether the image content has changed before deciding
        whether to reuse it.

        In general you should use drawImage in preference to drawInlineImage
        unless you have read the PDF Spec and understand the tradeoffs."""        
       
        self._currentPageHasImages = 1

        # first, generate a unique name/signature for the image.  If ANYTHING
        # is different, even the mask, this should be different.
        if isinstance(image,ImageReader):
            rawdata = image.getRGBData()
            smask = image._dataA
            if mask=='auto' and smask:
                mdata = smask.getRGBData()
            else:
                mdata = str(mask)
            if isUnicode(mdata):
                mdata = mdata.encode('utf8')
            name = _digester(rawdata+mdata)
        else:
            #filename, use it
            s = '%s%s' % (image, mask)
            if isUnicode(s):
                s = s.encode('utf-8')
            name = _digester(s)

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
            smask = getattr(imgObj,'_smask',None)
            if smask:   #set up the softmask obtained above
                mRegName = self._doc.getXObjectName(smask.name)
                mImgObj = self._doc.idToObject.get(mRegName, None)
                if not mImgObj:
                    self._setXObjects(smask)
                    imgObj.smask = self._doc.Reference(smask,mRegName)
                else:
                    imgObj.smask = pdfdoc.PDFObjectReference(mRegName)
                del imgObj._smask

        # ensure we have a size, as PDF will make it 1x1 pixel otherwise!
        x,y,width,height,scaled = aspectRatioFix(preserveAspectRatio,anchor,x,y,width,height,imgObj.width,imgObj.height,anchorAtXY)

        # scale and draw
        self.saveState()
        self.translate(x, y)
        self.scale(width, height)
        self._code.append("/%s Do" % regName)
        self.restoreState()
        if showBoundary:
            self.rect(x,y,width,height,stroke=1,fill=0)

        # track what's been used on this page
        self._formsinuse.append(name)

        return (imgObj.width, imgObj.height)

    def _restartAccumulators(self):
        if self._codeStack:
            # restore the saved code
            self._code, self._formsinuse, self._annotationrefs, self._formData,self._colorsUsed, self._shadingUsed = self._codeStack.pop(-1)
        else:
            self._code = []    # ready for more...
            self._psCommandsAfterPage = []
            self._psCommandsBeforePage = []
            self._currentPageHasImages = 1 # for safety...
            self._formsinuse = []
            self._annotationrefs = []
            self._formData = None
            self._colorsUsed = {}
            self._shadingUsed = {}

    def _pushAccumulators(self):
        "when you enter a form, save accumulator info not related to the form for page (if any)"
        saved = (self._code, self._formsinuse, self._annotationrefs, self._formData, self._colorsUsed, self._shadingUsed)
        self._codeStack.append(saved)
        self._code = []    # ready for more...
        self._currentPageHasImages = 1 # for safety...
        self._formsinuse = []
        self._annotationrefs = []
        self._formData = None
        self._colorsUsed = {}
        self._shadingUsed = {}

    def _setExtGState(self, obj):
        obj.ExtGState = self._extgstate.getState()

    def beginForm(self, name, lowerx=0, lowery=0, upperx=None, uppery=None):
        """declare the current graphics stream to be a named form.
           A graphics stream can either be a page or a form, not both.
           Some operations (like bookmarking) are permitted for pages
           but not forms.  The form will not automatically be shown in the
           document but must be explicitly referenced using doForm in pages
           that require the form."""
        self.push_state_stack()
        self.init_graphics_state()
        if self._code or self._formData:
            # save the code that is not in the formf
            self._pushAccumulators()
            #self._codeStack.append(self._code)
            #self._code = []
        self._formData = (name, lowerx, lowery, upperx, uppery)
        self._doc.inForm()
        #self._inForm0()

    def endForm(self,**extra_attributes):
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
        for k, v in extra_attributes.items():
            setattr(form,k,v)
        self._setColorSpace(form)
        self._setExtGState(form)
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
        if isUnicode(command):
            rawName = 'PS' + hashlib.md5(command.encode('utf-8')).hexdigest()
        else:
            rawName = 'PS' + hashlib.md5(command).hexdigest()
        regName = self._doc.getXObjectName(rawName)
        psObj = self._doc.idToObject.get(regName, None)
        if not psObj:
            #first use of this chunk of Postscript, make an object
            psObj = pdfdoc.PDFPostScriptXObject(command + '\n')
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
        bw = self._getCmShift()
        if bw:
            rect = rect[0]+bw,rect[1]+bw,rect[2]+bw,rect[3]+bw
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

    def highlightAnnotation(self, contents, Rect, QuadPoints=None, Color=[0.83, 0.89, 0.95], addtopage=1,
                            name=None, relative=0, **kw):
        """
        Allows adding of a highlighted annotation.

        Rect: Mouseover area to show contents of annotation
        QuadPoints: List of four x/y points [TOP-LEFT, TOP-RIGHT, BOTTOM-LEFT, BOTTOM-RIGHT]
          These points outline the areas to highlight.
          You can have multiple groups of four to allow multiple highlighted areas.
          Is in the format [x1, y1, x2, y2, x3, y3, x4, y4, x1, y1, x2, y2, x3, y3, x4, y4] etc
          QuadPoints defaults to be area inside of passed in Rect
        Color: The color of the highlighting.
        """
        Rect = self._absRect(Rect, relative)
        if not QuadPoints:
            QuadPoints = pdfdoc.rect_to_quad(Rect)
        self._addAnnotation(pdfdoc.HighlightAnnotation(Rect, contents, QuadPoints, Color, **kw), name, addtopage)

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

    def linkRect(self, contents, destinationname, Rect=None, addtopage=1, name=None, relative=1,
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
        s = self._doc.GetPDFData(self)
        if isUnicode(s):
            s = s.encode('utf-8')
        return s

    def setPageSize(self, size):
        """accepts a 2-tuple in points for paper size for this
        and subsequent pages"""
        self._pagesize = size
        self._make_preamble()

    def setCropBox(self, size, name='crop'):
        """accepts a 2-tuple in points for name+'Box' size for this and subsequent pages"""
        name = name.lower()
        if name.endswith('box'): name = name[:-3]
        if name not in ('crop','art','trim','bleed'):
            raise ValueError('unknown box name: %r' % name)
        setattr(self,'_%sBox' % name, size)

    def setTrimBox(self,size):
        self.setCropBox(size,name='trim')

    def setArtBox(self,size):
        self.setCropBox(size,name='art')

    def setBleedBox(self,size):
        self.setCropBox(size,name='bleed')

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
           Reset the matrix! This should be used usually as follows::
           
              canv.saveState()
              canv.resetTransforms()
              #...draw some stuff in default space coords...
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
        #How can Python track this?
        if ENABLE_TRACKING:
            a0,b0,c0,d0,e0,f0 = self._currentMatrix
            self._currentMatrix = (a0*a+c0*b,    b0*a+d0*b,
                                   a0*c+c0*d,    b0*c+d0*d,
                                   a0*e+c0*f+e0, b0*e+d0*f+f0)
        if self._code and self._code[-1][-3:]==' cm':
            L = self._code[-1].split()
            a0, b0, c0, d0, e0, f0 = list(map(float,L[-7:-1]))
            s = len(L)>7 and join(L)+ ' %s cm' or '%s cm'
            self._code[-1] = s % fp_str(a0*a+c0*b,b0*a+d0*b,a0*c+c0*d,b0*c+d0*d,a0*e+c0*f+e0,b0*e+d0*f+f0)
        else:
            self._code.append('%s cm' % fp_str(a,b,c,d,e,f))

    def absolutePosition(self, x, y):
        """return the absolute position of x,y in user space w.r.t. default user space"""
        if not ENABLE_TRACKING:
            raise ValueError("tracking not enabled! (canvas.ENABLE_TRACKING=0)")
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
           for example for the figure::
           
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

    def cross(self, x, y, size=5, gap=1, text=None, strokeColor=None, strokeWidth=None, fontSize=3):
        size *= 0.5
        gap *= 0.5
        crosshairs = [(x,y-size,x,y-gap),(x,y+gap,x,y+size), (x-size,y,x-gap,y),(x+gap,y,x+size,y)]
        self.saveState()
        if strokeColor:
            self.setStrokeColor(strokeColor)
            if text:
                self.setFillColor(strokeColor)
        if strokeWidth:
            self.setLineWidth(strokeWidth)
        self.lines(crosshairs)
        if text:
            if fontSize is not None: self.setFontSize(fontSize)
            self.drawRightString(x-size, y, text)
        self.restoreState()

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
        These should have x1<x2 and y1<y2."""
        pathobject.PDFPathObject(code=self._code).arc(x1,y1,x2,y2,startAng,extent)
        self._strokeAndFill(1,0)

    #--------now the shape drawing methods-----------------------
    def rect(self, x, y, width, height, stroke=1, fill=0):
        "draws a rectangle with lower left corner at (x,y) and width and height as given."
        self._code.append('n %s re ' % fp_str(x, y, width, height)
                          + PATH_OPS[stroke, fill, self._fillMode])

    def ellipse(self, x1, y1, x2, y2, stroke=1, fill=0):
        """Draw an ellipse defined by an enclosing rectangle.

        Note that (x1,y1) and (x2,y2) are the corner points of
        the enclosing rectangle.
        """
        pathobject.PDFPathObject(code=self._code).ellipse(x1, y1, x2-x1, y2-y1)
        self._strokeAndFill(stroke, fill)

    def wedge(self, x1,y1, x2,y2, startAng, extent, stroke=1, fill=0):
        """Like arc, but connects to the centre of the ellipse.
        Most useful for pie charts and PacMan!"""
        p = pathobject.PDFPathObject(code=self._code)
        p.moveTo(0.5*(x1+x2),0.5*(y1+y2))
        p.arcTo(x1,y1,x2,y2,startAng,extent)
        p.close()
        self._strokeAndFill(stroke,fill)

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
        #make the path operators draw into our code
        pathobject.PDFPathObject(code=self._code).roundRect(x, y, width, height, radius)
        self._strokeAndFill(stroke,fill)

    def _addShading(self, shading):
        name = self._doc.addShading(shading)
        self._shadingUsed[name] = name
        return name

    def shade(self, shading):
        name = self._addShading(shading)
        self._code.append('/%s sh' % name)

    def linearGradient(self, x0, y0, x1, y1, colors, positions=None, extend=True):
        #this code contributed by Peter Johnson <johnson.peter@gmail.com>
        from reportlab.pdfbase.pdfdoc import PDFAxialShading
        colorSpace, ncolors = _normalizeColors(colors)
        fcn = _buildColorFunction(ncolors, positions)
        if extend:
            extendStr = "[true true]"
        else:
            extendStr = "[false false]"
        shading = PDFAxialShading(x0, y0, x1, y1, Function=fcn,
                ColorSpace=colorSpace, Extend=extendStr)
        self.shade(shading)

    def radialGradient(self, x, y, radius, colors, positions=None, extend=True):
        #this code contributed by Peter Johnson <johnson.peter@gmail.com>
        from reportlab.pdfbase.pdfdoc import PDFRadialShading
        colorSpace, ncolors = _normalizeColors(colors)
        fcn = _buildColorFunction(ncolors, positions)
        if extend:
            extendStr = "[true true]"
        else:
            extendStr = "[false false]"
        shading = PDFRadialShading(x, y, 0.0, x, y, radius, Function=fcn,
                ColorSpace=colorSpace, Extend=extendStr)
        self.shade(shading)

        ##################################################
        #
        #  Text methods
        #
        # As with graphics, a separate object ensures that
        # everything is bracketed between  text operators.
        # The methods below are a high-level convenience.
        # use PDFTextObject for multi-line text.
        ##################################################

    def drawString(self, x, y, text, mode=None, charSpace=0, direction=None, wordSpace=None):
        """Draws a string in the current text styles."""
        text = asUnicode(text)
        #we could inline this for speed if needed
        t = self.beginText(x, y, direction=direction)
        if mode is not None: t.setTextRenderMode(mode)
        if charSpace: t.setCharSpace(charSpace)
        if wordSpace: t.setWordSpace(wordSpace)
        t.textLine(text)
        if charSpace: t.setCharSpace(0)
        if wordSpace: t.setWordSpace(0)
        if mode is not None: t.setTextRenderMode(0)
        self.drawText(t)

    def drawRightString(self, x, y, text, mode=None, charSpace=0, direction=None, wordSpace=None):
        """Draws a string right-aligned with the x coordinate"""
        if not isinstance(text, str):
            text = text.decode('utf-8')
        width = self.stringWidth(text, self._fontname, self._fontsize)
        if charSpace: width += (len(text)-1)*charSpace
        if wordSpace: width += (text.count(u' ')+text.count(u'\xa0')-1)*wordSpace
        t = self.beginText(x - width, y, direction=direction)
        if mode is not None: t.setTextRenderMode(mode)
        if charSpace: t.setCharSpace(charSpace)
        if wordSpace: t.setWordSpace(wordSpace)
        t.textLine(text)
        if charSpace: t.setCharSpace(0)
        if wordSpace: t.setWordSpace(0)
        if mode is not None: t.setTextRenderMode(0)
        self.drawText(t)

    def drawCentredString(self, x, y, text, mode=None, charSpace=0, direction=None, wordSpace=None):
        """Draws a string centred on the x coordinate. 
        
        We're British, dammit, and proud of our spelling!"""
        if not isinstance(text, str):
            text = text.decode('utf-8')
        width = self.stringWidth(text, self._fontname, self._fontsize)
        if charSpace: width += (len(text)-1)*charSpace
        if wordSpace: width += (text.count(u' ')+text.count(u'\xa0')-1)*wordSpace
        t = self.beginText(x - 0.5*width, y, direction=direction)
        if mode is not None: t.setTextRenderMode(mode)
        if charSpace: t.setCharSpace(charSpace)
        if wordSpace: t.setWordSpace(wordSpace)
        t.textLine(text)
        if charSpace: t.setCharSpace(0)
        if wordSpace: t.setWordSpace(0)
        if mode is not None: t.setTextRenderMode(0)
        self.drawText(t)

    def drawAlignedString(self, x, y, text, pivotChar=rl_config.decimalSymbol, mode=None, charSpace=0, direction=None, wordSpace=None):
        """Draws a string aligned on the first '.' (or other pivot character).

        The centre position of the pivot character will be used as x.
        So, you could draw a straight line down through all the decimals in a
        column of numbers, and anything without a decimal should be
        optically aligned with those that have.

        There is one special rule to help with accounting formatting.  Here's
        how normal numbers should be aligned on the 'dot'. Look at the
        LAST two::
        
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

            self.drawRightString(x-0.5*pivW, y, leftText, mode=mode, charSpace=charSpace,
                    direction=direction, wordSpace=wordSpace)
            self.drawString(x-0.5*pivW, y, rightText, mode=mode, charSpace=charSpace,
                    direction=direction, wordSpace=wordSpace)

        else:
            #normal case
            leftText = parts[0]
            self.drawRightString(x-0.5*pivW, y, leftText, mode=mode, charSpace=charSpace,
                    direction=direction, wordSpace=wordSpace)
            if len(parts) > 1:
                rightText = pivotChar + parts[1]
                self.drawString(x-0.5*pivW, y, rightText, mode=mode, charSpace=charSpace,
                        direction=direction, wordSpace=wordSpace)

    def getAvailableFonts(self):
        """Returns the list of PostScript font names available.

        Standard set now, but may grow in future with font embedding."""
        fontnames = self._doc.getAvailableFonts()
        return fontnames

    def listLoadedFonts0(self):
        "Convenience function to list all loaded fonts"
        names = list(pdfmetrics.widths.keys())
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
        if not font._dynamicFont:
            if font.face.builtIn or not getattr(self,'_drawTextAsPath',False):
                pdffontname = self._doc.getInternalFontName(psfontname)
                self._code.append('BT %s %s Tf %s TL ET' % (pdffontname, fp_str(size), fp_str(leading)))

    def setFontSize(self, size=None, leading=None):
        '''Sets font size or leading without knowing the font face'''
        if size is None: size = self._fontsize
        if leading is None: leading = self._leading
        self.setFont(self._fontname, size, leading)

    def stringWidth(self, text, fontName=None, fontSize=None):
        "gets width of a string in the given font and size"
        return pdfmetrics.stringWidth(text, fontName or self._fontname,
                                    (fontSize,self._fontsize)[fontSize is None])

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
        reason = ''
        if isinstance(array,(int,float)):
            array = (array, phase)
            phase = 0
        elif not isSeq(array):
            reason = 'array should be a sequence of numbers or a number'
        bad = [_ for _ in array if not isinstance(_,(int,float)) or _ < 0]
        if bad or not isinstance(phase,(int,float)) or phase<0:
            reason = 'array & phase should be non-negative numbers'
        elif array and sum(array)<=0:
            reason = 'dash cycle should be larger than zero'
        if reason:
            raise ValueError('setDash: array=%r phase=%r\n%s' % (array, phase, reason))
        self._code.append('[%s] %s d' % (fp_str(array), phase))

    # path stuff - the separate path object builds it

    def beginPath(self):
        """Returns a fresh path object.  Paths are used to draw
        complex figures.  The object returned follows the protocol
        for a pathobject.PDFPathObject instance"""
        return pathobject.PDFPathObject()

    def drawPath(self, aPath, stroke=1, fill=0, fillMode=None):
        "Draw the path object in the mode indicated"
        if fillMode is None:
            fillMode = getattr(aPath,'_fillMode',self._fillMode)
        self._code.append(str(aPath.getCode()))
        self._strokeAndFill(stroke,fill,fillMode)

    def _strokeAndFill(self,stroke,fill,fillMode=None):
        self._code.append(PATH_OPS[stroke, fill, fillMode if fillMode is not None else self._fillMode])

    def clipPath(self, aPath, stroke=1, fill=0, fillMode=None):
        "clip as well as drawing"
        if fillMode is None:
            fillMode = getattr(aPath,'_fillMode',self._fillMode)
        gc = aPath.getCode(); pathops = PATH_OPS[stroke, fill, fillMode]
        clip = (fillMode == FILL_EVEN_ODD and ' W* ' or ' W ')
        item = "%s%s%s" % (gc, clip, pathops) # ensure string conversion
        self._code.append(item)
        #self._code.append(  aPath.getCode()
        #                   + (self._fillMode == FILL_EVEN_ODD and ' W* ' or ' W ')
        #                   + PATH_OPS[stroke,fill,self._fillMode])

    def beginText(self, x=0, y=0, direction=None):
        """Returns a fresh text object.  Text objects are used
           to add large amounts of text.  See PDFTextObject"""
        return PDFTextObject(self, x, y, direction=direction)

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
        argument permitted, and here are the allowed values::
        
            direction_arg = [0,90,180,270]
            dimension_arg = ['H', 'V']
            motion_arg = ['I','O'] (start at inside or outside)
        
        This table says which ones take which arguments::

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
            raise pdfdoc.PDFError(' directions allowed are 0,90,180,270')

        if dimension in ['H', 'V']:
            dimension_arg = ('Dm', '/' + dimension)
        else:
            raise pdfdoc.PDFError('dimension values allowed are H and V')

        if motion in ['I','O']:
            motion_arg = ('M', '/' + motion)
        else:
            raise pdfdoc.PDFError('motion values allowed are I and O')

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
            raise pdfdoc.PDFError('Unknown Effect Name "%s"' % effectname)

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

    def setViewerPreference(self,pref,value):
        '''set one of the allowed enbtries in the documents viewer preferences'''
        catalog = self._doc.Catalog
        VP = getattr(catalog,'ViewerPreferences',None)
        if VP is None:
            from reportlab.pdfbase.pdfdoc import ViewerPreferencesPDFDictionary
            VP = catalog.ViewerPreferences = ViewerPreferencesPDFDictionary()
        VP[pref] = value

    def getViewerPreference(self,pref):
        '''you'll get an error here if none have been set'''
        return self._doc.Catalog.ViewerPreferences[pref]

    def delViewerPreference(self,pref):
        '''you'll get an error here if none have been set'''
        del self._doc.Catalog.ViewerPreferences[pref]

    def setCatalogEntry(self,key,value):
        from reportlab.pdfbase.pdfdoc import PDFDictionary, PDFArray, PDFString
        if isStr(value):
            value = PDFString(value)
        elif isinstance(value,(list,tuple)):
            value = PDFArray(value)
        elif isinstance(value,dict):
            value = PDFDictionary(value)
        setattr(self._doc.Catalog,key,value)

    def getCatalogEntry(self,key):
        return getattr(self._doc.Catalog,key)

    def delCatalogEntry(self,key):
        '''you'll get an error here if it's not been set'''
        delattr(self._doc.Catalog,key)

    def addPageLabel(self, pageNum, style=None, start=None, prefix=None):
        '''add a PDFPageLabel for pageNum'''
        catalog = self._doc.Catalog
        PL = getattr(catalog,'PageLabels',None)
        if PL is None:
            from reportlab.pdfbase.pdfdoc import PDFPageLabels
            PL = catalog.PageLabels = PDFPageLabels()

        from reportlab.pdfbase.pdfdoc import PDFPageLabel
        PL.addPageLabel(pageNum,PDFPageLabel(style,start,prefix))

    @property
    def acroForm(self):
        "get form from canvas, create the form if needed"
        try:
            return self.AcroForm
        except AttributeError:
            from reportlab.pdfbase.acroform import AcroForm
            self._doc._catalog.AcroForm = self.AcroForm = AcroForm(self)
            return self.AcroForm

    @property
    def drawBoundary(self):
        if not hasattr(self,'_drawBoundary'):
            from reportlab.platypus import Frame
            self._drawBoundary = lambda sb,x,y,w,h: Frame._drawBoundary(self,sb,x,y,w,h)
        return self._drawBoundary

if __name__ == '__main__':
    print('For test scripts, look in tests')
