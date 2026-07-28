#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/lib/colors.py
__version__='3.3.0'
__doc__='''Defines standard colour-handling classes and colour names.

We define standard classes to hold colours in two models:  RGB and CMYK.
rhese can be constructed from several popular formats.  We also include

- pre-built colour objects for the HTML standard colours

- pre-built colours used in ReportLab's branding

- various conversion and construction functions

These tests are here because doctest cannot find them otherwise.
>>> toColor('rgb(128,0,0)')==toColor('rgb(50%,0%,0%)')
True
>>> toColor('rgb(50%,0%,0%)')!=Color(0.5,0,0,1)
True
>>> toColor('hsl(0,100%,50%)')==toColor('rgb(255,0,0)')
True
>>> toColor('hsl(-120,100%,50%)')==toColor('rgb(0,0,255)')
True
>>> toColor('hsl(120,100%,50%)')==toColor('rgb(0,255,0)')
True
>>> toColor('rgba( 255,0,0,0.5)')==Color(1,0,0,0.5)
True
>>> toColor('cmyk(1,0,0,0 )')==CMYKColor(1,0,0,0)
True
>>> toColor('pcmyk( 100 , 0 , 0 , 0 )')==PCMYKColor(100,0,0,0)
True
>>> toColor('cmyka(1,0,0,0,0.5)')==CMYKColor(1,0,0,0,alpha=0.5)
True
>>> toColor('pcmyka(100,0,0,0,0.5)')==PCMYKColor(100,0,0,0,alpha=0.5)
True
>>> toColor('pcmyka(100,0,0,0)')
Traceback (most recent call last):
    ....
ValueError: css color 'pcmyka(100,0,0,0)' has wrong number of components
'''
import math, re, functools
from reportlab.lib.rl_accel import fp_str
from reportlab.lib.utils import asNative, isStr, rl_safe_eval, rl_extended_literal_eval
from reportlab import rl_config
from ast import literal_eval

class Color:
    """This class is used to represent color.  Components red, green, blue
    are in the range 0 (dark) to 1 (full intensity)."""

    def __init__(self, red=0, green=0, blue=0, alpha=1):
        "Initialize with red, green, blue in range [0-1]."
        self.red = red
        self.green = green
        self.blue = blue
        self.alpha = alpha

    def __repr__(self):
        return "Color(%s)" % fp_str(*(self.red, self.green, self.blue,self.alpha)).replace(' ',',')

    @property
    def __key__(self):
        '''simple comparison by component; cmyk != color ever
        >>> from reportlab import cmp
        >>> cmp(Color(0,0,0),None)
        -1
        >>> cmp(Color(0,0,0),black)
        0
        >>> cmp(Color(0,0,0),CMYKColor(0,0,0,1)),Color(0,0,0).rgba()==CMYKColor(0,0,0,1).rgba()
        (1, True)
        '''
        return self.red, self.green, self.blue, self.alpha

    def __hash__(self):
        return hash(self.__key__)

    def __comparable__(self,other):
        return not isinstance(other,CMYKColor) and isinstance(other,Color)

    def __lt__(self,other):
        if not self.__comparable__(other): return True
        try:
            return self.__key__ < other.__key__
        except:
            pass
        return True

    def __eq__(self,other):
        if not self.__comparable__(other): return False
        try:
            return self.__key__ == other.__key__
        except:
            return False

    def rgb(self):
        "Returns a three-tuple of components"
        return (self.red, self.green, self.blue)

    def rgba(self):
        "Returns a four-tuple of components"
        return (self.red, self.green, self.blue, self.alpha)

    def bitmap_rgb(self):
        return tuple([int(x*255)&255 for x in self.rgb()])

    def bitmap_rgba(self):
        return tuple([int(x*255)&255 for x in self.rgba()])

    def hexval(self):
        return '0x%02x%02x%02x' % self.bitmap_rgb()

    def hexvala(self):
        return '0x%02x%02x%02x%02x' % self.bitmap_rgba()

    def int_rgb(self):
        v = self.bitmap_rgb()
        return v[0]<<16|v[1]<<8|v[2]

    def int_rgba(self):
        v = self.bitmap_rgba()
        return int((v[0]<<24|v[1]<<16|v[2]<<8|v[3])&0xffffff)

    _cKwds='red green blue alpha'.split()
    def cKwds(self):
        for k in self._cKwds:
            yield k,getattr(self,k)
    cKwds=property(cKwds)

    def clone(self,**kwds):
        '''copy then change values in kwds'''
        D = dict([kv for kv in self.cKwds])
        D.update(kwds)
        return self.__class__(**D)

    def _lookupName(self,D={}):
        if not D:
            for n,v in getAllNamedColors().items():
                if not isinstance(v,CMYKColor):
                    t = v.red,v.green,v.blue
                    if t in D:
                        n = n+'/'+D[t]
                    D[t] = n
        t = self.red,self.green,self.blue
        return t in D and D[t] or None

    @property
    def normalizedAlpha(self):
        return self.alpha
Color = functools.total_ordering(Color)

def opaqueColor(c):
    '''utility to check we have a color that's not fully transparent'''
    return isinstance(c,Color) and c.alpha>0

