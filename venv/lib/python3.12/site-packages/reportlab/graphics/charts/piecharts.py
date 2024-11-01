#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/graphics/charts/piecharts.py
# experimental pie chart script.  Two types of pie - one is a monolithic
#widget with all top-level properties, the other delegates most stuff to
#a wedges collection whic lets you customize the group or every individual
#wedge.

__version__='3.3.0'
__doc__="""Basic Pie Chart class.

This permits you to customize and pop out individual wedges;
supports elliptical and circular pies.
"""

import functools
from math import sin, cos, pi

from reportlab.lib import colors
from reportlab.lib.validators import isNumber, isListOfNumbersOrNone,\
                                    isListOfNumbers, isColorOrNone, isString,\
                                    isListOfStringsOrNone, OneOf,\
                                    isBoolean, isListOfColors, isNumberOrNone,\
                                    isNoneOrListOfNoneOrStrings, isTextAnchor,\
                                    isNoneOrListOfNoneOrNumbers, isBoxAnchor,\
                                    isStringOrNone, NoneOr, EitherOr,\
                                    isNumberInRange, isCallable
from reportlab.graphics.widgets.markers import uSymbol2Symbol, isSymbol
from reportlab.lib.attrmap import *
from reportlab.graphics.shapes import Group, Drawing, Ellipse, Wedge, String, STATE_DEFAULTS, ArcPath, Polygon, Rect, PolyLine, Line
from reportlab.graphics.widgetbase import TypedPropertyCollection, PropHolder
from reportlab.graphics.charts.areas import PlotArea
from reportlab.graphics.charts.legends import _objStr
from reportlab.graphics.charts.textlabels import Label
from reportlab import cmp

_ANGLE2BOXANCHOR={0:'w', 45:'sw', 90:'s', 135:'se', 180:'e', 225:'ne', 270:'n', 315: 'nw', -45: 'nw'}
_ANGLE2RBOXANCHOR={0:'e', 45:'ne', 90:'n', 135:'nw', 180:'w', 225:'sw', 270:'s', 315: 'se', -45: 'se'}

_ANGLELO    = 1e-7
_ANGLEHI    = 360.0 - _ANGLELO

class WedgeLabel(Label):
    def _checkDXY(self,ba):
        pass
    def _getBoxAnchor(self):
        ba = self.boxAnchor
        if ba in ('autox','autoy'):
            na = (int((self._pmv%360)/45.)*45)%360
            if not (na % 90): # we have a right angle case
                da = (self._pmv - na) % 360
                if abs(da)>5:
                    na += (da>0 and 45 or -45)
            ba = (getattr(self,'_anti',None) and _ANGLE2RBOXANCHOR or _ANGLE2BOXANCHOR)[na]
            self._checkDXY(ba)
        return ba

class WedgeProperties(PropHolder):
    """This holds descriptive information about the wedges in a pie chart.

    It is not to be confused with the 'wedge itself'; this just holds
    a recipe for how to format one, and does not allow you to hack the
    angles.  It can format a genuine Wedge object for you with its
    format method.
    """
    _attrMap = AttrMap(
        strokeWidth = AttrMapValue(isNumber,desc='Width of the wedge border'),
        fillColor = AttrMapValue(isColorOrNone,desc='Filling color of the wedge'),
        strokeColor = AttrMapValue(isColorOrNone,desc='Color of the wedge border'),
        strokeDashArray = AttrMapValue(isListOfNumbersOrNone,desc='Style of the wedge border, expressed as a list of lengths of alternating dashes and blanks'),
        strokeLineCap = AttrMapValue(OneOf(0,1,2),desc="Line cap 0=butt, 1=round & 2=square"),
        strokeLineJoin = AttrMapValue(OneOf(0,1,2),desc="Line join 0=miter, 1=round & 2=bevel"),
        strokeMiterLimit = AttrMapValue(isNumber,desc='Miter limit control miter line joins'),
        popout = AttrMapValue(isNumber,desc="How far of centre a wedge to pop"),
        fontName = AttrMapValue(isString,desc='Name of the font of the label text'),
        fontSize = AttrMapValue(isNumber,desc='Size of the font of the label text in points'),
        fontColor = AttrMapValue(isColorOrNone,desc='Color of the font of the label text'),
        labelRadius = AttrMapValue(isNumber,desc='Distance between the center of the label box and the center of the pie, expressed in times the radius of the pie'),
        label_dx = AttrMapValue(isNumber,desc='X Offset of the label'),
        label_dy = AttrMapValue(isNumber,desc='Y Offset of the label'),
        label_angle = AttrMapValue(isNumber,desc='Angle of the label, default (0) is horizontal, 90 is vertical, 180 is upside down'),
        label_boxAnchor = AttrMapValue(isBoxAnchor,desc='Anchoring point of the label'),
        label_boxStrokeColor = AttrMapValue(isColorOrNone,desc='Border color for the label box'),
        label_boxStrokeWidth = AttrMapValue(isNumber,desc='Border width for the label box'),
        label_boxFillColor = AttrMapValue(isColorOrNone,desc='Filling color of the label box'),
        label_strokeColor = AttrMapValue(isColorOrNone,desc='Border color for the label text'),
        label_strokeWidth = AttrMapValue(isNumber,desc='Border width for the label text'),
        label_text = AttrMapValue(isStringOrNone,desc='Text of the label'),
        label_leading = AttrMapValue(isNumberOrNone,desc=''),
        label_width = AttrMapValue(isNumberOrNone,desc='Width of the label'),
        label_maxWidth = AttrMapValue(isNumberOrNone,desc='Maximum width the label can grow to'),
        label_height = AttrMapValue(isNumberOrNone,desc='Height of the label'),
        label_textAnchor = AttrMapValue(isTextAnchor,desc='Maximum height the label can grow to'),
        label_visible = AttrMapValue(isBoolean,desc="True if the label is to be drawn"),
        label_topPadding = AttrMapValue(isNumber,'Padding at top of box'),
        label_leftPadding = AttrMapValue(isNumber,'Padding at left of box'),
        label_rightPadding = AttrMapValue(isNumber,'Padding at right of box'),
        label_bottomPadding = AttrMapValue(isNumber,'Padding at bottom of box'),
        label_simple_pointer = AttrMapValue(isBoolean,'Set to True for simple pointers'),
        label_pointer_strokeColor = AttrMapValue(isColorOrNone,desc='Color of indicator line'),
        label_pointer_strokeWidth = AttrMapValue(isNumber,desc='StrokeWidth of indicator line'),
        label_pointer_elbowLength = AttrMapValue(isNumber,desc='Length of final indicator line segment'),
        label_pointer_edgePad = AttrMapValue(isNumber,desc='pad between pointer label and box'),
        label_pointer_piePad = AttrMapValue(isNumber,desc='pad between pointer label and pie'),
        swatchMarker = AttrMapValue(NoneOr(isSymbol), desc="None or makeMarker('Diamond') ...",advancedUsage=1),
        visible = AttrMapValue(isBoolean,'Set to false to skip displaying'),
        shadingAmount = AttrMapValue(isNumberOrNone,desc='amount by which to shade fillColor'),
        shadingAngle = AttrMapValue(isNumber,desc='shading changes at multiple of this angle (in degrees)'),
        shadingDirection = AttrMapValue(OneOf('normal','anti'),desc="Whether shading is at start or end of wedge/sector"),
        shadingKind = AttrMapValue(OneOf(None,'lighten','darken'),desc="use colors.Whiter or Blacker"),
        )

    def __init__(self):
        self.strokeWidth = 0
        self.fillColor = None
        self.strokeColor = STATE_DEFAULTS["strokeColor"]
        self.strokeDashArray = STATE_DEFAULTS["strokeDashArray"]
        self.strokeLineJoin = 1
        self.strokeLineCap = 0
        self.strokeMiterLimit = 0
        self.popout = 0
        self.fontName = STATE_DEFAULTS["fontName"]
        self.fontSize = STATE_DEFAULTS["fontSize"]
        self.fontColor = STATE_DEFAULTS["fillColor"]
        self.labelRadius = 1.2
        self.label_dx = self.label_dy = self.label_angle = 0
        self.label_text = None
        self.label_topPadding = self.label_leftPadding = self.label_rightPadding = self.label_bottomPadding = 0
        self.label_boxAnchor = 'autox'
        self.label_boxStrokeColor = None    #boxStroke
        self.label_boxStrokeWidth = 0.5 #boxStrokeWidth
        self.label_boxFillColor = None
        self.label_strokeColor = None
        self.label_strokeWidth = 0.1
        self.label_leading =    self.label_width = self.label_maxWidth = self.label_height = None
        self.label_textAnchor = 'start'
        self.label_simple_pointer = 0
        self.label_visible = 1
        self.label_pointer_strokeColor = colors.black
        self.label_pointer_strokeWidth = 0.5
        self.label_pointer_elbowLength = 3
        self.label_pointer_edgePad = 2
        self.label_pointer_piePad = 3
        self.visible = 1
        self.shadingKind = None
        self.shadingAmount = 0.5
        self.shadingAngle = 2.0137
        self.shadingDirection = 'normal'    #or 'anti'

