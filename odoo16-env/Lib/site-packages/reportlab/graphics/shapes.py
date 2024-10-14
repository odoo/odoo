#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/graphics/shapes.py

__version__='3.5.60'
__doc__='''Core of the graphics library - defines Drawing and Shapes'''

import os, sys
from math import pi, cos, sin, sqrt, radians, floor

from reportlab.platypus import Flowable
from reportlab.rl_config import shapeChecking, verbose, defaultGraphicsFontName as _baseGFontName, _unset_, decimalSymbol
from reportlab.lib import logger
from reportlab.lib import colors
from reportlab.lib.validators import *
from reportlab.lib.utils import isSeq, asBytes
isOpacity = NoneOr(isNumberInRange(0,1))
from reportlab.lib.attrmap import *
from reportlab.lib.rl_accel import fp_str
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.fonts import tt2ps
from reportlab.pdfgen.canvas import FILL_EVEN_ODD, FILL_NON_ZERO
_baseGFontNameB = tt2ps(_baseGFontName,1,0)
_baseGFontNameI = tt2ps(_baseGFontName,0,1)
_baseGFontNameBI = tt2ps(_baseGFontName,1,1)

# two constants for filling rules
NON_ZERO_WINDING = 'Non-Zero Winding'
EVEN_ODD = 'Even-Odd'

## these can be overridden at module level before you start
#creating shapes.  So, if using a special color model,
#this provides support for the rendering mechanism.
#you can change defaults globally before you start
#making shapes; one use is to substitute another
#color model cleanly throughout the drawing.

STATE_DEFAULTS = {   # sensible defaults for all
    'transform': (1,0,0,1,0,0),

    # styles follow SVG naming
    'strokeColor': colors.black,
    'strokeWidth': 1,
    'strokeLineCap': 0,
    'strokeLineJoin': 0,
    'strokeMiterLimit' : 10,    # don't know yet so let bomb here
    'strokeDashArray': None,
    'strokeOpacity': None, #100%
    'fillOpacity': None,
    'fillOverprint': False,
    'strokeOverprint': False,
    'overprintMask': 0,

    'fillColor': colors.black,   #...or text will be invisible
    'fillMode': FILL_EVEN_ODD,      #same as pdfgen.canvas

    'fontSize': 10,
    'fontName': _baseGFontName,
    'textAnchor':  'start' # can be start, middle, end, inherited
    }

####################################################################
# math utilities.  These are now in reportlab.graphics.transform
####################################################################
from . transform import *

def _textBoxLimits(text, font, fontSize, leading, textAnchor, boxAnchor):
    w = 0
    for t in text:
        w = max(w,stringWidth(t,font, fontSize))

    h = len(text)*leading
    yt = fontSize
    if boxAnchor[0]=='s':
        yb = -h
        yt = yt - h
    elif boxAnchor[0]=='n':
        yb = 0
    else:
        yb = -h/2.0
        yt = yt + yb

    if boxAnchor[-1]=='e':
        xb = -w
        if textAnchor=='end': xt = 0
        elif textAnchor=='start': xt = -w
        else: xt = -w/2.0
    elif boxAnchor[-1]=='w':
        xb = 0
        if textAnchor=='end': xt = w
        elif textAnchor=='start': xt = 0
        else: xt = w/2.0
    else:
        xb = -w/2.0
        if textAnchor=='end': xt = -xb
        elif textAnchor=='start': xt = xb
        else: xt = 0

    return xb, yb, w, h, xt, yt

def _rotatedBoxLimits( x, y, w, h, angle):
    '''
    Find the corner points of the rotated w x h sized box at x,y
    return the corner points and the min max points in the original space
    '''
    C = zTransformPoints(rotate(angle),((x,y),(x+w,y),(x+w,y+h),(x,y+h)))
    X = [x[0] for x in C]
    Y = [x[1] for x in C]
    return min(X), max(X), min(Y), max(Y), C

class _DrawTimeResizeable:
    '''Addin class to provide the horribleness of _drawTimeResize'''
    def _drawTimeResize(self,w,h):
        if hasattr(self,'_canvas'):
            canvas = self._canvas
            drawing = canvas._drawing
            drawing.width, drawing.height = w, h
            if hasattr(canvas,'_drawTimeResize'):
                canvas._drawTimeResize(w,h)

class _SetKeyWordArgs:
    def __init__(self, keywords={}):
        """In general properties may be supplied to the constructor."""
        for key, value in keywords.items():
            setattr(self, key, value)

#################################################################
#
#    Helper functions for working out bounds
#
#################################################################

def getRectsBounds(rectList):
    # filter out any None objects, e.g. empty groups
    L = [x for x in rectList if x is not None]
    if not L: return None

    xMin, yMin, xMax, yMax = L[0]
    for (x1, y1, x2, y2) in L[1:]:
        if x1 < xMin:
            xMin = x1
        if x2 > xMax:
            xMax = x2
        if y1 < yMin:
            yMin = y1
        if y2 > yMax:
            yMax = y2
    return (xMin, yMin, xMax, yMax)

def _getBezierExtrema(y0,y1,y2,y3):
    '''
    this is used to find if a curveTo path operator has extrema in its range
    The curveTo operator is defined by the points y0, y1, y2, y3

        B(t):=(1-t)^3*y0+3*(1-t)^2*t*y1+3*(1-t)*t^2*y2+t^3*y3
            :=t^3*(y3-3*y2+3*y1-y0)+t^2*(3*y2-6*y1+3*y0)+t*(3*y1-3*y0)+y0
    and is a cubic bezier curve.

    The differential is a quadratic
        t^2*(3*y3-9*y2+9*y1-3*y0)+t*(6*y2-12*y1+6*y0)+3*y1-3*y0

    The extrema must be at real roots, r, of the above which lie in 0<=r<=1

    The quadratic coefficients are
        a=3*y3-9*y2+9*y1-3*y0 b=6*y2-12*y1+6*y0 c=3*y1-3*y0
    or
        a=y3-3*y2+3*y1-y0 b=2*y2-4*y1+2*y0 c=y1-y0  (remove common factor of 3)
    or
        a=y3-3*(y2-y1)-y0 b=2*(y2-2*y1+y0) c=y1-y0

    The returned value is [y0,x1,x2,y3] where if found x1, x2 are any extremals that were found;
    there can be 0, 1 or 2 extremals
    '''
    a=y3-3*(y2-y1)-y0
    b=2*(y2-2*y1+y0)
    c=y1-y0
    Y = [y0] #the set of points

    #standard method to find roots of quadratic
    d = b*b - 4*a*c
    if d>=0:
        d = sqrt(d)
        if b<0: d = -d
        q = -0.5*(b+d)
        R = []
        try:
            R.append(q/a)
        except:
            pass
        try:
            R.append(c/q)
        except:
            pass
        b *= 1.5
        c *= 3
        for t in R:
            if 0<=t<=1:
                #real root in range evaluate spline there and add to X
                Y.append(t*(t*(t*a+b)+c)+y0)
    Y.append(y3)
    return Y

def getPathBounds(points):
    n = len(points)
    f = lambda i,p = points: p[i]
    xs = list(map(f,range(0,n,2)))
    ys = list(map(f,range(1,n,2)))
    return (min(xs), min(ys), max(xs), max(ys))

