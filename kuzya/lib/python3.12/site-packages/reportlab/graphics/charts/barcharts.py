#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/graphics/charts/barcharts.py
__version__='3.3.0'
__doc__="""This module defines a variety of Bar Chart components.

The basic flavors are stacked and side-by-side, available in horizontal and
vertical versions. 

"""

import copy, functools
from ast import literal_eval

from reportlab.lib import colors
from reportlab.lib.validators import isNumber, isNumberOrNone, isColorOrNone, isString,\
            SequenceOf, isBoolean, isStringOrNone,\
            NoneOr, isListOfNumbersOrNone, EitherOr, OneOf, isInt
from reportlab.lib.utils import isStr, yieldNoneSplits
from reportlab.graphics.widgets.markers import uSymbol2Symbol, isSymbol
from reportlab.lib.attrmap import AttrMap, AttrMapValue
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.graphics.widgetbase import TypedPropertyCollection, PropHolder, tpcGetItem
from reportlab.graphics.shapes import Line, Rect, Group, Drawing, PolyLine
from reportlab.graphics.charts.axes import XCategoryAxis, YValueAxis, YCategoryAxis, XValueAxis
from reportlab.graphics.charts.textlabels import BarChartLabel, NoneOrInstanceOfNA_Label
from reportlab.graphics.charts.areas import PlotArea
from reportlab.graphics.charts.legends import _objStr
from reportlab import cmp

class BarChartProperties(PropHolder):
    _attrMap = AttrMap(
        strokeColor = AttrMapValue(isColorOrNone, desc='Color of the bar border.'),
        fillColor = AttrMapValue(isColorOrNone, desc='Color of the bar interior area.'),
        strokeWidth = AttrMapValue(isNumber, desc='Width of the bar border.'),
        strokeDashArray = AttrMapValue(isListOfNumbersOrNone, desc='Dash array of a line.'),
        symbol = AttrMapValue(None, desc='A widget to be used instead of a normal bar.',advancedUsage=1),
        name = AttrMapValue(isString, desc='Text to be associated with a bar (eg seriesname)'),
        swatchMarker = AttrMapValue(NoneOr(isSymbol), desc="None or makeMarker('Diamond') ...",advancedUsage=1),
        minDimen = AttrMapValue(isNumberOrNone, desc='minimum width/height that will be drawn.'),
        isLine = AttrMapValue(NoneOr(isBoolean), desc='if this bar should be drawn as a line'),
        )

    def __init__(self):
        self.strokeColor = None
        self.fillColor = colors.blue
        self.strokeWidth = 0.5
        self.symbol = None
        self.strokeDashArray = None

