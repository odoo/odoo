#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/lib/colors.py
__version__=''' $Id: colors.py 2587 2005-05-03 11:41:54Z rgbecker $ '''

import string, math
from types import StringType, ListType, TupleType
from reportlab.lib.utils import fp_str
_SeqTypes = (ListType,TupleType)

class Color:
    """This class is used to represent color.  Components red, green, blue
    are in the range 0 (dark) to 1 (full intensity)."""

    def __init__(self, red=0, green=0, blue=0):
        "Initialize with red, green, blue in range [0-1]."
        self.red, self.green, self.blue = red,green,blue

    def __repr__(self):
        return "Color(%s)" % string.replace(fp_str(self.red, self.green, self.blue),' ',',')

    def __hash__(self):
        return hash( (self.red, self.green, self.blue) )

    def __cmp__(self,other):
        try:
            dsum = 4*self.red-4*other.red + 2*self.green-2*other.green + self.blue-other.blue
        except:
            return -1
        if dsum > 0: return 1
        if dsum < 0: return -1
        return 0

    def rgb(self):
        "Returns a three-tuple of components"
        return (self.red, self.green, self.blue)

    def bitmap_rgb(self):
        return tuple(map(lambda x: int(x*255)&255, self.rgb()))

    def hexval(self):
        return '0x%02x%02x%02x' % self.bitmap_rgb()

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

    def __init__(self, cyan=0, magenta=0, yellow=0, black=0,
                spotName=None, density=1, knockout=None):
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
        return "CMYKColor(%s%s%s%s)" % (
            string.replace(fp_str(self.cyan, self.magenta, self.yellow, self.black),' ',','),
            (self.spotName and (',spotName='+repr(self.spotName)) or ''),
            (self.density!=1 and (',density='+fp_str(self.density)) or ''),
            (self.knockout is not None and (',knockout=%d' % self.knockout) or ''),
            )

    def __hash__(self):
        return hash( (self.cyan, self.magenta, self.yellow, self.black, self.density, self.spotName) )

    def __cmp__(self,other):
        """Partial ordering of colors according to a notion of distance.

        Comparing across the two color models is of limited use."""
        # why the try-except?  What can go wrong?
        if isinstance(other, CMYKColor):
            dsum = (((( (self.cyan-other.cyan)*2 +
                        (self.magenta-other.magenta))*2+
                        (self.yellow-other.yellow))*2+
                        (self.black-other.black))*2+
                        (self.density-other.density))*2 + cmp(self.spotName or '',other.spotName or '')
        else:  # do the RGB comparison
            try:
                dsum = ((self.red-other.red)*2+(self.green-other.green))*2+(self.blue-other.blue)
            except: # or just return 'not equal' if not a color
                return -1
        if dsum >= 0:
            return dsum>0
        else:
            return -1

    def cmyk(self):
        "Returns a tuple of four color components - syntactic sugar"
        return (self.cyan, self.magenta, self.yellow, self.black)

    def _density_str(self):
        return fp_str(self.density)

class PCMYKColor(CMYKColor):
    '''100 based CMYKColor with density and a spotName; just like Rimas uses'''
    def __init__(self,cyan,magenta,yellow,black,density=100,spotName=None,knockout=None):
        CMYKColor.__init__(self,cyan/100.,magenta/100.,yellow/100.,black/100.,spotName,density/100.,knockout=knockout)

    def __repr__(self):
        return "PCMYKColor(%s%s%s%s)" % (
            string.replace(fp_str(self.cyan*100, self.magenta*100, self.yellow*100, self.black*100),' ',','),
            (self.spotName and (',spotName='+repr(self.spotName)) or ''),
            (self.density!=1 and (',density='+fp_str(self.density*100)) or ''),
            (self.knockout is not None and (',knockout=%d' % self.knockout) or ''),
            )

def cmyk2rgb((c,m,y,k),density=1):
    "Convert from a CMYK color tuple to an RGB color tuple"
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
    r, g, b = col.red, col.green, col.blue
    n = (r + g + b) / 3.0
    bwColorRGB = Color(n, n, n)
    return bwColorRGB

def HexColor(val):
    """This function converts a hex string, or an actual integer number,
    into the corresponding color.  E.g., in "AABBCC" or 0xAABBCC,
    AA is the red, BB is the green, and CC is the blue (00-FF).

    HTML uses a hex string with a preceding hash; if this is present,
    it is stripped off.  (AR, 3-3-2000)

    For completeness I assume that #aabbcc or 0xaabbcc are hex numbers
    otherwise a pure integer is converted as decimal rgb
    """

    if type(val) == StringType:
        b = 10
        if val[:1] == '#':
            val = val[1:]
            b = 16
        elif string.lower(val[:2]) == '0x':
            b = 16
            val = val[2:]
        val = string.atoi(val,b)
    return Color(((val>>16)&0xFF)/255.0,((val>>8)&0xFF)/255.0,(val&0xFF)/255.0)