class CMYKColor(Color):
    """This represents colors using the CMYK (cyan, magenta, yellow, black)
    model commonly used in professional printing.  This is implemented
    as a derived class so that renderers which only know about RGB "see it"
    as an RGB color through its 'red','green' and 'blue' attributes, according
    to an approximate function.

    The RGB approximation is worked out when the object in constructed, so
    the color attributes should not be changed afterwards.

    Extra attributes may be attached to the class to support specific ink models,
    and renderers may look for these."""

    _scale = 1.0
    def __init__(self, cyan=0, magenta=0, yellow=0, black=0,
                spotName=None, density=1, knockout=None, alpha=1):
        """
        Initialize with four colors in range [0-1]. the optional
        spotName, density & knockout may be of use to specific renderers.
        spotName is intended for use as an identifier to the renderer not client programs.
        density is used to modify the overall amount of ink.
        knockout is a renderer dependent option that determines whether the applied colour
        knocksout (removes) existing colour; None means use the global default.
        """
        self.cyan = cyan
        self.magenta = magenta
        self.yellow = yellow
        self.black = black
        self.spotName = spotName
        self.density = max(min(density,1),0)    # force into right range
        self.knockout = knockout
        self.alpha = alpha

        # now work out the RGB approximation. override
        self.red, self.green, self.blue = cmyk2rgb( (cyan, magenta, yellow, black) )

        if density<1:
            #density adjustment of rgb approximants, effectively mix with white
            r, g, b = self.red, self.green, self.blue
            r = density*(r-1)+1
            g = density*(g-1)+1
            b = density*(b-1)+1
            self.red, self.green, self.blue = (r,g,b)

    def __repr__(self):
        return "%s(%s%s%s%s%s)" % (self.__class__.__name__,
            fp_str(self.cyan, self.magenta, self.yellow, self.black).replace(' ',','),
            (self.spotName and (',spotName='+repr(self.spotName)) or ''),
            (self.density!=1 and (',density='+fp_str(self.density)) or ''),
            (self.knockout is not None and (',knockout=%d' % self.knockout) or ''),
            (self.alpha is not None and (',alpha=%s' % self.alpha) or ''),
            )

    def fader(self, n, reverse=False):
        '''return n colors based on density fade
        *NB* note this dosen't reach density zero'''
        scale = self._scale
        dd = scale/float(n)
        L = [self.clone(density=scale - i*dd) for i in range(n)]
        if reverse: L.reverse()
        return L

    @property
    def __key__(self):
        """obvious way to compare colours
        Comparing across the two color models is of limited use.
        >>> cmp(CMYKColor(0,0,0,1),None)
        -1
        >>> cmp(CMYKColor(0,0,0,1),_CMYK_black)
        0
        >>> cmp(PCMYKColor(0,0,0,100),_CMYK_black)
        0
        >>> cmp(CMYKColor(0,0,0,1),Color(0,0,1)),Color(0,0,0).rgba()==CMYKColor(0,0,0,1).rgba()
        (-1, True)
        """
        return self.cyan, self.magenta, self.yellow, self.black, self.density, self.spotName, self.alpha

    def __comparable__(self,other):
        return isinstance(other,CMYKColor)

    def cmyk(self):
        "Returns a tuple of four color components - syntactic sugar"
        return (self.cyan, self.magenta, self.yellow, self.black)

    def cmyka(self):
        "Returns a tuple of five color components - syntactic sugar"
        return (self.cyan, self.magenta, self.yellow, self.black, self.alpha)

    def _density_str(self):
        return fp_str(self.density)
    _cKwds='cyan magenta yellow black density alpha spotName knockout'.split()

    def _lookupName(self,D={}):
        if not D:
            for n,v in getAllNamedColors().items():
                if isinstance(v,CMYKColor):
                    t = v.cyan,v.magenta,v.yellow,v.black
                    if t in D:
                        n = n+'/'+D[t]
                    D[t] = n
        t = self.cyan,self.magenta,self.yellow,self.black
        return t in D and D[t] or None

    @property
    def normalizedAlpha(self):
        return self.alpha*self._scale

class PCMYKColor(CMYKColor):
    '''100 based CMYKColor with density and a spotName; just like Rimas uses'''
    _scale = 100.
    def __init__(self,cyan,magenta,yellow,black,density=100,spotName=None,knockout=None,alpha=100):
        CMYKColor.__init__(self,cyan/100.,magenta/100.,yellow/100.,black/100.,spotName,density/100.,knockout=knockout,alpha=alpha/100.)

    def __repr__(self):
        return "%s(%s%s%s%s%s)" % (self.__class__.__name__,
            fp_str(self.cyan*100, self.magenta*100, self.yellow*100, self.black*100).replace(' ',','),
            (self.spotName and (',spotName='+repr(self.spotName)) or ''),
            (self.density!=1 and (',density='+fp_str(self.density*100)) or ''),
            (self.knockout is not None and (',knockout=%d' % self.knockout) or ''),
            (self.alpha is not None and (',alpha=%s' % (fp_str(self.alpha*100))) or ''),
            )

    def cKwds(self):
        K=self._cKwds
        S=K[:6]
        for k in self._cKwds:
            v=getattr(self,k)
            if k in S: v*=100
            yield k,v
    cKwds=property(cKwds)

class CMYKColorSep(CMYKColor):
    '''special case color for making separating pdfs'''
    _scale = 1.
    def __init__(self, cyan=0, magenta=0, yellow=0, black=0,
                spotName=None, density=1,alpha=1):
        CMYKColor.__init__(self,cyan,magenta,yellow,black,spotName,density,knockout=None,alpha=alpha)
    _cKwds='cyan magenta yellow black density alpha spotName'.split()

