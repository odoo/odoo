#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/platypus/flowables.py
__version__=''' $Id: flowables.py 2830 2006-04-05 15:18:32Z rgbecker $ '''
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
import string
from copy import deepcopy
from types import ListType, TupleType, StringType

from reportlab.lib.colors import red, gray, lightgrey
from reportlab.lib.utils import fp_str
from reportlab.pdfbase import pdfutils

from reportlab.rl_config import _FUZZ, overlapAttachedSpace
__all__=('TraceInfo','Flowable','XBox','Preformatted','Image','Spacer','PageBreak','SlowPageBreak',
        'CondPageBreak','KeepTogether','Macro','CallerMacro','ParagraphAndImage',
        'FailOnWrap','HRFlowable','PTOContainer','KeepInFrame','UseUpSpace')


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

    def drawOn(self, canvas, x, y, _sW=0):
        "Tell it to draw itself on the canvas.  Do not override"
        if _sW and hasattr(self,'hAlign'):
            a = self.hAlign
            if a in ['CENTER','CENTRE']:
                x = x + 0.5*_sW
            elif a == 'RIGHT':
                x = x + _sW
            elif a != 'LEFT':
                raise ValueError, "Bad hAlign value "+str(a)
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
        should split themselves and return a list of flowables"""
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

    def _frameName(self):
        f = getattr(self,'_frame',None)
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
        self.canv.setFont('Times-Roman',12)
        self.canv.drawCentredString(0.5*self.width, 0.5*self.height, self.text)

def _trimEmptyLines(lines):
    #don't want the first or last to be empty
    while len(lines) and string.strip(lines[0]) == '':
        lines = lines[1:]
    while len(lines) and string.strip(lines[-1]) == '':
        lines = lines[:-1]
    return lines

def _dedenter(text,dedent=0):
    '''
    tidy up text - carefully, it is probably code.  If people want to
    indent code within a source script, you can supply an arg to dedent
    and it will chop off that many character, otherwise it leaves
    left edge intact.
    '''
    lines = string.split(text, '\n')
    if dedent>0:
        templines = _trimEmptyLines(lines)
        lines = []
        for line in templines:
            line = string.rstrip(line[dedent:])
            lines.append(line)
    else:
        lines = _trimEmptyLines(lines)

    return lines

class Preformatted(Flowable):
    """This is like the HTML <PRE> tag.
    It attempts to display text exactly as you typed it in a fixed width "typewriter" font.
    The line breaks are exactly where you put
    them, and it will not be wrapped."""
    def __init__(self, text, style, bulletText = None, dedent=0):
        """text is the text to display. If dedent is set then common leading space
        will be chopped off the front (for example if the entire text is indented
        6 spaces or more then each line will have 6 spaces removed from the front).
        """
        self.style = style
        self.bulletText = bulletText
        self.lines = _dedenter(text,dedent)

    def __repr__(self):
        bT = self.bulletText
        H = "Preformatted("
        if bT is not None:
            H = "Preformatted(bulletText=%s," % repr(bT)
        return "%s'''\\ \n%s''')" % (H, string.join(self.lines,'\n'))

    def wrap(self, availWidth, availHeight):
        self.width = availWidth
        self.height = self.style.leading*len(self.lines)
        return (self.width, self.height)

    def split(self, availWidth, availHeight):
        #returns two Preformatted objects

        #not sure why they can be called with a negative height
        if availHeight < self.style.leading:
            return []

        linesThatFit = int(availHeight * 1.0 / self.style.leading)

        text1 = string.join(self.lines[0:linesThatFit], '\n')
        text2 = string.join(self.lines[linesThatFit:], '\n')
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
       are supported.  At the present time images as flowables are always centered horozontally
       in the frame. We allow for two kinds of lazyness to allow for many images in a document
       which could lead to file handle starvation.
       lazy=1 don't open image until required.
       lazy=2 open image when required then shut it.
    """
    _fixedWidth = 1
    _fixedHeight = 1
    def __init__(self, filename, width=None, height=None, kind='direct', mask="auto", lazy=1):
        """If size to draw at not specified, get it from the image."""
        self.hAlign = 'CENTER'
        self._mask = mask
        # if it is a JPEG, will be inlined within the file -
        # but we still need to know its size now
        fp = hasattr(filename,'read')
        if fp:
            self._file = filename
            self.filename = `filename`
        else:
            self._file = self.filename = filename
        if not fp and os.path.splitext(filename)[1] in ['.jpg', '.JPG', '.jpeg', '.JPEG']:
            from reportlab.lib.utils import open_for_read
            f = open_for_read(filename, 'b')
            info = pdfutils.readJPEGInfo(f)
            f.close()
            self.imageWidth = info[0]
            self.imageHeight = info[1]
            self._img = None
            self._setup(width,height,kind,0)
        elif fp:
            self._setup(width,height,kind,0)
        else:
            self._setup(width,height,kind,lazy)

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
        if img: self.imageWidth, self.imageHeight = img.getSize()
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

    def __getattr__(self,a):
        if a=='_img':
            from reportlab.lib.utils import ImageReader  #this may raise an error
            self._img = ImageReader(self._file)
            del self._file
            return self._img
        elif a in ('drawWidth','drawHeight','imageWidth','imageHeight'):
            self._setup_inner()
            return self.__dict__[a]
        raise AttributeError(a)

    def wrap(self, availWidth, availHeight):
        #the caller may decide it does not fit.
        return (self.drawWidth, self.drawHeight)

    def draw(self):
        lazy = self._lazy
        if lazy>=2: self._lazy = 1
        self.canv.drawImage(    self._img or self.filename,
                                0,
                                0,
                                self.drawWidth,
                                self.drawHeight,
                                mask=self._mask,
                                )
        if lazy>=2:
            self._img = None
            self._lazy = lazy

    def identity(self,maxLen=None):
        r = Flowable.identity(self,maxLen)
        if r[-4:]=='>...' and type(self.filename) is StringType:
            r = "%s filename=%s>" % (r[:-4],self.filename)
        return r