# Bar chart classes.
class BarChart(PlotArea):
    "Abstract base class, unusable by itself."

    _attrMap = AttrMap(BASE=PlotArea,
        useAbsolute = AttrMapValue(EitherOr((isBoolean,EitherOr((isString,isNumber)))), desc='Flag to use absolute spacing values; use string of gsb for finer control\n(g=groupSpacing,s=barSpacing,b=barWidth).',advancedUsage=1),
        barWidth = AttrMapValue(isNumber, desc='The width of an individual bar.'),
        groupSpacing = AttrMapValue(isNumber, desc='Width between groups of bars.'),
        barSpacing = AttrMapValue(isNumber, desc='Width between individual bars.'),
        bars = AttrMapValue(None, desc='Handle of the individual bars.'),
        valueAxis = AttrMapValue(None, desc='Handle of the value axis.'),
        categoryAxis = AttrMapValue(None, desc='Handle of the category axis.'),
        data = AttrMapValue(None, desc='Data to be plotted, list of (lists of) numbers.'),
        barLabels = AttrMapValue(None, desc='Handle to the list of bar labels.'),
        barLabelFormat = AttrMapValue(None, desc='Formatting string or function used for bar labels. Can be a list or list of lists of such.'),
        barLabelCallOut = AttrMapValue(None, desc='Callout function(label)\nlabel._callOutInfo = (self,g,rowNo,colNo,x,y,width,height,x00,y00,x0,y0)',advancedUsage=1),
        barLabelArray = AttrMapValue(None, desc='explicit array of bar label values, must match size of data if present.'),
        reversePlotOrder = AttrMapValue(isBoolean, desc='If true, reverse common category plot order.',advancedUsage=1),
        naLabel = AttrMapValue(NoneOrInstanceOfNA_Label, desc='Label to use for N/A values.',advancedUsage=1),
        annotations = AttrMapValue(None, desc='list of callables, will be called with self, xscale, yscale.'),
        categoryLabelBarSize = AttrMapValue(isNumber, desc='width to leave for a category label to go between categories.'),
        categoryLabelBarOrder = AttrMapValue(OneOf('first','last','auto'), desc='where any label bar should appear first/last'),
        barRecord = AttrMapValue(None, desc='callable(bar,label=labelText,value=value,**kwds) to record bar information', advancedUsage=1),
        zIndexOverrides = AttrMapValue(isStringOrNone, desc='''None (the default ie use old z ordering scheme) or a ',' separated list of key=value (int/float) for new zIndex ordering. If used defaults are
    background=0,
    categoryAxis=1,
    valueAxis=2,
    bars=3,
    barLabels=4,
    categoryAxisGrid=5,
    valueAxisGrid=6,
    annotations=7'''),
        categoryNALabel = AttrMapValue(NoneOrInstanceOfNA_Label, desc='Label to use for a group of N/A values.',advancedUsage=1),
        seriesOrder = AttrMapValue(SequenceOf(SequenceOf(isInt,emptyOK=0,NoneOK=0,lo=1),emptyOK=0,NoneOK=1,lo=1),"dynamic 'mixed' category style case"),
        )

    def makeSwatchSample(self, rowNo, x, y, width, height):
        baseStyle = self.bars
        styleIdx = rowNo % len(baseStyle)
        style = baseStyle[styleIdx]
        strokeColor = getattr(style, 'strokeColor', getattr(baseStyle,'strokeColor',None))
        fillColor = getattr(style, 'fillColor', getattr(baseStyle,'fillColor',None))
        strokeDashArray = getattr(style, 'strokeDashArray', getattr(baseStyle,'strokeDashArray',None))
        strokeWidth = getattr(style, 'strokeWidth', getattr(style, 'strokeWidth',None))
        swatchMarker = getattr(style, 'swatchMarker', getattr(baseStyle, 'swatchMarker',None))
        if swatchMarker:
            return uSymbol2Symbol(swatchMarker,x+width/2.,y+height/2.,fillColor)
        elif getattr(style,'isLine',False):
            yh2 = y+height/2.
            if hasattr(style, 'symbol'):
                S = style.symbol
            elif hasattr(baseStyle, 'symbol'):
                S = baseStyle.symbol
            else:
                S = None
            L = Line(x,yh2, x+width, yh2,
                    strokeColor=style.strokeColor or style.fillColor,
                    strokeWidth=style.strokeWidth,
                    strokeDashArray = style.strokeDashArray)

            if S: S = uSymbol2Symbol(S,x+width/2.,yh2,style.strokeColor or style.fillColor)
            if S and L:
                g = Group()
                g.add(L)
                g.add(S)
                return g
            return S or L
        else:
            return Rect(x,y,width,height,strokeWidth=strokeWidth,strokeColor=strokeColor,
                        strokeDashArray=strokeDashArray,fillColor=fillColor)

    def getSeriesName(self,i,default=None):
        '''return series name i or default'''
        return _objStr(getattr(self.bars[i],'name',default))

    def __init__(self):
        assert self.__class__.__name__ not in ('BarChart','BarChart3D'), 'Abstract Class %s Instantiated' % self.__class__.__name__

        if self._flipXY:
            self.categoryAxis = YCategoryAxis()
            self.valueAxis = XValueAxis()
        else:
            self.categoryAxis = XCategoryAxis()
            self.valueAxis = YValueAxis()
        self.categoryAxis._attrMap['style'].validate = OneOf('stacked','parallel','parallel_3d','mixed')

        PlotArea.__init__(self)
        self.barSpacing = 0
        self.reversePlotOrder = 0


        # this defines two series of 3 points.  Just an example.
        self.data = [(100,110,120,130),
                    (70, 80, 85, 90)]

        # control bar spacing. is useAbsolute = 1 then
        # the next parameters are in points; otherwise
        # they are 'proportions' and are normalized to
        # fit the available space.  Half a barSpacing
        # is allocated at the beginning and end of the
        # chart.
        self.useAbsolute = 0   #- not done yet
        self.barWidth = 10
        self.groupSpacing = 5
        self.barSpacing = 0

        self.barLabels = TypedPropertyCollection(BarChartLabel)
        self.barLabels.boxAnchor = 'c'
        self.barLabels.textAnchor = 'middle'
        self.barLabelFormat = None
        self.barLabelArray = None
        # this says whether the origin is inside or outside
        # the bar - +10 means put the origin ten points
        # above the tip of the bar if value > 0, or ten
        # points inside if bar value < 0.  This is different
        # to label dx/dy which are not dependent on the
        # sign of the data.
        self.barLabels.nudge = 0

        # if you have multiple series, by default they butt
        # together.

        # we really need some well-designed default lists of
        # colors e.g. from Tufte.  These will be used in a
        # cycle to set the fill color of each series.
        self.bars = TypedPropertyCollection(BarChartProperties)
        self.bars.strokeWidth = 1
        self.bars.strokeColor = colors.black
        self.bars.strokeDashArray = None

        self.bars[0].fillColor = colors.red
        self.bars[1].fillColor = colors.green
        self.bars[2].fillColor = colors.blue
        self.naLabel = self.categoryNALabel = None
        self.zIndexOverrides = None

    def demo(self):
        """Shows basic use of a bar chart"""
        if self.__class__.__name__=='BarChart':
            raise NotImplementedError('Abstract Class BarChart has no demo')
        drawing = Drawing(200, 100)
        bc = self.__class__()
        drawing.add(bc)
        return drawing

    def getSeriesOrder(self):
        bs = getattr(self,'seriesOrder',None)
        n = len(self.data)
        if not bs: 
            R = [(ss,) for ss in range(n)]
        else:
            bars = self.bars
            unseen = set(range(n))
            lines = set()
            R = []
            for s in bs:
                g = {ss for ss in s if 0<=ss<=n}
                gl = {ss for ss in g if bars.checkAttr(ss,'isLine',False)}
                if gl:
                    g -= gl
                    lines |= gl
                    unseen -= gl
                if g:
                    R.append(tuple(g))
                    unseen -= g
            if unseen:
                R.extend((ss,) for ss in sorted(unseen))
            if lines:
                R.extend((ss,) for ss in sorted(lines))
        self._seriesOrder = R

    def _getConfigureData(self):
        cAStyle = self.categoryAxis.style
        data = self.data
        cc = max(list(map(len,data)))   #category count
        _data = data
        if cAStyle not in ('parallel','parallel_3d'):
            #stacked or mixed
            data = []
            def _accumulate(*D):
                pdata = max((len(d) for d in D))*[0]
                ndata = pdata[:]
                for d in D:
                    for i,v in enumerate(d):
                        v = v or 0
                        if v<=-1e-6:
                            ndata[i] += v
                        else:
                            pdata[i] += v
                data.append(ndata)
                data.append(pdata)
            if cAStyle=='stacked':
                _accumulate(*_data)
            else:
                self.getSeriesOrder()
                for b in self._seriesOrder:
                    _accumulate(*(_data[j] for j in b))
        self._configureData = data

    def _getMinMax(self):
        '''Attempt to return the data range'''
        self._getConfigureData()
        self.valueAxis._setRange(self._configureData)
        return self.valueAxis._valueMin, self.valueAxis._valueMax

    def _drawBegin(self,org,length):
        '''Position and configure value axis, return crossing value'''
        vA = self.valueAxis
        vA.setPosition(self.x, self.y, length)
        self._getConfigureData()
        vA.configure(self._configureData)

        # if zero is in chart, put the other axis there, otherwise use org
        crossesAt = vA.scale(0)
        return crossesAt if vA.forceZero or (crossesAt>=org and crossesAt<=org+length) else org

    def _drawFinish(self):
        '''finalize the drawing of a barchart'''
        cA = self.categoryAxis
        vA = self.valueAxis
        cA.configure(self._configureData)
        self.calcBarPositions()
        g = Group()

        zIndex = getattr(self,'zIndexOverrides',None)
        if not zIndex:
            g.add(self.makeBackground())
            cAdgl = getattr(cA,'drawGridLast',False)
            vAdgl = getattr(vA,'drawGridLast',False)
            if not cAdgl: cA.makeGrid(g,parent=self, dim=vA.getGridDims)
            if not vAdgl: vA.makeGrid(g,parent=self, dim=cA.getGridDims)
            g.add(self.makeBars())
            g.add(cA)
            g.add(vA)
            if cAdgl: cA.makeGrid(g,parent=self, dim=vA.getGridDims)
            if vAdgl: vA.makeGrid(g,parent=self, dim=cA.getGridDims)
            for a in getattr(self,'annotations',()): g.add(a(self,cA.scale,vA.scale))
        else:
            Z=dict(
                background=0,
                categoryAxis=1,
                valueAxis=2,
                bars=3,
                barLabels=4,
                categoryAxisGrid=5,
                valueAxisGrid=6,
                annotations=7,
                )
            for z in zIndex.strip().split(','):
                z = z.strip()
                if not z: continue
                try:
                    k,v=z.split('=')
                except:
                    raise ValueError('Badly formatted zIndex clause %r in %r\nallowed variables are\n%s' % (z,zIndex,'\n'.join(['%s=%r'% (k,Z[k]) for k in sorted(Z.keys())])))
                if k not in Z:
                    raise ValueError('Unknown zIndex variable %r in %r\nallowed variables are\n%s' % (k,Z,'\n'.join(['%s=%r'% (k,Z[k]) for k in sorted(Z.keys())])))
                try:
                    v = literal_eval(v) #only constants allowed
                    assert isinstance(v,(float,int))
                except:
                    raise ValueError('Bad zIndex value %r in clause %r of zIndex\nallowed variables are\n%s' % (v,z,zIndex,'\n'.join(['%s=%r'% (k,Z[k]) for k in sorted(Z.keys())])))
                Z[k] = v
            Z = [(v,k) for k,v in Z.items()]
            Z.sort()
            b = self.makeBars()
            bl = b.contents.pop(-1)
            for v,k in Z:
                if k=='background':
                    g.add(self.makeBackground())
                elif k=='categoryAxis':
                    g.add(cA)
                elif k=='categoryAxisGrid':
                    cA.makeGrid(g,parent=self, dim=vA.getGridDims)
                elif k=='valueAxis':
                    g.add(vA)
                elif k=='valueAxisGrid':
                    vA.makeGrid(g,parent=self, dim=cA.getGridDims)
                elif k=='bars':
                    g.add(b)
                elif k=='barLabels':
                    g.add(bl)
                elif k=='annotations':
                    for a in getattr(self,'annotations',()): g.add(a(self,cA.scale,vA.scale))

        del self._configureData
        return g

    def calcBarPositions(self):
        """Works out where they go. default vertical.

        Sets an attribute _barPositions which is a list of
        lists of (x, y, width, height) matching the data.
        """

        flipXY = self._flipXY
        if flipXY:
            org = self.y
        else:
            org = self.x
        cA = self.categoryAxis
        cScale = cA.scale

        data = self.data

        seriesCount = self._seriesCount = len(data)
        self._rowLength = rowLength = max(list(map(len,data)))
        wG = self.groupSpacing
        barSpacing = self.barSpacing
        barWidth = self.barWidth
        clbs = getattr(self,'categoryLabelBarSize',0)
        clbo = getattr(self,'categoryLabelBarOrder','auto')
        if clbo=='auto': clbo = flipXY and 'last' or 'first'
        clbo = clbo=='first'
        style = cA.style
        bars = self.bars
        lineCount = sum((int(bars.checkAttr(_,'isLine',False)) for _ in range(seriesCount)))
        seriesMLineCount = seriesCount - lineCount
        if style=='mixed':
            ss = self._seriesOrder
            barsPerGroup = len(ss) - lineCount
            wB = barsPerGroup*barWidth
            wS = (barsPerGroup-1)*barSpacing
            if barsPerGroup>1:
                bGapB = barWidth
                bGapS = barSpacing
            else:
                bGapB = bGapS = 0
            accumNeg = barsPerGroup*rowLength*[0]
            accumPos = accumNeg[:]
        elif style in ('parallel','parallel_3d'):
            barsPerGroup = 1
            wB = seriesMLineCount*barWidth
            wS = (seriesMLineCount-1)*barSpacing
            bGapB = barWidth
            bGapS = barSpacing
        else:
            barsPerGroup = seriesMLineCount
            accumNeg = rowLength*[0]
            accumPos = accumNeg[:]
            wB = barWidth
            wS = bGapB = bGapS = 0
            
        self._groupWidth = groupWidth = wG+wB+wS
        useAbsolute = self.useAbsolute

        if useAbsolute:
            if not isinstance(useAbsolute,str):
                useAbsolute = 7 #all three are fixed
            else:
                useAbsolute = 0 + 1*('b' in useAbsolute)+2*('g' in useAbsolute)+4*('s' in useAbsolute)
        else:
            useAbsolute = 0

        aW0 = float(cScale(0)[1])
        aW = aW0 - clbs

        if useAbsolute==0: #case 0 all are free
            self._normFactor = fB = fG = fS = aW/groupWidth
        elif useAbsolute==7:    #all fixed
            fB = fG = fS = 1.0
            _cscale = cA._scale
        elif useAbsolute==1: #case 1 barWidth is fixed
            fB = 1.0
            fG = fS = (aW-wB)/(wG+wS)
        elif useAbsolute==2: #groupspacing is fixed
            fG=1.0
            fB = fS = (aW-wG)/(wB+wS)
        elif useAbsolute==3: #groupspacing & barwidth are fixed
            fB = fG = 1.0
            fS = (aW-wG-wB)/wS if wS else 0
        elif useAbsolute==4: #barspacing is fixed
            fS=1.0
            fG = fB = (aW-wS)/(wG+wB)
        elif useAbsolute==5: #barspacing & barWidth are fixed
            fS = fB = 1.0
            fG = (aW-wB-wS)/wG
        elif useAbsolute==6: #barspacing & groupspacing are fixed
            fS = fG = 1
            fB = (aW-wS-wG)/wB
        self._normFactorB = fB
        self._normFactorG = fG
        self._normFactorS = fS

        # 'Baseline' correction...
        vA = self.valueAxis
        vScale = vA.scale
        vARD = vA.reverseDirection
        vm, vM = vA._valueMin, vA._valueMax
        if vm <= 0 <= vM:
            baseLine = vScale(0)
        elif 0 < vm:
            baseLine = vScale(vm)
        elif vM < 0:
            baseLine = vScale(vM)
        self._baseLine = baseLine

        width = barWidth*fB
        offs = 0.5*wG*fG
        bGap = bGapB*fB+bGapS*fS

        if clbs:
            if clbo: #the lable bar comes first
                lbpf = (offs+clbs/6.0)/aW0
                offs += clbs
            else:
                lbpf = (offs+wB*fB+wS*fS+clbs/6.0)/aW0
            cA.labels.labelPosFrac = lbpf

        self._barPositions = []
        aBP = self._barPositions.append
        reversePlotOrder = self.reversePlotOrder

        def _addBar(colNo, accx):
            # Ufff...
            if useAbsolute==7:
                x = groupWidth*_cscale(colNo) + xVal + org
            else:
                (g, _) = cScale(colNo)
                x = g + xVal

            datum = row[colNo]
            if datum is None:
                height = None
                y = baseLine
            else:
                if style not in ('parallel','parallel_3d') and not isLine:
                    if datum<=-1e-6:
                        y = vScale(accumNeg[accx])
                        if (y<baseLine if vARD else y>baseLine): y = baseLine
                        accumNeg[accx] += datum
                        datum = accumNeg[accx]
                    else:
                        y = vScale(accumPos[accx])
                        if (y>baseLine if vARD else y<baseLine): y = baseLine
                        accumPos[accx] += datum
                        datum = accumPos[accx]
                else:
                    y = baseLine
                height = vScale(datum) - y
                if -1e-8<height<=1e-8:
                    height = 1e-8
                    if datum<-1e-8: height = -1e-8
            barRow.append(flipXY and (y,x,height,width) or (x,y,width,height))

        if style!='mixed':
            lineSeen = 0
            for rowNo, row in enumerate(data):  #iterate over the separate series
                barRow = []
                xVal = barsPerGroup - 1 - rowNo if reversePlotOrder else rowNo
                xVal = offs + xVal*bGap
                isLine = bars.checkAttr(rowNo, 'isLine', False)
                if isLine:
                    lineSeen += 1
                    xVal = offs+(seriesMLineCount-1)*bGap*0.5
                else:
                    xVal -= lineSeen*bGap
                for colNo in range(rowLength): #iterate over categories
                    _addBar(colNo,colNo)
                aBP(barRow)
        else:
            lineSeen = 0
            for sb,sg in enumerate(self._seriesOrder):  #the sub bar nos and series groups
                style = 'parallel' if len(sg)<=1 else 'stacked'
                for rowNo in sg:    #the individual series
                    xVal = barsPerGroup - 1 - sb if reversePlotOrder else sb
                    xVal = offs + xVal*bGap
                    barRow = []
                    row = data[rowNo]
                    isLine = bars.checkAttr(rowNo, 'isLine', False)
                    if isLine:
                        lineSeen += 1
                        xVal = offs+(barsPerGroup-1)*bGap*0.5
                    else:
                        xVal -= lineSeen*bGap
                    for colNo in range(rowLength): #iterate over categories
                        _addBar(colNo,colNo*barsPerGroup + sb)
                    aBP(barRow)

    def _getLabelText(self, rowNo, colNo):
        '''return formatted label text'''
        labelFmt = self.barLabelFormat
        if isinstance(labelFmt,(list,tuple)):
            labelFmt = labelFmt[rowNo]
            if isinstance(labelFmt,(list,tuple)):
                labelFmt = labelFmt[colNo]
        if labelFmt is None:
            labelText = None
        elif labelFmt == 'values':
            labelText = self.barLabelArray[rowNo][colNo]
        elif isStr(labelFmt):
            labelText = labelFmt % self.data[rowNo][colNo]
        elif hasattr(labelFmt,'__call__'):
            labelText = labelFmt(self.data[rowNo][colNo])
        else:
            msg = "Unknown formatter type %s, expected string or function" % labelFmt
            raise Exception(msg)
        return labelText

    def _labelXY(self,label,x,y,width,height):
        'Compute x, y for a label'
        nudge = label.nudge
        bt = getattr(label,'boxTarget','normal')
        anti = bt=='anti'
        if anti: nudge = -nudge
        pm = value = height
        if anti: value = 0
        a = x + 0.5*width
        nudge = (height>=0 and 1 or -1)*nudge
        if bt=='mid':
            b = y+height*0.5
        elif bt=='hi':
            if value>=0:
                b = y + value + nudge
            else:
                b = y - nudge
                pm = -pm
        elif bt=='lo':
            if value<=0:
                b = y + value + nudge
            else:
                b = y - nudge
                pm = -pm
        else:
            b = y + value + nudge
        label._pmv = pm #the plus minus val
        return a,b,pm

    def _addBarLabel(self, g, rowNo, colNo, x, y, width, height):
        text = self._getLabelText(rowNo,colNo)
        if text:
            self._addLabel(text, self.barLabels[(rowNo, colNo)], g, rowNo, colNo, x, y, width, height)

    def _addNABarLabel(self, g, rowNo, colNo, x, y, width, height, calcOnly=False, na=None):
        if na is None: na = self.naLabel
        if na and na.text:
            na = copy.copy(na)
            v = self.valueAxis._valueMax<=0 and -1e-8 or 1e-8
            if width is None: width = v
            if height is None: height = v
            return self._addLabel(na.text, na, g, rowNo, colNo, x, y, width, height, calcOnly=calcOnly)

    def _addLabel(self, text, label, g, rowNo, colNo, x, y, width, height, calcOnly=False):
        if label.visible:
            labelWidth = stringWidth(text, label.fontName, label.fontSize)
            flipXY = self._flipXY
            if flipXY:
                y0, x0, pm = self._labelXY(label,y,x,height,width)
            else:
                x0, y0, pm = self._labelXY(label,x,y,width,height)
            fixedEnd = getattr(label,'fixedEnd', None)
            if fixedEnd is not None:
                v = fixedEnd._getValue(self,pm)
                x00, y00 = x0, y0
                if flipXY:
                    x0 = v
                else:
                    y0 = v
            else:
                if flipXY:
                    x00 = x0
                    y00 = y+height/2.0
                else:
                    x00 = x+width/2.0
                    y00 = y0
            fixedStart = getattr(label,'fixedStart', None)
            if fixedStart is not None:
                v = fixedStart._getValue(self,pm)
                if flipXY:
                    x00 = v
                else:
                    y00 = v

            if pm<0:
                if flipXY:
                    dx = -2*label.dx
                    dy = 0
                else:
                    dy = -2*label.dy
                    dx = 0
            else:
                dy = dx = 0
            if calcOnly: return x0+dx, y0+dy
            label.setOrigin(x0+dx, y0+dy)
            label.setText(text)
            sC, sW = label.lineStrokeColor, label.lineStrokeWidth
            if sC and sW: g.insert(0,Line(x00,y00,x0,y0, strokeColor=sC, strokeWidth=sW))
            g.add(label)
            alx = getattr(self,'barLabelCallOut',None)
            if alx:
                label._callOutInfo = (self,g,rowNo,colNo,x,y,width,height,x00,y00,x0,y0)
                alx(label)
                del label._callOutInfo

    def _makeBar(self,g,x,y,width,height,rowNo,style):
        r = Rect(x, y, width, height)
        r.strokeWidth = style.strokeWidth
        r.fillColor = style.fillColor
        r.strokeColor = style.strokeColor
        if style.strokeDashArray:
            r.strokeDashArray = style.strokeDashArray
        g.add(r)

    def _makeBars(self,g,lg):
        bars = self.bars
        br = getattr(self,'barRecord',None)
        BP = self._barPositions
        flipXY = self._flipXY

        catNAL = self.categoryNALabel
        catNNA = {}
        if catNAL:
            CBL = []
            rowNoL = len(self.data) - 1
            #find all the categories that have at least one value
            for rowNo, row in enumerate(BP):
                for colNo, (x, y, width, height) in enumerate(row):
                    if None not in (width,height):
                        catNNA[colNo] = 1

        lines = [].append
        lineSyms = [].append
        for rowNo, row in enumerate(BP):
            styleCount = len(bars)
            styleIdx = rowNo % styleCount
            rowStyle = bars[styleIdx]
            isLine = bars.checkAttr(rowNo, 'isLine', False)
            linePts = [].append
            for colNo, (x,y,width,height) in enumerate(row):
                style = (styleIdx,colNo) in bars and bars[(styleIdx,colNo)] or rowStyle
                if None in (width,height):
                    if not catNAL or colNo in catNNA:
                        self._addNABarLabel(lg,rowNo,colNo,x,y,width,height)
                    elif catNAL and colNo not in CBL:
                        r0 = self._addNABarLabel(lg,rowNo,colNo,x,y,width,height,True,catNAL)
                        if r0:
                            x, y, width, height = BP[rowNoL][colNo]
                            r1 = self._addNABarLabel(lg,rowNoL,colNo,x,y,width,height,True,catNAL)
                            x = (r0[0]+r1[0])/2.0
                            y = (r0[1]+r1[1])/2.0
                            self._addNABarLabel(lg,rowNoL,colNo,x,y,0.0001,0.0001,na=catNAL)
                        CBL.append(colNo)
                    if isLine: linePts(None)
                    continue

                # Draw a rectangular symbol for each data item,
                # or a normal colored rectangle.
                symbol = None
                if hasattr(style, 'symbol'):
                    symbol = copy.deepcopy(style.symbol)
                elif hasattr(self.bars, 'symbol'):
                    symbol = self.bars.symbol

                minDimen=getattr(style,'minDimen',None)
                if minDimen:
                    if flipXY:
                        if width<0:
                            width = min(-style.minDimen,width)
                        else:
                            width = max(style.minDimen,width)
                    else:
                        if height<0:
                            height = min(-style.minDimen,height)
                        else:
                            height = max(style.minDimen,height)

                if isLine:
                    if not flipXY:
                        yL = y + height
                        xL = x + width*0.5
                    else:
                        xL = x + width
                        yL = y + height*0.5
                    linePts(xL)
                    linePts(yL)
                    if symbol:
                        sym = uSymbol2Symbol(tpcGetItem(symbol,colNo),xL,yL,style.strokeColor or style.fillColor)
                        if sym: lineSyms(sym)

                elif symbol:
                    symbol.x = x
                    symbol.y = y
                    symbol.width = width
                    symbol.height = height
                    g.add(symbol)

                elif abs(width)>1e-7 and abs(height)>=1e-7 and (style.fillColor is not None or style.strokeColor is not None):
                    self._makeBar(g,x,y,width,height,rowNo,style)
                    if br: br(g.contents[-1],label=self._getLabelText(rowNo,colNo),value=self.data[rowNo][colNo],rowNo=rowNo,colNo=colNo)

                self._addBarLabel(lg,rowNo,colNo,x,y,width,height)

            for linePts in yieldNoneSplits(linePts.__self__):
                if linePts:
                    lines(PolyLine(linePts,
                            strokeColor=rowStyle.strokeColor or rowStyle.fillColor,
                            strokeWidth=rowStyle.strokeWidth,
                            strokeDashArray = rowStyle.strokeDashArray))

        for pl in lines.__self__:
            g.add(pl)
        for sym in lineSyms.__self__:
            g.add(sym)

    def _computeLabelPosition(self, text, label, rowNo, colNo, x, y, width, height):
        if label.visible:
            labelWidth = stringWidth(text, label.fontName, label.fontSize)
            flipXY = self._flipXY
            if flipXY:
                y0, x0, pm = self._labelXY(label,y,x,height,width)
            else:
                x0, y0, pm = self._labelXY(label,x,y,width,height)
            fixedEnd = getattr(label,'fixedEnd', None)
            if fixedEnd is not None:
                v = fixedEnd._getValue(self,pm)
                x00, y00 = x0, y0
                if flipXY:
                    x0 = v
                else:
                    y0 = v
            else:
                if flipXY:
                    x00 = x0
                    y00 = y+height/2.0
                else:
                    x00 = x+width/2.0
                    y00 = y0
            fixedStart = getattr(label,'fixedStart', None)
            if fixedStart is not None:
                v = fixedStart._getValue(self,pm)
                if flipXY:
                    x00 = v
                else:
                    y00 = v

            if pm<0:
                if flipXY:
                    dx = -2*label.dx
                    dy = 0
                else:
                    dy = -2*label.dy
                    dx = 0
            else:
                dy = dx = 0
            label.setOrigin(x0+dx, y0+dy)
            label.setText(text)
            return pm,label.getBounds()

    def _computeBarPositions(self):
        """Information function, can be called by charts which want to with space around bars"""
        cA, vA = self.categoryAxis, self.valueAxis
        if vA: vA.joinAxis = cA
        if cA: cA.joinAxis = vA
        if self._flipXY:
            cA.setPosition(self._drawBegin(self.x,self.width), self.y, self.height)
        else:
            cA.setPosition(self.x, self._drawBegin(self.y,self.height), self.width)
        cA.configure(self._configureData)
        self.calcBarPositions()

    def _computeMaxSpace(self,size,required):
        '''helper for madmen who want to put stuff inside their barcharts
        basically after _computebarPositions we slide a line of length size
        down the bar profile on either side of the bars to find the
        maximum space. If the space at any point is >= required then we're
        done. Otherwise we return the largest space location and amount.
        '''
        flipXY = self._flipXY
        self._computeBarPositions()
        lenData = len(self.data)
        BP = self._barPositions
        C = []
        aC = C.append
        if flipXY:
            lo = self.x
            hi = lo + self.width
            end = self.y+self.height
            for bp in BP:
                for x, y, w, h in bp:
                    v = x+w
                    z = y+h
                    aC((min(y,z),max(y,z), min(x,v) - lo, hi - max(x,v)))
        else:
            lo = self.y
            hi = lo + self.height
            end = self.x+self.width
            for bp in BP:
                for x, y, w, h in bp:
                    v = y+h
                    z = x+w
                    aC((min(x,z), max(x,z), min(y,v) - lo, hi - max(y,v)))
        C.sort()
        R = [C[0]]
        for c in C:
            r = R[-1]
            if r[0]<c[1] and c[0]<r[1]: #merge overlapping space
                R[-1] = (min(r[0],c[0]),max(r[1],c[1]),min(r[2],c[2]),min(r[3],c[3]))
            else:
                R.append(c)
        C = R
        maxS = -0x7fffffff
        maxP = None
        nC = len(C)
        for i,ci in enumerate(C):
            v0 = ci[0]
            v1 = v0+size
            if v1>end: break
            j = i
            alo = ahi = 0x7fffffff
            while j<nC and C[j][1]<=v1:
                alo = min(C[j][2],alo)
                ahi = min(C[j][3],ahi)
                j += 1
            if alo>ahi:
                if alo>maxS:
                    maxS = alo
                    maxP = flipXY and (lo,v0,lo+alo,v0+size,0) or (v0,lo,v0+size,lo+alo,0)
                    if maxS >= required: break
            elif ahi>maxS:
                maxS = ahi
                maxP = flipXY and (hi-ahi,v0,hi,v0+size,1) or (v0,hi-ahi,v0+size,hi,1)
                if maxS >= required: break
        return maxS, maxP

    def _computeSimpleBarLabelPositions(self):
        """Information function, can be called by charts which want to mess with labels"""
        cA, vA = self.categoryAxis, self.valueAxis
        if vA: vA.joinAxis = cA
        if cA: cA.joinAxis = vA
        if self._flipXY:
            cA.setPosition(self._drawBegin(self.x,self.width), self.y, self.height)
        else:
            cA.setPosition(self.x, self._drawBegin(self.y,self.height), self.width)
        cA.configure(self._configureData)
        self.calcBarPositions()

        bars = self.bars
        R = [].append
        BP = self._barPositions
        for rowNo, row in enumerate(BP):
            C = [].append
            for colNo, (x, y, width, height) in enumerate(row):
                if None in (width,height):
                    na = self.naLabel
                    if na and na.text:
                        na = copy.copy(na)
                        v = self.valueAxis._valueMax<=0 and -1e-8 or 1e-8
                        if width is None: width = v
                        if height is None: height = v
                        C(self._computeLabelPosition(na.text, na, rowNo, colNo, x, y, width, height))
                    else:
                        C(None)
                else:
                    text = self._getLabelText(rowNo,colNo)
                    if text:
                        C(self._computeLabelPosition(text, self.barLabels[(rowNo, colNo)], rowNo, colNo, x, y, width, height))
                    else:
                        C(None)
            R(C.__self__)
        return R.__self__

    def makeBars(self):
        g = Group()
        lg = Group()
        self._makeBars(g,lg)
        g.add(lg)
        return g

    def _desiredCategoryAxisLength(self):
        '''for dynamically computing the desired category axis length'''
        style = self.categoryAxis.style
        data = self.data
        n = len(data)
        m = max(list(map(len,data)))
        if style=='parallel':
            groupWidth = (n-1)*self.barSpacing+n*self.barWidth
        else:
            groupWidth = self.barWidth
        return m*(self.groupSpacing+groupWidth)

    def draw(self):
        cA, vA = self.categoryAxis, self.valueAxis
        if vA: vA.joinAxis = cA
        if cA: cA.joinAxis = vA
        if self._flipXY:
            cA.setPosition(self._drawBegin(self.x,self.width), self.y, self.height)
        else:
            cA.setPosition(self.x, self._drawBegin(self.y,self.height), self.width)
        return self._drawFinish()

