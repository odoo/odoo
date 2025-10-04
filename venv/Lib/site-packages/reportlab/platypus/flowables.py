#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/platypus/flowables.py
__version__='3.3.0'
__doc__="""
A flowable is a "floating element" in a document whose exact position is determined by the
other elements that precede it, such as a paragraph, a diagram interspersed between paragraphs,
a section header, etcetera.  Examples of non-flowables include page numbering annotations,
headers, footers, fixed diagrams or logos, among others.

Flowables are defined here as objects which know how to determine their size and which
can draw themselves onto a page with respect to a relative "origin" position determined
at a higher level. The object's draw() method should assume that (0,0) corresponds to the
bottom left corner of the enclosing rectangle that will contain the object. The attributes
vAlign and hAlign may be used by 'packers' as hints as to how the object should be placed.

Some Flowables also know how to "split themselves".  For example a
long paragraph might split itself between one page and the next.

Packers should set the canv attribute during wrap, split & draw operations to allow
the flowable to work out sizes etc in the proper context.

The "text" of a document usually consists mainly of a sequence of flowables which
flow into a document from top to bottom (with column and page breaks controlled by
higher level components).
"""
import os
from copy import deepcopy, copy
from reportlab.lib.colors import gray, lightgrey
from reportlab.lib.rl_accel import fp_str
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.styles import _baseFontName
from reportlab.lib.utils import strTypes, rl_safe_exec
from reportlab.lib.abag import ABag
from reportlab.pdfbase import pdfutils
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.rl_config import _FUZZ, overlapAttachedSpace, ignoreContainerActions, listWrapOnFakeWidth

__all__ = '''AnchorFlowable BalancedColumns BulletDrawer CallerMacro CondPageBreak DDIndenter DocAssert
        DocAssign DocExec DocIf DocPara DocWhile FailOnDraw FailOnWrap Flowable FrameBG FrameSplitter
        HRFlowable Image ImageAndFlowables KeepInFrame KeepTogether LIIndenter ListFlowable ListItem
        Macro NullDraw PTOContainer PageBreak PageBreakIfNotEmpty ParagraphAndImage Preformatted
        SetPageTopFlowables SetTopFlowables SlowPageBreak Spacer TopPadder TraceInfo UseUpSpace XBox
        splitLine splitLines'''.split()

class TraceInfo:
    "Holder for info about where an object originated"
    def __init__(self):
        self.srcFile = '(unknown)'
        self.startLineNo = -1
        self.startLinePos = -1
        self.endLineNo = -1
        self.endLinePos = -1

#############################################################
#   Flowable Objects - a base class and a few examples.
#   One is just a box to get some metrics.  We also have
#   a paragraph, an image and a special 'page break'
#   object which fills the space.
#############################################################
class Flowable:
    """Abstract base class for things to be drawn.  Key concepts:

    1. It knows its size
    2. It draws in its own coordinate system (this requires the
       base API to provide a translate() function.

    """
    _fixedWidth = 0         #assume wrap results depend on arguments?
    _fixedHeight = 0

    def __init__(self):
        self.width = 0
        self.height = 0
        self.wrapped = 0

        #these are hints to packers/frames as to how the floable should be positioned
        self.hAlign = 'LEFT'    #CENTER/CENTRE or RIGHT
        self.vAlign = 'BOTTOM'  #MIDDLE or TOP

        #optional holder for trace info
        self._traceInfo = None
        self._showBoundary = None

        #many flowables handle text and must be processed in the
        #absence of a canvas.  tagging them with their encoding
        #helps us to get conversions right.  Use Python codec names.
        self.encoding = None

    def _drawOn(self,canv):
        '''ensure canv is set on and then draw'''
        self.canv = canv
        self.draw()#this is the bit you overload
        del self.canv

    def _hAlignAdjust(self,x,sW=0):
        if sW and hasattr(self,'hAlign'):
            a = self.hAlign
            if a in ('CENTER','CENTRE', TA_CENTER):
                x += 0.5*sW
            elif a in ('RIGHT',TA_RIGHT):
                x += sW
            elif a not in ('LEFT',TA_LEFT):
                raise ValueError("Bad hAlign value "+str(a))
        return x

    def drawOn(self, canvas, x, y, _sW=0):
        "Tell it to draw itself on the canvas.  Do not override"
        x = self._hAlignAdjust(x,_sW)
        canvas.saveState()
        canvas.translate(x, y)
        self._drawOn(canvas)
        if hasattr(self, '_showBoundary') and self._showBoundary:
            #diagnostic tool support
            canvas.setStrokeColor(gray)
            canvas.rect(0,0,self.width, self.height)
        canvas.restoreState()

    def wrapOn(self, canv, aW, aH):
        '''intended for use by packers allows setting the canvas on
        during the actual wrap'''
        self.canv = canv
        w, h = self.wrap(aW,aH)
        del self.canv
        return w, h

    def wrap(self, availWidth, availHeight):
        """This will be called by the enclosing frame before objects
        are asked their size, drawn or whatever.  It returns the
        size actually used."""
        return (self.width, self.height)

    def minWidth(self):
        """This should return the minimum required width"""
        return getattr(self,'_minWidth',self.width)

    def splitOn(self, canv, aW, aH):
        '''intended for use by packers allows setting the canvas on
        during the actual split'''
        self.canv = canv
        S = self.split(aW,aH)
        del self.canv
        return S

    def split(self, availWidth, availheight):
        """This will be called by more sophisticated frames when
        wrap fails. Stupid flowables should return []. Clever flowables
        should split themselves and return a list of flowables.
        If they decide that nothing useful can be fitted in the
        available space (e.g. if you have a table and not enough
        space for the first row), also return []"""
        return []

    def getKeepWithNext(self):
        """returns boolean determining whether the next flowable should stay with this one"""
        if hasattr(self,'keepWithNext'): return self.keepWithNext
        elif hasattr(self,'style') and hasattr(self.style,'keepWithNext'): return self.style.keepWithNext
        else: return 0

    def getSpaceAfter(self):
        """returns how much space should follow this item if another item follows on the same page."""
        if hasattr(self,'spaceAfter'): return self.spaceAfter
        elif hasattr(self,'style') and hasattr(self.style,'spaceAfter'): return self.style.spaceAfter
        else: return 0

    def getSpaceBefore(self):
        """returns how much space should precede this item if another item precedess on the same page."""
        if hasattr(self,'spaceBefore'): return self.spaceBefore
        elif hasattr(self,'style') and hasattr(self.style,'spaceBefore'): return self.style.spaceBefore
        else: return 0

    def isIndexing(self):
        """Hook for IndexingFlowables - things which have cross references"""
        return 0

    def identity(self, maxLen=None):
        '''
        This method should attempt to return a string that can be used to identify
        a particular flowable uniquely. The result can then be used for debugging
        and or error printouts
        '''
        if hasattr(self, 'getPlainText'):
            r = self.getPlainText(identify=1)
        elif hasattr(self, 'text'):
            r = str(self.text)
        else:
            r = '...'
        if r and maxLen:
            r = r[:maxLen]
        return "<%s at %s%s>%s" % (self.__class__.__name__, hex(id(self)), self._frameName(), r)

    @property
    def _doctemplate(self):
        return getattr(getattr(self,'canv',None),'_doctemplate',None)

    def _doctemplateAttr(self,a):
        return getattr(self._doctemplate,a,None)

    def _frameName(self):
        f = getattr(self,'_frame',None)
        if not f: f = self._doctemplateAttr('frame')
        if f and f.id: return ' frame=%s' % f.id
        return ''

class XBox(Flowable):
    """Example flowable - a box with an x through it and a caption.
    This has a known size, so does not need to respond to wrap()."""
    def __init__(self, width, height, text = 'A Box'):
        Flowable.__init__(self)
        self.width = width
        self.height = height
        self.text = text

    def __repr__(self):
        return "XBox(w=%s, h=%s, t=%s)" % (self.width, self.height, self.text)

    def draw(self):
        self.canv.rect(0, 0, self.width, self.height)
        self.canv.line(0, 0, self.width, self.height)
        self.canv.line(0, self.height, self.width, 0)

        #centre the text
        self.canv.setFont(_baseFontName,12)
        self.canv.drawCentredString(0.5*self.width, 0.5*self.height, self.text)

def _trimEmptyLines(lines):
    #don't want the first or last to be empty
    while len(lines) and lines[0].strip() == '':
        lines = lines[1:]
    while len(lines) and lines[-1].strip() == '':
        lines = lines[:-1]
    return lines

def _dedenter(text,dedent=0):
    '''
    tidy up text - carefully, it is probably code.  If people want to
    indent code within a source script, you can supply an arg to dedent
    and it will chop off that many character, otherwise it leaves
    left edge intact.
    '''
    lines = text.split('\n')
    if dedent>0:
        templines = _trimEmptyLines(lines)
        lines = []
        for line in templines:
            line = line[dedent:].rstrip()
            lines.append(line)
    else:
        lines = _trimEmptyLines(lines)

    return lines


SPLIT_CHARS = "[{( ,.;:/\\-"

def splitLines(lines, maximum_length, split_characters, new_line_characters):
    if split_characters is None:
        split_characters = SPLIT_CHARS
    if new_line_characters is None:
        new_line_characters = ""
    # Return a table of lines
    lines_splitted = []
    for line in lines:
        if len(line) > maximum_length:
            splitLine(line, lines_splitted, maximum_length, \
            split_characters, new_line_characters)
        else:
            lines_splitted.append(line)
    return lines_splitted

def splitLine(line_to_split, lines_splitted, maximum_length, \
split_characters, new_line_characters):
    # Used to implement the characters added
    #at the beginning of each new line created
    first_line = True

    # Check if the text can be splitted
    while line_to_split and len(line_to_split)>0:

        # Index of the character where we can split
        split_index = 0

        # Check if the line length still exceeds the maximum length
        if len(line_to_split) <= maximum_length:
            # Return the remaining of the line
            split_index = len(line_to_split)
        else:
            # Iterate for each character of the line
            for line_index in range(maximum_length):
                # Check if the character is in the list
                # of allowed characters to split on
                if line_to_split[line_index] in split_characters:
                    split_index = line_index + 1

        # If the end of the line was reached
        # with no character to split on
        if split_index==0:
            split_index = line_index + 1

        if first_line:
            lines_splitted.append(line_to_split[0:split_index])
            first_line = False
            maximum_length -= len(new_line_characters)
        else:
            lines_splitted.append(new_line_characters + \
            line_to_split[0:split_index])

        # Remaining text to split
        line_to_split = line_to_split[split_index:]

