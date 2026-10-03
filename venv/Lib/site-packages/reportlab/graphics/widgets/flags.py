#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/graphics/widgets/flags.py
# Flag Widgets - a collection of flags as widgets
# author: John Precedo (johnp@reportlab.com)

__version__='3.3.0'
__doc__="""This file is a collection of flag graphics as widgets.

All flags are represented at the ratio of 1:2, even where the official ratio for the flag is something else
(such as 3:5 for the German national flag). The only exceptions are for where this would look _very_ wrong,
such as the Danish flag whose (ratio is 28:37), or the Swiss flag (which is square).

Unless otherwise stated, these flags are all the 'national flags' of the countries, rather than their
state flags, naval flags, ensigns or any other variants. (National flags are the flag flown by civilians
of a country and the ones usually used to represent a country abroad. State flags are the variants used by
the government and by diplomatic missions overseas).

To check on how close these are to the 'official' representations of flags, check the World Flag Database at
http://www.flags.ndirect.co.uk/

The flags this file contains are:

EU Members:
United Kingdom, Austria, Belgium, Denmark, Finland, France, Germany, Greece, Ireland, Italy, Luxembourg,
Holland (The Netherlands), Spain, Sweden

Others:
USA, Czech Republic, European Union, Switzerland, Turkey, Brazil

(Brazilian flag contributed by Publio da Costa Melo [publio@planetarium.com.br]).
"""

from reportlab.lib import colors
from reportlab.lib.validators import *
from reportlab.lib.attrmap import *
from reportlab.graphics.shapes import Line, Rect, Polygon, Drawing, Group, String, Circle, Wedge
from reportlab.graphics import renderPDF
from reportlab.graphics.widgets.signsandsymbols import _Symbol
import copy
from math import sin, cos, pi

validFlag=OneOf(None,
                'UK',
                'USA',
                'Afghanistan',
                'Austria',
                'Belgium',
                'China',
                'Cuba',
                'Denmark',
                'Finland',
                'France',
                'Germany',
                'Greece',
                'Ireland',
                'Italy',
                'Japan',
                'Luxembourg',
                'Holland',
                'Palestine',
                'Portugal',
                'Russia',
                'Spain',
                'Sweden',
                'Norway',
                'CzechRepublic',
                'Turkey',
                'Switzerland',
                'EU',
                'Brazil'
                )

_size = 100.

class Star(_Symbol):
    """This draws a 5-pointed star.

        possible attributes:
        'x', 'y', 'size', 'fillColor', 'strokeColor'

        """
    _attrMap = AttrMap(BASE=_Symbol,
            angle = AttrMapValue(isNumber, desc='angle in degrees'),
            )
    _size = 100.

    def __init__(self):
        _Symbol.__init__(self)
        self.size = 100
        self.fillColor = colors.yellow
        self.strokeColor = None
        self.angle = 0

    def demo(self):
        D = Drawing(200, 100)
        et = Star()
        et.x=50
        et.y=0
        D.add(et)
        labelFontSize = 10
        D.add(String(et.x+(et.size/2.0),(et.y-(1.2*labelFontSize)),
                            et.__class__.__name__, fillColor=colors.black, textAnchor='middle',
                            fontSize=labelFontSize))
        return D

    def draw(self):
        s = float(self.size)  #abbreviate as we will use this a lot
        g = Group()

        # new algorithm from markers.StarFive
        R = float(self.size)/2
        r = R*sin(18*(pi/180.0))/cos(36*(pi/180.0))
        P = []
        angle = 90
        for i in range(5):
            for radius in R, r:
                theta = angle*(pi/180.0)
                P.append(radius*cos(theta))
                P.append(radius*sin(theta))
                angle = angle + 36
        # star specific bits
        star = Polygon(P,
                    fillColor = self.fillColor,
                    strokeColor = self.strokeColor,
                    strokeWidth=s/50)
        g.rotate(self.angle)
        g.shift(self.x+self.dx,self.y+self.dy)
        g.add(star)

        return g