class Spacer(Flowable):
    """A spacer just takes up space and doesn't draw anything - it guarantees
       a gap between objects."""
    _fixedWidth = 1
    _fixedHeight = 1
    def __init__(self, width, height):
        self.width = width
        self.height = height

    def __repr__(self):
        return "%s(%s, %s)" % (self.__class__.__name__,self.width, self.height)

    def draw(self):
        pass

class UseUpSpace(Flowable):
    def __init__(self):
        pass

    def __repr__(self):
        return "%s()" % self.__class__.__name__

    def wrap(self, availWidth, availHeight):
        self.width = availWidth
        self.height = availHeight
        return (availWidth,availHeight-1e-8)  #step back a point

    def draw(self):
        pass

class PageBreak(UseUpSpace):
    """Move on to the next page in the document.
       This works by consuming all remaining space in the frame!"""

class SlowPageBreak(PageBreak):
    pass

class CondPageBreak(Spacer):
    """Throw a page if not enough vertical space"""
    def __init__(self, height):
        self.height = height

    def __repr__(self):
        return "CondPageBreak(%s)" %(self.height,)

    def wrap(self, availWidth, availHeight):
        if availHeight<self.height:
            return (availWidth, availHeight)
        return (0, 0)

def _listWrapOn(F,availWidth,canv,mergeSpace=1,obj=None,dims=None):
    '''return max width, required height for a list of flowables F'''
    W = 0
    H = 0
    pS = 0
    atTop = 1
    for f in F:
        w,h = f.wrapOn(canv,availWidth,0xfffffff)
        if dims is not None: dims.append((w,h))
        if w<=_FUZZ or h<=_FUZZ: continue
        W = max(W,w)
        H += h
        if not atTop:
            h = f.getSpaceBefore()
            if mergeSpace: h = max(h-pS,0) 
            H += h
        else:
            if obj is not None: obj._spaceBefore = f.getSpaceBefore()
            atTop = 0
        pS = f.getSpaceAfter()
        H += pS
    if obj is not None: obj._spaceAfter = pS
    return W, H-pS