class PCMYKColorSep(PCMYKColor,CMYKColorSep):
    '''special case color for making separating pdfs'''
    _scale = 100.
    def __init__(self, cyan=0, magenta=0, yellow=0, black=0,
                spotName=None, density=100, alpha=100):
        PCMYKColor.__init__(self,cyan,magenta,yellow,black,density,spotName,knockout=None,alpha=alpha)
    _cKwds='cyan magenta yellow black density alpha spotName'.split()

def cmyk2rgb(cmyk,density=1):
    "Convert from a CMYK color tuple to an RGB color tuple"
    c,m,y,k = cmyk
    # From the Adobe Postscript Ref. Manual 2nd ed.
    r = 1.0 - min(1.0, c + k)
    g = 1.0 - min(1.0, m + k)
    b = 1.0 - min(1.0, y + k)
    return (r,g,b)

def rgb2cmyk(r,g,b):
    '''one way to get cmyk from rgb'''
    c = 1 - r
    m = 1 - g
    y = 1 - b
    k = min(c,m,y)
    c = min(1,max(0,c-k))
    m = min(1,max(0,m-k))
    y = min(1,max(0,y-k))
    k = min(1,max(0,k))
    return (c,m,y,k)

def color2bw(colorRGB):
    "Transform an RGB color to a black and white equivalent."

    col = colorRGB
    r, g, b, a = col.red, col.green, col.blue, col.alpha
    n = (r + g + b) / 3.0
    bwColorRGB = Color(n, n, n, a)
    return bwColorRGB

def HexColor(val, htmlOnly=False, hasAlpha=False):
    """This function converts a hex string, or an actual integer number,
    into the corresponding color.  E.g., in "#AABBCC" or 0xAABBCC,
    AA is the red, BB is the green, and CC is the blue (00-FF).

    An alpha value can also be given in the form #AABBCCDD or 0xAABBCCDD where
    DD is the alpha value if hasAlpha is True.

    For completeness I assume that #aabbcc or 0xaabbcc are hex numbers
    otherwise a pure integer is converted as decimal rgb.  If htmlOnly is true,
    only the #aabbcc form is allowed.

    >>> HexColor('#ffffff')
    Color(1,1,1,1)
    >>> HexColor('#FFFFFF')
    Color(1,1,1,1)
    >>> HexColor('0xffffff')
    Color(1,1,1,1)
    >>> HexColor('16777215')
    Color(1,1,1,1)

    An '0x' or '#' prefix is required for hex (as opposed to decimal):

    >>> HexColor('ffffff')
    Traceback (most recent call last):
    ValueError: invalid literal for int() with base 10: 'ffffff'

    >>> HexColor('#FFFFFF', htmlOnly=True)
    Color(1,1,1,1)
    >>> HexColor('0xffffff', htmlOnly=True)
    Traceback (most recent call last):
    ValueError: not a hex string
    >>> HexColor('16777215', htmlOnly=True)
    Traceback (most recent call last):
    ValueError: not a hex string

    """ #" for emacs

    if isStr(val):
        val = asNative(val)
        b = 10
        if val[:1] == '#':
            val = val[1:]
            b = 16
            if len(val) == 8:
                alpha = True
        else:
            if htmlOnly:
                raise ValueError('not a hex string')
            if val[:2].lower() == '0x':
                b = 16
                val = val[2:]
                if len(val) == 8:
                    alpha = True
        val = int(val,b)
    if hasAlpha:
        return Color(((val>>24)&0xFF)/255.0,((val>>16)&0xFF)/255.0,((val>>8)&0xFF)/255.0,(val&0xFF)/255.0)
    return Color(((val>>16)&0xFF)/255.0,((val>>8)&0xFF)/255.0,(val&0xFF)/255.0)