class Preformatted(Flowable):
    """This is like the HTML <PRE> tag.
    It attempts to display text exactly as you typed it in a fixed width "typewriter" font.
    By default the line breaks are exactly where you put them, and it will not be wrapped.
    You can optionally define a maximum line length and the code will be wrapped; and
    extra characters to be inserted at the beginning of each wrapped line (e.g. '> ').
    """
    def __init__(self, text, style, bulletText = None, dedent=0, maxLineLength=None, splitChars=None, newLineChars=""):
        """text is the text to display. If dedent is set then common leading space
        will be chopped off the front (for example if the entire text is indented
        6 spaces or more then each line will have 6 spaces removed from the front).
        """
        self.style = style
        self.bulletText = bulletText
        self.lines = _dedenter(text,dedent)
        if text and maxLineLength:
            self.lines = splitLines(
                                self.lines,
                                maxLineLength,
                                splitChars,
                                newLineChars
                        )

    def __repr__(self):
        bT = self.bulletText
        H = "Preformatted("
        if bT is not None:
            H = "Preformatted(bulletText=%s," % repr(bT)
        return "%s'''\\ \n%s''')" % (H, '\n'.join(self.lines))

    def wrap(self, availWidth, availHeight):
        self.width = availWidth
        self.height = self.style.leading*len(self.lines)
        return (self.width, self.height)

    def minWidth(self):
        style = self.style
        fontSize = style.fontSize
        fontName = style.fontName
        return max([stringWidth(line,fontName,fontSize) for line in self.lines])

    def split(self, availWidth, availHeight):
        #returns two Preformatted objects

        #not sure why they can be called with a negative height
        if availHeight < self.style.leading:
            return []

        linesThatFit = int(availHeight * 1.0 / self.style.leading)

        text1 = '\n'.join(self.lines[0:linesThatFit])
        text2 = '\n'.join(self.lines[linesThatFit:])
        style = self.style
        if style.firstLineIndent != 0:
            style = deepcopy(style)
            style.firstLineIndent = 0
        return [Preformatted(text1, self.style), Preformatted(text2, style)]

    def draw(self):
        #call another method for historical reasons.  Besides, I
        #suspect I will be playing with alternate drawing routines
        #so not doing it here makes it easier to switch.

        cur_x = self.style.leftIndent
        cur_y = self.height - self.style.fontSize
        self.canv.addLiteral('%PreformattedPara')
        if self.style.textColor:
            self.canv.setFillColor(self.style.textColor)
        tx = self.canv.beginText(cur_x, cur_y)
        #set up the font etc.
        tx.setFont( self.style.fontName,
                    self.style.fontSize,
                    self.style.leading)

        for text in self.lines:
            tx.textLine(text)
        self.canv.drawText(tx)

class Image(Flowable):
    """an image (digital picture).  Formats supported by PIL/Java 1.4 (the Python/Java Imaging Library
       are supported. Images as flowables may be aligned horizontally in the
       frame with the hAlign parameter - accepted values are 'CENTER',
       'LEFT' or 'RIGHT' with 'CENTER' being the default.
       We allow for two kinds of lazyness to allow for many images in a document
       which could lead to file handle starvation.
       lazy=1 don't open image until required.
       lazy=2 open image when required then shut it.
    """
    _fixedWidth = 1
    _fixedHeight = 1
    def __init__(self, filename, width=None, height=None, kind='direct',
                 mask="auto", lazy=1, hAlign='CENTER', useDPI=False):
        """If size to draw at not specified, get it from the image."""
        self.hAlign = hAlign
        self._mask = mask
        fp = hasattr(filename,'read')
        self._drawing = None
        if fp:
            self._file = filename
            self.filename = repr(filename)
        elif hasattr(filename,'_renderPy'):
            self._drawing = filename
            self.filename=repr(filename)
            self._file = None
            self._img = None
            fp = True
        else:
            self._file = self.filename = filename
        self._dpi = useDPI
        if not fp and os.path.splitext(filename)[1] in ['.jpg', '.JPG', '.jpeg', '.JPEG']:
            # if it is a JPEG, will be inlined within the file -
            # but we still need to know its size now
            from reportlab.lib.utils import open_for_read
            f = open_for_read(filename, 'b')
            try:
                try:
                    info = pdfutils.readJPEGInfo(f)
                except:
                    #couldn't read as a JPEG, try like normal
                    self._setup(width,height,kind,lazy)
                    return
            finally:
                f.close()
            self.imageWidth = info[0]
            self.imageHeight = info[1]
            if useDPI:
                self._dpi = info[3]
            self._img = None
            self._setup(width,height,kind,0)
        elif fp:
            self._setup(width,height,kind,0)
        else:
            self._setup(width,height,kind,lazy)

    def _dpiAdjust(self):
        dpi = self._dpi
        if dpi:
            if dpi[0]!=72: self.imageWidth *= 72.0 / dpi[0]
            if dpi[1]!=72: self.imageHeight *= 72.0 / dpi[1]

    def _setup(self,width,height,kind,lazy):
        self._lazy = lazy
        self._width = width
        self._height = height
        self._kind = kind
        if lazy<=0: self._setup_inner()

    def _setup_inner(self):
        width = self._width
        height = self._height
        kind = self._kind
        img = self._img
        if img:
            self.imageWidth, self.imageHeight = img.getSize()
            if self._dpi and hasattr(img,'_image'):
                self._dpi = img._image.info.get('dpi',(72,72))
        elif self._drawing:
            self.imageWidth, self.imageHeight = self._drawing.width,self._drawing.height
            self._dpi = False
        self._dpiAdjust()
        if self._lazy>=2: del self._img
        if kind in ['direct','absolute']:
            self.drawWidth = width or self.imageWidth
            self.drawHeight = height or self.imageHeight
        elif kind in ['percentage','%']:
            self.drawWidth = self.imageWidth*width*0.01
            self.drawHeight = self.imageHeight*height*0.01
        elif kind in ['bound','proportional']:
            factor = min(float(width)/self.imageWidth,float(height)/self.imageHeight)
            self.drawWidth = self.imageWidth*factor
            self.drawHeight = self.imageHeight*factor

    def _restrictSize(self,aW,aH):
        if self.drawWidth>aW+_FUZZ or self.drawHeight>aH+_FUZZ:
            self._oldDrawSize = self.drawWidth, self.drawHeight
            factor = min(float(aW)/self.drawWidth,float(aH)/self.drawHeight)
            self.drawWidth *= factor
            self.drawHeight *= factor
        return self.drawWidth, self.drawHeight

    def _unRestrictSize(self):
        dwh = getattr(self,'_oldDrawSize',None)
        if dwh:
            self.drawWidth, self.drawHeight = dwh

    def __getattr__(self,a):
        if a=='_img':
            from reportlab.lib.utils import ImageReader  #this may raise an error
            self._img = ImageReader(self._file)
            if not isinstance(self._file,strTypes):
                self._file = None
                if self._lazy>=2: self._lazy = 1    #here we're assuming we cannot read again
            return self._img
        elif a in ('drawWidth','drawHeight','imageWidth','imageHeight'):
            self._setup_inner()
            return self.__dict__[a]
        raise AttributeError("<Image @ 0x%x>.%s" % (id(self),a))

    def wrap(self, availWidth, availHeight):
        #the caller may decide it does not fit.
        return self.drawWidth, self.drawHeight

    def draw(self):
        dx = getattr(self,'_offs_x',0)
        dy = getattr(self,'_offs_y',0)
        d = self._drawing
        if d:
            sx = self.drawWidth / float(self.imageWidth)
            sy = self.drawHeight / float(self.imageHeight)
            otrans = d.transform
            try:
                d.scale(sx,sy)
                d.drawOn(self.canv,dx,dy)
            finally:
                d.transform = otrans
        else:
            lazy = self._lazy
            if lazy>=2: self._lazy = 1
            self.canv.drawImage(    self._img or self.filename,
                                    dx,
                                    dy,
                                    self.drawWidth,
                                    self.drawHeight,
                                    mask=self._mask,
                                    )
            if lazy>=2:
                self._img = self._file = None
                self._lazy = lazy

    def identity(self,maxLen=None):
        r = Flowable.identity(self,maxLen)
        if r[-4:]=='>...' and isinstance(self.filename,str):
            r = "%s filename=%s>" % (r[:-4],self.filename)
        return r

class NullDraw(Flowable):
    def draw(self):
        pass

class Spacer(NullDraw):
    """A spacer just takes up space and doesn't draw anything - it guarantees
       a gap between objects."""
    _fixedWidth = 1
    _fixedHeight = 1
    def __init__(self, width, height, isGlue=False):
        self.width = width
        if isGlue:
            self.height = 1e-4
            self.spacebefore = height
        self.height = height

    def __repr__(self):
        return "%s(%s, %s)" % (self.__class__.__name__,self.width, self.height)

class UseUpSpace(NullDraw):
    def __init__(self):
        pass

    def __repr__(self):
        return "%s()" % self.__class__.__name__

    def wrap(self, availWidth, availHeight):
        self.width = availWidth
        self.height = availHeight
        return (availWidth,availHeight-1e-8)  #step back a point

class PageBreak(UseUpSpace):
    locChanger=1
    """Move on to the next page in the document.
       This works by consuming all remaining space in the frame!"""
    def __init__(self,nextTemplate=None):
        self.nextTemplate = nextTemplate

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__,repr(self.nextTemplate) if self.nextTemplate else '')

class SlowPageBreak(PageBreak):
    pass

class PageBreakIfNotEmpty(PageBreak):
    pass

class CondPageBreak(Spacer):
    locChanger=1
    """use up a frame if not enough vertical space effectively CondFrameBreak"""
    def __init__(self, height):
        self.height = height

    def __repr__(self):
        return "CondPageBreak(%s)" %(self.height,)

    def wrap(self, availWidth, availHeight):
        if availHeight<self.height:
            f = self._doctemplateAttr('frame')
            if not f: return availWidth, availHeight
            from reportlab.platypus.doctemplate import FrameBreak
            f.add_generated_content(FrameBreak)
        return 0, 0

    def identity(self,maxLen=None):
        return repr(self).replace(')',',frame=%s)'%self._frameName())

def _listWrapOn(F,availWidth,canv,mergeSpace=1,obj=None,dims=None,fakeWidth=None):
    '''return max width, required height for a list of flowables F'''
    doct = getattr(canv,'_doctemplate',None)
    cframe = getattr(doct,'frame',None)
    if fakeWidth is None:
        fakeWidth = listWrapOnFakeWidth
    if cframe:
        from reportlab.platypus.doctemplate import _addGeneratedContent, Indenter
        doct_frame = cframe
        cframe = doct.frame = deepcopy(doct_frame)
        cframe._generated_content = None
        del cframe._generated_content
    try:
        W = 0
        H = 0
        pS = 0
        atTop = 1
        F = F[:]
        while F:
            f = F.pop(0)
            if hasattr(f,'frameAction'):
                from reportlab.platypus.doctemplate import Indenter
                if isinstance(f,Indenter):
                    availWidth -= f.left+f.right
                continue
            w,h = f.wrapOn(canv,availWidth,0xfffffff)
            if dims is not None: dims.append((w,h))
            if cframe:
                _addGeneratedContent(F,cframe)
            if (w<=_FUZZ and False) or h<=_FUZZ: continue
            W = max(W,min(w,availWidth) if fakeWidth else w)
            H += h
            if not atTop:
                h = f.getSpaceBefore()
                if mergeSpace:
                    if getattr(f,'_SPACETRANSFER',False):
                        h = pS
                    h = max(h-pS,0)
                H += h
            else:
                if obj is not None: obj._spaceBefore = f.getSpaceBefore()
                atTop = 0
            s = f.getSpaceAfter()
            if getattr(f,'_SPACETRANSFER',False):
                s = pS
            pS = s
            H += pS
        if obj is not None: obj._spaceAfter = pS
        return W, H-pS
    finally:
        if cframe:
            doct.frame = doct_frame

