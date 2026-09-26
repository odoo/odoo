#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/graphics/charts/utils.py

__version__='3.3.0'
__doc__="Utilities used here and there."
from time import mktime, gmtime, strftime
from math import log10, pi, floor, sin, cos, hypot
import weakref
from reportlab.graphics.shapes import transformPoints, inverse, Ellipse, Group, String, numericXShift
from reportlab.lib.utils import flatten
from reportlab.pdfbase.pdfmetrics import stringWidth

### Dinu's stuff used in some line plots (likely to vansih).
def mkTimeTuple(timeString):
    "Convert a 'dd/mm/yyyy' formatted string to a tuple for use in the time module."

    L = [0] * 9
    dd, mm, yyyy = list(map(int, timeString.split('/')))
    L[:3] = [yyyy, mm, dd]

    return tuple(L)

def str2seconds(timeString):
    "Convert a number of seconds since the epoch into a date string."

    return mktime(mkTimeTuple(timeString))

def seconds2str(seconds):
    "Convert a date string into the number of seconds since the epoch."

    return strftime('%Y-%m-%d', gmtime(seconds))

### Aaron's rounding function for making nice values on axes.
def nextRoundNumber(x):
    """Return the first 'nice round number' greater than or equal to x

    Used in selecting apropriate tick mark intervals; we say we want
    an interval which places ticks at least 10 points apart, work out
    what that is in chart space, and ask for the nextRoundNumber().
    Tries the series 1,2,5,10,20,50,100.., going up or down as needed.
    """

    #guess to nearest order of magnitude
    if x in (0, 1):
        return x

    if x < 0:
        return -1.0 * nextRoundNumber(-x)
    else:
        lg = int(log10(x))

        if lg == 0:
            if x < 1:
                base = 0.1
            else:
                base = 1.0
        elif lg < 0:
            base = 10.0 ** (lg - 1)
        else:
            base = 10.0 ** lg    # e.g. base(153) = 100
        # base will always be lower than x

        if base >= x:
            return base * 1.0
        elif (base * 2) >= x:
            return base * 2.0
        elif (base * 5) >= x:
            return base * 5.0
        else:
            return base * 10.0

_intervals=(.1, .2, .25, .5)
_j_max=len(_intervals)-1
def find_interval(lo,hi,I=5):
    'determine tick parameters for range [lo, hi] using I intervals'

    if lo >= hi:
        if lo==hi:
            if lo==0:
                lo = -.1
                hi =  .1
            else:
                lo = 0.9*lo
                hi = 1.1*hi
        else:
            raise ValueError("lo>hi")
    x=(hi - lo)/float(I)
    b= (x>0 and (x<1 or x>10)) and 10**floor(log10(x)) or 1
    b = b
    while 1:
        a = x/b
        if a<=_intervals[-1]: break
        b = b*10

    j = 0
    while a>_intervals[j]: j = j + 1

    while 1:
        ss = _intervals[j]*b
        n = lo/ss
        l = int(n)-(n<0)
        n = ss*l
        x = ss*(l+I)
        a = I*ss
        if n>0:
            if a>=hi:
                n = 0.0
                x = a
        elif hi<0:
            a = -a
            if lo>a:
                n = a
                x = 0
        if hi<=x and n<=lo: break
        j = j + 1
        if j>_j_max:
            j = 0
            b = b*10
    return n, x, ss, lo - n + x - hi

def find_good_grid(lower,upper,n=(4,5,6,7,8,9), grid=None):
    if grid:
        t = divmod(lower,grid)[0] * grid
        hi, z = divmod(upper,grid)
        if z>1e-8: hi = hi+1
        hi = hi*grid
    else:
        try:
            n[0]
        except TypeError:
            n = range(max(1,n-2),max(n+3,2))

        w = 1e308
        for i in n:
            z=find_interval(lower,upper,i)
            if z[3]<w:
                t, hi, grid = z[:3]
                w=z[3]
    return t, hi, grid