def linearlyInterpolatedColor(c0, c1, x0, x1, x):
    """
    Linearly interpolates colors. Can handle RGB, CMYK and PCMYK
    colors - give ValueError if colours aren't the same.
    Doesn't currently handle 'Spot Color Interpolation'.
    """

    if c0.__class__ != c1.__class__:
        raise ValueError("Color classes must be the same for interpolation!\nGot %r and %r'"%(c0,c1))
    if x1<x0:
        x0,x1,c0,c1 = x1,x0,c1,c0 # normalized so x1>x0
    if x<x0-1e-8 or x>x1+1e-8: # fudge factor for numerical problems
        raise ValueError("Can't interpolate: x=%f is not between %f and %f!" % (x,x0,x1))
    if x<=x0:
        return c0
    elif x>=x1:
        return c1

    cname = c0.__class__.__name__
    dx = float(x1-x0)
    x = x-x0

    if cname == 'Color': # RGB
        r = c0.red+x*(c1.red - c0.red)/dx
        g = c0.green+x*(c1.green- c0.green)/dx
        b = c0.blue+x*(c1.blue - c0.blue)/dx
        a = c0.alpha+x*(c1.alpha - c0.alpha)/dx
        return Color(r,g,b,alpha=a)
    elif cname == 'CMYKColor':
        if cmykDistance(c0,c1)<1e-8:
            #colors same do density and preserve spotName if any
            assert c0.spotName == c1.spotName, "Identical cmyk, but different spotName"
            c = c0.cyan
            m = c0.magenta
            y = c0.yellow
            k = c0.black
            d = c0.density+x*(c1.density - c0.density)/dx
            a = c0.alpha+x*(c1.alpha - c0.alpha)/dx
            return CMYKColor(c,m,y,k, density=d, spotName=c0.spotName, alpha=a)
        elif cmykDistance(c0,_CMYK_white)<1e-8:
            #special c0 is white
            c = c1.cyan
            m = c1.magenta
            y = c1.yellow
            k = c1.black
            d = x*c1.density/dx
            a = x*c1.alpha/dx
            return CMYKColor(c,m,y,k, density=d, spotName=c1.spotName, alpha=a)
        elif cmykDistance(c1,_CMYK_white)<1e-8:
            #special c1 is white
            c = c0.cyan
            m = c0.magenta
            y = c0.yellow
            k = c0.black
            d = x*c0.density/dx
            d = c0.density*(1-x/dx)
            a = c0.alpha*(1-x/dx)
            return PCMYKColor(c,m,y,k, density=d, spotName=c0.spotName, alpha=a)
        else:
            c = c0.cyan+x*(c1.cyan - c0.cyan)/dx
            m = c0.magenta+x*(c1.magenta - c0.magenta)/dx
            y = c0.yellow+x*(c1.yellow - c0.yellow)/dx
            k = c0.black+x*(c1.black - c0.black)/dx
            d = c0.density+x*(c1.density - c0.density)/dx
            a = c0.alpha+x*(c1.alpha - c0.alpha)/dx
            return CMYKColor(c,m,y,k, density=d, alpha=a)
    elif cname == 'PCMYKColor':
        if cmykDistance(c0,c1)<1e-8:
            #colors same do density and preserve spotName if any
            assert c0.spotName == c1.spotName, "Identical cmyk, but different spotName"
            c = c0.cyan
            m = c0.magenta
            y = c0.yellow
            k = c0.black
            d = c0.density+x*(c1.density - c0.density)/dx
            a = c0.alpha+x*(c1.alpha - c0.alpha)/dx
            return PCMYKColor(c*100,m*100,y*100,k*100, density=d*100,
                              spotName=c0.spotName, alpha=100*a)
        elif cmykDistance(c0,_CMYK_white)<1e-8:
            #special c0 is white
            c = c1.cyan
            m = c1.magenta
            y = c1.yellow
            k = c1.black
            d = x*c1.density/dx
            a = x*c1.alpha/dx
            return PCMYKColor(c*100,m*100,y*100,k*100, density=d*100,
                              spotName=c1.spotName, alpha=a*100)
        elif cmykDistance(c1,_CMYK_white)<1e-8:
            #special c1 is white
            c = c0.cyan
            m = c0.magenta
            y = c0.yellow
            k = c0.black
            d = x*c0.density/dx
            d = c0.density*(1-x/dx)
            a = c0.alpha*(1-x/dx)
            return PCMYKColor(c*100,m*100,y*100,k*100, density=d*100,
                              spotName=c0.spotName, alpha=a*100)
        else:
            c = c0.cyan+x*(c1.cyan - c0.cyan)/dx
            m = c0.magenta+x*(c1.magenta - c0.magenta)/dx
            y = c0.yellow+x*(c1.yellow - c0.yellow)/dx
            k = c0.black+x*(c1.black - c0.black)/dx
            d = c0.density+x*(c1.density - c0.density)/dx
            a = c0.alpha+x*(c1.alpha - c0.alpha)/dx
            return PCMYKColor(c*100,m*100,y*100,k*100, density=d*100, alpha=a*100)
    else:
        raise ValueError("Can't interpolate: Unknown color class %s!" % cname)

def obj_R_G_B(c):
    '''attempt to convert an object to (red,green,blue)'''
    if isinstance(c,Color):
        return c.red,c.green,c.blue
    elif isinstance(c,(tuple,list)):
        if len(c)==3:
            return tuple(c)
        elif len(c)==4:
            return toColor(c).rgb()
        else:
            raise ValueError('obj_R_G_B(%r) bad argument' % (c))

# special case -- indicates no drawing should be done
# this is a hangover from PIDDLE - suggest we ditch it since it is not used anywhere
transparent = Color(0,0,0,alpha=0)

_CMYK_white=CMYKColor(0,0,0,0)
_PCMYK_white=PCMYKColor(0,0,0,0)
_CMYK_black=CMYKColor(0,0,0,1)
_PCMYK_black=PCMYKColor(0,0,0,100)

# Special colors
ReportLabBlueOLD = HexColor(0x4e5688)
ReportLabBlue = HexColor(0x00337f)
ReportLabBluePCMYK = PCMYKColor(100,65,0,30,spotName='Pantone 288U')
ReportLabLightBlue = HexColor(0xb7b9d3)
ReportLabFidBlue=HexColor(0x3366cc)
ReportLabFidRed=HexColor(0xcc0033)
ReportLabGreen = HexColor(0x336600)
ReportLabLightGreen = HexColor(0x339933)