def _addWedgeLabel(self,text,angle,labelX,labelY,wedgeStyle,labelClass=None):
    # now draw a label
    if self.simpleLabels:
        theLabel = String(labelX, labelY, text)
        if not self.sideLabels:
            theLabel.textAnchor = "middle"
        else:
            if (abs(angle) < 90 ) or (angle >270 and angle<450) or (-450< angle <-270):
                theLabel.textAnchor = "start"
            else:
                theLabel.textAnchor = "end"
        theLabel._pmv = angle
        theLabel._simple_pointer = 0
    else:
        if labelClass is None:
            labelClass = getattr(self,'labelClass',WedgeLabel)
        theLabel = labelClass()
        theLabel._pmv = angle
        theLabel.x = labelX
        theLabel.y = labelY
        theLabel.dx = wedgeStyle.label_dx
        if not self.sideLabels:
            theLabel.dy = wedgeStyle.label_dy
            theLabel.boxAnchor = wedgeStyle.label_boxAnchor
        else:
            if wedgeStyle.fontSize is None:
                sideLabels_dy = self.fontSize / 2.5
            else:
                sideLabels_dy = wedgeStyle.fontSize / 2.5
            if wedgeStyle.label_dy is None:
                theLabel.dy = sideLabels_dy
            else:
                theLabel.dy = wedgeStyle.label_dy + sideLabels_dy
            if (abs(angle) < 90 ) or (angle >270 and angle<450) or (-450< angle <-270):
                theLabel.boxAnchor = 'w'
            else:
                theLabel.boxAnchor = 'e'
        theLabel.angle = wedgeStyle.label_angle
        theLabel.boxStrokeColor = wedgeStyle.label_boxStrokeColor
        theLabel.boxStrokeWidth = wedgeStyle.label_boxStrokeWidth
        theLabel.boxFillColor = wedgeStyle.label_boxFillColor
        theLabel.strokeColor = wedgeStyle.label_strokeColor
        theLabel.strokeWidth = wedgeStyle.label_strokeWidth
        _text = wedgeStyle.label_text
        if _text is None: _text = text
        theLabel._text = _text
        theLabel.leading = wedgeStyle.label_leading
        theLabel.width = wedgeStyle.label_width
        theLabel.maxWidth = wedgeStyle.label_maxWidth
        theLabel.height = wedgeStyle.label_height
        theLabel.textAnchor = wedgeStyle.label_textAnchor
        theLabel.visible = wedgeStyle.label_visible
        theLabel.topPadding = wedgeStyle.label_topPadding
        theLabel.leftPadding = wedgeStyle.label_leftPadding
        theLabel.rightPadding = wedgeStyle.label_rightPadding
        theLabel.bottomPadding = wedgeStyle.label_bottomPadding
        theLabel._simple_pointer = wedgeStyle.label_simple_pointer
    theLabel.fontSize = wedgeStyle.fontSize
    theLabel.fontName = wedgeStyle.fontName
    theLabel.fillColor = wedgeStyle.fontColor
    return theLabel

def _fixLabels(labels,n):
    if labels is None:
        labels = [''] * n
    else:
        i = n-len(labels)
        if i>0: labels = list(labels)+['']*i
    return labels

class AbstractPieChart(PlotArea):

    def makeSwatchSample(self, rowNo, x, y, width, height):
        baseStyle = self.slices
        styleIdx = rowNo % len(baseStyle)
        style = baseStyle[styleIdx]
        strokeColor = getattr(style, 'strokeColor', getattr(baseStyle,'strokeColor',None))
        fillColor = getattr(style, 'fillColor', getattr(baseStyle,'fillColor',None))
        strokeDashArray = getattr(style, 'strokeDashArray', getattr(baseStyle,'strokeDashArray',None))
        strokeWidth = getattr(style, 'strokeWidth', getattr(baseStyle, 'strokeWidth',None))
        swatchMarker = getattr(style, 'swatchMarker', getattr(baseStyle, 'swatchMarker',None))
        if swatchMarker:
            return uSymbol2Symbol(swatchMarker,x+width/2.,y+height/2.,fillColor)
        return Rect(x,y,width,height,strokeWidth=strokeWidth,strokeColor=strokeColor,
                    strokeDashArray=strokeDashArray,fillColor=fillColor)

    def getSeriesName(self,i,default=None):
        '''return series name i or default'''
        try:
            text = _objStr(self.labels[i])
        except:
            text = default
        if not self.simpleLabels:
            _text = getattr(self.slices[i],'label_text','')
            if _text is not None: text = _text
        return text

def boundsOverlap(P,Q):
    return not(P[0]>Q[2]-1e-2 or Q[0]>P[2]-1e-2 or P[1]>(0.5*(Q[1]+Q[3]))-1e-2 or Q[1]>(0.5*(P[1]+P[3]))-1e-2)

def _findOverlapRun(B,i,wrap):
    '''find overlap run containing B[i]'''
    n = len(B)
    R = [i]
    while 1:
        i = R[-1]
        j = (i+1)%n
        if j in R or not boundsOverlap(B[i],B[j]): break
        R.append(j)
    while 1:
        i = R[0]
        j = (i-1)%n
        if j in R or not boundsOverlap(B[i],B[j]): break
        R.insert(0,j)
    return R

def findOverlapRun(B,wrap=1):
    '''determine a set of overlaps in bounding boxes B or return None'''
    n = len(B)
    if n>1:
        for i in range(n-1):
            R = _findOverlapRun(B,i,wrap)
            if len(R)>1: return R
    return None

def fixLabelOverlaps(L, sideLabels=False, mult0=1.0):
    nL = len(L)
    if nL<2: return
    B = [l._origdata['bounds'] for l in L]
    OK = 1
    RP = []
    iter = 0
    mult0 = float(mult0 + 0)
    mult = mult0

    if not sideLabels:
        while iter<30:
            R = findOverlapRun(B)
            if not R: break
            nR = len(R)
            if nR==nL: break
            if not [r for r in RP if r in R]:
                mult = mult0
            da = 0
            r0 = R[0]
            rL = R[-1]
            bi = B[r0]
            taa = aa = _360(L[r0]._pmv)
            for r in R[1:]:
                b = B[r]
                da = max(da,min(b[2]-bi[0],bi[2]-b[0]))
                bi = b
                aa += L[r]._pmv
            aa = aa/float(nR)
            utaa = abs(L[rL]._pmv-taa)
            ntaa = _360(utaa)
            da *= mult*(nR-1)/ntaa
    
            for r in R:
                l = L[r]
                orig = l._origdata
                angle = l._pmv = _360(l._pmv+da*(_360(l._pmv)-aa))
                rad = angle/_180_pi
                l.x = orig['cx'] + orig['rx']*cos(rad)
                l.y = orig['cy'] + orig['ry']*sin(rad)
                B[r] = l.getBounds()
            RP = R
            mult *= 1.05
            iter += 1

    else:
        while iter<30:
            R = findOverlapRun(B)
            if not R: break
            nR = len(R)
            if nR == nL: break
            l1 = L[-1]
            orig1 = l1._origdata
            bounds1 = orig1['bounds']
            for i,r in enumerate(R):
                l = L[r]
                orig = l._origdata
                bounds = orig['bounds']
                diff1 = 0
                diff2 = 0
                if not i == nR-1:
                    if not bounds == bounds1:
                        if bounds[3]>bounds1[1] and bounds1[1]<bounds[1]:
                            diff1 = bounds[3]-bounds1[1]
                        if bounds1[3]>bounds[1] and bounds[1]<bounds1[1]:
                            diff2 = bounds1[3]-bounds[1]
                        if diff1 > diff2: 
                            l.y +=0.5*(bounds1[3]-bounds1[1])
                        elif diff2 >= diff1:
                            l.y -= 0.5*(bounds1[3]-bounds1[1])
                    B[r] = l.getBounds()
            iter += 1
    
def intervalIntersection(A,B):
    x,y = max(min(A),min(B)),min(max(A),max(B))
    if x>=y: return None
    return x,y

def _makeSideArcDefs(sa,direction):
    sa %= 360
    if 90<=sa<270:
        if direction=='clockwise':
            a = (0,90,sa),(1,-90,90),(0,-360+sa,-90)
        else:
            a = (0,sa,270),(1,270,450),(0,450,360+sa)
    else:
        offs = sa>=270 and 360 or 0
        if direction=='clockwise':
            a = (1,offs-90,sa),(0,offs-270,offs-90),(1,-360+sa,offs-270)
        else:
            a = (1,sa,offs+90),(0,offs+90,offs+270),(1,offs+270,360+sa)
    return tuple([a for a in a if a[1]<a[2]])

