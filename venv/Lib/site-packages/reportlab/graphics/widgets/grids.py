#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/graphics/widgets/grids.py
__version__='3.3.0'

from reportlab.lib import colors
from reportlab.lib.validators import isNumber, isColorOrNone, isBoolean, isListOfNumbers, OneOf, isListOfColors, isNumberOrNone
from reportlab.lib.attrmap import AttrMap, AttrMapValue
from reportlab.graphics.shapes import Drawing, Group, Line, Rect, LineShape, definePath, EmptyClipPath
from reportlab.graphics.widgetbase import Widget

def frange(start, end=None, inc=None):
    "A range function, that does accept float increments..."

    if end == None:
        end = start + 0.0
        start = 0.0

    if inc == None:
        inc = 1.0

    L = []
    end = end - inc*0.0001  #to avoid numrical problems
    while 1:
        next = start + len(L) * inc
        if inc > 0 and next >= end:
            break
        elif inc < 0 and next <= end:
            break
        L.append(next)

    return L


def makeDistancesList(list):
    """Returns a list of distances between adjacent numbers in some input list.

    E.g. [1, 1, 2, 3, 5, 7] -> [0, 1, 1, 2, 2]
    """

    d = []
    for i in range(len(list[:-1])):
        d.append(list[i+1] - list[i])

    return d


class Grid(Widget):
    """This makes a rectangular grid of equidistant stripes.

    The grid contains an outer border rectangle, and stripes
    inside which can be drawn with lines and/or as solid tiles.
    The drawing order is: outer rectangle, then lines and tiles.

    The stripes' width is indicated as 'delta'. The sequence of
    stripes can have an offset named 'delta0'. Both values need
    to be positive!
    """

    _attrMap = AttrMap(
        x = AttrMapValue(isNumber, desc="The grid's lower-left x position."),
        y = AttrMapValue(isNumber, desc="The grid's lower-left y position."),
        width = AttrMapValue(isNumber, desc="The grid's width."),
        height = AttrMapValue(isNumber, desc="The grid's height."),
        orientation = AttrMapValue(OneOf(('vertical', 'horizontal')),
            desc='Determines if stripes are vertical or horizontal.'),
        useLines = AttrMapValue(OneOf((0, 1)),
            desc='Determines if stripes are drawn with lines.'),
        useRects = AttrMapValue(OneOf((0, 1)),
            desc='Determines if stripes are drawn with solid rectangles.'),
        delta = AttrMapValue(isNumber,
            desc='Determines the width/height of the stripes.'),
        delta0 = AttrMapValue(isNumber,
            desc='Determines the stripes initial width/height offset.'),
        deltaSteps = AttrMapValue(isListOfNumbers,
            desc='List of deltas to be used cyclically.'),
        stripeColors = AttrMapValue(isListOfColors,
            desc='Colors applied cyclically in the right or upper direction.'),
        fillColor = AttrMapValue(isColorOrNone,
            desc='Background color for entire rectangle.'),
        strokeColor = AttrMapValue(isColorOrNone,
            desc='Color used for lines.'),
        strokeWidth = AttrMapValue(isNumber,
            desc='Width used for lines.'),
        rectStrokeColor = AttrMapValue(isColorOrNone, desc='Color for outer rect stroke.'),
        rectStrokeWidth = AttrMapValue(isNumberOrNone, desc='Width for outer rect stroke.'),
        )

    def __init__(self):
        self.x = 0
        self.y = 0
        self.width = 100
        self.height = 100
        self.orientation = 'vertical'
        self.useLines = 0
        self.useRects = 1
        self.delta = 20
        self.delta0 = 0
        self.deltaSteps = []
        self.fillColor = colors.white
        self.stripeColors = [colors.red, colors.green, colors.blue]
        self.strokeColor = colors.black
        self.strokeWidth = 2


    def demo(self):
        D = Drawing(100, 100)

        g = Grid()
        D.add(g)

        return D

    def makeOuterRect(self):
        strokeColor = getattr(self,'rectStrokeColor',self.strokeColor)
        strokeWidth = getattr(self,'rectStrokeWidth',self.strokeWidth)
        if self.fillColor or (strokeColor and strokeWidth):
            rect = Rect(self.x, self.y, self.width, self.height)
            rect.fillColor = self.fillColor
            rect.strokeColor = strokeColor
            rect.strokeWidth = strokeWidth
            return rect
        else:
            return None

    def makeLinePosList(self, start, isX=0):
        "Returns a list of positions where to place lines."

        w, h = self.width, self.height
        if isX:
            length = w
        else:
            length = h
        if self.deltaSteps:
            r = [start + self.delta0]
            i = 0
            while 1:
                if r[-1] > start + length:
                    del r[-1]
                    break
                r.append(r[-1] + self.deltaSteps[i % len(self.deltaSteps)])
                i = i + 1
        else:
            r = frange(start + self.delta0, start + length, self.delta)

        r.append(start + length)
        if self.delta0 != 0:
            r.insert(0, start)
        #print 'Grid.makeLinePosList() -> %s' % r
        return r


    def makeInnerLines(self):
        # inner grid lines
        group = Group()

        w, h = self.width, self.height

        if self.useLines == 1:
            if self.orientation == 'vertical':
                r = self.makeLinePosList(self.x, isX=1)
                for x in r:
                    line = Line(x, self.y, x, self.y + h)
                    line.strokeColor = self.strokeColor
                    line.strokeWidth = self.strokeWidth
                    group.add(line)
            elif self.orientation == 'horizontal':
                r = self.makeLinePosList(self.y, isX=0)
                for y in r:
                    line = Line(self.x, y, self.x + w, y)
                    line.strokeColor = self.strokeColor
                    line.strokeWidth = self.strokeWidth
                    group.add(line)

        return group


    def makeInnerTiles(self):
        # inner grid lines
        group = Group()

        w, h = self.width, self.height

        # inner grid stripes (solid rectangles)
        if self.useRects == 1:
            cols = self.stripeColors

            if self.orientation == 'vertical':
                r = self.makeLinePosList(self.x, isX=1)
            elif self.orientation == 'horizontal':
                r = self.makeLinePosList(self.y, isX=0)

            dist = makeDistancesList(r)

            i = 0
            for j in range(len(dist)):
                if self.orientation == 'vertical':
                    x = r[j]
                    stripe = Rect(x, self.y, dist[j], h)
                elif self.orientation == 'horizontal':
                    y = r[j]
                    stripe = Rect(self.x, y, w, dist[j])
                stripe.fillColor = cols[i % len(cols)]
                stripe.strokeColor = None
                group.add(stripe)
                i = i + 1

        return group


    def draw(self):
        # general widget bits
        group = Group()

        group.add(self.makeOuterRect())
        group.add(self.makeInnerTiles())
        group.add(self.makeInnerLines(),name='_gridLines')

        return group