def _flowableSublist(V):
    "if it isn't a list or tuple, wrap it in a list"
    if not isinstance(V,(list,tuple)): V = V is not None and [V] or []
    from reportlab.platypus.doctemplate import LCActionFlowable
    assert not [x for x in V if isinstance(x,LCActionFlowable)],'LCActionFlowables not allowed in sublists'
    return V

class _ContainerSpace:  #Abstract some common container like behaviour
    def getSpaceBefore(self,content=None):
        for c in (self._content if content is None else content):
            if not hasattr(c,'frameAction'):
                return c.getSpaceBefore()
        return 0

    def getSpaceAfter(self,content=None):
        for c in reversed(self._content if content is None else content):
            if not hasattr(c,'frameAction'):
                return c.getSpaceAfter()
        return 0

class KeepTogether(_ContainerSpace,Flowable):
    splitAtTop = False

    def __init__(self,flowables,maxHeight=None):
        if not hasattr(KeepTogether,'NullActionFlowable'):
            #cache these on the class
            from reportlab.platypus.doctemplate import NullActionFlowable
            from reportlab.platypus.doctemplate import FrameBreak
            from reportlab.lib.utils import annotateException
            KeepTogether.NullActionFlowable = NullActionFlowable
            KeepTogether.FrameBreak = FrameBreak
            KeepTogether.annotateException = annotateException

        if not flowables:
            flowables = [self.NullActionFlowable()]
        self._content = _flowableSublist(flowables)
        self._maxHeight = maxHeight

    def __repr__(self):
        f = self._content
        L = list(map(repr,f))
        L = "\n"+"\n".join(L)
        L = L.replace("\n", "\n  ")
        return "%s(%s,maxHeight=%s)" % (self.__class__.__name__,L,self._maxHeight)

    def wrap(self, aW, aH):
        dims = []
        try:
            W,H = _listWrapOn(self._content,aW,self.canv,dims=dims)
        except:
            self.annotateException('\nraised by class %s(%s)@0x%8.8x wrap\n' % (self.__class__.__name__,self.__class__.__module__,id(self)))
        self._H = H
        self._H0 = dims and dims[0][1] or 0
        self._wrapInfo = aW,aH
        return W, 0xffffff  # force a split

    def split(self, aW, aH):
        if getattr(self,'_wrapInfo',None)!=(aW,aH): self.wrap(aW,aH)
        S = self._content[:]
        cf = atTop = getattr(self,'_frame',None)
        if cf:
            atTop = getattr(cf,'_atTop',None)
            cAW = cf._width
            cAH = cf._height
        C0 = self._H>aH and (not self._maxHeight or aH>self._maxHeight)
        C1 = (self._H0>aH) or C0 and atTop
        if C0 or C1:
            fb = False
            panf = self._doctemplateAttr('_peekNextFrame')
            if cf and panf:
                nf = panf()
                nAW = nf._width
                nAH = nf._height
            if C0 and not (self.splitAtTop and atTop):
                fb = not (atTop and cf and nf and cAW>=nAW and cAH>=nAH)
            elif nf and nAW>=cf._width and nAH>=self._H:
                fb = True

            S.insert(0,(self.FrameBreak if fb else self.NullActionFlowable)())
        return S

    def identity(self, maxLen=None):
        msg = "<%s at %s%s> containing :%s" % (self.__class__.__name__,hex(id(self)),self._frameName(),"\n".join([f.identity() for f in self._content]))
        if maxLen:
            return msg[0:maxLen]
        else:
            return msg

class KeepTogetherSplitAtTop(KeepTogether):
    '''
    Same as KeepTogether, but it will split content immediately if it cannot
    fit at the top of a frame.
    '''
    splitAtTop = True

class Macro(Flowable):
    """This is not actually drawn (i.e. it has zero height)
    but is executed when it would fit in the frame.  Allows direct
    access to the canvas through the object 'canvas'"""
    def __init__(self, command):
        self.command = command
    def __repr__(self):
        return "Macro(%s)" % repr(self.command)
    def wrap(self, availWidth, availHeight):
        return (0,0)
    def draw(self):
        rl_safe_exec(self.command, g=None, l={'canvas':self.canv})

def _nullCallable(*args,**kwds):
    pass

class CallerMacro(Flowable):
    '''
    like Macro, but with callable command(s)
    drawCallable(self)
    wrapCallable(self,aW,aH)
    '''
    def __init__(self, drawCallable=None, wrapCallable=None):
        self._drawCallable = drawCallable or _nullCallable
        self._wrapCallable = wrapCallable or _nullCallable
    def __repr__(self):
        return "CallerMacro(%r,%r)" % (self._drawCallable,self._wrapCallable)
    def wrap(self, aW, aH):
        self._wrapCallable(self,aW,aH)
        return (0,0)
    def draw(self):
        self._drawCallable(self)

class ParagraphAndImage(Flowable):
    '''combine a Paragraph and an Image'''
    def __init__(self,P,I,xpad=3,ypad=3,side='right'):
        self.P = P
        self.I = I
        self.xpad = xpad
        self.ypad = ypad
        self._side = side

    def getSpaceBefore(self):
        return max(self.P.getSpaceBefore(),self.I.getSpaceBefore())

    def getSpaceAfter(self):
        return max(self.P.getSpaceAfter(),self.I.getSpaceAfter())

    def wrap(self,availWidth,availHeight):
        wI, hI = self.I.wrap(availWidth,availHeight)
        self.wI = wI
        self.hI = hI
        # work out widths array for breaking
        self.width = availWidth
        P = self.P
        style = P.style
        xpad = self.xpad
        ypad = self.ypad
        leading = style.leading
        leftIndent = style.leftIndent
        later_widths = availWidth - leftIndent - style.rightIndent
        intermediate_widths = later_widths - xpad - wI
        first_line_width = intermediate_widths - style.firstLineIndent
        P.width = 0
        nIW = int((hI+ypad)/(leading*1.0))
        P.blPara = P.breakLines([first_line_width] + nIW*[intermediate_widths]+[later_widths])
        if self._side=='left':
            self._offsets = [wI+xpad]*(1+nIW)+[0]
        P.height = len(P.blPara.lines)*leading
        self.height = max(hI,P.height)
        return (self.width, self.height)

    def split(self,availWidth, availHeight):
        P, wI, hI, ypad = self.P, self.wI, self.hI, self.ypad
        if hI+ypad>availHeight or len(P.frags)<=0: return []
        S = P.split(availWidth,availHeight)
        if not S: return S
        P = self.P = S[0]
        del S[0]
        style = P.style
        P.height = len(self.P.blPara.lines)*style.leading
        self.height = max(hI,P.height)
        return [self]+S

    def draw(self):
        canv = self.canv
        if self._side=='left':
            self.I.drawOn(canv,0,self.height-self.hI-self.ypad)
            self.P._offsets = self._offsets
            try:
                self.P.drawOn(canv,0,0)
            finally:
                del self.P._offsets
        else:
            self.I.drawOn(canv,self.width-self.wI-self.xpad,self.height-self.hI-self.ypad)
            self.P.drawOn(canv,0,0)

class FailOnWrap(NullDraw):
    def wrap(self, availWidth, availHeight):
        raise ValueError("FailOnWrap flowable wrapped and failing as ordered!")

class FailOnDraw(Flowable):
    def wrap(self, availWidth, availHeight):
        return 0,0

    def draw(self):
        raise ValueError("FailOnDraw flowable drawn, and failing as ordered!")

class HRFlowable(Flowable):
    '''Like the hr tag'''
    def __init__(self,
            width="80%",
            thickness=1,
            lineCap='round',
            color=lightgrey,
            spaceBefore=1, spaceAfter=1,
            hAlign='CENTER', vAlign='BOTTOM',
            dash=None):
        Flowable.__init__(self)
        self.width = width
        self.lineWidth = thickness
        self.lineCap=lineCap
        self.spaceBefore = spaceBefore
        self.spaceAfter = spaceAfter
        self.color = color
        self.hAlign = hAlign
        self.vAlign = vAlign
        self.dash = dash

    def __repr__(self):
        return "HRFlowable(width=%s, height=%s)" % (self.width, self.height)

    def wrap(self, availWidth, availHeight):
        w = self.width
        if isinstance(w,strTypes):
            w = w.strip()
            if w.endswith('%'): w = availWidth*float(w[:-1])*0.01
            else: w = float(w)
        w = min(w,availWidth)
        self._width = w
        return w, self.lineWidth

    def draw(self):
        canv = self.canv
        canv.saveState()
        canv.setLineWidth(self.lineWidth)
        canv.setLineCap({'butt':0,'round':1, 'square': 2}[self.lineCap.lower()])
        canv.setStrokeColor(self.color)
        if self.dash: canv.setDash(self.dash)
        canv.line(0, 0, self._width, self.height)
        canv.restoreState()

class _PTOInfo:
    def __init__(self,trailer,header):
        self.trailer = _flowableSublist(trailer)
        self.header = _flowableSublist(header)

def cdeepcopy(obj):
    if hasattr(obj,'deepcopy'):
        return obj.deepcopy()
    else:
        return deepcopy(obj)

class _Container(_ContainerSpace):  #Abstract some common container like behaviour
    def drawOn(self, canv, x, y, _sW=0, scale=1.0, content=None, aW=None):
        '''we simulate being added to a frame'''
        from reportlab.platypus.doctemplate import ActionFlowable, Indenter
        x0 = x
        y0 = y
        pS = 0
        if aW is None: aW = self.width
        aW *= scale
        if content is None:
            content = self._content
        x = self._hAlignAdjust(x,_sW*scale)
        y += self.height*scale
        yt = y
        frame = getattr(self,'_frame',None)
        for c in content:
            if not ignoreContainerActions and isinstance(c,ActionFlowable):
                c.apply(canv._doctemplate)
                continue
            if isinstance(c,Indenter):
                x += c.left*scale
                aW -= (c.left+c.right)*scale
                continue
            w, h = c.wrapOn(canv,aW,0xfffffff)
            if h<_FUZZ and not getattr(c,'_ZEROSIZE',None): continue
            if yt!=y:
                s = c.getSpaceBefore()
                if not getattr(c,'_SPACETRANSFER',False):
                    h += max(s-pS,0)
            y -= h
            s = c.getSpaceAfter()
            if getattr(c,'_SPACETRANSFER',False):
                s = pS
            pS = s
            fbg = getattr(frame,'_frameBGs',None)
            if fbg and fbg[-1].active:
                bg = fbg[-1]
                fbgl = bg.left
                fbgr = bg.right
                bgm = bg.start
                fbw = scale*(frame._width-fbgl-fbgr)
                fbx = x0+scale*(fbgl-frame._leftPadding)
                fbh = y + h + pS
                fby = max(y0,y-pS)
                fbh = max(0,fbh-fby)
                bg.render(canv,frame,fbx,fby,fbw,fbh)
            c._frame = frame
            c.drawOn(canv,x,y,_sW=aW-w)
            if c is not content[-1] and not getattr(c,'_SPACETRANSFER',None):
                y -= pS
            del c._frame

    def copyContent(self,content=None):
        C = [].append
        for c in (content or self._content):
            C(cdeepcopy(c))
        self._content = C.__self__