def _keyFLA(x,y):
    return cmp(y[1]-y[0],x[1]-x[0])
_keyFLA = functools.cmp_to_key(_keyFLA)

def _findLargestArc(xArcs,side):
    a = [a[1] for a in xArcs if a[0]==side and a[1] is not None]
    if not a: return None
    if len(a)>1: a.sort(key=_keyFLA)
    return a[0]

def _fPLSide(l,width,side=None):
    data = l._origdata
    if side is None:
        li = data['li']
        ri = data['ri']
        if li is None:
            side = 1
            i = ri
        elif ri is None:
            side = 0
            i = li
        elif li[1]-li[0]>ri[1]-ri[0]:
            side = 0
            i = li
        else:
            side = 1
            i = ri
    w = data['width']
    edgePad = data['edgePad']
    if not side:    #on left
        l._pmv = 180
        l.x = edgePad+w
        i = data['li']
    else:
        l._pmv = 0
        l.x = width - w - edgePad
        i = data['ri']
    mid = data['mid'] = (i[0]+i[1])*0.5
    data['smid'] = sin(mid/_180_pi)
    data['cmid'] = cos(mid/_180_pi)
    data['side'] = side
    return side,w

#key functions
def _fPLCF(a,b): 
    return cmp(b._origdata['smid'],a._origdata['smid'])
_fPLCF = functools.cmp_to_key(_fPLCF)

def _arcCF(a):
    return a[1]

def _fixPointerLabels(n,L,x,y,width,height,side=None):
    LR = [],[]
    mlr = [0,0]
    for l in L:
        i,w = _fPLSide(l,width,side)
        LR[i].append(l)
        mlr[i] = max(w,mlr[i])
    mul = 1
    G = n*[None]
    mel = 0
    hh = height*0.5
    yhh = y+hh
    m = max(mlr)
    for i in (0,1):
        T = LR[i]
        if T:
            B = []
            aB = B.append
            S = []
            aS = S.append
            T.sort(key=_fPLCF)
            p = 0
            yh = y+height
            for l in T:
                data = l._origdata
                inc = x+mul*(m-data['width'])
                l.x += inc
                G[data['index']] = l
                ly = yhh+data['smid']*hh
                b = data['bounds']
                b2 = (b[3]-b[1])*0.5
                if ly+b2>yh: ly = yh-b2
                if ly-b2<y: ly = y+b2
                data['bounds'] = b = (b[0],ly-b2,b[2],ly+b2)
                aB(b)
                l.y = ly
                aS(max(0,yh-ly-b2))
                yh = ly-b2
                p = max(p,data['edgePad']+data['piePad'])
                mel = max(mel,abs(data['smid']*(hh+data['elbowLength']))-hh)
            aS(yh-y)

            iter = 0
            nT = len(T)
            while iter<30:
                R = findOverlapRun(B,wrap=0)
                if not R: break
                nR = len(R)
                if nR==nT: break
                j0 = R[0]
                j1 = R[-1]
                jl = j1+1
                sAbove = sum(S[:j0+1])
                sFree = sAbove+sum(S[jl:])
                sNeed = sum([b[3]-b[1] for b in B[j0:jl]])+jl-j0-(B[j0][3]-B[j1][1])
                if sNeed>sFree: break
                yh = B[j0][3]+sAbove*sNeed/sFree
                for r in R:
                    l = T[r]
                    data = l._origdata
                    b = data['bounds']
                    b2 = (b[3]-b[1])*0.5
                    yh -= 0.5
                    ly = l.y = yh-b2
                    B[r] = data['bounds'] = (b[0],ly-b2,b[2],yh)
                    yh = ly - b2 - 0.5
            mlr[i] = m+p
        mul = -1
    return G, mlr[0], mlr[1], mel

def theta0(data, direction):
    fac = (2*pi)/sum(data)
    rads = [d*fac for d in data]
    
    r0 = 0
    hrads = []
    for r in rads:
        hrads.append(r0+r*0.5)
        r0 += r
    
    vstar = len(data)*1e6
    rstar = 0
    delta = pi/36.0
    for i in range(36):
        r = i*delta
        v = sum([abs(sin(r+a)) for a in hrads])
        if v < vstar:
            if direction == 'clockwise':
                rstar=-r
            else:
                rstar=r
            vstar = v
    return rstar*180/pi


class AngleData(float):
    '''use this to carry the data along with the angle'''
    def __new__(cls,angle,data):
        self = float.__new__(cls,angle)
        self._data = data
        return self

