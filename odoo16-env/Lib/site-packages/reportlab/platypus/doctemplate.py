#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/platypus/doctemplate.py
__all__ = (
        'ActionFlowable',
        'BaseDocTemplate',
        'CurrentFrameFlowable',
        'FrameActionFlowable',
        'FrameBreak',
        'Indenter',
        'IndexingFlowable',
        'LayoutError',
        'LCActionFlowable',
        'NextFrameFlowable',
        'NextPageTemplate',
        'NotAtTopPageBreak',
        'NullActionFlowable',
        'PageAccumulator',
        'PageBegin',
        'PageTemplate',
        'SimpleDocTemplate',
        )
__version__='3.5.20'

__doc__="""
This module contains the core structure of platypus.

rlatypus constructs documents.  Document styles are determined by DocumentTemplates.

Each DocumentTemplate contains one or more PageTemplates which defines the look of the
pages of the document.

Each PageTemplate has a procedure for drawing the "non-flowing" part of the page
(for example the header, footer, page number, fixed logo graphic, watermark, etcetera) and
a set of Frames which enclose the flowing part of the page (for example the paragraphs,
tables, or non-fixed diagrams of the text).

A document is built when a DocumentTemplate is fed a sequence of Flowables.
The action of the build consumes the flowables in order and places them onto
frames on pages as space allows.  When a frame runs out of space the next frame
of the page is used.  If no frame remains a new page is created.  A new page
can also be created if a page break is forced.

The special invisible flowable NextPageTemplate can be used to specify
the page template for the next page (which by default is the one being used
for the current frame).
"""

from reportlab.platypus.flowables import *
from reportlab.platypus.flowables import _ContainerSpace
from reportlab.lib.units import inch
from reportlab.lib import rl_safe_eval
from reportlab.platypus.paragraph import Paragraph
from reportlab.platypus.frames import Frame
from reportlab.rl_config import defaultPageSize, verbose
import reportlab.lib.sequencer
from reportlab.pdfgen import canvas
from reportlab.lib.utils import isSeq, encode_label, decode_label, annotateException, strTypes, _rl_repr

try:
    set
except NameError:
    from sets import Set as set

import sys
import logging
logger = logging.getLogger("reportlab.platypus")

class LayoutError(Exception):
    pass

def _fSizeString(f):
    #used to get size during error messages
    w=getattr(f,'width',None)
    if w is None:
        w=getattr(f,'_width',None)

    h=getattr(f,'height',None)
    if h is None:
        h=getattr(f,'_height',None)
    #tables in particular may have some nasty large culprit
    if hasattr(f, '_culprit'):
        c = ', %s, ' % f._culprit()
    else:
        c = ''
    if w is not None or h is not None:
        if w is None: w='???'
        if h is None: h='???'
        return '(%s x %s)%s' % (w,h,c)
    return ''

def _doNothing(canvas, doc):
    "Dummy callback for onPage"
    pass

class PTCycle(list):
    def __new__(cls,*args,**kwds):
        self = list.__new__(cls,*args,**kwds)
        self._restart = 0
        self._idx = 0
        return self

    @property
    def next_value(self):
        v = self[self._idx]
        self._idx += 1
        if self._idx>=len(self):
            self._idx = self._restart
        return v

    @property
    def peek(self):
        return self[self._idx]

class IndexingFlowable(Flowable):
    """Abstract interface definition for flowables which might
    hold references to other pages or themselves be targets
    of cross-references.  XRefStart, XRefDest, Table of Contents,
    Indexes etc."""
    def isIndexing(self):
        return 1

    def isSatisfied(self):
        return 1

    def notify(self, kind, stuff):
        """This will be called by the framework wherever 'stuff' happens.
        'kind' will be a value that can be used to decide whether to
        pay attention or not."""
        pass

    def beforeBuild(self):
        """Called by multiBuild before it starts; use this to clear
        old contents"""
        pass

    def afterBuild(self):
        """Called after build ends but before isSatisfied"""
        pass

class ActionFlowable(Flowable):
    '''This Flowable is never drawn, it can be used for data driven controls
       For example to change a page template (from one column to two, for example)
       use NextPageTemplate which creates an ActionFlowable.
    '''
    def __init__(self,action=()):
        #must call super init to ensure it has a width and height (of zero),
        #as in some cases the packer might get called on it...
        Flowable.__init__(self)
        if not isSeq(action):
            action = (action,)
        self.action = tuple(action)

    def apply(self,doc):
        '''
        This is called by the doc.build processing to allow the instance to
        implement its behaviour
        '''
        action = self.action[0]
        args = tuple(self.action[1:])
        arn = 'handle_'+action
        if arn=="handle_nextPageTemplate" and args[0]=='main':
            pass
        try:
            getattr(doc,arn)(*args)
        except AttributeError as aerr:
            if aerr.args[0]==arn:
                raise NotImplementedError("Can't handle ActionFlowable(%s)" % action)
            else:
                raise
        except:
            annotateException("\nhandle_%s args=%s"%(action,ascii(args)))

    def __call__(self):
        return self

    def identity(self, maxLen=None):
        return "ActionFlowable: %s%s" % (str(self.action),self._frameName())

class NullActionFlowable(ActionFlowable):
    '''an ActionFlowable that does nothing'''
    def apply(self,doc):
        pass

class LCActionFlowable(ActionFlowable):
    locChanger = 1                  #we cause a frame or page change

    def wrap(self, availWidth, availHeight):
        '''Should never be called.'''
        raise NotImplementedError('%s.wrap should never be called' % self.__class__.__name__)

    def draw(self):
        '''Should never be called.'''
        raise NotImplementedError('%s.draw should never be called' % self.__class__.__name__)

class NextFrameFlowable(ActionFlowable):
    locChanger = 1                  #we cause a frame or page change
    def __init__(self,ix,resume=0):
        ActionFlowable.__init__(self,('nextFrame',ix,resume))

class CurrentFrameFlowable(LCActionFlowable):
    def __init__(self,ix,resume=0):
        ActionFlowable.__init__(self,('currentFrame',ix,resume))

class NullActionFlowable(ActionFlowable):
    def apply(self,doc):
        pass