# color constants -- mostly from HTML standard
aliceblue =     HexColor(0xF0F8FF)
antiquewhite =  HexColor(0xFAEBD7)
aqua =  HexColor(0x00FFFF)
aquamarine =    HexColor(0x7FFFD4)
azure =     HexColor(0xF0FFFF)
beige =     HexColor(0xF5F5DC)
bisque =    HexColor(0xFFE4C4)
black =     HexColor(0x000000)
blanchedalmond =    HexColor(0xFFEBCD)
blue =  HexColor(0x0000FF)
blueviolet =    HexColor(0x8A2BE2)
brown =     HexColor(0xA52A2A)
burlywood =     HexColor(0xDEB887)
cadetblue =     HexColor(0x5F9EA0)
chartreuse =    HexColor(0x7FFF00)
chocolate =     HexColor(0xD2691E)
coral =     HexColor(0xFF7F50)
cornflowerblue = cornflower =   HexColor(0x6495ED)
cornsilk =  HexColor(0xFFF8DC)
crimson =   HexColor(0xDC143C)
cyan =  HexColor(0x00FFFF)
darkblue =  HexColor(0x00008B)
darkcyan =  HexColor(0x008B8B)
darkgoldenrod =     HexColor(0xB8860B)
darkgray =  HexColor(0xA9A9A9)
darkgrey =  darkgray
darkgreen =     HexColor(0x006400)
darkkhaki =     HexColor(0xBDB76B)
darkmagenta =   HexColor(0x8B008B)
darkolivegreen =    HexColor(0x556B2F)
darkorange =    HexColor(0xFF8C00)
darkorchid =    HexColor(0x9932CC)
darkred =   HexColor(0x8B0000)
darksalmon =    HexColor(0xE9967A)
darkseagreen =  HexColor(0x8FBC8B)
darkslateblue =     HexColor(0x483D8B)
darkslategray =     HexColor(0x2F4F4F)
darkslategrey = darkslategray
darkturquoise =     HexColor(0x00CED1)
darkviolet =    HexColor(0x9400D3)
deeppink =  HexColor(0xFF1493)
deepskyblue =   HexColor(0x00BFFF)
dimgray =   HexColor(0x696969)
dimgrey = dimgray
dodgerblue =    HexColor(0x1E90FF)
firebrick =     HexColor(0xB22222)
floralwhite =   HexColor(0xFFFAF0)
forestgreen =   HexColor(0x228B22)
fuchsia =   HexColor(0xFF00FF)
gainsboro =     HexColor(0xDCDCDC)
ghostwhite =    HexColor(0xF8F8FF)
gold =  HexColor(0xFFD700)
goldenrod =     HexColor(0xDAA520)
gray =  HexColor(0x808080)
grey = gray
green =     HexColor(0x008000)
greenyellow =   HexColor(0xADFF2F)
honeydew =  HexColor(0xF0FFF0)
hotpink =   HexColor(0xFF69B4)
indianred =     HexColor(0xCD5C5C)
indigo =    HexColor(0x4B0082)
ivory =     HexColor(0xFFFFF0)
khaki =     HexColor(0xF0E68C)
lavender =  HexColor(0xE6E6FA)
lavenderblush =     HexColor(0xFFF0F5)
lawngreen =     HexColor(0x7CFC00)
lemonchiffon =  HexColor(0xFFFACD)
lightblue =     HexColor(0xADD8E6)
lightcoral =    HexColor(0xF08080)
lightcyan =     HexColor(0xE0FFFF)
lightgoldenrodyellow =  HexColor(0xFAFAD2)
lightgreen =    HexColor(0x90EE90)
lightgrey =     HexColor(0xD3D3D3)
lightpink =     HexColor(0xFFB6C1)
lightsalmon =   HexColor(0xFFA07A)
lightseagreen =     HexColor(0x20B2AA)
lightskyblue =  HexColor(0x87CEFA)
lightslategray =    HexColor(0x778899)
lightslategrey = lightslategray
lightsteelblue =    HexColor(0xB0C4DE)
lightyellow =   HexColor(0xFFFFE0)
lime =  HexColor(0x00FF00)
limegreen =     HexColor(0x32CD32)
linen =     HexColor(0xFAF0E6)
magenta =   HexColor(0xFF00FF)
maroon =    HexColor(0x800000)
mediumaquamarine =  HexColor(0x66CDAA)
mediumblue =    HexColor(0x0000CD)
mediumorchid =  HexColor(0xBA55D3)
mediumpurple =  HexColor(0x9370DB)
mediumseagreen =    HexColor(0x3CB371)
mediumslateblue =   HexColor(0x7B68EE)
mediumspringgreen =     HexColor(0x00FA9A)
mediumturquoise =   HexColor(0x48D1CC)
mediumvioletred =   HexColor(0xC71585)
midnightblue =  HexColor(0x191970)
mintcream =     HexColor(0xF5FFFA)
mistyrose =     HexColor(0xFFE4E1)
moccasin =  HexColor(0xFFE4B5)
navajowhite =   HexColor(0xFFDEAD)
navy =  HexColor(0x000080)
oldlace =   HexColor(0xFDF5E6)
olive =     HexColor(0x808000)
olivedrab =     HexColor(0x6B8E23)
orange =    HexColor(0xFFA500)
orangered =     HexColor(0xFF4500)
orchid =    HexColor(0xDA70D6)
palegoldenrod =     HexColor(0xEEE8AA)
palegreen =     HexColor(0x98FB98)
paleturquoise =     HexColor(0xAFEEEE)
palevioletred =     HexColor(0xDB7093)
papayawhip =    HexColor(0xFFEFD5)
peachpuff =     HexColor(0xFFDAB9)
peru =  HexColor(0xCD853F)
pink =  HexColor(0xFFC0CB)
plum =  HexColor(0xDDA0DD)
powderblue =    HexColor(0xB0E0E6)
purple =    HexColor(0x800080)
red =   HexColor(0xFF0000)
rosybrown =     HexColor(0xBC8F8F)
royalblue =     HexColor(0x4169E1)
saddlebrown =   HexColor(0x8B4513)
salmon =    HexColor(0xFA8072)
sandybrown =    HexColor(0xF4A460)
seagreen =  HexColor(0x2E8B57)
seashell =  HexColor(0xFFF5EE)
sienna =    HexColor(0xA0522D)
silver =    HexColor(0xC0C0C0)
skyblue =   HexColor(0x87CEEB)
slateblue =     HexColor(0x6A5ACD)
slategray =     HexColor(0x708090)
slategrey = slategray
snow =  HexColor(0xFFFAFA)
springgreen =   HexColor(0x00FF7F)
steelblue =     HexColor(0x4682B4)
tan =   HexColor(0xD2B48C)
teal =  HexColor(0x008080)
thistle =   HexColor(0xD8BFD8)
tomato =    HexColor(0xFF6347)
turquoise =     HexColor(0x40E0D0)
violet =    HexColor(0xEE82EE)
wheat =     HexColor(0xF5DEB3)
white =     HexColor(0xFFFFFF)
whitesmoke =    HexColor(0xF5F5F5)
yellow =    HexColor(0xFFFF00)
yellowgreen =   HexColor(0x9ACD32)
fidblue=HexColor(0x3366cc)
fidred=HexColor(0xcc0033)
fidlightblue=HexColor("#d6e0f5")

