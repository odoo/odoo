#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/graphics/widgets/markers.py
"""
This modules defines a collection of markers used in charts.
"""
__version__=''' $Id: markers.py 2385 2004-06-17 15:26:05Z rgbecker $ '''
from types import FunctionType, ClassType
from reportlab.graphics.shapes import Rect, Line, Circle, Polygon, Drawing, Group
from reportlab.graphics.widgets.signsandsymbols import SmileyFace
from reportlab.graphics.widgetbase import Widget
from reportlab.lib.validators import isNumber, isColorOrNone, OneOf, Validator
from reportlab.lib.attrmap import AttrMap, AttrMapValue
from reportlab.lib.colors import black
from reportlab.graphics.widgets.flags import Flag
from math import sin, cos, pi
import copy, new
_toradians = pi/180.0

class Marker(Widget):
    '''A polymorphic class of markers'''
    _attrMap = AttrMap(BASE=Widget,
                    kind = AttrMapValue(
                            OneOf(None, 'Square', 'Diamond', 'Circle', 'Cross', 'Triangle', 'StarSix',
                                'Pentagon', 'Hexagon', 'Heptagon', 'Octagon', 'StarFive',
                                'FilledSquare', 'FilledCircle', 'FilledDiamond', 'FilledCross',
                                'FilledTriangle','FilledStarSix', 'FilledPentagon', 'FilledHexagon',
                                'FilledHeptagon', 'FilledOctagon', 'FilledStarFive',
                                'Smiley'),
                            desc='marker type name'),
                    size = AttrMapValue(isNumber,desc='marker size'),
                    x = AttrMapValue(isNumber,desc='marker x coordinate'),
                    y = AttrMapValue(isNumber,desc='marker y coordinate'),
                    dx = AttrMapValue(isNumber,desc='marker x coordinate adjustment'),
                    dy = AttrMapValue(isNumber,desc='marker y coordinate adjustment'),
                    angle = AttrMapValue(isNumber,desc='marker rotation'),
                    fillColor = AttrMapValue(isColorOrNone, desc='marker fill colour'),
                    strokeColor = AttrMapValue(isColorOrNone, desc='marker stroke colour'),
                    strokeWidth = AttrMapValue(isNumber, desc='marker stroke width'),
                    )

    def __init__(self,*args,**kw):
        self.kind = None
        self.strokeColor = black
        self.strokeWidth = 0.1
        self.fillColor = None
        self.size = 5
        self.x = self.y = self.dx = self.dy = self.angle = 0
        self.setProperties(kw)

    def clone(self):
        return new.instance(self.__class__,self.__dict__.copy())

    def _Smiley(self):
        x, y = self.x+self.dx, self.y+self.dy
        d = self.size/2.0
        s = SmileyFace()
        s.fillColor = self.fillColor
        s.strokeWidth = self.strokeWidth
        s.strokeColor = self.strokeColor
        s.x = x-d
        s.y = y-d
        s.size = d*2
        return s

    def _Square(self):
        x, y = self.x+self.dx, self.y+self.dy
        d = self.size/2.0
        s = Rect(x-d,y-d,2*d,2*d,fillColor=self.fillColor,strokeColor=self.strokeColor,strokeWidth=self.strokeWidth)
        return s

    def _Diamond(self):
        d = self.size/2.0
        return self._doPolygon((-d,0,0,d,d,0,0,-d))

    def _Circle(self):
        x, y = self.x+self.dx, self.y+self.dy
        s = Circle(x,y,self.size/2.0,fillColor=self.fillColor,strokeColor=self.strokeColor,strokeWidth=self.strokeWidth)
        return s

    def _Cross(self):
        x, y = self.x+self.dx, self.y+self.dy
        s = float(self.size)
        h, s = s/2, s/6
        return self._doPolygon((-s,-h,-s,-s,-h,-s,-h,s,-s,s,-s,h,s,h,s,s,h,s,h,-s,s,-s,s,-h))

    def _Triangle(self):
        x, y = self.x+self.dx, self.y+self.dy
        r = float(self.size)/2
        c = 30*_toradians
        s = sin(30*_toradians)*r
        c = cos(c)*r
        return self._doPolygon((0,r,-c,-s,c,-s))

    def _StarSix(self):
        r = float(self.size)/2
        c = 30*_toradians
        s = sin(c)*r
        c = cos(c)*r
        z = s/2
        g = c/2
        return self._doPolygon((0,r,-z,s,-c,s,-s,0,-c,-s,-z,-s,0,-r,z,-s,c,-s,s,0,c,s,z,s))

    def _StarFive(self):
        R = float(self.size)/2
        r = R*sin(18*_toradians)/cos(36*_toradians)
        P = []
        angle = 90
        for i in xrange(5):
            for radius in R, r:
                theta = angle*_toradians
                P.append(radius*cos(theta))
                P.append(radius*sin(theta))
                angle = angle + 36
        return self._doPolygon(P)

    def _Pentagon(self):
        return self._doNgon(5)

    def _Hexagon(self):
        return self._doNgon(6)

    def _Heptagon(self):
        return self._doNgon(7)

    def _Octagon(self):
        return self._doNgon(8)

    def _doPolygon(self,P):
        x, y = self.x+self.dx, self.y+self.dy
        if x or y: P = map(lambda i,P=P,A=[x,y]: P[i] + A[i&1], range(len(P)))
        return Polygon(P, strokeWidth =self.strokeWidth, strokeColor=self.strokeColor, fillColor=self.fillColor)

    def _doFill(self):
        old = self.fillColor
        if old is None:
            self.fillColor = self.strokeColor
        r = (self.kind and getattr(self,'_'+self.kind[6:]) or Group)()
        self.fillColor = old
        return r

    def _doNgon(self,n):
        P = []
        size = float(self.size)/2
        for i in xrange(n):
            r = (2.*i/n+0.5)*pi
            P.append(size*cos(r))
            P.append(size*sin(r))
        return self._doPolygon(P)

    _FilledCircle = _doFill
    _FilledSquare = _doFill
    _FilledDiamond = _doFill
    _FilledCross = _doFill
    _FilledTriangle = _doFill
    _FilledStarSix = _doFill
    _FilledPentagon = _doFill
    _FilledHexagon = _doFill
    _FilledHeptagon = _doFill
    _FilledOctagon = _doFill
    _FilledStarFive = _doFill

    def draw(self):
        if self.kind:
            m = getattr(self,'_'+self.kind)
            if self.angle:
                _x, _dx, _y, _dy = self.x, self.dx, self.y, self.dy
                self.x, self.dx, self.y, self.dy = 0,0,0,0
                try:
                    m = m()
                finally:
                    self.x, self.dx, self.y, self.dy = _x, _dx, _y, _dy
                if not isinstance(m,Group):
                    _m, m = m, Group()
                    m.add(_m)
                if self.angle: m.rotate(self.angle)
                x, y = _x+_dx, _y+_dy
                if x or y: m.shift(x,y)
            else:
                m = m()
        else:
            m = Group()
        return m