def getPointsBounds(pointList):
    "Helper function for list of points"
    first = pointList[0]
    if isSeq(first):
        xs = [xy[0] for xy in pointList]
        ys = [xy[1] for xy in pointList]
        return (min(xs), min(ys), max(xs), max(ys))
    else:
        return getPathBounds(pointList)

#################################################################
#
#    And now the shapes themselves....
#
#################################################################
class Shape(_SetKeyWordArgs,_DrawTimeResizeable):
    """Base class for all nodes in the tree. Nodes are simply
    packets of data to be created, stored, and ultimately
    rendered - they don't do anything active.  They provide
    convenience methods for verification but do not
    check attribiute assignments or use any clever setattr
    tricks this time."""
    _attrMap = AttrMap()

    def copy(self):
        """Return a clone of this shape."""

        # implement this in the descendants as they need the right init methods.
        raise NotImplementedError("No copy method implemented for %s" % self.__class__.__name__)

    def getProperties(self,recur=1):
        """Interface to make it easy to extract automatic
        documentation"""

        #basic nodes have no children so this is easy.
        #for more complex objects like widgets you
        #may need to override this.
        props = {}
        for key, value in self.__dict__.items():
            if key[0:1] != '_':
                props[key] = value
        return props

    def setProperties(self, props):
        """Supports the bulk setting if properties from,
        for example, a GUI application or a config file."""

        self.__dict__.update(props)
        #self.verify()

    def dumpProperties(self, prefix=""):
        """Convenience. Lists them on standard output.  You
        may provide a prefix - mostly helps to generate code
        samples for documentation."""

        propList = list(self.getProperties().items())
        propList.sort()
        if prefix:
            prefix = prefix + '.'
        for (name, value) in propList:
            print('%s%s = %s' % (prefix, name, value))

    def verify(self):
        """If the programmer has provided the optional
        _attrMap attribute, this checks all expected
        attributes are present; no unwanted attributes
        are present; and (if a checking function is found)
        checks each attribute.  Either succeeds or raises
        an informative exception."""

        if self._attrMap is not None:
            for key in self.__dict__.keys():
                if key[0] != '_':
                    assert key in self._attrMap, "Unexpected attribute %s found in %s" % (key, self)
            for attr, metavalue in self._attrMap.items():
                assert hasattr(self, attr), "Missing attribute %s from %s" % (attr, self)
                value = getattr(self, attr)
                assert metavalue.validate(value), "Invalid value %s for attribute %s in class %s" % (value, attr, self.__class__.__name__)

    if shapeChecking:
        """This adds the ability to check every attribute assignment as it is made.
        It slows down shapes but is a big help when developing. It does not
        get defined if rl_config.shapeChecking = 0"""
        def __setattr__(self, attr, value):
            """By default we verify.  This could be off
            in some parallel base classes."""
            validateSetattr(self,attr,value)    #from reportlab.lib.attrmap

    def getBounds(self):
        "Returns bounding rectangle of object as (x1,y1,x2,y2)"
        raise NotImplementedError("Shapes and widgets must implement getBounds")

class Group(Shape):
    """Groups elements together.  May apply a transform
    to its contents.  Has a publicly accessible property
    'contents' which may be used to iterate over contents.
    In addition, child nodes may be given a name in which
    case they are subsequently accessible as properties."""

    _attrMap = AttrMap(
        transform = AttrMapValue(isTransform,desc="Coordinate transformation to apply",advancedUsage=1),
        contents = AttrMapValue(isListOfShapes,desc="Contained drawable elements"),
        strokeOverprint = AttrMapValue(isBoolean,desc='Turn on stroke overprinting'),
        fillOverprint = AttrMapValue(isBoolean,desc='Turn on fill overprinting',advancedUsage=1),
        overprintMask = AttrMapValue(isBoolean,desc='overprinting for ordinary CMYK',advancedUsage=1),
        )

    def __init__(self, *elements, **keywords):
        """Initial lists of elements may be provided to allow
        compact definitions in literal Python code.  May or
        may not be useful."""

        # Groups need _attrMap to be an instance rather than
        # a class attribute, as it may be extended at run time.
        self._attrMap = self._attrMap.clone()
        self.contents = []
        self.transform = (1,0,0,1,0,0)
        for elt in elements:
            self.add(elt)
        # this just applies keywords; do it at the end so they
        #don;t get overwritten
        _SetKeyWordArgs.__init__(self, keywords)

    def _addNamedNode(self,name,node):
        'if name is not None add an attribute pointing to node and add to the attrMap'
        if name:
            if name not in list(self._attrMap.keys()):
                self._attrMap[name] = AttrMapValue(isValidChild)
            setattr(self, name, node)

    def add(self, node, name=None):
        """Appends non-None child node to the 'contents' attribute. In addition,
        if a name is provided, it is subsequently accessible by name
        """
        # propagates properties down
        if node is not None:
            try:
                assert isValidChild(node), "Can only add Shape or UserNode objects to a Group"
            except:
                breakpoint()
                raise
            self.contents.append(node)
            self._addNamedNode(name,node)

    def _nn(self,node):
        self.add(node)
        return self.contents[-1]

    def insert(self, i, n, name=None):
        'Inserts sub-node n in contents at specified location'
        if n is not None:
            assert isValidChild(n), "Can only insert Shape or UserNode objects in a Group"
            if i<0:
                self.contents[i:i] =[n]
            else:
                self.contents.insert(i,n)
            self._addNamedNode(name,n)

    def expandUserNodes(self):
        """Return a new object which only contains primitive shapes."""

        # many limitations - shared nodes become multiple ones,
        obj = isinstance(self,Drawing) and Drawing(self.width,self.height) or Group()
        obj._attrMap = self._attrMap.clone()
        if hasattr(obj,'transform'): obj.transform = self.transform[:]

        self_contents = self.contents
        a = obj.contents.append
        for child in self_contents:
            if isinstance(child, UserNode):
                newChild = child.provideNode()
            elif isinstance(child, Group):
                newChild = child.expandUserNodes()
            else:
                newChild = child.copy()
            a(newChild)

        self._copyNamedContents(obj)
        return obj

    def _explode(self):
        ''' return a fully expanded object'''
        obj = Group()
        if hasattr(self,'__label__'):
            obj.__label__=self.__label__
        if hasattr(obj,'transform'): obj.transform = self.transform[:]
        P = self.getContents()[:]   # pending nodes
        while P:
            n = P.pop(0)
            if isinstance(n, UserNode):
                P.append(n.provideNode())
            elif isinstance(n, Group):
                n = n._explode()
                if n.transform==(1,0,0,1,0,0):
                    obj.contents.extend(n.contents)
                else:
                    obj.add(n)
            else:
                obj.add(n)
        return obj

    def _copyContents(self,obj):
        for child in self.contents:
            obj.contents.append(child)

    def _copyNamedContents(self,obj,aKeys=None,noCopy=('contents',)):
        from copy import copy
        self_contents = self.contents
        if not aKeys: aKeys = list(self._attrMap.keys())
        for k, v in self.__dict__.items():
            if v in self_contents:
                pos = self_contents.index(v)
                setattr(obj, k, obj.contents[pos])
            elif k in aKeys and k not in noCopy:
                setattr(obj, k, copy(v))

    def _copy(self,obj):
        """copies to obj"""
        obj._attrMap = self._attrMap.clone()
        self._copyContents(obj)
        self._copyNamedContents(obj)
        return obj

    def copy(self):
        """returns a copy"""
        return self._copy(self.__class__())

    def rotate(self, theta):
        """Convenience to help you set transforms"""
        self.transform = mmult(self.transform, rotate(theta))

    def translate(self, dx, dy):
        """Convenience to help you set transforms"""
        self.transform = mmult(self.transform, translate(dx, dy))

    def scale(self, sx, sy):
        """Convenience to help you set transforms"""
        self.transform = mmult(self.transform, scale(sx, sy))

    def skew(self, kx, ky):
        """Convenience to help you set transforms"""
        self.transform = mmult(mmult(self.transform, skewX(kx)),skewY(ky))

    def shift(self, x, y):
        '''Convenience function to set the origin arbitrarily'''
        self.transform = self.transform[:-2]+(x,y)

    def asDrawing(self, width, height):
        """ Convenience function to make a drawing from a group
            After calling this the instance will be a drawing!
        """
        self.__class__ = Drawing
        self._attrMap.update(self._xtraAttrMap)
        self.width = width
        self.height = height

    def getContents(self):
        '''Return the list of things to be rendered
        override to get more complicated behaviour'''
        b = getattr(self,'background',None)
        C = self.contents
        if b and b not in C: C = [b]+C
        return C

    def getBounds(self):
        if self.contents:
            b = []
            for elem in self.contents:
                b.append(elem.getBounds())
            x1 = getRectsBounds(b)
            if x1 is None: return None
            x1, y1, x2, y2 = x1
            trans = self.transform
            corners = [[x1,y1], [x1, y2], [x2, y1], [x2,y2]]
            newCorners = []
            for corner in corners:
                newCorners.append(transformPoint(trans, corner))
            return getPointsBounds(newCorners)
        else:
            #empty group needs a sane default; this
            #will happen when interactively creating a group
            #nothing has been added to yet.  The alternative is
            #to handle None as an allowed return value everywhere.
            return None

