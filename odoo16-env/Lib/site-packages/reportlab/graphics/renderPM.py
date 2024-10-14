#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history www.reportlab.co.uk/rl-cgi/viewcvs.cgi/rlextra/graphics/Csrc/renderPM/renderP.py
__version__='3.3.0'
__doc__="""Render drawing objects in common bitmap formats

Usage::

    from reportlab.graphics import renderPM
    renderPM.drawToFile(drawing,filename,fmt='GIF',configPIL={....})

Other functions let you create a PM drawing as string or into a PM buffer.
Execute the script to see some test drawings."""

from reportlab.graphics.shapes import *
from reportlab.graphics.renderbase import getStateDelta, renderScaledDrawing
from reportlab.pdfbase.pdfmetrics import getFont, unicode2T1
from reportlab.lib.utils import isUnicode
from reportlab.lib.colors import toColor, white
from reportlab import rl_config
from .utils import setFont as _setFont, RenderPMError

import os, sys
from io import BytesIO, StringIO
from math import sin, cos, pi, ceil

def _getPMBackend(backend=None):
    if not backend: backend = rl_config.renderPMBackend
    if backend=='_renderPM':
        try:
            import _rl_renderPM as M
        except ImportError as errMsg:
            try:
                import rlPyCairo as M
            except ImportError:
                raise RenderPMError("""Cannot import desired renderPM backend, {backend}.
No module named _rl_renderPM
it may be badly or not installed!
You may need to install development tools
or seek advice at the users list see
https://pairlist2.pair.net/mailman/listinfo/reportlab-users""")
    elif 'cairo' in backend.lower():
        try:
            import rlPyCairo as M
        except ImportError as errMsg:
            try:
                import _rl_renderPM as M
            except ImportError:
                raise RenderPMError(f"""cannot import desired renderPM backend {backend}
Seek advice at the users list see
https://pairlist2.pair.net/mailman/listinfo/reportlab-users""")
    else:
        raise RenderPMError(f'Invalid renderPM backend, {backend}')
    return M

try:
    _pmBackend = _getPMBackend(rl_config.renderPMBackend)
except RenderPMError:
    _pmBackend=None

def _getImage():
    try:
        from PIL import Image
    except ImportError:
        import Image
    return Image

def Color2Hex(c):
    #assert isinstance(colorobj, colors.Color) #these checks don't work well RGB
    if c: return ((0xFF&int(255*c.red)) << 16) | ((0xFF&int(255*c.green)) << 8) | (0xFF&int(255*c.blue))
    return c

def CairoColor(c):
    '''
    c should be None or something convertible to Color
    rlPyCairo.GState can handle Color directly in either RGB24 or ARGB32
    '''
    return toColor(c) if c is not None else c

# the main entry point for users...
def draw(drawing, canvas, x, y, showBoundary=rl_config._unset_):
    """As it says"""
    R = _PMRenderer()
    R.draw(renderScaledDrawing(drawing), canvas, x, y, showBoundary=showBoundary)