class VerticalBarChart(BarChart):
    "Vertical bar chart with multiple side-by-side bars."
    _flipXY = 0

class HorizontalBarChart(BarChart):
    "Horizontal bar chart with multiple side-by-side bars."
    _flipXY = 1

class _FakeGroup:
    def __init__(self, cmp=None):
        self._data = []
        self._key = functools.cmp_to_key(cmp)

    def add(self,what):
        self._data.append(what)

    def value(self):
        return self._data

    def sort(self):
        self._data.sort(key=self._key)

class BarChart3D(BarChart):
    _attrMap = AttrMap(BASE=BarChart,
        theta_x = AttrMapValue(isNumber, desc='dx/dz'),
        theta_y = AttrMapValue(isNumber, desc='dy/dz'),
        zDepth = AttrMapValue(isNumber, desc='depth of an individual series'),
        zSpace = AttrMapValue(isNumber, desc='z gap around series'),
        )
    theta_x = .5
    theta_y = .5
    zDepth = None
    zSpace = None

    def calcBarPositions(self):
        BarChart.calcBarPositions(self)
        seriesCount = self._seriesCount
        zDepth = self.zDepth
        if zDepth is None: zDepth = self.barWidth
        zSpace = self.zSpace
        if zSpace is None: zSpace = self.barSpacing
        if self.categoryAxis.style=='parallel_3d':
            _3d_depth = seriesCount*zDepth+(seriesCount+1)*zSpace
        else:
            _3d_depth = zDepth + 2*zSpace
        _3d_depth *= self._normFactor
        self._3d_dx = self.theta_x*_3d_depth
        self._3d_dy = self.theta_y*_3d_depth

    def _calc_z0(self,rowNo):
        zDepth = self.zDepth
        if zDepth is None: zDepth = self.barWidth
        zSpace = self.zSpace
        if zSpace is None: zSpace = self.barSpacing
        if self.categoryAxis.style=='parallel_3d':
            z0 = self._normFactor*(rowNo*(zDepth+zSpace)+zSpace)
        else:
            z0 = self._normFactor*zSpace
        return z0

    def _makeBar(self,g,x,y,width,height,rowNo,style):
        zDepth = self.zDepth
        if zDepth is None: zDepth = self.barWidth
        zSpace = self.zSpace
        if zSpace is None: zSpace = self.barSpacing
        z0 = self._calc_z0(rowNo)
        z1 = z0 + zDepth*self._normFactor
        if width<0:
            x += width
            width = -width
        x += z0*self.theta_x
        y += z0*self.theta_y
        if self._flipXY:
            y += zSpace
        else:
            x += zSpace
        g.add((0,z0,z1,x,y,width,height,rowNo,style))

    def _addBarLabel(self, g, rowNo, colNo, x, y, width, height):
        z0 = self._calc_z0(rowNo)
        zSpace = self.zSpace
        if zSpace is None: zSpace = self.barSpacing
        z1 = z0
        x += z0*self.theta_x
        y += z0*self.theta_y
        if self._flipXY:
            y += zSpace
        else:
            x += zSpace
        g.add((1,z0,z1,x,y,width,height,rowNo,colNo))

    def makeBars(self):
        from reportlab.graphics.charts.utils3d import _draw_3d_bar
        fg = _FakeGroup(cmp=self._cmpZ)
        self._makeBars(fg,fg)
        fg.sort()
        g = Group()
        theta_x = self.theta_x
        theta_y = self.theta_y
        fg_value = fg.value()
        cAStyle = self.categoryAxis.style
        if cAStyle=='stacked':
            fg_value.reverse()
        elif cAStyle=='mixed':
            fg_value = [_[1] for _ in sorted((((t[1],t[2],t[3],t[4]),t) for t in fg_value))]

        for t in fg_value:
            if t[0]==0:
                z0,z1,x,y,width,height,rowNo,style = t[1:]
                dz = z1 - z0
                _draw_3d_bar(g, x, x+width, y, y+height, dz*theta_x, dz*theta_y,
                            fillColor=style.fillColor, fillColorShaded=None,
                            strokeColor=style.strokeColor, strokeWidth=style.strokeWidth,
                            shading=0.45)
        for t in fg_value:
            if t==1:
                z0,z1,x,y,width,height,rowNo,colNo = t[1:]
                BarChart._addBarLabel(self,g,rowNo,colNo,x,y,width,height)
        return g