class Flag(_Symbol):
    """This is a generic flag class that all the flags in this file use as a basis.

        This class basically provides edges and a tidy-up routine to hide any bits of
        line that overlap the 'outside' of the flag

        possible attributes:
        'x', 'y', 'size', 'fillColor'
    """

    _attrMap = AttrMap(BASE=_Symbol,
            fillColor = AttrMapValue(isColor, desc='Background color'),
            border = AttrMapValue(isBoolean, 'Whether a background is drawn'),
            kind = AttrMapValue(validFlag, desc='Which flag'),
            )

    _cache = {}

    def __init__(self,**kw):
        _Symbol.__init__(self)
        self.kind = None
        self.size = 100
        self.fillColor = colors.white
        self.border=1
        self.setProperties(kw)

    def availableFlagNames(self):
        '''return a list of the things we can display'''
        return [x for x in self._attrMap['kind'].validate._enum if x is not None]

    def _Flag_None(self):
        s = _size  # abbreviate as we will use this a lot
        g = Group()
        g.add(Rect(0, 0, s*2, s, fillColor = colors.purple, strokeColor = colors.black, strokeWidth=0))
        return g

    def _borderDraw(self,f):
        s = self.size  # abbreviate as we will use this a lot
        g = Group()
        g.add(f)
        x, y, sW = self.x+self.dx, self.y+self.dy, self.strokeWidth/2.
        g.insert(0,Rect(-sW, -sW, width=getattr(self,'_width',2*s)+3*sW, height=getattr(self,'_height',s)+2*sW,
                fillColor = None, strokeColor = self.strokeColor, strokeWidth=sW*2))
        g.shift(x,y)
        g.scale(s/_size, s/_size)
        return g

    def draw(self):
        kind = self.kind or 'None'
        f = self._cache.get(kind)
        if not f:
            f = getattr(self,'_Flag_'+kind)()
            self._cache[kind] = f._explode()
        return self._borderDraw(f)

    def clone(self):
        return copy.copy(self)

    def demo(self):
        D = Drawing(200, 100)
        name = self.availableFlagNames()
        import time
        name = name[int(time.time()) % len(name)]
        fx = Flag()
        fx.kind = name
        fx.x = 0
        fx.y = 0
        D.add(fx)
        labelFontSize = 10
        D.add(String(fx.x+(fx.size/2.0),(fx.y-(1.2*labelFontSize)),
                            name, fillColor=colors.black, textAnchor='middle',
                            fontSize=labelFontSize))
        labelFontSize = int(fx.size/4.0)
        D.add(String(fx.x+(fx.size),(fx.y+((fx.size/2.0))),
                            "SAMPLE", fillColor=colors.gold, textAnchor='middle',
                            fontSize=labelFontSize, fontName="Helvetica-Bold"))
        return D

    def _Flag_UK(self):
        s = _size
        g = Group()
        w = s*2
        g.add(Rect(0, 0, w, s, fillColor = colors.navy, strokeColor = colors.black, strokeWidth=0))
        g.add(Polygon([0,0, s*.225,0, w,s*(1-.1125), w,s, w-s*.225,s, 0, s*.1125], fillColor = colors.mintcream, strokeColor=None, strokeWidth=0))
        g.add(Polygon([0,s*(1-.1125), 0, s, s*.225,s, w, s*.1125, w,0, w-s*.225,0], fillColor = colors.mintcream, strokeColor=None, strokeWidth=0))
        g.add(Polygon([0, s-(s/15.0), (s-((s/10.0)*4)), (s*0.65), (s-(s/10.0)*3), (s*0.65), 0, s], fillColor = colors.red, strokeColor = None, strokeWidth=0))
        g.add(Polygon([0, 0, (s-((s/10.0)*3)), (s*0.35), (s-((s/10.0)*2)), (s*0.35), (s/10.0), 0], fillColor = colors.red, strokeColor = None, strokeWidth=0))
        g.add(Polygon([w, s, (s+((s/10.0)*3)), (s*0.65), (s+((s/10.0)*2)), (s*0.65), w-(s/10.0), s], fillColor = colors.red, strokeColor = None, strokeWidth=0))
        g.add(Polygon([w, (s/15.0), (s+((s/10.0)*4)), (s*0.35), (s+((s/10.0)*3)), (s*0.35), w, 0], fillColor = colors.red, strokeColor = None, strokeWidth=0))
        g.add(Rect(((s*0.42)*2), 0, width=(0.16*s)*2, height=s, fillColor = colors.mintcream, strokeColor = None, strokeWidth=0))
        g.add(Rect(0, (s*0.35), width=w, height=s*0.3, fillColor = colors.mintcream, strokeColor = None, strokeWidth=0))
        g.add(Rect(((s*0.45)*2), 0, width=(0.1*s)*2, height=s, fillColor = colors.red, strokeColor = None, strokeWidth=0))
        g.add(Rect(0, (s*0.4), width=w, height=s*0.2, fillColor = colors.red, strokeColor = None, strokeWidth=0))
        return g

    def _Flag_USA(self):
        s = _size  # abbreviate as we will use this a lot
        g = Group()

        box = Rect(0, 0, s*2, s, fillColor = colors.mintcream, strokeColor = colors.black, strokeWidth=0)
        g.add(box)

        for stripecounter in range (13,0, -1):
            stripeheight = s/13.0
            if not (stripecounter%2 == 0):
                stripecolor = colors.red
            else:
                stripecolor = colors.mintcream
            redorwhiteline = Rect(0, (s-(stripeheight*stripecounter)), width=s*2, height=stripeheight,
                fillColor = stripecolor, strokeColor = None, strokeWidth=20)
            g.add(redorwhiteline)

        bluebox = Rect(0, (s-(stripeheight*7)), width=0.8*s, height=stripeheight*7,
            fillColor = colors.darkblue, strokeColor = None, strokeWidth=0)
        g.add(bluebox)

        lss = s*0.045
        lss2 = lss/2.0
        s9 = s/9.0
        s7 = s/7.0
        for starxcounter in range(5):
            for starycounter in range(4):
                ls = Star()
                ls.size = lss
                ls.x = 0-s/22.0+lss/2.0+s7+starxcounter*s7
                ls.fillColor = colors.mintcream
                ls.y = s-(starycounter+1)*s9+lss2
                g.add(ls)

        for starxcounter in range(6):
            for starycounter in range(5):
                ls = Star()
                ls.size = lss
                ls.x = 0-(s/22.0)+lss/2.0+s/14.0+starxcounter*s7
                ls.fillColor = colors.mintcream
                ls.y = s-(starycounter+1)*s9+(s/18.0)+lss2
                g.add(ls)
        return g

    def _Flag_Afghanistan(self):
        s = _size
        g = Group()

        box = Rect(0, 0, s*2, s,
            fillColor = colors.mintcream, strokeColor = colors.black, strokeWidth=0)
        g.add(box)

        greenbox = Rect(0, ((s/3.0)*2.0), width=s*2.0, height=s/3.0,
                fillColor = colors.limegreen, strokeColor = None, strokeWidth=0)
        g.add(greenbox)

        blackbox = Rect(0, 0, width=s*2.0, height=s/3.0,
                fillColor = colors.black, strokeColor = None, strokeWidth=0)
        g.add(blackbox)
        return g

    def _Flag_Austria(self):
        s = _size  # abbreviate as we will use this a lot
        g = Group()

        box = Rect(0, 0, s*2, s, fillColor = colors.mintcream,
            strokeColor = colors.black, strokeWidth=0)
        g.add(box)


        redbox1 = Rect(0, 0, width=s*2.0, height=s/3.0,
            fillColor = colors.red, strokeColor = None, strokeWidth=0)
        g.add(redbox1)

        redbox2 = Rect(0, ((s/3.0)*2.0), width=s*2.0, height=s/3.0,
            fillColor = colors.red, strokeColor = None, strokeWidth=0)
        g.add(redbox2)
        return g

    def _Flag_Belgium(self):
        s = _size
        g = Group()

        box = Rect(0, 0, s*2, s,
            fillColor = colors.black, strokeColor = colors.black, strokeWidth=0)
        g.add(box)


        box1 = Rect(0, 0, width=(s/3.0)*2.0, height=s,
            fillColor = colors.black, strokeColor = None, strokeWidth=0)
        g.add(box1)

        box2 = Rect(((s/3.0)*2.0), 0, width=(s/3.0)*2.0, height=s,
            fillColor = colors.gold, strokeColor = None, strokeWidth=0)
        g.add(box2)

        box3 = Rect(((s/3.0)*4.0), 0, width=(s/3.0)*2.0, height=s,
            fillColor = colors.red, strokeColor = None, strokeWidth=0)
        g.add(box3)
        return g

    def _Flag_China(self):
        s = _size
        g = Group()
        self._width = w = s*1.5
        g.add(Rect(0, 0, w, s, fillColor=colors.red, strokeColor=None, strokeWidth=0))

        def addStar(x,y,size,angle,g=g,w=s/20.0,x0=0,y0=s/2.0):
            s = Star()
            s.fillColor=colors.yellow
            s.angle = angle
            s.size = size*w*2
            s.x = x*w+x0
            s.y = y*w+y0
            g.add(s)

        addStar(5,5,3, 0)
        addStar(10,1,1,36.86989765)
        addStar(12,3,1,8.213210702)
        addStar(12,6,1,16.60154960)
        addStar(10,8,1,53.13010235)
        return g

    def _Flag_Cuba(self):
        s = _size
        g = Group()

        for i in range(5):
            stripe = Rect(0, i*s/5.0, width=s*2, height=s/5.0,
                fillColor = [colors.darkblue, colors.mintcream][i%2],
                strokeColor = None,
                strokeWidth=0)
            g.add(stripe)

        redwedge = Polygon(points = [ 0, 0, 4*s/5.0, (s/2.0), 0, s],
                    fillColor = colors.red, strokeColor = None, strokeWidth=0)
        g.add(redwedge)

        star = Star()
        star.x = 2.5*s/10.0
        star.y = s/2.0
        star.size = 3*s/10.0
        star.fillColor = colors.white
        g.add(star)

        box = Rect(0, 0, s*2, s,
            fillColor = None,
            strokeColor = colors.black,
            strokeWidth=0)
        g.add(box)

        return g

    def _Flag_Denmark(self):
        s = _size
        g = Group()
        self._width = w = s*1.4

        box = Rect(0, 0, w, s,
            fillColor = colors.red, strokeColor = colors.black, strokeWidth=0)
        g.add(box)

        whitebox1 = Rect(((s/5.0)*2), 0, width=s/6.0, height=s,
            fillColor = colors.mintcream, strokeColor = None, strokeWidth=0)
        g.add(whitebox1)

        whitebox2 = Rect(0, ((s/2.0)-(s/12.0)), width=w, height=s/6.0,
            fillColor = colors.mintcream, strokeColor = None, strokeWidth=0)
        g.add(whitebox2)
        return g

    def _Flag_Finland(self):
        s = _size
        g = Group()

        # crossbox specific bits
        box = Rect(0, 0, s*2, s,
            fillColor = colors.ghostwhite, strokeColor = colors.black, strokeWidth=0)
        g.add(box)

        blueline1 = Rect((s*0.6), 0, width=0.3*s, height=s,
            fillColor = colors.darkblue, strokeColor = None, strokeWidth=0)
        g.add(blueline1)

        blueline2 = Rect(0, (s*0.4), width=s*2, height=s*0.3,
            fillColor = colors.darkblue, strokeColor = None, strokeWidth=0)
        g.add(blueline2)
        return g

    def _Flag_France(self):
        s = _size
        g = Group()

        box = Rect(0, 0, s*2, s, fillColor = colors.navy, strokeColor = colors.black, strokeWidth=0)
        g.add(box)

        bluebox = Rect(0, 0, width=((s/3.0)*2.0), height=s,
            fillColor = colors.blue, strokeColor = None, strokeWidth=0)
        g.add(bluebox)

        whitebox = Rect(((s/3.0)*2.0), 0, width=((s/3.0)*2.0), height=s,
            fillColor = colors.mintcream, strokeColor = None, strokeWidth=0)
        g.add(whitebox)

        redbox = Rect(((s/3.0)*4.0), 0, width=((s/3.0)*2.0), height=s,
            fillColor = colors.red,
            strokeColor = None,
            strokeWidth=0)
        g.add(redbox)
        return g

    def _Flag_Germany(self):
        s = _size
        g = Group()

        box = Rect(0, 0, s*2, s,
                fillColor = colors.gold, strokeColor = colors.black, strokeWidth=0)
        g.add(box)

        blackbox1 = Rect(0, ((s/3.0)*2.0), width=s*2.0, height=s/3.0,
            fillColor = colors.black, strokeColor = None, strokeWidth=0)
        g.add(blackbox1)

        redbox1 = Rect(0, (s/3.0), width=s*2.0, height=s/3.0,
            fillColor = colors.orangered, strokeColor = None, strokeWidth=0)
        g.add(redbox1)
        return g

    def _Flag_Greece(self):
        s = _size
        g = Group()

        box = Rect(0, 0, s*2, s, fillColor = colors.gold,
                        strokeColor = colors.black, strokeWidth=0)
        g.add(box)

        for stripecounter in range (9,0, -1):
            stripeheight = s/9.0
            if not (stripecounter%2 == 0):
                stripecolor = colors.deepskyblue
            else:
                stripecolor = colors.mintcream

            blueorwhiteline = Rect(0, (s-(stripeheight*stripecounter)), width=s*2, height=stripeheight,
                fillColor = stripecolor, strokeColor = None, strokeWidth=20)
            g.add(blueorwhiteline)

        bluebox1 = Rect(0, ((s)-stripeheight*5), width=(stripeheight*5), height=stripeheight*5,
            fillColor = colors.deepskyblue, strokeColor = None, strokeWidth=0)
        g.add(bluebox1)

        whiteline1 = Rect(0, ((s)-stripeheight*3), width=stripeheight*5, height=stripeheight,
            fillColor = colors.mintcream, strokeColor = None, strokeWidth=0)
        g.add(whiteline1)

        whiteline2 = Rect((stripeheight*2), ((s)-stripeheight*5), width=stripeheight, height=stripeheight*5,
            fillColor = colors.mintcream, strokeColor = None, strokeWidth=0)
        g.add(whiteline2)

        return g

    def _Flag_Ireland(self):
        s = _size
        g = Group()

        box = Rect(0, 0, s*2, s,
            fillColor = colors.forestgreen, strokeColor = colors.black, strokeWidth=0)
        g.add(box)

        whitebox = Rect(((s*2.0)/3.0), 0, width=(2.0*(s*2.0)/3.0), height=s,
                fillColor = colors.mintcream, strokeColor = None, strokeWidth=0)
        g.add(whitebox)

        orangebox = Rect(((2.0*(s*2.0)/3.0)), 0, width=(s*2.0)/3.0, height=s,
            fillColor = colors.darkorange, strokeColor = None, strokeWidth=0)
        g.add(orangebox)
        return g

    def _Flag_Italy(self):
        s = _size
        g = Group()
        g.add(Rect(0,0,s*2,s,fillColor=colors.forestgreen,strokeColor=None, strokeWidth=0))
        g.add(Rect((2*s)/3.0, 0, width=(s*4)/3.0, height=s, fillColor = colors.mintcream, strokeColor = None, strokeWidth=0))
        g.add(Rect((4*s)/3.0, 0, width=(s*2)/3.0, height=s, fillColor = colors.red, strokeColor = None, strokeWidth=0))
        return g

    def _Flag_Japan(self):
        s = _size
        g = Group()
        w = self._width = s*1.5
        g.add(Rect(0,0,w,s,fillColor=colors.mintcream,strokeColor=None, strokeWidth=0))
        g.add(Circle(cx=w/2.0,cy=s/2.0,r=0.3*w,fillColor=colors.red,strokeColor=None, strokeWidth=0))
        return g

    def _Flag_Luxembourg(self):
        s = _size
        g = Group()

        box = Rect(0, 0, s*2, s,
            fillColor = colors.mintcream, strokeColor = colors.black, strokeWidth=0)
        g.add(box)

        redbox = Rect(0, ((s/3.0)*2.0), width=s*2.0, height=s/3.0,
                fillColor = colors.red, strokeColor = None, strokeWidth=0)
        g.add(redbox)

        bluebox = Rect(0, 0, width=s*2.0, height=s/3.0,
                fillColor = colors.dodgerblue, strokeColor = None, strokeWidth=0)
        g.add(bluebox)
        return g

    def _Flag_Holland(self):
        s = _size
        g = Group()

        box = Rect(0, 0, s*2, s,
            fillColor = colors.mintcream, strokeColor = colors.black, strokeWidth=0)
        g.add(box)

        redbox = Rect(0, ((s/3.0)*2.0), width=s*2.0, height=s/3.0,
                fillColor = colors.red, strokeColor = None, strokeWidth=0)
        g.add(redbox)

        bluebox = Rect(0, 0, width=s*2.0, height=s/3.0,
                fillColor = colors.darkblue, strokeColor = None, strokeWidth=0)
        g.add(bluebox)
        return g

    def _Flag_Portugal(self):
        return Group()

    def _Flag_Russia(self):
        s = _size
        g = Group()
        w = self._width = s*1.5
        t = s/3.0
        g.add(Rect(0, 0, width=w, height=t, fillColor = colors.red, strokeColor = None, strokeWidth=0))
        g.add(Rect(0, t, width=w, height=t, fillColor = colors.blue, strokeColor = None, strokeWidth=0))
        g.add(Rect(0, 2*t, width=w, height=t, fillColor = colors.mintcream, strokeColor = None, strokeWidth=0))
        return g

    def _Flag_Spain(self):
        s = _size
        g = Group()
        w = self._width = s*1.5
        g.add(Rect(0, 0, width=w, height=s, fillColor = colors.red, strokeColor = None, strokeWidth=0))
        g.add(Rect(0, (s/4.0), width=w, height=s/2.0, fillColor = colors.yellow, strokeColor = None, strokeWidth=0))
        return g

    def _Flag_Sweden(self):
        s = _size
        g = Group()
        self._width = s*1.4
        box = Rect(0, 0, self._width, s,
            fillColor = colors.dodgerblue, strokeColor = colors.black, strokeWidth=0)
        g.add(box)

        box1 = Rect(((s/5.0)*2), 0, width=s/6.0, height=s,
                fillColor = colors.gold, strokeColor = None, strokeWidth=0)
        g.add(box1)

        box2 = Rect(0, ((s/2.0)-(s/12.0)), width=self._width, height=s/6.0,
            fillColor = colors.gold,
            strokeColor = None,
            strokeWidth=0)
        g.add(box2)
        return g

    def _Flag_Norway(self):
        s = _size
        g = Group()
        self._width = s*1.4

        box = Rect(0, 0, self._width, s,
                fillColor = colors.red, strokeColor = colors.black, strokeWidth=0)
        g.add(box)

        box = Rect(0, 0, self._width, s,
                fillColor = colors.red, strokeColor = colors.black, strokeWidth=0)
        g.add(box)

        whiteline1 = Rect(((s*0.2)*2), 0, width=s*0.2, height=s,
                fillColor = colors.ghostwhite, strokeColor = None, strokeWidth=0)
        g.add(whiteline1)

        whiteline2 = Rect(0, (s*0.4), width=self._width, height=s*0.2,
                fillColor = colors.ghostwhite, strokeColor = None, strokeWidth=0)
        g.add(whiteline2)

        blueline1 = Rect(((s*0.225)*2), 0, width=0.1*s, height=s,
                fillColor = colors.darkblue, strokeColor = None, strokeWidth=0)
        g.add(blueline1)

        blueline2 = Rect(0, (s*0.45), width=self._width, height=s*0.1,
                fillColor = colors.darkblue, strokeColor = None, strokeWidth=0)
        g.add(blueline2)
        return g

    def _Flag_CzechRepublic(self):
        s = _size
        g = Group()
        box = Rect(0, 0, s*2, s,
            fillColor = colors.mintcream,
                        strokeColor = colors.black,
            strokeWidth=0)
        g.add(box)

        redbox = Rect(0, 0, width=s*2, height=s/2.0,
            fillColor = colors.red,
            strokeColor = None,
            strokeWidth=0)
        g.add(redbox)

        bluewedge = Polygon(points = [ 0, 0, s, (s/2.0), 0, s],
                    fillColor = colors.darkblue, strokeColor = None, strokeWidth=0)
        g.add(bluewedge)
        return g

    def _Flag_Palestine(self):
        s = _size
        g = Group()
        box = Rect(0, s/3.0, s*2, s/3.0,
            fillColor = colors.mintcream,
                        strokeColor = None,
            strokeWidth=0)
        g.add(box)

        greenbox = Rect(0, 0, width=s*2, height=s/3.0,
            fillColor = colors.limegreen,
            strokeColor = None,
            strokeWidth=0)
        g.add(greenbox)

        blackbox = Rect(0, 2*s/3.0, width=s*2, height=s/3.0,
            fillColor = colors.black,
            strokeColor = None,
            strokeWidth=0)
        g.add(blackbox)

        redwedge = Polygon(points = [ 0, 0, 2*s/3.0, (s/2.0), 0, s],
                    fillColor = colors.red, strokeColor = None, strokeWidth=0)
        g.add(redwedge)
        return g

    def _Flag_Turkey(self):
        s = _size
        g = Group()

        box = Rect(0, 0, s*2, s,
            fillColor = colors.red,
                        strokeColor = colors.black,
            strokeWidth=0)
        g.add(box)

        whitecircle = Circle(cx=((s*0.35)*2), cy=s/2.0, r=s*0.3,
            fillColor = colors.mintcream,
            strokeColor = None,
            strokeWidth=0)
        g.add(whitecircle)

        redcircle = Circle(cx=((s*0.39)*2), cy=s/2.0, r=s*0.24,
            fillColor = colors.red,
            strokeColor = None,
            strokeWidth=0)
        g.add(redcircle)

        ws = Star()
        ws.angle = 15
        ws.size = s/5.0
        ws.x = (s*0.5)*2+ws.size/2.0
        ws.y = (s*0.5)
        ws.fillColor = colors.mintcream
        ws.strokeColor = None
        g.add(ws)
        return g

    def _Flag_Switzerland(self):
        s = _size
        g = Group()
        self._width = s

        g.add(Rect(0, 0, s, s, fillColor = colors.red, strokeColor = colors.black, strokeWidth=0))
        g.add(Line((s/2.0), (s/5.5), (s/2), (s-(s/5.5)),
            fillColor = colors.mintcream, strokeColor = colors.mintcream, strokeWidth=(s/5.0)))
        g.add(Line((s/5.5), (s/2.0), (s-(s/5.5)), (s/2.0),
            fillColor = colors.mintcream, strokeColor = colors.mintcream, strokeWidth=s/5.0))
        return g

    def _Flag_EU(self):
        s = _size
        g = Group()
        w = self._width = 1.5*s

        g.add(Rect(0, 0, w, s, fillColor = colors.darkblue, strokeColor = None, strokeWidth=0))
        centerx=w/2.0
        centery=s/2.0
        radius=s/3.0
        yradius = radius
        xradius = radius
        nStars = 12
        delta = 2*pi/nStars
        for i in range(nStars):
            rad = i*delta
            gs = Star()
            gs.x=cos(rad)*radius+centerx
            gs.y=sin(rad)*radius+centery
            gs.size=s/10.0
            gs.fillColor=colors.gold
            g.add(gs)
        return g

    def _Flag_Brazil(self):
        s = _size  # abbreviate as we will use this a lot
        g = Group()

        m = s/14.0
        self._width = w = (m * 20)

        def addStar(x,y,size, g=g, w=w, s=s, m=m):
            st = Star()
            st.fillColor=colors.mintcream
            st.size = size*m
            st.x = (w/2.0) + (x * (0.35 * m))
            st.y = (s/2.0) + (y * (0.35 * m))
            g.add(st)

        g.add(Rect(0, 0, w, s, fillColor = colors.green, strokeColor = None, strokeWidth=0))
        g.add(Polygon(points = [ 1.7*m, (s/2.0), (w/2.0), s-(1.7*m), w-(1.7*m),(s/2.0),(w/2.0), 1.7*m],
                      fillColor = colors.yellow, strokeColor = None, strokeWidth=0))
        g.add(Circle(cx=w/2.0, cy=s/2.0, r=3.5*m,
                     fillColor=colors.blue,strokeColor=None, strokeWidth=0))
        g.add(Wedge((w/2.0)-(2*m), 0, 8.5*m, 50, 98.1, 8.5*m,
                    fillColor=colors.mintcream,strokeColor=None, strokeWidth=0))
        g.add(Wedge((w/2.0), (s/2.0), 3.501*m, 156, 352, 3.501*m,
                    fillColor=colors.mintcream,strokeColor=None, strokeWidth=0))
        g.add(Wedge((w/2.0)-(2*m), 0, 8*m, 48.1, 100, 8*m,
                    fillColor=colors.blue,strokeColor=None, strokeWidth=0))
        g.add(Rect(0, 0, w, (s/4.0) + 1.7*m,
                   fillColor = colors.green, strokeColor = None, strokeWidth=0))
        g.add(Polygon(points = [ 1.7*m,(s/2.0), (w/2.0),s/2.0 - 2*m,    w-(1.7*m),(s/2.0) , (w/2.0),1.7*m],
                      fillColor = colors.yellow, strokeColor = None, strokeWidth=0))
        g.add(Wedge(w/2.0, s/2.0, 3.502*m, 166, 342.1, 3.502*m,
                    fillColor=colors.blue,strokeColor=None, strokeWidth=0))

        addStar(3.2,3.5,0.3)
        addStar(-8.5,1.5,0.3)
        addStar(-7.5,-3,0.3)
        addStar(-4,-5.5,0.3)
        addStar(0,-4.5,0.3)
        addStar(7,-3.5,0.3)
        addStar(-3.5,-0.5,0.25)
        addStar(0,-1.5,0.25)
        addStar(1,-2.5,0.25)
        addStar(3,-7,0.25)
        addStar(5,-6.5,0.25)
        addStar(6.5,-5,0.25)
        addStar(7,-4.5,0.25)
        addStar(-5.5,-3.2,0.25)
        addStar(-6,-4.2,0.25)
        addStar(-1,-2.75,0.2)
        addStar(2,-5.5,0.2)
        addStar(4,-5.5,0.2)
        addStar(5,-7.5,0.2)
        addStar(5,-5.5,0.2)
        addStar(6,-5.5,0.2)
        addStar(-8.8,-3.2,0.2)
        addStar(2.5,0.5,0.2)
        addStar(-0.2,-3.2,0.14)
        addStar(-7.2,-2,0.14)
        addStar(0,-8,0.1)

        sTmp = "ORDEM E PROGRESSO"
        nTmp = len(sTmp)
        delta = 0.850848010347/nTmp
        radius = 7.9 *m
        centerx = (w/2.0)-(2*m)
        centery = 0
        for i in range(nTmp):
            rad = 2*pi - i*delta -4.60766922527
            x=cos(rad)*radius+centerx
            y=sin(rad)*radius+centery
            if i == 6:
                z = 0.35*m
            else:
                z= 0.45*m
            g2 = Group(String(x, y, sTmp[i], fontName='Helvetica-Bold',
                fontSize = z,strokeColor=None,fillColor=colors.green))
            g2.rotate(rad)
            g.add(g2)
        return g