class Pie(AbstractPieChart):
    _attrMap = AttrMap(BASE=AbstractPieChart,
        data = AttrMapValue(isListOfNumbers, desc='List of numbers defining wedge sizes; need not sum to 1'),
        labels = AttrMapValue(isListOfStringsOrNone, desc="Optional list of labels to use for each data point"),
        startAngle = AttrMapValue(isNumber, desc="Angle of first slice; 0 is due East"),
        direction = AttrMapValue(OneOf('clockwise', 'anticlockwise'), desc="'clockwise' or 'anticlockwise'"),
        slices = AttrMapValue(None, desc="Collection of wedge descriptor objects"),
        simpleLabels = AttrMapValue(isBoolean, desc="If true(default) use a simple String not an advanced WedgeLabel. A WedgeLabel is customisable using the properties prefixed label_ in the collection slices."),
        other_threshold = AttrMapValue(isNumber, desc='A value for doing threshholding, not used yet.',advancedUsage=1),
        checkLabelOverlap = AttrMapValue(EitherOr((isNumberInRange(0.05,1),isBoolean)), desc="If true check and attempt to fix\n standard label overlaps(default off)",advancedUsage=1),
        pointerLabelMode = AttrMapValue(OneOf(None,'LeftRight','LeftAndRight'), desc='',advancedUsage=1),
        sameRadii = AttrMapValue(isBoolean, desc="If true make x/y radii the same(default off)",advancedUsage=1),
        orderMode = AttrMapValue(OneOf('fixed','alternate'),advancedUsage=1),
        xradius = AttrMapValue(isNumberOrNone, desc="X direction Radius"),
        yradius = AttrMapValue(isNumberOrNone, desc="Y direction Radius"),
        innerRadiusFraction = AttrMapValue(isNumberOrNone, desc="fraction of radii to start wedges at"),
        wedgeRecord = AttrMapValue(None, desc="callable(wedge,*args,**kwds)",advancedUsage=1),
        sideLabels = AttrMapValue(isBoolean, desc="If true attempt to make piechart with labels along side and pointers"),
        sideLabelsOffset = AttrMapValue(isNumber, desc="The fraction of the pie width that the labels are situated at from the edges of the pie"),
        labelClass=AttrMapValue(NoneOr(isCallable), desc="A class factory to use for non simple labels"),
        )
    other_threshold=None

    def __init__(self,**kwd):
        PlotArea.__init__(self)
        self.x = 0
        self.y = 0
        self.width = 100
        self.height = 100
        self.data = [1,2.3,1.7,4.2]
        self.labels = None  # or list of strings
        self.startAngle = 90
        self.direction = "clockwise"
        self.simpleLabels = 1
        self.checkLabelOverlap = 0
        self.pointerLabelMode = None
        self.sameRadii = False
        self.orderMode = 'fixed'
        self.xradius = self.yradius = self.innerRadiusFraction = None
        self.sideLabels = 0
        self.sideLabelsOffset = 0.1

        self.slices = TypedPropertyCollection(WedgeProperties)
        self.slices[0].fillColor = colors.darkcyan
        self.slices[1].fillColor = colors.blueviolet
        self.slices[2].fillColor = colors.blue
        self.slices[3].fillColor = colors.cyan
        self.slices[4].fillColor = colors.pink
        self.slices[5].fillColor = colors.magenta
        self.slices[6].fillColor = colors.yellow

    def demo(self):
        d = Drawing(200, 100)

        pc = Pie()
        pc.x = 50
        pc.y = 10
        pc.width = 100
        pc.height = 80
        pc.data = [10,20,30,40,50,60]
        pc.labels = ['a','b','c','d','e','f']

        pc.slices.strokeWidth=0.5
        pc.slices[3].popout = 10
        pc.slices[3].strokeWidth = 2
        pc.slices[3].strokeDashArray = [2,2]
        pc.slices[3].labelRadius = 1.75
        pc.slices[3].fontColor = colors.red
        pc.slices[0].fillColor = colors.darkcyan
        pc.slices[1].fillColor = colors.blueviolet
        pc.slices[2].fillColor = colors.blue
        pc.slices[3].fillColor = colors.cyan
        pc.slices[4].fillColor = colors.aquamarine
        pc.slices[5].fillColor = colors.cadetblue
        pc.slices[6].fillColor = colors.lightcoral

        d.add(pc)
        return d

    def makePointerLabels(self,angles,plMode):
        class PL:
            def __init__(self,centerx,centery,xradius,yradius,data,lu=0,ru=0):
                self.centerx = centerx
                self.centery = centery
                self.xradius = xradius
                self.yradius = yradius
                self.data = data
                self.lu = lu
                self.ru = ru

        labelX = self.width-2
        labelY = self.height
        n = nr = nl = maxW = sumH = 0
        styleCount = len(self.slices)
        L=[]
        L_add = L.append
        refArcs = _makeSideArcDefs(self.startAngle,self.direction)
        for i, A in angles:
            if A[1] is None: continue
            sn = self.getSeriesName(i,'')
            if not sn: continue
            style = self.slices[i%styleCount]
            if not style.label_visible or not style.visible: continue
            n += 1
            l=_addWedgeLabel(self,sn,180,labelX,labelY,style)
            L_add(l)
            b = l.getBounds()
            w = b[2]-b[0]
            h = b[3]-b[1]
            ri = [(a[0],intervalIntersection(A,(a[1],a[2]))) for a in refArcs]
            li = _findLargestArc(ri,0)
            ri = _findLargestArc(ri,1)
            if li and ri:
                if plMode=='LeftAndRight':
                    if li[1]-li[0]<ri[1]-ri[0]:
                        li = None
                    else:
                        ri = None
                else:
                    if li[1]-li[0]<0.02*(ri[1]-ri[0]):
                        li = None
                    elif (li[1]-li[0])*0.02>ri[1]-ri[0]:
                        ri = None
            if ri: nr += 1
            if li: nl += 1
            l._origdata = dict(bounds=b,width=w,height=h,li=li,ri=ri,index=i,edgePad=style.label_pointer_edgePad,piePad=style.label_pointer_piePad,elbowLength=style.label_pointer_elbowLength)
            maxW = max(w,maxW)
            sumH += h+2

        if not n:   #we have no labels
            xradius = self.width*0.5
            yradius = self.height*0.5
            centerx = self.x+xradius
            centery = self.y+yradius
            if self.xradius: xradius = self.xradius
            if self.yradius: yradius = self.yradius
            if self.sameRadii: xradius=yradius=min(xradius,yradius)
            return PL(centerx,centery,xradius,yradius,[])

        aonR = nr==n
        if sumH<self.height and (aonR or nl==n):
            side=int(aonR)
        else:
            side=None
        G,lu,ru,mel = _fixPointerLabels(len(angles),L,self.x,self.y,self.width,self.height,side=side)
        if plMode=='LeftAndRight':
            lu = ru = max(lu,ru)
        x0 = self.x+lu
        x1 = self.x+self.width-ru
        xradius = (x1-x0)*0.5
        yradius = self.height*0.5-mel
        centerx = x0+xradius
        centery = self.y+yradius+mel
        if self.xradius: xradius = self.xradius
        if self.yradius: yradius = self.yradius
        if self.sameRadii: xradius=yradius=min(xradius,yradius)
        return PL(centerx,centery,xradius,yradius,G,lu,ru)

    def normalizeData(self,keepData=False):
        data = list(map(abs,self.data))
        s = self._sum = float(sum(data))
        f = 360./s if s!=0 else 1
        if keepData:
            return [AngleData(f*x,x) for x in data]
        else:
            return [f*x for x in data]

    def makeAngles(self):
        wr = getattr(self,'wedgeRecord',None)
        if self.sideLabels:
            startAngle = theta0(self.data, self.direction)
            self.slices.label_visible = 1
        else:
            startAngle = self.startAngle % 360
        whichWay = self.direction == "clockwise" and -1 or 1
        D = [a for a in enumerate(self.normalizeData(keepData=wr))]
        if self.orderMode=='alternate' and not self.sideLabels:
            W = [a for a in D if abs(a[1])>=1e-5]
            W.sort(key=_arcCF)
            T = [[],[]]
            i = 0
            while W:
                if i<2:
                    a = W.pop(0)
                else:
                    a = W.pop(-1)
                T[i%2].append(a)
                i += 1
                i %= 4
            T[1].reverse()
            D = T[0]+T[1] + [a for a in D if abs(a[1])<1e-5]
        A = []
        a = A.append
        for i, angle in D:
            endAngle = (startAngle + (angle * whichWay))
            if abs(angle)>=_ANGLELO:
                if startAngle >= endAngle:
                    aa = endAngle,startAngle
                else:
                    aa = startAngle,endAngle
            else:
                aa = startAngle, None
            if wr:
                aa = (AngleData(aa[0],angle._data),aa[1])
            startAngle = endAngle
            a((i,aa))
        return A

    def makeWedges(self):
        angles = self.makeAngles()
        #Checking to see whether there are too many wedges packed in too small a space
        halfAngles = []
        for i,(a1,a2) in angles:
            if a2 is None:
                halfAngle = a1
            else:
                halfAngle = 0.5*(a2+a1)
            halfAngles.append(halfAngle)
        sideLabels = self.sideLabels
        n = len(angles)
        labels = _fixLabels(self.labels,n)
        wr = getattr(self,'wedgeRecord',None)

        self._seriesCount = n
        styleCount = len(self.slices)

        plMode = self.pointerLabelMode
        if sideLabels:
            plMode = None
        if plMode:
            checkLabelOverlap = False
            PL=self.makePointerLabels(angles,plMode)
            xradius = PL.xradius
            yradius = PL.yradius
            centerx = PL.centerx
            centery = PL.centery
            PL_data = PL.data
            gSN = lambda i: ''
        else:
            xradius = self.width*0.5
            yradius = self.height*0.5
            centerx = self.x + xradius
            centery = self.y + yradius
            if self.xradius: xradius = self.xradius
            if self.yradius: yradius = self.yradius
            if self.sameRadii: xradius=yradius=min(xradius,yradius)
            checkLabelOverlap = self.checkLabelOverlap
            gSN = lambda i: self.getSeriesName(i,'')

        g = Group()
        g_add = g.add
        L = []
        L_add = L.append

        innerRadiusFraction = self.innerRadiusFraction


        for i,(a1,a2) in angles:
            if a2 is None: continue
            #if we didn't use %stylecount here we'd end up with the later wedges
            #all having the default style
            wedgeStyle = self.slices[i%styleCount]
            if not wedgeStyle.visible: continue
            aa = abs(a2-a1)

            # is it a popout?
            cx, cy = centerx, centery
            text = gSN(i)
            popout = wedgeStyle.popout
            if text or popout:
                averageAngle = (a1+a2)/2.0
                aveAngleRadians = averageAngle/_180_pi
                cosAA = cos(aveAngleRadians)
                sinAA = sin(aveAngleRadians)
                if popout and aa<_ANGLEHI:
                    # pop out the wedge
                    cx = centerx + popout*cosAA
                    cy = centery + popout*sinAA

            if innerRadiusFraction:
                theWedge = Wedge(cx, cy, xradius, a1, a2, yradius=yradius,
                        radius1=xradius*innerRadiusFraction,yradius1=yradius*innerRadiusFraction)
            else:
                if aa>=_ANGLEHI:
                    theWedge = Ellipse(cx, cy, xradius, yradius)
                else:
                    theWedge = Wedge(cx, cy, xradius, a1, a2, yradius=yradius)


            theWedge.fillColor = wedgeStyle.fillColor
            theWedge.strokeColor = wedgeStyle.strokeColor
            theWedge.strokeWidth = wedgeStyle.strokeWidth
            theWedge.strokeLineJoin = wedgeStyle.strokeLineJoin
            theWedge.strokeLineCap = wedgeStyle.strokeLineCap
            theWedge.strokeMiterLimit = wedgeStyle.strokeMiterLimit
            theWedge.strokeDashArray = wedgeStyle.strokeDashArray

            shader = wedgeStyle.shadingKind
            if shader:
                nshades = aa / float(wedgeStyle.shadingAngle)
                if nshades > 1:
                    shader = colors.Whiter if shader=='lighten' else colors.Blacker
                    nshades = 1+int(nshades)
                    shadingAmount = 1-wedgeStyle.shadingAmount
                    if wedgeStyle.shadingDirection=='normal':
                        dsh = (1-shadingAmount)/float(nshades-1)
                        shf1 = shadingAmount
                    else:
                        dsh = (shadingAmount-1)/float(nshades-1)
                        shf1 = 1
                    shda = (a2-a1)/float(nshades)
                    shsc = wedgeStyle.fillColor
                    theWedge.fillColor = None
                    for ish in range(nshades):
                        sha1 = a1 + ish*shda
                        sha2 = a1 + (ish+1)*shda
                        shc = shader(shsc,shf1 + dsh*ish)
                        if innerRadiusFraction:
                            shWedge = Wedge(cx, cy, xradius, sha1, sha2, yradius=yradius,
                                    radius1=xradius*innerRadiusFraction,yradius1=yradius*innerRadiusFraction)
                        else:
                            shWedge = Wedge(cx, cy, xradius, sha1, sha2, yradius=yradius)
                        shWedge.fillColor = shc
                        shWedge.strokeColor = None
                        shWedge.strokeWidth = 0
                        g_add(shWedge)

            g_add(theWedge)
            if wr:
                wr(theWedge,value=a1._data,label=text)
            if wedgeStyle.label_visible:
                if not sideLabels:
                    if text:
                        labelRadius = wedgeStyle.labelRadius
                        rx = xradius*labelRadius
                        ry = yradius*labelRadius
                        labelX = cx + rx*cosAA
                        labelY = cy + ry*sinAA
                        l = _addWedgeLabel(self,text,averageAngle,labelX,labelY,wedgeStyle)
                        L_add(l)
                        if not plMode and l._simple_pointer:
                            l._aax = cx+xradius*cosAA
                            l._aay = cy+yradius*sinAA
                        if checkLabelOverlap:
                            l._origdata = { 'x': labelX, 'y':labelY, 'angle': averageAngle,
                                            'rx': rx, 'ry':ry, 'cx':cx, 'cy':cy,
                                            'bounds': l.getBounds(), 'angles':(a1,a2),
                                            }
                    elif plMode and PL_data:
                        l = PL_data[i]
                        if l:
                            data = l._origdata
                            sinM = data['smid']
                            cosM = data['cmid']
                            lX = cx + xradius*cosM
                            lY = cy + yradius*sinM
                            lpel = wedgeStyle.label_pointer_elbowLength
                            lXi = lX + lpel*cosM
                            lYi = lY + lpel*sinM
                            L_add(PolyLine((lX,lY,lXi,lYi,l.x,l.y),
                                    strokeWidth=wedgeStyle.label_pointer_strokeWidth,
                                    strokeColor=wedgeStyle.label_pointer_strokeColor))
                            L_add(l)
                else:
                    if text:
                        slices_popout = self.slices.popout
                        m=0
                        for n, angle in angles:
                            if self.slices[n].fillColor:
                                m += 1
                            else:
                                r = n%m
                                self.slices[n].fillColor = self.slices[r].fillColor
                                self.slices[n].popout = self.slices[r].popout
                        for j in range(0,m-1):
                            if self.slices[j].popout > slices_popout:
                                slices_popout = self.slices[j].popout
                        labelRadius = wedgeStyle.labelRadius
                        ry = yradius*labelRadius
                        if (abs(averageAngle) < 90 ) or (averageAngle >270 and averageAngle <450) or (-450< 
                                averageAngle <-270):
                            labelX = (1+self.sideLabelsOffset)*self.width + self.x + slices_popout
                            rx = 0
                        else:
                            labelX = self.x - (self.sideLabelsOffset)*self.width - slices_popout
                            rx = 0
                        labelY = cy + ry*sinAA
                        l = _addWedgeLabel(self,text,averageAngle,labelX,labelY,wedgeStyle)
                        L_add(l)
                        if not plMode:
                            l._aax = cx+xradius*cosAA
                            l._aay = cy+yradius*sinAA
                        if checkLabelOverlap:
                            l._origdata = { 'x': labelX, 'y':labelY, 'angle': averageAngle,
                                            'rx': rx, 'ry':ry, 'cx':cx, 'cy':cy,
                                            'bounds': l.getBounds(),
                                            }
                        x1,y1,x2,y2 = l.getBounds()
        
        if checkLabelOverlap and L:
            fixLabelOverlaps(L, sideLabels, mult0=checkLabelOverlap)
        for l in L: g_add(l)

        if not plMode:
            for l in L:
                if l._simple_pointer and not sideLabels:
                    g_add(Line(l.x,l.y,l._aax,l._aay,
                        strokeWidth=wedgeStyle.label_pointer_strokeWidth,
                        strokeColor=wedgeStyle.label_pointer_strokeColor))
                elif sideLabels:
                    x1,y1,x2,y2 = l.getBounds()
                    #add pointers
                    if l.x == (1+self.sideLabelsOffset)*self.width + self.x:
                        g_add(Line(l._aax,l._aay,0.5*(l._aax+l.x),l.y+(0.25*(y2-y1)),
                            strokeWidth=wedgeStyle.label_pointer_strokeWidth,
                            strokeColor=wedgeStyle.label_pointer_strokeColor))
                        g_add(Line(0.5*(l._aax+l.x),l.y+(0.25*(y2-y1)),l.x,l.y+(0.25*(y2-y1)),
                            strokeWidth=wedgeStyle.label_pointer_strokeWidth,
                            strokeColor=wedgeStyle.label_pointer_strokeColor))
                    else:
                        g_add(Line(l._aax,l._aay,0.5*(l._aax+l.x),l.y+(0.25*(y2-y1)),
                            strokeWidth=wedgeStyle.label_pointer_strokeWidth,
                            strokeColor=wedgeStyle.label_pointer_strokeColor))
                        g_add(Line(0.5*(l._aax+l.x),l.y+(0.25*(y2-y1)),l.x,l.y+(0.25*(y2-y1)),
                            strokeWidth=wedgeStyle.label_pointer_strokeWidth,
                            strokeColor=wedgeStyle.label_pointer_strokeColor))

        return g

    def draw(self):
        G = self.makeBackground()
        w = self.makeWedges()
        if G: return Group(G,w)
        return w