class PTOContainer(_Container,Flowable):
    '''PTOContainer(contentList,trailerList,headerList)

    A container for flowables decorated with trailer & header lists.
    If the split operation would be called then the trailer and header
    lists are injected before and after the split. This allows specialist
    "please turn over" and "continued from previous" like behaviours.'''
    def __init__(self,content,trailer=None,header=None):
        I = _PTOInfo(trailer,header)
        self._content = C = []
        for _ in _flowableSublist(content):
            if isinstance(_,PTOContainer):
                C.extend(_._content)
            else:
                C.append(_)
                if not hasattr(_,'_ptoinfo'): _._ptoinfo = I

    def wrap(self,availWidth,availHeight):
        self.width, self.height = _listWrapOn(self._content,availWidth,self.canv)
        return self.width,self.height

    def split(self, availWidth, availHeight):
        from reportlab.platypus.doctemplate import Indenter
        if availHeight<0: return []
        canv = self.canv
        C = self._content
        x = i = H = pS = hx = 0
        n = len(C)
        I2W = {}
        dLeft = dRight = 0
        for x in range(n):
            c = C[x]
            I = c._ptoinfo
            if I not in I2W.keys():
                T = I.trailer
                Hdr = I.header
                tW, tH = _listWrapOn(T, availWidth, self.canv)
                if len(T):  #trailer may have no content
                    tSB = T[0].getSpaceBefore()
                else:
                    tSB = 0
                I2W[I] = T,tW,tH,tSB
            else:
                T,tW,tH,tSB = I2W[I]
            _, h = c.wrapOn(canv,availWidth,0xfffffff)
            if isinstance(c,Indenter):
                dw = c.left+c.right
                dLeft += c.left
                dRight += c.right
                availWidth -= dw
                pS = 0
                hx = 0
            else:
                if x:
                    hx = max(c.getSpaceBefore()-pS,0)
                    h += hx
                pS = c.getSpaceAfter()
            H += h+pS
            tHS = tH+max(tSB,pS)
            if H+tHS>=availHeight-_FUZZ: break
            i += 1

        #first retract last thing we tried
        H -= (h+pS)

        #attempt a sub split on the last one we have
        aH = (availHeight-H-tHS-hx)*0.99999
        if aH>=0.05*availHeight:
            SS = c.splitOn(canv,availWidth,aH)
        else:
            SS = []

        if abs(dLeft)+abs(dRight)>1e-8:
            R1I = [Indenter(-dLeft,-dRight)]
            R2I = [Indenter(dLeft,dRight)]
        else:
            R1I = R2I = []

        if not SS:
            j = i
            while i>1 and C[i-1].getKeepWithNext():
                i -= 1
                C[i].keepWithNext = 0

            if i==1 and C[0].getKeepWithNext():
                #robin's black sheep
                i = j
                C[0].keepWithNext = 0

        F = [UseUpSpace()]

        if len(SS)>1:
            R1 = C[:i]+SS[:1]+R1I+T+F
            R2 = Hdr+R2I+SS[1:]+C[i+1:]
        elif not i:
            return []
        else:
            R1 = C[:i]+R1I+T+F
            R2 = Hdr+R2I+C[i:]
        T =  R1 + [PTOContainer(R2,[copy(x) for x in I.trailer],[copy(x) for x in I.header])]
        return T

#utility functions used by KeepInFrame
def _hmodel(s0,s1,h0,h1):
    # calculate the parameters in the model
    # h = a/s**2 + b/s
    a11 = 1./s0**2
    a12 = 1./s0
    a21 = 1./s1**2
    a22 = 1./s1
    det = a11*a22-a12*a21
    b11 = a22/det
    b12 = -a12/det
    b21 = -a21/det
    b22 = a11/det
    a = b11*h0+b12*h1
    b = b21*h0+b22*h1
    return a,b

def _qsolve(h,ab):
    '''solve the model v = a/s**2 + b/s for an s which gives us v==h'''
    a,b = ab
    if abs(a)<=_FUZZ:
        return b/h
    t = 0.5*b/a
    from math import sqrt
    f = -h/a
    r = t*t-f
    if r<0: return None
    r = sqrt(r)
    if t>=0:
        s1 = -t - r
    else:
        s1 = -t + r
    s2 = f/s1
    return max(1./s1, 1./s2)

class KeepInFrame(_Container,Flowable):
    def __init__(self, maxWidth, maxHeight, content=[], mergeSpace=1, mode='shrink', name='',hAlign='LEFT',vAlign='BOTTOM', fakeWidth=None):
        '''mode describes the action to take when overflowing
            error       raise an error in the normal way
            continue    ignore ie just draw it and report maxWidth, maxHeight
            shrink      shrinkToFit
            truncate    fit as much as possible
            set fakeWidth to False to make _listWrapOn do the 'right' thing
        '''
        self.name = name
        self.maxWidth = maxWidth
        self.maxHeight = maxHeight
        self.mode = mode
        assert mode in ('error','overflow','shrink','truncate'), '%s invalid mode value %s' % (self.identity(),mode)
        assert maxHeight>=0,  '%s invalid maxHeight value %s' % (self.identity(),maxHeight)
        if mergeSpace is None: mergeSpace = overlapAttachedSpace
        self.mergespace = mergeSpace
        self._content = content or []
        self.vAlign = vAlign
        self.hAlign = hAlign
        self.fakeWidth = fakeWidth

    def _getAvailableWidth(self):
        return self.maxWidth - self._leftExtraIndent - self._rightExtraIndent

    def identity(self, maxLen=None):
        return "<%s at %s%s%s> size=%sx%s" % (self.__class__.__name__, hex(id(self)), self._frameName(),
                getattr(self,'name','') and (' name="%s"'% getattr(self,'name','')) or '',
                getattr(self,'maxWidth','') and (' maxWidth=%s'%fp_str(getattr(self,'maxWidth',0))) or '',
                getattr(self,'maxHeight','')and (' maxHeight=%s' % fp_str(getattr(self,'maxHeight')))or '')

    def wrap(self,availWidth,availHeight):
        from reportlab.platypus.doctemplate import LayoutError
        mode = self.mode
        maxWidth = float(min(self.maxWidth or availWidth,availWidth))
        maxHeight = float(min(self.maxHeight or availHeight,availHeight))
        fakeWidth = self.fakeWidth
        W, H = _listWrapOn(self._content,maxWidth,self.canv, fakeWidth=fakeWidth)
        if (mode=='error' and (W>maxWidth+_FUZZ or H>maxHeight+_FUZZ)):
            ident = 'content %sx%s too large for %s' % (W,H,self.identity(30))
            #leave to keep apart from the raise
            raise LayoutError(ident)
        elif W<=maxWidth+_FUZZ and H<=maxHeight+_FUZZ:
            self.width = W-_FUZZ      #we take what we get
            self.height = H-_FUZZ
        elif mode in ('overflow','truncate'):   #we lie
            self.width = min(maxWidth,W)-_FUZZ
            self.height = min(maxHeight,H)-_FUZZ
        else:
            def func(x):
                x = float(x)
                W, H = _listWrapOn(self._content,x*maxWidth,self.canv, fakeWidth=fakeWidth)
                W /= x
                H /= x
                return W, H
            W0 = W
            H0 = H
            s0 = 1
            if W>maxWidth+_FUZZ:
                #squeeze out the excess width and or Height
                s1 = W/maxWidth     #linear model
                W, H = func(s1)
                if H<=maxHeight+_FUZZ:
                    self.width = W-_FUZZ
                    self.height = H-_FUZZ
                    self._scale = s1
                    return W,H
                s0 = s1
                H0 = H
                W0 = W
            s1 = H/maxHeight
            W, H = func(s1)
            self.width = W-_FUZZ
            self.height = H-_FUZZ
            self._scale = s1
            if H<min(0.95*maxHeight,maxHeight-10) or H>=maxHeight+_FUZZ:
                #the standard case W should be OK, H is short we want
                #to find the smallest s with H<=maxHeight
                H1 = H
                for f in 0, 0.01, 0.05, 0.10, 0.15:
                    #apply the quadratic model
                    s = _qsolve(maxHeight*(1-f),_hmodel(s0,s1,H0,H1))
                    W, H = func(s)
                    if H<=maxHeight+_FUZZ and W<=maxWidth+_FUZZ:
                        self.width = W-_FUZZ
                        self.height = H-_FUZZ
                        self._scale = s
                        break

        return self.width, self.height

    def drawOn(self, canv, x, y, _sW=0):
        scale = getattr(self,'_scale',1.0)
        truncate = self.mode=='truncate'
        ss = scale!=1.0 or truncate
        if ss:
            canv.saveState()
            if truncate:
                p = canv.beginPath()
                p.rect(x, y, self.width,self.height)
                canv.clipPath(p,stroke=0)
            else:
                canv.translate(x,y)
                x=y=0
                canv.scale(1.0/scale, 1.0/scale)
        _Container.drawOn(self, canv, x, y, _sW=_sW, scale=scale)
        if ss: canv.restoreState()


class _FindSplitterMixin:
    def _findSplit(self,canv,availWidth,availHeight,mergeSpace=1,obj=None,content=None,paraFix=True):
        '''return max width, required height for a list of flowables F'''
        W = 0
        H = 0
        pS = sB = 0
        atTop = 1
        F = self._getContent(content)
        for i,f in enumerate(F):
            if hasattr(f,'frameAction'):
                from reportlab.platypus.doctemplate import Indenter
                if isinstance(f,Indenter):
                    availWidth -= f.left+f.right
                continue
            w,h = f.wrapOn(canv,availWidth,0xfffffff)
            if w<=_FUZZ or h<=_FUZZ: continue
            W = max(W,w)
            if not atTop:
                s = f.getSpaceBefore()
                if mergeSpace: s = max(s-pS,0)
                H += s
            else:
                if obj is not None: obj._spaceBefore = f.getSpaceBefore()
                atTop = 0
            if H>=availHeight or w>availWidth:
                return W, availHeight, F[:i],F[i:]
            H += h
            if H>availHeight:
                aH = availHeight-(H-h)
                if paraFix:
                    from reportlab.platypus.paragraph import Paragraph
                    if isinstance(f,(Paragraph,Preformatted)):
                        leading = f.style.leading
                        nH = leading*int(aH/float(leading))+_FUZZ
                        if nH<aH: nH += leading
                        availHeight += nH-aH
                        aH = nH
                try:
                    S = cdeepcopy(f).splitOn(canv,availWidth,aH)
                except:
                    S  = None   #sometimes the deepcopy cannot be done
                if not S:
                    return W, availHeight, F[:i],F[i:]
                else:
                    return W,availHeight,F[:i]+S[:1],S[1:]+F[i+1:]
            pS = f.getSpaceAfter()
            H += pS

        if obj is not None: obj._spaceAfter = pS
        return W, H-pS, F, []

    def _getContent(self,content=None):
        F = []
        C = content if content is not None else self._content
        for f in C:
            if isinstance(f,ListFlowable):
                F.extend(self._getContent(f._content))
            else:
                F.append(f)
        return F