def linearlyInterpolatedColor(c0, c1, x0, x1, x):
    """
    Linearly interpolates colors. Can handle RGB, CMYK and PCMYK
    colors - give ValueError if colours aren't the same.
    Doesn't currently handle 'Spot Color Interpolation'.
    """

    if c0.__class__ != c1.__class__:
        raise ValueError, "Color classes must be the same for interpolation!"
    if x1<x0:
        x0,x1,c0,c1 = x1,x0,c1,c0 # normalized so x1>x0
    if x<x0-1e-8 or x>x1+1e-8: # fudge factor for numerical problems
        raise ValueError, "Can't interpolate: x=%f is not between %f and %f!" % (x,x0,x1)
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
        return Color(r,g,b)
    elif cname == 'CMYKColor':
        c = c0.cyan+x*(c1.cyan - c0.cyan)/dx
        m = c0.magenta+x*(c1.magenta - c0.magenta)/dx
        y = c0.yellow+x*(c1.yellow - c0.yellow)/dx
        k = c0.black+x*(c1.black - c0.black)/dx
        d = c0.density+x*(c1.density - c0.density)/dx
        return CMYKColor(c,m,y,k, density=d)
    elif cname == 'PCMYKColor':
        if cmykDistance(c0,c1)<1e-8:
            #colors same do density and preserve spotName if any
            assert c0.spotName == c1.spotName, "Identical cmyk, but different spotName"
            c = c0.cyan
            m = c0.magenta
            y = c0.yellow
            k = c0.black
            d = c0.density+x*(c1.density - c0.density)/dx
            return PCMYKColor(c*100,m*100,y*100,k*100, density=d*100, spotName=c0.spotName)
        elif cmykDistance(c0,_CMYK_white)<1e-8:
            #special c0 is white
            c = c1.cyan
            m = c1.magenta
            y = c1.yellow
            k = c1.black
            d = x*c1.density/dx
            return PCMYKColor(c*100,m*100,y*100,k*100, density=d*100, spotName=c1.spotName)
        elif cmykDistance(c1,_CMYK_white)<1e-8:
            #special c1 is white
            c = c0.cyan
            m = c0.magenta
            y = c0.yellow
            k = c0.black
            d = x*c0.density/dx
            d = c0.density*(1-x/dx)
            return PCMYKColor(c*100,m*100,y*100,k*100, density=d*100, spotName=c0.spotName)
        else:
            c = c0.cyan+x*(c1.cyan - c0.cyan)/dx
            m = c0.magenta+x*(c1.magenta - c0.magenta)/dx
            y = c0.yellow+x*(c1.yellow - c0.yellow)/dx
            k = c0.black+x*(c1.black - c0.black)/dx
            d = c0.density+x*(c1.density - c0.density)/dx
            return PCMYKColor(c*100,m*100,y*100,k*100, density=d*100)
    else:
        raise ValueError, "Can't interpolate: Unknown color class %s!" % cname

# special case -- indicates no drawing should be done
# this is a hangover from PIDDLE - suggest we ditch it since it is not used anywhere
#transparent = Color(-1, -1, -1)

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
darkturquoise =     HexColor(0x00CED1)
darkviolet =    HexColor(0x9400D3)
deeppink =  HexColor(0xFF1493)
deepskyblue =   HexColor(0x00BFFF)
dimgray =   HexColor(0x696969)
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
    import colors
    _namedColors = {}
    for (name, value) in colors.__dict__.items():
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
    for (name, color) in namedColors.items():
        distance = colorDistance(aColor, color)
        if distance < closest[0]:
            closest = (distance, name, color)
    if mode<=1:
        s = 'best match is %s, distance %0.4f' % (closest[1], closest[0])
        if mode==0: print s
        else: return s
    elif mode==2:
        return (closest[1], closest[0])
    else:
        raise ValueError, "Illegal value for mode "+str(mode)

def toColor(arg,default=None):
    '''try to map an arbitrary arg to a color instance'''
    if isinstance(arg,Color): return arg
    tArg = type(arg)
    if tArg in _SeqTypes:
        assert 3<=len(arg)<=4, 'Can only convert 3 and 4 sequences to color'
        assert 0<=min(arg) and max(arg)<=1
        return len(arg)==3 and Color(arg[0],arg[1],arg[2]) or CMYKColor(arg[0],arg[1],arg[2],arg[3])
    elif tArg == StringType:
        C = getAllNamedColors()
        s = string.lower(arg)
        if C.has_key(s): return C[s]
        try:
            return toColor(eval(arg))
        except:
            pass

    try:
        return HexColor(arg)
    except:
        if default is None:
            raise 'Invalid color value', str(arg)
        return default

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
            if type(v) in (type(()),type([])):
                c = map(lambda x,UNDEF=UNDEF: toColor(x,UNDEF),v)
                if type(v) is type(()): c = tuple(c)
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
    if isinstance(c,PCMYKColor):
        w = _PCMYK_white
    elif isinstance(c,CMYKColor): w = _CMYK_white
    else: w = white
    return linearlyInterpolatedColor(w, c, 0, 1, f)

def Blacker(c,f):
    '''given a color combine with black as c*f+b*(1-f) 0<=f<=1'''
    c = toColor(c)
    if isinstance(c,PCMYKColor):
        b = _PCMYK_black
    elif isinstance(c,CMYKColor): b = _CMYK_black
    else: b = black
    return linearlyInterpolatedColor(b, c, 0, 1, f)