class VerticalBarChart3D(BarChart3D,VerticalBarChart):
    _cmpZ=lambda self,a,b:cmp((-a[1],a[3],a[0],-a[4]),(-b[1],b[3],b[0],-b[4]))

class HorizontalBarChart3D(BarChart3D,HorizontalBarChart):
    _cmpZ = lambda self,a,b: cmp((-a[1],a[4],a[0],-a[3]),(-b[1],b[4],b[0],-b[3]))   #t, z0, z1, x, y = a[:5]

# Vertical samples.
def sampleV0a():
    "A slightly pathologic bar chart with only TWO data items."

    drawing = Drawing(400, 200)

    data = [(13, 20)]

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data

    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'ne'
    bc.categoryAxis.labels.dx = 8
    bc.categoryAxis.labels.dy = -2
    bc.categoryAxis.labels.angle = 30
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleV0b():
    "A pathologic bar chart with only ONE data item."

    drawing = Drawing(400, 200)

    data = [(42,)]

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 50
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'ne'
    bc.categoryAxis.labels.dx = 8
    bc.categoryAxis.labels.dy = -2
    bc.categoryAxis.labels.angle = 30
    bc.categoryAxis.categoryNames = ['Jan-99']

    drawing.add(bc)

    return drawing


def sampleV0c():
    "A really pathologic bar chart with NO data items at all!"

    drawing = Drawing(400, 200)

    data = [()]

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'ne'
    bc.categoryAxis.labels.dx = 8
    bc.categoryAxis.labels.dy = -2
    bc.categoryAxis.categoryNames = []

    drawing.add(bc)

    return drawing