def _addObjImport(obj,I,n=None):
    '''add an import of obj's class to a dictionary of imports''' #'
    from inspect import getmodule
    c = obj.__class__
    m = getmodule(c).__name__
    n = n or c.__name__
    if m not in I:
        I[m] = [n]
    elif n not in I[m]:
        I[m].append(n)

def _repr(self,I=None):
    '''return a repr style string with named fixed args first, then keywords'''
    if isinstance(self,float):
        return fp_str(self)
    elif isSeq(self):
        s = ''
        for v in self:
            s = s + '%s,' % _repr(v,I)
        if isinstance(self,list):
            return '[%s]' % s[:-1]
        else:
            return '(%s%s)' % (s[:-1],len(self)==1 and ',' or '')
    elif self is EmptyClipPath:
        if I: _addObjImport(self,I,'EmptyClipPath')
        return 'EmptyClipPath'
    elif isinstance(self,Shape):
        if I: _addObjImport(self,I)
        from inspect import getfullargspec
        args, varargs, varkw, defaults, kwonlyargs, kwonlydefaults, annotations = getfullargspec(self.__init__)
        if defaults:
            kargs = args[-len(defaults):]
            del args[-len(defaults):]
        else:
            kargs = []
        P = self.getProperties()
        s = self.__class__.__name__+'('
        for n in args[1:]:
            v = P.pop(n,None)
            s += '%s,' % _repr(v,I)
        for n in kargs:
            v = P.pop(n,None)
            s += '%s=%s,' % (n,_repr(v,I))
        for n,v in P.items():
            v = P[n]
            s += '%s=%s,' % (n, _repr(v,I))
        return s[:-1]+')'
    else:
        return repr(self)

def _renderGroupPy(G,pfx,I,i=0,indent='\t\t'):
    s = ''
    C = getattr(G,'transform',None)
    if C: s = s + ('%s%s.transform = %s\n' % (indent,pfx,_repr(C)))
    C  = G.contents
    for n in C:
        if isinstance(n, Group):
            npfx = 'v%d' % i
            i += 1
            l = getattr(n,'__label__','')
            if l: l='#'+l
            s = s + '%s%s=%s._nn(Group())%s\n' % (indent,npfx,pfx,l)
            s = s + _renderGroupPy(n,npfx,I,i,indent)
            i -= 1
        else:
            s = s + '%s%s.add(%s)\n' % (indent,pfx,_repr(n,I))
    return s

def _extraKW(self,pfx,**kw):
    kw.update(self.__dict__)
    n = len(pfx)
    return {k[n:]:v for k,v in kw.items() if k.startswith(pfx)}