def _flowableSublist(V):
    "if it isn't a list or tuple, wrap it in a list"
    if type(V) not in (ListType, TupleType): V = V is not None and [V] or []
    from doctemplate import LCActionFlowable
    assert not [x for x in V if isinstance(x,LCActionFlowable)],'LCActionFlowables not allowed in sublists'
    return V

class _ContainerSpace:  #Abstract some common container like behaviour
    def getSpaceBefore(self):
        for c in self._content:
            if not hasattr(c,'frameAction'):
                return c.getSpaceBefore()
        return 0

    def getSpaceAfter(self,content=None):
        #this needs 2.4
        #for c in reversed(content or self._content):
        reverseContent = (content or self._content)[:]
        reverseContent.reverse()
        for c in reverseContent:
            if not hasattr(c,'frameAction'):
                return c.getSpaceAfter()
        return 0

class KeepTogether(_ContainerSpace,Flowable):
    def __init__(self,flowables,maxHeight=None):
        self._content = _flowableSublist(flowables)
        self._maxHeight = maxHeight

    def __repr__(self):
        f = self._content
        L = map(repr,f)
        import string
        L = "\n"+string.join(L, "\n")
        L = string.replace(L, "\n", "\n  ")
        return "KeepTogether(%s,maxHeight=%s) # end KeepTogether" % (L,self._maxHeight)

    def wrap(self, aW, aH):
        dims = []
        W,H = _listWrapOn(self._content,aW,self.canv,dims=dims)
        self._H = H
        self._H0 = dims and dims[0][1] or 0
        self._wrapInfo = aW,aH
        return W, 0xffffff  # force a split

    def split(self, aW, aH):
        if getattr(self,'_wrapInfo',None)!=(aW,aH): self.wrap(aW,aH)
        S = self._content[:]
        C0 = self._H>aH and (not self._maxHeight or aH>self._maxHeight)
        C1 = self._H0>aH
        if C0 or C1:
            if C0:
                from doctemplate import FrameBreak
                A = FrameBreak
            else:
                from doctemplate import NullActionFlowable
                A = NullActionFlowable
            S.insert(0,A())
        return S

    def identity(self, maxLen=None):
        msg = "<KeepTogether at %s%s> containing :%s" % (hex(id(self)),self._frameName(),"\n".join([f.identity() for f in self._content]))
        if maxLen:
            return msg[0:maxLen]
        else:
            return msg

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
        exec self.command in globals(), {'canvas':self.canv}

class CallerMacro(Flowable):
    '''
    like Macro, but with callable command(s)
    drawCallable(self)
    wrapCallable(self,aW,aH)
    '''
    def __init__(self, drawCallable=None, wrapCallable=None):
        _ = lambda *args: None
        self._drawCallable = drawCallable or _
        self._wrapCallable = wrapCallable or _
    def __repr__(self):
        return "CallerMacro(%s)" % repr(self.command)
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
        nIW = int((hI+ypad)/leading)
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
            self.I.drawOn(canv,0,self.height-self.hI)
            self.P._offsets = self._offsets
            try:
                self.P.drawOn(canv,0,0)
            finally:
                del self.P._offsets
        else:
            self.I.drawOn(canv,self.width-self.wI-self.xpad,self.height-self.hI)
            self.P.drawOn(canv,0,0)

class FailOnWrap(Flowable):
    def wrap(self, availWidth, availHeight):
        raise ValueError("FailOnWrap flowable wrapped and failing as ordered!")

    def draw(self):
        pass

class FailOnDraw(Flowable):
    def wrap(self, availWidth, availHeight):
        return (0,0)

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
        if type(w) is type(''):
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

