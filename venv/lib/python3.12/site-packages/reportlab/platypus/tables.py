#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/platypus/tables.py
__all__= (
        'Table',
        'TableStyle',
        'CellStyle',
        'LongTable',
        )
__version__='3.5.21'

__doc__="""
Tables are created by passing the constructor a tuple of column widths, a tuple of row heights and the data in
row order. Drawing of the table can be controlled by using a TableStyle instance. This allows control of the
color and weight of the lines (if any), and the font, alignment and padding of the text.

None values in the sequence of row heights or column widths, mean that the corresponding rows
or columns should be automatically sized.

All the cell values should be convertible to strings; embedded newline '\\n' characters
cause the value to wrap (ie are like a traditional linefeed).

See the test output from running this module as a script for a discussion of the method for constructing
tables and table styles.
"""
from reportlab.platypus.flowables import Flowable, Preformatted
from reportlab import rl_config
from reportlab.lib.styles import PropertySet, ParagraphStyle, _baseFontName
from reportlab.lib import colors
from reportlab.lib.utils import annotateException, IdentStr, flatten, isStr, asNative, strTypes, __UNSET__
from reportlab.lib.validators import isListOfNumbersOrNone
from reportlab.lib.rl_accel import fp_str
from reportlab.lib.abag import ABag as CellFrame
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus.doctemplate import Indenter, NullActionFlowable
from reportlab.platypus.flowables import LIIndenter
from collections import namedtuple

LINECAPS={None: None, 'butt':0,'round':1,'projecting':2,'squared':2}
LINEJOINS={None: None, 'miter':0, 'mitre':0, 'round':1,'bevel':2}

class CellStyle(PropertySet):
    fontname = _baseFontName
    fontsize = 10
    leading = 12
    leftPadding = 6
    rightPadding = 6
    topPadding = 3
    bottomPadding = 3
    firstLineIndent = 0
    color = 'black'
    alignment = 'LEFT'
    background = 'white'
    valign = "BOTTOM"
    href = None
    destination = None
    def __init__(self, name, parent=None):
        self.name = name
        if parent is not None:
            parent.copy(self)
    def copy(self, result=None):
        if result is None:
            result = CellStyle(self.name)
        for name in dir(self):
            if name.startswith('_'): continue
            setattr(result, name, getattr(self, name))
        return result

class TableStyle:
    def __init__(self, cmds=None, parent=None, **kw):
        #handle inheritance from parent first.
        if parent:
            # copy the parents list at construction time
            pcmds = parent.getCommands()[:]
            self._opts = parent._opts
            for a in ('spaceBefore','spaceAfter'):
                if hasattr(parent,a):
                    setattr(self,a,getattr(parent,a))
        else:
            pcmds = []

        self._cmds = pcmds + list(cmds or [])
        self._opts={}
        self._opts.update(kw)

    def add(self, *cmd):
        self._cmds.append(cmd)
    def __repr__(self):
        return "TableStyle(\n%s\n) # end TableStyle" % "  \n".join(map(repr, self._cmds))
    def getCommands(self):
        return self._cmds

def _rowLen(x):
    return not isinstance(x,(tuple,list)) and 1 or len(x)

def _calc_pc(V,avail):
    '''check list V for percentage or * values
    1) absolute values go through unchanged
    2) percentages are used as weights for unconsumed space
    3) if no None values were seen '*' weights are
    set equally with unclaimed space
    otherwise * weights are assigned as None'''
    R = []
    r = R.append
    I = []
    i = I.append
    J = []
    j = J.append
    s = avail
    w = n = 0.
    for v in V:
        if isinstance(v,strTypes):
            v = str(v).strip()
            if not v:
                v = None
                n += 1
            elif v.endswith('%'):
                v = float(v[:-1])
                w += v
                i(len(R))
            elif v=='*':
                j(len(R))
            else:
                v = float(v)
                s -= v
        elif v is None:
            n += 1
        else:
            s -= v
        r(v)
    s = max(0.,s)
    f = s/max(100.,w)
    for i in I:
        R[i] *= f
        s -= R[i]
    s = max(0.,s)
    m = len(J)
    if m:
        v =  n==0 and s/m or None
        for j in J:
            R[j] = v
    return R

def _calcBezierPoints(P, kind):
    '''calculate all or half of a bezier curve
    kind==0 all, 1=first half else second half''' 
    if kind==0:
        return P
    else:
        Q0 = (0.5*(P[0][0]+P[1][0]),0.5*(P[0][1]+P[1][1]))
        Q1 = (0.5*(P[1][0]+P[2][0]),0.5*(P[1][1]+P[2][1]))
        Q2 = (0.5*(P[2][0]+P[3][0]),0.5*(P[2][1]+P[3][1]))
        R0 = (0.5*(Q0[0]+Q1[0]),0.5*(Q0[1]+Q1[1]))
        R1 = (0.5*(Q1[0]+Q2[0]),0.5*(Q1[1]+Q2[1]))
        S0 = (0.5*(R0[0]+R1[0]),0.5*(R0[1]+R1[1]))
        return [P[0],Q0,R0,S0] if kind==1 else [S0,R1,Q2,P[3]]

def _quadrantDef(xpos, ypos, corner, r, kind=0, direction='left-right', m=0.4472):
    t = m*r
    if xpos=='right' and ypos=='bottom': #bottom right
        xhi,ylo = corner
        P = [(xhi - r, ylo),(xhi-t, ylo), (xhi, ylo + t), (xhi, ylo + r)]
    elif xpos=='right' and ypos=='top': #top right
        xhi,yhi = corner
        P = [(xhi, yhi - r),(xhi, yhi - t), (xhi - t, yhi), (xhi - r, yhi)]
    elif xpos=='left' and ypos=='top': #top left
        xlo,yhi = corner
        P = [(xlo + r, yhi),(xlo + t, yhi), (xlo, yhi - t), (xlo, yhi - r)]
    elif xpos=='left' and ypos=='bottom': #bottom left
        xlo,ylo = corner
        P = [(xlo, ylo + r),(xlo, ylo + t), (xlo + t, ylo), (xlo + r, ylo)]
    else:
        raise ValueError(f'Unknown quadrant position (xpos,ypos)={(xpos,ypos)!r}')
    if direction=='left-right' and P[0][0]>P[-1][0] or direction=='bottom-top' and P[0][1]>P[-1][1]:
        P.reverse()
    P = _calcBezierPoints(P, kind)
    return P

def _hLine(canvLine, scp, ecp, y, hBlocks, FUZZ=rl_config._FUZZ):
    '''
    Draw horizontal lines; do not draw through regions specified in hBlocks
    This also serves for vertical lines with a suitable canvLine
    '''
    if hBlocks: hBlocks = hBlocks.get(y,None)
    if not hBlocks or scp>=hBlocks[-1][1]-FUZZ or ecp<=hBlocks[0][0]+FUZZ:
        canvLine(scp,y,ecp,y)
    else:
        i = 0
        n = len(hBlocks)
        while scp<ecp-FUZZ and i<n:
            x0, x1 = hBlocks[i]
            if x1<=scp+FUZZ or x0>=ecp-FUZZ:
                i += 1
                continue
            i0 = max(scp,x0)
            i1 = min(ecp,x1)
            if i0>scp: canvLine(scp,y,i0,y)
            scp = i1
        if scp<ecp-FUZZ: canvLine(scp,y,ecp,y)

def _multiLine(scp,ecp,y,canvLine,ws,count):
    offset = 0.5*(count-1)*ws
    y += offset
    for idx in range(count):
        canvLine(scp, y, ecp, y)
        y -= ws

def _convert2int(value, map, low, high, name, cmd):
    '''private converter tries map(value) low<=int(value)<=high or finally an error'''
    try:
        return map[value]
    except KeyError:
        try:
            ivalue = int(value)
            if low<=ivalue<=high: return ivalue
        except:
            pass
    raise ValueError(f'Bad {name} value {value} in {cmd!a}')

def _endswith(obj,s):
    try:
        return obj.endswith(s)
    except:
        return 0

def spanFixDim(V0,V,spanCons,lim=None,FUZZ=rl_config._FUZZ):
    #assign required space to variable rows equally to existing calculated values
    M = {}
    if not lim: lim = len(V0)   #in longtables the row calcs may be truncated

    #we assign the largest spaces first hoping to get a smaller result
    for v,(x0,x1) in reversed(sorted(((iv,ik) for ik,iv in spanCons.items()))):
        if x0>=lim: continue
        x1 += 1
        t = sum([V[x]+M.get(x,0) for x in range(x0,x1)])
        if t>=v-FUZZ: continue      #already good enough
        X = [x for x in range(x0,x1) if V0[x] is None] #variable candidates
        if not X: continue          #something wrong here mate
        v -= t
        v /= float(len(X))
        for x in X:
            M[x] = M.get(x,0)+v
    for x,v in M.items():
        V[x] += v

class _ExpandedCellTuple(tuple):
    pass

class _ExpandedCellTupleEx(tuple):
    def __new__(cls,seq,tagType,altText,extras):
        self = tuple.__new__(cls,seq)
        self.tagType = tagType
        self.altText = altText
        self.extras = extras
        return self

RoundingRectDef = namedtuple('RoundingRectDefs','x0 y0 w h x1 y1 ar SL')
RoundingRectLine = namedtuple('RoundingRectLine','xs ys xe ye weight color cap dash join')

