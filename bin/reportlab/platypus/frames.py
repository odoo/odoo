#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/platypus/frames.py

__version__=''' $Id$ '''

__doc__="""
"""

_geomAttr=('x1', 'y1', 'width', 'height', 'leftPadding', 'bottomPadding', 'rightPadding', 'topPadding')
from reportlab import rl_config
_FUZZ=rl_config._FUZZ

class Frame:
    '''
    A Frame is a piece of space in a document that is filled by the
    "flowables" in the story.  For example in a book like document most
    pages have the text paragraphs in one or two frames.  For generality
    a page might have several frames (for example for 3 column text or
    for text that wraps around a graphic).

    After creation a Frame is not usually manipulated directly by the
    applications program -- it is used internally by the platypus modules.

    Here is a diagramatid abstraction for the definitional part of a Frame

                width                    x2,y2
        +---------------------------------+
        | l  top padding                r | h
        | e +-------------------------+ i | e
        | f |                         | g | i
        | t |                         | h | g
        |   |                         | t | h
        | p |                         |   | t
        | a |                         | p |
        | d |                         | a |
        |   |                         | d |
        |   +-------------------------+   |
        |    bottom padding               |
        +---------------------------------+
        (x1,y1) <-- lower left corner

        NOTE!! Frames are stateful objects.  No single frame should be used in
        two documents at the same time (especially in the presence of multithreading.
    '''
    def __init__(self, x1, y1, width,height, leftPadding=6, bottomPadding=6,
            rightPadding=6, topPadding=6, id=None, showBoundary=0,
            overlapAttachedSpace=None):
        self.id = id

        #these say where it goes on the page
        self.__dict__['_x1'] = x1
        self.__dict__['_y1'] = y1
        self.__dict__['_width'] = width
        self.__dict__['_height'] = height

        #these create some padding.
        self.__dict__['_leftPadding'] = leftPadding
        self.__dict__['_bottomPadding'] = bottomPadding
        self.__dict__['_rightPadding'] = rightPadding
        self.__dict__['_topPadding'] = topPadding

        # these two should NOT be set on a frame.
        # they are used when Indenter flowables want
        # to adjust edges e.g. to do nested lists
        self._leftExtraIndent = 0.0
        self._rightExtraIndent = 0.0

        # if we want a boundary to be shown
        self.showBoundary = showBoundary

        if overlapAttachedSpace is None: overlapAttachedSpace = rl_config.overlapAttachedSpace
        self._oASpace = overlapAttachedSpace
        self._geom()
        self._reset()

    def __getattr__(self,a):
        if a in _geomAttr: return self.__dict__['_'+a]
        raise AttributeError, a

    def __setattr__(self,a,v):
        if a in _geomAttr:
            self.__dict__['_'+a] = v
            self._geom()
        else:
            self.__dict__[a] = v

    def _geom(self):
        self._x2 = self._x1 + self._width
        self._y2 = self._y1 + self._height
        #efficiency
        self._y1p = self._y1 + self._bottomPadding
        #work out the available space
        self._aW = self._x2 - self._x1 - self._leftPadding - self._rightPadding
        self._aH = self._y2 - self._y1p - self._topPadding

    def _reset(self):
        #drawing starts at top left
        self._x = self._x1 + self._leftPadding
        self._y = self._y2 - self._topPadding
        self._atTop = 1
        self._prevASpace = 0

    def _getAvailableWidth(self):
        return self._aW - self._leftExtraIndent - self._rightExtraIndent

    def _add(self, flowable, canv, trySplit=0):
        """ Draws the flowable at the current position.
        Returns 1 if successful, 0 if it would not fit.
        Raises a LayoutError if the object is too wide,
        or if it is too high for a totally empty frame,
        to avoid infinite loops"""
        y = self._y
        p = self._y1p
        s = 0
        aW = self._getAvailableWidth()
        if not self._atTop:
            s =flowable.getSpaceBefore()
            if self._oASpace:
                s = max(s-self._prevASpace,0)
        h = y - p - s
        if h>0:
            flowable.canv = canv #so they can use stringWidth etc
            w, h = flowable.wrap(aW, h)
            del flowable.canv
        else:
            return 0

        h += s
        y -= h

        if y < p-_FUZZ:
            if not rl_config.allowTableBoundsErrors and ((h>self._aH or w>aW) and not trySplit):
                raise "LayoutError", "Flowable %s (%sx%s points) too large for frame (%sx%s points)." % (
                    flowable.__class__, w,h, aW,self._aH)
            return 0
        else:
            #now we can draw it, and update the current point.
            flowable.drawOn(canv, self._x + self._leftExtraIndent, y, _sW=aW-w)
            s = flowable.getSpaceAfter()
            y -= s
            if self._oASpace: self._prevASpace = s
            if y!=self._y: self._atTop = 0
            self._y = y
            return 1

    add = _add

    def split(self,flowable,canv):
        '''Ask the flowable to split using up the available space.'''
        y = self._y
        p = self._y1p
        s = 0
        if not self._atTop: s = flowable.getSpaceBefore()
        flowable.canv = canv    #some flowables might need this

        #print 'asked table to split.  _aW = %0.2f, y-p-s=%0.2f' % (self._aW, y-p-s)
        r = flowable.split(self._aW, y-p-s)
        del flowable.canv
        return r

    def drawBoundary(self,canv):
        "draw the frame boundary as a rectangle (primarily for debugging)."
        from reportlab.lib.colors import Color, CMYKColor, toColor
        sb = self.showBoundary
        isColor = type(sb) in (type(''),type(()),type([])) or isinstance(sb,Color)
        if isColor:
            sb = toColor(sb,self)
            if sb is self: isColor = 0
            else:
                canv.saveState()
                canv.setStrokeColor(sb)
        canv.rect(
                self._x1,
                self._y1,
                self._x2 - self._x1,
                self._y2 - self._y1
                )
        if isColor: canv.restoreState()

    def addFromList(self, drawlist, canv):
        """Consumes objects from the front of the list until the
        frame is full.  If it cannot fit one object, raises
        an exception."""

        if self.showBoundary:
            self.drawBoundary(canv)

        while len(drawlist) > 0:
            head = drawlist[0]
            if self.add(head,canv,trySplit=0):
                del drawlist[0]
            else:
                #leave it in the list for later
                break
