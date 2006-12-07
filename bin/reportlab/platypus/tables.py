#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/platypus/tables.py
__version__=''' $Id$ '''

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
from reportlab.lib.styles import PropertySet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.utils import fp_str
from reportlab.pdfbase import pdfmetrics
import operator, string
from types import TupleType, ListType, StringType

class CellStyle(PropertySet):
    defaults = {
        'fontname':'Times-Roman',
        'fontsize':10,
        'leading':12,
        'leftPadding':6,
        'rightPadding':6,
        'topPadding':3,
        'bottomPadding':3,
        'firstLineIndent':0,
        'color':colors.black,
        'alignment': 'LEFT',
        'background': (1,1,1),
        'valign': 'BOTTOM',
        }

LINECAPS={'butt':0,'round':1,'projecting':2,'squared':2}
LINEJOINS={'miter':0,'round':1,'bevel':2}

# experimental replacement
class CellStyle1(PropertySet):
    fontname = "Times-Roman"
    fontsize = 10
    leading = 12
    leftPadding = 6
    rightPadding = 6
    topPadding = 3
    bottomPadding = 3
    firstLineIndent = 0
    color = colors.black
    alignment = 'LEFT'
    background = (1,1,1)
    valign = "BOTTOM"
    def __init__(self, name, parent=None):
        self.name = name
        if parent is not None:
            parent.copy(self)
    def copy(self, result=None):
        if result is None:
            result = CellStyle1()
        for name in dir(self):
            setattr(result, name, gettattr(self, name))
        return result
CellStyle = CellStyle1

class TableStyle:
    def __init__(self, cmds=None, parent=None, **kw):
        #handle inheritance from parent first.
        commands = []
        if parent:
            # copy the parents list at construction time
            commands = commands + parent.getCommands()
            self._opts = parent._opts
        if cmds:
            commands = commands + list(cmds)
        self._cmds = commands
        self._opts={}
        self._opts.update(kw)

    def add(self, *cmd):
        self._cmds.append(cmd)
    def __repr__(self):
        L = map(repr, self._cmds)
        import string
        L = string.join(L, "  \n")
        return "TableStyle(\n%s\n) # end TableStyle" % L
    def getCommands(self):
        return self._cmds

TableStyleType = type(TableStyle())
_SeqTypes = (TupleType, ListType)

def _rowLen(x):
    return type(x) not in _SeqTypes and 1 or len(x)

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
        if type(v) is type(""):
            v = v.strip()
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
    for idx in xrange(count):
        canvLine(scp, y, ecp, y)
        y -= ws