class ImageAndFlowables(_Container,_FindSplitterMixin,Flowable):
    '''combine a list of flowables and an Image'''
    def __init__(self,I,F,imageLeftPadding=0,imageRightPadding=3,imageTopPadding=0,imageBottomPadding=3,
                    imageSide='right', imageHref=None):
        self._content = _flowableSublist(F)
        self._I = I
        self._irpad = imageRightPadding
        self._ilpad = imageLeftPadding
        self._ibpad = imageBottomPadding
        self._itpad = imageTopPadding
        self._side = imageSide
        self.imageHref = imageHref

    def deepcopy(self):
        c = copy(self)  #shallow
        self._reset()
        c.copyContent() #partially deep?
        return c

    def getSpaceAfter(self):
        if hasattr(self,'_C1'):
            C = self._C1
        elif hasattr(self,'_C0'):
            C = self._C0
        else:
            C = self._content
        return _Container.getSpaceAfter(self,C)

    def getSpaceBefore(self):
        return max(self._I.getSpaceBefore(),_Container.getSpaceBefore(self))

    def _reset(self):
        for a in ('_wrapArgs','_C0','_C1'):
            try:
                delattr(self,a)
            except:
                pass

    def wrap(self,availWidth,availHeight):
        canv = self.canv
        I = self._I
        if hasattr(self,'_wrapArgs'):
            if self._wrapArgs==(availWidth,availHeight) and getattr(I,'_oldDrawSize',None) is None:
                return self.width,self.height
            self._reset()
            I._unRestrictSize()
        self._wrapArgs = availWidth, availHeight
        I.wrap(availWidth,availHeight)
        wI, hI = I._restrictSize(availWidth,availHeight)
        self._wI = wI
        self._hI = hI
        ilpad = self._ilpad
        irpad = self._irpad
        ibpad = self._ibpad
        itpad = self._itpad
        self._iW = iW = availWidth - irpad - wI - ilpad
        aH = itpad + hI + ibpad
        if iW>_FUZZ:
            W,H0,self._C0,self._C1 = self._findSplit(canv,iW,aH)
        else:
            W = availWidth
            H0 = 0
        if W>iW+_FUZZ:
            self._C0 = []
            self._C1 = self._content
        aH = self._aH = max(aH,H0)
        self.width = availWidth
        if not self._C1:
            self.height = aH
        else:
            W1,H1 = _listWrapOn(self._C1,availWidth,canv)
            self.height = aH+H1
        return self.width, self.height

    def split(self,availWidth, availHeight):
        if hasattr(self,'_wrapArgs'):
            I = self._I
            if self._wrapArgs!=(availWidth,availHeight) or getattr(I,'_oldDrawSize',None) is not None:
                self._reset()
                I._unRestrictSize()
        W,H=self.wrap(availWidth,availHeight)
        if self._aH>availHeight: return []
        C1 = self._C1
        if C1:
            S = C1[0].split(availWidth,availHeight-self._aH)
            if not S:
                _C1 = []
            else:
                _C1 = [S[0]]
                C1 = S[1:]+C1[1:]
        else:
            _C1 = []
        return [ImageAndFlowables(
                    self._I,
                    self._C0+_C1,
                    imageLeftPadding=self._ilpad,
                    imageRightPadding=self._irpad,
                    imageTopPadding=self._itpad,
                    imageBottomPadding=self._ibpad,
                    imageSide=self._side, imageHref=self.imageHref)
                    ]+C1

    def drawOn(self, canv, x, y, _sW=0):
        if self._side=='left':
            Ix = x + self._ilpad
            Fx = Ix+ self._irpad + self._wI
        else:
            Ix = x + self.width-self._wI-self._irpad
            Fx = x
        self._I.drawOn(canv,Ix,y+self.height-self._itpad-self._hI)

        if self.imageHref:
            canv.linkURL(self.imageHref, (Ix, y+self.height-self._itpad-self._hI, Ix + self._wI, y+self.height), relative=1)

        if self._C0:
            _Container.drawOn(self, canv, Fx, y, content=self._C0, aW=self._iW)
        if self._C1:
            aW, aH = self._wrapArgs
            _Container.drawOn(self, canv, x, y-self._aH,content=self._C1, aW=aW)

class _AbsRect(NullDraw):
    _ZEROSIZE=1
    _SPACETRANSFER = True
    def __init__(self,x,y,width,height,strokeWidth=0,strokeColor=None,fillColor=None,strokeDashArray=None):
        self._x = x
        self._y = y
        self._width = width
        self._height = height
        self._strokeColor = strokeColor
        self._fillColor = fillColor
        self._strokeWidth = strokeWidth
        self._strokeDashArray = strokeDashArray

    def wrap(self, availWidth, availHeight):
        return 0,0

    def drawOn(self, canv, x, y, _sW=0):
        if self._width>_FUZZ and self._height>_FUZZ:
            st = self._strokeColor and self._strokeWidth is not None and self._strokeWidth>=0
            if st or self._fillColor:
                canv.saveState()
                if st:
                    canv.setStrokeColor(self._strokeColor)
                    canv.setLineWidth(self._strokeWidth)
                if self._fillColor:
                    canv.setFillColor(self._fillColor)
                canv.rect(self._x,self._y,self._width,self._height,stroke=1 if st else 0, fill=1 if self._fillColor else 0)
                canv.restoreState()

class _ExtendBG(NullDraw):
    _ZEROSIZE=1
    _SPACETRANSFER = True
    def __init__(self,y,height,bg,frame):
        self._y = y
        self._height = height
        self._bg = bg

    def wrap(self, availWidth, availHeight):
        return 0,0

    def frameAction(self, frame):
        bg = self._bg
        fby = self._y
        fbh = self._height
        fbgl = bg.left
        fbw = frame._width - fbgl - bg.right
        fbx = frame._x1 - fbgl
        canv = self.canv
        pn = canv.getPageNumber()
        bg.render(canv,frame,fbx,fby,fbw,fbh)

class _AbsLine(NullDraw):
    _ZEROSIZE=1
    _SPACETRANSFER = True
    def __init__(self,x,y,x1,y1,strokeWidth=0,strokeColor=None,strokeDashArray=None):
        self._x = x
        self._y = y
        self._x1 = x1
        self._y1 = y1
        self._strokeColor = strokeColor
        self._strokeWidth = strokeWidth
        self._strokeDashArray = strokeDashArray

    def wrap(self, availWidth, availHeight):
        return 0,0

    def drawOn(self, canv, x, y, _sW=0):
        if self._strokeColor and self._strokeWidth is not None and self._strokeWidth>=0:
            canv.saveState()
            canv.setStrokeColor(self._strokeColor)
            canv.setLineWidth(self._strokeWidth)
            canv.line(self._x,self._y,self._x1,self._y1)
            canv.restoreState()