def sampleV1():
    "Sample of multi-series bar chart."

    drawing = Drawing(400, 200)

    data = [
            (13, 5, 20, 22, 37, 45, 19, 4),
            (14, 6, 21, 23, 38, 46, 20, 5)
            ]

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'ne'
    bc.categoryAxis.labels.dx = 8
    bc.categoryAxis.labels.dy = -2
    bc.categoryAxis.labels.angle = 30

    catNames = 'Jan Feb Mar Apr May Jun Jul Aug'.split(' ')
    catNames = [n+'-99' for n in catNames]
    bc.categoryAxis.categoryNames = catNames
    drawing.add(bc)

    return drawing


def sampleV2a():
    "Sample of multi-series bar chart."

    data = [(2.4, -5.7, 2, 5, 9.2),
            (0.6, -4.9, -3, 4, 6.8)
            ]

    labels = ("Q3 2000", "Year to Date", "12 months",
              "Annualised\n3 years", "Since 07.10.99")

    drawing = Drawing(400, 200)

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 120
    bc.width = 300
    bc.data = data

    bc.barSpacing = 0
    bc.groupSpacing = 10
    bc.barWidth = 10

    bc.valueAxis.valueMin = -15
    bc.valueAxis.valueMax = +15
    bc.valueAxis.valueStep = 5
    bc.valueAxis.labels.fontName = 'Helvetica'
    bc.valueAxis.labels.fontSize = 8
    bc.valueAxis.labels.boxAnchor = 'n'   # irrelevant (becomes 'c')
    bc.valueAxis.labels.textAnchor = 'middle'

    bc.categoryAxis.categoryNames = labels
    bc.categoryAxis.labels.fontName = 'Helvetica'
    bc.categoryAxis.labels.fontSize = 8
    bc.categoryAxis.labels.dy = -60

    drawing.add(bc)

    return drawing