class _FrameBreak(LCActionFlowable):
    '''
    A special ActionFlowable that allows setting doc._nextFrameIndex

    eg story.append(FrameBreak('mySpecialFrame'))
    '''
    def __call__(self,ix=None,resume=0):
        r = self.__class__(self.action+(resume,))
        r._ix = ix
        return r

    def apply(self,doc):
        if getattr(self,'_ix',None):
            doc.handle_nextFrame(self._ix)
        ActionFlowable.apply(self,doc)

FrameBreak = _FrameBreak('frameEnd')
PageBegin = LCActionFlowable('pageBegin')

def _evalMeasurement(n):
    if isinstance(n,str):
        from reportlab.platypus.paraparser import _num
        n = _num(n)
        if isSeq(n): n = n[1]
    return n

class FrameActionFlowable(Flowable):
    _fixedWidth = _fixedHeight = 1
    def __init__(self,*arg,**kw):
        raise NotImplementedError('%s.__init__ should never be called for abstract Class'%self.__class__.__name__)

    def frameAction(self,frame):
        raise NotImplementedError('%s.frameAction should never be called for abstract Class'%self.__class__.__name__)

class Indenter(FrameActionFlowable):
    """Increases or decreases left and right margins of frame.

    This allows one to have a 'context-sensitive' indentation
    and makes nested lists way easier.
    """
    _ZEROSIZE=True
    width=0
    height=0
    def __init__(self, left=0, right=0):
        self.left = _evalMeasurement(left)
        self.right = _evalMeasurement(right)

    def frameAction(self, frame):
        frame._leftExtraIndent += self.left
        frame._rightExtraIndent += self.right

class NotAtTopPageBreak(FrameActionFlowable):
    locChanger = 1                  #we cause a frame or page change
    def __init__(self,nextTemplate=None):
        self.nextTemplate = nextTemplate

    def frameAction(self,frame):
        if not frame._atTop:
            frame.add_generated_content(PageBreak(nextTemplate=self.nextTemplate))

class NextPageTemplate(ActionFlowable):
    locChanger = 1                  #we cause a frame or page change
    """When you get to the next page, use the template specified (change to two column, for example)  """
    def __init__(self,pt):
        ActionFlowable.__init__(self,('nextPageTemplate',pt))

class PageTemplate:
    """
    essentially a list of Frames and an onPage routine to call at the start
    of a page when this is selected. onPageEnd gets called at the end.
    derived classes can also implement beforeDrawPage and afterDrawPage if they want
    """
    def __init__(self,id=None,frames=[],onPage=_doNothing, onPageEnd=_doNothing,
                 pagesize=None, autoNextPageTemplate=None,
                 cropBox=None,
                 artBox=None,
                 trimBox=None,
                 bleedBox=None,
                 ):
        frames = frames or []
        if not isSeq(frames): frames = [frames]
        assert [x for x in frames if not isinstance(x,Frame)]==[], "frames argument error"
        self.id = id
        self.frames = frames
        self.onPage = onPage
        self.onPageEnd = onPageEnd
        self.pagesize = pagesize
        self.autoNextPageTemplate = autoNextPageTemplate
        self.cropBox = cropBox
        self.artBox = artBox
        self.trimBox = trimBox
        self.bleedBox = bleedBox

    def beforeDrawPage(self,canv,doc):
        """Override this if you want additional functionality or prefer
        a class based page routine.  Called before any flowables for
        this page are processed."""
        pass

    def checkPageSize(self,canv,doc):
        """This gets called by the template framework
        If canv size != template size then the canv size is set to
        the template size or if that's not available to the
        doc size.
        """
        #### NEVER EVER EVER COMPARE FLOATS FOR EQUALITY
        #RGB converting pagesizes to ints means we are accurate to one point
        #RGB I suggest we should be aiming a little better
        cp = None
        dp = None
        sp = None
        if canv._pagesize: cp = list(map(int, canv._pagesize))
        if self.pagesize: sp = list(map(int, self.pagesize))
        if doc.pagesize: dp = list(map(int, doc.pagesize))
        if cp!=sp:
            if sp:
                canv.setPageSize(self.pagesize)
            elif cp!=dp:
                canv.setPageSize(doc.pagesize)
        for box in 'crop','art','trim','bleed':
            size = getattr(self,box+'Box',None)
            if size:
                canv.setCropBox(size,name=box)

    def afterDrawPage(self, canv, doc):
        """This is called after the last flowable for the page has
        been processed.  You might use this if the page header or
        footer needed knowledge of what flowables were drawn on
        this page."""
        pass

def _addGeneratedContent(flowables,frame):
    S = getattr(frame,'_generated_content',None)
    if S:
        flowables[0:0] = S
        del frame._generated_content

class onDrawStr(str):
    def __new__(cls,value,onDraw,label,kind=None):
        self = str.__new__(cls,value)
        self.onDraw = onDraw
        self.kind = kind
        self.label = label
        return self

    def __getnewargs__(self):
        return str(self),self.onDraw,self.label,self.kind

class PageAccumulator:
    '''gadget to accumulate information in a page
    and then allow it to be interrogated at the end
    of the page'''
    _count = 0
    def __init__(self,name=None):
        if name is None:
            name = self.__class__.__name__+str(self.__class__._count)
            self.__class__._count += 1
        self.name = name
        self.data = []

    def reset(self):
        self.data[:] = []

    def add(self,*args):
        self.data.append(args)

    def onDrawText(self,*args):
        return '<onDraw name="%s" label="%s" />' % (self.name,encode_label(args))

    def __call__(self,canv,kind,label):
        self.add(*decode_label(label))

    def attachToPageTemplate(self,pt):
        if pt.onPage:
            def onPage(canv,doc,oop=pt.onPage):
                self.onPage(canv,doc)
                oop(canv,doc)
        else:
            def onPage(canv,doc):
                self.onPage(canv,doc)
        pt.onPage = onPage
        if pt.onPageEnd:
            def onPageEnd(canv,doc,oop=pt.onPageEnd):
                self.onPageEnd(canv,doc)
                oop(canv,doc)
        else:
            def onPageEnd(canv,doc):
                self.onPageEnd(canv,doc)
        pt.onPageEnd = onPageEnd

    def onPage(self,canv,doc):
        '''this will be called at the start of the page'''
        setattr(canv,self.name,self)    #push ourselves onto the canvas
        self.reset()

    def onPageEnd(self,canv,doc):
        '''this will be called at the end of a page'''
        self.pageEndAction(canv,doc)
        try:
            delattr(canv,self.name)
        except:
            pass
        self.reset()

    def pageEndAction(self,canv,doc):
        '''this should be overridden to do something useful'''
        pass

    def onDrawStr(self,value,*args):
        return onDrawStr(value,self,encode_label(args))