from reportlab.graphics.renderbase import Renderer
class _PMRenderer(Renderer):
    """This draws onto a pix map image. It needs to be a class
    rather than a function, as some image-specific state tracking is
    needed outside of the state info in the SVG model."""

    def pop(self):
        self._tracker.pop()
        self.applyState()

    def push(self,node):
        deltas = getStateDelta(node)
        self._tracker.push(deltas)
        self.applyState()

    def applyState(self):
        s = self._tracker.getState()
        self._canvas.ctm = s['ctm']
        self._canvas.strokeWidth = s['strokeWidth']
        alpha = s['strokeOpacity']
        if alpha is not None:
            self._canvas.strokeOpacity = alpha
        self._canvas.setStrokeColor(s['strokeColor'])
        self._canvas.lineCap = s['strokeLineCap']
        self._canvas.lineJoin = s['strokeLineJoin']
        self._canvas.fillMode = s['fillMode']
        da = s['strokeDashArray']
        if not da:
            da = None
        else:
            if not isinstance(da,(list,tuple)):
                da = da,
            if len(da)!=2 or not isinstance(da[1],(list,tuple)):
                da = 0, da  #assume phase of 0
        self._canvas.dashArray = da
        alpha = s['fillOpacity']
        if alpha is not None:
            self._canvas.fillOpacity = alpha
        self._canvas.setFillColor(s['fillColor'])
        self._canvas.setFont(s['fontName'], s['fontSize'])

    def initState(self,x,y):
        deltas = self._tracker._combined[-1]
        deltas['transform'] = deltas['ctm'] = self._canvas._baseCTM[0:4]+(x,y)
        self._tracker.push(deltas)
        self.applyState()

    def drawNode(self, node):
        """This is the recursive method called for each node
        in the tree"""

        #apply state changes
        self.push(node)

        #draw the object, or recurse
        self.drawNodeDispatcher(node)

        # restore the state
        self.pop()

    def drawRect(self, rect):
        c = self._canvas
        if rect.rx == rect.ry == 0:
            #plain old rectangle, draw clockwise (x-axis to y-axis) direction
            c.rect(rect.x,rect.y, rect.width, rect.height)
        else:
            c.roundRect(rect.x,rect.y, rect.width, rect.height, rect.rx, rect.ry)

    def drawLine(self, line):
        self._canvas.line(line.x1,line.y1,line.x2,line.y2)

    def drawImage(self, image):
        path = image.path
        if isinstance(path,str):
            if not (path and os.path.isfile(path)): return
            im = _getImage().open(path).convert('RGB')
        elif hasattr(path,'convert'):
            im = path.convert('RGB')
        else:
            return
        srcW, srcH = im.size
        dstW, dstH = image.width, image.height
        if dstW is None: dstW = srcW
        if dstH is None: dstH = srcH
        self._canvas._aapixbuf(
                image.x, image.y, dstW, dstH,
                (im if self._canvas._backend=='rlPyCairo' #rlPyCairo has a from_pil method
                    else (im.tobytes if hasattr(im,'tobytes') else im.tostring)()),
                srcW, srcH, 3,
                )

    def drawCircle(self, circle):
        c = self._canvas
        c.circle(circle.cx,circle.cy, circle.r)
        c.fillstrokepath()

    def drawPolyLine(self, polyline, _doClose=0):
        P = polyline.points
        assert len(P) >= 2, 'Polyline must have 1 or more points'
        c = self._canvas
        c.pathBegin()
        c.moveTo(P[0], P[1])
        for i in range(2, len(P), 2):
            c.lineTo(P[i], P[i+1])
        if _doClose:
            c.pathClose()
            c.pathFill()
        c.pathStroke()

    def drawEllipse(self, ellipse):
        c=self._canvas
        c.ellipse(ellipse.cx, ellipse.cy, ellipse.rx,ellipse.ry)
        c.fillstrokepath()

    def drawPolygon(self, polygon):
        self.drawPolyLine(polygon,_doClose=1)

    def drawString(self, stringObj):
        canv = self._canvas
        fill = canv.fillColor
        textRenderMode = getattr(stringObj,'textRenderMode',0)
        if fill is not None or textRenderMode:
            S = self._tracker.getState()
            text_anchor = S['textAnchor']
            fontName = S['fontName']
            fontSize = S['fontSize']
            text = stringObj.text
            x = stringObj.x
            y = stringObj.y
            if not text_anchor in ['start','inherited']:
                textLen = stringWidth(text, fontName,fontSize)
                if text_anchor=='end':
                    x -= textLen
                elif text_anchor=='middle':
                    x -= textLen/2
                elif text_anchor=='numeric':
                    x -= numericXShift(text_anchor,text,textLen,fontName,fontSize,stringObj.encoding)
                else:
                    raise ValueError('bad value for textAnchor '+str(text_anchor))
            oldTextRenderMode = canv.textRenderMode
            canv.textRenderMode = textRenderMode
            try:
                canv.drawString(x,y,text,_fontInfo=(fontName,fontSize))
            finally:
                canv.textRenderMode = oldTextRenderMode

    def drawPath(self, path):
        c = self._canvas
        if path is EmptyClipPath:
            del c._clipPaths[-1]
            if c._clipPaths:
                P = c._clipPaths[-1]
                icp = P.isClipPath
                P.isClipPath = 1
                self.drawPath(P)
                P.isClipPath = icp
            else:
                c.clipPathClear()
            return
        from reportlab.graphics.shapes import _renderPath
        drawFuncs = (c.moveTo, c.lineTo, c.curveTo, c.pathClose)
        autoclose = getattr(path,'autoclose','')
        def rP(forceClose=False):
            c.pathBegin()
            return _renderPath(path, drawFuncs, forceClose=forceClose)
        if path.isClipPath:
            rP()
            c.clipPathSet()
            c._clipPaths.append(path)
        fill = c.fillColor is not None
        stroke = c.strokeColor is not None
        fillMode = getattr(path,'fillMode',-1)
        if autoclose=='svg':
            if fill and stroke:
                rP(forceClose=True)
                c.pathFill(fillMode)
                rP()
                c.pathStroke()
            elif fill:
                rP(forceClose=True)
                c.pathFill(fillMode)
            elif stroke:
                rP()
                c.pathStroke()
        elif autoclose=='pdf':
            rP(forceClose=True)
            if fill:
                c.pathFill(fillMode)
            if stroke:
                c.pathStroke()
        else:
            if rP():
                c.pathFill(fillMode)
            c.pathStroke()