def sampleV2b():
    "Sample of multi-series bar chart."

    data = [(2.4, -5.7, 2, 5, 9.2),
            (0.6, -4.9, -3, 4, 6.8)
            ]

    labels = ("Q3 2000", "Year to Date", "12 months",
              "Annualised\n3 years", "Since 07.10.99")

    drawing = Drawing(400, 200)

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 120
    bc.width = 300
    bc.data = data

    bc.barSpacing = 5
    bc.groupSpacing = 10
    bc.barWidth = 10

    bc.valueAxis.valueMin = -15
    bc.valueAxis.valueMax = +15
    bc.valueAxis.valueStep = 5
    bc.valueAxis.labels.fontName = 'Helvetica'
    bc.valueAxis.labels.fontSize = 8
    bc.valueAxis.labels.boxAnchor = 'n'   # irrelevant (becomes 'c')
    bc.valueAxis.labels.textAnchor = 'middle'

    bc.categoryAxis.categoryNames = labels
    bc.categoryAxis.labels.fontName = 'Helvetica'
    bc.categoryAxis.labels.fontSize = 8
    bc.categoryAxis.labels.dy = -60

    drawing.add(bc)

    return drawing


def sampleV2c():
    "Sample of multi-series bar chart."

    data = [(2.4, -5.7, 2, 5, 9.99),
            (0.6, -4.9, -3, 4, 9.99)
            ]

    labels = ("Q3 2000", "Year to Date", "12 months",
              "Annualised\n3 years", "Since 07.10.99")

    drawing = Drawing(400, 200)

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 120
    bc.width = 300
    bc.data = data

    bc.barSpacing = 2
    bc.groupSpacing = 10
    bc.barWidth = 10

    bc.valueAxis.valueMin = -15
    bc.valueAxis.valueMax = +15
    bc.valueAxis.valueStep = 5
    bc.valueAxis.labels.fontName = 'Helvetica'
    bc.valueAxis.labels.fontSize = 8

    bc.categoryAxis.categoryNames = labels
    bc.categoryAxis.labels.fontName = 'Helvetica'
    bc.categoryAxis.labels.fontSize = 8
    bc.valueAxis.labels.boxAnchor = 'n'
    bc.valueAxis.labels.textAnchor = 'middle'
    bc.categoryAxis.labels.dy = -60

    bc.barLabels.nudge = 10

    bc.barLabelFormat = '%0.2f'
    bc.barLabels.dx = 0
    bc.barLabels.dy = 0
    bc.barLabels.boxAnchor = 'n'  # irrelevant (becomes 'c')
    bc.barLabels.fontName = 'Helvetica'
    bc.barLabels.fontSize = 6

    drawing.add(bc)

    return drawing


def sampleV3():
    "Faked horizontal bar chart using a vertical real one (deprecated)."

    names = ("UK Equities", "US Equities", "European Equities", "Japanese Equities",
              "Pacific (ex Japan) Equities", "Emerging Markets Equities",
              "UK Bonds", "Overseas Bonds", "UK Index-Linked", "Cash")

    series1 = (-1.5, 0.3, 0.5, 1.0, 0.8, 0.7, 0.4, 0.1, 1.0, 0.3)
    series2 = (0.0, 0.33, 0.55, 1.1, 0.88, 0.77, 0.44, 0.11, 1.10, 0.33)

    assert len(names) == len(series1), "bad data"
    assert len(names) == len(series2), "bad data"

    drawing = Drawing(400, 200)

    bc = VerticalBarChart()
    bc.x = 0
    bc.y = 0
    bc.height = 100
    bc.width = 150
    bc.data = (series1,)
    bc.bars.fillColor = colors.green

    bc.barLabelFormat = '%0.2f'
    bc.barLabels.dx = 0
    bc.barLabels.dy = 0
    bc.barLabels.boxAnchor = 'w' # irrelevant (becomes 'c')
    bc.barLabels.angle = 90
    bc.barLabels.fontName = 'Helvetica'
    bc.barLabels.fontSize = 6
    bc.barLabels.nudge = 10

    bc.valueAxis.visible = 0
    bc.valueAxis.valueMin = -2
    bc.valueAxis.valueMax = +2
    bc.valueAxis.valueStep = 1

    bc.categoryAxis.tickUp = 0
    bc.categoryAxis.tickDown = 0
    bc.categoryAxis.categoryNames = names
    bc.categoryAxis.labels.angle = 90
    bc.categoryAxis.labels.boxAnchor = 'w'
    bc.categoryAxis.labels.dx = 0
    bc.categoryAxis.labels.dy = -125
    bc.categoryAxis.labels.fontName = 'Helvetica'
    bc.categoryAxis.labels.fontSize = 6

    g = Group(bc)
    g.translate(100, 175)
    g.rotate(-90)

    drawing.add(g)

    return drawing