class BalancedColumns(_FindSplitterMixin,NullDraw):
    '''combine a list of flowables and an Image'''
    def __init__(self, F, nCols=2, needed=72, spaceBefore=0, spaceAfter=0, showBoundary=None,
            leftPadding=None, innerPadding=None, rightPadding=None, topPadding=None, bottomPadding=None,
            name='', endSlack=0.1,
            boxStrokeColor=None,
            boxStrokeWidth=0,
            boxFillColor=None,
            boxMargin=None,
            vLinesStrokeColor=None,
            vLinesStrokeWidth=None,
            ):
        self.name = name or 'BalancedColumns-%d' % id(self)
        if nCols <2:
            raise ValueError('nCols should be at least 2 not %r in %s' % (nCols,self.identitity()))
        self._content = _flowableSublist(F)
        self._nCols = nCols
        self.spaceAfter = spaceAfter
        self._leftPadding = leftPadding
        self._innerPadding = innerPadding
        self._rightPadding = rightPadding
        self._topPadding = topPadding
        self._bottomPadding = bottomPadding
        self.spaceBefore = spaceBefore
        self._needed = needed - _FUZZ
        self.showBoundary = showBoundary
        self.endSlack = endSlack    #what we might allow as a lastcolumn overrun
        self._boxStrokeColor = boxStrokeColor
        self._boxStrokeWidth = boxStrokeWidth
        self._boxFillColor = boxFillColor
        self._boxMargin = boxMargin
        self._vLinesStrokeColor = vLinesStrokeColor
        self._vLinesStrokeWidth = vLinesStrokeWidth

    def identity(self, maxLen=None):
        return "<%s nCols=%r at %s%s%s>" % (self.__class__.__name__, self._nCols, hex(id(self)), self._frameName(),
                getattr(self,'name','') and (' name="%s"'% getattr(self,'name','')) or '',
                )

    def getSpaceAfter(self):
        return self.spaceAfter

    def getSpaceBefore(self):
        return self.spaceBefore

    def _generated_content(self,aW,aH):
        G = []
        frame = self._frame
        from reportlab.platypus.doctemplate import LayoutError, ActionFlowable, Indenter
        from reportlab.platypus.frames import Frame
        from reportlab.platypus.doctemplate import FrameBreak
        lpad = frame._leftPadding if self._leftPadding is None else self._leftPadding
        rpad = frame._rightPadding if self._rightPadding is None else self._rightPadding
        tpad = frame._topPadding if self._topPadding is None else self._topPadding
        bpad = frame._bottomPadding if self._bottomPadding is None else self._bottomPadding
        leftExtraIndent = frame._leftExtraIndent
        rightExtraIndent = frame._rightExtraIndent
        gap = max(lpad,rpad) if self._innerPadding is None else self._innerPadding
        hgap = gap*0.5
        canv = self.canv
        nCols = self._nCols
        cw = (aW - gap*(nCols-1) - lpad - rpad)/float(nCols)
        aH0 = aH
        aH -= tpad + bpad
        W,H0,_C0,C2 = self._findSplit(canv,cw,nCols*aH,paraFix=False)
        if not _C0:
            raise ValueError(
                    "%s cannot make initial split aW=%r aH=%r ie cw=%r ah=%r\ncontent=%s" % (
                        self.identity(),aW,aH,cw,nCols*aH,
                        [f.__class__.__name__ for f in self._content],
                        ))
        _fres = {}
        def splitFunc(ah,endSlack=0):
            if ah not in _fres:
                c = []
                w = 0
                h = 0
                cn = None
                icheck = nCols-2 if endSlack else -1
                for i in range(nCols):
                    wi, hi, c0, c1 = self._findSplit(canv,cw,ah,content=cn,paraFix=False)
                    w = max(w,wi)
                    h = max(h,hi)
                    c.append(c0)
                    if i==icheck:
                        wc, hc, cc0, cc1 = self._findSplit(canv,cw,2*ah,content=c1,paraFix=False)
                        if hc<=(1+endSlack)*ah:
                            c.append(c1)
                            h = ah-1e-6
                            cn = []
                            break
                    cn = c1
                _fres[ah] = ah+100000*int(cn!=[]),cn==[],(w,h,c,cn)
            return _fres[ah][2]

        endSlack = 0
        if C2:
            H = aH
        else:
            #we are short so use H0 to figure out what to use
            import math

            def func(ah):
                splitFunc(ah)
                return _fres[ah][0]

            def gss(f, a, b, tol=1, gr=(math.sqrt(5) + 1) / 2):
                c = b - (b - a) / gr
                d = a + (b - a) / gr
                while abs(a - b) > tol:
                    if f(c) < f(d):
                        b = d
                    else:
                        a = c

                    # we recompute both c and d here to avoid loss of precision which may lead to incorrect results or infinite loop
                    c = b - (b - a) / gr
                    d = a + (b - a) / gr

                F = [(x,tf,v) for x,tf,v in _fres.values() if tf]
                if F:
                    F.sort()
                    return F[0][2]
                return None

            H = min(int(H0/float(nCols)+self.spaceAfter*0.4),aH)
            splitFunc(H)
            if not _fres[H][1]:
                H = gss(func,H,aH)
                if H:
                    W, H0, _C0, C2 = H
                    H = H0
                    endSlack = False
                else:
                    H = aH
                    endSlack = self.endSlack
            else:
                H1 = H0/float(nCols)
                splitFunc(H1)
                if not _fres[H1][1]:
                    H = gss(func,H,aH)
                    if H:
                        W, H0, _C0, C2 = H
                        H = H0
                        endSlack = False
                    else:
                        H = aH
                        endSlack = self.endSlack
            assert not C2, "unexpected non-empty C2"
        W1, H1, C, C1 = splitFunc(H, endSlack)
        _fres.clear()
        if C[0]==[] and C[1]==[] and C1:
            #no split situation
            C, C1 = [C1,C[1]], C[0]

        x1 = frame._x1
        y1 = frame._y1
        fw = frame._width
        ftop = y1+bpad+tpad+aH
        fh = H1 + bpad + tpad
        y2 = ftop - fh
        dx = aW / float(nCols)
        if leftExtraIndent or rightExtraIndent:
            indenter0 = Indenter(-leftExtraIndent,-rightExtraIndent)
            indenter1 = Indenter(leftExtraIndent,rightExtraIndent)
        else:
            indenter0 = indenter1 = None

        showBoundary=self.showBoundary if self.showBoundary is not None else frame.showBoundary
        obx = x1+leftExtraIndent+frame._leftPadding
        F = [Frame(obx+i*dx,y2,dx,fh,
                leftPadding=lpad if not i else hgap, bottomPadding=bpad,
                rightPadding=rpad if i==nCols-1 else hgap, topPadding=tpad,
                id='%s-%d' %(self.name,i),
                showBoundary=showBoundary,
                overlapAttachedSpace=frame._oASpace,
                _debug=frame._debug) for i in range(nCols)]


        #we are going to modify the current template
        T=self._doctemplateAttr('pageTemplate')
        if T is None:
            raise LayoutError('%s used in non-doctemplate environment' % self.identity())

        BGs = getattr(frame,'_frameBGs',None)
        xbg = bg = BGs[-1] if BGs else None

        class TAction(ActionFlowable):
            '''a special Action flowable that sets stuff on the doc template T'''
            def __init__(self, bgs=[],F=[],f=None):
                Flowable.__init__(self)
                self.bgs = bgs
                self.F = F
                self.f = f

            def apply(self,doc,T=T):
                T.frames = self.F
                frame._frameBGs = self.bgs
                doc.handle_currentFrame(self.f.id)
                frame._frameBGs = self.bgs

        if bg:
            #G.append(Spacer(1e-5,1e-5))
            #G[-1].__id__ = 'spacer0'
            xbg = _ExtendBG(y2,fh,bg,frame)
            G.append(xbg)

        oldFrames = T.frames
        G.append(TAction([],F,F[0]))
        if indenter0: G.append(indenter0)
        doBox = (self._boxStrokeColor and self._boxStrokeWidth and self._boxStrokeWidth>=0) or self._boxFillColor
        doVLines = self._vLinesStrokeColor and self._vLinesStrokeWidth and self._vLinesStrokeWidth>=0
        if doBox or doVLines:
            obm = self._boxMargin
            if not obm: obm = (0,0,0,0)
            if len(obm)==1:
                obmt = obml = obmr = obmb = obm[0]
            elif len(obm)==2:
                obmt = obmb = obm[0]
                obml = obmr = obm[1]
            elif len(obm)==3:
                obmt = obm[0]
                obml = obmr = obm[1]
                obmb = obm[2]
            elif len(obm)==4:
                obmt = obm[0]
                obmr = obm[1]
                obmb = obm[2]
                obml = obm[3]
            else:
                raise ValueError('Invalid value %s for boxMargin' % repr(obm))
            obx1 = obx - obml
            obx2 = F[-1]._x1+F[-1]._width + obmr
            oby2 = y2-obmb
            obh = fh+obmt+obmb
            oby1 = oby2+obh
            if doBox:
                box = _AbsRect(obx1,oby2, obx2-obx1, obh,
                        fillColor=self._boxFillColor,
                        strokeColor=self._boxStrokeColor,
                        strokeWidth=self._boxStrokeWidth,
                        )
            if doVLines:
                vLines = []
                for i in range(1,nCols):
                    vlx = 0.5*(F[i]._x1 + F[i-1]._x1+F[i-1]._width)
                    vLines.append(_AbsLine(vlx,oby2,vlx,oby1,strokeWidth=self._vLinesStrokeWidth,strokeColor=self._vLinesStrokeColor))
        else:
            oby1 = ftop
            oby2 = y2

        if doBox: G.append(box)
        if doVLines: G.extend(vLines)
        sa = self.getSpaceAfter()
        for i in range(nCols):
            Ci = C[i]
            if Ci:
                Ci = KeepInFrame(W1,H1,Ci,mode='shrink')
                sa = max(sa,Ci.getSpaceAfter())
                G.append(Ci)
            if i!=nCols-1:
                G.append(FrameBreak)
        G.append(TAction(BGs,oldFrames,frame))
        if xbg:
            if C1: sa = 0
            xbg._y = min(y2,oby2) - sa
            xbg._height = max(ftop,oby1) - xbg._y
        if indenter1: G.append(indenter1)
        if C1:
            G.append(
                BalancedColumns(C1, nCols=nCols,
                    needed=self._needed, spaceBefore=self.spaceBefore, spaceAfter=self.spaceAfter,
                    showBoundary=self.showBoundary,
                    leftPadding=self._leftPadding,
                    innerPadding=self._innerPadding,
                    rightPadding=self._rightPadding,
                    topPadding=self._topPadding,
                    bottomPadding=self._bottomPadding,
                    name=self.name+'-1', endSlack=self.endSlack,
                    boxStrokeColor=self._boxStrokeColor,
                    boxStrokeWidth=self._boxStrokeWidth,
                    boxFillColor=self._boxFillColor,
                    boxMargin=self._boxMargin,
                    vLinesStrokeColor=self._vLinesStrokeColor,
                    vLinesStrokeWidth=self._vLinesStrokeWidth,
                    )
                )
        return fh, G

    def wrap(self,aW,aH):
        #here's where we mess with everything
        if aH<self.spaceBefore+self._needed-_FUZZ:
            #we are going straight to the nextTemplate with no attempt to modify the frames
            G = [PageBreak(), self]
            H1 = 0
        else:
            H1, G = self._generated_content(aW,aH)

        self._frame.add_generated_content(*G)
        return 0,min(H1,aH)

class AnchorFlowable(Spacer):
    '''create a bookmark in the pdf'''
    _ZEROSIZE=1
    _SPACETRANSFER = True
    def __init__(self,name):
        Spacer.__init__(self,0,0)
        self._name = name

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__,self._name)

    def wrap(self,aW,aH):
        return 0,0

    def draw(self):
        self.canv.bookmarkHorizontal(self._name,0,0)

class _FBGBag(ABag):
    def matches(self,frame,canv):
        fid = id(frame)
        return ((isinstance(self.fid,list) and fid in self.fid or fid==self.fid)
                    and id(canv)==self.cid and self.pn==canv.getPageNumber())

    def getDims(self,canv):
        self._inst = canv._code[self.codePos].split()
        return map(float,self._inst[1:5])

    def setDims(self,canv,x,y,w,h):
        self._inst[1:5] = [fp_str(x,y,w,h)]
        canv._code[self.codePos] = ' '.join(self._inst)

    def render(self,canv,frame,fbx,fby,fbw,fbh):
        if abs(fbw)>_FUZZ and abs(fbh)>_FUZZ:
            pn = canv.getPageNumber()
            if self.fid==id(frame) and self.cid==id(canv) and self.pn==pn:
                ox,oy,ow,oh = self.getDims(canv)
                self.setDims(canv,ox,fby,ow,oh+oy-fby)
            else:
                canv.saveState()
                fbgc = self.fillColor
                if fbgc:
                    canv.setFillColor(fbgc)
                sw = self.strokeWidth
                sc = None if sw is None or sw<0 else self.strokeColor
                if sc:
                    canv.setStrokeColor(sc)
                    canv.setLineWidth(sw)
                    da = self.strokeDashArray
                    if da:
                        canv.setDash(da)
                self.fid = id(frame)
                self.cid = id(canv)
                self.pn = pn
                self.codePos = len(canv._code)
                canv.rect(fbx,fby,fbw,fbh,stroke=1 if sc else 0,fill=1 if fbgc else 0)
                canv.restoreState()

class FrameBG(AnchorFlowable):
    """Start or stop coloring the frame background
    left & right are distances from the edge of the frame to start stop colouring.
    if start in ('frame','frame-permanent') then the background is filled from here to the bottom of the frame and immediately discarded
    for the frame case.
    """
    _ZEROSIZE=1
    def __init__(self, color=None, left=0, right=0, start=True, strokeWidth=None, strokeColor=None, strokeDashArray=None):
        Spacer.__init__(self,0,0)
        self.start = start
        if start:
            from reportlab.platypus.doctemplate import _evalMeasurement
            self.left = _evalMeasurement(left)
            self.right = _evalMeasurement(right)
            self.color = color
            self.strokeWidth = strokeWidth
            self.strokeColor = strokeColor
            self.strokeDashArray = strokeDashArray

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__,', '.join(['%s=%r' % (i,getattr(self,i,None)) for i in 'start color left right'.split()]))

    def draw(self):
        frame = getattr(self,'_frame',None)
        if frame is None: return
        if self.start:
            sc = self.strokeColor
            sw = self.strokeWidth
            sw = -1 if sw is None else sw
            frame._frameBGs.append(
                        _FBGBag(left=self.left,
                                right=self.right,
                                fillColor=self.color,
                                start=self.start if self.start in ('frame','frame-permanent') else None,
                                strokeColor=self.strokeColor,
                                strokeWidth=self.strokeWidth,
                                strokeDashArray=self.strokeDashArray,
                                fid = 0,
                                cid = 0,
                                pn = -1,
                                codePos = None,
                                active=True,
                                ))
        elif frame._frameBGs:
            frame._frameBGs.pop()