class _Container(_ContainerSpace):  #Abstract some common container like behaviour
    def drawOn(self, canv, x, y, _sW=0, scale=1.0, content=None, aW=None):
        '''we simulate being added to a frame'''
        pS = 0
        if aW is None: aW = self.width
        aW = scale*(aW+_sW)
        if content is None:
            content = self._content
        y += self.height*scale
        for c in content:
            w, h = c.wrapOn(canv,aW,0xfffffff)
            if w<_FUZZ or h<_FUZZ: continue
            if c is not content[0]: h += max(c.getSpaceBefore()-pS,0)
            y -= h
            c.drawOn(canv,x,y,_sW=aW-w)
            if c is not content[-1]:
                pS = c.getSpaceAfter()
                y -= pS

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
        if availHeight<0: return []
        canv = self.canv
        C = self._content
        x = i = H = pS = hx = 0
        n = len(C)
        I2W = {}
        for x in xrange(n):
            c = C[x]
            I = c._ptoinfo
            if I not in I2W.keys():
                T = I.trailer
                Hdr = I.header
                tW, tH = _listWrapOn(T, availWidth, self.canv)
                tSB = T[0].getSpaceBefore()
                I2W[I] = T,tW,tH,tSB
            else:
                T,tW,tH,tSB = I2W[I]
            _, h = c.wrapOn(canv,availWidth,0xfffffff)
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
        F = [UseUpSpace()]

        if len(SS)>1:
            R1 = C[:i] + SS[:1] + T + F
            R2 = Hdr + SS[1:]+C[i+1:]
        elif not i:
            return []
        else:
            R1 = C[:i]+T+F
            R2 = Hdr + C[i:]
        T =  R1 + [PTOContainer(R2,deepcopy(I.trailer),deepcopy(I.header))]
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

def _qsolve(h,(a,b)):
    '''solve the model v = a/s**2 + b/s for an s which gives us v==h'''
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
    def __init__(self, maxWidth, maxHeight, content=[], mergeSpace=1, mode='shrink', name=''):
        '''mode describes the action to take when overflowing
            error       raise an error in the normal way
            continue    ignore ie just draw it and report maxWidth, maxHeight
            shrink      shrinkToFit
            truncate    fit as much as possible
        '''
        self.name = name
        self.maxWidth = maxWidth
        self.maxHeight = maxHeight
        self.mode = mode
        assert mode in ('error','overflow','shrink','truncate'), '%s invalid mode value %s' % (self.identity(),mode)
        assert maxHeight>=0,  '%s invalid maxHeight value %s' % (self.identity(),maxHeight)
        if mergeSpace is None: mergeSpace = overlapAttachedSpace
        self.mergespace = mergeSpace
        self._content = content

    def _getAvailableWidth(self):
        return self.maxWidth - self._leftExtraIndent - self._rightExtraIndent

    def identity(self, maxLen=None):
        return "<%s at %s%s%s> size=%sx%s" % (self.__class__.__name__, hex(id(self)), self._frameName(),
                getattr(self,'name','') and (' name="%s"'% getattr(self,'name','')) or '',
                getattr(self,'maxWidth','') and (' maxWidth=%s'%fp_str(getattr(self,'maxWidth',0))) or '',
                getattr(self,'maxHeight','')and (' maxHeight=%s' % fp_str(getattr(self,'maxHeight')))or '')

    def wrap(self,availWidth,availHeight):
        from doctemplate import LayoutError
        mode = self.mode
        maxWidth = float(self.maxWidth or availWidth)
        maxHeight = float(self.maxHeight or availHeight)
        W, H = _listWrapOn(self._content,availWidth,self.canv)
        if (mode=='error' and (W>availWidth+_FUZZ or H>availHeight+_FUZZ)):
            ident = 'content %sx%s too large for %s' % (W,H,self.identity(30))
            #leave to keep apart from the raise
            raise LayoutError(ident)
        elif W<=availWidth+_FUZZ and H<=availHeight+_FUZZ:
            self.width = W-_FUZZ      #we take what we get
            self.height = H-_FUZZ
        elif (maxWidth>=availWidth+_FUZZ or maxHeight>=availHeight+_FUZZ):
            ident = 'Specified size too large for available space %sx%s in %s' % (availWidth,availHeight,self.identity(30))
            #leave to keep apart from the raise
            raise LayoutError(ident)
        elif mode in ('overflow','truncate'):   #we lie
            self.width = min(maxWidth,W)-_FUZZ
            self.height = min(maxHeight,H)-_FUZZ
        else:
            def func(x):
                W, H = _listWrapOn(self._content,x*availWidth,self.canv)
                W /= x
                H /= x
                return W, H
            W0 = W
            H0 = H
            s0 = 1
            if W>maxWidth+_FUZZ:
                #squeeze out the excess width and or Height
                s1 = W/maxWidth
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