def _convert2pilp(im):
    Image = _getImage()
    return im.convert("P", dither=Image.NONE, palette=Image.ADAPTIVE)

def _convert2pilL(im):
    return im.convert("L")

def _convert2pil1(im):
    return im.convert("1")

def _saveAsPICT(im,fn,fmt,transparent=None):
    im = _convert2pilp(im)
    cols, rows = im.size
    s = _pmBackend.pil2pict(cols,rows,(im.tobytes if hasattr(im,'tobytes') else im.tostring)(),im.im.getpalette())
    if not hasattr(fn,'write'):
        with open(os.path.splitext(fn)[0]+'.'+fmt.lower(),'wb') as f:
            f.write(s)
        if os.name=='mac':
            from reportlab.lib.utils import markfilename
            markfilename(fn,ext='PICT')
    else:
        fn.write(s)

_pycairoFmtsMap = dict(ARGB='ARGB32',RGBA='ARGB32',RGB='RGB24')
BEZIER_ARC_MAGIC = 0.5522847498     #constant for drawing circular arcs w/ Beziers
class PMCanvas:
    def __init__(self,w,h,dpi=72,bg=0xffffff,configPIL=None,backend=None,
                    backendFmt='RGB'):
        '''configPIL dict is passed to image save method'''
        scale = dpi/72.0
        w = int(w*scale+0.5)
        h = int(h*scale+0.5)
        self.__dict__['_gs'] = self._getGState(w,h,bg,backend,fmt=backendFmt)
        self.__dict__['_bg'] = bg
        self.__dict__['_baseCTM'] = (scale,0,0,scale,0,0)
        self.__dict__['_clipPaths'] = []
        self.__dict__['configPIL'] = configPIL
        self.__dict__['_dpi'] = dpi
        #the _rl_renderPM.gstate object doesn't support hasattr so we use this as a proxy test for 'isbuiltin' 
        self.__dict__['_backend'] = '_renderPM' if type(self._gs._aapixbuf)==type(pow) else 'rlPyCairo'
        self.__dict__['_backendfmt'] = backendFmt
        self.__dict__['_colorConverter'] = CairoColor if self._backend=='rlPyCairo' else Color2Hex
        self.ctm = self._baseCTM

    @staticmethod
    def _getGState(w, h, bg, backend=None, fmt='RGB24'):
        mod = _getPMBackend(backend)
        if backend is None:
            backend = rl_config.renderPMBackend
        if backend=='_renderPM':
            try:
                return mod.gstate(w,h,bg=bg)
            except TypeError:
                try:
                    return mod.GState(w,h,bg,fmt=fmt)
                except:
                    pass
        elif 'cairo' in backend.lower():
            fmt = fmt.upper()
            fmt = _pycairoFmtsMap.get(fmt,fmt)
            try:
                return mod.GState(w,h,bg,fmt=fmt)
            except AttributeError:
                return mod.gstate(w,h,bg=bg)
        raise RuntimeError(f'Cannot obtain PM graphics state using backend {backend!r}')

    def _drawTimeResize(self,w,h,bg=None):
        if bg is None: bg = self._bg
        self._drawing.width, self._drawing.height = w, h
        A = {'ctm':None, 'strokeWidth':None, 'strokeColor':None, 'lineCap':None, 'lineJoin':None, 'dashArray':None, 'fillColor':None}
        gs = self._gs
        fN,fS = gs.fontName, gs.fontSize
        for k in A.keys():
            A[k] = getattr(gs,k)
        del gs, self._gs
        gs = self.__dict__['_gs'] = _pmBackend.gstate(w,h,bg=bg)
        for k in A.keys():
            setattr(self,k,A[k])
        gs.setFont(fN,fS)

    def toPIL(self):
        im = _getImage().new('RGBA' if self._backend=='rlPyCairo' and getattr(self,'_fmt')=='ARGB32' else 'RGB', size=(self._gs.width, self._gs.height))
        im.frombytes(self._gs.pixBuf)
        return im

    def saveToFile(self,fn,fmt=None):
        im = self.toPIL()
        if fmt is None:
            if not isinstance(fn,str):
                raise ValueError("Invalid value '%s' for fn when fmt is None" % ascii(fn))
            fmt = os.path.splitext(fn)[1]
            if fmt.startswith('.'): fmt = fmt[1:]
        configPIL = self.configPIL or {}
        configPIL.setdefault('preConvertCB',None)
        preConvertCB=configPIL.pop('preConvertCB')
        if preConvertCB:
            im = preConvertCB(im)
        fmt = fmt.upper()
        if fmt in ('GIF',):
            im = _convert2pilp(im)
        elif fmt in ('TIFF','TIFFP','TIFFL','TIF','TIFF1'):
            if fmt.endswith('P'):
                im = _convert2pilp(im)
            elif fmt.endswith('L'):
                im = _convert2pilL(im)
            elif fmt.endswith('1'):
                im = _convert2pil1(im)
            fmt='TIFF'
        elif fmt in ('PCT','PICT'):
            return _saveAsPICT(im,fn,fmt,transparent=configPIL.get('transparent',None))
        elif fmt in ('PNG','BMP', 'PPM'):
            pass
        elif fmt in ('JPG','JPEG'):
            fmt = 'JPEG'
        else:
            raise RenderPMError("Unknown image kind %s" % fmt)
        if fmt=='TIFF':
            tc = configPIL.get('transparent',None)
            if tc:
                from PIL import ImageChops, Image
                T = 768*[0]
                for o, c in zip((0,256,512), tc.bitmap_rgb()):
                    T[o+c] = 255
                #if isinstance(fn,str): ImageChops.invert(im.point(T).convert('L').point(255*[0]+[255])).save(fn+'_mask.gif','GIF')
                im = Image.merge('RGBA', im.split()+(ImageChops.invert(im.point(T).convert('L').point(255*[0]+[255])),))
                #if isinstance(fn,str): im.save(fn+'_masked.gif','GIF')
            for a,d in ('resolution',self._dpi),('resolution unit','inch'):
                configPIL[a] = configPIL.get(a,d)
        configPIL.setdefault('chops_invert',0)
        if configPIL.pop('chops_invert'):
            from PIL import ImageChops
            im = ImageChops.invert(im)
        configPIL.setdefault('preSaveCB',None)
        preSaveCB=configPIL.pop('preSaveCB')
        if preSaveCB:
            im = preSaveCB(im)
        im.save(fn,fmt,**configPIL)
        if not hasattr(fn,'write') and os.name=='mac':
            from reportlab.lib.utils import markfilename
            markfilename(fn,ext=fmt)

    def saveToString(self,fmt='GIF'):
        s = BytesIO()
        self.saveToFile(s,fmt=fmt)
        return s.getvalue()

    def _saveToBMP(self,f):
        '''
        Niki Spahiev, <niki@vintech.bg>, asserts that this is a respectable way to get BMP without PIL
        f is a file like object to which the BMP is written
        '''
        import struct
        gs = self._gs
        if self._backend=='rlPyCairo' and gs._fmt=='ARGB32':    #pixBuf would have 4 bytes
            gs._fmt = 'RGB24'   #force 3 bytes out until our BMP allows Alpha
            pix = gs.pixBuf
            gs._fmt = 'ARGB32'
        else:
            pix = gs.pixBuf
        width, height = gs.width, gs.height
        f.write(struct.pack('=2sLLLLLLhh24x','BM',len(pix)+54,0,54,40,width,height,1,24))
        rowb = width * 3
        for o in range(len(pix),0,-rowb):
            f.write(pix[o-rowb:o])
        f.write( '\0' * 14 )

    def setFont(self,fontName,fontSize,leading=None):
        _setFont(self._gs,fontName,fontSize)

    def __setattr__(self,name,value):
        setattr(self._gs,name,value)

    def __getattr__(self,name):
        return getattr(self._gs,name)

    def fillstrokepath(self,stroke=1,fill=1):
        if fill: self.pathFill()
        if stroke: self.pathStroke()

    def _bezierArcSegmentCCW(self, cx,cy, rx,ry, theta0, theta1):
        """compute the control points for a bezier arc with theta1-theta0 <= 90.
        Points are computed for an arc with angle theta increasing in the
        counter-clockwise (CCW) direction.  returns a tuple with starting point
        and 3 control points of a cubic bezier curve for the curvto opertator"""

        # Requires theta1 - theta0 <= 90 for a good approximation
        assert abs(theta1 - theta0) <= 90
        cos0 = cos(pi*theta0/180.0)
        sin0 = sin(pi*theta0/180.0)
        x0 = cx + rx*cos0
        y0 = cy + ry*sin0

        cos1 = cos(pi*theta1/180.0)
        sin1 = sin(pi*theta1/180.0)

        x3 = cx + rx*cos1
        y3 = cy + ry*sin1

        dx1 = -rx * sin0
        dy1 = ry * cos0

        #from pdfgeom
        halfAng = pi*(theta1-theta0)/(2.0 * 180.0)
        k = abs(4.0 / 3.0 * (1.0 - cos(halfAng) ) /(sin(halfAng)) )
        x1 = x0 + dx1 * k
        y1 = y0 + dy1 * k

        dx2 = -rx * sin1
        dy2 = ry * cos1

        x2 = x3 - dx2 * k
        y2 = y3 - dy2 * k
        return ((x0,y0), ((x1,y1), (x2,y2), (x3,y3)) )

    def bezierArcCCW(self, cx,cy, rx,ry, theta0, theta1):
        """return a set of control points for Bezier approximation to an arc
        with angle increasing counter clockwise. No requirement on (theta1-theta0) <= 90
        However, it must be true that theta1-theta0 > 0."""

        # I believe this is also clockwise
        # pretty much just like Robert Kern's pdfgeom.BezierArc
        angularExtent = theta1 - theta0
        # break down the arc into fragments of <=90 degrees
        if abs(angularExtent) <= 90.0:  # we just need one fragment
            angleList = [(theta0,theta1)]
        else:
            Nfrag = int( ceil( abs(angularExtent)/90.) )
            fragAngle = float(angularExtent)/ Nfrag  # this could be negative
            angleList = []
            for ii in range(Nfrag):
                a = theta0 + ii * fragAngle
                b = a + fragAngle # hmm.. is I wonder if this is precise enought
                angleList.append((a,b))

        ctrlpts = []
        for (a,b) in angleList:
            if not ctrlpts: # first time
                [(x0,y0), pts] = self._bezierArcSegmentCCW(cx,cy, rx,ry, a,b)
                ctrlpts.append(pts)
            else:
                [(tmpx,tmpy), pts] = self._bezierArcSegmentCCW(cx,cy, rx,ry, a,b)
                ctrlpts.append(pts)
        return ((x0,y0), ctrlpts)

    def addEllipsoidalArc(self, cx,cy, rx, ry, ang1, ang2):
        """adds an ellisesoidal arc segment to a path, with an ellipse centered
        on cx,cy and with radii (major & minor axes) rx and ry.  The arc is
        drawn in the CCW direction.  Requires: (ang2-ang1) > 0"""

        ((x0,y0), ctrlpts) = self.bezierArcCCW(cx,cy, rx,ry,ang1,ang2)

        self.lineTo(x0,y0)
        for ((x1,y1), (x2,y2),(x3,y3)) in ctrlpts:
            self.curveTo(x1,y1,x2,y2,x3,y3)

    def drawCentredString(self, x, y, text, text_anchor='middle'):
        self.drawString(x,y,text, text_anchor=text_anchor)

    def drawRightString(self, text, x, y):
        self.drawString(text,x,y,text_anchor='end')

    def drawString(self, x, y, text, _fontInfo=None, text_anchor='left'):
        gs = self._gs
        gs_fontSize = gs.fontSize
        gs_fontName = gs.fontName
        if _fontInfo and _fontInfo!=(gs_fontSize,gs_fontName):
            fontName, fontSize = _fontInfo
            _setFont(gs,fontName,fontSize)
        else:
            fontName = gs_fontName
            fontSize = gs_fontSize

        try:
            if text_anchor in ('end','middle', 'end'):
                textLen = stringWidth(text, fontName,fontSize)
                if text_anchor=='end':
                    x -= textLen
                elif text_anchor=='middle':
                    x -= textLen/2.
                elif text_anchor=='numeric':
                    x -= numericXShift(text_anchor,text,textLen,fontName,fontSize)

            if self._backend=='rlPyCairo':
                gs.drawString(x,y,text)
            else:
                font = getFont(fontName)
                if font._dynamicFont:
                    gs.drawString(x,y,text)
                else:
                    fc = font
                    if not isUnicode(text):
                        try:
                            text = text.decode('utf8')
                        except UnicodeDecodeError as e:
                            i,j = e.args[2:4]
                            raise UnicodeDecodeError(*(e.args[:4]+('%s\n%s-->%s<--%s' % (e.args[4],text[i-10:i],text[i:j],text[j:j+10]),)))

                    FT = unicode2T1(text,[font]+font.substitutionFonts)
                    n = len(FT)
                    nm1 = n-1
                    for i in range(n):
                        f, t = FT[i]
                        if f!=fc:
                            _setFont(gs,f.fontName,fontSize)
                            fc = f
                        gs.drawString(x,y,t)
                        if i!=nm1:
                            x += f.stringWidth(t.decode(f.encName),fontSize)
        finally:
            gs.setFont(gs_fontName,gs_fontSize)

    def line(self,x1,y1,x2,y2):
        if self.strokeColor is not None:
            self.pathBegin()
            self.moveTo(x1,y1)
            self.lineTo(x2,y2)
            self.pathStroke()

    def rect(self,x,y,width,height,stroke=1,fill=1):
        self.pathBegin()
        self.moveTo(x, y)
        self.lineTo(x+width, y)
        self.lineTo(x+width, y + height)
        self.lineTo(x, y + height)
        self.pathClose()
        self.fillstrokepath(stroke=stroke,fill=fill)

    def roundRect(self, x, y, width, height, rx,ry):
        """rect(self, x, y, width, height, rx,ry):
        Draw a rectangle if rx or rx and ry are specified the corners are
        rounded with ellipsoidal arcs determined by rx and ry
        (drawn in the counter-clockwise direction)"""
        if rx==0: rx = ry
        if ry==0: ry = rx
        x2 = x + width
        y2 = y + height
        self.pathBegin()
        self.moveTo(x+rx,y)
        self.addEllipsoidalArc(x2-rx, y+ry, rx, ry, 270, 360 )
        self.addEllipsoidalArc(x2-rx, y2-ry, rx, ry, 0, 90)
        self.addEllipsoidalArc(x+rx, y2-ry, rx, ry, 90, 180)
        self.addEllipsoidalArc(x+rx, y+ry, rx, ry, 180,  270)
        self.pathClose()
        self.fillstrokepath()

    def circle(self, cx, cy, r):
        "add closed path circle with center cx,cy and axes r: counter-clockwise orientation"
        self.ellipse(cx,cy,r,r)

    def ellipse(self, cx,cy,rx,ry):
        """add closed path ellipse with center cx,cy and axes rx,ry: counter-clockwise orientation
        (remember y-axis increases downward) """
        self.pathBegin()
        # first segment
        x0 = cx + rx   # (x0,y0) start pt
        y0 = cy

        x3 = cx        # (x3,y3) end pt of arc
        y3 = cy-ry

        x1 = cx+rx
        y1 = cy-ry*BEZIER_ARC_MAGIC

        x2 = x3 + rx*BEZIER_ARC_MAGIC
        y2 = y3
        self.moveTo(x0, y0)
        self.curveTo(x1,y1,x2,y2,x3,y3)
        # next segment
        x0 = x3
        y0 = y3

        x3 = cx-rx
        y3 = cy

        x1 = cx-rx*BEZIER_ARC_MAGIC
        y1 = cy-ry

        x2 = x3
        y2 = cy- ry*BEZIER_ARC_MAGIC
        self.curveTo(x1,y1,x2,y2,x3,y3)
        # next segment
        x0 = x3
        y0 = y3

        x3 = cx
        y3 = cy+ry

        x1 = cx-rx
        y1 = cy+ry*BEZIER_ARC_MAGIC

        x2 = cx -rx*BEZIER_ARC_MAGIC
        y2 = cy+ry
        self.curveTo(x1,y1,x2,y2,x3,y3)
        #last segment
        x0 = x3
        y0 = y3

        x3 = cx+rx
        y3 = cy

        x1 = cx+rx*BEZIER_ARC_MAGIC
        y1 = cy+ry

        x2 = cx+rx
        y2 = cy+ry*BEZIER_ARC_MAGIC
        self.curveTo(x1,y1,x2,y2,x3,y3)
        self.pathClose()

    def saveState(self):
        '''do nothing for compatibility'''
        pass

    def setFillColor(self,aColor):
        self.fillColor = self._colorConverter(aColor)
        alpha = getattr(aColor,'alpha',None)
        if alpha is not None:
            self.fillOpacity = alpha

    def setStrokeColor(self,aColor):
        self.strokeColor = self._colorConverter(aColor)
        alpha = getattr(aColor,'alpha',None)
        if alpha is not None:
            self.strokeOpacity = alpha

    restoreState = saveState

    # compatibility routines
    def setLineCap(self,cap):
        self.lineCap = cap

    def setLineJoin(self,join):
        self.lineJoin = join

    def setLineWidth(self,width):
        self.strokeWidth = width