def _ktAllow(f):
    '''return true if allowed in containers like KeepTogether'''
    return not (isinstance(f,(_ContainerSpace,DocIf,DocWhile)) or getattr(f,'locChanger',False))

class BaseDocTemplate:
    """
    First attempt at defining a document template class.

    The basic idea is simple.

    1)  The document has a list of data associated with it
        this data should derive from flowables. We'll have
        special classes like PageBreak, FrameBreak to do things
        like forcing a page end etc.

    2)  The document has one or more page templates.

    3)  Each page template has one or more frames.

    4)  The document class provides base methods for handling the
        story events and some reasonable methods for getting the
        story flowables into the frames.

    5)  The document instances can override the base handler routines.

    Most of the methods for this class are not called directly by the user,
    but in some advanced usages they may need to be overridden via subclassing.

    EXCEPTION: doctemplate.build(...) must be called for most reasonable uses
    since it builds a document using the page template.

    Each document template builds exactly one document into a file specified
    by the filename argument on initialization.

    Possible keyword arguments for the initialization:

    - pageTemplates: A list of templates.  Must be nonempty.  Names
      assigned to the templates are used for referring to them so no two used
      templates should have the same name.  For example you might want one template
      for a title page, one for a section first page, one for a first page of
      a chapter and two more for the interior of a chapter on odd and even pages.
      If this argument is omitted then at least one pageTemplate should be provided
      using the addPageTemplates method before the document is built.
    - pageSize: a 2-tuple or a size constant from reportlab/lib/pagesizes.pu.
      Used by the SimpleDocTemplate subclass which does NOT accept a list of
      pageTemplates but makes one for you; ignored when using pageTemplates.

    - showBoundary: if set draw a box around the frame boundaries.
    - leftMargin:
    - rightMargin:
    - topMargin:
    - bottomMargin:  Margin sizes in points (default 1 inch).  These margins may be
      overridden by the pageTemplates.  They are primarily of interest for the
      SimpleDocumentTemplate subclass.

    - allowSplitting:  If set flowables (eg, paragraphs) may be split across frames or pages
      (default: 1)
    - title: Internal title for document (does not automatically display on any page)
    - author: Internal author for document (does not automatically display on any page)
    """
    _initArgs = {   'pagesize':defaultPageSize,
                    'pageTemplates':[],
                    'showBoundary':0,
                    'leftMargin':inch,
                    'rightMargin':inch,
                    'topMargin':inch,
                    'bottomMargin':inch,
                    'allowSplitting':1,
                    'title':None,
                    'author':None,
                    'subject':None,
                    'creator':None,
                    'producer':None,
                    'keywords':[],
                    'invariant':None,
                    'pageCompression':None,
                    '_pageBreakQuick':1,
                    'rotation':0,
                    '_debug':0,
                    'encrypt': None,
                    'cropMarks': None,
                    'enforceColorSpace': None,
                    'displayDocTitle': None,
                    'lang': None,
                    'initialFontName': None,
                    'initialFontSize': None,
                    'initialLeading': None,
                    'cropBox': None,
                    'artBox': None,
                    'trimBox': None,
                    'bleedBox': None,
                    'keepTogetherClass': KeepTogether,
                    'hideToolbar': None,
                    'hideMenubar': None,
                    'hideWindowUI': None,
                    'fitWindow': None,
                    'centerWindow': None,
                    'nonFullScreenPageMode': None,
                    'direction': None,
                    'viewArea': None,
                    'viewClip': None,
                    'printArea': None,
                    'printClip': None,
                    'printScaling': None,
                    'duplex': None,
                    }
    _invalidInitArgs = ()
    _firstPageTemplateIndex = 0

    def __init__(self, filename, **kw):
        """create a document template bound to a filename (see class documentation for keyword arguments)"""
        self.filename = filename
        self._nameSpace = dict(doc=self)
        self._lifetimes = {}

        for k in self._initArgs.keys():
            if k not in kw:
                v = self._initArgs[k]
            else:
                if k in self._invalidInitArgs:
                    raise ValueError("Invalid argument %s" % k)
                v = kw[k]
            setattr(self,k,v)

        p = self.pageTemplates
        self.pageTemplates = []
        self.addPageTemplates(p)

        # facility to assist multi-build and cross-referencing.
        # various hooks can put things into here - key is what
        # you want, value is a page number.  This can then be
        # passed to indexing flowables.
        self._pageRefs = {}
        self._indexingFlowables = []

        #callback facility for progress monitoring
        self._onPage = None
        self._onProgress = None
        self._flowableCount = 0  # so we know how far to go

        #infinite loop detection if we start doing lots of empty pages
        self._curPageFlowableCount = 0
        self._emptyPages = 0
        self._emptyPagesAllowed = 10

        #context sensitive margins - set by story, not from outside
        self._leftExtraIndent = 0.0
        self._rightExtraIndent = 0.0
        self._topFlowables = []
        self._pageTopFlowables = []
        self._frameBGs = []

        self._calc()
        self.afterInit()

    def _calc(self):
        self._rightMargin = self.pagesize[0] - self.rightMargin
        self._topMargin = self.pagesize[1] - self.topMargin
        self.width = self._rightMargin - self.leftMargin
        self.height = self._topMargin - self.bottomMargin

    def setPageCallBack(self, func):
        'Simple progress monitor - func(pageNo) called on each new page'
        self._onPage = func

    def setProgressCallBack(self, func):
        '''Cleverer progress monitor - func(typ, value) called regularly'''
        self._onProgress = func

    def clean_hanging(self):
        'handle internal postponed actions'
        while len(self._hanging):
            self.handle_flowable(self._hanging)

    def addPageTemplates(self,pageTemplates):
        'add one or a sequence of pageTemplates'
        if not isSeq(pageTemplates):
            pageTemplates = [pageTemplates]
        #this test below fails due to inconsistent imports!
        #assert filter(lambda x: not isinstance(x,PageTemplate), pageTemplates)==[], "pageTemplates argument error"
        for t in pageTemplates:
            self.pageTemplates.append(t)

    def handle_documentBegin(self):
        '''implement actions at beginning of document'''
        self._hanging = [PageBegin]
        if isinstance(self._firstPageTemplateIndex,list):
            self.handle_nextPageTemplate(self._firstPageTemplateIndex)
            self._setPageTemplate()
        else:
            self.pageTemplate = self.pageTemplates[self._firstPageTemplateIndex]
        self.page = 0
        self.beforeDocument()

    def handle_pageBegin(self):
        """Perform actions required at beginning of page.
        shouldn't normally be called directly"""
        self.page += 1
        if self._debug: logger.debug("beginning page %d" % self.page)
        self.pageTemplate.beforeDrawPage(self.canv,self)
        self.pageTemplate.checkPageSize(self.canv,self)
        self.pageTemplate.onPage(self.canv,self)
        for f in self.pageTemplate.frames: f._reset()
        self.beforePage()
        #keep a count of flowables added to this page.  zero indicates bad stuff
        self._curPageFlowableCount = 0
        if hasattr(self,'_nextFrameIndex'):
            del self._nextFrameIndex
        self.frame = self.pageTemplate.frames[0]
        self.frame._debug = self._debug
        self.handle_frameBegin(pageTopFlowables=self._pageTopFlowables)

    def _setPageTemplate(self):
        if hasattr(self,'_nextPageTemplateCycle'):
            #they are cycling through pages'; we keep the index
            self.pageTemplate = self._nextPageTemplateCycle.next_value
        elif hasattr(self,'_nextPageTemplateIndex'):
            self.pageTemplate = self.pageTemplates[self._nextPageTemplateIndex]
            del self._nextPageTemplateIndex
        elif self.pageTemplate.autoNextPageTemplate:
            self.handle_nextPageTemplate(self.pageTemplate.autoNextPageTemplate)
            self.pageTemplate = self.pageTemplates[self._nextPageTemplateIndex]

    def _samePT(self,npt):
        if isSeq(npt):
            return getattr(self,'_nextPageTemplateCycle',[])
        if isinstance(npt,strTypes):
            return npt == (self.pageTemplates[self._nextPageTemplateIndex].id if hasattr(self,'_nextPageTemplateIndex') else self.pageTemplate.id)
        if isinstance(npt,int) and 0<=npt<len(self.pageTemplates):
            if hasattr(self,'_nextPageTemplateIndex'):
                return npt==self._nextPageTemplateIndex
            return npt==self.pageTemplates.find(self.pageTemplate)

    def handle_pageEnd(self):
        ''' show the current page
            check the next page template
            hang a page begin
        '''
        self._removeVars(('page','frame'))
        self._leftExtraIndent = self.frame._leftExtraIndent
        self._rightExtraIndent = self.frame._rightExtraIndent
        self._frameBGs = self.frame._frameBGs
        #detect infinite loops...
        if self._curPageFlowableCount == 0:
            self._emptyPages += 1
        else:
            self._emptyPages = 0
        if self._emptyPages >= self._emptyPagesAllowed:
            if 1:
                ident = "More than %d pages generated without content - halting layout.  Likely that a flowable is too large for any frame." % self._emptyPagesAllowed
                #leave to keep apart from the raise
                raise LayoutError(ident)
            else:
                pass    #attempt to restore to good state
        else:
            if self._onProgress:
                self._onProgress('PAGE', self.canv.getPageNumber())
            self.pageTemplate.afterDrawPage(self.canv, self)
            self.pageTemplate.onPageEnd(self.canv, self)
            self.afterPage()
            if self._debug: logger.debug("ending page %d" % self.page)
            self.canv.setPageRotation(getattr(self.pageTemplate,'rotation',self.rotation))
            self.canv.showPage()
            self._setPageTemplate()
            if self._emptyPages==0:
                pass    #store good state here
        self._hanging.append(PageBegin)

    def handle_pageBreak(self,slow=None):
        '''some might choose not to end all the frames'''
        if self._pageBreakQuick and not slow:
            self.handle_pageEnd()
        else:
            n = len(self._hanging)
            while len(self._hanging)==n:
                self.handle_frameEnd()

    def handle_frameBegin(self,resume=0,pageTopFlowables=None):
        '''What to do at the beginning of a frame'''
        f = self.frame
        if f._atTop:
            boundary = self.frame.showBoundary or self.showBoundary
            if boundary:
                self.frame.drawBoundary(self.canv,boundary)
        f._leftExtraIndent = self._leftExtraIndent
        f._rightExtraIndent = self._rightExtraIndent
        f._frameBGs = self._frameBGs
        if pageTopFlowables:
            self._hanging.extend(pageTopFlowables)
        if self._topFlowables:
            self._hanging.extend(self._topFlowables)

    def handle_frameEnd(self,resume=0):
        ''' Handles the semantics of the end of a frame. This includes the selection of
            the next frame or if this is the last frame then invoke pageEnd.
        '''
        self._removeVars(('frame',))
        self._leftExtraIndent = self.frame._leftExtraIndent
        self._rightExtraIndent = self.frame._rightExtraIndent
        self._frameBGs = self.frame._frameBGs

        if hasattr(self,'_nextFrameIndex'):
            self.frame = self.pageTemplate.frames[self._nextFrameIndex]
            self.frame._debug = self._debug
            del self._nextFrameIndex
            self.handle_frameBegin(resume)
        else:
            f = self.frame
            if hasattr(f,'lastFrame') or f is self.pageTemplate.frames[-1]:
                self.handle_pageEnd()
                self.frame = None
            else:
                self.frame = self.pageTemplate.frames[self.pageTemplate.frames.index(f) + 1]
                self.frame._debug = self._debug
                self.handle_frameBegin()

    def handle_nextPageTemplate(self,pt):
        '''On endPage change to the page template with name or index pt'''
        if isinstance(pt,strTypes):
            if hasattr(self, '_nextPageTemplateCycle'): del self._nextPageTemplateCycle
            for t in self.pageTemplates:
                if t.id == pt:
                    self._nextPageTemplateIndex = self.pageTemplates.index(t)
                    return
            raise ValueError("can't find template('%s')"%pt)
        elif isinstance(pt,int):
            if hasattr(self, '_nextPageTemplateCycle'): del self._nextPageTemplateCycle
            self._nextPageTemplateIndex = pt
        elif isSeq(pt):
            #used for alternating left/right pages
            #collect the refs to the template objects, complain if any are bad
            c = PTCycle()
            for ptn in pt:
                found = 0
                if ptn=='*':    #special case name used to short circuit the iteration
                    c._restart = len(c)
                    continue
                for t in self.pageTemplates:
                    if t.id == ptn:
                        c.append(t)
                        found = 1
                if not found:
                    raise ValueError("Cannot find page template called %s" % ptn)
            if not c:
                raise ValueError("No valid page templates in cycle")
            elif c._restart>len(c):
                raise ValueError("Invalid cycle restart position")

            #ensure we start on the first one
            self._nextPageTemplateCycle = c
        else:
            raise TypeError("argument pt should be string or integer or list")

    def _peekNextPageTemplate(self,pt):
        if isinstance(pt,strTypes):
            for t in self.pageTemplates:
                if t.id == pt:
                    return t
            raise ValueError("can't find template('%s')"%pt)
        elif isinstance(pt,int):
            self.pageTemplates[pt]
        elif isSeq(pt):
            #used for alternating left/right pages
            #collect the refs to the template objects, complain if any are bad
            c = PTCycle()
            for ptn in pt:
                found = 0
                if ptn=='*':    #special case name used to short circuit the iteration
                    c._restart = len(c)
                    continue
                for t in self.pageTemplates:
                    if t.id == ptn:
                        c.append(t)
                        found = 1
                if not found:
                    raise ValueError("Cannot find page template called %s" % ptn)
            if not c:
                raise ValueError("No valid page templates in cycle")
            elif c._restart>len(c):
                raise ValueError("Invalid cycle restart position")
            return c.peek
        else:
            raise TypeError("argument pt should be string or integer or list")

    def _peekNextFrame(self):
        '''intended to be used by extreme flowables'''
        if hasattr(self,'_nextFrameIndex'):
            return self.pageTemplate.frames[self._nextFrameIndex]
        f = self.frame
        if hasattr(f,'lastFrame') or f is self.pageTemplate.frames[-1]:
            if hasattr(self,'_nextPageTemplateCycle'):
                #they are cycling through pages'; we keep the index
                pageTemplate = self._nextPageTemplateCycle.peek
            elif hasattr(self,'_nextPageTemplateIndex'):
                pageTemplate = self.pageTemplates[self._nextPageTemplateIndex]
            elif self.pageTemplate.autoNextPageTemplate:
                pageTemplate = self._peekNextPageTemplate(self.pageTemplate.autoNextPageTemplate)
            else:
                pageTemplate = self.pageTemplate
            return pageTemplate.frames[0]
        else:
            return self.pageTemplate.frames[self.pageTemplate.frames.index(f) + 1]

    def handle_nextFrame(self,fx,resume=0):
        '''On endFrame change to the frame with name or index fx'''
        if isinstance(fx,strTypes):
            for f in self.pageTemplate.frames:
                if f.id == fx:
                    self._nextFrameIndex = self.pageTemplate.frames.index(f)
                    return
            raise ValueError("can't find frame('%s') in %r(%s) which has frames %r"%(fx,self.pageTemplate,self.pageTemplate.id,[(f,f.id) for f in self.pageTemplate.frames]))
        elif isinstance(fx,int):
            self._nextFrameIndex = fx
        else:
            raise TypeError("argument fx should be string or integer")

    def handle_currentFrame(self,fx,resume=0):
        '''change to the frame with name or index fx'''
        self.handle_nextFrame(fx,resume)
        self.handle_frameEnd(resume)

    def handle_breakBefore(self, flowables):
        '''preprocessing step to allow pageBreakBefore and frameBreakBefore attributes'''
        first = flowables[0]
        # if we insert a page break before, we'll process that, see it again,
        # and go in an infinite loop.  So we need to set a flag on the object
        # saying 'skip me'.  This should be unset on the next pass
        if hasattr(first, '_skipMeNextTime'):
            delattr(first, '_skipMeNextTime')
            return
        # this could all be made much quicker by putting the attributes
        # in to the flowables with a defult value of 0
        if hasattr(first,'pageBreakBefore') and first.pageBreakBefore == 1:
            first._skipMeNextTime = 1
            first.insert(0, PageBreak())
            return
        if hasattr(first,'style') and hasattr(first.style, 'pageBreakBefore') and first.style.pageBreakBefore == 1:
            first._skipMeNextTime = 1
            flowables.insert(0, PageBreak())
            return
        if hasattr(first,'frameBreakBefore') and first.frameBreakBefore == 1:
            first._skipMeNextTime = 1
            flowables.insert(0, FrameBreak())
            return
        if hasattr(first,'style') and hasattr(first.style, 'frameBreakBefore') and first.style.frameBreakBefore == 1:
            first._skipMeNextTime = 1
            flowables.insert(0, FrameBreak())
            return

    def handle_keepWithNext(self, flowables):
        "implements keepWithNext"
        i = 0
        n = len(flowables)
        while i<n and flowables[i].getKeepWithNext() and _ktAllow(flowables[i]): i += 1
        if i:
            if i<n and _ktAllow(flowables[i]): i += 1
            K = self.keepTogetherClass(flowables[:i])
            mbe = getattr(self,'_multiBuildEdits',None)
            if mbe:
                for f in K._content[:-1]:
                    if hasattr(f,'keepWithNext'):
                        mbe((setattr,f,'keepWithNext',f.keepWithNext))
                    else:
                        mbe((delattr,f,'keepWithNext')) #must get it from a style
                    f.__dict__['keepWithNext'] = 0
            else:
                for f in K._content[:-1]:
                    f.__dict__['keepWithNext'] = 0
            del flowables[:i]
            flowables.insert(0,K)

    def _fIdent(self,f,maxLen=None,frame=None):
        if frame: f._frame = frame
        try:
            return f.identity(maxLen)
        finally:
            if frame: del f._frame

    def handle_flowable(self,flowables):
        '''try to handle one flowable from the front of list flowables.'''

        #allow document a chance to look at, modify or ignore
        #the object(s) about to be processed
        self.filterFlowables(flowables)

        f = flowables[0]
        if f:
            self.handle_breakBefore(flowables)
            self.handle_keepWithNext(flowables)
            f = flowables[0]
        del flowables[0]
        if f is None:
            return

        if isinstance(f,PageBreak):
            npt = f.nextTemplate
            if npt and not self._samePT(npt):
                npt=NextPageTemplate(npt)
                npt.apply(self)
                self.afterFlowable(npt)
            if isinstance(f,SlowPageBreak):
                self.handle_pageBreak(slow=1)
            else:
                self.handle_pageBreak()
            self.afterFlowable(f)
        elif isinstance(f,ActionFlowable):
            f.apply(self)
            self.afterFlowable(f)
        else:
            frame = self.frame
            canv = self.canv
            #try to fit it then draw it
            if frame.add(f, canv, trySplit=self.allowSplitting):
                if not isinstance(f,FrameActionFlowable):
                    self._curPageFlowableCount += 1
                    self.afterFlowable(f)
                _addGeneratedContent(flowables,frame)
            else:
                if self.allowSplitting:
                    # see if this is a splittable thing
                    S = frame.split(f,canv)
                    n = len(S)
                else:
                    n = 0
                if n:
                    if not isinstance(S[0],(PageBreak,SlowPageBreak,ActionFlowable,DDIndenter)):
                        if not frame.add(S[0], canv, trySplit=0):
                            ident = "Splitting error(n==%d) on page %d in\n%s\nS[0]=%s" % (n,self.page,self._fIdent(f,60,frame),self._fIdent(S[0],60,frame))
                            #leave to keep apart from the raise
                            raise LayoutError(ident)
                        self._curPageFlowableCount += 1
                        self.afterFlowable(S[0])
                        flowables[0:0] = S[1:]  # put rest of splitted flowables back on the list
                        _addGeneratedContent(flowables,frame)
                    else:
                        flowables[0:0] = S  # put split flowables back on the list
                else:
                    if hasattr(f,'_postponed'):
                        ident = "Flowable %s%s too large on page %d in frame %r%s of template %r" % \
                                (self._fIdent(f,60,frame),_fSizeString(f),self.page, self.frame.id,
                                        self.frame._aSpaceString(), self.pageTemplate.id)
                        #leave to keep apart from the raise
                        raise LayoutError(ident)
                    # this ought to be cleared when they are finally drawn!
                    f._postponed = 1
                    mbe = getattr(self,'_multiBuildEdits',None)
                    if mbe:
                        mbe((delattr,f,'_postponed'))
                    flowables.insert(0,f)           # put the flowable back
                    self.handle_frameEnd()

    #these are provided so that deriving classes can refer to them
    _handle_documentBegin = handle_documentBegin
    _handle_pageBegin = handle_pageBegin
    _handle_pageEnd = handle_pageEnd
    _handle_frameBegin = handle_frameBegin
    _handle_frameEnd = handle_frameEnd
    _handle_flowable = handle_flowable
    _handle_nextPageTemplate = handle_nextPageTemplate
    _handle_currentFrame = handle_currentFrame
    _handle_nextFrame = handle_nextFrame

    def _makeCanvas(self, filename=None, canvasmaker=canvas.Canvas):
        '''make and return a sample canvas. As suggested by 
        Chris Jerdonek cjerdonek @ bitbucket this allows testing of stringWidths
        etc.

        *NB* only the canvases created in self._startBuild will actually be used
        in the build process.
        '''
        #each distinct pass gets a sequencer
        self.seq = reportlab.lib.sequencer.Sequencer()
        canv = canvasmaker(filename or self.filename,
                            pagesize=self.pagesize,
                            invariant=self.invariant,
                            pageCompression=self.pageCompression,
                            enforceColorSpace=self.enforceColorSpace,
                            initialFontName = self.initialFontName,
                            initialFontSize = self.initialFontSize,
                            initialLeading = self.initialLeading,
                            cropBox = self.cropBox,
                            artBox = self.artBox,
                            trimBox = self.trimBox,
                            bleedBox = self.bleedBox,
                            lang = self.lang,
                            )

        getattr(canv,'setEncrypt',lambda x: None)(self.encrypt)

        canv._cropMarks = self.cropMarks
        canv.setAuthor(self.author)
        canv.setTitle(self.title)
        canv.setSubject(self.subject)
        canv.setCreator(self.creator)
        canv.setProducer(self.producer)
        canv.setKeywords(self.keywords)
        from reportlab.pdfbase.pdfdoc import (
                ViewerPreferencesPDFDictionary as VPD, checkPDFBoolean as cPDFB,
                )
        for k,vf in VPD.validate.items():
            v = getattr(self,k[0].lower()+k[1:],None)
            if v is not None:
                if vf is cPDFB:
                    v = ['false','true'][v] #convert to pdf form of boolean
                canv.setViewerPreference(k,v)

        if self._onPage:
            canv.setPageCallBack(self._onPage)
        return canv

    def _startBuild(self, filename=None, canvasmaker=canvas.Canvas):
        self._calc()
        self.canv = self._makeCanvas(filename=filename,canvasmaker=canvasmaker)
        self.handle_documentBegin()

    def _endBuild(self):
        self._removeVars(('build','page','frame'))
        if self._hanging!=[] and self._hanging[-1] is PageBegin:
            del self._hanging[-1]
            self.clean_hanging()
        else:
            self.clean_hanging()
            self.handle_pageBreak()

        if getattr(self,'_doSave',1): self.canv.save()
        if self._onPage: self.canv.setPageCallBack(None)

    def build(self, flowables, filename=None, canvasmaker=canvas.Canvas):
        """Build the document from a list of flowables.
           If the filename argument is provided then that filename is used
           rather than the one provided upon initialization.
           If the canvasmaker argument is provided then it will be used
           instead of the default.  For example a slideshow might use
           an alternate canvas which places 6 slides on a page (by
           doing translations, scalings and redefining the page break
           operations).
        """
        #assert filter(lambda x: not isinstance(x,Flowable), flowables)==[], "flowables argument error"
        flowableCount = len(flowables)
        if self._onProgress:
            self._onProgress('STARTED',0)
            self._onProgress('SIZE_EST', len(flowables))
        self._startBuild(filename,canvasmaker)

        #pagecatcher can drag in information from embedded PDFs and we want ours
        #to take priority, so cache and reapply our own info dictionary after the build.
        canv = self.canv
        self._savedInfo = canv._doc.info
        handled = 0

        try:
            canv._doctemplate = self
            while len(flowables):
                if self._hanging and self._hanging[-1] is PageBegin and isinstance(flowables[0],PageBreakIfNotEmpty):
                    npt = flowables[0].nextTemplate
                    if npt and not self._samePT(npt):
                        npt=NextPageTemplate(npt)
                        npt.apply(self)
                        self._setPageTemplate()
                    del flowables[0]
                self.clean_hanging()
                try:
                    first = flowables[0]
                    self.handle_flowable(flowables)
                    handled += 1
                except:
                    #if it has trace info, add it to the traceback message.
                    if hasattr(first, '_traceInfo') and first._traceInfo:
                        exc = sys.exc_info()[1]
                        args = list(exc.args)
                        tr = first._traceInfo
                        args[0] += '\n(srcFile %s, line %d char %d to line %d char %d)' % (
                            tr.srcFile,
                            tr.startLineNo,
                            tr.startLinePos,
                            tr.endLineNo,
                            tr.endLinePos
                            )
                        exc.args = tuple(args)
                    raise
                if self._onProgress:
                    self._onProgress('PROGRESS',flowableCount - len(flowables))
        finally:
            del canv._doctemplate


        #reapply pagecatcher info
        canv._doc.info = self._savedInfo

        self._endBuild()
        if self._onProgress:
            self._onProgress('FINISHED',0)

    def _allSatisfied(self):
        """Called by multi-build - are all cross-references resolved?"""
        allHappy = 1
        for f in self._indexingFlowables:
            if not f.isSatisfied():
                allHappy = 0
                break
        return allHappy

    def notify(self, kind, stuff):
        """Forward to any listeners"""
        for l in self._indexingFlowables:
            _canv = getattr(l,'_canv',self)
            try:
                if _canv==self:
                    l._canv = self.canv
                l.notify(kind, stuff)
            finally:
                if _canv==self:
                    del l._canv

    def pageRef(self, label):
        """hook to register a page number"""
        if verbose: print("pageRef called with label '%s' on page %d" % (
            label, self.page))
        self._pageRefs[label] = self.page

    def multiBuild(self, story,
                   maxPasses = 10,
                   **buildKwds
                   ):
        """Makes multiple passes until all indexing flowables
        are happy.

        Returns number of passes"""
        self._indexingFlowables = []
        #scan the story and keep a copy
        for thing in story:
            if thing.isIndexing():
                self._indexingFlowables.append(thing)

        #better fix for filename is a 'file' problem
        self._doSave = 0
        passes = 0
        mbe = []
        self._multiBuildEdits = mbe.append
        while 1:
            passes += 1
            if self._onProgress:
                self._onProgress('PASS', passes)
            if verbose: sys.stdout.write('building pass '+str(passes) + '...')

            for fl in self._indexingFlowables:
                fl.beforeBuild()

            # work with a copy of the story, since it is consumed
            tempStory = story[:]
            self.build(tempStory, **buildKwds)
            #self.notify('debug',None)

            for fl in self._indexingFlowables:
                fl.afterBuild()

            happy = self._allSatisfied()

            if happy:
                self._doSave = 0
                self.canv.save()
                break
            if passes > maxPasses:
                raise IndexError("Index entries not resolved after %d passes" % maxPasses)

            #work through any edits
            while mbe:
                e = mbe.pop(0)
                e[0](*e[1:])

        del self._multiBuildEdits
        if verbose: print('saved')
        return passes

    #these are pure virtuals override in derived classes
    #NB these get called at suitable places by the base class
    #so if you derive and override the handle_xxx methods
    #it's up to you to ensure that they maintain the needed consistency
    def afterInit(self):
        """This is called after initialisation of the base class."""
        pass

    def beforeDocument(self):
        """This is called before any processing is
        done on the document."""
        pass

    def beforePage(self):
        """This is called at the beginning of page
        processing, and immediately before the
        beforeDrawPage method of the current page
        template."""
        pass

    def afterPage(self):
        """This is called after page processing, and
        immediately after the afterDrawPage method
        of the current page template."""
        pass

    def filterFlowables(self,flowables):
        '''called to filter flowables at the start of the main handle_flowable method.
        Upon return if flowables[0] has been set to None it is discarded and the main
        method returns.
        '''
        pass

    def afterFlowable(self, flowable):
        '''called after a flowable has been rendered'''
        pass

    _allowedLifetimes = 'page','frame','build','forever'
    def docAssign(self,var,expr,lifetime):
        if not isinstance(expr,strTypes): expr=str(expr)
        expr=expr.strip()
        var=var.strip()
        self.docExec('%s=(%s)'%(var.strip(),expr.strip()),lifetime)

    def docExec(self,stmt,lifetime):
        stmt=stmt.strip()
        NS=self._nameSpace
        K0=list(NS.keys())
        try:
            if lifetime not in self._allowedLifetimes:
                raise ValueError('bad lifetime %r not in %r'%(lifetime,self._allowedLifetimes))
            rl_safe_eval.rl_safe_exec(stmt.strip(),{},NS)
        except:
            K1 = [k for k in NS if k not in K0] #the added keys we need to delete
            for k in K1:
                del NS[k]
            annotateException('\ndocExec %s lifetime=%r failed!\n' % (stmt,lifetime))
        self._addVars([k for k in NS.keys() if k not in K0],lifetime)

    def _addVars(self,vars,lifetime):
        '''add namespace variables to lifetimes lists'''
        LT=self._lifetimes
        for var in vars:
            for v in LT.values():
                if var in v:
                    v.remove(var)
            LT.setdefault(lifetime,set([])).add(var)

    def _removeVars(self,lifetimes):
        '''remove namespace variables for with lifetime in lifetimes'''
        LT=self._lifetimes
        NS=self._nameSpace
        for lifetime in lifetimes:
            for k in LT.setdefault(lifetime,[]):
                try:
                    del NS[k]
                except KeyError:
                    pass
            del LT[lifetime]

    def docEval(self,expr):
        try:
            return rl_safe_eval.rl_safe_eval(expr.strip(),{},self._nameSpace)
        except:
            annotateException('\ndocEval %s failed!\n' % expr)

    def __repr__(self):
        return _rl_repr(self)