class DoubleGrid(Widget):
    """This combines two ordinary Grid objects orthogonal to each other.
    """

    _attrMap = AttrMap(
        x = AttrMapValue(isNumber, desc="The grid's lower-left x position."),
        y = AttrMapValue(isNumber, desc="The grid's lower-left y position."),
        width = AttrMapValue(isNumber, desc="The grid's width."),
        height = AttrMapValue(isNumber, desc="The grid's height."),
        grid0 = AttrMapValue(None, desc="The first grid component."),
        grid1 = AttrMapValue(None, desc="The second grid component."),
        )

    def __init__(self):
        self.x = 0
        self.y = 0
        self.width = 100
        self.height = 100

        g0 = Grid()
        g0.x = self.x
        g0.y = self.y
        g0.width = self.width
        g0.height = self.height
        g0.orientation = 'vertical'
        g0.useLines = 1
        g0.useRects = 0
        g0.delta = 20
        g0.delta0 = 0
        g0.deltaSteps = []
        g0.fillColor = colors.white
        g0.stripeColors = [colors.red, colors.green, colors.blue]
        g0.strokeColor = colors.black
        g0.strokeWidth = 1

        g1 = Grid()
        g1.x = self.x
        g1.y = self.y
        g1.width = self.width
        g1.height = self.height
        g1.orientation = 'horizontal'
        g1.useLines = 1
        g1.useRects = 0
        g1.delta = 20
        g1.delta0 = 0
        g1.deltaSteps = []
        g1.fillColor = colors.white
        g1.stripeColors = [colors.red, colors.green, colors.blue]
        g1.strokeColor = colors.black
        g1.strokeWidth = 1

        self.grid0 = g0
        self.grid1 = g1