def sampleV4a():
    "A bar chart showing value axis region starting at *exactly* zero."

    drawing = Drawing(400, 200)

    data = [(13, 20)]

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data

    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'n'
    bc.categoryAxis.labels.dy = -5
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleV4b():
    "A bar chart showing value axis region starting *below* zero."

    drawing = Drawing(400, 200)

    data = [(13, 20)]

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data

    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = -10
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'n'
    bc.categoryAxis.labels.dy = -5
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleV4c():
    "A bar chart showing value axis region staring *above* zero."

    drawing = Drawing(400, 200)

    data = [(13, 20)]

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data

    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 10
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'n'
    bc.categoryAxis.labels.dy = -5
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleV4d():
    "A bar chart showing value axis region entirely *below* zero."

    drawing = Drawing(400, 200)

    data = [(-13, -20)]

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data

    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = -30
    bc.valueAxis.valueMax = -10
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'n'
    bc.categoryAxis.labels.dy = -5
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


###

##dataSample5 = [(10, 20), (20, 30), (30, 40), (40, 50), (50, 60)]
##dataSample5 = [(10, 60), (20, 50), (30, 40), (40, 30), (50, 20)]
dataSample5 = [(10, 60), (20, 50), (30, 40), (40, 30)]

def sampleV5a():
    "A simple bar chart with no expressed spacing attributes."

    drawing = Drawing(400, 200)

    data = dataSample5

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'n'
    bc.categoryAxis.labels.dy = -5
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleV5b():
    "A simple bar chart with proportional spacing."

    drawing = Drawing(400, 200)

    data = dataSample5

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.useAbsolute = 0
    bc.barWidth = 40
    bc.groupSpacing = 20
    bc.barSpacing = 10

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'n'
    bc.categoryAxis.labels.dy = -5
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleV5c1():
    "Make sampe simple bar chart but with absolute spacing."

    drawing = Drawing(400, 200)

    data = dataSample5

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.useAbsolute = 1
    bc.barWidth = 40
    bc.groupSpacing = 0
    bc.barSpacing = 0

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'n'
    bc.categoryAxis.labels.dy = -5
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleV5c2():
    "Make sampe simple bar chart but with absolute spacing."

    drawing = Drawing(400, 200)

    data = dataSample5

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.useAbsolute = 1
    bc.barWidth = 40
    bc.groupSpacing = 20
    bc.barSpacing = 0

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'n'
    bc.categoryAxis.labels.dy = -5
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleV5c3():
    "Make sampe simple bar chart but with absolute spacing."

    drawing = Drawing(400, 200)

    data = dataSample5

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.useAbsolute = 1
    bc.barWidth = 40
    bc.groupSpacing = 0
    bc.barSpacing = 10

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'n'
    bc.categoryAxis.labels.dy = -5
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleV5c4():
    "Make sampe simple bar chart but with absolute spacing."

    drawing = Drawing(400, 200)

    data = dataSample5

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.useAbsolute = 1
    bc.barWidth = 40
    bc.groupSpacing = 20
    bc.barSpacing = 10

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'n'
    bc.categoryAxis.labels.dy = -5
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


# Horizontal samples

def sampleH0a():
    "Make a slightly pathologic bar chart with only TWO data items."

    drawing = Drawing(400, 200)

    data = [(13, 20)]

    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data

    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'se'
    bc.categoryAxis.labels.angle = 30
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleH0b():
    "Make a pathologic bar chart with only ONE data item."

    drawing = Drawing(400, 200)

    data = [(42,)]

    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 50
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'se'
    bc.categoryAxis.labels.angle = 30
    bc.categoryAxis.categoryNames = ['Jan-99']

    drawing.add(bc)

    return drawing


def sampleH0c():
    "Make a really pathologic bar chart with NO data items at all!"

    drawing = Drawing(400, 200)

    data = [()]

    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'se'
    bc.categoryAxis.labels.angle = 30
    bc.categoryAxis.categoryNames = []

    drawing.add(bc)

    return drawing


def sampleH1():
    "Sample of multi-series bar chart."

    drawing = Drawing(400, 200)

    data = [
            (13, 5, 20, 22, 37, 45, 19, 4),
            (14, 6, 21, 23, 38, 46, 20, 5)
            ]

    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'e'
    catNames = 'Jan Feb Mar Apr May Jun Jul Aug'.split(' ')
    catNames = [n+'-99' for n in catNames]
    bc.categoryAxis.categoryNames = catNames
    drawing.add(bc, 'barchart')

    return drawing


def sampleH2a():
    "Sample of multi-series bar chart."

    data = [(2.4, -5.7, 2, 5, 9.2),
            (0.6, -4.9, -3, 4, 6.8)
            ]

    labels = ("Q3 2000", "Year to Date", "12 months",
              "Annualised\n3 years", "Since 07.10.99")

    drawing = Drawing(400, 200)

    bc = HorizontalBarChart()
    bc.x = 80
    bc.y = 50
    bc.height = 120
    bc.width = 300
    bc.data = data

    bc.barSpacing = 0
    bc.groupSpacing = 10
    bc.barWidth = 10

    bc.valueAxis.valueMin = -15
    bc.valueAxis.valueMax = +15
    bc.valueAxis.valueStep = 5
    bc.valueAxis.labels.fontName = 'Helvetica'
    bc.valueAxis.labels.fontSize = 8
    bc.valueAxis.labels.boxAnchor = 'n'   # irrelevant (becomes 'c')
    bc.valueAxis.labels.textAnchor = 'middle'
    bc.valueAxis.configure(bc.data)

    bc.categoryAxis.categoryNames = labels
    bc.categoryAxis.labels.fontName = 'Helvetica'
    bc.categoryAxis.labels.fontSize = 8
    bc.categoryAxis.labels.dx = -150

    drawing.add(bc)

    return drawing


def sampleH2b():
    "Sample of multi-series bar chart."

    data = [(2.4, -5.7, 2, 5, 9.2),
            (0.6, -4.9, -3, 4, 6.8)
            ]

    labels = ("Q3 2000", "Year to Date", "12 months",
              "Annualised\n3 years", "Since 07.10.99")

    drawing = Drawing(400, 200)

    bc = HorizontalBarChart()
    bc.x = 80
    bc.y = 50
    bc.height = 120
    bc.width = 300
    bc.data = data

    bc.barSpacing = 5
    bc.groupSpacing = 10
    bc.barWidth = 10

    bc.valueAxis.valueMin = -15
    bc.valueAxis.valueMax = +15
    bc.valueAxis.valueStep = 5
    bc.valueAxis.labels.fontName = 'Helvetica'
    bc.valueAxis.labels.fontSize = 8
    bc.valueAxis.labels.boxAnchor = 'n'   # irrelevant (becomes 'c')
    bc.valueAxis.labels.textAnchor = 'middle'

    bc.categoryAxis.categoryNames = labels
    bc.categoryAxis.labels.fontName = 'Helvetica'
    bc.categoryAxis.labels.fontSize = 8
    bc.categoryAxis.labels.dx = -150

    drawing.add(bc)

    return drawing


def sampleH2c():
    "Sample of multi-series bar chart."

    data = [(2.4, -5.7, 2, 5, 9.99),
            (0.6, -4.9, -3, 4, 9.99)
            ]

    labels = ("Q3 2000", "Year to Date", "12 months",
              "Annualised\n3 years", "Since 07.10.99")

    drawing = Drawing(400, 200)

    bc = HorizontalBarChart()
    bc.x = 80
    bc.y = 50
    bc.height = 120
    bc.width = 300
    bc.data = data

    bc.barSpacing = 2
    bc.groupSpacing = 10
    bc.barWidth = 10

    bc.valueAxis.valueMin = -15
    bc.valueAxis.valueMax = +15
    bc.valueAxis.valueStep = 5
    bc.valueAxis.labels.fontName = 'Helvetica'
    bc.valueAxis.labels.fontSize = 8
    bc.valueAxis.labels.boxAnchor = 'n'
    bc.valueAxis.labels.textAnchor = 'middle'

    bc.categoryAxis.categoryNames = labels
    bc.categoryAxis.labels.fontName = 'Helvetica'
    bc.categoryAxis.labels.fontSize = 8
    bc.categoryAxis.labels.dx = -150

    bc.barLabels.nudge = 10

    bc.barLabelFormat = '%0.2f'
    bc.barLabels.dx = 0
    bc.barLabels.dy = 0
    bc.barLabels.boxAnchor = 'n'  # irrelevant (becomes 'c')
    bc.barLabels.fontName = 'Helvetica'
    bc.barLabels.fontSize = 6

    drawing.add(bc)

    return drawing