class SimpleDocTemplate(BaseDocTemplate):
    """A special case document template that will handle many simple documents.
       See documentation for BaseDocTemplate.  No pageTemplates are required
       for this special case.   A page templates are inferred from the
       margin information and the onFirstPage, onLaterPages arguments to the build method.

       A document which has all pages with the same look except for the first
       page may can be built using this special approach.
    """
    _invalidInitArgs = ('pageTemplates',)

    def handle_pageBegin(self):
        '''override base method to add a change of page template after the firstpage.
        '''
        self._handle_pageBegin()
        self._handle_nextPageTemplate('Later')

    def build(self,flowables,onFirstPage=_doNothing, onLaterPages=_doNothing, canvasmaker=canvas.Canvas):
        """build the document using the flowables.  Annotate the first page using the onFirstPage
               function and later pages using the onLaterPages function.  The onXXX pages should follow
               the signature

                  def myOnFirstPage(canvas, document):
                      # do annotations and modify the document
                      ...

               The functions can do things like draw logos, page numbers,
               footers, etcetera. They can use external variables to vary
               the look (for example providing page numbering or section names).
        """
        self._calc()    #in case we changed margins sizes etc
        frameT = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id='normal')
        self.addPageTemplates([PageTemplate(id='First',frames=frameT, onPage=onFirstPage,pagesize=self.pagesize),
                        PageTemplate(id='Later',frames=frameT, onPage=onLaterPages,pagesize=self.pagesize)])
        if onFirstPage is _doNothing and hasattr(self,'onFirstPage'):
            self.pageTemplates[0].beforeDrawPage = self.onFirstPage
        if onLaterPages is _doNothing and hasattr(self,'onLaterPages'):
            self.pageTemplates[1].beforeDrawPage = self.onLaterPages
        BaseDocTemplate.build(self,flowables, canvasmaker=canvasmaker)