class LegendedPie(Pie):
    """Pie with a two part legend (one editable with swatches, one hidden without swatches)."""

    _attrMap = AttrMap(BASE=Pie,
        drawLegend = AttrMapValue(isBoolean, desc="If true then create and draw legend"),
        legend1 = AttrMapValue(None, desc="Handle to legend for pie"),
        legendNumberFormat = AttrMapValue(None, desc="Formatting routine for number on right hand side of legend."),
        legendNumberOffset = AttrMapValue(isNumber, desc="Horizontal space between legend and numbers on r/hand side"),
        pieAndLegend_colors = AttrMapValue(isListOfColors, desc="Colours used for both swatches and pie"),
        legend_names = AttrMapValue(isNoneOrListOfNoneOrStrings, desc="Names used in legend (or None)"),
        legend_data = AttrMapValue(isNoneOrListOfNoneOrNumbers, desc="Numbers used on r/hand side of legend (or None)"),
        leftPadding = AttrMapValue(isNumber, desc='Padding on left of drawing'),
        rightPadding = AttrMapValue(isNumber, desc='Padding on right of drawing'),
        topPadding = AttrMapValue(isNumber, desc='Padding at top of drawing'),
        bottomPadding = AttrMapValue(isNumber, desc='Padding at bottom of drawing'),
        )

    def __init__(self):
        Pie.__init__(self)
        self.x = 0
        self.y = 0
        self.height = 100
        self.width = 100
        self.data = [38.4, 20.7, 18.9, 15.4, 6.6]
        self.labels = None
        self.direction = 'clockwise'
        PCMYKColor, black = colors.PCMYKColor, colors.black
        self.pieAndLegend_colors = [PCMYKColor(11,11,72,0,spotName='PANTONE 458 CV'),
                                    PCMYKColor(100,65,0,30,spotName='PANTONE 288 CV'),
                                    PCMYKColor(11,11,72,0,spotName='PANTONE 458 CV',density=75),
                                    PCMYKColor(100,65,0,30,spotName='PANTONE 288 CV',density=75),
                                    PCMYKColor(11,11,72,0,spotName='PANTONE 458 CV',density=50),
                                    PCMYKColor(100,65,0,30,spotName='PANTONE 288 CV',density=50)]

        #Allows us up to six 'wedges' to be coloured
        self.slices[0].fillColor=self.pieAndLegend_colors[0]
        self.slices[1].fillColor=self.pieAndLegend_colors[1]
        self.slices[2].fillColor=self.pieAndLegend_colors[2]
        self.slices[3].fillColor=self.pieAndLegend_colors[3]
        self.slices[4].fillColor=self.pieAndLegend_colors[4]
        self.slices[5].fillColor=self.pieAndLegend_colors[5]

        self.slices.strokeWidth = 0.75
        self.slices.strokeColor = black

        legendOffset = 17
        self.legendNumberOffset = 51
        self.legendNumberFormat = '%.1f%%'
        self.legend_data = self.data

        #set up the legends
        from reportlab.graphics.charts.legends import Legend
        self.legend1 = Legend()
        self.legend1.x = self.width+legendOffset
        self.legend1.y = self.height
        self.legend1.deltax = 5.67
        self.legend1.deltay = 14.17
        self.legend1.dxTextSpace = 11.39
        self.legend1.dx = 5.67
        self.legend1.dy = 5.67
        self.legend1.columnMaximum = 7
        self.legend1.alignment = 'right'
        self.legend_names = ['AAA:','AA:','A:','BBB:','NR:']
        for f in range(len(self.data)):
            self.legend1.colorNamePairs.append((self.pieAndLegend_colors[f], self.legend_names[f]))
        self.legend1.fontName = "Helvetica-Bold"
        self.legend1.fontSize = 6
        self.legend1.strokeColor = black
        self.legend1.strokeWidth = 0.5

        self._legend2 = Legend()
        self._legend2.dxTextSpace = 0
        self._legend2.dx = 0
        self._legend2.alignment = 'right'
        self._legend2.fontName = "Helvetica-Oblique"
        self._legend2.fontSize = 6
        self._legend2.strokeColor = self.legend1.strokeColor

        self.leftPadding = 5
        self.rightPadding = 5
        self.topPadding = 5
        self.bottomPadding = 5
        self.drawLegend = 1

    def draw(self):
        if self.drawLegend:
            self.legend1.colorNamePairs = []
            self._legend2.colorNamePairs = []
        for f in range(len(self.data)):
            if self.legend_names == None:
                self.slices[f].fillColor = self.pieAndLegend_colors[f]
                self.legend1.colorNamePairs.append((self.pieAndLegend_colors[f], None))
            else:
                try:
                    self.slices[f].fillColor = self.pieAndLegend_colors[f]
                    self.legend1.colorNamePairs.append((self.pieAndLegend_colors[f], self.legend_names[f]))
                except IndexError:
                    self.slices[f].fillColor = self.pieAndLegend_colors[f%len(self.pieAndLegend_colors)]
                    self.legend1.colorNamePairs.append((self.pieAndLegend_colors[f%len(self.pieAndLegend_colors)], self.legend_names[f]))
            if self.legend_data != None:
                ldf = self.legend_data[f]
                lNF = self.legendNumberFormat
                if ldf is None or lNF is None:
                    pass
                elif isinstance(lNF,str):
                    ldf = lNF % ldf
                elif hasattr(lNF,'__call__'):
                    ldf = lNF(ldf)
                else:
                    raise ValueError("Unknown formatter type %s, expected string or function" % ascii(self.legendNumberFormat))
                self._legend2.colorNamePairs.append((None,ldf))
        p = Pie.draw(self)
        if self.drawLegend:
            p.add(self.legend1)
            #hide from user - keeps both sides lined up!
            self._legend2.x = self.legend1.x+self.legendNumberOffset
            self._legend2.y = self.legend1.y
            self._legend2.deltax = self.legend1.deltax
            self._legend2.deltay = self.legend1.deltay
            self._legend2.dy = self.legend1.dy
            self._legend2.columnMaximum = self.legend1.columnMaximum
            p.add(self._legend2)
        p.shift(self.leftPadding, self.bottomPadding)
        return p

    def _getDrawingDimensions(self):
        tx = self.rightPadding
        if self.drawLegend:
            tx += self.legend1.x+self.legendNumberOffset #self._legend2.x
            tx += self._legend2._calculateMaxWidth(self._legend2.colorNamePairs)
        ty = self.bottomPadding+self.height+self.topPadding
        return (tx,ty)

    def demo(self, drawing=None):
        if not drawing:
            tx,ty = self._getDrawingDimensions()
            drawing = Drawing(tx, ty)
        drawing.add(self.draw())
        return drawing

