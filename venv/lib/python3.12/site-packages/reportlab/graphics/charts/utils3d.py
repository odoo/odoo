from reportlab.graphics.shapes import Drawing, Polygon, Line

def _getShaded(col,shd=None,shading=0.1):
    if shd is None:
        from reportlab.lib.colors import Blacker
        if col: shd = Blacker(col,1-shading)
    return shd

def _getLit(col,shd=None,lighting=0.1):
    if shd is None:
        from reportlab.lib.colors import Whiter
        if col: shd = Whiter(col,1-lighting)
    return shd


def _draw_3d_bar(G, x1, x2, y0, yhigh, xdepth, ydepth,
                fillColor=None, fillColorShaded=None,
                strokeColor=None, strokeWidth=1, shading=0.1):
    fillColorShaded = _getShaded(fillColor,None,shading)
    fillColorShadedTop = _getShaded(fillColor,None,shading/2.0)

    def _add_3d_bar(x1, x2, y1, y2, xoff, yoff,
                    G=G,strokeColor=strokeColor, strokeWidth=strokeWidth, fillColor=fillColor):
        G.add(Polygon((x1,y1, x1+xoff,y1+yoff, x2+xoff,y2+yoff, x2,y2),
            strokeWidth=strokeWidth, strokeColor=strokeColor, fillColor=fillColor,strokeLineJoin=1))

    usd = max(y0, yhigh)
    if xdepth or ydepth:
        if y0!=yhigh:   #non-zero height
            _add_3d_bar( x2, x2, y0, yhigh, xdepth, ydepth, fillColor=fillColorShaded) #side

        _add_3d_bar(x1, x2, usd, usd, xdepth, ydepth, fillColor=fillColorShadedTop)    #top

    G.add(Polygon((x1,y0,x2,y0,x2,yhigh,x1,yhigh),
        strokeColor=strokeColor, strokeWidth=strokeWidth, fillColor=fillColor,strokeLineJoin=1)) #front

    if xdepth or ydepth:
        G.add(Line( x1, usd, x2, usd, strokeWidth=strokeWidth, strokeColor=strokeColor or fillColorShaded))

class _YStrip:
    def __init__(self,y0,y1, slope, fillColor, fillColorShaded, shading=0.1):
        self.y0 = y0
        self.y1 = y1
        self.slope = slope
        self.fillColor = fillColor
        self.fillColorShaded = _getShaded(fillColor,fillColorShaded,shading)

def _ystrip_poly( x0, x1, y0, y1, xoff, yoff):
    return [x0,y0,x0+xoff,y0+yoff,x1+xoff,y1+yoff,x1,y1]


def _make_3d_line_info( G, x0, x1, y0, y1, z0, z1,
                    theta_x, theta_y,
                    fillColor, fillColorShaded=None, tileWidth=1,
                    strokeColor=None, strokeWidth=None, strokeDashArray=None,
                    shading=0.1):
    zwidth = abs(z1-z0)
    xdepth = zwidth*theta_x
    ydepth = zwidth*theta_y
    depth_slope  = xdepth==0 and 1e150 or -ydepth/float(xdepth)

    x = float(x1-x0)
    slope = x==0 and 1e150 or (y1-y0)/x

    c = slope>depth_slope and _getShaded(fillColor,fillColorShaded,shading) or fillColor
    zy0 = z0*theta_y
    zx0 = z0*theta_x

    tileStrokeWidth = 0.6
    if tileWidth is None:
        D = [(x1,y1)]
    else:
        T = ((y1-y0)**2+(x1-x0)**2)**0.5
        tileStrokeWidth *= tileWidth
        if T<tileWidth:
            D = [(x1,y1)]
        else:
            n = int(T/float(tileWidth))+1
            dx = float(x1-x0)/n
            dy = float(y1-y0)/n
            D = []
            a = D.append
            for i in range(1,n):
                a((x0+dx*i,y0+dy*i))

    a = G.add
    x_0 = x0+zx0
    y_0 = y0+zy0
    for x,y in D:
        x_1 = x+zx0
        y_1 = y+zy0
        P = Polygon(_ystrip_poly(x_0, x_1, y_0, y_1, xdepth, ydepth),
                    fillColor = c, strokeColor=c, strokeWidth=tileStrokeWidth)
        a((0,z0,z1,x_0,y_0,P))
        x_0 = x_1
        y_0 = y_1

from math import pi
_pi_2 = pi*0.5
_2pi = 2*pi
_180_pi=180./pi

def _2rad(angle):
    return angle/_180_pi

def mod_2pi(radians):
    radians = radians % _2pi
    if radians<-1e-6: radians += _2pi
    return radians