def ticks(lower, upper, n=(4,5,6,7,8,9), split=1, percent=0, grid=None, labelVOffset=0):
    '''
    return tick positions and labels for range lower<=x<=upper
    n=number of intervals to try (can be a list or sequence)
    split=1 return ticks then labels else (tick,label) pairs
    '''
    t, hi, grid = find_good_grid(lower, upper, n, grid)
    power = floor(log10(grid))
    if power==0: power = 1
    w = grid/10.**power
    w = int(w)!=w

    if power > 3 or power < -3:
        format = '%+'+repr(w+7)+'.0e'
    else:
        if power >= 0:
            digits = int(power)+w
            format = '%' + repr(digits)+'.0f'
        else:
            digits = w-int(power)
            format = '%'+repr(digits+2)+'.'+repr(digits)+'f'

    if percent: format=format+'%%'
    T = []
    n = int(float(hi-t)/grid+0.1)+1
    if split:
        labels = []
        for i in range(n):
            v = t+grid*i
            T.append(v)
            labels.append(format % (v+labelVOffset))
        return T, labels
    else:
        for i in range(n):
            v = t+grid*i
            T.append((v, format % (v+labelVOffset)))
        return T

def findNones(data):
    m = len(data)
    if None in data:
        b = 0
        while b<m and data[b] is None:
            b += 1
        if b==m: return data
        l = m-1
        while data[l] is None:
            l -= 1
        l+=1
        if b or l: data = data[b:l]
        I = [i for i in range(len(data)) if data[i] is None]
        for i in I:
            data[i] = 0.5*(data[i-1]+data[i+1])
        return b, l, data
    return 0,m,data

def pairFixNones(pairs):
    Y = [x[1] for x in pairs]
    b,l,nY = findNones(Y)
    m = len(Y)
    if b or l<m or nY!=Y:
        if b or l<m: pairs = pairs[b:l]
        pairs = [(x[0],y) for x,y in zip(pairs,nY)]
    return pairs

def maverage(data,n=6):
    data = (n-1)*[data[0]]+data
    data = [float(sum(data[i-n:i]))/n for i in range(n,len(data)+1)]
    return data

def pairMaverage(data,n=6):
    return [(x[0],s) for x,s in zip(data, maverage([x[1] for x in data],n))]

class DrawTimeCollector:
    '''
    generic mechanism for collecting information about nodes at the time they are about to be drawn
    '''
    def __init__(self,formats=['gif']):
        self._nodes = weakref.WeakKeyDictionary()
        self.clear()
        self._pmcanv = None
        self.formats = formats
        self.disabled = False

    def clear(self):
        self._info = []
        self._info_append = self._info.append

    def record(self,func,node,*args,**kwds):
        self._nodes[node] = (func,args,kwds)
        node.__dict__['_drawTimeCallback'] = self

    def __call__(self,node,canvas,renderer):
        func = self._nodes.get(node,None)
        if func:
            func, args, kwds = func
            i = func(node,canvas,renderer, *args, **kwds)
            if i is not None: self._info_append(i)

    @staticmethod
    def rectDrawTimeCallback(node,canvas,renderer,**kwds):
        A = getattr(canvas,'ctm',None)
        if not A: return
        x1 = node.x
        y1 = node.y
        x2 = x1 + node.width
        y2 = y1 + node.height

        D = kwds.copy()
        D['rect']=DrawTimeCollector.transformAndFlatten(A,((x1,y1),(x2,y2)))
        return D

    @staticmethod
    def transformAndFlatten(A,p):
        ''' transform an flatten a list of points
        A   transformation matrix
        p   points [(x0,y0),....(xk,yk).....]
        '''
        if tuple(A)!=(1,0,0,1,0,0):
            iA = inverse(A)
            p = transformPoints(iA,p)
        return tuple(flatten(p))

    @property
    def pmcanv(self):
        if not self._pmcanv:
            import renderPM
            self._pmcanv = renderPM.PMCanvas(1,1)
        return self._pmcanv

    def wedgeDrawTimeCallback(self,node,canvas,renderer,**kwds):
        A = getattr(canvas,'ctm',None)
        if not A: return
        if isinstance(node,Ellipse):
            c = self.pmcanv
            c.ellipse(node.cx, node.cy, node.rx,node.ry)
            p = c.vpath
            p = [(x[1],x[2]) for x in p]
        else:
            p = node.asPolygon().points
            p = [(p[i],p[i+1]) for i in range(0,len(p),2)]

        D = kwds.copy()
        D['poly'] = self.transformAndFlatten(A,p)
        return D

    def save(self,fnroot):
        '''
        save the current information known to this collector
        fnroot is the root name of a resource to name the saved info
        override this to get the right semantics for your collector
        '''
        import pprint
        f=open(fnroot+'.default-collector.out','w')
        try:
            pprint.pprint(self._info,f)
        finally:
            f.close()