def drawToPMCanvas(d, dpi=72, bg=0xffffff, configPIL=None, showBoundary=rl_config._unset_,backend=rl_config.renderPMBackend,backendFmt='RGB'):
    d = renderScaledDrawing(d)
    c = PMCanvas(d.width, d.height, dpi=dpi, bg=bg, configPIL=configPIL, backend=backend,backendFmt=backendFmt)
    draw(d, c, 0, 0, showBoundary=showBoundary)
    return c

def drawToPIL(d, dpi=72, bg=0xffffff, configPIL=None, showBoundary=rl_config._unset_,backend=rl_config.renderPMBackend,backendFmt='RGB'):
    return drawToPMCanvas(d, dpi=dpi, bg=bg, configPIL=configPIL, showBoundary=showBoundary, backend=backend,backendFmt=backendFmt).toPIL()

def drawToPILP(d, dpi=72, bg=0xffffff, configPIL=None, showBoundary=rl_config._unset_,backend=rl_config.renderPMBackend,backendFmt='RGB'):
    Image = _getImage()
    im = drawToPIL(d, dpi=dpi, bg=bg, configPIL=configPIL, showBoundary=showBoundary,backend=backend,backendFmt=backendFmt)
    return im.convert("P", dither=Image.NONE, palette=Image.ADAPTIVE)