##    # This gives an AttributeError:
##    #   DoubleGrid instance has no attribute 'grid0'
##    def __setattr__(self, name, value):
##        if name in ('x', 'y', 'width', 'height'):
##            setattr(self.grid0, name, value)
##            setattr(self.grid1, name, value)


    def demo(self):
        D = Drawing(100, 100)
        g = DoubleGrid()
        D.add(g)
        return D


    def draw(self):
        group = Group()
        g0, g1 = self.grid0, self.grid1
        # Order groups to make sure both v and h lines
        # are visible (works only when there is only
        # one kind of stripes, v or h).
        G = g0.useRects == 1 and g1.useRects == 0 and (g0,g1) or (g1,g0)
        for g in G:
            group.add(g.makeOuterRect())
        for g in G:
            group.add(g.makeInnerTiles())
            group.add(g.makeInnerLines(),name='_gridLines')

        return group


class ShadedRect(Widget):
    """This makes a rectangle with shaded colors between two colors.

    Colors are interpolated linearly between 'fillColorStart'
    and 'fillColorEnd', both of which appear at the margins.
    If 'numShades' is set to one, though, only 'fillColorStart'
    is used.
    """

    _attrMap = AttrMap(
        x = AttrMapValue(isNumber, desc="The grid's lower-left x position."),
        y = AttrMapValue(isNumber, desc="The grid's lower-left y position."),
        width = AttrMapValue(isNumber, desc="The grid's width."),
        height = AttrMapValue(isNumber, desc="The grid's height."),
        orientation = AttrMapValue(OneOf(('vertical', 'horizontal')), desc='Determines if stripes are vertical or horizontal.'),
        numShades = AttrMapValue(isNumber, desc='The number of interpolating colors.'),
        fillColorStart = AttrMapValue(isColorOrNone, desc='Start value of the color shade.'),
        fillColorEnd = AttrMapValue(isColorOrNone, desc='End value of the color shade.'),
        strokeColor = AttrMapValue(isColorOrNone, desc='Color used for border line.'),
        strokeWidth = AttrMapValue(isNumber, desc='Width used for lines.'),
        cylinderMode = AttrMapValue(isBoolean, desc='True if shading reverses in middle.'),
        )

    def __init__(self,**kw):
        self.x = 0
        self.y = 0
        self.width = 100
        self.height = 100
        self.orientation = 'vertical'
        self.numShades = 20
        self.fillColorStart = colors.pink
        self.fillColorEnd = colors.black
        self.strokeColor = colors.black
        self.strokeWidth = 2
        self.cylinderMode = 0
        self.setProperties(kw)

    def demo(self):
        D = Drawing(100, 100)
        g = ShadedRect()
        D.add(g)

        return D

    def _flipRectCorners(self):
        "Flip rectangle's corners if width or height is negative."
        x, y, width, height, fillColorStart, fillColorEnd = self.x, self.y, self.width, self.height, self.fillColorStart, self.fillColorEnd
        if width < 0 and height > 0:
            x = x + width
            width = -width
            if self.orientation=='vertical': fillColorStart, fillColorEnd = fillColorEnd, fillColorStart
        elif height<0 and width>0:
            y = y + height
            height = -height
            if self.orientation=='horizontal': fillColorStart, fillColorEnd = fillColorEnd, fillColorStart
        elif height < 0 and height < 0:
            x = x + width
            width = -width
            y = y + height
            height = -height
        return x, y, width, height, fillColorStart, fillColorEnd

    def draw(self):
        # general widget bits
        group = Group()
        x, y, w, h, c0, c1 = self._flipRectCorners()
        numShades = self.numShades
        if self.cylinderMode:
            if not numShades%2: numShades = numShades+1
            halfNumShades = int((numShades-1)/2) + 1
        num = float(numShades) # must make it float!
        vertical = self.orientation == 'vertical'
        if vertical:
            if numShades == 1:
                V = [x]
            else:
                V = frange(x, x + w, w/num)
        else:
            if numShades == 1:
                V = [y]
            else:
                V = frange(y, y + h, h/num)

        for v in V:
            stripe = vertical and Rect(v, y, w/num, h) or Rect(x, v, w, h/num)
            if self.cylinderMode:
                if V.index(v)>=halfNumShades:
                    col = colors.linearlyInterpolatedColor(c1,c0,V[halfNumShades],V[-1], v)
                else:
                    col = colors.linearlyInterpolatedColor(c0,c1,V[0],V[halfNumShades], v)
            else:
                col = colors.linearlyInterpolatedColor(c0,c1,V[0],V[-1], v)
            stripe.fillColor = col
            stripe.strokeColor = col
            stripe.strokeWidth = 1
            group.add(stripe)
        if self.strokeColor and self.strokeWidth>=0:
            rect = Rect(x, y, w, h)
            rect.strokeColor = self.strokeColor
            rect.strokeWidth = self.strokeWidth
            rect.fillColor = None
            group.add(rect)
        return group