from reportlab.graphics.charts.utils3d import _getShaded, _2rad, _360, _180_pi
class Wedge3dProperties(PropHolder):
    """This holds descriptive information about the wedges in a pie chart.

    It is not to be confused with the 'wedge itself'; this just holds
    a recipe for how to format one, and does not allow you to hack the
    angles.  It can format a genuine Wedge object for you with its
    format method.
    """
    _attrMap = AttrMap(
        fillColor = AttrMapValue(isColorOrNone,desc=''),
        fillColorShaded = AttrMapValue(isColorOrNone,desc=''),
        fontColor = AttrMapValue(isColorOrNone,desc=''),
        fontName = AttrMapValue(isString,desc=''),
        fontSize = AttrMapValue(isNumber,desc=''),
        label_angle = AttrMapValue(isNumber,desc=''),
        label_bottomPadding = AttrMapValue(isNumber,'padding at bottom of box'),
        label_boxAnchor = AttrMapValue(isBoxAnchor,desc=''),
        label_boxFillColor = AttrMapValue(isColorOrNone,desc=''),
        label_boxStrokeColor = AttrMapValue(isColorOrNone,desc=''),
        label_boxStrokeWidth = AttrMapValue(isNumber,desc=''),
        label_dx = AttrMapValue(isNumber,desc=''),
        label_dy = AttrMapValue(isNumber,desc=''),
        label_height = AttrMapValue(isNumberOrNone,desc=''),
        label_leading = AttrMapValue(isNumberOrNone,desc=''),
        label_leftPadding = AttrMapValue(isNumber,'padding at left of box'),
        label_maxWidth = AttrMapValue(isNumberOrNone,desc=''),
        label_rightPadding = AttrMapValue(isNumber,'padding at right of box'),
        label_simple_pointer = AttrMapValue(isBoolean,'set to True for simple pointers'),
        label_strokeColor = AttrMapValue(isColorOrNone,desc=''),
        label_strokeWidth = AttrMapValue(isNumber,desc=''),
        label_text = AttrMapValue(isStringOrNone,desc=''),
        label_textAnchor = AttrMapValue(isTextAnchor,desc=''),
        label_topPadding = AttrMapValue(isNumber,'padding at top of box'),
        label_visible = AttrMapValue(isBoolean,desc="True if the label is to be drawn"),
        label_width = AttrMapValue(isNumberOrNone,desc=''),
        labelRadius = AttrMapValue(isNumber,desc=''),
        popout = AttrMapValue(isNumber,desc=''),
        shading = AttrMapValue(isNumber,desc=''),
        strokeColor = AttrMapValue(isColorOrNone,desc=''),
        strokeColorShaded = AttrMapValue(isColorOrNone,desc=''),
        strokeDashArray = AttrMapValue(isListOfNumbersOrNone,desc=''),
        strokeWidth = AttrMapValue(isNumber,desc=''),
        visible = AttrMapValue(isBoolean,'set to false to skip displaying'),
        )

    def __init__(self):
        self.strokeWidth = 0
        self.shading = 0.3
        self.visible = 1
        self.strokeColorShaded = self.fillColorShaded = self.fillColor = None
        self.strokeColor = STATE_DEFAULTS["strokeColor"]
        self.strokeDashArray = STATE_DEFAULTS["strokeDashArray"]
        self.popout = 0
        self.fontName = STATE_DEFAULTS["fontName"]
        self.fontSize = STATE_DEFAULTS["fontSize"]
        self.fontColor = STATE_DEFAULTS["fillColor"]
        self.labelRadius = 1.2
        self.label_dx = self.label_dy = self.label_angle = 0
        self.label_text = None
        self.label_topPadding = self.label_leftPadding = self.label_rightPadding = self.label_bottomPadding = 0
        self.label_boxAnchor = 'autox'
        self.label_boxStrokeColor = None    #boxStroke
        self.label_boxStrokeWidth = 0.5 #boxStrokeWidth
        self.label_boxFillColor = None
        self.label_strokeColor = None
        self.label_strokeWidth = 0.1
        self.label_leading =    self.label_width = self.label_maxWidth = self.label_height = None
        self.label_textAnchor = 'start'
        self.label_visible = 1
        self.label_simple_pointer = 0

class _SL3D:
    def __init__(self,lo,hi):
        if lo<0:
            lo += 360
            hi += 360
        self.lo = lo
        self.hi = hi
        self.mid = (lo+hi)*0.5
        self.not360 = abs(hi-lo) < _ANGLEHI

    def __str__(self):
        return '_SL3D(%.2f,%.2f)' % (self.lo,self.hi)

def _keyS3D(a,b):
    return -cmp(a[0],b[0])
_keyS3D = functools.cmp_to_key(_keyS3D)