ColorType=type(black)

    ################################################################
    #
    #  Helper functions for dealing with colors.  These tell you
    #  which are predefined, so you can print color charts;
    #  and can give the nearest match to an arbitrary color object
    #
    #################################################################

def colorDistance(col1, col2):
    """Returns a number between 0 and root(3) stating how similar
    two colours are - distance in r,g,b, space.  Only used to find
    names for things."""
    return math.sqrt(
            (col1.red - col2.red)**2 +
            (col1.green - col2.green)**2 +
            (col1.blue - col2.blue)**2
            )

def cmykDistance(col1, col2):
    """Returns a number between 0 and root(4) stating how similar
    two colours are - distance in r,g,b, space.  Only used to find
    names for things."""
    return math.sqrt(
            (col1.cyan - col2.cyan)**2 +
            (col1.magenta - col2.magenta)**2 +
            (col1.yellow - col2.yellow)**2 +
            (col1.black - col2.black)**2
            )

_namedColors = None

def getAllNamedColors():
    #returns a dictionary of all the named ones in the module
    # uses a singleton for efficiency
    global _namedColors
    if _namedColors is not None: return _namedColors
    from reportlab.lib import colors
    _namedColors = {}
    for name, value in colors.__dict__.items():
        if isinstance(value, Color):
            _namedColors[name] = value

    return _namedColors

def describe(aColor,mode=0):
    '''finds nearest colour match to aColor.
    mode=0 print a string desription
    mode=1 return a string description
    mode=2 return (distance, colorName)
    '''
    namedColors = getAllNamedColors()
    closest = (10, None, None)  #big number, name, color
    for name, color in namedColors.items():
        distance = colorDistance(aColor, color)
        if distance < closest[0]:
            closest = (distance, name, color)
    if mode<=1:
        s = 'best match is %s, distance %0.4f' % (closest[1], closest[0])
        if mode==0: print(s)
        else: return s
    elif mode==2:
        return (closest[1], closest[0])
    else:
        raise ValueError("Illegal value for mode "+str(mode))

def hue2rgb(m1, m2, h):
    if h<0: h += 1
    if h>1: h -= 1
    if h*6<1: return m1+(m2-m1)*h*6
    if h*2<1: return m2
    if h*3<2: return m1+(m2-m1)*(4-6*h)
    return m1

def hsl2rgb(h, s, l): 
    if l<=0.5:
        m2 = l*(s+1)
    else:
        m2 = l+s-l*s
    m1 = l*2-m2
    return hue2rgb(m1, m2, h+1./3),hue2rgb(m1, m2, h),hue2rgb(m1, m2, h-1./3)

import re
_re_css = re.compile(r'^\s*(pcmyk|cmyk|rgb|hsl)(a|)\s*\(\s*([^)]*)\)\s*$')
class cssParse:
    def pcVal(self,v):
        v = v.strip()
        try:
            c=float(v[:-1])
            c=min(100,max(0,c))/100.
        except:
            raise ValueError('bad percentage argument value %r in css color %r' % (v,self.s))
        return c

    def rgbPcVal(self,v):
        return int(self.pcVal(v)*255+0.5)/255.

    def rgbVal(self,v):
        v = v.strip()
        try:
            c=float(v)
            if 0<c<=1: c *= 255
            return int(min(255,max(0,c)))/255.
        except:
            raise ValueError('bad argument value %r in css color %r' % (v,self.s))

    def hueVal(self,v):
        v = v.strip()
        try:
            c=float(v)
            return ((c%360+360)%360)/360.
        except:
            raise ValueError('bad hue argument value %r in css color %r' % (v,self.s))

    def alphaVal(self,v,c=1,n='alpha'):
        try:
            a = float(v)
            return min(c,max(0,a))
        except:
            raise ValueError('bad %s argument value %r in css color %r' % (n,v,self.s))

    _n_c = dict(pcmyk=(4,100,True,False),cmyk=(4,1,True,False),hsl=(3,1,False,True),rgb=(3,1,False,False))

    def __call__(self,s):
        n = _re_css.match(s)
        if not n: return
        self.s = s
        b,c,cmyk,hsl = self._n_c[n.group(1)]
        ha = n.group(2)
        n = n.group(3).split(',')   #strip parens and split on comma
        if len(n)!=(b+(ha and 1 or 0)):
            raise ValueError('css color %r has wrong number of components' % s)
        if ha:
            n,a = n[:b],self.alphaVal(n[b],c)
        else:
            a = c

        if cmyk:
            C = self.alphaVal(n[0],c,'cyan')
            M = self.alphaVal(n[1],c,'magenta')
            Y = self.alphaVal(n[2],c,'yellow')
            K = self.alphaVal(n[3],c,'black')
            return (c>1 and PCMYKColor or CMYKColor)(C,M,Y,K,alpha=a)
        else:
            if hsl:
                R,G,B= hsl2rgb(self.hueVal(n[0]),self.pcVal(n[1]),self.pcVal(n[2]))
            else:
                R,G,B = list(map('%' in n[0] and self.rgbPcVal or self.rgbVal,n))

            return Color(R,G,B,a)