def sampleH3():
    "A really horizontal bar chart (compared to the equivalent faked one)."

    names = ("UK Equities", "US Equities", "European Equities", "Japanese Equities",
              "Pacific (ex Japan) Equities", "Emerging Markets Equities",
              "UK Bonds", "Overseas Bonds", "UK Index-Linked", "Cash")

    series1 = (-1.5, 0.3, 0.5, 1.0, 0.8, 0.7, 0.4, 0.1, 1.0, 0.3)
    series2 = (0.0, 0.33, 0.55, 1.1, 0.88, 0.77, 0.44, 0.11, 1.10, 0.33)

    assert len(names) == len(series1), "bad data"
    assert len(names) == len(series2), "bad data"

    drawing = Drawing(400, 200)

    bc = HorizontalBarChart()
    bc.x = 100
    bc.y = 20
    bc.height = 150
    bc.width = 250
    bc.data = (series1,)
    bc.bars.fillColor = colors.green

    bc.barLabelFormat = '%0.2f'
    bc.barLabels.dx = 0
    bc.barLabels.dy = 0
    bc.barLabels.boxAnchor = 'w' # irrelevant (becomes 'c')
    bc.barLabels.fontName = 'Helvetica'
    bc.barLabels.fontSize = 6
    bc.barLabels.nudge = 10

    bc.valueAxis.visible = 0
    bc.valueAxis.valueMin = -2
    bc.valueAxis.valueMax = +2
    bc.valueAxis.valueStep = 1

    bc.categoryAxis.tickLeft = 0
    bc.categoryAxis.tickRight = 0
    bc.categoryAxis.categoryNames = names
    bc.categoryAxis.labels.boxAnchor = 'w'
    bc.categoryAxis.labels.dx = -170
    bc.categoryAxis.labels.fontName = 'Helvetica'
    bc.categoryAxis.labels.fontSize = 6

    g = Group(bc)
    drawing.add(g)

    return drawing


def sampleH4a():
    "A bar chart showing value axis region starting at *exactly* zero."

    drawing = Drawing(400, 200)

    data = [(13, 20)]

    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data

    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleH4b():
    "A bar chart showing value axis region starting *below* zero."

    drawing = Drawing(400, 200)

    data = [(13, 20)]

    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data

    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = -10
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleH4c():
    "A bar chart showing value axis region starting *above* zero."

    drawing = Drawing(400, 200)

    data = [(13, 20)]

    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data

    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 10
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleH4d():
    "A bar chart showing value axis region entirely *below* zero."

    drawing = Drawing(400, 200)

    data = [(-13, -20)]

    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data

    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = -30
    bc.valueAxis.valueMax = -10
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


dataSample5 = [(10, 60), (20, 50), (30, 40), (40, 30)]

def sampleH5a():
    "A simple bar chart with no expressed spacing attributes."

    drawing = Drawing(400, 200)

    data = dataSample5

    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleH5b():
    "A simple bar chart with proportional spacing."

    drawing = Drawing(400, 200)

    data = dataSample5

    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.useAbsolute = 0
    bc.barWidth = 40
    bc.groupSpacing = 20
    bc.barSpacing = 10

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleH5c1():
    "A simple bar chart with absolute spacing."

    drawing = Drawing(400, 200)

    data = dataSample5

    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.useAbsolute = 1
    bc.barWidth = 10
    bc.groupSpacing = 0
    bc.barSpacing = 0

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleH5c2():
    "Simple bar chart with absolute spacing."

    drawing = Drawing(400, 200)

    data = dataSample5

    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.useAbsolute = 1
    bc.barWidth = 10
    bc.groupSpacing = 20
    bc.barSpacing = 0

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleH5c3():
    "Simple bar chart with absolute spacing."

    drawing = Drawing(400, 200)

    data = dataSample5

    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 20
    bc.height = 155
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.useAbsolute = 1
    bc.barWidth = 10
    bc.groupSpacing = 0
    bc.barSpacing = 2

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing


def sampleH5c4():
    "Simple bar chart with absolute spacing."

    drawing = Drawing(400, 200)

    data = dataSample5

    bc = HorizontalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.useAbsolute = 1
    bc.barWidth = 10
    bc.groupSpacing = 20
    bc.barSpacing = 10

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    drawing.add(bc)

    return drawing

def sampleSymbol1():
    "Simple bar chart using symbol attribute."

    drawing = Drawing(400, 200)

    data = dataSample5

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.barWidth = 10
    bc.groupSpacing = 15
    bc.barSpacing = 3

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 15

    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    from reportlab.graphics.widgets.grids import ShadedRect
    sym1 = ShadedRect()
    sym1.fillColorStart = colors.black
    sym1.fillColorEnd = colors.blue
    sym1.orientation = 'horizontal'
    sym1.strokeWidth = 0

    sym2 = ShadedRect()
    sym2.fillColorStart = colors.black
    sym2.fillColorEnd = colors.pink
    sym2.orientation = 'horizontal'
    sym2.strokeWidth = 0

    sym3 = ShadedRect()
    sym3.fillColorStart = colors.blue
    sym3.fillColorEnd = colors.white
    sym3.orientation = 'vertical'
    sym3.cylinderMode = 1
    sym3.strokeWidth = 0

    bc.bars.symbol = sym1
    bc.bars[2].symbol = sym2
    bc.bars[3].symbol = sym3

    drawing.add(bc)

    return drawing

def sampleStacked1():
    "Simple bar chart using symbol attribute."

    drawing = Drawing(400, 200)

    data = dataSample5

    bc = VerticalBarChart()
    bc.categoryAxis.style = 'stacked'
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.barWidth = 10
    bc.groupSpacing = 15
    bc.valueAxis.valueMin = 0

    bc.categoryAxis.labels.boxAnchor = 'e'
    bc.categoryAxis.categoryNames = ['Ying', 'Yang']

    from reportlab.graphics.widgets.grids import ShadedRect
    bc.bars.symbol = ShadedRect()
    bc.bars.symbol.fillColorStart = colors.red
    bc.bars.symbol.fillColorEnd = colors.white
    bc.bars.symbol.orientation = 'vertical'
    bc.bars.symbol.cylinderMode = 1
    bc.bars.symbol.strokeWidth = 0

    bc.bars[1].symbol = ShadedRect()
    bc.bars[1].symbol.fillColorStart = colors.magenta
    bc.bars[1].symbol.fillColorEnd = colors.white
    bc.bars[1].symbol.orientation = 'vertical'
    bc.bars[1].symbol.cylinderMode = 1
    bc.bars[1].symbol.strokeWidth = 0

    bc.bars[2].symbol = ShadedRect()
    bc.bars[2].symbol.fillColorStart = colors.green
    bc.bars[2].symbol.fillColorEnd = colors.white
    bc.bars[2].symbol.orientation = 'vertical'
    bc.bars[2].symbol.cylinderMode = 1
    bc.bars[2].symbol.strokeWidth = 0

    bc.bars[3].symbol = ShadedRect()
    bc.bars[3].symbol.fillColorStart = colors.blue
    bc.bars[3].symbol.fillColorEnd = colors.white
    bc.bars[3].symbol.orientation = 'vertical'
    bc.bars[3].symbol.cylinderMode = 1
    bc.bars[3].symbol.strokeWidth = 0

    drawing.add(bc)

    return drawing

#class version of function sampleH5c4 above
class SampleH5c4(Drawing):
    "Simple bar chart with absolute spacing."

    def __init__(self,width=400,height=200,*args,**kw):
        Drawing.__init__(self,width,height,*args,**kw)
        bc = HorizontalBarChart()
        bc.x = 50
        bc.y = 50
        bc.height = 125
        bc.width = 300
        bc.data = dataSample5
        bc.strokeColor = colors.black

        bc.useAbsolute = 1
        bc.barWidth = 10
        bc.groupSpacing = 20
        bc.barSpacing = 10

        bc.valueAxis.valueMin = 0
        bc.valueAxis.valueMax = 60
        bc.valueAxis.valueStep = 15

        bc.categoryAxis.labels.boxAnchor = 'e'
        bc.categoryAxis.categoryNames = ['Ying', 'Yang']

        self.add(bc,name='HBC')
        bc._computeSimpleBarLabelPositions()