def progressCB(typ, value):
    """Example prototype for progress monitoring.

    This aims to provide info about what is going on
    during a big job.  It should enable, for example, a reasonably
    smooth progress bar to be drawn.  We design the argument
    signature to be predictable and conducive to programming in
    other (type safe) languages.  If set, this will be called
    repeatedly with pairs of values.  The first is a string
    indicating the type of call; the second is a numeric value.

    typ 'STARTING', value = 0
    typ 'SIZE_EST', value = numeric estimate of job size
    typ 'PASS', value = number of this rendering pass
    typ 'PROGRESS', value = number between 0 and SIZE_EST
    typ 'PAGE', value = page number of page
    type 'FINISHED', value = 0

    The sequence is
        STARTING - always called once
        SIZE_EST - always called once
        PROGRESS - called often
        PAGE - called often when page is emitted
        FINISHED - called when really, really finished

    some juggling is needed to accurately estimate numbers of
    pages in pageDrawing mode.

    NOTE: the SIZE_EST is a guess.  It is possible that the
    PROGRESS value may slightly exceed it, or may even step
    back a little on rare occasions.  The only way to be
    really accurate would be to do two passes, and I don't
    want to take that performance hit.
    """
    print('PROGRESS MONITOR:  %-10s   %d' % (typ, value))