cssParse=cssParse()

class toColor:
    """Accepot an expression returnng a Color subclass.

    This used to accept arbitrary Python expressions, which resulted in increasngly devilish CVEs and
    security holes from tie to time.  In April 2023 we are creating explicit, "dumb" parsing code to
    replace this.  Acceptable patterns are

    a Color instance passed in by the Python programmer
    a named list of colours ('pink' etc')
    list of 3 or 4 numbers
    all CSS colour expression
    """
    _G = {} #globals we like (eventually)

    def __init__(self):
        self.extraColorsNS = {} #used for overriding/adding to existing color names
                                #make case insensitive if that's your wish

    def setExtraColorsNameSpace(self,NS):
        self.extraColorsNS = NS

    def __call__(self,arg,default=None):
        '''try to map an arbitrary arg to a color instance
        '''
        if isinstance(arg,Color): return arg
        if isinstance(arg,(tuple,list)):
            assert 3<=len(arg)<=4, 'Can only convert 3 and 4 sequences to color'
            assert 0<=min(arg) and max(arg)<=1
            return len(arg)==3 and Color(arg[0],arg[1],arg[2]) or CMYKColor(arg[0],arg[1],arg[2],arg[3])
        elif isStr(arg):
            arg = asNative(arg)
            C = cssParse(arg)
            if C: return C
            if arg in self.extraColorsNS: return self.extraColorsNS[arg]
            C = getAllNamedColors()
            s = arg.lower()
            if s in C: return C[s]


            # allow expressions like 'Blacker(red, 0.5)'
            # >>> re.compile(r"(Blacker|Whiter)\((\w+)\,\s?([0-9.]+)\)").match(msg).groups()
            # ('Blacker', 'red', '0.5')
            # >>> 
            pat = re.compile(r"(Blacker|Whiter)\((\w+)\,\s?([0-9.]+)\)")
            m = pat.match(arg)
            if m:
                funcname, rootcolor, num = m.groups()
                if funcname == 'Blacker':
                    return Blacker(rootcolor, float(num))
                else:
                    return Whiter(rootcolor, float(num))

            try:
                import ast
                expr = ast.literal_eval(arg)    #safe probably only a tuple or list of values
                return toColor(expr)
            except (SyntaxError, ValueError):
                pass

            if rl_config.toColorCanUse=='rl_safe_eval':
                #the most dangerous option
                G = C.copy()
                G.update(self.extraColorsNS)
                if not self._G:
                    C = globals()
                    self._G = {s:C[s] for s in '''Blacker CMYKColor CMYKColorSep Color ColorType HexColor PCMYKColor PCMYKColorSep Whiter
                        _chooseEnforceColorSpace _enforceCMYK _enforceError _enforceRGB _enforceSEP _enforceSEP_BLACK
                        _enforceSEP_CMYK _namedColors _re_css asNative cmyk2rgb cmykDistance color2bw colorDistance
                        cssParse describe fade fp_str getAllNamedColors hsl2rgb hue2rgb isStr linearlyInterpolatedColor
                        literal_eval obj_R_G_B opaqueColor rgb2cmyk setColors toColor toColorOrNone'''.split()}
                G.update(self._G)
                try:
                    return toColor(rl_safe_eval(arg,g=G,l={}))
                except:
                    pass
            elif rl_config.toColorCanUse=='rl_extended_literal_eval':
                C = globals()
                S = getAllNamedColors().copy()
                C = {k:C[k] for k in '''Blacker CMYKColor CMYKColorSep Color ColorType HexColor PCMYKColor PCMYKColorSep Whiter
                        _chooseEnforceColorSpace _enforceCMYK _enforceError _enforceRGB _enforceSEP _enforceSEP_BLACK
                        _enforceSEP_CMYK _namedColors _re_css asNative cmyk2rgb cmykDistance color2bw colorDistance
                        cssParse describe fade fp_str getAllNamedColors hsl2rgb hue2rgb linearlyInterpolatedColor
                        obj_R_G_B opaqueColor rgb2cmyk setColors toColor toColorOrNone'''.split()
                        if callable(C.get(k,None))}
                try:
                    return rl_extended_literal_eval(arg,C,S)
                except (ValueError, SyntaxError):
                    pass

        try:
            return HexColor(arg)
        except:
            if default is None:
                raise ValueError('Invalid color value %r' % arg)
            return default

toColor = toColor()

def toColorOrNone(arg,default=None):
    '''as above but allows None as a legal value'''
    if arg is None:
        return None
    else:
        return toColor(arg, default)

def setColors(**kw):
    UNDEF = []
    progress = 1
    assigned = {}
    while kw and progress:
        progress = 0
        for k, v in kw.items():
            if isinstance(v,(tuple,list)):
                c = list(map(lambda x,UNDEF=UNDEF: toColor(x,UNDEF),v))
                if isinstance(v,tuple): c = tuple(c)
                ok = UNDEF not in c
            else:
                c = toColor(v,UNDEF)
                ok = c is not UNDEF
            if ok:
                assigned[k] = c
                del kw[k]
                progress = 1

    if kw: raise ValueError("Can't convert\n%s" % str(kw))
    getAllNamedColors()
    for k, c in assigned.items():
        globals()[k] = c
        if isinstance(c,Color): _namedColors[k] = c