class Table(Flowable):
    def __init__(self, data, colWidths=None, rowHeights=None, style=None,
                repeatRows=0, repeatCols=0, splitByRow=1, emptyTableAction=None):
        self.hAlign = 'CENTER'
        self.vAlign = 'MIDDLE'
        if type(data) not in _SeqTypes:
            raise ValueError, "%s invalid data type" % self.identity()
        self._nrows = nrows = len(data)
        self._cellvalues = []
        _seqCW = type(colWidths) in _SeqTypes
        _seqRH = type(rowHeights) in _SeqTypes
        if nrows: self._ncols = ncols = max(map(_rowLen,data))
        elif colWidths and _seqCW: ncols = len(colWidths)
        else: ncols = 0
        if not emptyTableAction: emptyTableAction = rl_config.emptyTableAction
        if not (nrows and ncols):
            if emptyTableAction=='error':
                raise ValueError, "%s must have at least a row and column" % self.identity()
            elif emptyTableAction=='indicate':
                self.__class__ = Preformatted
                global _emptyTableStyle
                if '_emptyTableStyle' not in globals().keys():
                    _emptyTableStyle = ParagraphStyle('_emptyTableStyle')
                    _emptyTableStyle.textColor = colors.red
                    _emptyTableStyle.backColor = colors.yellow
                Preformatted.__init__(self,'%s(%d,%d)' % (self.__class__.__name__,nrows,ncols), _emptyTableStyle)
            elif emptyTableAction=='ignore':
                self.__class__ = Spacer
                Spacer.__init__(self,0,0)
            else:
                raise ValueError, '%s bad emptyTableAction: "%s"' % (self.identity(),emptyTableAction)
            return

        self._cellvalues = data
        if not _seqCW: colWidths = ncols*[colWidths]
        elif len(colWidths) != ncols:
            raise ValueError, "%s data error - %d columns in data but %d in grid" % (self.identity(),ncols, len(colWidths))
        if not _seqRH: rowHeights = nrows*[rowHeights]
        elif len(rowHeights) != nrows:
            raise ValueError, "%s data error - %d rows in data but %d in grid" % (self.identity(),nrows, len(rowHeights))
        for i in range(nrows):
            if len(data[i]) != ncols:
                raise ValueError, "%s not enough data points in row %d!" % (self.identity(),i)
        self._rowHeights = self._argH = rowHeights
        self._colWidths = self._argW = colWidths
        cellrows = []
        for i in range(nrows):
            cellcols = []
            for j in range(ncols):
                cellcols.append(CellStyle(`(i,j)`))
            cellrows.append(cellcols)
        self._cellStyles = cellrows

        self._bkgrndcmds = []
        self._linecmds = []
        self._spanCmds = []
        self.repeatRows = repeatRows
        self.repeatCols = repeatCols
        self.splitByRow = splitByRow

        if style:
            self.setStyle(style)
    def __repr__(self):
        "incomplete, but better than nothing"
        r = getattr(self,'_rowHeights','[unknown]')
        c = getattr(self,'_colWidths','[unknown]')
        cv = getattr(self,'_cellvalues','[unknown]')
        import pprint, string
        cv = pprint.pformat(cv)
        cv = string.replace(cv, "\n", "\n  ")
        return "%s(\n rowHeights=%s,\n colWidths=%s,\n%s\n) # end table" % (self.__class__.__name__,r,c,cv)

    def identity(self, maxLen=30):
        '''Identify our selves as well as possible'''
        vx = None
        nr = getattr(self,'_nrows','unknown')
        nc = getattr(self,'_ncols','unknown')
        cv = getattr(self,'_cellvalues',None)
        if cv and 'unknown' not in (nr,nc):
            b = 0
            for i in xrange(nr):
                for j in xrange(nc):
                    v = cv[i][j]
                    t = type(v)
                    if t in _SeqTypes or isinstance(v,Flowable):
                        if not t in _SeqTypes: v = (v,)
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
                        b = (vx and t is StringType) and 1 or 0
                        if maxLen: vx = vx[:maxLen]
                    if b: break
                if b: break
        if vx:
            vx = ' with cell(%d,%d) containing\n%s' % (ix,jx,repr(vx))
        else:
            vx = '...'

        return "<%s at %d %d rows x %s cols>%s" % (self.__class__.__name__, id(self), nr, nc, vx)

    def _listCellGeom(self, V,w,s,W=None,H=None,aH=72000):
        aW = w-s.leftPadding-s.rightPadding
        aH = aH - s.topPadding - s.bottomPadding
        t = 0
        w = 0
        canv = getattr(self,'canv',None)
        for v in V:
            vw, vh = v.wrapOn(canv,aW, aH)
            if W is not None: W.append(vw)
            if H is not None: H.append(vh)
            w = max(w,vw)
            t = t + vh + v.getSpaceBefore()+v.getSpaceAfter()
        return w, t - V[0].getSpaceBefore()-V[-1].getSpaceAfter()

    def _calc_width(self,availWidth,W=None):
        if getattr(self,'_width_calculated_once',None): return
        #comments added by Andy to Robin's slightly terse variable names
        if not W: W = _calc_pc(self._argW,availWidth)   #widths array
        if None in W:  #some column widths are not given
            canv = getattr(self,'canv',None)
            saved = None
            colSpanCells = self._spanCmds and self._colSpanCells or ()
            if W is self._argW: W = W[:]
            while None in W:
                j = W.index(None) #find first unspecified column
                f = lambda x,j=j: operator.getitem(x,j)
                V = map(f,self._cellvalues)  #values for this column
                S = map(f,self._cellStyles)  #styles for this column
                w = 0
                i = 0

                for v, s in map(None, V, S):
                    #if the current cell is part of a spanned region,
                    #assume a zero size.
                    if (j, i) in colSpanCells:
                        t = 0.0
                    else:#work out size
                        t = self._elementWidth(v,s)
                        if t is None:
                            raise ValueError, "Flowable %s in cell(%d,%d) can't have auto width\n%s" % (v.identity(30),i,j,self.identity(30))
                        t = t + s.leftPadding+s.rightPadding
                    if t>w: w = t   #record a new maximum
                    i = i + 1

                W[j] = w

        self._colWidths = W
        width = 0
        self._colpositions = [0]        #index -1 is right side boundary; we skip when processing cells
        for w in W:
            width = width + w
            self._colpositions.append(width)

        self._width = width
        self._width_calculated_once = 1

    def _elementWidth(self,v,s):
        t = type(v)
        if t in _SeqTypes:
            w = 0
            for e in v:
                ew = self._elementWidth(self,v)
                if ew is None: return None
                w = max(w,ew)
            return w
        elif isinstance(v,Flowable) and v._fixedWidth:
            return v.width
        else:
            if t is not StringType: v = v is None and '' or str(v)
            v = string.split(v, "\n")
            return max(map(lambda a, b=s.fontname, c=s.fontsize,d=pdfmetrics.stringWidth: d(a,b,c), v))

    def _calc_height(self, availHeight, availWidth, H=None, W=None):

        H = self._argH
        if not W: W = _calc_pc(self._argW,availWidth)   #widths array

        hmax = lim = len(H)
        longTable = getattr(self,'_longTableOptimize',None)

        if None in H:
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
            if canv: saved = canv._fontname, canv._fontsize, canv._leading
            H = H[:]    #make a copy as we'll change it
            self._rowHeights = H
            while None in H:
                i = H.index(None)
                if longTable:
                    hmax = i
                    height = reduce(operator.add, H[:i], 0)
                    # we can stop if we have filled up all available room
                    if height > availHeight: break
                V = self._cellvalues[i] # values for row i
                S = self._cellStyles[i] # styles for row i
                h = 0
                j = 0
                for v, s, w in map(None, V, S, W): # value, style, width (lengths must match)
                    ji = j,i
                    if ji in rowSpanCells:
                        t = 0.0  # don't count it, it's either occluded or unreliable
                    else:
                        t = type(v)
                        if t in _SeqTypes or isinstance(v,Flowable):
                            if not t in _SeqTypes: v = (v,)
                            if w is None:
                                raise ValueError, "Flowable %s in cell(%d,%d) can't have auto width in\n%s" % (v[0].identity(30),i,j,self.identity(30))
                            if canv: canv._fontname, canv._fontsize, canv._leading = s.fontname, s.fontsize, s.leading or 1.2*s.fontsize
                            if ji in colSpanCells:
                                t = spanRanges[ji]
                                w = max(colpositions[t[2]+1]-colpositions[t[0]],w)
                            dW,t = self._listCellGeom(v,w,s)
                            if canv: canv._fontname, canv._fontsize, canv._leading = saved
                            dW = dW + s.leftPadding + s.rightPadding
                            if not rl_config.allowTableBoundsErrors and dW>w:
                                raise "LayoutError", "Flowable %s (%sx%s points) too wide for cell(%d,%d) (%sx* points) in\n%s" % (v[0].identity(30),fp_str(dW),fp_str(t),i,j, fp_str(w), self.identity(30))
                        else:
                            if t is not StringType:
                                v = v is None and '' or str(v)
                            v = string.split(v, "\n")
                            t = s.leading*len(v)
                        t = t+s.bottomPadding+s.topPadding
                    if t>h: h = t   #record a new maximum
                    j = j + 1
                H[i] = h
            if None not in H: hmax = lim

        height = self._height = reduce(operator.add, H[:hmax], 0)
        self._rowpositions = [height]    # index 0 is actually topline; we skip when processing cells
        for h in H[:hmax]:
            height = height - h
            self._rowpositions.append(height)
        assert abs(height)<1e-8, 'Internal height error'
        self._hmax = hmax

    def _calc(self, availWidth, availHeight):
        #if hasattr(self,'_width'): return

        #in some cases there are unsizable things in
        #cells.  If so, apply a different algorithm
        #and assign some withs in a dumb way.
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

        # calculate the full table height
        self._calc_height(availHeight,availWidth,W=W)

        # calculate the full table width
        self._calc_width(availWidth,W=W)

        if self._spanCmds:
            #now work out the actual rect for each spanned cell from the underlying grid
            self._calcSpanRects()

    def _hasVariWidthElements(self, upToRow=None):
        """Check for flowables in table cells and warn up front.

        Allow a couple which we know are fixed size such as
        images and graphics."""
        bad = 0
        if upToRow is None: upToRow = self._nrows
        for row in range(min(self._nrows, upToRow)):
            for col in range(self._ncols):
                value = self._cellvalues[row][col]
                if not self._canGetWidth(value):
                    bad = 1
                    #raise Exception('Unsizable elements found at row %d column %d in table with content:\n %s' % (row, col, value))
        return bad

    def _canGetWidth(self, thing):
        "Can we work out the width quickly?"
        if type(thing) in (ListType, TupleType):
            for elem in thing:
                if not self._canGetWidth(elem):
                    return 0
            return 1
        elif isinstance(thing, Flowable):
            return thing._fixedWidth  # must loosen this up
        else: #string, number, None etc.
            #anything else gets passed to str(...)
            # so should be sizable
            return 1

    def _calcPreliminaryWidths(self, availWidth):
        """Fallback algorithm for when main one fails.

        Where exact width info not given but things like
        paragraphs might be present, do a preliminary scan
        and assign some sensible values - just divide up
        all unsizeable columns by the remaining space."""

        W = _calc_pc(self._argW,availWidth) #widths array
        verbose = 0
        totalDefined = 0.0
        numberUndefined = 0
        for w in W:
            if w is None:
                numberUndefined = numberUndefined + 1
            else:
                totalDefined = totalDefined + w
        if verbose: print 'prelim width calculation.  %d columns, %d undefined width, %0.2f units remain' % (
            self._ncols, numberUndefined, availWidth - totalDefined)

        #check columnwise in each None column to see if they are sizable.
        given = []
        sizeable = []
        unsizeable = []
        for colNo in range(self._ncols):
            if W[colNo] is None:
                siz = 1
                for rowNo in range(self._nrows):
                    value = self._cellvalues[rowNo][colNo]
                    if not self._canGetWidth(value):
                        siz = 0
                        break
                if siz:
                    sizeable.append(colNo)
                else:
                    unsizeable.append(colNo)
            else:
                given.append(colNo)
        if len(given) == self._ncols:
            return
        if verbose: print 'predefined width:   ',given
        if verbose: print 'uncomputable width: ',unsizeable
        if verbose: print 'computable width:    ',sizeable

        #how much width is left:
        # on the next iteration we could size the sizeable ones, for now I'll just
        # divide up the space
        newColWidths = list(W)
        guessColWidth = (availWidth - totalDefined) / (len(unsizeable)+len(sizeable))
        assert guessColWidth >= 0, "table is too wide already, cannot choose a sane width for undefined columns"
        if verbose: print 'assigning width %0.2f to all undefined columns' % guessColWidth
        for colNo in sizeable:
            newColWidths[colNo] = guessColWidth
        for colNo in unsizeable:
            newColWidths[colNo] = guessColWidth

        if verbose: print 'new widths are:', newColWidths
        self._argW = self._colWidths = newColWidths
        return newColWidths

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
        for x in xrange(self._ncols):
            for y in xrange(self._nrows):
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
                #column span
                if x0!=x1:
                    for y in xrange(y0, y1+1):
                        for x in xrange(x0,x1+1):
                            csa((x,y))
                #row span
                if y0!=y1:
                    for y in xrange(y0, y1+1):
                        for x in xrange(x0,x1+1):
                            rsa((x,y))

                for y in xrange(y0, y1+1):
                    for x in xrange(x0,x1+1):
                        spanRanges[x,y] = None
                # set the main entry
                spanRanges[x0,y0] = (x0, y0, x1, y1)

    def _calcSpanRects(self):
        """Work out rects for tables which do row and column spanning.

        Based on self._spanRanges, which is already known,
        and the widths which were given or previously calculated,
        self._spanRects shows the real coords for drawing:
          (col, row) -> (x, y, width, height)

        for each cell.  Any cell which 'does not exist' as another
        has spanned over it will get a None entry on the right
        """
        if getattr(self,'_spanRects',None): return
        colpositions = self._colpositions
        rowpositions = self._rowpositions
        self._spanRects = spanRects = {}
        self._vBlocks = vBlocks = {}
        self._hBlocks = hBlocks = {}
        for (coord, value) in self._spanRanges.items():
            if value is None:
                spanRects[coord] = None
            else:
                col,row = coord
                col0, row0, col1, row1 = value
                if col1-col0>0:
                    for _ in xrange(col0+1,col1+1):
                        vBlocks.setdefault(colpositions[_],[]).append((rowpositions[row1+1],rowpositions[row0]))
                if row1-row0>0:
                    for _ in xrange(row0+1,row1+1):
                        hBlocks.setdefault(rowpositions[_],[]).append((colpositions[col0],colpositions[col1+1]))
                x = colpositions[col0]
                y = rowpositions[row1+1]
                width = colpositions[col1+1] - x
                height = rowpositions[row0] - y
                spanRects[coord] = (x, y, width, height)

        for _ in hBlocks, vBlocks:
            for value in _.values():
                value.sort()

    def setStyle(self, tblstyle):
        if type(tblstyle) is not TableStyleType:
            tblstyle = TableStyle(tblstyle)
        for cmd in tblstyle.getCommands():
            self._addCommand(cmd)
        for k,v in tblstyle._opts.items():
            setattr(self,k,v)

    def _addCommand(self,cmd):
        if cmd[0] in ('BACKGROUND','ROWBACKGROUNDS','COLBACKGROUNDS'):
            self._bkgrndcmds.append(cmd)
        elif cmd[0] == 'SPAN':
            self._spanCmds.append(cmd)
        elif _isLineCommand(cmd):
            # we expect op, start, stop, weight, colour, cap, dashes, join
            cmd = tuple(cmd)
            if len(cmd)<5: raise ValueError('bad line command '+str(cmd))

            #determine line cap value at position 5. This can be string or numeric.
            if len(cmd)<6:
                cmd = cmd+(1,)
            else:
                cap = cmd[5]
                try:
                    if type(cap) is not type(int):
                        cap = LINECAPS[cap]
                    elif cap<0 or cap>2:
                        raise ValueError
                    cmd = cmd[:5]+(cap,)+cmd[6:]
                except:
                    ValueError('Bad cap value %s in %s'%(cap,str(cmd)))
            #dashes at index 6 - this is a dash array:
            if len(cmd)<7: cmd = cmd+(None,)

            #join mode at index 7 - can be string or numeric, look up as for caps
            if len(cmd)<8: cmd = cmd+(1,)
            else:
                join = cmd[7]
                try:
                    if type(join) is not type(int):
                        join = LINEJOINS[cap]
                    elif join<0 or join>2:
                        raise ValueError
                    cmd = cmd[:7]+(join,)
                except:
                    ValueError('Bad join value %s in %s'%(join,str(cmd)))

            #linecount at index 8.  Default is 1, set to 2 for double line.
            if len(cmd)<9:
                lineCount = 1
                cmd = cmd + (lineCount,)
            else:
                lineCount = cmd[8]
            assert lineCount >= 1
            #linespacing at index 9. Not applicable unless 2+ lines, defaults to line
            #width so you get a visible gap between centres
            if len(cmd)<10: cmd = cmd + (cmd[3],)

            assert len(cmd) == 10

            self._linecmds.append(cmd)
        else:
            (op, (sc, sr), (ec, er)), values = cmd[:3] , cmd[3:]
            if sc < 0: sc = sc + self._ncols
            if ec < 0: ec = ec + self._ncols
            if sr < 0: sr = sr + self._nrows
            if er < 0: er = er + self._nrows
            for i in range(sr, er+1):
                for j in range(sc, ec+1):
                    _setCellStyle(self._cellStyles, i, j, op, values)

    def _drawLines(self):
        ccap, cdash, cjoin = None, None, None
        self.canv.saveState()
        for op, (sc,sr), (ec,er), weight, color, cap, dash, join, count, space in self._linecmds:
            if type(sr) is type('') and sr.startswith('split'): continue
            if sc < 0: sc = sc + self._ncols
            if ec < 0: ec = ec + self._ncols
            if sr < 0: sr = sr + self._nrows
            if er < 0: er = er + self._nrows
            if cap!=None and ccap!=cap:
                self.canv.setLineCap(cap)
                ccap = cap
            getattr(self,_LineOpMap.get(op, '_drawUnknown' ))( (sc, sr), (ec, er), weight, color, count, space)
        self.canv.restoreState()
        self._curcolor = None

    def _drawUnknown(self,  (sc, sr), (ec, er), weight, color, count, space):
        raise ValueError, "Unknown line command '%s'" % op

    def _drawGrid(self, (sc, sr), (ec, er), weight, color, count, space):
        self._drawBox( (sc, sr), (ec, er), weight, color, count, space)
        self._drawInnerGrid( (sc, sr), (ec, er), weight, color, count, space)

    def _drawBox(self,  (sc, sr), (ec, er), weight, color, count, space):
        self._drawHLines((sc, sr), (ec, sr), weight, color, count, space)
        self._drawHLines((sc, er+1), (ec, er+1), weight, color, count, space)
        self._drawVLines((sc, sr), (sc, er), weight, color, count, space)
        self._drawVLines((ec+1, sr), (ec+1, er), weight, color, count, space)

    def _drawInnerGrid(self, (sc, sr), (ec, er), weight, color, count, space):
        self._drawHLines((sc, sr+1), (ec, er), weight, color, count, space)
        self._drawVLines((sc+1, sr), (ec, er), weight, color, count, space)

    def _prepLine(self, weight, color):
        if color != self._curcolor:
            self.canv.setStrokeColor(color)
            self._curcolor = color
        if weight != self._curweight:
            self.canv.setLineWidth(weight)
            self._curweight = weight

    def _drawHLines(self, (sc, sr), (ec, er), weight, color, count, space):
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

    def _drawHLinesB(self, (sc, sr), (ec, er), weight, color, count, space):
        self._drawHLines((sc, sr+1), (ec, er+1), weight, color, count, space)

    def _drawVLines(self, (sc, sr), (ec, er), weight, color, count, space):
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

    def _drawVLinesA(self, (sc, sr), (ec, er), weight, color, count, space):
        self._drawVLines((sc+1, sr), (ec+1, er), weight, color, count, space)

    def wrap(self, availWidth, availHeight):
        self._calc(availWidth, availHeight)
        #nice and easy, since they are predetermined size
        self.availWidth = availWidth
        return (self._width, self._height)

    def onSplit(self,T,byRow=1):
        '''
        This method will be called when the Table is split.
        Special purpose tables can override to do special stuff.
        '''
        pass

    def _cr_0(self,n,cmds):
        for c in cmds:
            c = tuple(c)
            (sc,sr), (ec,er) = c[1:3]
            if sr>=n: continue
            if er>=n: er = n-1
            self._addCommand((c[0],)+((sc, sr), (ec, er))+c[3:])

    def _cr_1_1(self,n,repeatRows, cmds):
        for c in cmds:
            c = tuple(c)
            (sc,sr), (ec,er) = c[1:3]
            if sr in ('splitfirst','splitlast'): self._addCommand(c)
            else:
                if sr>=0 and sr>=repeatRows and sr<n and er>=0 and er<n: continue
                if sr>=repeatRows and sr<n: sr=repeatRows
                elif sr>=repeatRows and sr>=n: sr=sr+repeatRows-n
                if er>=repeatRows and er<n: er=repeatRows
                elif er>=repeatRows and er>=n: er=er+repeatRows-n
                self._addCommand((c[0],)+((sc, sr), (ec, er))+c[3:])

    def _cr_1_0(self,n,cmds):
        for c in cmds:
            c = tuple(c)
            (sc,sr), (ec,er) = c[1:3]
            if sr in ('splitfirst','splitlast'): self._addCommand(c)
            else:
                if er>=0 and er<n: continue
                if sr>=0 and sr<n: sr=0
                if sr>=n: sr = sr-n
                if er>=n: er = er-n
                self._addCommand((c[0],)+((sc, sr), (ec, er))+c[3:])

    def _splitRows(self,availHeight):
        h = 0
        n = 0
        lim = len(self._rowHeights)
        while n<self._hmax:
            hn = h + self._rowHeights[n]
            if hn>availHeight: break
            h = hn
            n = n + 1

        if n<=self.repeatRows:
            return []

        if n==lim: return [self]

        repeatRows = self.repeatRows
        repeatCols = self.repeatCols
        splitByRow = self.splitByRow
        data = self._cellvalues

        #we're going to split into two superRows
        #R0 = slelf.__class__( data[:n], self._argW, self._argH[:n],
        R0 = self.__class__( data[:n], self._colWidths, self._argH[:n],
                repeatRows=repeatRows, repeatCols=repeatCols,
                splitByRow=splitByRow)

        #copy the styles and commands
        R0._cellStyles = self._cellStyles[:n]

        A = []
        # hack up the line commands
        for op, (sc,sr), (ec,er), weight, color, cap, dash, join, count, space in self._linecmds:
            if type(sr)is type('') and sr.startswith('split'):
                A.append((op,(sc,sr), (ec,sr), weight, color, cap, dash, join, count, space))
                if sr=='splitlast':
                    sr = er = n-1
                elif sr=='splitfirst':
                    sr = n
                    er = n

            if sc < 0: sc = sc + self._ncols
            if ec < 0: ec = ec + self._ncols
            if sr < 0: sr = sr + self._nrows
            if er < 0: er = er + self._nrows

            if op in ('BOX','OUTLINE','GRID'):
                if sr<n and er>=n:
                    # we have to split the BOX
                    A.append(('LINEABOVE',(sc,sr), (ec,sr), weight, color, cap, dash, join, count, space))
                    A.append(('LINEBEFORE',(sc,sr), (sc,er), weight, color, cap, dash, join, count, space))
                    A.append(('LINEAFTER',(ec,sr), (ec,er), weight, color, cap, dash, join, count, space))
                    A.append(('LINEBELOW',(sc,er), (ec,er), weight, color, cap, dash, join, count, space))
                    if op=='GRID':
                        A.append(('LINEBELOW',(sc,n-1), (ec,n-1), weight, color, cap, dash, join, count, space))
                        A.append(('LINEABOVE',(sc,n), (ec,n), weight, color, cap, dash, join, count, space))
                        A.append(('INNERGRID',(sc,sr), (ec,er), weight, color, cap, dash, join, count, space))
                else:
                    A.append((op,(sc,sr), (ec,er), weight, color, cap, dash, join, count, space))
            elif op in ('INNERGRID','LINEABOVE'):
                if sr<n and er>=n:
                    A.append(('LINEBELOW',(sc,n-1), (ec,n-1), weight, color, cap, dash, join, count, space))
                    A.append(('LINEABOVE',(sc,n), (ec,n), weight, color, cap, dash, join, count, space))
                A.append((op,(sc,sr), (ec,er), weight, color, cap, dash, join, count, space))
            elif op == 'LINEBELOW':
                if sr<n and er>=(n-1):
                    A.append(('LINEABOVE',(sc,n), (ec,n), weight, color, cap, dash, join, count, space))
                A.append((op,(sc,sr), (ec,er), weight, color))
            elif op == 'LINEABOVE':
                if sr<=n and er>=n:
                    A.append(('LINEBELOW',(sc,n-1), (ec,n-1), weight, color, cap, dash, join, count, space))
                A.append((op,(sc,sr), (ec,er), weight, color, cap, dash, join, count, space))
            else:
                A.append((op,(sc,sr), (ec,er), weight, color, cap, dash, join, count, space))

        R0._cr_0(n,A)
        R0._cr_0(n,self._bkgrndcmds)

        if repeatRows:
            #R1 = slelf.__class__(data[:repeatRows]+data[n:],self._argW,
            R1 = self.__class__(data[:repeatRows]+data[n:],self._colWidths,
                    self._argH[:repeatRows]+self._argH[n:],
                    repeatRows=repeatRows, repeatCols=repeatCols,
                    splitByRow=splitByRow)
            R1._cellStyles = self._cellStyles[:repeatRows]+self._cellStyles[n:]
            R1._cr_1_1(n,repeatRows,A)
            R1._cr_1_1(n,repeatRows,self._bkgrndcmds)
        else:
            #R1 = slelf.__class__(data[n:], self._argW, self._argH[n:],
            R1 = self.__class__(data[n:], self._colWidths, self._argH[n:],
                    repeatRows=repeatRows, repeatCols=repeatCols,
                    splitByRow=splitByRow)
            R1._cellStyles = self._cellStyles[n:]
            R1._cr_1_0(n,A)
            R1._cr_1_0(n,self._bkgrndcmds)


        R0.hAlign = R1.hAlign = self.hAlign
        R0.vAlign = R1.vAlign = self.vAlign
        self.onSplit(R0)
        self.onSplit(R1)
        return [R0,R1]

    def split(self, availWidth, availHeight):
        self._calc(availWidth, availHeight)
        if self.splitByRow:
            if not rl_config.allowTableBoundsErrors and self._width>availWidth: return []
            return self._splitRows(availHeight)
        else:
            raise NotImplementedError

    def draw(self):
        self._curweight = self._curcolor = self._curcellstyle = None
        self._drawBkgrnd()
        if self._spanCmds == []:
            # old fashioned case, no spanning, steam on and do each cell
            for row, rowstyle, rowpos, rowheight in map(None, self._cellvalues, self._cellStyles, self._rowpositions[1:], self._rowHeights):
                for cellval, cellstyle, colpos, colwidth in map(None, row, rowstyle, self._colpositions[:-1], self._colWidths):
                    self._drawCell(cellval, cellstyle, (colpos, rowpos), (colwidth, rowheight))
        else:
            # we have some row or col spans, need a more complex algorithm
            # to find the rect for each
            for rowNo in range(self._nrows):
                for colNo in range(self._ncols):
                    cellRect = self._spanRects[colNo, rowNo]
                    if cellRect is not None:
                        (x, y, width, height) = cellRect
                        cellval = self._cellvalues[rowNo][colNo]
                        cellstyle = self._cellStyles[rowNo][colNo]
                        self._drawCell(cellval, cellstyle, (x, y), (width, height))
        self._drawLines()


    def _drawBkgrnd(self):
        nrows = self._nrows
        ncols = self._ncols
        for cmd, (sc, sr), (ec, er), arg in self._bkgrndcmds:
            if sc < 0: sc = sc + ncols
            if ec < 0: ec = ec + ncols
            if sr < 0: sr = sr + nrows
            if er < 0: er = er + nrows
            x0 = self._colpositions[sc]
            y0 = self._rowpositions[sr]
            x1 = self._colpositions[min(ec+1,ncols)]
            y1 = self._rowpositions[min(er+1,nrows)]
            w, h = x1-x0, y1-y0
            canv = self.canv
            if callable(arg):
                apply(arg,(self,canv, x0, y0, w, h))
            elif cmd == 'ROWBACKGROUNDS':
                #Need a list of colors to cycle through.  The arguments
                #might be already colours, or convertible to colors, or
                # None, or the string 'None'.
                #It's very common to alternate a pale shade with None.
                #print 'rowHeights=', self._rowHeights
                colorCycle = map(colors.toColorOrNone, arg)
                count = len(colorCycle)
                rowCount = er - sr + 1
                for i in range(rowCount):
                    color = colorCycle[i%count]
                    h = self._rowHeights[sr + i]
                    if color:
                        canv.setFillColor(color)
                        canv.rect(x0, y0, w, -h, stroke=0,fill=1)
                    #print '    draw %0.0f, %0.0f, %0.0f, %0.0f' % (x0,y0,w,-h)
                    y0 = y0 - h

            elif cmd == 'COLBACKGROUNDS':
                #cycle through colours columnwise
                colorCycle = map(colors.toColorOrNone, arg)
                count = len(colorCycle)
                colCount = ec - sc + 1
                for i in range(colCount):
                    color = colorCycle[i%count]
                    w = self._colWidths[sc + i]
                    if color:
                        canv.setFillColor(color)
                        canv.rect(x0, y0, w, h, stroke=0,fill=1)
                    x0 = x0 +w
            else:   #cmd=='BACKGROUND'
                canv.setFillColor(colors.toColor(arg))
                canv.rect(x0, y0, w, h, stroke=0,fill=1)

    def _drawCell(self, cellval, cellstyle, (colpos, rowpos), (colwidth, rowheight)):
        if self._curcellstyle is not cellstyle:
            cur = self._curcellstyle
            if cur is None or cellstyle.color != cur.color:
                self.canv.setFillColor(cellstyle.color)
            if cur is None or cellstyle.leading != cur.leading or cellstyle.fontname != cur.fontname or cellstyle.fontsize != cur.fontsize:
                self.canv.setFont(cellstyle.fontname, cellstyle.fontsize, cellstyle.leading)
            self._curcellstyle = cellstyle

        just = cellstyle.alignment
        valign = cellstyle.valign
        n = type(cellval)
        if n in _SeqTypes or isinstance(cellval,Flowable):
            if not n in _SeqTypes: cellval = (cellval,)
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
            y = y+cellval[0].getSpaceBefore()
            for v, w, h in map(None,cellval,W,H):
                if just=='LEFT': x = colpos+cellstyle.leftPadding
                elif just=='RIGHT': x = colpos+colwidth-cellstyle.rightPadding - w
                elif just in ('CENTRE', 'CENTER'):
                    x = colpos+(colwidth+cellstyle.leftPadding-cellstyle.rightPadding-w)/2.0
                else:
                    raise ValueError, 'Invalid justification %s' % just
                y = y - v.getSpaceBefore()
                y = y - h
                v.drawOn(self.canv,x,y)
                y = y - v.getSpaceAfter()
        else:
            if just == 'LEFT':
                draw = self.canv.drawString
                x = colpos + cellstyle.leftPadding
            elif just in ('CENTRE', 'CENTER'):
                draw = self.canv.drawCentredString
                x = colpos + colwidth * 0.5
            elif just == 'RIGHT':
                draw = self.canv.drawRightString
                x = colpos + colwidth - cellstyle.rightPadding
            elif just == 'DECIMAL':
                draw = self.canv.drawAlignedString
                x = colpos + colwidth - cellstyle.rightPadding
            else:
                raise ValueError, 'Invalid justification %s' % just
            if n is StringType: val = cellval
            else: val = str(cellval)
            vals = string.split(val, "\n")
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
                raise ValueError, "Bad valign: '%s'" % str(valign)

            for v in vals:
                draw(x, y, v)
                y = y-leading

# for text,
#   drawCentredString(self, x, y, text) where x is center
#   drawRightString(self, x, y, text) where x is right
#   drawString(self, x, y, text) where x is left

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

LINECOMMANDS = _LineOpMap.keys()

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
    from reportlab.test.test_platypus_tables import old_tables_test
    old_tables_test()