if __name__ == '__main__':
    from reportlab.lib.styles import _baseFontName, _baseFontNameB
    def myFirstPage(canvas, doc):
        from reportlab.lib.colors import red
        PAGE_HEIGHT = canvas._pagesize[1]
        canvas.saveState()
        canvas.setStrokeColor(red)
        canvas.setLineWidth(5)
        canvas.line(66,72,66,PAGE_HEIGHT-72)
        canvas.setFont(_baseFontNameB,24)
        canvas.drawString(108, PAGE_HEIGHT-108, "TABLE OF CONTENTS DEMO")
        canvas.setFont(_baseFontName,12)
        canvas.drawString(4 * inch, 0.75 * inch, "First Page")
        canvas.restoreState()

    def myLaterPages(canvas, doc):
        from reportlab.lib.colors import red
        PAGE_HEIGHT = canvas._pagesize[1]
        canvas.saveState()
        canvas.setStrokeColor(red)
        canvas.setLineWidth(5)
        canvas.line(66,72,66,PAGE_HEIGHT-72)
        canvas.setFont(_baseFontName,12)
        canvas.drawString(4 * inch, 0.75 * inch, "Page %d" % doc.page)
        canvas.restoreState()

    def run():
        objects_to_draw = []
        from reportlab.lib.styles import ParagraphStyle
        #from paragraph import Paragraph
        from reportlab.platypus.doctemplate import SimpleDocTemplate

        #need a style
        normal = ParagraphStyle('normal')
        normal.firstLineIndent = 18
        normal.spaceBefore = 6
        from reportlab.lib.randomtext import randomText
        import random
        for i in range(15):
            height = 0.5 + (2*random.random())
            box = XBox(6 * inch, height * inch, 'Box Number %d' % i)
            objects_to_draw.append(box)
            para = Paragraph(randomText(), normal)
            objects_to_draw.append(para)

        SimpleDocTemplate('doctemplate.pdf').build(objects_to_draw,
            onFirstPage=myFirstPage,onLaterPages=myLaterPages)

    run()