class FrameSplitter(NullDraw):
    '''When encountered this flowable should either switch directly to nextTemplate
    if remaining space in the current frame is less than gap+required or it should
    temporarily modify the current template to have the frames from nextTemplate
    that are listed in nextFrames and switch to the first of those frames.
    '''
    _ZEROSIZE=1
    def __init__(self, nextTemplate, nextFrames=[], gap=10, required=72, adjustHeight=True):
        self.nextTemplate = nextTemplate
        self.nextFrames = nextFrames or []
        self.gap = gap
        self.required = required
        self.adjustHeight = adjustHeight

    def wrap(self,aW,aH):
        frame = self._frame
        from reportlab.platypus.doctemplate import NextPageTemplate,CurrentFrameFlowable,LayoutError
        G=[NextPageTemplate(self.nextTemplate)]
        if aH<self.gap+self.required-_FUZZ:
            #we are going straight to the nextTemplate with no attempt to modify the frames
            G.append(PageBreak())
        else:
            #we are going to modify the incoming templates
            templates = self._doctemplateAttr('pageTemplates')
            if templates is None:
                raise LayoutError('%s called in non-doctemplate environment'%self.identity())
            T=[t for t in templates if t.id==self.nextTemplate]
            if not T:
                raise LayoutError('%s.nextTemplate=%s not found' % (self.identity(),self.nextTemplate))
            T=T[0]
            F=[f for f in T.frames if f.id in self.nextFrames]
            N=[f.id for f in F]
            N=[f for f in self.nextFrames if f not in N]
            if N:
                raise LayoutError('%s frames=%r not found in pageTemplate(%s)\n%r has frames %r' % (self.identity(),N,T.id,T,[f.id for f in T.frames]))
            T=self._doctemplateAttr('pageTemplate')
            def unwrap(canv,doc,T=T,onPage=T.onPage,oldFrames=T.frames):
                T.frames=oldFrames
                T.onPage=onPage
                onPage(canv,doc)
            T.onPage=unwrap
            h=aH-self.gap
            for i,f in enumerate(F):
                f=copy(f)
                if self.adjustHeight: f.height=h
                f._reset()
                F[i]=f
            T.frames=F
            G.append(CurrentFrameFlowable(F[0].id))
        frame.add_generated_content(*G)
        return 0,0


from reportlab.lib.sequencer import _type2formatter
_bulletNames = dict(
                bulletchar=u'\u2022',   #usually a small circle
                circle=u'\u25cf',   #circle as high as the font
                square=u'\u25a0',
                disc=u'\u25cb',
                diamond=u'\u25c6',
                diamondwx=u'\u2756',
                rarrowhead=u'\u27a4',
                sparkle=u'\u2747',
                squarelrs=u'\u274f',
                blackstar=u'\u2605',
                )

def _bulletFormat(value,type='1',format=None):
    if type=='bullet':
        s = _bulletNames.get(value,value)
    else:
        s = _type2formatter[type](int(value))

    if format:
        if isinstance(format,strTypes):
            s = format % s
        elif callable(format):
            s = format(s)
        else:
            raise ValueError('unexpected BulletDrawer format %r' % format)
    return s

class BulletDrawer:
    def __init__(self,
                    value='0',
                    bulletAlign='left',
                    bulletType='1',
                    bulletColor='black',
                    bulletFontName='Helvetica',
                    bulletFontSize=12,
                    bulletOffsetY=0,
                    bulletDedent=0,
                    bulletDir='ltr',
                    bulletFormat=None,
                    ):
        self.value = value
        self._bulletAlign = bulletAlign
        self._bulletType = bulletType
        self._bulletColor = bulletColor
        self._bulletFontName = bulletFontName
        self._bulletFontSize = bulletFontSize
        self._bulletOffsetY = bulletOffsetY
        self._bulletDedent = bulletDedent
        self._bulletDir = bulletDir
        self._bulletFormat = bulletFormat

    def drawOn(self,indenter,canv,x,y,_sW=0):
        value = self.value
        if not value: return
        canv.saveState()
        canv.translate(x, y)

        y = indenter.height-self._bulletFontSize+self._bulletOffsetY
        if self._bulletDir=='rtl':
            x = indenter.width - indenter._rightIndent + self._bulletDedent
        else:
            x = indenter._leftIndent - self._bulletDedent
        canv.setFont(self._bulletFontName,self._bulletFontSize)
        canv.setFillColor(self._bulletColor)
        bulletAlign = self._bulletAlign
        value = _bulletFormat(value,self._bulletType,self._bulletFormat)

        if bulletAlign=='left':
            canv.drawString(x,y,value)
        elif bulletAlign=='right':
            canv.drawRightString(x,y,value)
        elif bulletAlign in ('center','centre'):
            canv.drawCentredString(x,y,value)
        elif bulletAlign.startswith('numeric') or bulletAlign.startswith('decimal'):
            pc = bulletAlign[7:].strip() or '.'
            canv.drawAlignedString(x,y,value,pc)
        else:
            raise ValueError('Invalid bulletAlign: %r' % bulletAlign)
        canv.restoreState()

def _computeBulletWidth(b,value):
    value = _bulletFormat(value,b._bulletType,b._bulletFormat)
    return stringWidth(value,b._bulletFontName,b._bulletFontSize)

class DDIndenter(Flowable):
    _IndenterAttrs = '_flowable _leftIndent _rightIndent width height'.split()
    def __init__(self,flowable,leftIndent=0,rightIndent=0):
        self._flowable = flowable
        self._leftIndent = leftIndent
        self._rightIndent = rightIndent
        self.width = None
        self.height = None

    def split(self, aW, aH):
        S = self._flowable.split(aW-self._leftIndent-self._rightIndent, aH)
        return [
                DDIndenter(s,
                        leftIndent=self._leftIndent,
                        rightIndent=self._rightIndent,
                        ) for s in S
                ]

    def drawOn(self, canv, x, y, _sW=0):
        self._flowable.drawOn(canv,x+self._leftIndent,y,max(0,_sW-self._leftIndent-self._rightIndent))

    def wrap(self, aW, aH):
        w,h = self._flowable.wrap(aW-self._leftIndent-self._rightIndent, aH)
        self.width = w+self._leftIndent+self._rightIndent
        self.height = h
        return self.width,h

    def __getattr__(self,a):
        if a in self._IndenterAttrs:
            try:
                return self.__dict__[a]
            except KeyError:
                if a not in ('spaceBefore','spaceAfter'):
                    raise AttributeError('%r has no attribute %s' % (self,a))
        return getattr(self._flowable,a)

    def __setattr__(self,a,v):
        if a in self._IndenterAttrs:
            self.__dict__[a] = v
        else:
            setattr(self._flowable,a,v)

    def __delattr__(self,a):
        if a in self._IndenterAttrs:
            del self.__dict__[a]
        else:
            delattr(self._flowable,a)

    def identity(self,maxLen=None):
        return '%s containing %s' % (self.__class__.__name__,self._flowable.identity(maxLen))

class LIIndenter(DDIndenter):
    _IndenterAttrs = '_flowable _bullet _leftIndent _rightIndent width height spaceBefore spaceAfter'.split()
    def __init__(self,flowable,leftIndent=0,rightIndent=0,bullet=None, spaceBefore=None, spaceAfter=None):
        self._flowable = flowable
        self._bullet = bullet
        self._leftIndent = leftIndent
        self._rightIndent = rightIndent
        self.width = None
        self.height = None
        if spaceBefore is not None:
            self.spaceBefore = spaceBefore
        if spaceAfter is not None:
            self.spaceAfter = spaceAfter

    def split(self, aW, aH):
        S = self._flowable.split(aW-self._leftIndent-self._rightIndent, aH)
        return [
                LIIndenter(s,
                        leftIndent=self._leftIndent,
                        rightIndent=self._rightIndent,
                        bullet = (s is S[0] and self._bullet or None),
                        ) for s in S
                ]

    def drawOn(self, canv, x, y, _sW=0):
        if self._bullet:
            self._bullet.drawOn(self,canv,x,y,0)
        self._flowable.drawOn(canv,x+self._leftIndent,y,max(0,_sW-self._leftIndent-self._rightIndent))


from reportlab.lib.styles import ListStyle
class ListItem:
    def __init__(self,
                    flowables,  #the initial flowables
                    style=None,
                    #leftIndent=18,
                    #rightIndent=0,
                    #spaceBefore=None,
                    #spaceAfter=None,
                    #bulletType='1',
                    #bulletColor='black',
                    #bulletFontName='Helvetica',
                    #bulletFontSize=12,
                    #bulletOffsetY=0,
                    #bulletDedent='auto',
                    #bulletDir='ltr',
                    #bulletFormat=None,
                    **kwds
                    ):
        if not isinstance(flowables,(list,tuple)):
            flowables = (flowables,)
        self._flowables = flowables
        params = self._params = {}

        if style:
            if not isinstance(style,ListStyle):
                raise ValueError('%s style argument (%r) not a ListStyle' % (self.__class__.__name__,style))
            self._style = style

        for k in ListStyle.defaults:
            if k in kwds:
                v = kwds.get(k)
            elif style:
                v = getattr(style,k)
            else:
                continue
            params[k] = v

        for k in ('value', 'spaceBefore','spaceAfter'):
            v = kwds.get(k,getattr(style,k,None))
            if v is not None:
                params[k] = v

class _LIParams:
    def __init__(self,flowable,params,value,first):
        self.flowable = flowable
        self.params = params
        self.value = value
        self.first= first