class Drawing(Group, Flowable):
    """Outermost container; the thing a renderer works on.
    This has no properties except a height, width and list
    of contents."""

    _saveModes = {
            'bmp',
            'eps',
            'gif',
            'jpeg',
            'jpg',
            'pct',
            'pdf',
            'pict',
            'png',
            'ps',
            'py',
            'svg',
            'tif',
            'tiff',
            'tiff1',
            'tiffl',
            'tiffp',
            }

    _bmModes = _saveModes - {'eps','pdf','ps','py','svg'}

    _xtraAttrMap = AttrMap(
        width = AttrMapValue(isNumber,desc="Drawing width in points."),
        height = AttrMapValue(isNumber,desc="Drawing height in points."),
        canv = AttrMapValue(None),
        background = AttrMapValue(isValidChildOrNone,desc="Background widget for the drawing e.g. Rect(0,0,width,height)"),
        hAlign = AttrMapValue(OneOf("LEFT", "RIGHT", "CENTER", "CENTRE"), desc="Horizontal alignment within parent document"),
        vAlign = AttrMapValue(OneOf("TOP", "BOTTOM", "CENTER", "CENTRE"), desc="Vertical alignment within parent document"),
        #AR temporary hack to track back up.
        #fontName = AttrMapValue(isStringOrNone),
        renderScale = AttrMapValue(isNumber,desc="Global scaling for rendering"),
        initialFontName = AttrMapValue(isStringOrNone,desc="override the STATE_DEFAULTS value for fontName"),
        initialFontSize = AttrMapValue(isNumberOrNone,desc="override the STATE_DEFAULTS value for fontSize"),
        )

    _attrMap = AttrMap(BASE=Group,
            formats = AttrMapValue(SequenceOf(
                OneOf(*_saveModes),
                lo=1,emptyOK=0), desc='One or more plot modes'),
            )
    _attrMap.update(_xtraAttrMap)

    def __init__(self, width=400, height=200, *nodes, **keywords):
        self.background = None
        Group.__init__(self,*nodes,**keywords)
        self.width = width
        self.height = height
        self.hAlign = 'LEFT'
        self.vAlign = 'BOTTOM'
        self.renderScale = 1.0

    def _renderPy(self):
        I = {
                'reportlab.graphics.shapes': ['_DrawingEditorMixin','Drawing','Group'],
                'reportlab.lib.colors': ['Color','CMYKColor','PCMYKColor'],
            }
        G = _renderGroupPy(self._explode(),'self',I)
        n = 'ExplodedDrawing_' + self.__class__.__name__
        s = '#Autogenerated by ReportLab guiedit do not edit\n'
        for m, o in I.items():
            s = s + 'from %s import %s\n' % (m,str(o)[1:-1].replace("'",""))
        s = s + '\nclass %s(_DrawingEditorMixin,Drawing):\n' % n
        s = s + '\tdef __init__(self,width=%s,height=%s,*args,**kw):\n' % (self.width,self.height)
        s = s + '\t\tDrawing.__init__(self,width,height,*args,**kw)\n'
        s = s + G
        s = s + '\n\nif __name__=="__main__": #NORUNTESTS\n\t%s().save(formats=[\'pdf\'],outDir=\'.\',fnRoot=None)\n' % n
        return s

    def draw(self,showBoundary=_unset_):
        """This is used by the Platypus framework to let the document
        draw itself in a story.  It is specific to PDF and should not
        be used directly."""
        from reportlab.graphics import renderPDF
        renderPDF.draw(self, self.canv, 0, 0,
                showBoundary=showBoundary if showBoundary is not _unset_ else getattr(self,'_showBoundary',_unset_))

    def wrap(self, availWidth, availHeight):
        width = self.width
        height = self.height
        renderScale = self.renderScale
        if renderScale!=1.0:
            width *= renderScale
            height *= renderScale
        return width, height

    def expandUserNodes(self):
        """Return a new drawing which only contains primitive shapes."""
        obj = Group.expandUserNodes(self)
        obj.width = self.width
        obj.height = self.height
        return obj

    def copy(self):
        """Returns a copy"""
        return self._copy(self.__class__(self.width, self.height))

    def asGroup(self,*args,**kw):
        return self._copy(Group(*args,**kw))

    def save(self, formats=None, verbose=None, fnRoot=None, outDir=None, title='', **kw):
        """Saves copies of self in desired location and formats.
        Multiple formats can be supported in one call

        the extra keywords can be of the form
        _renderPM_dpi=96 (which passes dpi=96 to renderPM)
        """
        genFmt = kw.pop('seqNumber','')
        if isinstance(genFmt,int):
            genFmt = '%4d: ' % genFmt
        else:
            genFmt = ''
        genFmt += 'generating %s file %s'
        from reportlab import rl_config
        ext = ''
        if not fnRoot:
            fnRoot = getattr(self,'fileNamePattern',(self.__class__.__name__+'%03d'))
            chartId = getattr(self,'chartId',0)
            if hasattr(chartId,'__call__'):
                chartId = chartId(self)
            if hasattr(fnRoot,'__call__'):
                fnRoot = fnRoot(chartId)
            else:
                try:
                    fnRoot = fnRoot % chartId
                except TypeError as err:
                    #the exact error message changed from 2.2 to 2.3 so we need to
                    #check a substring
                    if str(err).find('not all arguments converted') < 0: raise

        if outDir is None:
            outDir = getattr(self,'outDir',None)
        if hasattr(outDir,'__call__'):
            outDir = outDir(self)
        if os.path.isabs(fnRoot):
            outDir, fnRoot = os.path.split(fnRoot)
        else:
            outDir = outDir or getattr(self,'outDir','.')
        outDir = outDir.rstrip().rstrip(os.sep)
        if not outDir: outDir = '.'
        if not os.path.isabs(outDir): outDir = os.path.join(getattr(self,'_override_CWD',os.path.dirname(sys.argv[0])),outDir)
        if not os.path.isdir(outDir): os.makedirs(outDir)
        fnroot = os.path.normpath(os.path.join(outDir,fnRoot))
        plotMode = os.path.splitext(fnroot)
        if plotMode[1][1:].lower() in self._saveModes:
            fnroot = plotMode[0]

        plotMode = [x.lower() for x in (formats or getattr(self,'formats',['pdf']))]
        verbose = (verbose is not None and (verbose,) or (getattr(self,'verbose',verbose),))[0]
        _saved = logger.warnOnce.enabled, logger.infoOnce.enabled
        logger.warnOnce.enabled = logger.infoOnce.enabled = verbose
        if 'pdf' in plotMode:
            from reportlab.graphics import renderPDF
            filename = fnroot+'.pdf'
            if verbose: print(genFmt % ('PDF',filename))
            renderPDF.drawToFile(self, filename, title, showBoundary=getattr(self,'showBorder',rl_config.showBoundary),**_extraKW(self,'_renderPDF_',**kw))
            ext = ext +  '/.pdf'
            if sys.platform=='mac':
                import macfs, macostools
                macfs.FSSpec(filename).SetCreatorType("CARO", "PDF ")
                macostools.touched(filename)

        for bmFmt in self._bmModes:
            if bmFmt in plotMode:
                from reportlab.graphics import renderPM
                filename = '%s.%s' % (fnroot,bmFmt)
                if verbose: print(genFmt % (bmFmt,filename))
                dtc = getattr(self,'_drawTimeCollector',None)
                if dtc:
                    dtcfmts = getattr(dtc,'formats',[bmFmt])
                    if bmFmt in dtcfmts and not getattr(dtc,'disabled',0):
                        dtc.clear()
                    else:
                        dtc = None
                renderPM.drawToFile(self, filename,fmt=bmFmt,showBoundary=getattr(self,'showBorder',rl_config.showBoundary),**_extraKW(self,'_renderPM_',**kw))
                ext = ext + '/.' + bmFmt
                if dtc: dtc.save(filename)

        if 'eps' in plotMode:
            try:
                from rlextra.graphics import renderPS_SEP as renderPS
            except ImportError:
                from reportlab.graphics import renderPS
            filename = fnroot+'.eps'
            if verbose: print(genFmt % ('EPS',filename))
            renderPS.drawToFile(self,
                                filename,
                                title = fnroot,
                                dept = getattr(self,'EPS_info',['Testing'])[0],
                                company = getattr(self,'EPS_info',['','ReportLab'])[1],
                                preview = getattr(self,'preview',rl_config.eps_preview),
                                showBoundary=getattr(self,'showBorder',rl_config.showBoundary),
                                ttf_embed=getattr(self,'ttf_embed',rl_config.eps_ttf_embed),
                                **_extraKW(self,'_renderPS_',**kw))
            ext = ext +  '/.eps'

        if 'svg' in plotMode:
            from reportlab.graphics import renderSVG
            filename = fnroot+'.svg'
            if verbose: print(genFmt % ('SVG',filename))
            renderSVG.drawToFile(self,
                                filename,
                                showBoundary=getattr(self,'showBorder',rl_config.showBoundary),**_extraKW(self,'_renderSVG_',**kw))
            ext = ext +  '/.svg'

        if 'ps' in plotMode:
            from reportlab.graphics import renderPS
            filename = fnroot+'.ps'
            if verbose: print(genFmt % ('EPS',filename))
            renderPS.drawToFile(self, filename, showBoundary=getattr(self,'showBorder',rl_config.showBoundary),**_extraKW(self,'_renderPS_',**kw))
            ext = ext +  '/.ps'

        if 'py' in plotMode:
            filename = fnroot+'.py'
            if verbose: print(genFmt % ('py',filename))
            with open(filename,'wb') as f:
                f.write(asBytes(self._renderPy().replace('\n',os.linesep)))
            ext = ext +  '/.py'

        logger.warnOnce.enabled, logger.infoOnce.enabled = _saved
        if hasattr(self,'saveLogger'):
            self.saveLogger(fnroot,ext)
        return ext and fnroot+ext[1:] or ''

    def asString(self, format, verbose=None, preview=0, **kw):
        """Converts to an 8 bit string in given format."""
        assert format in self._saveModes, 'Unknown file format "%s"' % format
        from reportlab import rl_config
        #verbose = verbose is not None and (verbose,) or (getattr(self,'verbose',verbose),)[0]
        if format == 'pdf':
            from reportlab.graphics import renderPDF
            title = kw.pop('title','')
            return renderPDF.drawToString(self, title, showBoundary=getattr(self,'showBorder',rl_config.showBoundary),**_extraKW(self,'_renderPDF_',**kw))
        elif format in self._bmModes:
            from reportlab.graphics import renderPM
            return renderPM.drawToString(self, fmt=format,showBoundary=getattr(self,'showBorder',
                            rl_config.showBoundary),**_extraKW(self,'_renderPM_',**kw))
        elif format == 'eps':
            try:
                from rlextra.graphics import renderPS_SEP as renderPS
            except ImportError:
                from reportlab.graphics import renderPS

            return renderPS.drawToString(self,
                                preview = preview,
                                showBoundary=getattr(self,'showBorder',rl_config.showBoundary))
        elif format == 'ps':
            from reportlab.graphics import renderPS
            return renderPS.drawToString(self, showBoundary=getattr(self,'showBorder',rl_config.showBoundary))
        elif format == 'py':
            return self._renderPy()
        elif format == 'svg':
            from reportlab.graphics import renderSVG
            return renderSVG.drawToString(self,showBoundary=getattr(self,'showBorder',rl_config.showBoundary),**_extraKW(self,'_renderSVG_',**kw))

    def resized(self,kind='fit',lpad=0,rpad=0,bpad=0,tpad=0):
        '''return a base class drawing which ensures all the contents fits'''
        C = self.getContents()
        oW = self.width
        oH = self.height
        drawing = Drawing(oW,oH,*C)
        xL,yL,xH,yH = drawing.getBounds()
        if kind=='fit' or (kind=='expand' and (xL<lpad or xH>oW-rpad or yL<bpad or yH>oH-tpad)):
            drawing.width = xH-xL+lpad+rpad
            drawing.height = yH-yL+tpad+bpad
            drawing.transform = (1,0,0,1,lpad-xL,bpad-yL)
        elif kind=='fitx' or (kind=='expandx' and (xL<lpad or xH>oW-rpad)):
            drawing.width = xH-xL+lpad+rpad
            drawing.transform = (1,0,0,1,lpad-xL,0)
        elif kind=='fity' or (kind=='expandy' and (yL<bpad or yH>oH-tpad)):
            drawing.height = yH-yL+tpad+bpad
            drawing.transform = (1,0,0,1,0,bpad-yL)
        return drawing