def xyDist(xxx_todo_changeme, xxx_todo_changeme1 ):
    '''return distance between two points'''
    (x0,y0) = xxx_todo_changeme
    (x1,y1) = xxx_todo_changeme1
    return hypot((x1-x0),(y1-y0))

def lineSegmentIntersect(xxx_todo_changeme2, xxx_todo_changeme3, xxx_todo_changeme4, xxx_todo_changeme5
                ):
    (x00,y00) = xxx_todo_changeme2
    (x01,y01) = xxx_todo_changeme3
    (x10,y10) = xxx_todo_changeme4
    (x11,y11) = xxx_todo_changeme5
    p = x00,y00
    r = x01-x00,y01-y00

    
    q = x10,y10
    s = x11-x10,y11-y10

    rs = float(r[0]*s[1]-r[1]*s[0])
    qp = q[0]-p[0],q[1]-p[1]

    qpr = qp[0]*r[1]-qp[1]*r[0]
    qps = qp[0]*s[1]-qp[1]*s[0]

    if abs(rs)<1e-8:
        if abs(qpr)<1e-8: return 'collinear'
        return None

    t = qps/rs
    u = qpr/rs

    if 0<=t<=1 and 0<=u<=1:
        return p[0]+t*r[0], p[1]+t*r[1]

def makeCircularString(x, y, radius, angle, text, fontName, fontSize, inside=0, G=None,textAnchor='start'):
    '''make a group with circular text in it'''
    if not G: G = Group()

    angle %= 360
    pi180 = pi/180
    phi = angle*pi180
    width = stringWidth(text, fontName, fontSize)
    sig = inside and -1 or 1
    hsig = sig*0.5
    sig90 = sig*90

    if textAnchor!='start':
        if textAnchor=='middle':
            phi += sig*(0.5*width)/radius
        elif textAnchor=='end':
            phi += sig*float(width)/radius
        elif textAnchor=='numeric':
            phi += sig*float(numericXShift(textAnchor,text,width,fontName,fontSize,None))/radius

    for letter in text:
        width = stringWidth(letter, fontName, fontSize)
        beta = float(width)/radius
        h = Group()
        h.add(String(0, 0, letter, fontName=fontName,fontSize=fontSize,textAnchor="start"))
        h.translate(x+cos(phi)*radius,y+sin(phi)*radius)    #translate to radius and angle
        h.rotate((phi-hsig*beta)/pi180-sig90)               # rotate as needed
        G.add(h)                                            #add to main group
        phi -= sig*beta                                     #increment

    return G

class CustomDrawChanger:
    '''
    a class to simplify making changes at draw time
    '''
    def __init__(self):
        self.store = None

    def __call__(self,change,obj):
        if change:
            self.store = self._changer(obj)
            assert isinstance(self.store,dict), '%s.changer should return a dict of changed attributes' % self.__class__.__name__
        elif self.store is not None:
            for a,v in self.store.items():
                setattr(obj,a,v)
            self.store = None

    def _changer(self,obj):
        '''
        When implemented this method should return a dictionary of
        original attribute values so that a future self(False,obj)
        can restore them.
        '''
        raise RuntimeError('Abstract method _changer called')

class FillPairedData(list):
    def __init__(self,v,other=0):
        list.__init__(self,v)
        self.other = other