def drawToFile(d,fn,fmt='GIF', dpi=72, bg=0xffffff, configPIL=None, showBoundary=rl_config._unset_,backend=rl_config.renderPMBackend,backendFmt='RGB'):
    '''create a pixmap and draw drawing, d to it then save as a file
    configPIL dict is passed to image save method'''
    c = drawToPMCanvas(d, dpi=dpi, bg=bg, configPIL=configPIL, showBoundary=showBoundary,backend=backend,backendFmt=backendFmt)
    c.saveToFile(fn,fmt)

def drawToString(d,fmt='GIF', dpi=72, bg=0xffffff, configPIL=None, showBoundary=rl_config._unset_,backend=rl_config.renderPMBackend,backendFmt='RGB'):
    s = BytesIO()
    drawToFile(d,s,fmt=fmt, dpi=dpi, bg=bg, configPIL=configPIL,backend=backend,backendFmt=backendFmt)
    return s.getvalue()

save = drawToFile

def test(outDir='pmout', shout=False):
    def ext(x):
        if x=='tiff': x='tif'
        return x
    #grab all drawings from the test module and write out.
    #make a page of links in HTML to assist viewing.
    import os
    from reportlab.graphics import testshapes
    from reportlab.rl_config import verbose
    getAllTestDrawings = testshapes.getAllTestDrawings
    drawings = []
    if not os.path.isdir(outDir):
        os.mkdir(outDir)
    htmlTop = """<html><head><title>renderPM output results</title></head>
    <body>
    <h1>renderPM results of output</h1>
    """
    htmlBottom = """</body>
    </html>
    """
    html = [htmlTop]
    names = {}
    argv = sys.argv[1:]
    E = [a for a in argv if a.startswith('--ext=')]
    if not E:
        E = ['gif','tiff', 'png', 'jpg', 'pct', 'py', 'svg']
    else:
        for a in E:
            argv.remove(a)
        E = (','.join([a[6:] for a in E])).split(',')

    errs = []
    import traceback
    from xml.sax.saxutils import escape
    def handleError(name,fmt):
        msg = 'Problem drawing %s fmt=%s file'%(name,fmt)
        if shout or verbose>2: print(msg)
        errs.append('<br/><h2 style="color:red">%s</h2>' % msg)
        buf = StringIO()
        traceback.print_exc(file=buf)
        errs.append('<pre>%s</pre>' % escape(buf.getvalue()))

    #print in a loop, with their doc strings
    for (drawing, docstring, name) in getAllTestDrawings(doTTF=hasattr(_pmBackend,'ft_get_face')):
        i = names[name] = names.setdefault(name,0)+1
        if i>1: name += '.%02d' % (i-1)
        if argv and name not in argv: continue
        fnRoot = name
        w = int(drawing.width)
        h = int(drawing.height)
        html.append('<hr><h2>Drawing %s</h2>\n<pre>%s</pre>' % (name, docstring))

        for k in E:
            if k in ['gif','png','jpg','pct']:
                html.append('<p>%s format</p>\n' % k.upper())
            try:
                filename = '%s.%s' % (fnRoot, ext(k))
                fullpath = os.path.join(outDir, filename)
                if os.path.isfile(fullpath):
                    os.remove(fullpath)
                if k=='pct':
                    drawToFile(drawing,fullpath,fmt=k,configPIL={'transparent':white})
                elif k in ['py','svg']:
                    drawing.save(formats=['py','svg'],outDir=outDir,fnRoot=fnRoot)
                else:
                    drawToFile(drawing,fullpath,fmt=k)
                if k in ['gif','png','jpg']:
                    html.append('<img src="%s" border="1"><br>\n' % filename)
                elif k=='py':
                    html.append('<a href="%s">python source</a><br>\n' % filename)
                elif k=='svg':
                    html.append('<a href="%s">SVG</a><br>\n' % filename)
                if shout or verbose>2: print('wrote %s'%ascii(fullpath))
            except AttributeError:
                handleError(name,k)
        if os.environ.get('RL_NOEPSPREVIEW','0')=='1': drawing.__dict__['preview'] = 0
        for k in ('eps', 'pdf'):
            try:
                drawing.save(formats=[k],outDir=outDir,fnRoot=fnRoot)
            except:
                handleError(name,k)

    if errs:
        html[0] = html[0].replace('</h1>',' <a href="#errors" style="color: red">(errors)</a></h1>')
        html.append('<a name="errors"/>')
        html.extend(errs)
    html.append(htmlBottom)
    htmlFileName = os.path.join(outDir, 'pm-index.html')
    with open(htmlFileName, 'w') as f:
        f.writelines(html)
    if sys.platform=='mac':
        from reportlab.lib.utils import markfilename
        markfilename(htmlFileName,ext='HTML')
    if shout or verbose>2: print('wrote %s' % htmlFileName)

if __name__=='__main__':
    test(shout=True)