def makeFlag(name):
    flag = Flag()
    flag.kind = name
    return flag

def test():
    """This function produces three pdf files with examples of all the signs and symbols from this file.
    """
# page 1

    labelFontSize = 10

    X = (20,245)

    flags = [
            'UK',
            'USA',
            'Afghanistan',
            'Austria',
            'Belgium',
            'Denmark',
            'Cuba',
            'Finland',
            'France',
            'Germany',
            'Greece',
            'Ireland',
            'Italy',
            'Luxembourg',
            'Holland',
            'Palestine',
            'Portugal',
            'Spain',
            'Sweden',
            'Norway',
            'CzechRepublic',
            'Turkey',
            'Switzerland',
            'EU',
            'Brazil',
            ]
    y = Y0 = 530
    f = 0
    D = None
    for name in flags:
        if not D: D = Drawing(450,650)
        flag = makeFlag(name)
        i = flags.index(name)
        flag.x = X[i%2]
        flag.y = y
        D.add(flag)
        D.add(String(flag.x+(flag.size/2.0),(flag.y-(1.2*labelFontSize)),
                name, fillColor=colors.black, textAnchor='middle', fontSize=labelFontSize))
        if i%2: y = y - 125
        if (i%2 and y<0) or name==flags[-1]:
            renderPDF.drawToFile(D, 'flags%02d.pdf'%f, 'flags.py - Page #%d'%(f+1))
            y = Y0
            f = f+1
            D = None

if __name__=='__main__':
    test()