class ImageAndFlowables(_Container,Flowable):
    '''combine a list of flowables and an Image'''
    def __init__(self,I,F,imageLeftPadding=0,imageRightPadding=3,imageTopPadding=0,imageBottomPadding=3,
                    imageSide='right'):
        self._content = _flowableSublist(F)
        self._I = I
        self._irpad = imageRightPadding
        self._ilpad = imageLeftPadding
        self._ibpad = imageBottomPadding
        self._itpad = imageTopPadding
        self._side = imageSide

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
        if hasattr(self,'_wrapArgs'):
            if self._wrapArgs==(availWidth,availHeight):
                return self.width,self.height
            self._reset()
        self._wrapArgs = availWidth, availHeight
        wI, hI = self._I.wrap(availWidth,availHeight)
        self._wI = wI
        self._hI = hI
        ilpad = self._ilpad
        irpad = self._irpad
        ibpad = self._ibpad
        itpad = self._itpad
        self._iW = availWidth - irpad - wI - ilpad
        aH = itpad + hI + ibpad
        W,H0,self._C0,self._C1 = self._findSplit(canv,self._iW,aH)
        self.width = availWidth
        aH = self._aH = max(aH,H0)
        if not self._C1:
            self.height = aH
        else:
            W1,H1 = _listWrapOn(self._C1,availWidth,canv)
            self.height = aH+H1
        return self.width, self.height

    def split(self,availWidth, availHeight):
        if hasattr(self,'_wrapArgs'):
            if self._wrapArgs!=(availWidth,availHeight):
                self._reset()
        W,H=self.wrap(availWidth,availHeight)
        if self._aH>availHeight: return []
        C1 = self._C1
        if C1:
            c0 = C1[0]
            S = c0.split(availWidth,availHeight-self._aH)
            if not S:
                self._C1 = []
                self.height = self._aH
            else:
                self._C1 = [S[0]]
                self.height = self._aH + S[0].height
                C1 = S[1:]+C1[1:]
        else:
            self._C1 = []
            self.height = self._aH
        return [self]+C1

    def drawOn(self, canv, x, y, _sW=0):
        if self._side=='left':
            Ix = x + self._ilpad
            Fx = Ix+ self._irpad + self._wI
        else:
            Ix = x + self.width-self._wI-self._irpad - self._ilpad
            Fx = x
        self._I.drawOn(canv,Ix,y+self.height-self._itpad-self._hI)
        _Container.drawOn(self, canv, Fx, y, content=self._C0, aW=self._iW)
        if self._C1:
            _Container.drawOn(self, canv, x, y-self._aH,content=self._C1)

    def _findSplit(self,canv,availWidth,availHeight,mergeSpace=1,obj=None):
        '''return max width, required height for a list of flowables F'''
        W = 0
        H = 0
        pS = sB = 0
        atTop = 1
        F = self._content
        for i,f in enumerate(F):
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
            if H>=availHeight:
                return W, availHeight, F[:i],F[i:]
            H += h
            if H>availHeight:
                from paragraph import Paragraph
                aH = availHeight-(H-h)
                if isinstance(f,(Paragraph,Preformatted)):
                    leading = f.style.leading
                    nH = leading*int(aH/float(leading))+_FUZZ
                    if nH<aH: nH += leading
                    availHeight += nH-aH
                    aH = nH
                S = deepcopy(f).split(availWidth,aH)
                if not S:
                    return W, availHeight, F[:i],F[i:]
                else:
                    return W,availHeight,F[:i]+S[:1],S[1:]+F[i+1:]
            pS = f.getSpaceAfter()
            H += pS
        if obj is not None: obj._spaceAfter = pS
        return W, H-pS, F, []