_SPECIALROWS=("splitfirst", "splitlast", "inrowsplitstart","inrowsplitend")
class Table(Flowable):
    def __init__(self, data, colWidths=None, rowHeights=None, style=None,
                repeatRows=0, repeatCols=0, splitByRow=1, splitInRow=0, emptyTableAction=None, ident=None,
                hAlign=None,vAlign=None, normalizedData=0, cellStyles=None, rowSplitRange=None,
                spaceBefore=None,spaceAfter=None, longTableOptimize=None, minRowHeights=None,
                cornerRadii=__UNSET__, #or [topLeft, topRight, bottomLeft bottomRight]
                renderCB=None,
                ):
        self.ident = ident
        self.hAlign = hAlign or 'CENTER'
        self.vAlign = vAlign or 'MIDDLE'
        if not isinstance(data,(tuple,list)):
            raise ValueError("%s invalid data type" % self.identity())
        self._renderCB = renderCB
        self._nrows = nrows = len(data)
        self._cellvalues = []
        _seqCW = isinstance(colWidths,(tuple,list))
        _seqRH = isinstance(rowHeights,(tuple,list))
        if nrows: self._ncols = ncols = max(list(map(_rowLen,data)))
        elif colWidths and _seqCW: ncols = len(colWidths)
        else: ncols = 0
        if not emptyTableAction: emptyTableAction = rl_config.emptyTableAction
        self._longTableOptimize = (getattr(self,'_longTableOptimize',rl_config.longTableOptimize)
                                    if longTableOptimize is None else longTableOptimize)
        if not (nrows and ncols):
            if emptyTableAction=='error':
                raise ValueError(f'{self.identity()} must have at least a row and column')
            elif emptyTableAction=='indicate':
                self.__class__ = Preformatted
                global _emptyTableStyle
                if '_emptyTableStyle' not in list(globals().keys()):
                    _emptyTableStyle = ParagraphStyle('_emptyTableStyle')
                    _emptyTableStyle.textColor = colors.red
                    _emptyTableStyle.backColor = colors.yellow
                Preformatted.__init__(self,'%s(%d,%d)' % (self.__class__.__name__,nrows,ncols), _emptyTableStyle)
            elif emptyTableAction=='ignore':
                self.__class__ = NullActionFlowable
            else:
                raise ValueError(f'{self.identitiy()} bad emptyTableAction: {emptyTableAction!a}')
            return

        # we need a cleanup pass to ensure data is strings - non-unicode and non-null
        if normalizedData:
            self._cellvalues = data
        else:
            self._cellvalues = data = self.normalizeData(data)
        if not _seqCW: colWidths = ncols*[colWidths]
        elif len(colWidths)!=ncols:
            if rl_config.allowShortTableRows and isinstance(colWidths,list):
                n = len(colWidths)
                if n<ncols:
                    colWidths[n:] = (ncols-n)*[colWidths[-1]]
                else:
                    colWidths = colWidths[:ncols]
            else:
                raise ValueError(f'{self.identity()} data error - {ncols} columns in data but {len(colWidths)} column widths')
        if not _seqRH: rowHeights = nrows*[rowHeights]
        elif len(rowHeights) != nrows:
            raise ValueError(f'{self.identity()} data error - {nrows} rows in data but {len(rowHeights)} row heights')
        for i,d in enumerate(data):
            n = len(d)
            if n!=ncols:
                if rl_config.allowShortTableRows and isinstance(d,list):
                    d[n:] = (ncols-n)*['']
                else:
                    raise ValueError(f'{self.identity()} expected {ncols} not {n} columns in row {i}!')
        self._rowHeights = self._argH = rowHeights
        self._colWidths = self._argW = colWidths
        if cellStyles is None:
            cellrows = []
            for i in range(nrows):
                cellcols = []
                for j in range(ncols):
                    cellcols.append(CellStyle(repr((i,j))))
                cellrows.append(cellcols)
            self._cellStyles = cellrows
        else:
            self._cellStyles = cellStyles

        self._bkgrndcmds = []
        self._linecmds = []
        self._spanCmds = []
        self._nosplitCmds = []
        self._srflcmds = [] # split first last
        self._sircmds = []  # split in row special commands
        # NB repeatRows can be a list or tuple eg (1,) repeats only the second row of a table
        # or an integer eg 2 to repeat both rows 0 & 1
        self.repeatRows = repeatRows
        self.repeatCols = repeatCols
        self.splitByRow = splitByRow
        self.splitInRow = splitInRow

        if style:
            self.setStyle(style)

        if cornerRadii is not __UNSET__:    #instance argument overrides
            self._setCornerRadii(cornerRadii)

        self._rowSplitRange = rowSplitRange
        if spaceBefore is not None:
            self.spaceBefore = spaceBefore
        if spaceAfter is not None:
            self.spaceAfter = spaceAfter
            
        if minRowHeights != None:
            lmrh = len(minRowHeights)
            if not lmrh:
                raise ValueError('{self.idenity()} Supplied mismatching minimum row heights of length {lmrh}')
            elif lmrh<nrows:
                minRowHeights = minRowHeights+(nrows-lmrh)*minRowHeights.__class__((0,))
        self._minRowHeights = minRowHeights


    def __repr__(self):
        "incomplete, but better than nothing"
        r = getattr(self,'_rowHeights','[unknown]')
        c = getattr(self,'_colWidths','[unknown]')
        cv = getattr(self,'_cellvalues','[unknown]')
        import pprint
        cv = pprint.pformat(cv)
        cv = cv.replace("\n", "\n  ")
        return "%s(\n rowHeights=%s,\n colWidths=%s,\n%s\n) # end table" % (self.__class__.__name__,r,c,cv)

    def normalizeData(self, data):
        """Takes a block of input data (list of lists etc.) and
        - coerces unicode strings to non-unicode UTF8
        - coerces nulls to ''
        -

        """
        def normCell(stuff):
            if stuff is None:
                return ''
            elif isStr(stuff):
                return asNative(stuff)
            else:
                return stuff
        outData = []
        for row in data:
            outRow = [normCell(cell) for cell in row]
            outData.append(outRow)
        return outData

    def identity(self, maxLen=30):
        '''Identify our selves as well as possible'''
        if self.ident: return self.ident
        vx = None
        nr = getattr(self,'_nrows','unknown')
        nc = getattr(self,'_ncols','unknown')
        cv = getattr(self,'_cellvalues',None)
        rh = getattr(self, '_rowHeights', None)
        if cv and 'unknown' not in (nr,nc):
            b = 0
            for i in range(nr):
                for j in range(nc):
                    v = cv[i][j]
                    if isinstance(v,(list,tuple,Flowable)):
                        if not isinstance(v,(tuple,list)): v = (v,)
                        r = ''
                        for vij in v:
                            r = vij.identity(maxLen)
                            if r and r[-4:]!='>...':
                                break
                        if r and r[-4:]!='>...':
                            ix, jx, vx, b = i, j, r, 1
                    else:
                        v = v is None and '' or str(v)
                        ix, jx, vx = i, j, v
                        b = (vx and isinstance(v,strTypes)) and 1 or 0
                        if maxLen: vx = vx[:maxLen]
                    if b: break
                if b: break
        if rh:  #find tallest row, it's of great interest'
            tallest = '(tallest row %d)' % int(max(rh))
        else:
            tallest = ''
        if vx:
            vx = ' with cell(%d,%d) containing\n%s' % (ix,jx,repr(vx))
        else:
            vx = '...'

        return "<%s@0x%8.8X %s rows x %s cols%s>%s" % (self.__class__.__name__, id(self), nr, nc, tallest, vx)

    def _cellListIter(self,C,aW,aH):
        canv = getattr(self,'canv',None)
        for c in C:
            if getattr(c,'__split_only__',None):
                for d in c.splitOn(canv,aW,aH):
                    yield d
            else:
                yield c

    def _cellListProcess(self,v,aW,aH):
        if isinstance(v,_ExpandedCellTuple):
            C = v
        else:
            C = (v,) if isinstance(v,Flowable) else flatten(v)
            frame = None
            R = [].append
            for c in self._cellListIter(C,aW,aH):
                if isinstance(c,Indenter):
                    if not frame:
                        frame = CellFrame(_leftExtraIndent=0,_rightExtraIndent=0)
                    c.frameAction(frame)
                    if frame._leftExtraIndent<1e-8 and frame._rightExtraIndent<1e-8:
                        frame = None
                    continue
                if frame:
                    R(LIIndenter(c,leftIndent=frame._leftExtraIndent,rightIndent=frame._rightExtraIndent))
                else:
                    R(c)
            if hasattr(v,'tagType'):
                C = _ExpandedCellTupleEx(R.__self__,v.tagType,v.altText,v.extras)
            else:
                C = _ExpandedCellTuple(R.__self__)

        return C

    def _listCellGeom(self, V,w,s,W=None,H=None,aH=72000):
        if not V: return 0,0
        aW = w - s.leftPadding - s.rightPadding
        aH = aH - s.topPadding - s.bottomPadding
        t = 0
        w = 0
        canv = getattr(self,'canv',None)
        sb0 = None
        if isinstance(V, str):
            vw = self._elementWidth(V, s)
            vh = len(V.split('\n'))*s.fontsize*1.2
            return max(w, vw), vh
        for v in V:
            vw, vh = v.wrapOn(canv, aW, aH)
            sb = v.getSpaceBefore()
            sa = v.getSpaceAfter()
            if W is not None: W.append(vw)
            if H is not None: H.append(vh)
            w = max(w,vw)
            t += vh + sa + sb
            if sb0 is None:
                sb0 = sb
        return w, t - sb0 - sa

    def _listValueWidth(self,V,aH=72000,aW=72000):
        if not V: return 0,0
        t = 0
        w = 0
        canv = getattr(self,'canv',None)
        return max([v.wrapOn(canv,aW,aH)[0] for v in V])

    def _calc_width(self,availWidth,W=None):
        if getattr(self,'_width_calculated_once',None): return
        #comments added by Andy to Robin's slightly terse variable names
        if not W: W = _calc_pc(self._argW,availWidth)   #widths array
        if None in W:  #some column widths are not given
            canv = getattr(self,'canv',None)
            saved = None
            if self._spanCmds:
                colSpanCells = self._colSpanCells
                spanRanges = self._spanRanges
            else:
                colSpanCells = ()
                spanRanges = {}
            spanCons = {}
            if W is self._argW:
                W0 = W
                W = W[:]
            else:
                W0 = W[:]
            V = self._cellvalues
            S = self._cellStyles
            while None in W:
                j = W.index(None) #find first unspecified column
                w = 0
                for i,Vi in enumerate(V):
                    v = Vi[j]
                    s = S[i][j]
                    ji = j,i
                    span = spanRanges.get(ji,None)
                    if ji in colSpanCells and not span: #if the current cell is part of a spanned region,
                        t = 0.0                         #assume a zero size.
                    else:#work out size
                        t = self._elementWidth(v,s)
                        if t is None:
                            raise ValueError(f'Flowable {v.identity()} in cell({i},{j}) can\'t have auto width\n{self.identity(30)}')
                        t += s.leftPadding+s.rightPadding
                        if span:
                            c0 = span[0]
                            c1 = span[2]
                            if c0!=c1:
                                x = c0,c1
                                spanCons[x] = max(spanCons.get(x,t),t)
                                t = 0
                    if t>w: w = t   #record a new maximum

                W[j] = w

            if spanCons:
                try:
                    spanFixDim(W0,W,spanCons)
                except:
                    annotateException('\nspanning problem in %s\nW0=%r W=%r\nspanCons=%r' % (self.identity(),W0,W,spanCons))

        self._colWidths = W
        width = 0
        self._colpositions = [0]        #index -1 is right side boundary; we skip when processing cells
        for w in W:
            width = width + w
            self._colpositions.append(width)

        self._width = width
        self._width_calculated_once = 1

    def _elementWidth(self,v,s):
        if isinstance(v,(list,tuple)):
            w = 0
            for e in v:
                ew = self._elementWidth(e,s)
                if ew is None: return None
                w = max(w,ew)
            return w
        elif isinstance(v,Flowable):
            if v._fixedWidth:
                if hasattr(v, 'width') and isinstance(v.width,(int,float)): return v.width
                if hasattr(v, 'drawWidth') and isinstance(v.drawWidth,(int,float)): return v.drawWidth
            if hasattr(v,'__styledWrap__'): #very experimental
                try:
                    return getattr(v,'__styledWrap__')(s)[0]
                except:
                    pass
        # Even if something is fixedWidth, the attribute to check is not
        # necessarily consistent (cf. Image.drawWidth).  Therefore, we'll
        # be extra-careful and fall through to this code if necessary.
        if hasattr(v, 'minWidth'):
            try:
                w = v.minWidth() # should be all flowables
                if isinstance(w,(float,int)): return w
            except AttributeError:
                pass
        if v is None:
            return 0
        else:
            try:
                v = str(v).split("\n")
            except:
                return 0
        fontName = s.fontname
        fontSize = s.fontsize
        return max([stringWidth(x,fontName,fontSize) for x in v])

    def _calc_height(self, availHeight, availWidth, H=None, W=None):
        H = self._argH
        if not W: W = _calc_pc(self._argW,availWidth)   #widths array

        hmax = lim = len(H)
        longTable = self._longTableOptimize

        if None in H:
            minRowHeights = self._minRowHeights
            canv = getattr(self,'canv',None)
            saved = None
            #get a handy list of any cells which span rows. should be ignored for sizing
            if self._spanCmds:
                rowSpanCells = self._rowSpanCells
                colSpanCells = self._colSpanCells
                spanRanges = self._spanRanges
                colpositions = self._colpositions
            else:
                rowSpanCells = colSpanCells = ()
                spanRanges = {}
            if canv: saved = canv._fontname, canv._fontsize, canv._leading
            H0 = H
            H = H[:]    #make a copy as we'll change it
            self._rowHeights = H
            spanCons = {}
            FUZZ = rl_config._FUZZ
            while None in H:
                i = H.index(None)
                V = self._cellvalues[i] # values for row i
                S = self._cellStyles[i] # styles for row i
                h = 0
                j = 0
                for j,(v, s, w) in enumerate(list(zip(V, S, W))): # value, style, width (lengths must match)
                    ji = j,i
                    span = spanRanges.get(ji,None)
                    if ji in rowSpanCells and not span:
                        continue # don't count it, it's either occluded or unreliable
                    else:
                        if isinstance(v,(tuple,list,Flowable)):
                            v = V[j] = self._cellListProcess(v,w,None)
                            if w is None and not self._canGetWidth(v):
                                raise ValueError(f'Flowable {v[0].identity()} in cell({i},{j}) can\'t have auto width\n{self.identity(30)}')
                            if canv: canv._fontname, canv._fontsize, canv._leading = s.fontname, s.fontsize, s.leading or 1.2*s.fontsize
                            if ji in colSpanCells:
                                if not span: continue
                                w = max(colpositions[span[2]+1]-colpositions[span[0]],w or 0)
                            dW,t = self._listCellGeom(v,w or self._listValueWidth(v),s)
                            if canv: canv._fontname, canv._fontsize, canv._leading = saved
                            dW = dW + s.leftPadding + s.rightPadding
                            if not rl_config.allowTableBoundsErrors and dW>w:
                                from reportlab.platypus.doctemplate import LayoutError
                                raise LayoutError("Flowable %s (%sx%s points) too wide for cell(%d,%d) (%sx* points) in\n%s" % (v[0].identity(30),fp_str(dW),fp_str(t),i,j, fp_str(w), self.identity(30)))
                        else:
                            v = (v is not None and str(v) or '').split("\n")
                            t = (s.leading or 1.2*s.fontsize)*len(v)
                        t += s.bottomPadding+s.topPadding
                        if span:
                            r0 = span[1]
                            r1 = span[3]
                            if r0!=r1:
                                x = r0,r1
                                spanCons[x] = max(spanCons.get(x,t),t)
                                t = 0
                    if t>h: h = t   #record a new maximum
                # If a minimum height has been specified use that, otherwise allow the cell to grow
                H[i] = max(minRowHeights[i],h) if minRowHeights else h
                # we can stop if we have filled up all available room
                if longTable:
                    hmax = i+1      #we computed H[i] so known len == i+1
                    height = sum(H[:hmax])
                    if height > availHeight:
                        #we can terminate if all spans are complete in H[:hmax]
                        if spanCons:
                            msr = max(x[1] for x in spanCons.keys())    #RS=[endrowspan,.....]
                            if hmax>msr:
                                break
            if None not in H: hmax = lim

            if spanCons:
                try:
                    spanFixDim(H0,H,spanCons)
                except:
                    annotateException('\nspanning problem in %s hmax=%s lim=%s avail=%s x %s\nH0=%r H=%r\nspanCons=%r' % (self.identity(),hmax,lim,availWidth,availHeight,H0,H,spanCons))

        #iterate backwards through the heights to get rowpositions in reversed order
        self._rowpositions = j = []
        height = c = 0
        for i in range(hmax-1,-1,-1):
            j.append(height)
            y = H[i] - c
            t = height + y
            c = (t - height) - y
            height = t
        j.append(height)
        self._height = height
        j.reverse()     #reverse the reversed list of row positions
        self._hmax = hmax

    def _calc(self, availWidth, availHeight):
        #if hasattr(self,'_width'): return

        #in some cases there are unsizable things in
        #cells.  If so, apply a different algorithm
        #and assign some withs in a less (thanks to Gary Poster) dumb way.
        #this CHANGES the widths array.
        if (None in self._colWidths or '*' in self._colWidths) and self._hasVariWidthElements():
            W = self._calcPreliminaryWidths(availWidth) #widths
        else:
            W = None

        # need to know which cells are part of spanned
        # ranges, so _calc_height and _calc_width can ignore them
        # in sizing
        if self._spanCmds:
            self._calcSpanRanges()
            if None in self._argH:
                self._calc_width(availWidth,W=W)

        if self._nosplitCmds:
            self._calcNoSplitRanges()

        # calculate the full table height
        self._calc_height(availHeight,availWidth,W=W)

        # calculate the full table width
        self._calc_width(availWidth,W=W)

        if self._spanCmds:
            #now work out the actual rect for each spanned cell from the underlying grid
            self._calcSpanRects()

    def _culprit(self):
        """Return a string describing the tallest element.

        Usually this is what causes tables to fail to split.  Currently
        tables are the only items to have a '_culprit' method. Doctemplate
        checks for it.
        """
        rh = self._rowHeights
        tallest = max(rh)
        rowNum = rh.index(tallest)
        #rowNum of limited interest as usually it's a split one
        #and we see row #1.  Text might be a nice addition.

        return 'tallest cell %0.1f points' % tallest



    def _hasVariWidthElements(self, upToRow=None):
        """Check for flowables in table cells and warn up front.

        Allow a couple which we know are fixed size such as
        images and graphics."""
        if upToRow is None: upToRow = self._nrows
        for row in range(min(self._nrows, upToRow)):
            for col in range(self._ncols):
                value = self._cellvalues[row][col]
                if not self._canGetWidth(value):
                    return 1
        return 0

    def _canGetWidth(self, thing):
        "Can we work out the width quickly?"
        if isinstance(thing,(list, tuple)):
            for elem in thing:
                if not self._canGetWidth(elem):
                    return 0
            return 1
        elif isinstance(thing, Flowable):
            return thing._fixedWidth  # must loosen this up
        else: #str, number, None etc.
            #anything else gets passed to str(...)
            # so should be sizable
            return 1

    def _calcPreliminaryWidths(self, availWidth):
        """Fallback algorithm for when main one fails.

        Where exact width info not given but things like
        paragraphs might be present, do a preliminary scan
        and assign some best-guess values."""

        W = list(self._argW) # _calc_pc(self._argW,availWidth)
        #_debug = getattr(self,'_debug',0)
        totalDefined = 0.0
        percentDefined = 0
        percentTotal = 0
        numberUndefined = 0
        numberGreedyUndefined = 0
        for w in W:
            if w is None:
                numberUndefined += 1
            elif w == '*':
                numberUndefined += 1
                numberGreedyUndefined += 1
            elif _endswith(w,'%'):
                percentDefined += 1
                percentTotal += float(w[:-1])
            else:
                assert isinstance(w,(int,float))
                totalDefined = totalDefined + w
        #if _debug: print('prelim width calculation.  %d columns, %d undefined width, %0.2f units remain' % (self._ncols, numberUndefined, availWidth - totalDefined))

        #check columnwise in each None column to see if they are sizable.
        given = []
        sizeable = []
        unsizeable = []
        minimums = {}
        totalMinimum = 0
        elementWidth = self._elementWidth
        for colNo in range(self._ncols):
            w = W[colNo]
            if w is None or w=='*' or _endswith(w,'%'):
                siz = 1
                final = 0
                for rowNo in range(self._nrows):
                    value = self._cellvalues[rowNo][colNo]
                    style = self._cellStyles[rowNo][colNo]
                    new = elementWidth(value,style) or 0
                    new += style.leftPadding+style.rightPadding
                    #if _debug: print('[%d,%d] new=%r-->%r' % (rowNo,colNo,new - style.leftPadding+style.rightPadding, new))
                    final = max(final, new)
                    siz = siz and self._canGetWidth(value) # irrelevant now?
                if siz:
                    sizeable.append(colNo)
                else:
                    unsizeable.append(colNo)
                minimums[colNo] = final
                totalMinimum += final
            else:
                given.append(colNo)
        if len(given) == self._ncols:
            return
        #if _debug: print('predefined width: ',given)
        #if _debug: print('uncomputable width: ',unsizeable)
        #if _debug: print('computable width: ',sizeable)
        #if _debug: print('minimums=%r' % (list(sorted(list(minimums.items()))),))

        # how much width is left:
        remaining = availWidth - (totalMinimum + totalDefined)
        if remaining > 0:
            # we have some room left; fill it.
            definedPercentage = (totalDefined/float(availWidth))*100
            percentTotal += definedPercentage
            if numberUndefined and percentTotal < 100:
                undefined = numberGreedyUndefined or numberUndefined
                defaultWeight = (100-percentTotal)/float(undefined)
                percentTotal = 100
                defaultDesired = (defaultWeight/float(percentTotal))*availWidth
            else:
                defaultWeight = defaultDesired = 1
            # we now calculate how wide each column wanted to be, and then
            # proportionately shrink that down to fit the remaining available
            # space.  A column may not shrink less than its minimum width,
            # however, which makes this a bit more complicated.
            desiredWidths = []
            totalDesired = 0
            effectiveRemaining = remaining
            for colNo, minimum in minimums.items():
                w = W[colNo]
                if _endswith(w,'%'):
                    desired = (float(w[:-1])/percentTotal)*availWidth
                elif w == '*':
                    desired = defaultDesired
                else:
                    desired = not numberGreedyUndefined and defaultDesired or 1
                if desired <= minimum:
                    W[colNo] = minimum
                else:
                    desiredWidths.append(
                        (desired-minimum, minimum, desired, colNo))
                    totalDesired += desired
                    effectiveRemaining += minimum
            if desiredWidths: # else we're done
                # let's say we have two variable columns.  One wanted
                # 88 points, and one wanted 264 points.  The first has a
                # minWidth of 66, and the second of 55.  We have 71 points
                # to divide up in addition to the totalMinimum (i.e.,
                # remaining==71).  Our algorithm tries to keep the proportion
                # of these variable columns.
                #
                # To do this, we add up the minimum widths of the variable
                # columns and the remaining width.  That's 192.  We add up the
                # totalDesired width.  That's 352.  That means we'll try to
                # shrink the widths by a proportion of 192/352--.545454.
                # That would make the first column 48 points, and the second
                # 144 points--adding up to the desired 192.
                #
                # Unfortunately, that's too small for the first column.  It
                # must be 66 points.  Therefore, we go ahead and save that
                # column width as 88 points.  That leaves (192-88==) 104
                # points remaining.  The proportion to shrink the remaining
                # column is (104/264), which, multiplied  by the desired
                # width of 264, is 104: the amount assigned to the remaining
                # column.
                proportion = effectiveRemaining/float(totalDesired)
                # we sort the desired widths by difference between desired and
                # and minimum values, a value called "disappointment" in the
                # code.  This means that the columns with a bigger
                # disappointment will have a better chance of getting more of
                # the available space.
                desiredWidths.sort()
                finalSet = []
                for disappointment, minimum, desired, colNo in desiredWidths:
                    adjusted = proportion * desired
                    if adjusted < minimum:
                        W[colNo] = minimum
                        totalDesired -= desired
                        effectiveRemaining -= minimum
                        if totalDesired:
                            proportion = effectiveRemaining/float(totalDesired)
                    else:
                        finalSet.append((minimum, desired, colNo))
                for minimum, desired, colNo in finalSet:
                    adjusted = proportion * desired
                    assert adjusted >= minimum
                    W[colNo] = adjusted
        else:
            if percentTotal>0:
                #transfer percentages to the defined cols
                d = []
                for colNo, w in minimums.items():
                    if w.endswith('%'):
                        W[colNo] = w = availWidth*float(w[:-1])/percentTotal
                        totalDefined += w
                        d.append(colNo)
                for colNo in d:
                    del minimums[colNo]
                del d
                totalMinimum = sum(minimums.values())
                remaining = availWidth - (totalDefined + totalMinimum)
            #if _debug: print(f'0:remaining={remaining} totalDefined={totalDefined}')
            #if _debug: print(f'0:minimums={minimums}')
            if remaining<0 and totalDefined*rl_config.defCWRF+remaining>=0:
                adj = -remaining/totalDefined
                for colNo, w in enumerate(W):
                    if colNo not in minimums:
                        dw = adj*w
                        W[colNo] -= dw
                        totalDefined -= dw
                remaining = availWidth - (totalDefined + totalMinimum)
                #if _debug: print(f'1:remaining={remaining} totalDefined={totalDefined}')
                #if _debug: print(f'1:minimums={minimums}')
                adj = 1
            else:
                remaining = availWidth - totalDefined
                adj = 1 if remaining<=0 else remaining/totalMinimum
            for colNo, minimum in minimums.items():
                W[colNo] = minimum * adj
        #if _debug: print(f'new widths are: {W} sum={sum(W)} availWidth={availWidth}')
        self._argW = self._colWidths = W
        return W

    def minWidth(self):
        W = list(self._argW)
        width = 0
        elementWidth = self._elementWidth
        rowNos = range(self._nrows)
        values = self._cellvalues
        styles = self._cellStyles
        for colNo in range(len(W)):
            w = W[colNo]
            if w is None or w=='*' or _endswith(w,'%'):
                final = 0
                for rowNo in rowNos:
                    value = values[rowNo][colNo]
                    style = styles[rowNo][colNo]
                    new = (elementWidth(value,style)+
                           style.leftPadding+style.rightPadding)
                    final = max(final, new)
                width += final
            else:
                width += float(w)
        return width # XXX + 1/2*(left and right border widths)

    def _calcSpanRanges(self):
        """Work out rects for tables which do row and column spanning.

        This creates some mappings to let the later code determine
        if a cell is part of a "spanned" range.
        self._spanRanges shows the 'coords' in integers of each
        'cell range', or None if it was clobbered:
        (col, row) -> (col0, row0, col1, row1)

        Any cell not in the key is not part of a spanned region
        """
        self._spanRanges = spanRanges = {}
        for x in range(self._ncols):
            for y in range(self._nrows):
                spanRanges[x,y] = (x, y, x, y)
        self._colSpanCells = []
        self._rowSpanCells = []
        csa = self._colSpanCells.append
        rsa = self._rowSpanCells.append
        for (cmd, start, stop) in self._spanCmds:
            x0, y0 = start
            x1, y1 = stop

            #normalize
            if x0 < 0: x0 = x0 + self._ncols
            if x1 < 0: x1 = x1 + self._ncols
            if y0 < 0: y0 = y0 + self._nrows
            if y1 < 0: y1 = y1 + self._nrows
            if x0 > x1: x0, x1 = x1, x0
            if y0 > y1: y0, y1 = y1, y0

            if x0!=x1 or y0!=y1:
                if x0!=x1: #column span
                    for y in range(y0, y1+1):
                        for x in range(x0,x1+1):
                            csa((x,y))
                if y0!=y1: #row span
                    for y in range(y0, y1+1):
                        for x in range(x0,x1+1):
                            rsa((x,y))

                for y in range(y0, y1+1):
                    for x in range(x0,x1+1):
                        spanRanges[x,y] = None
                # set the main entry
                spanRanges[x0,y0] = (x0, y0, x1, y1)

    def _calcNoSplitRanges(self):
        """
        This creates some mappings to let the later code determine
        if a cell is part of a "nosplit" range.
        self._nosplitRanges shows the 'coords' in integers of each
        'cell range', or None if it was clobbered:
        (col, row) -> (col0, row0, col1, row1)

        Any cell not in the key is not part of a spanned region
        """
        self._nosplitRanges = nosplitRanges = {}
        for x in range(self._ncols):
            for y in range(self._nrows):
                nosplitRanges[x,y] = (x, y, x, y)
        self._colNoSplitCells = []
        self._rowNoSplitCells = []
        csa = self._colNoSplitCells.append
        rsa = self._rowNoSplitCells.append
        for (cmd, start, stop) in self._nosplitCmds:
            x0, y0 = start
            x1, y1 = stop

            #normalize
            if x0 < 0: x0 = x0 + self._ncols
            if x1 < 0: x1 = x1 + self._ncols
            if y0 < 0: y0 = y0 + self._nrows
            if y1 < 0: y1 = y1 + self._nrows
            if x0 > x1: x0, x1 = x1, x0
            if y0 > y1: y0, y1 = y1, y0

            if x0!=x1 or y0!=y1:
                #column span
                if x0!=x1:
                    for y in range(y0, y1+1):
                        for x in range(x0,x1+1):
                            csa((x,y))
                #row span
                if y0!=y1:
                    for y in range(y0, y1+1):
                        for x in range(x0,x1+1):
                            rsa((x,y))

                for y in range(y0, y1+1):
                    for x in range(x0,x1+1):
                        nosplitRanges[x,y] = None
                # set the main entry
                nosplitRanges[x0,y0] = (x0, y0, x1, y1)

    def _calcSpanRects(self):
        """Work out rects for tables which do row and column spanning.

        Based on self._spanRanges, which is already known,
        and the widths which were given or previously calculated,
        self._spanRects shows the real coords for drawing:

            (col, row) -> (x, y, width, height)

        for each cell.  Any cell which 'does not exist' as another
        has spanned over it will get a None entry on the right
        """
        spanRects = getattr(self,'_spanRects',{})
        hmax = getattr(self,'_hmax',None)
        longTable = self._longTableOptimize
        if spanRects and (longTable and hmax==self._hmax_spanRects or not longTable):
            return
        colpositions = self._colpositions
        rowpositions = self._rowpositions
        vBlocks = {}
        hBlocks = {}
        rlim = len(rowpositions)-1
        for (coord, value) in self._spanRanges.items():
            if value is None:
                spanRects[coord] = None
            else:
                try:
                    col0, row0, col1, row1 = value
                    if row1>=rlim: continue
                    col,row = coord
                    if col1-col0>0:
                        for _ in range(col0+1,col1+1):
                            vBlocks.setdefault(colpositions[_],[]).append((rowpositions[row1+1],rowpositions[row0]))
                    if row1-row0>0:
                        for _ in range(row0+1,row1+1):
                            hBlocks.setdefault(rowpositions[_],[]).append((colpositions[col0],colpositions[col1+1]))
                    x = colpositions[col0]
                    y = rowpositions[row1+1]
                    width = colpositions[col1+1] - x
                    height = rowpositions[row0] - y
                    spanRects[coord] = (x, y, width, height)
                except:
                    annotateException('\nspanning problem in %s' % (self.identity(),))

        for _ in hBlocks, vBlocks:
            for value in _.values():
                value.sort()
        self._spanRects = spanRects
        self._vBlocks = vBlocks
        self._hBlocks = hBlocks
        self._hmax_spanRects = hmax

    def setStyle(self, tblstyle):
        if not isinstance(tblstyle,TableStyle):
            tblstyle = TableStyle(tblstyle)
        for cmd in tblstyle.getCommands():
            if len(cmd)>=3:
                c, (sc,sr), (ec,er) = cmd[0:3]
                if (isinstance(sc,str) or isinstance(ec,str)
                    or (isinstance(sr,str) and sr not in _SPECIALROWS)
                    or (isinstance(er,str) and er not in _SPECIALROWS)):
                    raise ValueError(f'''bad style command {cmd!r} illegal of invalid string coordinate
only rows may be strings with values in {_SPECIALROWS!r}''')
            self._addCommand(cmd)
        for k,v in tblstyle._opts.items():
            setattr(self,k,v)
        for a in ('spaceBefore','spaceAfter'):
            if not hasattr(self,a) and hasattr(tblstyle,a):
                setattr(self,a,getattr(tblstyle,a))

    def normCellRange(self, sc, ec, sr, er):
        '''ensure cell range ends are with the table bounds'''
        if sc < 0: sc = sc + self._ncols
        if ec < 0: ec = ec + self._ncols
        if sr < 0: sr = sr + self._nrows
        if er < 0: er = er + self._nrows
        return max(0,sc), min(self._ncols-1,ec), max(0,sr), min(self._nrows-1,er)

    def _addCommand(self,cmd):
        if cmd[0] in ('BACKGROUND','ROWBACKGROUNDS','COLBACKGROUNDS'):
            self._bkgrndcmds.append(cmd)
        elif cmd[0] == 'SPAN':
            self._spanCmds.append(cmd)
        elif cmd[0] == 'NOSPLIT':
            # we expect op, start, stop
            self._nosplitCmds.append(cmd)
        elif _isLineCommand(cmd):
            # we expect op, start, stop, weight, colour, cap, dashes, join
            cmd = list(cmd)
            if len(cmd)<5: raise ValueError(f'bad line command {cmd!a}')

            #determine line cap value at position 5. This can be str or numeric.
            if len(cmd)<6:
                cmd.append(1)
            else:
                cap = _convert2int(cmd[5], LINECAPS, 0, 2, 'cap', cmd)
                cmd[5] = cap

            #dashes at index 6 - this is a dash array:
            if len(cmd)<7: cmd.append(None)

            #join mode at index 7 - can be str or numeric, look up as for caps
            if len(cmd)<8: cmd.append(1)
            else:
                join = _convert2int(cmd[7], LINEJOINS, 0, 2, 'join', cmd)
                cmd[7] = join

            #linecount at index 8.  Default is 1, set to 2 for double line.
            if len(cmd)<9: cmd.append(1)
            else:
                lineCount = cmd[8]
                if lineCount is None:
                    lineCount = 1
                    cmd[8] = lineCount
                assert lineCount >= 1
            #linespacing at index 9. Not applicable unless 2+ lines, defaults to line
            #width so you get a visible gap between centres
            if len(cmd)<10: cmd.append(cmd[3])
            else:
                space = cmd[9]
                if space is None:
                    space = cmd[3]
                    cmd[9] = space
            assert len(cmd) == 10

            self._linecmds.append(tuple(cmd))
        elif cmd[0]=="ROUNDEDCORNERS":
            self._setCornerRadii(cmd[1])
        else:
            (op, (sc, sr), (ec, er)), values = cmd[:3] , cmd[3:]
            if sr in _SPECIALROWS:
                (self._srflcmds if sr[0]=='s' else self._sircmds).append(cmd)
            else:
                sc, ec, sr, er = self.normCellRange(sc,ec,sr,er)
                ec += 1
                for i in range(sr, er+1):
                    for j in range(sc, ec):
                        _setCellStyle(self._cellStyles, i, j, op, values)

    def _drawLines(self):
        ccap, cdash, cjoin = None, None, None
        canv = self.canv
        canv.saveState()

        rrd = self._roundingRectDef
        if rrd: #we are collection some lines
            SL = rrd.SL
            SL[:] = []  #empty saved lines list
            ocanvline = canv.line
            aSL = SL.append
            def rcCanvLine(xs, ys, xe, ye):
                if  (
                    (xs==xe and (xs>=rrd.x1 or xs<=rrd.x0)) #vertical line that needs to be saved
                    or
                    (ys==ye and (ys>=rrd.y1 or ys<=rrd.y0)) #horizontal line that needs to be saved
                    ):
                    aSL(RoundingRectLine(xs,ys,xe,ye,weight,color,cap,dash,join))
                else:
                    ocanvline(xs,ys,xe,ye)
            canv.line = rcCanvLine

        try:
            for op, (sc,sr), (ec,er), weight, color, cap, dash, join, count, space in self._linecmds:
                if isinstance(sr,strTypes) and sr in _SPECIALROWS: continue
                if cap!=None and ccap!=cap:
                    canv.setLineCap(cap)
                    ccap = cap
                if dash is None or dash == []:
                    if cdash is not None:
                        canv.setDash()
                        cdash = None
                elif dash != cdash:
                    canv.setDash(dash)
                    cdash = dash
                if join is not None and cjoin!=join:
                    canv.setLineJoin(join)
                    cjoin = join
                sc, ec, sr, er = self.normCellRange(sc,ec,sr,er)
                getattr(self,_LineOpMap.get(op, '_drawUnknown' ))( (sc, sr), (ec, er), weight, color, count, space)
        finally:
            if rrd:
                canv.line = ocanvline
        canv.restoreState()
        self._curcolor = None

    def _drawUnknown(self,  start, end, weight, color, count, space):
        #we are only called from _drawLines which is one level up
        import sys
        op = sys._getframe(1).f_locals['op']
        raise ValueError(f'Unknown line command {op!a}')

    def _drawGrid(self, start, end, weight, color, count, space):
        self._drawBox( start, end, weight, color, count, space)
        self._drawInnerGrid( start, end, weight, color, count, space)

    def _drawBox(self,  start, end, weight, color, count, space):
        sc,sr = start
        ec,er = end
        self._drawHLines((sc, sr), (ec, sr), weight, color, count, space)
        self._drawHLines((sc, er+1), (ec, er+1), weight, color, count, space)
        self._drawVLines((sc, sr), (sc, er), weight, color, count, space)
        self._drawVLines((ec+1, sr), (ec+1, er), weight, color, count, space)

    def _drawInnerGrid(self, start, end, weight, color, count, space):
        sc,sr = start
        ec,er = end
        self._drawHLines((sc, sr+1), (ec, er), weight, color, count, space)
        self._drawVLines((sc+1, sr), (ec, er), weight, color, count, space)

    def _prepLine(self, weight, color):
        if color and color!=self._curcolor:
            self.canv.setStrokeColor(color)
            self._curcolor = color
        if weight and weight!=self._curweight:
            self.canv.setLineWidth(weight)
            self._curweight = weight

    def _drawHLines(self, start, end, weight, color, count, space):
        sc,sr = start
        ec,er = end
        ecp = self._colpositions[sc:ec+2]
        rp = self._rowpositions[sr:er+1]
        if len(ecp)<=1 or len(rp)<1: return
        self._prepLine(weight, color)
        scp = ecp[0]
        ecp = ecp[-1]
        hBlocks = getattr(self,'_hBlocks',{})
        canvLine = self.canv.line
        if count == 1:
            for y in rp:
                _hLine(canvLine, scp, ecp, y, hBlocks)
        else:
            lf = lambda x0,y0,x1,y1,canvLine=canvLine, ws=weight+space, count=count: _multiLine(x0,x1,y0,canvLine,ws,count)
            for y in rp:
                _hLine(lf, scp, ecp, y, hBlocks)

    def _drawHLinesB(self, start, end, weight, color, count, space):
        sc,sr = start
        ec,er = end
        self._drawHLines((sc, sr+1), (ec, er+1), weight, color, count, space)

    def _drawVLines(self, start, end, weight, color, count, space):
        sc,sr = start
        ec,er = end
        erp = self._rowpositions[sr:er+2]
        cp  = self._colpositions[sc:ec+1]
        if len(erp)<=1 or len(cp)<1: return
        self._prepLine(weight, color)
        srp = erp[0]
        erp = erp[-1]
        vBlocks = getattr(self,'_vBlocks',{})
        canvLine = lambda y0, x0, y1, x1, _line=self.canv.line: _line(x0,y0,x1,y1)
        if count == 1:
            for x in cp:
                _hLine(canvLine, erp, srp, x, vBlocks)
        else:
            lf = lambda x0,y0,x1,y1,canvLine=canvLine, ws=weight+space, count=count: _multiLine(x0,x1,y0,canvLine,ws,count)
            for x in cp:
                _hLine(lf, erp, srp, x, vBlocks)

    def _drawVLinesA(self, start, end, weight, color, count, space):
        sc,sr = start
        ec,er = end
        self._drawVLines((sc+1, sr), (ec+1, er), weight, color, count, space)

    def wrap(self, availWidth, availHeight):
        self._calc(availWidth, availHeight)
        self.availWidth = availWidth
        return (self._width, self._height)

    def onSplit(self,T,byRow=1):
        '''
        This method will be called when the Table is split.
        Special purpose tables can override to do special stuff.
        '''
        pass

    def _cr_0(self,n,cmds,nr0,doInRowSplit, _srflMode=False):
        #ths is used to modify/apply styles in splitIn row case
        #for the first part of a split. 
        ncols = self._ncols
        for c in cmds:
            (sc,sr), (ec,er) = c[1:3]
            if sr in _SPECIALROWS:
                if sr[0]=='i':
                    self._addCommand(c)             #re-append the command
                    if sr=='inrowsplitstart' and doInRowSplit:
                        if sc<0: sc+=ncols
                        if ec<0: ec+=ncols
                        self._addCommand((c[0],)+((sc, n-1), (ec, n-1))+tuple(c[3:]))
                    continue
                if not _srflMode: continue
                self._addCommand(c)             #re-append the command
                if sr=='splitfirst': continue
                sr = er = n-1
            if sr<0: sr += nr0
            if sr>=n: continue
            if er>=n: er = n-1
            self._addCommand((c[0],)+((sc, sr), (ec, er))+tuple(c[3:]))

    def _cr_1_1(self, n, nRows, repeatRows, cmds, doInRowSplit, _srflMode=False):
        nrr = len(repeatRows)
        rrS = set(repeatRows)
        ncols = self._ncols
        for c in cmds:
            (sc,sr), (ec,er) = c[1:3]
            if sr in _SPECIALROWS:
                if sr[0]=='i':
                    self._addCommand(c)             #re-append the command
                    if sr=='inrowsplitend' and doInRowSplit:
                        if sc<0: sc+=ncols
                        if ec<0: ec+=ncols
                        self._addCommand((c[0],)+((sc, nrr), (ec, nrr))+tuple(c[3:]))
                    continue
                if not _srflMode: continue
                self._addCommand(c)
                if sr=='splitlast': continue
                sr = er = n
            if sr<0: sr += nRows
            if er<0: er += nRows
            cS = set(range(sr,er+1)) & rrS
            if cS:
                #it's a repeat row
                cS = list(cS)
                self._addCommand((c[0],)+((sc, repeatRows.index(min(cS))), (ec, repeatRows.index(max(cS))))+tuple(c[3:]))
            if er<n: continue
            sr = max(sr-n,0)+nrr
            er = max(er-n,0)+nrr
            self._addCommand((c[0],)+((sc, sr), (ec, er))+tuple(c[3:]))
        sr = self._rowSplitRange
        if sr:
            sr, er = sr
            if sr<0: sr += nRows
            if er<0: er += nRows
            if er<n:
                self._rowSplitRange = None
            else:
                sr = max(sr-n,0)+nrr
                er = max(er-n,0)+nrr
                self._rowSplitRange = sr,er

    def _cr_1_0(self,n,cmds,doInRowSplit,_srflMode=False):
        for c in cmds:
            (sc,sr), (ec,er) = c[1:3]
            if sr in _SPECIALROWS:
                if sr[0]=='i':
                    self._addCommand(c)             #re-append the command
                    if sr=='inrowsplitend' and doInRowSplit:
                        if sc<0: sc+=ncols
                        if ec<0: ec+=ncols
                        self._addCommand((c[0],)+((sc, 0), (ec, 0))+tuple(c[3:]))
                    continue
                if not _srflMode: continue
                self._addCommand(c)
                if sr=='splitlast': continue
                sr = er = n
            if er>=0 and er<n: continue
            if sr>=0 and sr<n: sr=0
            if sr>=n: sr -= n
            if er>=n: er -= n
            self._addCommand((c[0],)+((sc, sr), (ec, er))+tuple(c[3:]))

    def _splitCell(self, value, style, oldHeight, newHeight, width):
        # Content height of the new top row
        height0 = newHeight - style.topPadding
        # Content height of the new bottom row
        height1 = oldHeight - (style.topPadding + newHeight)

        if isinstance(value, (tuple, list)):
            newCellContent = []
            postponedContent = []
            split = False
            cellHeight = self._listCellGeom(value, width, style)[1]

            if style.valign == "MIDDLE":
                usedHeight = (oldHeight - cellHeight) / 2
            else:
                usedHeight = 0

            for flowable in value:
                if split:
                    if flowable.height <= height1:
                        postponedContent.append(flowable)
                        # Shrink the available height:
                        height1 -= flowable.height
                    else:
                        # The content doesn't fit after the split:
                        return []
                elif usedHeight + flowable.height <= height0:
                    newCellContent.append(flowable)
                    usedHeight += flowable.height
                else:
                    # This is where we need to split
                    splits = flowable.split(width, height0-usedHeight)
                    if splits:
                        newCellContent.append(splits[0])
                        postponedContent.append(splits[1])
                    else:
                        # We couldn't split this flowable at the desired
                        # point. If we already has added previous paragraphs
                        # to the content, just add everything after the split.
                        # Also try adding it after the split if valign isn't TOP
                        if newCellContent or style.valign != "TOP":
                            if flowable.height <= height1:
                                postponedContent.append(flowable)
                                # Shrink the available height:
                                height1 -= flowable.height
                            else:
                                # The content doesn't fit after the split:
                                return []
                        else:
                            # We could not split this, so we fail:
                            return []

                    split = True

            return (tuple(newCellContent), tuple(postponedContent))

        elif isinstance(value, str):
            rows = value.split("\n")
            lineHeight = 1.2 * style.fontsize
            contentHeight = (style.leading or lineHeight) * len(rows)
            if style.valign == "TOP" and contentHeight <= height0:
                # This fits in the first cell, all is good
                return (value, '')
            elif style.valign == "BOTTOM" and contentHeight <= height1:
                # This fits in the second cell, all is good
                return ('', value)
            elif style.valign == "MIDDLE":
                # Put it in the largest cell:
                if height1 > height0:
                    return ('', value)
                else:
                    return (value, '')

            elif len(rows) < 2:
                # It doesn't fit, and there's nothing to split: Fail
                return []
            # We need to split this, and there are multiple lines, so we can
            if style.valign == "TOP":
                splitPoint = height0 // lineHeight
            elif style.valign == "BOTTOM":
                splitPoint = len(rows) - (height1 // lineHeight)
            else:  # MID
                splitPoint = (height0 - height1 + contentHeight) // (2 * lineHeight)

            splitPoint = int(splitPoint)
            return ('\n'.join(rows[:splitPoint]), '\n'.join(rows[splitPoint:]))

        # No content
        return ('', '')

    def _splitLineCmds(self, n, doInRowSplit=0):
        nrows = self._nrows
        ncols = self._ncols
        #copy the commands
        A = []
        # hack up the line commands
        for op, (sc,sr), (ec,er), weight, color, cap, dash, join, count, space in self._linecmds:
            if isinstance(sr,strTypes) and sr in _SPECIALROWS:
                A.append((op,(sc,sr), (ec,sr), weight, color, cap, dash, join, count, space))
                if sr=='splitlast':
                    sr = er = n-1
                elif sr=='splitfirst':
                    sr = n
                    er = n
                else:
                    if sc < 0: sc += ncols
                    if ec < 0: ec += ncols
                    A[-1] = (op,(sc,sr), (ec,sr), weight, color, cap, dash, join, count, space)
                    continue

            if sc < 0: sc += ncols
            if ec < 0: ec += ncols
            if sr < 0: sr += nrows
            if er < 0: er += nrows

            if op in ('BOX','OUTLINE','GRID'):
                if (sr<n and er>=n) or (doInRowSplit and sr==n):
                    # we have to split the BOX
                    A.append(('LINEABOVE',(sc,sr), (ec,sr), weight, color, cap, dash, join, count, space))
                    A.append(('LINEBEFORE',(sc,sr), (sc,er), weight, color, cap, dash, join, count, space))
                    A.append(('LINEAFTER',(ec,sr), (ec,er), weight, color, cap, dash, join, count, space))
                    A.append(('LINEBELOW',(sc,er), (ec,er), weight, color, cap, dash, join, count, space))
                    if op=='GRID':
                        if doInRowSplit:
                            A.append(('INNERGRID',(sc,sr), (ec,n-1), weight, color, cap, dash, join, count, space))
                            A.append(('INNERGRID',(sc,n), (ec,er), weight, color, cap, dash, join, count, space))
                        else:
                            A.append(('LINEBELOW',(sc,n-1), (ec,n-1), weight, color, cap, dash, join, count, space))
                            A.append(('LINEABOVE',(sc,n), (ec,n), weight, color, cap, dash, join, count, space))
                            A.append(('INNERGRID',(sc,sr), (ec,er), weight, color, cap, dash, join, count, space))
                else:
                    A.append((op,(sc,sr), (ec,er), weight, color, cap, dash, join, count, space))
            elif op == 'INNERGRID':
                if sr<n and er>=n and not doInRowSplit:
                    A.append(('LINEBELOW',(sc,n-1), (ec,n-1), weight, color, cap, dash, join, count, space))
                    A.append(('LINEABOVE',(sc,n), (ec,n), weight, color, cap, dash, join, count, space))
                A.append((op,(sc,sr), (ec,er), weight, color, cap, dash, join, count, space))
            elif op == 'LINEBELOW':
                if sr<n and er>=(n-1):
                    A.append(('LINEABOVE',(sc,n), (ec,n), weight, color, cap, dash, join, count, space))
                A.append((op,(sc,sr), (ec,er), weight, color, cap, dash, join, count, space))
            elif op == 'LINEABOVE':
                if sr<=n and er>=n:
                    A.append(('LINEBELOW',(sc,n-1), (ec,n-1), weight, color, cap, dash, join, count, space))
                A.append((op,(sc,sr), (ec,er), weight, color, cap, dash, join, count, space))
            else:
                A.append((op,(sc,sr), (ec,er), weight, color, cap, dash, join, count, space))

        return A

    def _stretchCommands(self, n, cmds, oldrowcount):
        """Stretches the commands when a row is split

        The row start is sr, the row end is er.

         sr   | er  | result
        ---------------------------------------------------------------------
          <n  |  <n | Do nothing.
              | >=n | A command that spans the break, extend end.
        ---------------------------------------------------------------------
         ==n  | ==n | Zero height. Extend the end, unless it's a LINEABOVE
              |     | commands, it's between rows so do nothing.
              |     | For LINEBELOW increase both.
              |  >n | A command that spans the break, extend end.
        ---------------------------------------------------------------------
          >n  |  >n | This command comes after the break, increase both.
        ---------------------------------------------------------------------

        Summary:
        1. If er > n then increase er
        2. If sr > n then increase sr
        3. If er == n and sr < n, increase er
        4. If er == sr == n and cmd is not line, increase er

        """
        stretched = [].append
        for c in cmds:
            cmd, (sc,sr), (ec,er) = c[0:3]

            if sr in _SPECIALROWS or er in _SPECIALROWS:
                stretched(c)
                continue

            if er < 0:
                er += oldrowcount
            if sr < 0:
                sr += oldrowcount

            if er > n:
                er += 1
            elif  er == n:
                if sr < n or (sr == n and cmd != "LINEABOVE"):
                    er += 1

            if sr > n or (sr == n and cmd == "LINEBELOW"):
                sr += 1

            stretched((cmd, (sc,sr), (ec,er)) + c[3:])

        return stretched.__self__

    def _splitRows(self,availHeight,doInRowSplit=0):
        # Get the split position. if we split between rows (doInRowSplit=0),
        # then n will be the first row after the split. If we split a row,
        # then n is the row we split in two.
        n=self._getFirstPossibleSplitRowPosition(availHeight,ignoreSpans=doInRowSplit)

        # We can't split before or in the repeatRows/headers
        repeatRows = self.repeatRows
        maxrepeat = repeatRows if isinstance(repeatRows,int) else max(repeatRows)+1
        if doInRowSplit and n<maxrepeat or not doInRowSplit and n<=maxrepeat:
            return []

        # If the whole table fits, return it
        lim = len(self._rowHeights)
        if n==lim: return [self]

        lo = self._rowSplitRange
        if lo:
            lo, hi = lo
            if lo<0: lo += lim
            if hi<0: hi += lim
            if n>hi:
                return self._splitRows(availHeight - sum(self._rowHeights[hi:n]), doInRowSplit=doInRowSplit)
            elif n<lo:
                return []

        repeatCols = self.repeatCols

        if not doInRowSplit:
            T = self
            data = self._cellvalues
        else:
            data = [_[:] for _ in self._cellvalues]
            # We are splitting the n row into two, if possible.
            # We can't split if the available height is less than the minimum set:
            if self._minRowHeights and availHeight < self._minRowHeights[n]:
                return []

            usedHeights = sum(self._rowHeights[:n])

            cellvalues = self._cellvalues[n]
            cellStyles = self._cellStyles[n]
            cellWidths = self._colWidths
            curRowHeight = self._rowHeights[n]

            # First find the min/max split point
            minSplit = 0  # Counted from top
            maxSplit = 0  # Counted from bottom
            maxHeight = 0

            for column, (value, style, width) in enumerate(zip(cellvalues, cellStyles, cellWidths)):
                if self._spanCmds and self._spanRanges.get((column, n), None) is None:
                    # This is part of another cell span, the value will not be displayed
                    continue

                if isinstance(value, (tuple, list)):
                    # A sequence of flowables:
                    w, height = self._listCellGeom(value, width, style)
                    height += style.topPadding + style.bottomPadding
                    if height > maxHeight:
                        maxHeight = height
                elif isinstance(value, str):
                    rows = value.split("\n")
                    lineHeight = 1.2 * style.fontsize
                    height = lineHeight * len(rows) + style.topPadding + style.bottomPadding

                    # Make sure we don't try to split in the middle of the first or last line
                    minSplit = max(minSplit, lineHeight + style.topPadding)
                    maxSplit = max(maxSplit, lineHeight + style.bottomPadding)

                    if height > maxHeight:
                        maxHeight = height

            if ((minSplit + maxSplit > curRowHeight) or
                 (minSplit > (availHeight - usedHeights))):
                # We can't split this row. So we should fail, and let the split get retried
                # with splitInRow = 0. However, if there is a spanned row that will also
                # fail. So first we need to check if any cell in the current row is spanned.
                if not self._spanCmds:
                    # There are no spans to look at, so we can skip this and fail directly
                    return []

                splitCells = set()
                for column in range(self._ncols):
                    cell = (column, n)
                    if (cell in self._rowSpanCells and
                        self._spanRanges.get((column, n), None) is None):
                        # This cell is a part of a rowSpan, and not the main cell.
                        # Find the real cell and cell value
                        for cell, span in self._spanRanges.items():
                            if span is None:
                                continue
                            start_col, start_row, end_col, end_row = span
                            if (column >= start_col and
                                column <= end_col and
                                n > start_row and
                                n <= end_row):
                                splitCells.add(cell)
                                break

                if not splitCells:
                    # There were no spanned rows that could be split, so we fail.
                    return []

                spanCmds = []
                for cmd, (sc, sr), (ec, er) in self._spanCmds:
                    # -1 means last row/column, handle that here.
                    if sc < 0:
                        sc += self._ncols
                    if ec < 0:
                        ec += self._ncols
                    if sr < 0:
                        sr += self._nrows
                    if er < 0:
                        er += self._nrows
                    spanCmds.append((cmd, (sc, sr), (ec, er)))

                newCellStyles = [_[:] for _ in self._cellStyles]
                bkgrndcmds = self._bkgrndcmds

                # There are cells spanning the rows we want to split. They can be split,
                # because the  _getFirstPossibleSplitRowPosition() call above checked
                # that they are not in a nosplit range, so let's split them.
                for cell in splitCells:
                    span_sc, span_sr, span_ec, span_er = self._spanRanges[cell]
                    spanRect = self._spanRects[cell]
                    oldHeight = spanRect[3]
                    newHeight = sum(self._rowHeights[span_sr:n])

                    # Copy the style:
                    oldStyle = newCellStyles[span_sr][span_sc]

                    res = self._splitCell(self._cellvalues[span_sr][span_sc],
                                          oldStyle, oldHeight, newHeight, width)
                    if not res:
                        # Could not split
                        return []

                    # Replace the data values:
                    data[span_sr][span_sc] = res[0]
                    data[n][span_sc] = res[1]

                    # Now get replace the rowspan with two new rowspans, or
                    # remove the spans if no span remains

                    newSpanCmds = []
                    for cmd, start, end in spanCmds:
                        if ((span_sc, span_sr) == start and
                            (span_ec, span_er) == end):
                            # Modify this:
                            if n-1 > span_sr or span_sc != span_ec:
                                newSpanCmds.append((cmd, (span_sc, span_sr), (span_ec, n-1)))
                            if n < span_er or span_sc != span_ec:
                                newSpanCmds.append((cmd, (span_sc, n), (span_ec, span_er)))
                        else:
                            newSpanCmds.append((cmd, start, end))

                    spanCmds = newSpanCmds

                    newbkgrndcmds = []
                    for cmd, start, end, color in bkgrndcmds:
                        if start == (span_sc, span_sr):
                            # The cell we are splitting has a background color command.
                            # Add commands for the new split cells:
                            newbkgrndcmds.append((cmd, start, (end[0], n-1), color))
                            newbkgrndcmds.append((cmd, (start[0], n), (end[0], n), color))
                        else:
                            newbkgrndcmds.append((cmd, start, end, color))

                    bkgrndcmds = newbkgrndcmds

                    # And adjust the style
                    newStyle = oldStyle.copy()
                    if oldStyle.valign == "MIDDLE":
                        # Adjust margins
                        if res[0] and res[1]:
                            # We split the content, so fix up the valign:
                            oldStyle.valign = "BOTTOM"
                            newStyle.valign = "TOP"
                        else:
                            # Adjust the margins to push it towards the true middle
                            h = self._listCellGeom(v[0] or v[1], width, oldStyle)[1]
                            margin = (curRowHeight - h) / 2
                            if v[0]:
                                oldStyle.topPadding += margin
                            elif v[1]:
                                newStyle.bottomPadding += margin
                    newCellStyles[n][span_sc] = newStyle

                # Make a new table here
                T = self.__class__( data, colWidths=self._colWidths,
                    rowHeights=self._rowHeights, repeatRows=self.repeatRows,
                    repeatCols=self.repeatCols, splitByRow=self.splitByRow,
                    splitInRow=self.splitInRow, normalizedData=1,
                    cellStyles=newCellStyles, ident=self.ident,
                    spaceBefore=getattr(self,'spaceBefore',None),
                    longTableOptimize=self._longTableOptimize,
                    cornerRadii=getattr(self,'_cornerRadii',None),
                    renderCB=getattr(self,'_renderCB',None),
                    )

                T._bkgrndcmds = bkgrndcmds
                T._spanCmds = spanCmds
                T._nosplitCmds = self._nosplitCmds
                T._srflcmds = self._srflcmds
                T._sircmds = self._sircmds
                T._colpositions = self._colpositions
                T._rowpositions = self._rowpositions

                T._calcNoSplitRanges()
                T._calcSpanRanges()
                T._calcSpanRects()

                # And then, remove any lines that now appear that were inside
                # the spanning cell before the split. First, we need to split
                # the grids, and convert the bit of the grid that spans the
                # split to a line.
                newlinecmds = []
                for linecmd in self._linecmds:
                    op, (sc,sr), (ec,er), weight, color, cap, dash, join, count, space = linecmd
                    # -1 means "to the end", so we handle that here
                    if er < 0:
                        er += T._nrows
                    if ec < 0:
                        ec += T._ncols

                    if ((op == 'BOX') or (op == 'GRID' and (sr <= n or er >=n)) or
                        (op == 'INNERGRID' and (sr < n or er > n))):

                        if op in ('GRID', 'INNERGRID'):
                            newlinecmds.append(('INNERGRID',(sc,sr), (ec,n-1), weight, color, cap, dash, join, count, space))
                            newlinecmds.append(('INNERGRID',(sc,n), (ec,er), weight, color, cap, dash, join, count, space))
                            newlinecmds.append(('LINEBELOW',(sc,n-1), (ec,n-1), weight, color, cap, dash, join, count, space))
                        if op in ('GRID', 'BOX'):
                            # The box must be made of lines, because  otherwise
                            # it might not get split where it should, below.
                            newlinecmds.append(('LINEABOVE', (sc,sr), (ec,sr), weight, color, cap, dash, join, count, space))
                            newlinecmds.append(('LINEBELOW', (sc,er), (ec,er), weight, color, cap, dash, join, count, space))
                            newlinecmds.append(('LINEBEFORE', (sc,sr), (sc,er), weight, color, cap, dash, join, count, space))
                            newlinecmds.append(('LINEAFTER', (ec,sr), (ec,er), weight, color, cap, dash, join, count, space))
                    else:
                        newlinecmds.append(linecmd)
                        continue

                # Then secondly split any LINEABOVE and LINEBELOW so that the
                # split cells don't get them.
                for cell in splitCells:

                    moddedcmds = []
                    for linecmd in newlinecmds:
                        op, (sc,sr), (ec,er), weight, color, cap, dash, join, count, space = linecmd
                        span_sc, span_sr, span_ec, span_er = self._spanRanges[cell]

                        if (((op == "LINEABOVE" and er > span_sr and sr <= span_er) or
                           (op == "LINEBELOW" and er >= span_sr and sr < span_er)) and
                           (sc <= span_ec and ec >= span_sc)):
                            # This needs handling of some sort

                            if op == "LINEABOVE":
                                startrow = span_sr
                                endrow = span_er + 1
                            else:
                                startrow = span_sr - 1
                                endrow = span_er

                            if sr <= startrow:
                                # Anything before the span should be unaffected:
                                moddedcmds.append(
                                    (op, (sc, sr), (ec, startrow), weight, color, cap, dash, join, count, space)
                                )

                            # For any lines in between we need to remove the split cell
                            if span_sc > sc:
                                # The start column of the span is higher than the start column of
                                # the line. So we need a line up until but not including the start column
                                moddedcmds.append(
                                    (op, (sc, max(startrow, sr)), (span_sc-1, min(er, endrow)), weight, color, cap, dash, join, count, space)
                                )
                            if span_ec < ec:
                                # The start column of the span is lower than the end column of
                                # the line. So we need a line up starting after but not including the end column
                                moddedcmds.append(
                                    (op, (span_ec+1, max(startrow, sr)), (ec, min(er, endrow)), weight, color, cap, dash, join, count, space)
                                )

                            if er >= endrow:
                                moddedcmds.append(
                                    (op, (sc, endrow), (ec, er), weight, color, cap, dash, join, count, space)
                                )
                                # Anything after the span should be unaffected:

                        else:
                            moddedcmds.append(linecmd)

                    newlinecmds = moddedcmds

                T._linecmds = newlinecmds

                return T._splitRows(availHeight,doInRowSplit=False)

            # This is where we split the row:
            splitPoint = min(availHeight - usedHeights, maxHeight - maxSplit)
            if splitPoint+1 < self.splitInRow:
                # The height of the split is smaller than the minimum.
                # Fail, and the whole table will be moved to the next page.
                return []

            remaining = self._height - splitPoint
            if remaining < self.splitInRow:
                # The remaining height of the table is smaller than the minimum.
                # Fail, and the whole table will be moved to the next page.
                return []

            R0 = []  # Top half of the row
            R0Height = 0  # Minimum height
            R1 = []  # Bottom half of the row
            R1Height = 0  # Minimum height
            R1Styles = []
            for (value, style, width) in zip(cellvalues, cellStyles, cellWidths):
                v = self._splitCell(value, style, curRowHeight, splitPoint, width)
                if not v:
                    # Splitting the table failed
                    return []

                newStyle = style.copy()
                if style.valign == "MIDDLE":
                    # Adjust margins
                    if v[0] and v[1]:
                        # We split the content, so fix up the valign:
                        style.valign = "BOTTOM"
                        newStyle.valign = "TOP"
                    else:
                        # Adjust the margins to push it towards the true middle
                        h = self._listCellGeom(v[0] or v[1], width, style)[1]
                        margin = (curRowHeight - h) / 2
                        if v[0]:
                            style.topPadding += margin
                        elif v[1]:
                            newStyle.bottomPadding += margin
                R0.append(v[0])
                R1.append(v[1])
                h0 = self._listCellGeom(v[0], width, style)[1] + style.topPadding + style.bottomPadding
                R0Height = max(R0Height, h0)
                h1 = self._listCellGeom(v[1], width, style)[1] + style.topPadding + style.bottomPadding
                R1Height = max(R1Height, h1)
                R1Styles.append(newStyle)

            # Make a new table with the row split into two:
            usedHeight = min(splitPoint, R0Height)
            newRowHeight = max(R1Height, self._rowHeights[n] - usedHeight)
            newRowHeights = self._rowHeights[:]
            newRowHeights.insert(n + 1, newRowHeight)
            newRowHeights[n] = usedHeight
            newCellStyles = self._cellStyles[:]
            newCellStyles.insert(n + 1, R1Styles)

            data = data[:n] + [R0] + [R1] + data[n+1:]

            T = self.__class__( data, colWidths=self._colWidths,
                rowHeights=newRowHeights, repeatRows=self.repeatRows,
                repeatCols=self.repeatCols, splitByRow=self.splitByRow,
                splitInRow=self.splitInRow, normalizedData=1,
                cellStyles=newCellStyles, ident=self.ident,
                spaceBefore=getattr(self,'spaceBefore',None),
                longTableOptimize=self._longTableOptimize,
                cornerRadii=getattr(self,'_cornerRadii',None),
                renderCB=getattr(self,'_renderCB',None),
                )

            T._linecmds = self._stretchCommands(n, self._linecmds, lim)
            T._bkgrndcmds = self._stretchCommands(n, self._bkgrndcmds, lim)
            T._spanCmds = self._stretchCommands(n, self._spanCmds, lim)
            T._nosplitCmds = self._stretchCommands(n, self._nosplitCmds, lim)
            T._srflcmds = self._stretchCommands(n, self._srflcmds, lim)
            T._sircmds = self._stretchCommands(n, self._sircmds, lim)
            n = n + 1

        #we're going to split into two superRows
        ident = self.ident
        if ident: ident = IdentStr(ident)
        lto = T._longTableOptimize
        if lto:
            splitH = T._rowHeights
        else:
            splitH = T._argH

        cornerRadii = getattr(self,'_cornerRadii',None)
        renderCB = getattr(self,'_renderCB',None)
        R0 = self.__class__( data[:n], colWidths=T._colWidths, rowHeights=splitH[:n],
                repeatRows=repeatRows, repeatCols=repeatCols, splitByRow=self.splitByRow,
                splitInRow=self.splitInRow, normalizedData=1, cellStyles=T._cellStyles[:n],
                ident=ident,
                spaceBefore=getattr(self,'spaceBefore',None),
                longTableOptimize=lto,
                cornerRadii=cornerRadii[:2] if cornerRadii else None,
                renderCB=renderCB,
                )

        nrows = T._nrows
        ncols = T._ncols

        _linecmds = T._splitLineCmds(n, doInRowSplit=doInRowSplit)

        R0._cr_0(n,_linecmds,nrows,doInRowSplit)
        R0._cr_0(n,T._bkgrndcmds,nrows,doInRowSplit,_srflMode=True)
        R0._cr_0(n,T._spanCmds,nrows,doInRowSplit)
        R0._cr_0(n,T._nosplitCmds,nrows,doInRowSplit)

        for c in T._srflcmds:
            R0._addCommand(c)
            if c[1][1]!='splitlast': continue
            (sc,sr), (ec,er) = c[1:3]
            R0._addCommand((c[0],)+((sc, n-1), (ec, n-1))+tuple(c[3:]))

        if ident: ident = IdentStr(ident)
        if repeatRows:
            if isinstance(repeatRows,int):
                iRows = data[:repeatRows]
                iRowH = splitH[:repeatRows]
                iCS = T._cellStyles[:repeatRows]
                repeatRows = list(range(repeatRows))
            else:
                #we have a list of repeated rows eg (1,3)
                repeatRows = list(sorted(repeatRows))
                iRows = [data[i] for i in repeatRows]
                iRowH = [splitH[i] for i in repeatRows]
                iCS = [T._cellStyles[i] for i in repeatRows]
            R1 = self.__class__(iRows+data[n:],colWidths=T._colWidths,
                    rowHeights=iRowH+splitH[n:],
                    repeatRows=len(repeatRows), repeatCols=repeatCols,
                    splitByRow=self.splitByRow, splitInRow=self.splitInRow,
                    normalizedData=1,
                    cellStyles=iCS+T._cellStyles[n:],
                    ident=ident,
                    spaceAfter=getattr(self,'spaceAfter',None),
                    longTableOptimize=lto,
                    cornerRadii = cornerRadii,
                    renderCB = renderCB,
                    )
            R1._cr_1_1(n,nrows,repeatRows,_linecmds,doInRowSplit)
            R1._cr_1_1(n,nrows,repeatRows,T._bkgrndcmds,doInRowSplit,_srflMode=True)
            R1._cr_1_1(n,nrows,repeatRows,T._spanCmds,doInRowSplit)
            R1._cr_1_1(n,nrows,repeatRows,T._nosplitCmds,doInRowSplit)
        else:
            #R1 = slelf.__class__(data[n:], self._argW, self._argH[n:],
            R1 = self.__class__(data[n:], colWidths=T._colWidths, rowHeights=splitH[n:],
                    repeatRows=repeatRows, repeatCols=repeatCols,
                    splitByRow=self.splitByRow, splitInRow=self.splitInRow,
                    normalizedData=1, cellStyles=T._cellStyles[n:],
                    ident=ident,
                    spaceAfter=getattr(self,'spaceAfter',None),
                    longTableOptimize=lto,
                    cornerRadii = ([0,0] + cornerRadii[2:]) if cornerRadii else None,
                    renderCB = renderCB,
                    )

            R1._cr_1_0(n,_linecmds,doInRowSplit)
            R1._cr_1_0(n,T._bkgrndcmds,doInRowSplit,_srflMode=True)
            R1._cr_1_0(n,T._spanCmds,doInRowSplit)
            R1._cr_1_0(n,T._nosplitCmds,doInRowSplit)
        for c in T._srflcmds:
            R1._addCommand(c)
            if c[1][1]!='splitfirst': continue
            (sc,sr), (ec,er) = c[1:3]
            R1._addCommand((c[0],)+((sc, 0), (ec, 0))+tuple(c[3:]))

        R0.hAlign = R1.hAlign = T.hAlign
        R0.vAlign = R1.vAlign = T.vAlign
        self.onSplit(R0)
        self.onSplit(R1)
        return [R0,R1]

    def _getRowImpossible(impossible,cells,ranges):
        for xy in cells:
            r=ranges[xy]
            if r!=None:
                y1,y2=r[1],r[3]
                if y1!=y2:
                    ymin=min(y1,y2) #normalize
                    ymax=max(y1,y2) #normalize
                    y=ymin+1
                    while 1:
                        if y>ymax: break
                        impossible[y]=None #split at position y is impossible because of overlapping rowspan
                        y+=1
    _getRowImpossible=staticmethod(_getRowImpossible)

    def _getFirstPossibleSplitRowPosition(self,availHeight,ignoreSpans=0):
        # Returns the LAST possible split row position
        impossible={}
        # With inRowSplits we ignore spans
        if self._spanCmds and not ignoreSpans:
            self._getRowImpossible(impossible,self._rowSpanCells,self._spanRanges)
        if self._nosplitCmds:
            self._getRowImpossible(impossible,self._rowNoSplitCells,self._nosplitRanges)
        h = 0
        n = 1
        split_at = 0 # from this point of view 0 is the first position where the table may *always* be splitted
        for rh in self._rowHeights:
            if h+rh>availHeight:
                break
            if n not in impossible:
                split_at=n
            h=h+rh
            n=n+1
        return split_at

    def split(self, availWidth, availHeight):
        self._calc(availWidth, availHeight)
        if self.splitByRow or self.splitInRow:
            if not rl_config.allowTableBoundsErrors and self._width>availWidth: return []

            # If self.splitByRow is true, first try with doInRowSplit as false.
            # Otherwise, first try with doInRowSplit as true
            result = self._splitRows(availHeight, doInRowSplit=not self.splitByRow)
            if result:
                # That worked, return that:
                return result

            # The first attempt did NOT succeed, now try with the flag flipped
            # (unless self.splitInRow is false)
            if self.splitInRow:
                return self._splitRows(availHeight, doInRowSplit=self.splitByRow)

        # We can't split this table in any way, raise an error:
        return []

    def _makeRoundedCornersClip(self, FUZZ=rl_config._FUZZ):
        self._roundingRectDef = None
        cornerRadii = getattr(self,'_cornerRadii',None)
        if not cornerRadii or max(cornerRadii)<=FUZZ: return
        nrows = self._nrows
        ncols = self._ncols
        ar = [min(self._rowHeights[i],self._colWidths[j],cornerRadii[k]) for
                k,(i,j) in enumerate((
                    (0,0),
                    (0,ncols-1),
                    (nrows-1,0),
                    (nrows-1, ncols-1),
                    ))]
        rp = self._rowpositions
        cp = self._colpositions

        x0 = cp[0]
        y0 = rp[nrows]
        x1 = cp[ncols]
        y1 = rp[0]
        w = x1 - x0
        h = y1 - y0
        self._roundingRectDef = RoundingRectDef(x0, y0, w, h, x1, y1, ar, [])
        P = self.canv.beginPath()
        P.roundRect(x0, y0, w, h, ar)
        c = self.canv
        c.addLiteral('%begin table rect clip')
        c.clipPath(P,stroke=0)
        c.addLiteral('%end table rect clip')

    def _restoreRoundingObscuredLines(self):
        x0, y0, w, h, x1, y1, ar, SL = self._roundingRectDef
        if not SL: return
        canv = self.canv
        canv.saveState()
        ccap = cdash = cjoin = self._curweight = self._curcolor = None
        line = canv.line
        cornerRadii = self._cornerRadii
        for (xs,ys,xe,ye,weight,color,cap,dash,join) in SL:
            if cap!=None and ccap!=cap:
                canv.setLineCap(cap)
                ccap = cap
            if dash is None or dash == []:
                if cdash is not None:
                    canv.setDash()
                    cdash = None
            elif dash != cdash:
                canv.setDash(dash)
                cdash = dash
            if join is not None and cjoin!=join:
                canv.setLineJoin(join)
                cjoin = join
            self._prepLine(weight, color)
            if ys==ye:
                #horizontal line
                if ys>y1 or ys<y0:
                    line(xs,ys,xe,ye)   #simple line that's outside the clip
                    continue
                #which corners are involved
                if ys==y0:
                    ypos = 'bottom'
                    r0 = ar[2]
                    r1 = ar[3]
                else: #ys==y1
                    ypos = 'top'
                    r0 = ar[0]
                    r1 = ar[1]
                if xs>=x0+r0 and xe<=x1-r1:
                    line(xs,ys,xe,ye)   #simple line with no rounding
                    continue
                #we have some rounding so we must use a path
                c0 = _quadrantDef('left',ypos,(xs,ys), r0, kind=2, direction='left-right') if xs<x0+r0 else None
                c1 = _quadrantDef('right',ypos,(xe,ye), r1, kind=1, direction='left-right') if xe>x1-r1 else None
            else:
                #vertical line
                if xs>x1 or xs<x0:
                    line(xs,ys,xe,ye)   #simple line that's outside the clip
                    continue
                #which corners are involved
                if xs==x0:
                    xpos = 'left'
                    r0 = ar[2]
                    r1 = ar[0]
                else: #xs==x1
                    xpos = 'right'
                    r0 = ar[3]
                    r1 = ar[1]
                if ys>=y0+r0 and ye<=y1-r1:
                    line(xs,ys,xe,ye)   #simple line with no rounding
                    continue
                #we have some rounding so we must use a path
                c0 = _quadrantDef(xpos,'bottom',(xs,ys), r0, kind=2, direction='bottom-top') if ys<y0+r0 else None
                c1 = _quadrantDef(xpos,'top',(xe,ye), r1, kind=1, direction='bottom-top') if ye>y1-r1 else None
            P = canv.beginPath()
            if c0:
                P.moveTo(*c0[0])
                P.curveTo(c0[1][0],c0[1][1],c0[2][0],c0[2][1], c0[3][0],c0[3][1])
            else:
                P.moveTo(xs,ys)
            if not c1:
                P.lineTo(xe,ye)
            else:
                P.lineTo(*c1[0])
                P.curveTo(c1[1][0],c1[1][1],c1[2][0],c1[2][1], c1[3][0],c1[3][1])
            canv.drawPath(P, stroke=1, fill=0)
        canv.restoreState()

    def draw(self):
        c = self.canv
        c.saveState()
        self._curweight = self._curcolor = self._curcellstyle = None
        renderCB = getattr(self,'_renderCB')
        if renderCB:
            renderCB(self,'startTable')
            renderCB(self,'startBG')
        self._makeRoundedCornersClip()
        self._drawBkgrnd()
        if renderCB: renderCB(self,'endBG')
        if not self._spanCmds:
            # old fashioned case, no spanning, steam on and do each cell
            if renderCB:
                for rowNo, (row, rowstyle, rowpos, rowheight) in enumerate(zip(self._cellvalues, self._cellStyles, self._rowpositions[1:], self._rowHeights)):
                    renderCB(self,'startRow',rowNo)
                    for colNo, (cellval, cellstyle, colpos, colwidth) in enumerate(zip(row, rowstyle, self._colpositions[:-1], self._colWidths)):
                        renderCB(self,'startCell', rowNo, colNo, cellval, cellstyle, (colpos, rowpos), (colwidth, rowheight))
                        self._drawCell(cellval, cellstyle, (colpos, rowpos), (colwidth, rowheight))
                        renderCB(self,'endCell')
                    renderCB(self,'endRow')
            else:
                for row, rowstyle, rowpos, rowheight in zip(self._cellvalues, self._cellStyles, self._rowpositions[1:], self._rowHeights):
                    for colNo, (cellval, cellstyle, colpos, colwidth) in enumerate(zip(row, rowstyle, self._colpositions[:-1], self._colWidths)):
                        self._drawCell(cellval, cellstyle, (colpos, rowpos), (colwidth, rowheight))
        else:
            # we have some row or col spans, need a more complex algorithm
            # to find the rect for each
            if renderCB:
                for rowNo in range(self._nrows):
                    renderCB(self,'startRow',rowNo)
                    for colNo in range(self._ncols):
                        cellRect = self._spanRects[colNo, rowNo]
                        if cellRect is not None:
                            (x, y, width, height) = cellRect
                            cellval = self._cellvalues[rowNo][colNo]
                            cellstyle = self._cellStyles[rowNo][colNo]
                            renderCB(self,'startCell', rowNo, colNo, cellval, cellstyle, (x, y), (width, height))
                            self._drawCell(cellval, cellstyle, (x, y), (width, height))
                            renderCB(self,'endCell')
                    renderCB(self,'endRow')
            else:
                for rowNo in range(self._nrows):
                    for colNo in range(self._ncols):
                        cellRect = self._spanRects[colNo, rowNo]
                        if cellRect is not None:
                            (x, y, width, height) = cellRect
                            cellval = self._cellvalues[rowNo][colNo]
                            cellstyle = self._cellStyles[rowNo][colNo]
                            self._drawCell(cellval, cellstyle, (x, y), (width, height))
        if renderCB: renderCB(self,'startLines')
        self._drawLines()
        if renderCB:
            renderCB(self,'endLines')
            renderCB(self,'endTable')
        c.restoreState()
        if self._roundingRectDef:
            self._restoreRoundingObscuredLines()

    def _drawBkgrnd(self):
        nrows = self._nrows
        ncols = self._ncols
        canv = self.canv
        colpositions = self._colpositions
        rowpositions = self._rowpositions
        rowHeights = self._rowHeights
        colWidths = self._colWidths
        spanRects = getattr(self,'_spanRects',None)
        for cmd, (sc, sr), (ec, er), arg in self._bkgrndcmds:
            if sr in _SPECIALROWS: continue
            if sc < 0: sc = sc + ncols
            if ec < 0: ec = ec + ncols
            if sr < 0: sr = sr + nrows
            if er < 0: er = er + nrows
            x0 = colpositions[sc]
            y0 = rowpositions[sr]
            x1 = colpositions[min(ec+1,ncols)]
            y1 = rowpositions[min(er+1,nrows)]
            w, h = x1-x0, y1-y0
            if hasattr(arg,'__call__'):
                arg(self,canv, x0, y0, w, h)
            elif cmd == 'ROWBACKGROUNDS':
                #Need a list of colors to cycle through.  The arguments
                #might be already colours, or convertible to colors, or
                # None, or the str 'None'.
                #It's very common to alternate a pale shade with None.
                colorCycle = list(map(colors.toColorOrNone, arg))
                count = len(colorCycle)
                rowCount = er - sr + 1
                for i in range(rowCount):
                    color = colorCycle[i%count]
                    h = rowHeights[sr + i]
                    if color:
                        canv.setFillColor(color)
                        canv.rect(x0, y0, w, -h, stroke=0,fill=1)
                    y0 = y0 - h
            elif cmd == 'COLBACKGROUNDS':
                #cycle through colours columnwise
                colorCycle = list(map(colors.toColorOrNone, arg))
                count = len(colorCycle)
                colCount = ec - sc + 1
                for i in range(colCount):
                    color = colorCycle[i%count]
                    w = colWidths[sc + i]
                    if color:
                        canv.setFillColor(color)
                        canv.rect(x0, y0, w, h, stroke=0,fill=1)
                    x0 = x0 +w
            else:   #cmd=='BACKGROUND'
                if (arg and isinstance(arg,(list,tuple))
                        and arg[0] in ('VERTICAL','HORIZONTAL', 'VERTICAL2', 'HORIZONTAL2',
                                'LINEARGRADIENT', 'RADIALGRADIENT')):
                    if ec==sc and er==sr and spanRects:
                        xywh = spanRects.get((sc,sr))
                        if xywh:
                            #it's a single spanned cell
                            x0, y0, w, h = xywh
                    arg0, arg = arg[0], arg[1:]
                    #
                    # arg is a list, assume we are going for a gradient fill
                    # where we expect a containing a direction for the gradient
                    # and the starting an final gradient colors. For example:
                    # ['HORIZONTAL', colors.white, colors.grey]   or
                    # ['VERTICAL', colors.red, colors.blue]
                    #
                    canv.saveState()
                    p = canv.beginPath()
                    p.rect(x0, y0, w, h)
                    canv.clipPath(p, stroke=0)
                    if arg0=="HORIZONTAL":
                        canv.linearGradient(x0,y0,x0+w,y0,arg,extend=False)
                    elif arg0 == "HORIZONTAL2":
                        xh = x0 + w/2.0
                        canv.linearGradient(x0, y0, xh, y0, arg, extend=False)
                        canv.linearGradient(xh, y0, x0 + w, y0, arg[::-1], extend=False)
                        #canv.linearGradient(x0, y0, x0 + w, y0, arg+arg[1::-1], extend=False)
                    elif arg0 == "VERTICAL2":
                        yh = y0 + h/2.0
                        canv.linearGradient(x0, y0, x0, yh, arg, extend=False)
                        canv.linearGradient(x0, yh, x0, y0 + h, arg[::-1], extend=False)
                        #canv.linearGradient(x0, y0, x0, y0 + h, arg+arg[1::-1], extend=False)
                    elif arg0=="VERTICAL":
                        canv.linearGradient(x0, y0, x0, y0 + h, arg, extend=False)
                    elif arg0=='LINEARGRADIENT':
                        # the remaining arguments define the axis, extend, colors, stops as
                        # axis = (x0,y0, x1, y1)    given as fractions of width / height
                        # extend = bool or [bool, bool]
                        # colors a sequence/list of colors
                        # stops an optional sequence of fractions 0 - 1
                        if 4<=len(arg)<=5:
                            (ax0, ay0), (ax1, ay1) = arg[:2]
                            ax0 = x0 + ax0*w
                            ax1 = x0 + ax1*w
                            ay0 = y0 + ay0*h
                            ay1 = y0 + ay1*h
                            extend = arg[2]
                            C = arg[3]
                            P = arg[4] if len(arg)==4 else None
                            canv.linearGradient(ax0, ay0, ax1, ay1, C, positions=P, extend=extend)
                        else:
                            raise ValueError(f'Wrong length for {op!a} arguments {arg!a}')
                    elif arg0=='RADIALGRADIENT':
                        # the remaining arguments define the centre, radius, extend, colors, stops as
                        # center = (xc,yc) given as fractions of width / height
                        # radius = (r,'ref') op in ('width','height','min','max')
                        # extend = bool or [bool, bool]
                        # colors a sequence/list of colors
                        # stops an optional sequence of fractions 0 - 1
                        if 4<=len(arg)<=5:
                            xc, yc = arg[0]
                            xc = x0 + xc*w
                            yc = y0 + yc*h
                            r, ref = arg[1]
                            if ref=='width':
                                ref = w
                            elif ref=='height':
                                ref = h
                            elif ref=='min':
                                ref = min (w,h)
                            elif ref=='max':
                                ref = max(w,h)
                            else:
                                raise ValueError(f'Bad radius, {arg[1]!a}, for {op!a} arguments {arg!r}')
                            r *= ref
                            extend = arg[2]
                            C = arg[3]
                            P = arg[4] if len(arg)==4 else None
                            canv.radialGradient(xc, yc, r, C, positions=P, extend=extend)
                        else:
                            raise ValueError(f'Wrong length for {op!a} arguments {arg}')
                    canv.restoreState()
                else:
                    color = colors.toColorOrNone(arg)
                    if color:
                        if ec==sc and er==sr and spanRects:
                            xywh = spanRects.get((sc,sr))
                            if xywh:
                                #it's a single cell
                                x0, y0, w, h = xywh
                        canv.setFillColor(color)
                        canv.rect(x0, y0, w, h, stroke=0,fill=1)

    def _drawCell(self, cellval, cellstyle, pos, size):
        colpos, rowpos = pos
        colwidth, rowheight = size
        if self._curcellstyle is not cellstyle:
            cur = self._curcellstyle
            if cur is None or cellstyle.color != cur.color:
                self.canv.setFillColor(cellstyle.color)
            if cur is None or cellstyle.leading != cur.leading or cellstyle.fontname != cur.fontname or cellstyle.fontsize != cur.fontsize:
                self.canv.setFont(cellstyle.fontname, cellstyle.fontsize, cellstyle.leading)
            self._curcellstyle = cellstyle

        just = cellstyle.alignment
        valign = cellstyle.valign
        if isinstance(cellval,(tuple,list,Flowable)):
            if not isinstance(cellval,(tuple,list)): cellval = (cellval,)
            # we assume it's a list of Flowables
            W = []
            H = []
            w, h = self._listCellGeom(cellval,colwidth,cellstyle,W=W, H=H,aH=rowheight)
            if valign=='TOP':
                y = rowpos + rowheight - cellstyle.topPadding
            elif valign=='BOTTOM':
                y = rowpos+cellstyle.bottomPadding + h
            else:
                y = rowpos+(rowheight+cellstyle.bottomPadding-cellstyle.topPadding+h)/2.0
            if cellval: y += cellval[0].getSpaceBefore()
            for v, w, h in zip(cellval,W,H):
                if just=='LEFT': x = colpos+cellstyle.leftPadding
                elif just=='RIGHT': x = colpos+colwidth-cellstyle.rightPadding - w
                elif just in ('CENTRE', 'CENTER'):
                    x = colpos+(colwidth+cellstyle.leftPadding-cellstyle.rightPadding-w)/2.0
                else:
                    raise ValueError(f'Invalid justification {just!a} for {type(v)}')
                y -= v.getSpaceBefore()
                y -= h
                v.drawOn(self.canv,x,y)
                y -= v.getSpaceAfter()
        else:
            if just == 'LEFT':
                draw = self.canv.drawString
                x = colpos + cellstyle.leftPadding
            elif just in ('CENTRE', 'CENTER'):
                draw = self.canv.drawCentredString
                x = colpos+(colwidth+cellstyle.leftPadding-cellstyle.rightPadding)*0.5
            elif just == 'RIGHT':
                draw = self.canv.drawRightString
                x = colpos + colwidth - cellstyle.rightPadding
            elif just == 'DECIMAL':
                draw = self.canv.drawAlignedString
                x = colpos + colwidth - cellstyle.rightPadding
            else:
                raise ValueError(f'Invalid justification {just!a}')
            vals = str(cellval).split("\n")
            n = len(vals)
            leading = cellstyle.leading
            fontsize = cellstyle.fontsize
            if valign=='BOTTOM':
                y = rowpos + cellstyle.bottomPadding+n*leading-fontsize
            elif valign=='TOP':
                y = rowpos + rowheight - cellstyle.topPadding - fontsize
            elif valign=='MIDDLE':
                #tim roberts pointed out missing fontsize correction 2004-10-04
                y = rowpos + (cellstyle.bottomPadding + rowheight-cellstyle.topPadding+n*leading)/2.0 - fontsize
            else:
                raise ValueError(f'Bad valign: {valign!a}')

            for v in vals:
                draw(x, y, v)
                y -= leading
            onDraw = getattr(cellval,'onDraw',None)
            if onDraw:
                onDraw(self.canv,cellval.kind,cellval.label)

        if cellstyle.href:
            #external hyperlink
            self.canv.linkURL(cellstyle.href, (colpos, rowpos, colpos + colwidth, rowpos + rowheight), relative=1)
        if cellstyle.destination:
            #external hyperlink
            self.canv.linkRect("", cellstyle.destination, Rect=(colpos, rowpos, colpos + colwidth, rowpos + rowheight), relative=1)

    def _setCornerRadii(self, cornerRadii):
        if isListOfNumbersOrNone(cornerRadii):
            self._cornerRadii = None if not cornerRadii else list(cornerRadii) + (max(4-len(cornerRadii),0)*[0])
        else:
            raise ValueError(f'cornerRadii should be None or a list/tuple of numeric radii\nnot {cornerRadii!a}')

_LineOpMap = {  'GRID':'_drawGrid',
                'BOX':'_drawBox',
                'OUTLINE':'_drawBox',
                'INNERGRID':'_drawInnerGrid',
                'LINEBELOW':'_drawHLinesB',
                'LINEABOVE':'_drawHLines',
                'LINEBEFORE':'_drawVLines',
                'LINEAFTER':'_drawVLinesA', }

class LongTable(Table):
    '''Henning von Bargen's changes will be active'''
    _longTableOptimize = 1

LINECOMMANDS = list(_LineOpMap.keys())

class TableRenderCB:
    '''table render callback abstract base klass to be called in Table.draw'''
    def __call__(self,T,cmd,*args):
        if not isinstance(T,Table): raise ValueError(f'TableRenderCB first argument, {repr(T)} is not a Table')
        meth = getattr(self,cmd,None)
        if not meth: raise ValueError(f'invalid TablerenderCB cmd {cmd}')
        meth(T,*args)
    def startTable(self,T):
        raise NotImplementedError('startTable')
    def startBG(self,T):
        raise NotImplementedError('startBG')
    def endBG(self,T):
        raise NotImplementedError('endBG')
    def startRow(self,T,rowNo):
        raise NotImplementedError('startRow')
    def startCell(self,T,rowNo, colNo, cellval, cellstyle, pos, size):
        raise NotImplementedError('startCell')
    def endCell(self,T):
        raise NotImplementedError('endCell')
    def endRow(self,T):
        raise NotImplementedError('endRow')
    def startLines(self,T):
        raise NotImplementedError('startLines')
    def endLines(self,T):
        raise NotImplementedError('endLines')
    def endTable(self,T):
        raise NotImplementedError('endTable')

def _isLineCommand(cmd):
    return cmd[0] in LINECOMMANDS

def _setCellStyle(cellStyles, i, j, op, values):
    #new = CellStyle('<%d, %d>' % (i,j), cellStyles[i][j])
    #cellStyles[i][j] = new
    ## modify in place!!!
    new = cellStyles[i][j]
    if op == 'FONT':
        n = len(values)
        new.fontname = values[0]
        if n>1:
            new.fontsize = values[1]
            if n>2:
                new.leading = values[2]
            else:
                new.leading = new.fontsize*1.2
    elif op in ('FONTNAME', 'FACE'):
        new.fontname = values[0]
    elif op in ('SIZE', 'FONTSIZE'):
        new.fontsize = values[0]
    elif op == 'LEADING':
        new.leading = values[0]
    elif op == 'TEXTCOLOR':
        new.color = colors.toColor(values[0], colors.Color(0,0,0))
    elif op in ('ALIGN', 'ALIGNMENT'):
        new.alignment = values[0]
    elif op == 'VALIGN':
        new.valign = values[0]
    elif op == 'LEFTPADDING':
        new.leftPadding = values[0]
    elif op == 'RIGHTPADDING':
        new.rightPadding = values[0]
    elif op == 'TOPPADDING':
        new.topPadding = values[0]
    elif op == 'BOTTOMPADDING':
        new.bottomPadding = values[0]
    elif op == 'HREF':
        new.href = values[0]
    elif op == 'DESTINATION':
        new.destination = values[0]

GRID_STYLE = TableStyle(
    [('GRID', (0,0), (-1,-1), 0.25, colors.black),
     ('ALIGN', (1,1), (-1,-1), 'RIGHT')]
    )
BOX_STYLE = TableStyle(
    [('BOX', (0,0), (-1,-1), 0.50, colors.black),
     ('ALIGN', (1,1), (-1,-1), 'RIGHT')]
    )
LABELED_GRID_STYLE = TableStyle(
    [('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
     ('BOX', (0,0), (-1,-1), 2, colors.black),
     ('LINEBELOW', (0,0), (-1,0), 2, colors.black),
     ('LINEAFTER', (0,0), (0,-1), 2, colors.black),
     ('ALIGN', (1,1), (-1,-1), 'RIGHT')]
    )
COLORED_GRID_STYLE = TableStyle(
    [('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
     ('BOX', (0,0), (-1,-1), 2, colors.red),
     ('LINEBELOW', (0,0), (-1,0), 2, colors.black),
     ('LINEAFTER', (0,0), (0,-1), 2, colors.black),
     ('ALIGN', (1,1), (-1,-1), 'RIGHT')]
    )
LIST_STYLE = TableStyle(
    [('LINEABOVE', (0,0), (-1,0), 2, colors.green),
     ('LINEABOVE', (0,1), (-1,-1), 0.25, colors.black),
     ('LINEBELOW', (0,-1), (-1,-1), 2, colors.green),
     ('ALIGN', (1,1), (-1,-1), 'RIGHT')]
    )

# experimental iterator which can apply a sequence
# of colors e.g. Blue, None, Blue, None as you move
# down.
if __name__ == '__main__':
    from tests.test_platypus_tables import old_tables_test
    old_tables_test()