class _DrawingEditorMixin:
    '''This is a mixin to provide functionality for edited drawings'''
    def _add(self,obj,value,name=None,validate=None,desc=None,pos=None):
        '''
        effectively setattr(obj,name,value), but takes care of things with _attrMaps etc
        '''
        ivc = isValidChild(value)
        if name and hasattr(obj,'_attrMap'):
            if '_attrMap' not in obj.__dict__:
                obj._attrMap = obj._attrMap.clone()
            if ivc and validate is None: validate = isValidChild
            obj._attrMap[name] = AttrMapValue(validate,desc)
        if hasattr(obj,'add') and ivc:
            if pos:
                obj.insert(pos,value,name)
            else:
                obj.add(value,name)
        elif name:
            setattr(obj,name,value)
        else:
            raise ValueError("Can't add, need name")

class isStrokeDashArray(Validator):
    def test(self,x):
        return isListOfNumbersOrNone.test(x) or (isinstance(x,(list,tuple)) and isNumber(x[0]) and isListOfNumbers(x[1]))
isStrokeDashArray = isStrokeDashArray()

class LineShape(Shape):
    # base for types of lines

    _attrMap = AttrMap(
        strokeColor = AttrMapValue(isColorOrNone),
        strokeWidth = AttrMapValue(isNumber),
        strokeLineCap = AttrMapValue(OneOf(0,1,2),desc="Line cap 0=butt, 1=round & 2=square"),
        strokeLineJoin = AttrMapValue(OneOf(0,1,2),desc="Line join 0=miter, 1=round & 2=bevel"),
        strokeMiterLimit = AttrMapValue(isNumber,desc="miter limit control miter line joins"),
        strokeDashArray = AttrMapValue(isStrokeDashArray,desc="[numbers] or [phase,[numbers]]"),
        strokeOpacity = AttrMapValue(isOpacity,desc="The level of transparency of the line, any real number betwen 0 and 1"),
        strokeOverprint = AttrMapValue(isBoolean,desc='Turn on stroke overprinting'),
        overprintMask = AttrMapValue(isBoolean,desc='overprinting for ordinary CMYK',advancedUsage=1),
        )

    def __init__(self, kw):
        self.strokeColor = STATE_DEFAULTS['strokeColor']
        self.strokeWidth = 1
        self.strokeLineCap = 0
        self.strokeLineJoin = 0
        self.strokeMiterLimit = 0
        self.strokeDashArray = None
        self.strokeOpacity = None
        self.setProperties(kw)

class Line(LineShape):
    _attrMap = AttrMap(BASE=LineShape,
        x1 = AttrMapValue(isNumber,desc=""),
        y1 = AttrMapValue(isNumber,desc=""),
        x2 = AttrMapValue(isNumber,desc=""),
        y2 = AttrMapValue(isNumber,desc=""),
        )

    def __init__(self, x1, y1, x2, y2, **kw):
        LineShape.__init__(self, kw)
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def getBounds(self):
        "Returns bounding rectangle of object as (x1,y1,x2,y2)"
        return (self.x1, self.y1, self.x2, self.y2)

class SolidShape(LineShape):
    # base for anything with outline and content

    _attrMap = AttrMap(BASE=LineShape,
        fillColor = AttrMapValue(isColorOrNone,desc="filling color of the shape, e.g. red"),
        fillOpacity = AttrMapValue(isOpacity,desc="the level of transparency of the color, any real number between 0 and 1"),
        fillOverprint = AttrMapValue(isBoolean,desc='Turn on fill overprinting'),
        overprintMask = AttrMapValue(isBoolean,desc='overprinting for ordinary CMYK',advancedUsage=1),
        fillMode = AttrMapValue(OneOf(FILL_EVEN_ODD,FILL_NON_ZERO)),
        )

    def __init__(self, kw):
        self.fillColor = STATE_DEFAULTS['fillColor']
        self.fillOpacity = None
        # do this at the end so keywords overwrite
        #the above settings
        LineShape.__init__(self, kw)

# path operator  constants
_MOVETO, _LINETO, _CURVETO, _CLOSEPATH = list(range(4))
_PATH_OP_ARG_COUNT = (2, 2, 6, 0)  # [moveTo, lineTo, curveTo, closePath]
_PATH_OP_NAMES=['moveTo','lineTo','curveTo','closePath']

def _renderPath(path,drawFuncs,countOnly=False,forceClose=False):
    """Helper function for renderers."""
    # this could be a method of Path...
    points = path.points
    i = 0
    hadClosePath = 0
    hadMoveTo = 0
    active = not countOnly
    for op in path.operators:
        if op == _MOVETO:
            if forceClose:
                if hadMoveTo and pop!=_CLOSEPATH:
                    hadClosePath += 1
                    if active:
                        drawFuncs[_CLOSEPATH]()
            hadMoveTo += 1
        nArgs = _PATH_OP_ARG_COUNT[op]
        j = i + nArgs
        drawFuncs[op](*points[i:j])
        i = j
        if op == _CLOSEPATH:
            hadClosePath += 1
        pop = op
    if forceClose and hadMoveTo and pop!=_CLOSEPATH:
        hadClosePath += 1
        if active:
            drawFuncs[_CLOSEPATH]()
    return hadMoveTo == hadClosePath

