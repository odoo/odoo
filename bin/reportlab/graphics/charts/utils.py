#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/graphics/charts/utils.py
"Utilities used here and there."
__version__=''' $Id: utils.py 2385 2004-06-17 15:26:05Z rgbecker $ '''

from time import mktime, gmtime, strftime
import string


### Dinu's stuff used in some line plots (likely to vansih).

def mkTimeTuple(timeString):
    "Convert a 'dd/mm/yyyy' formatted string to a tuple for use in the time module."

    list = [0] * 9
    dd, mm, yyyy = map(int, string.split(timeString, '/'))
    list[:3] = [yyyy, mm, dd]

    return tuple(list)


def str2seconds(timeString):
    "Convert a number of seconds since the epoch into a date string."

    return mktime(mkTimeTuple(timeString))


def seconds2str(seconds):
    "Convert a date string into the number of seconds since the epoch."

    return strftime('%Y-%m-%d', gmtime(seconds))


### Aaron's rounding function for making nice values on axes.

from math import log10

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


### Robin's stuff from rgb_ticks.

from math import log10, floor

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
            raise ValueError, "lo>hi"
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
            n = xrange(max(1,n-2),max(n+3,2))

        w = 1e308
        for i in n:
            z=find_interval(lower,upper,i)
            if z[3]<w:
                t, hi, grid = z[:3]
                w=z[3]
    return t, hi, grid


def ticks(lower, upper, n=(4,5,6,7,8,9), split=1, percent=0, grid=None):
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
        format = '%+'+`w+7`+'.0e'
    else:
        if power >= 0:
            digits = int(power)+w
            format = '%' + `digits`+'.0f'
        else:
            digits = w-int(power)
            format = '%'+`digits+2`+'.'+`digits`+'f'

    if percent: format=format+'%%'
    T = []
    n = int(float(hi-t)/grid+0.1)+1
    if split:
        labels = []
        for i in xrange(n):
            v = t+grid*i
            T.append(v)
            labels.append(format % v)
        return T, labels
    else:
        for i in xrange(n):
            v = t+grid*i
            T.append((v, format % v))
        return T