def uSymbol2Symbol(uSymbol,x,y,color):
    if type(uSymbol) == FunctionType:
        symbol = uSymbol(x, y, 5, color)
    elif type(uSymbol) == ClassType and issubclass(uSymbol,Widget):
        size = 10.
        symbol = uSymbol()
        symbol.x = x - (size/2)
        symbol.y = y - (size/2)
        try:
            symbol.size = size
            symbol.color = color
        except:
            pass
    elif isinstance(uSymbol,Marker) or isinstance(uSymbol,Flag):
        symbol = uSymbol.clone()
        if isinstance(uSymbol,Marker): symbol.fillColor = symbol.fillColor or color
        symbol.x, symbol.y = x, y
    else:
        symbol = None
    return symbol

class _isSymbol(Validator):
    def test(self,x):
        return callable(x) or isinstance(x,Marker) or isinstance(x,Flag) \
                or (type(x)==ClassType and issubclass(x,Widget))

isSymbol = _isSymbol()

def makeMarker(name,**kw):
    if Marker._attrMap['kind'].validate(name):
        m = apply(Marker,(),kw)
        m.kind = name
    elif name[-5:]=='_Flag' and Flag._attrMap['kind'].validate(name[:-5]):
        m = apply(Flag,(),kw)
        m.kind = name[:-5]
        m.size = 10
    else:
        raise ValueError, "Invalid marker name %s" % name
    return m

if __name__=='__main__':
    D = Drawing()
    D.add(Marker())
    D.save(fnRoot='Marker',formats=['pdf'], outDir='/tmp')