_fillModeMap = {
        None: None,
        FILL_NON_ZERO: FILL_NON_ZERO,
        'non-zero': FILL_NON_ZERO,
        'nonzero': FILL_NON_ZERO,
        FILL_EVEN_ODD: FILL_EVEN_ODD,
        'even-odd': FILL_EVEN_ODD,
        'evenodd': FILL_EVEN_ODD,
        }

class Path(SolidShape):
    """Path, made up of straight lines and bezier curves."""

    _attrMap = AttrMap(BASE=SolidShape,
        points = AttrMapValue(isListOfNumbers),
        operators = AttrMapValue(isListOfNumbers),
        isClipPath = AttrMapValue(isBoolean),
        autoclose = AttrMapValue(NoneOr(OneOf('svg','pdf'))),
        fillMode = AttrMapValue(OneOf(FILL_EVEN_ODD,FILL_NON_ZERO)),
        )

    def __init__(self, points=None, operators=None, isClipPath=0, autoclose=None, fillMode=FILL_EVEN_ODD, **kw):
        SolidShape.__init__(self, kw)
        if points is None:
            points = []
        if operators is None:
            operators = []
        assert len(points) % 2 == 0, 'Point list must have even number of elements!'
        self.points = points
        self.operators = operators
        self.isClipPath = isClipPath
        self.autoclose=autoclose
        self.fillMode = fillMode

    def copy(self):
        new = self.__class__(self.points[:], self.operators[:])
        new.setProperties(self.getProperties())
        return new

    def moveTo(self, x, y):
        self.points.extend([x, y])
        self.operators.append(_MOVETO)

    def lineTo(self, x, y):
        self.points.extend([x, y])
        self.operators.append(_LINETO)

    def curveTo(self, x1, y1, x2, y2, x3, y3):
        self.points.extend([x1, y1, x2, y2, x3, y3])
        self.operators.append(_CURVETO)

    def closePath(self):
        self.operators.append(_CLOSEPATH)

    def getBounds(self):
        points = self.points
        try:    #in case this complex algorithm is not yet ready :)
            X = []
            aX = X.append
            eX = X.extend
            Y=[]
            aY = Y.append
            eY = Y.extend
            i = 0
            for op in self.operators:
                nArgs = _PATH_OP_ARG_COUNT[op]
                j = i + nArgs
                if nArgs==2:
                    #either moveTo or lineT0
                    aX(points[i])
                    aY(points[i+1])
                elif nArgs==6:
                    #curveTo
                    x1,x2,x3 = points[i:j:2]
                    eX(_getBezierExtrema(X[-1],x1,x2,x3))
                    y1,y2,y3 = points[i+1:j:2]
                    eY(_getBezierExtrema(Y[-1],y1,y2,y3))
                i = j
            return min(X),min(Y),max(X),max(Y)
        except:
            return getPathBounds(points)

EmptyClipPath=Path()    #special path

def getArcPoints(centerx, centery, radius, startangledegrees, endangledegrees, yradius=None, degreedelta=None, reverse=None):
    if yradius is None: yradius = radius
    points = []
    degreestoradians = pi/180.0
    startangle = startangledegrees*degreestoradians
    endangle = endangledegrees*degreestoradians
    while endangle<startangle:
        endangle = endangle+2*pi
    angle = float(endangle - startangle)
    a = points.append
    if angle>.001:
        degreedelta = min(angle,degreedelta or 1.)
        radiansdelta = degreedelta*degreestoradians
        n = max(int(angle/radiansdelta+0.5),1)
        radiansdelta = angle/n
        n += 1
    else:
        n = 1
        radiansdelta = 0

    for angle in range(n):
        angle = startangle+angle*radiansdelta
        a((centerx+radius*cos(angle),centery+yradius*sin(angle)))

    if reverse: points.reverse()
    return points

class ArcPath(Path):
    '''Path with an addArc method'''
    def addArc(self, centerx, centery, radius, startangledegrees, endangledegrees, yradius=None, degreedelta=None, moveTo=None, reverse=None):
        P = getArcPoints(centerx, centery, radius, startangledegrees, endangledegrees, yradius=yradius, degreedelta=degreedelta, reverse=reverse)
        if moveTo or not len(self.operators):
            self.moveTo(P[0][0],P[0][1])
            del P[0]
        for x, y in P: self.lineTo(x,y)

def definePath(pathSegs=[],isClipPath=0, dx=0, dy=0, **kw):
    O = []
    P = []
    for seg in pathSegs:
        if not isSeq(seg):
            opName = seg
            args = []
        else:
            opName = seg[0]
            args = seg[1:]
        if opName not in _PATH_OP_NAMES:
            raise ValueError('bad operator name %s' % opName)
        op = _PATH_OP_NAMES.index(opName)
        if len(args)!=_PATH_OP_ARG_COUNT[op]:
            raise ValueError('%s bad arguments %s' % (opName,str(args)))
        O.append(op)
        P.extend(list(args))
    for d,o in (dx,0), (dy,1):
        for i in range(o,len(P),2):
            P[i] = P[i]+d

    #if there's a bounding box given we constrain so our points lie in it
    #partial bbox is allowed and does something sensible
    bbox = kw.pop('bbox',None)
    if bbox:
        for j in 0,1:
            d = bbox[j],bbox[j+2]
            if d[0] is None and d[1] is None: continue
            a = P[j::2]
            a, b = min(a), max(a)
            if d[0] is not None and d[1] is not None:
                c, d = min(d), max(d)
                fac = (b-a)
                if abs(fac)>=1e-6:
                    fac = (d-c)/fac
                    for i in range(j,len(P),2):
                        P[i] = c + fac*(P[i]-a)
                else:
                    #there's no range in the bbox so fixed as average
                    for i in range(j,len(P),2):
                        P[i] = (c + d)*0.5
            else:
                #if   there's a  lower bound shift so min is lower bound
                #else there's an upper bound shift so max is upper bound
                c = d[0] - a if d[0] is not None else d[1] - b
                for i in range(j,len(P),2):
                    P[i] += c

    return Path(P,O,isClipPath,**kw)

class Rect(SolidShape):
    """Rectangle, possibly with rounded corners."""

    _attrMap = AttrMap(BASE=SolidShape,
        x = AttrMapValue(isNumber),
        y = AttrMapValue(isNumber),
        width = AttrMapValue(isNumber,desc="width of the object in points"),
        height = AttrMapValue(isNumber,desc="height of the objects in points"),
        rx = AttrMapValue(isNumber),
        ry = AttrMapValue(isNumber),
        )

    def __init__(self, x, y, width, height, rx=0, ry=0, **kw):
        SolidShape.__init__(self, kw)
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.rx = rx
        self.ry = ry

    def copy(self):
        new = self.__class__(self.x, self.y, self.width, self.height)
        new.setProperties(self.getProperties())
        return new

    def getBounds(self):
        return (self.x, self.y, self.x + self.width, self.y + self.height)