_270r = _2rad(270)
class Pie3d(Pie):
    _attrMap = AttrMap(BASE=Pie,
        perspective = AttrMapValue(isNumber, desc='A flattening parameter.'),
        depth_3d = AttrMapValue(isNumber, desc='depth of the pie.'),
        angle_3d = AttrMapValue(isNumber, desc='The view angle.'),
        )
    perspective = 70
    depth_3d = 25
    angle_3d = 180

    def _popout(self,i):
        return self._sl3d[i].not360 and self.slices[i].popout or 0

    def CX(self, i,d ):
        return self._cx+(d and self._xdepth_3d or 0)+self._popout(i)*cos(_2rad(self._sl3d[i].mid))
    def CY(self,i,d):
        return self._cy+(d and self._ydepth_3d or 0)+self._popout(i)*sin(_2rad(self._sl3d[i].mid))
    def OX(self,i,o,d):
        return self.CX(i,d)+self._radiusx*cos(_2rad(o))
    def OY(self,i,o,d):
        return self.CY(i,d)+self._radiusy*sin(_2rad(o))

    def rad_dist(self,a):
        _3dva = self._3dva
        return min(abs(a-_3dva),abs(a-_3dva+360))

    def __init__(self):
        Pie.__init__(self)
        self.slices = TypedPropertyCollection(Wedge3dProperties)
        self.slices[0].fillColor = colors.darkcyan
        self.slices[1].fillColor = colors.blueviolet
        self.slices[2].fillColor = colors.blue
        self.slices[3].fillColor = colors.cyan
        self.slices[4].fillColor = colors.azure
        self.slices[5].fillColor = colors.crimson
        self.slices[6].fillColor = colors.darkviolet
        self.xradius = self.yradius = None
        self.width = 300
        self.height = 200
        self.data = [12.50,20.10,2.00,22.00,5.00,18.00,13.00]

    def _fillSide(self,L,i,angle,strokeColor,strokeWidth,fillColor):
        rd = self.rad_dist(angle)
        if rd<self.rad_dist(self._sl3d[i].mid):
            p = [self.CX(i,0),self.CY(i,0),
                self.CX(i,1),self.CY(i,1),
                self.OX(i,angle,1),self.OY(i,angle,1),
                self.OX(i,angle,0),self.OY(i,angle,0)]
            L.append((rd,Polygon(p, strokeColor=strokeColor, fillColor=fillColor,strokeWidth=strokeWidth,strokeLineJoin=1)))

    def draw(self):
        slices = self.slices
        _3d_angle = self.angle_3d
        _3dva = self._3dva = _360(_3d_angle+90)
        a0 = _2rad(_3dva)
        depth_3d = self.depth_3d
        self._xdepth_3d = cos(a0)*depth_3d
        self._ydepth_3d = sin(a0)*depth_3d
        self._cx = self.x+self.width/2.0
        self._cy = self.y+(self.height - self._ydepth_3d)/2.0
        radiusx = radiusy = self._cx-self.x
        if self.xradius: radiusx = self.xradius
        if self.yradius: radiusy = self.yradius
        self._radiusx = radiusx
        self._radiusy = radiusy = (1.0 - self.perspective/100.0)*radiusy
        data = self.normalizeData()
        sum = self._sum

        CX = self.CX
        CY = self.CY
        OX = self.OX
        OY = self.OY
        rad_dist = self.rad_dist
        _fillSide = self._fillSide
        self._seriesCount = n = len(data)
        _sl3d = self._sl3d = []
        g = Group()
        last = _360(self.startAngle)
        a0 = self.direction=='clockwise' and -1 or 1
        for v in data:
            v *= a0
            angle1, angle0 = last, v+last
            last = angle0
            if a0>0: angle0, angle1 = angle1, angle0
            _sl3d.append(_SL3D(angle0,angle1))

        labels = _fixLabels(self.labels,n)
        a0 = _3d_angle
        a1 = _3d_angle+180
        T = []
        S = []
        L = []

        class WedgeLabel3d(WedgeLabel):
            _ydepth_3d = self._ydepth_3d
            def _checkDXY(self,ba):
                if ba[0]=='n':
                    if not hasattr(self,'_ody'):
                        self._ody = self.dy
                        self.dy = -self._ody + self._ydepth_3d
    
        checkLabelOverlap = self.checkLabelOverlap

        for i in range(n):
            style = slices[i]
            if not style.visible: continue
            sl = _sl3d[i]
            lo = angle0 = sl.lo
            hi = angle1 = sl.hi
            aa = abs(hi-lo)
            if aa<_ANGLELO: continue
            fillColor = _getShaded(style.fillColor,style.fillColorShaded,style.shading)
            strokeColor = _getShaded(style.strokeColor,style.strokeColorShaded,style.shading) or fillColor
            strokeWidth = style.strokeWidth
            cx0 = CX(i,0)
            cy0 = CY(i,0)
            cx1 = CX(i,1)
            cy1 = CY(i,1)
            if depth_3d:
                #background shaded pie bottom
                g.add(Wedge(cx1,cy1,radiusx, lo, hi,yradius=radiusy,
                                strokeColor=strokeColor,strokeWidth=strokeWidth,fillColor=fillColor,
                                strokeLineJoin=1))
                #connect to top
                if lo < a0 < hi: angle0 = a0
                if lo < a1 < hi: angle1 = a1
                p = ArcPath(strokeColor=strokeColor, fillColor=fillColor,strokeWidth=strokeWidth,strokeLineJoin=1)
                p.addArc(cx1,cy1,radiusx,angle0,angle1,yradius=radiusy,moveTo=1)
                p.lineTo(OX(i,angle1,0),OY(i,angle1,0))
                p.addArc(cx0,cy0,radiusx,angle0,angle1,yradius=radiusy,reverse=1)
                p.closePath()
                if angle0<=_3dva and angle1>=_3dva:
                    rd = 0
                else:
                    rd = min(rad_dist(angle0),rad_dist(angle1))
                S.append((rd,p))
                _fillSide(S,i,lo,strokeColor,strokeWidth,fillColor)
                _fillSide(S,i,hi,strokeColor,strokeWidth,fillColor)

            #bright shaded top
            fillColor = style.fillColor
            strokeColor = style.strokeColor or fillColor
            T.append(Wedge(cx0,cy0,radiusx,lo,hi,yradius=radiusy,
                            strokeColor=strokeColor,strokeWidth=strokeWidth,fillColor=fillColor,strokeLineJoin=1))
            if aa>=_ANGLEHI:
                theWedge = Ellipse(cx0, cy0, radiusx, radiusy,
                            strokeColor=strokeColor,strokeWidth=strokeWidth,fillColor=fillColor,strokeLineJoin=1)
            else:
                theWedge = Wedge(cx0,cy0,radiusx,lo,hi,yradius=radiusy,
                            strokeColor=strokeColor,strokeWidth=strokeWidth,fillColor=fillColor,strokeLineJoin=1)
            T.append(theWedge)

            text = labels[i]
            if style.label_visible and text:
                rat = style.labelRadius
                self._radiusx *= rat
                self._radiusy *= rat
                mid = sl.mid
                labelX = OX(i,mid,0)
                labelY = OY(i,mid,0)
                l=_addWedgeLabel(self,text,mid,labelX,labelY,style,labelClass=WedgeLabel3d)
                L.append(l)
                if checkLabelOverlap:
                    l._origdata = { 'x': labelX, 'y':labelY, 'angle': mid,
                                    'rx': self._radiusx, 'ry':self._radiusy, 'cx':CX(i,0), 'cy':CY(i,0),
                                    'bounds': l.getBounds(),
                                    }
                self._radiusx = radiusx
                self._radiusy = radiusy

        S.sort(key=_keyS3D)
        if checkLabelOverlap and L:
            fixLabelOverlaps(L,self.sideLabels)
        for x in ([s[1] for s in S]+T+L):
            g.add(x)
        return g

    def demo(self):
        d = Drawing(200, 100)

        pc = Pie()
        pc.x = 50
        pc.y = 10
        pc.width = 100
        pc.height = 80
        pc.data = [10,20,30,40,50,60]
        pc.labels = ['a','b','c','d','e','f']

        pc.slices.strokeWidth=0.5
        pc.slices[3].popout = 10
        pc.slices[3].strokeWidth = 2
        pc.slices[3].strokeDashArray = [2,2]
        pc.slices[3].labelRadius = 1.75
        pc.slices[3].fontColor = colors.red
        pc.slices[0].fillColor = colors.darkcyan
        pc.slices[1].fillColor = colors.blueviolet
        pc.slices[2].fillColor = colors.blue
        pc.slices[3].fillColor = colors.cyan
        pc.slices[4].fillColor = colors.aquamarine
        pc.slices[5].fillColor = colors.cadetblue
        pc.slices[6].fillColor = colors.lightcoral
        self.slices[1].visible = 0
        self.slices[3].visible = 1
        self.slices[4].visible = 1
        self.slices[5].visible = 1
        self.slices[6].visible = 0

        d.add(pc)
        return d


def sample0a():
    "Make a degenerated pie chart with only one slice."

    d = Drawing(400, 200)

    pc = Pie()
    pc.x = 150
    pc.y = 50
    pc.data = [10]
    pc.labels = ['a']
    pc.slices.strokeWidth=1#0.5

    d.add(pc)

    return d