def colorRange(c0, c1, n):
    "Return a range of intermediate colors between c0 and c1"
    if n==1: return [c0]

    C = []
    if n>1:
        lim = n-1
        for i in range(n):
            C.append(colors.linearlyInterpolatedColor(c0,c1,0,lim, i))
    return C


def centroid(P):
    '''compute average point of a set of points'''
    cx = 0
    cy = 0
    for x,y in P:
        cx+=x
        cy+=y
    n = float(len(P))
    return cx/n, cy/n

def rotatedEnclosingRect(P, angle, rect):
    '''
    given P a sequence P of x,y coordinate pairs and an angle in degrees
    find the centroid of P and the axis at angle theta through it
    find the extreme points of P wrt axis parallel distance and axis
    orthogonal distance. Then compute the least rectangle that will still
    enclose P when rotated by angle.

    The class R
    '''
    from math import pi, cos, sin
    x0, y0 = centroid(P)
    theta = (angle/180.)*pi
    s,c=sin(theta),cos(theta)
    def parallelAxisDist(xy,s=s,c=c,x0=x0,y0=y0):
        x,y = xy
        return (s*(y-y0)+c*(x-x0))
    def orthogonalAxisDist(xy,s=s,c=c,x0=x0,y0=y0):
        x,y = xy
        return (c*(y-y0)+s*(x-x0))
    L = list(map(parallelAxisDist,P))
    L.sort()
    a0, a1 = L[0], L[-1]
    L = list(map(orthogonalAxisDist,P))
    L.sort()
    b0, b1 = L[0], L[-1]
    rect.x, rect.width = a0, a1-a0
    rect.y, rect.height = b0, b1-b0
    g = Group(transform=(c,s,-s,c,x0,y0))
    g.add(rect)
    return g

class ShadedPolygon(Widget,LineShape):
    _attrMap = AttrMap(BASE=LineShape,
        angle = AttrMapValue(isNumber,desc="Shading angle"),
        fillColorStart = AttrMapValue(isColorOrNone),
        fillColorEnd = AttrMapValue(isColorOrNone),
        numShades = AttrMapValue(isNumber, desc='The number of interpolating colors.'),
        cylinderMode = AttrMapValue(isBoolean, desc='True if shading reverses in middle.'),
        points = AttrMapValue(isListOfNumbers),
        )

    def __init__(self,**kw):
        self.angle = 90
        self.fillColorStart = colors.red
        self.fillColorEnd = colors.green
        self.cylinderMode = 0
        self.numShades = 50
        self.points = [-1,-1,2,2,3,-1]
        LineShape.__init__(self,kw)

    def draw(self):
        P = self.points
        P = list(map(lambda i, P=P:(P[i],P[i+1]),range(0,len(P),2)))
        path = definePath([('moveTo',)+P[0]]+[('lineTo',)+x for x in P[1:]]+['closePath'],
            fillColor=None, strokeColor=None)
        path.isClipPath = 1
        g = Group()
        g.add(path)
        angle = self.angle
        orientation = 'vertical'
        if angle==180:
            angle = 0
        elif angle in (90,270):
            orientation ='horizontal'
            angle = 0
        rect = ShadedRect(strokeWidth=0,strokeColor=None,orientation=orientation)
        for k in 'fillColorStart', 'fillColorEnd', 'numShades', 'cylinderMode':
            setattr(rect,k,getattr(self,k))
        g.add(rotatedEnclosingRect(P, angle, rect))
        g.add(EmptyClipPath)
        path = path.copy()
        path.isClipPath = 0
        path.strokeColor = self.strokeColor
        path.strokeWidth = self.strokeWidth
        g.add(path)
        return g

if __name__=='__main__': #noruntests
    angle=45
    D = Drawing(120,120)
    D.add(ShadedPolygon(points=(10,10,60,60,110,10),strokeColor=None,strokeWidth=1,angle=90,numShades=50,cylinderMode=0))
    D.save(formats=['gif'],fnRoot='shobj',outDir='/tmp')