class Image(SolidShape):
    """Bitmap image."""

    _attrMap = AttrMap(BASE=SolidShape,
        x = AttrMapValue(isNumber),
        y = AttrMapValue(isNumber),
        width = AttrMapValue(isNumberOrNone,desc="width of the object in points"),
        height = AttrMapValue(isNumberOrNone,desc="height of the objects in points"),
        path = AttrMapValue(None),
        )

    def __init__(self, x, y, width, height, path, **kw):
        SolidShape.__init__(self, kw)
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.path = path

    def copy(self):
        new = self.__class__(self.x, self.y, self.width, self.height, self.path)
        new.setProperties(self.getProperties())
        return new

    def getBounds(self):
        # bug fix contributed by Marcel Tromp <mtromp.docbook@gmail.com>
        return (self.x, self.y, self.x + self.width, self.y + self.height)

class Circle(SolidShape):

    _attrMap = AttrMap(BASE=SolidShape,
        cx = AttrMapValue(isNumber,desc="x of the centre"),
        cy = AttrMapValue(isNumber,desc="y of the centre"),
        r = AttrMapValue(isNumber,desc="radius in points"),
        )

    def __init__(self, cx, cy, r, **kw):
        SolidShape.__init__(self, kw)
        self.cx = cx
        self.cy = cy
        self.r = r

    def copy(self):
        new = self.__class__(self.cx, self.cy, self.r)
        new.setProperties(self.getProperties())
        return new

    def getBounds(self):
        return (self.cx - self.r, self.cy - self.r, self.cx + self.r, self.cy + self.r)

class Ellipse(SolidShape):
    _attrMap = AttrMap(BASE=SolidShape,
        cx = AttrMapValue(isNumber,desc="x of the centre"),
        cy = AttrMapValue(isNumber,desc="y of the centre"),
        rx = AttrMapValue(isNumber,desc="x radius"),
        ry = AttrMapValue(isNumber,desc="y radius"),
        )

    def __init__(self, cx, cy, rx, ry, **kw):
        SolidShape.__init__(self, kw)
        self.cx = cx
        self.cy = cy
        self.rx = rx
        self.ry = ry

    def copy(self):
        new = self.__class__(self.cx, self.cy, self.rx, self.ry)
        new.setProperties(self.getProperties())
        return new

    def getBounds(self):
            return (self.cx - self.rx, self.cy - self.ry, self.cx + self.rx, self.cy + self.ry)

class Wedge(SolidShape):
    """A "slice of a pie" by default translates to a polygon moves anticlockwise
       from start angle to end angle"""

    _attrMap = AttrMap(BASE=SolidShape,
        centerx = AttrMapValue(isNumber,desc="x of the centre"),
        centery = AttrMapValue(isNumber,desc="y of the centre"),
        radius = AttrMapValue(isNumber,desc="radius in points"),
        startangledegrees = AttrMapValue(isNumber),
        endangledegrees = AttrMapValue(isNumber),
        yradius = AttrMapValue(isNumberOrNone),
        radius1 = AttrMapValue(isNumberOrNone),
        yradius1 = AttrMapValue(isNumberOrNone),
        annular = AttrMapValue(isBoolean,desc='treat as annular ring'),
        )

    degreedelta = 1 # jump every 1 degrees

    def __init__(self, centerx, centery, radius, startangledegrees, endangledegrees, yradius=None,
            annular=False, **kw):
        SolidShape.__init__(self, kw)
        while endangledegrees<startangledegrees:
            endangledegrees = endangledegrees+360
        #print "__init__"
        self.centerx, self.centery, self.radius, self.startangledegrees, self.endangledegrees = \
            centerx, centery, radius, startangledegrees, endangledegrees
        self.yradius = yradius
        self.annular = annular

    def _xtraRadii(self):
        yradius = getattr(self, 'yradius', None)
        if yradius is None: yradius = self.radius
        radius1 = getattr(self,'radius1', None)
        yradius1 = getattr(self,'yradius1',radius1)
        if radius1 is None: radius1 = yradius1
        return yradius, radius1, yradius1

    #def __repr__(self):
    #        return "Wedge"+repr((self.centerx, self.centery, self.radius, self.startangledegrees, self.endangledegrees ))
    #__str__ = __repr__

    def asPolygon(self):
        #print "asPolygon"
        centerx= self.centerx
        centery = self.centery
        radius = self.radius
        yradius, radius1, yradius1 = self._xtraRadii()
        startangledegrees = self.startangledegrees
        endangledegrees = self.endangledegrees
        degreestoradians = pi/180.0
        startangle = startangledegrees*degreestoradians
        endangle = endangledegrees*degreestoradians
        while endangle<startangle:
            endangle = endangle+2*pi
        angle = float(endangle-startangle)
        points = []
        if angle>0.001:
            degreedelta = min(self.degreedelta or 1.,angle)
            radiansdelta = degreedelta*degreestoradians
            n = max(1,int(angle/radiansdelta+0.5))
            radiansdelta = angle/n
            n += 1
        else:
            n = 1
            radiansdelta = 0
        CA = []
        CAA = CA.append
        a = points.append
        for angle in range(n):
            angle = startangle+angle*radiansdelta
            CAA((cos(angle),sin(angle)))
        for c,s in CA:
            a(centerx+radius*c)
            a(centery+yradius*s)
        if (radius1==0 or radius1 is None) and (yradius1==0 or yradius1 is None):
            a(centerx); a(centery)
        else:
            CA.reverse()
            for c,s in CA:
                a(centerx+radius1*c)
                a(centery+yradius1*s)
        if self.annular:
            P = Path(fillMode=getattr(self,'fillMode', FILL_EVEN_ODD))
            P.moveTo(points[0],points[1])
            for x in range(2,2*n,2):
                P.lineTo(points[x],points[x+1])
            P.closePath()
            P.moveTo(points[2*n],points[2*n+1])
            for x in range(2*n+2,4*n,2):
                P.lineTo(points[x],points[x+1])
            P.closePath()
            return P
        else:
            return Polygon(points)

    def copy(self):
        new = self.__class__(self.centerx,
                    self.centery,
                    self.radius,
                    self.startangledegrees,
                    self.endangledegrees)
        new.setProperties(self.getProperties())
        return new

    def getBounds(self):
        return self.asPolygon().getBounds()

class Polygon(SolidShape):
    """Defines a closed shape; Is implicitly
    joined back to the start for you."""

    _attrMap = AttrMap(BASE=SolidShape,
        points = AttrMapValue(isListOfNumbers,desc="list of numbers in the form x1, y1, x2, y2 ... xn, yn"),
        )

    def __init__(self, points=[], **kw):
        SolidShape.__init__(self, kw)
        assert len(points) % 2 == 0, 'Point list must have even number of elements!'
        self.points = points or []

    def copy(self):
        new = self.__class__(self.points)
        new.setProperties(self.getProperties())
        return new

    def getBounds(self):
        return getPointsBounds(self.points)

class PolyLine(LineShape):
    """Series of line segments.  Does not define a
    closed shape; never filled even if apparently joined.
    Put the numbers in the list, not two-tuples."""

    _attrMap = AttrMap(BASE=LineShape,
        points = AttrMapValue(isListOfNumbers,desc="list of numbers in the form x1, y1, x2, y2 ... xn, yn"),
        )

    def __init__(self, points=[], **kw):
        LineShape.__init__(self, kw)
        points = points or []
        lenPoints = len(points)
        if lenPoints:
            if isSeq(points[0]):
                L = []
                for (x,y) in points:
                    L.append(x)
                    L.append(y)
                points = L
            else:
                assert len(points) % 2 == 0, 'Point list must have even number of elements!'
        self.points = points

    def copy(self):
        new = self.__class__(self.points)
        new.setProperties(self.getProperties())
        return new

    def getBounds(self):
        return getPointsBounds(self.points)

