try:
    from pylibdmtx import pylibdmtx
except ImportError:
    pylibdmtx = None
    __all__ = ()
else:
    __all__=('DataMatrix',)

from reportlab.graphics.barcode.common import Barcode
from reportlab.lib.utils import asBytes
from reportlab.platypus.paraparser import _num as paraparser_num
from reportlab.graphics.widgetbase import Widget
from reportlab.lib.validators import isColor, isString, isColorOrNone, isNumber, isBoxAnchor
from reportlab.lib.attrmap import AttrMap, AttrMapValue
from reportlab.lib.colors import toColor
from reportlab.graphics.shapes import Group, Rect

def _numConv(x):
    return x if isinstance(x,(int,float)) else paraparser_num(x)

class _DMTXCheck:
    @classmethod
    def pylibdmtx_check(cls):
        if not pylibdmtx:
            raise ValueError('The %s class requires package pylibdmtx' % cls.__name__)

class DataMatrix(Barcode,_DMTXCheck):
    def __init__(self, value='', **kwds):
        self.pylibdmtx_check()
        self._recalc = True
        self.value = value
        self.cellSize = kwds.pop('cellSize','5x5')
        self.size = kwds.pop('size','SquareAuto')
        self.encoding = kwds.pop('encoding','Ascii')
        self.anchor = kwds.pop('anchor','sw')
        self.color = kwds.pop('color',(0,0,0))
        self.bgColor = kwds.pop('bgColor',None)
        self.x = kwds.pop('x',0)
        self.y = kwds.pop('y',0)
        self.border = kwds.pop('border',5)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self,v):
        self._value = asBytes(v)
        self._recalc = True

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self,v):
        self._size = self._checkVal('size', v, pylibdmtx.ENCODING_SIZE_NAMES)
        self._recalc = True

    @property
    def border(self):
        return self._border

    @border.setter
    def border(self,v):
        self._border = _numConv(v)
        self._recalc = True

    @property
    def x(self):
        return self._x

    @x.setter
    def x(self,v):
        self._x = _numConv(v)
        self._recalc = True

    @property
    def y(self):
        return self._y

    @y.setter
    def y(self,v):
        self._y = _numConv(v)
        self._recalc = True

    @property
    def cellSize(self):
        return self._cellSize

    @size.setter
    def cellSize(self,v):
        self._cellSize = v
        self._recalc = True

    @property
    def encoding(self):
        return self._encoding

    @encoding.setter
    def encoding(self,v):
        self._encoding = self._checkVal('encoding', v, pylibdmtx.ENCODING_SCHEME_NAMES)
        self._recalc = True

    @property
    def anchor(self):
        return self._anchor

    @anchor.setter
    def anchor(self,v):
        self._anchor = self._checkVal('anchor', v, ('n','ne','e','se','s','sw','w','nw','c'))
        self._recalc = True

    def recalc(self):
        if not self._recalc: return
        data = self._value
        size = self._size
        encoding = self._encoding
        e = pylibdmtx.encode(data, size=size, scheme=encoding)
        iW = e.width
        iH = e.height
        p = e.pixels
        iCellSize = 5
        bpp = 3 #bytes per pixel
        rowLen = iW*bpp
        cellLen = iCellSize*bpp
        assert len(p)//rowLen == iH
        matrix = list(filter(None,
                            (''.join(
                                (('x' if p[j:j+bpp] != b'\xff\xff\xff' else ' ')
                                for j in range(i,i+rowLen,cellLen))).strip()
                            for i in range(0,iH*rowLen,rowLen*iCellSize))))
        self._nRows = len(matrix)
        self._nCols = len(matrix[-1])
        self._matrix = '\n'.join(matrix)

        cellWidth = self._cellSize
        if cellWidth:
            cellWidth = cellWidth.split('x')
            if len(cellWidth)>2:
                raise ValueError('cellSize needs to be distance x distance not %r' % self._cellSize)
            elif len(cellWidth)==2:
                cellWidth, cellHeight = cellWidth
            else:
                cellWidth = cellHeight = cellWidth[0]
            cellWidth = _numConv(cellWidth)
            cellHeight = _numConv(cellHeight)
        else:
            cellWidth = cellHeight = iCellSize
        self._cellWidth = cellWidth
        self._cellHeight = cellHeight
        self._recalc = False
        self._bord = max(self.border,cellWidth,cellHeight)
        self._width = cellWidth*self._nCols + 2*self._bord
        self._height = cellHeight*self._nRows + 2*self._bord

    @property
    def matrix(self):
        self.recalc()
        return self._matrix

    @property
    def width(self):
        self.recalc()
        return self._width

    @property
    def height(self):
        self.recalc()
        return self._height

    @property
    def cellWidth(self):
        self.recalc()
        return self._cellWidth

    @property
    def cellHeight(self):
        self.recalc()
        return self._cellHeight

    def draw(self):
        self.recalc()
        canv = self.canv
        w = self.width
        h = self.height
        x = self.x
        y = self.y
        b = self._bord

        anchor = self.anchor
        if anchor in ('nw','n','ne'):
            y -= h
        elif anchor in ('c','e','w'):
            y -= h//2
        if anchor in ('ne','e','se'):
            x -= w
        elif anchor in ('n','c','s'):
            x -= w//2

        canv.saveState()
        if self.bgColor:
            canv.setFillColor(toColor(self.bgColor))
            canv.rect(x, y-h, w, h, fill=1, stroke=0)
        canv.setFillColor(toColor(self.color))
        canv.setStrokeColor(None)

        cellWidth = self.cellWidth
        cellHeight = self.cellHeight
        yr = y - b - cellHeight
        x += b
        for row in self.matrix.split('\n'):
            xr = x 
            for c in row:
                if c=='x':
                    canv.rect(xr, yr, cellWidth, cellHeight, fill=1, stroke=0)
                xr += cellWidth
            yr -= cellHeight
        canv.restoreState()
    