def sample0b():
    "Make a degenerated pie chart with only one slice."

    d = Drawing(400, 200)

    pc = Pie()
    pc.x = 150
    pc.y = 50
    pc.width = 120
    pc.height = 100
    pc.data = [10]
    pc.labels = ['a']
    pc.slices.strokeWidth=1#0.5

    d.add(pc)

    return d


def sample1():
    "Make a typical pie chart with with one slice treated in a special way."

    d = Drawing(400, 200)

    pc = Pie()
    pc.x = 150
    pc.y = 50
    pc.data = [10, 20, 30, 40, 50, 60]
    pc.labels = ['a', 'b', 'c', 'd', 'e', 'f']

    pc.slices.strokeWidth=1#0.5
    pc.slices[3].popout = 20
    pc.slices[3].strokeWidth = 2
    pc.slices[3].strokeDashArray = [2,2]
    pc.slices[3].labelRadius = 1.75
    pc.slices[3].fontColor = colors.red

    d.add(pc)

    return d


def sample2():
    "Make a pie chart with nine slices."

    d = Drawing(400, 200)

    pc = Pie()
    pc.x = 125
    pc.y = 25
    pc.data = [0.31, 0.148, 0.108,
               0.076, 0.033, 0.03,
               0.019, 0.126, 0.15]
    pc.labels = ['1', '2', '3', '4', '5', '6', '7', '8', 'X']

    pc.width = 150
    pc.height = 150
    pc.slices.strokeWidth=1#0.5

    pc.slices[0].fillColor = colors.steelblue
    pc.slices[1].fillColor = colors.thistle
    pc.slices[2].fillColor = colors.cornflower
    pc.slices[3].fillColor = colors.lightsteelblue
    pc.slices[4].fillColor = colors.aquamarine
    pc.slices[5].fillColor = colors.cadetblue
    pc.slices[6].fillColor = colors.lightcoral
    pc.slices[7].fillColor = colors.tan
    pc.slices[8].fillColor = colors.darkseagreen

    d.add(pc)

    return d


def sample3():
    "Make a pie chart with a very slim slice."

    d = Drawing(400, 200)

    pc = Pie()
    pc.x = 125
    pc.y = 25

    pc.data = [74, 1, 25]

    pc.width = 150
    pc.height = 150
    pc.slices.strokeWidth=1#0.5
    pc.slices[0].fillColor = colors.steelblue
    pc.slices[1].fillColor = colors.thistle
    pc.slices[2].fillColor = colors.cornflower

    d.add(pc)

    return d


def sample4():
    "Make a pie chart with several very slim slices."

    d = Drawing(400, 200)

    pc = Pie()
    pc.x = 125
    pc.y = 25

    pc.data = [74, 1, 1, 1, 1, 22]

    pc.width = 150
    pc.height = 150
    pc.slices.strokeWidth=1#0.5
    pc.slices[0].fillColor = colors.steelblue
    pc.slices[1].fillColor = colors.thistle
    pc.slices[2].fillColor = colors.cornflower
    pc.slices[3].fillColor = colors.lightsteelblue
    pc.slices[4].fillColor = colors.aquamarine
    pc.slices[5].fillColor = colors.cadetblue

    d.add(pc)

    return d

def sample5():
    "Make a pie with side labels."

    d = Drawing(400, 200)

    pc = Pie()
    pc.x = 125
    pc.y = 25

    pc.data = [7, 1, 1, 1, 1, 2]
    pc.labels = ['example1', 'example2', 'example3', 'example4', 'example5', 'example6']
    pc.sideLabels = 1

    pc.width = 150
    pc.height = 150
    pc.slices.strokeWidth=1#0.5
    pc.slices[0].fillColor = colors.steelblue
    pc.slices[1].fillColor = colors.thistle
    pc.slices[2].fillColor = colors.cornflower
    pc.slices[3].fillColor = colors.lightsteelblue
    pc.slices[4].fillColor = colors.aquamarine
    pc.slices[5].fillColor = colors.cadetblue

    d.add(pc)

    return d

def sample6():

    "Illustrates the pie moving to leave space for the left labels"

    d = Drawing(400, 200)

    pc = Pie()
    "The x value of the pie chart is 0"
    pc.x = 0
    pc.y = 25

    pc.data = [74, 1, 1, 1, 1, 22]
    pc.labels = ['example1', 'example2', 'example3', 'example4', 'example5', 'example6']
    pc.sideLabels = 1

    pc.width = 150
    pc.height = 150
    pc.slices.strokeWidth=1#0.5
    pc.slices[0].fillColor = colors.steelblue
    pc.slices[1].fillColor = colors.thistle
    pc.slices[2].fillColor = colors.cornflower
    pc.slices[3].fillColor = colors.lightsteelblue
    pc.slices[4].fillColor = colors.aquamarine
    pc.slices[5].fillColor = colors.cadetblue

    l = Line(0,0,0,200)

    d.add(pc)
    d.add(l)

    return d

def sample7():

    "Case with overlapping pointers"

    d = Drawing(400, 200)

    pc = Pie()   
    pc.y = 50
    pc.x = 150
    pc.width = 100
    pc.height = 100

    pc.data = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    pc.labels = ['example1', 'example2', 'example3', 'example4', 'example5', 'example6', 'example7', 
                'example8', 'example9', 'example10', 'example11', 'example12', 'example13', 'example14', 
                'example15', 'example16', 'example17', 'example18', 'example19', 'example20', 'example21', 
                'example22', 'example23', 'example24', 'example25', 'example26', 'example27', 'example28']
    pc.sideLabels = 1
    pc.checkLabelOverlap = 1
    pc.simpleLabels = 0
    

    pc.slices.strokeWidth=1#0.5
    pc.slices[0].fillColor = colors.steelblue
    pc.slices[1].fillColor = colors.thistle
    pc.slices[2].fillColor = colors.cornflower
    pc.slices[3].fillColor = colors.lightsteelblue
    pc.slices[4].fillColor = colors.aquamarine
    pc.slices[5].fillColor = colors.cadetblue

    d.add(pc)

    return d

def sample8():

    "Case with overlapping labels"
    "Labels overlap if they do not belong to adjacent pie slices due to nature of checkLabelOverlap"

    d = Drawing(400, 200)

    pc = Pie()   
    pc.y = 50
    pc.x = 150
    pc.width = 100
    pc.height = 100

    pc.data = [1, 1, 1, 1, 1, 30, 50, 1, 1, 1, 1, 1, 1, 40,20,10]
    pc.labels = ['example1', 'example2', 'example3', 'example4', 'example5', 'example6', 'example7', 
                'example8', 'example9', 'example10', 'example11', 'example12', 'example13', 'example14', 
                'example15', 'example16']
    pc.sideLabels = 1
    pc.checkLabelOverlap = 1

    pc.slices.strokeWidth=1#0.5
    pc.slices[0].fillColor = colors.steelblue
    pc.slices[1].fillColor = colors.thistle
    pc.slices[2].fillColor = colors.cornflower
    pc.slices[3].fillColor = colors.lightsteelblue
    pc.slices[4].fillColor = colors.aquamarine
    pc.slices[5].fillColor = colors.cadetblue

    d.add(pc)

    return d

def sample9():

    "Case with overlapping labels"
    "Labels overlap if they do not belong to adjacent pies due to nature of checkLabelOverlap"

    d = Drawing(400, 200)

    pc = Pie()   
    pc.x = 125
    pc.y = 50

    pc.data = [41, 20, 40, 15, 20, 30, 50, 15, 25, 35, 25, 20, 30, 40, 20, 30]
    pc.labels = ['example1', 'example2', 'example3', 'example4', 'example5', 'example6', 'example7', 
                'example8', 'example9', 'example10', 'example11', 'example12', 'example13', 'example14', 
                'example15', 'example16']
    pc.sideLabels = 1
    pc.checkLabelOverlap = 1

    pc.width = 100
    pc.height = 100
    pc.slices.strokeWidth=1#0.5
    pc.slices[0].fillColor = colors.steelblue
    pc.slices[1].fillColor = colors.thistle
    pc.slices[2].fillColor = colors.cornflower
    pc.slices[3].fillColor = colors.lightsteelblue
    pc.slices[4].fillColor = colors.aquamarine
    pc.slices[5].fillColor = colors.cadetblue

    d.add(pc)

    return d

if __name__=='__main__':
    """Normally nobody will execute this

    It's helpful for reportlab developers to put a 'main' block in to execute
    the most recently edited feature.
    """
    import sys
    from reportlab.graphics import renderPDF
    argv = sys.argv[1:] or ['7']
    for a in argv:
        name = a if a.startswith('sample') else 'sample%s' % a
        drawing = globals()[name]()
        renderPDF.drawToFile(drawing, '%s.pdf' % name)

    