class Hatching(Path):
    '''define a hatching of a set of polygons defined by lists of the form [x0,y0,x1,y1,....,xn,yn]'''

    _attrMap = AttrMap(BASE=Path,
        xyLists = AttrMapValue(EitherOr((isListOfNumbers,SequenceOf(isListOfNumbers,lo=1)),"xy list(s)"),desc="list(s) of numbers in the form x1, y1, x2, y2 ... xn, yn"),
        angles = AttrMapValue(EitherOr((isNumber,isListOfNumbers,"angle(s)")),desc="the angle or list of angles at which hatching lines should be drawn"),
        spacings = AttrMapValue(EitherOr((isNumber,isListOfNumbers,"spacings(s)")),desc="orthogonal distance(s) between hatching lines"),
        )

    def __init__(self, spacings=2, angles=45, xyLists=[], **kwds):
        Path.__init__(self, **kwds)
        if isListOfNumbers(xyLists):
            xyLists  = (xyLists,)
        if isNumber(angles):
            angles = (angles,)  #turn into a sequence
        if isNumber(spacings):
            spacings = (spacings,)  #turn into a sequence
        i = len(angles)-len(spacings)
        if i>0:
            spacings = list(spacings)+i*[spacings[-1]]

        self.xyLists = xyLists
        self.angles = angles
        self.spacings = spacings

        moveTo = self.moveTo
        lineTo = self.lineTo

        for i, theta in enumerate(angles):
            spacing = spacings[i]
            theta = radians(theta)
            cosTheta = cos(theta)
            sinTheta = sin(theta)

            spanMin = 0x7fffffff
            spanMax = -spanMin

            #   Loop to determine the span over which diagonal lines must be drawn.
            for P in xyLists:
                for j in range(0,len(P),2):
                    #   rotated point, since the stripes may be at an angle.
                    y = P[j+1]*cosTheta-P[j]*sinTheta
                    spanMin = min(y,spanMin)
                    spanMax = max(y,spanMax)

            #   Turn the span into a discrete step range.
            spanStart = int(floor(spanMin/spacing)) - 1
            spanEnd  = int(floor(spanMax/spacing)) + 1

            #   Loop to create all stripes.
            for step in range(spanStart,spanEnd):
                nodeX = []
                stripeY = spacing*step

                #   Loop to build a node list for one row of stripes.
                for P in xyLists:
                    k = len(P)-2    #start by comparing with the last point
                    for j in range(0,len(P),2):
                        a = P[k]
                        b = P[k+1]
                        a1 = a*cosTheta + b*sinTheta
                        b1 = b*cosTheta - a*sinTheta
                        x = P[j]
                        y = P[j+1]

                        x1 = x*cosTheta+y*sinTheta
                        y1 = y*cosTheta-x*sinTheta

                        #   Find the node, if any.
                        if (b1<stripeY and y1>=stripeY) or y1<stripeY and b1>=stripeY:
                            nodeX.append(a1+(x1-a1)*(stripeY-b1)/(y1-b1))

                        k = j

                nodeX.sort()

                #   Loop to draw one row of line segments.
                for j in range(0,len(nodeX),2):
                    #   Rotate the points back to their original coordinate system.
                    a = nodeX[j]*cosTheta - stripeY*sinTheta
                    b = stripeY*cosTheta+nodeX[j]*sinTheta
                    x = nodeX[j+1]*cosTheta - stripeY*sinTheta
                    y = stripeY*cosTheta + nodeX[j+1]*sinTheta

                    #Draw a single stripe segment.
                    moveTo(a,b)
                    lineTo(x,y)

def numericXShift(tA,text,w,fontName,fontSize,encoding=None,pivotCharacter=decimalSymbol):
    dp = getattr(tA,'_dp',pivotCharacter)
    i = text.rfind(dp)
    if i>=0:
        dpOffs = getattr(tA,'_dpLen',0)
        w = dpOffs + stringWidth(text[:i],fontName,fontSize,encoding)
    return w

class String(Shape):
    """Not checked against the spec, just a way to make something work.
    Can be anchored left, middle or end."""

    # to do.
    _attrMap = AttrMap(
        x = AttrMapValue(isNumber,desc="x point of anchoring"),
        y = AttrMapValue(isNumber,desc="y point of anchoring"),
        text = AttrMapValue(isString,desc="the text of the string"),
        fontName = AttrMapValue(None,desc="font name of the text - font is either acrobat standard or registered when using external font."),
        fontSize = AttrMapValue(isNumber,desc="font size"),
        fillColor = AttrMapValue(isColorOrNone,desc="color of the font"),
        textAnchor = AttrMapValue(OneOf('start','middle','end','numeric'),desc="treat (x,y) as one of the options below."),
        encoding = AttrMapValue(isString),
        textRenderMode = AttrMapValue(OneOf(0,1,2,3,4,5,6,7),desc="Control whether text is filled/stroked etc etc"),
        )
    encoding = 'utf8'

    def __init__(self, x, y, text, **kw):
        self.x = x
        self.y = y
        self.text = text
        self.textAnchor = 'start'
        self.fontName = STATE_DEFAULTS['fontName']
        self.fontSize = STATE_DEFAULTS['fontSize']
        self.fillColor = STATE_DEFAULTS['fillColor']
        self.setProperties(kw)

    def getEast(self):
        return self.x + stringWidth(self.text,self.fontName,self.fontSize, self.encoding)

    def copy(self):
        new = self.__class__(self.x, self.y, self.text)
        new.setProperties(self.getProperties())
        return new

    def getBounds(self):
        # assumes constant drop of 0.2*size to baseline
        t = self.text
        w = stringWidth(t,self.fontName,self.fontSize,self.encoding)
        tA = self.textAnchor
        x = self.x
        if tA!='start':
            if tA=='middle':
                x -= 0.5*w
            elif tA=='end':
                x -= w
            elif tA=='numeric':
                x -= numericXShift(tA,t,w,self.fontName,self.fontSize,self.encoding)
        return (x, self.y - 0.2 * self.fontSize, x+w, self.y + self.fontSize)

class UserNode(_DrawTimeResizeable):
    """A simple template for creating a new node.  The user (Python
    programmer) may subclasses this.  provideNode() must be defined to
    provide a Shape primitive when called by a renderer.  It does
    NOT inherit from Shape, as the renderer always replaces it, and
    your own classes can safely inherit from it without getting
    lots of unintended behaviour."""

    def provideNode(self):
        """Override this to create your own node. This lets widgets be
        added to drawings; they must create a shape (typically a group)
        so that the renderer can draw the custom node."""

        raise NotImplementedError("this method must be redefined by the user/programmer")

class DirectDraw(Shape):
    """try to draw directly on the canvas"""
    def drawDirectly(self,canvas):
        raise NotImplementedError("this method must be redefined by the user/programmer")

def test():
    r = Rect(10,10,200,50)
    import pprint
    pp = pprint.pprint
    w = sys.stdout.write
    w('a Rectangle: ')
    pp(r.getProperties())
    w('\nverifying...')
    r.verify()
    w(' OK\n')
    #print 'setting rect.z = "spam"'
    #r.z = 'spam'
    w('deleting rect.width ')
    del r.width
    w('verifying...')
    r.verify()

if __name__=='__main__':
    test()