class DataMatrixWidget(Widget,_DMTXCheck):
    codeName = "DataMatrix"
    _attrMap = AttrMap(
        BASE = Widget,
        value = AttrMapValue(isString, desc='Datamatrix data'),
        x = AttrMapValue(isNumber, desc='x-coord'),
        y = AttrMapValue(isNumber, desc='y-coord'),
        color = AttrMapValue(isColor, desc='foreground color'),
        bgColor = AttrMapValue(isColorOrNone, desc='background color'),
        encoding = AttrMapValue(isString, desc='encoding'),
        size = AttrMapValue(isString, desc='size'),
        cellSize = AttrMapValue(isString, desc='cellSize'),
        anchor = AttrMapValue(isBoxAnchor, desc='anchor pooint for x,y'),
        )

    _defaults = dict(
        x = ('0',_numConv),
        y = ('0',_numConv),
        color = ('black',toColor),
        bgColor = (None,lambda _: toColor(_) if _ is not None else _),
        encoding = ('Ascii',None),
        size = ('SquareAuto',None),
        cellSize = ('5x5',None),
        anchor = ('sw', None),
        )
    def __init__(self,value='Hello Cruel World!', **kwds):
        self.pylibdmtx_check()
        self.value = value
        for k,(d,c) in self._defaults.items():
            v = kwds.pop(k,d)
            if c: v = c(v)
            setattr(self,k,v)

    def rect(self, x, y, w, h, fill=1, stroke=0):
        self._gadd(Rect(x,y,w,h,strokeColor=None,fillColor=self._fillColor))

    def saveState(self,*args,**kwds):
        pass

    restoreState = setStrokeColor = saveState

    def setFillColor(self,c):
        self._fillColor = c

    def draw(self):
        m = DataMatrix(value=self.value,**{k: getattr(self,k) for k in self._defaults})
        m.canv = self
        m.y += m.height
        g = Group()
        self._gadd = g.add
        m.draw()
        return g