class ListFlowable(_Container,Flowable):
    _numberStyles = '1aAiI'
    def __init__(self,
                    flowables,  #the initial flowables
                    start=None,
                    style=None,
                    #leftIndent=18,
                    #rightIndent=0,
                    #spaceBefore=None,
                    #spaceAfter=None,
                    #bulletType='1',
                    #bulletColor='black',
                    #bulletFontName='Helvetica',
                    #bulletFontSize=12,
                    #bulletOffsetY=0,
                    #bulletDedent='auto',
                    #bulletDir='ltr',
                    #bulletFormat=None,
                    **kwds
                    ):
        self._flowables = flowables

        if style:
            if not isinstance(style,ListStyle):
                raise ValueError('%s style argument not a ListStyle' % self.__class__.__name__)
            self.style = style

        for k,v in ListStyle.defaults.items():
            setattr(self,'_'+k,kwds.get(k,getattr(style,k,v)))

        for k in ('spaceBefore','spaceAfter'):
            v = kwds.get(k,getattr(style,k,None))
            if v is not None:
                setattr(self,k,v)

        auto = False
        if start is None:
            start = getattr(self,'_start',None)
            if start is None:
                if self._bulletType=='bullet':
                    start = 'bulletchar'
                    auto = True
                else:
                    start = self._bulletType
                    auto = True
        if self._bulletType!='bullet':
            if auto:
                for v in start:
                    if v not in self._numberStyles:
                        raise ValueError('invalid start=%r or bullettype=%r' % (start,self._bulletType))
            else:
                for v in self._bulletType:
                    if v not in self._numberStyles:
                        raise ValueError('invalid bullettype=%r' % self._bulletType)
        self._start = start
        self._auto = auto or isinstance(start,(list,tuple))

        self._list_content = None
        self._dims = None

    @property
    def _content(self):
        if self._list_content is None:
            self._list_content = self._getContent()
            del self._flowables
        return self._list_content

    def wrap(self,aW,aH):
        if self._dims!=aW:
            self.width, self.height = _listWrapOn(self._content,aW,self.canv)
            self._dims = aW
        return self.width,self.height

    def split(self,aW,aH):
        return self._content

    def _flowablesIter(self):
        for f in self._flowables:
            if isinstance(f,(list,tuple)):
                if f:
                    for i, z in enumerate(f):
                        yield i==0 and not isinstance(z,LIIndenter), z
            elif isinstance(f,ListItem):
                params = f._params
                if not params:
                    #meerkat simples just a list like object
                    for i, z in enumerate(f._flowables):
                        if isinstance(z,LIIndenter):
                            raise ValueError('LIIndenter not allowed in ListItem')
                        yield i==0, z
                else:
                    params = params.copy()
                    value = params.pop('value',None)
                    spaceBefore = params.pop('spaceBefore',None)
                    spaceAfter = params.pop('spaceAfter',None)
                    n = len(f._flowables) - 1
                    for i, z in enumerate(f._flowables):
                        P = params.copy()
                        if not i and spaceBefore is not None:
                            P['spaceBefore'] = spaceBefore
                        if i==n and spaceAfter is not None:
                            P['spaceAfter'] = spaceAfter
                        if i: value=None
                        yield 0, _LIParams(z,P,value,i==0)
            else:
                yield not isinstance(f,LIIndenter), f

    def _makeLIIndenter(self,flowable, bullet, params=None):
        if params:
            leftIndent = params.get('leftIndent',self._leftIndent)
            rightIndent = params.get('rightIndent',self._rightIndent)
            spaceBefore = params.get('spaceBefore',None)
            spaceAfter = params.get('spaceAfter',None)
            return LIIndenter(flowable,leftIndent,rightIndent,bullet,spaceBefore=spaceBefore,spaceAfter=spaceAfter)
        else:
            return LIIndenter(flowable,self._leftIndent,self._rightIndent,bullet)

    def _makeBullet(self,value,params=None):
        if params is None:
            def getp(a):
                return getattr(self,'_'+a)
        else:
            style = getattr(params,'style',None)
            def getp(a):
                if a in params: return params[a]
                if style and a in style.__dict__: return getattr(self,a)
                return getattr(self,'_'+a)

        return BulletDrawer(
                    value=value,
                    bulletAlign=getp('bulletAlign'),
                    bulletType=getp('bulletType'),
                    bulletColor=getp('bulletColor'),
                    bulletFontName=getp('bulletFontName'),
                    bulletFontSize=getp('bulletFontSize'),
                    bulletOffsetY=getp('bulletOffsetY'),
                    bulletDedent=getp('calcBulletDedent'),
                    bulletDir=getp('bulletDir'),
                    bulletFormat=getp('bulletFormat'),
                    )

    def _getContent(self):
        bt = self._bulletType
        value = self._start
        if isinstance(value,(list,tuple)):
            values = value
            value = values[0]
        else:
            values = [value]
        autov = values[0]
        inc = int(bt in '1aAiI')
        if inc:
            try:
                value = int(value)
            except:
                value = 1

        bd = self._bulletDedent
        if bd=='auto':
            align = self._bulletAlign
            dir = self._bulletDir
            if dir=='ltr' and align=='left':
                bd = self._leftIndent
            elif align=='right':
                bd = self._rightIndent
            else:
                #we need to work out the maximum width of any of the labels
                tvalue = value
                maxW = 0
                for d,f in self._flowablesIter():
                    if d:
                        maxW = max(maxW,_computeBulletWidth(self,tvalue))
                        if inc: tvalue += inc
                    elif isinstance(f,LIIndenter):
                        b = f._bullet
                        if b:
                            if b.bulletType==bt:
                                maxW = max(maxW,_computeBulletWidth(b,b.value))
                                tvalue = int(b.value)
                        else:
                            maxW = max(maxW,_computeBulletWidth(self,tvalue))
                        if inc: tvalue += inc
                if dir=='ltr':
                    if align=='right':
                        bd = self._leftIndent - maxW
                    else:
                        bd = self._leftIndent - maxW*0.5
                elif align=='left':
                    bd = self._rightIndent - maxW
                else:
                    bd = self._rightIndent - maxW*0.5

        self._calcBulletDedent = bd

        S = []
        aS = S.append
        i=0
        for d,f in self._flowablesIter():
            if isinstance(f,ListFlowable):
                fstart = f._start
                if isinstance(fstart,(list,tuple)):
                    fstart = fstart[0]
                if fstart in values:
                    #my kind of ListFlowable
                    if f._auto:
                        autov = values.index(autov)+1
                        f._start = values[autov:]+values[:autov]
                        autov = f._start[0]
                        if inc: f._bulletType = autov
                    else:
                        autov = fstart
            fparams = {}
            if not i:
                i += 1
                spaceBefore = getattr(self,'spaceBefore',None)
                if spaceBefore is not None:
                    fparams['spaceBefore'] = spaceBefore
            if d:
                aS(self._makeLIIndenter(f,bullet=self._makeBullet(value),params=fparams))
                if inc: value += inc
            elif isinstance(f,LIIndenter):
                b = f._bullet
                if b:
                    if b.bulletType!=bt:
                        raise ValueError('Included LIIndenter bulletType=%s != OrderedList bulletType=%s' % (b.bulletType,bt))
                    value = int(b.value)
                else:
                    f._bullet = self._makeBullet(value,params=getattr(f,'params',None))
                if fparams:
                    f.__dict__['spaceBefore'] = max(f.__dict__.get('spaceBefore',0),spaceBefore)
                aS(f)
                if inc: value += inc
            elif isinstance(f,_LIParams):
                fparams.update(f.params)
                z = self._makeLIIndenter(f.flowable,bullet=None,params=fparams)
                if f.first:
                    if f.value is not None:
                        value = f.value
                        if inc: value = int(value)
                    z._bullet = self._makeBullet(value,f.params)
                    if inc: value += inc
                aS(z)
            else:
                aS(self._makeLIIndenter(f,bullet=None,params=fparams))

        spaceAfter = getattr(self,'spaceAfter',None)
        if spaceAfter is not None:
            f=S[-1]
            f.__dict__['spaceAfter'] = max(f.__dict__.get('spaceAfter',0),spaceAfter)
        return S

class TopPadder(Flowable):
    '''wrap a single flowable so that its first bit will be
    padded to fill out the space so that it appears at the
    bottom of its frame'''
    def __init__(self,f):
        self.__dict__['_TopPadder__f'] = f

    def wrap(self,aW,aH):
        w,h = self.__f.wrap(aW,aH)
        self.__dict__['_TopPadder__dh'] = aH-h
        return w,h

    def split(self,aW,aH):
        S = self.__f.split(aW,aH)
        if len(S)>1:
            S[0] = TopPadder(S[0])
        return S

    def drawOn(self, canvas, x, y, _sW=0):
        self.__f.drawOn(canvas,x,y-max(0,self.__dh-1e-8),_sW)

    def __setattr__(self,a,v):
        setattr(self.__f,a,v)

    def __getattr__(self,a):
        return getattr(self.__f,a)

    def __delattr__(self,a):
        delattr(self.__f,a)

class DocAssign(NullDraw):
    '''At wrap time this flowable evaluates var=expr in the doctemplate namespace'''
    _ZEROSIZE=1
    def __init__(self,var,expr,life='forever'):
        Flowable.__init__(self)
        self.args = var,expr,life

    def funcWrap(self,aW,aH):
        NS=self._doctemplateAttr('_nameSpace')
        NS.update(dict(availableWidth=aW,availableHeight=aH))
        try:
            return self.func()
        finally:
            for k in 'availableWidth','availableHeight':
                try:
                    del NS[k]
                except:
                    pass

    def func(self):
        return self._doctemplateAttr('d'+self.__class__.__name__[1:])(*self.args)

    def wrap(self,aW,aH):
        self.funcWrap(aW,aH)
        return 0,0

class DocExec(DocAssign):
    '''at wrap time exec stmt in doc._nameSpace'''
    def __init__(self,stmt,lifetime='forever'):
        Flowable.__init__(self)
        self.args=stmt,lifetime

class DocPara(DocAssign):
    '''at wrap time create a paragraph with the value of expr as text
    if format is specified it should use %(__expr__)s for string interpolation
    of the expression expr (if any). It may also use %(name)s interpolations
    for other variables in the namespace.
    suitable defaults will be used if style and klass are None
    '''
    def __init__(self,expr,format=None,style=None,klass=None,escape=True):
        Flowable.__init__(self)
        self.expr=expr
        self.format=format
        self.style=style
        self.klass=klass
        self.escape=escape

    def func(self):
        expr = self.expr
        if expr:
            if not isinstance(expr,str): expr = str(expr)
            return self._doctemplateAttr('docEval')(expr)

    def add_content(self,*args):
        self._doctemplateAttr('frame').add_generated_content(*args)

    def get_value(self,aW,aH):
        value = self.funcWrap(aW,aH)
        if self.format:
            NS=self._doctemplateAttr('_nameSpace').copy()
            NS.update(dict(availableWidth=aW,availableHeight=aH))
            NS['__expr__'] = value
            value = self.format % NS
        else:
            value = str(value)
        return value

    def wrap(self,aW,aH):
        value = self.get_value(aW,aH)
        P = self.klass
        if not P:
            from reportlab.platypus.paragraph import Paragraph as P
        style = self.style
        if not style:
            from reportlab.lib.styles import getSampleStyleSheet
            style=getSampleStyleSheet()['Code']
        if self.escape:
            from xml.sax.saxutils import escape
            value=escape(value)
        self.add_content(P(value,style=style))
        return 0,0

class DocAssert(DocPara):
    def __init__(self,cond,format=None):
        Flowable.__init__(self)
        self.expr=cond
        self.format=format

    def funcWrap(self,aW,aH):
        self._cond = DocPara.funcWrap(self,aW,aH)
        return self._cond

    def wrap(self,aW,aH):
        value = self.get_value(aW,aH)
        if not bool(self._cond):
            raise AssertionError(value)
        return 0,0

class DocIf(DocPara):
    def __init__(self,cond,thenBlock,elseBlock=[]):
        Flowable.__init__(self)
        self.expr = cond
        self.blocks = elseBlock or [],thenBlock

    def checkBlock(self,block):
        if not isinstance(block,(list,tuple)):
            block = (block,)
        return block

    def wrap(self,aW,aH):
        self.add_content(*self.checkBlock(self.blocks[int(bool(self.funcWrap(aW,aH)))]))
        return 0,0

class DocWhile(DocIf):
    def __init__(self,cond,whileBlock):
        Flowable.__init__(self)
        self.expr = cond
        self.block = self.checkBlock(whileBlock)

    def wrap(self,aW,aH):
        if bool(self.funcWrap(aW,aH)):
            self.add_content(*(list(self.block)+[self]))
        return 0,0

class SetTopFlowables(NullDraw):
    _ZEROZSIZE = 1
    def __init__(self,F,show=False):
        self._F = F
        self._show = show

    def wrap(self,aW,aH):
        doc = getattr(getattr(self,'canv',None),'_doctemplate',None)
        if doc:
            doc._topFlowables = self._F
            if self._show and self._F:
                doc.frame._generated_content = self._F
        return 0,0

class SetPageTopFlowables(NullDraw):
    _ZEROZSIZE = 1
    def __init__(self,F,show=False):
        self._F = F
        self._show = show

    def wrap(self,aW,aH):
        doc = getattr(getattr(self,'canv',None),'_doctemplate',None)
        if doc:
            doc._pageTopFlowables = self._F
            if self._show and self._F:
                doc.frame._generated_content = self._F
        return 0,0