def _2deg(o):
    return o*_180_pi

def _360(a):
    a %= 360
    if a<-1e-6: a += 360
    return a

_ZERO = 1e-8
_ONE = 1-_ZERO
class _Segment:
    def __init__(self,s,i,data):
        S = data[s]
        x0 = S[i-1][0]
        y0 = S[i-1][1]
        x1 = S[i][0]
        y1 = S[i][1]
        if x1<x0:
            x0,y0,x1,y1 = x1,y1,x0,y0
        # (y-y0)*(x1-x0) = (y1-y0)*(x-x0)
        # (x1-x0)*y + (y0-y1)*x = y0*(x1-x0)+x0*(y0-y1)
        # a*y+b*x = c
        self.a = float(x1-x0)
        self.b = float(y1-y0)
        self.x0 = x0
        self.x1 = x1
        self.y0 = y0
        self.y1 = y1
        self.series = s
        self.i = i
        self.s = s

    def __str__(self):
        return '[(%s,%s),(%s,%s)]' % (self.x0,self.y0,self.x1,self.y1)

    __repr__ = __str__

    def intersect(self,o,I):
        '''try to find an intersection with _Segment o
        '''
        x0 = self.x0
        ox0 = o.x0
        assert x0<=ox0
        if ox0>self.x1: return 1
        if o.s==self.s and o.i in (self.i-1,self.i+1): return
        a = self.a
        b = self.b
        oa = o.a
        ob = o.b
        det = ob*a - oa*b
        if -1e-8<det<1e-8: return
        dx = x0 - ox0
        dy = self.y0 - o.y0
        u = (oa*dy - ob*dx)/det
        ou = (a*dy - b*dx)/det
        if u<0 or u>1 or ou<0 or ou>1: return
        x = x0 + u*a
        y = self.y0 + u*b
        if _ZERO<u<_ONE:
            t = self.s,self.i,x,y
            if t not in I: I.append(t)
        if _ZERO<ou<_ONE:
            t = o.s,o.i,x,y
            if t not in I:  I.append(t)

def _segKey(a):
    return (a.x0,a.x1,a.y0,a.y1,a.s,a.i)

def find_intersections(data,small=0):
    '''
    data is a sequence of series
    each series is a list of (x,y) coordinates
    where x & y are ints or floats

    find_intersections returns a sequence of 4-tuples
        i, j, x, y

    where i is a data index j is an insertion position for data[i]
    and x, y are coordinates of an intersection of series data[i]
    with some other series. If correctly implemented we get all such
    intersections. We don't count endpoint intersections and consider
    parallel lines as non intersecting (even when coincident).
    We ignore segments that have an estimated size less than small.
    '''

    #find all line segments
    S = []
    a = S.append
    for s in range(len(data)):
        ds = data[s]
        if not ds: continue
        n = len(ds)
        if n==1: continue
        for i in range(1,n):
            seg = _Segment(s,i,data)
            if seg.a+abs(seg.b)>=small: a(seg)
    S.sort(key=_segKey)
    I = []
    n = len(S)
    for i in range(0,n-1):
        s = S[i]
        for j in range(i+1,n):
            if s.intersect(S[j],I)==1: break
    I.sort()
    return I

if __name__=='__main__':
    from reportlab.graphics.shapes import Drawing
    from reportlab.lib.colors import lightgrey, pink
    D = Drawing(300,200)
    _draw_3d_bar(D, 10, 20, 10, 50, 5, 5, fillColor=lightgrey, strokeColor=pink)
    _draw_3d_bar(D, 30, 40, 10, 45, 5, 5, fillColor=lightgrey, strokeColor=pink)

    D.save(formats=['pdf'],outDir='.',fnRoot='_draw_3d_bar')

    print(find_intersections([[(0,0.5),(1,0.5),(0.5,0),(0.5,1)],[(.2666666667,0.4),(0.1,0.4),(0.1,0.2),(0,0),(1,1)],[(0,1),(0.4,0.1),(1,0.1)]]))
    print(find_intersections([[(0.1, 0.2), (0.1, 0.4)], [(0, 1), (0.4, 0.1)]]))
    print(find_intersections([[(0.2, 0.4), (0.1, 0.4)], [(0.1, 0.8), (0.4, 0.1)]]))
    print(find_intersections([[(0,0),(1,1)],[(0.4,0.1),(1,0.1)]]))
    print(find_intersections([[(0,0.5),(1,0.5),(0.5,0),(0.5,1)],[(0,0),(1,1)],[(0.1,0.8),(0.4,0.1),(1,0.1)]]))