def Whiter(c,f):
    '''given a color combine with white as c*f w*(1-f) 0<=f<=1'''
    c = toColor(c)
    if isinstance(c,CMYKColorSep):
        c = c.clone()
        if isinstance(c,PCMYKColorSep):
            c.__class__ = PCMYKColor
        else:
            c.__class__ = CMYKColor
    if isinstance(c,PCMYKColor):
        w = _PCMYK_white
    elif isinstance(c,CMYKColor): w = _CMYK_white
    else: w = white
    return linearlyInterpolatedColor(w, c, 0, 1, f)

def Blacker(c,f):
    '''given a color combine with black as c*f+b*(1-f) 0<=f<=1'''
    c = toColor(c)
    if isinstance(c,CMYKColorSep):
        c = c.clone()
        if isinstance(c,PCMYKColorSep):
            c.__class__ = PCMYKColor
        else:
            c.__class__ = CMYKColor
    if isinstance(c,PCMYKColor):
        b = _PCMYK_black
    elif isinstance(c,CMYKColor): b = _CMYK_black
    else: b = black
    return linearlyInterpolatedColor(b, c, 0, 1, f)

def fade(aSpotColor, percentages):
    """Waters down spot colors and returns a list of new ones

    e.g fade(myColor, [100,80,60,40,20]) returns a list of five colors
    """
    out = []
    for percent in percentages:
        frac = percent * 0.01   #assume they give us numbers from 0 to 100
        newCyan = frac * aSpotColor.cyan
        newMagenta = frac * aSpotColor.magenta
        newYellow = frac * aSpotColor.yellow
        newBlack = frac * aSpotColor.black
        newDensity = frac * aSpotColor.density
        newSpot = CMYKColor(    newCyan, newMagenta, newYellow, newBlack,
                            spotName = aSpotColor.spotName,
                            density = newDensity)
        out.append(newSpot)
    return out

def _enforceError(kind,c,tc):
    if isinstance(tc,Color):
        xtra = tc._lookupName()
        xtra = xtra and '(%s)'%xtra or ''
    else:
        xtra = ''
    raise ValueError('Non %s color %r%s' % (kind,c,xtra))

def _enforceSEP(c):
    '''pure separating colors only, this makes black a problem'''
    tc = toColor(c)
    if not isinstance(tc,CMYKColorSep):
        _enforceError('separating',c,tc)
    return tc

def _enforceSEP_BLACK(c):
    '''separating + blacks only'''
    tc = toColor(c)
    if not isinstance(tc,CMYKColorSep):
        if isinstance(tc,Color) and tc.red==tc.blue==tc.green: #ahahahah it's a grey
            tc = _CMYK_black.clone(density=1-tc.red)
        elif not (isinstance(tc,CMYKColor) and tc.cyan==tc.magenta==tc.yellow==0): #ie some shade of grey
            _enforceError('separating or black',c,tc)
    return tc

def _enforceSEP_CMYK(c):
    '''separating or cmyk only'''
    tc = toColor(c)
    if not isinstance(tc,CMYKColorSep):
        if isinstance(tc,Color) and tc.red==tc.blue==tc.green: #ahahahah it's a grey
            tc = _CMYK_black.clone(density=1-tc.red)
        elif not isinstance(tc,CMYKColor):
            _enforceError('separating or CMYK',c,tc)
    return tc

def _enforceCMYK(c):
    '''cmyk outputs only (rgb greys converted)'''
    tc = toColor(c)
    if not isinstance(tc,CMYKColor):
        if isinstance(tc,Color) and tc.red==tc.blue==tc.green: #ahahahah it's a grey
            tc = _CMYK_black.clone(black=1-tc.red,alpha=tc.alpha)
        else:
            _enforceError('CMYK',c,tc)
    elif isinstance(tc,CMYKColorSep):
        tc = tc.clone()
        tc.__class__ = CMYKColor
    return tc

def _enforceRGB(c):
    tc = toColor(c)
    if isinstance(tc,CMYKColor):
        if tc.cyan==tc.magenta==tc.yellow==0: #ahahahah it's grey
            v = 1-tc.black*tc.density
            tc = Color(v,v,v,alpha=tc.alpha)
        else:
            _enforceError('RGB',c,tc)
    return tc

def _chooseEnforceColorSpace(enforceColorSpace):
    if enforceColorSpace is not None and not callable(enforceColorSpace):
        if isinstance(enforceColorSpace,str): enforceColorSpace=enforceColorSpace.upper()
        if enforceColorSpace=='CMYK':
            enforceColorSpace = _enforceCMYK
        elif enforceColorSpace=='RGB':
            enforceColorSpace = _enforceRGB
        elif enforceColorSpace=='SEP':
            enforceColorSpace = _enforceSEP
        elif enforceColorSpace=='SEP_BLACK':
            enforceColorSpace = _enforceSEP_BLACK
        elif enforceColorSpace=='SEP_CMYK':
            enforceColorSpace = _enforceSEP_CMYK
        else:
            raise ValueError('Invalid value for Canvas argument enforceColorSpace=%r' % enforceColorSpace)
    return enforceColorSpace

if __name__ == "__main__":
    import doctest
    doctest.testmod()
