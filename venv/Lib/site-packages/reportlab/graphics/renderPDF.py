#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/graphics/renderPDF.py
# renderPDF - draws Drawings onto a canvas

__version__='3.3.0'
__doc__="""Render Drawing objects within others PDFs or standalone

Usage::
    
    import renderpdf
    renderpdf.draw(drawing, canvas, x, y)

Execute the script to see some test drawings.
changed
"""

from io import BytesIO

from reportlab.graphics.shapes import *
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab import rl_config
from reportlab.graphics.renderbase import Renderer, getStateDelta, renderScaledDrawing, STATE_DEFAULTS

# the main entry point for users...
def draw(drawing, canvas, x, y, showBoundary=rl_config._unset_):
    """As it says"""
    R = _PDFRenderer()
    R.draw(renderScaledDrawing(drawing), canvas, x, y, showBoundary=showBoundary)

class _PDFRenderer(Renderer):
    """This draws onto a PDF document.  It needs to be a class
    rather than a function, as some PDF-specific state tracking is
    needed outside of the state info in the SVG model."""

    def __init__(self):
        self._stroke = 0
        self._fill = 0

    def drawNode(self, node):
        """This is the recursive method called for each node
        in the tree"""
        #print "pdf:drawNode", self
        #if node.__class__ is Wedge: stop
        if not (isinstance(node, Path) and node.isClipPath):
            self._canvas.saveState()

        #apply state changes
        deltas = getStateDelta(node)
        self._tracker.push(deltas)
        self.applyStateChanges(deltas, {})

        #draw the object, or recurse
        self.drawNodeDispatcher(node)

        self._tracker.pop()
        if not (isinstance(node, Path) and node.isClipPath):
            self._canvas.restoreState()

    def drawRect(self, rect):
        if rect.rx == rect.ry == 0:
            #plain old rectangle
            self._canvas.rect(
                    rect.x, rect.y,
                    rect.width, rect.height,
                    stroke=self._stroke,
                    fill=self._fill
                    )
        else:
            #cheat and assume ry = rx; better to generalize
            #pdfgen roundRect function.  TODO
            self._canvas.roundRect(
                    rect.x, rect.y,
                    rect.width, rect.height, rect.rx,
                    fill=self._fill,
                    stroke=self._stroke
                    )

    def drawImage(self, image):
        path = image.path
        # currently not implemented in other renderers
        if path and (hasattr(path,'mode') or os.path.exists(image.path)):
            self._canvas.drawInlineImage(
                    path,
                    image.x, image.y,
                    image.width, image.height
                    )

    def drawLine(self, line):
        if self._stroke:
            self._canvas.line(line.x1, line.y1, line.x2, line.y2)

    def drawCircle(self, circle):
            self._canvas.circle(
                    circle.cx, circle.cy, circle.r,
                    fill=self._fill,
                    stroke=self._stroke,
                    )

    def drawPolyLine(self, polyline):
        if self._stroke:
            assert len(polyline.points) >= 2, 'Polyline must have 2 or more points'
            head, tail = polyline.points[0:2], polyline.points[2:],
            path = self._canvas.beginPath()
            path.moveTo(head[0], head[1])
            for i in range(0, len(tail), 2):
                path.lineTo(tail[i], tail[i+1])
            self._canvas.drawPath(path)

    def drawWedge(self, wedge):
        if wedge.annular:
            self.drawPath(wedge.asPolygon())
        else:
            centerx, centery, radius, startangledegrees, endangledegrees = \
             wedge.centerx, wedge.centery, wedge.radius, wedge.startangledegrees, wedge.endangledegrees
            yradius, radius1, yradius1 = wedge._xtraRadii()
            if yradius is None: yradius = radius
            angle = endangledegrees-startangledegrees
            path = self._canvas.beginPath()
            if (radius1==0 or radius1 is None) and (yradius1==0 or yradius1 is None):
                path.moveTo(centerx, centery)
                path.arcTo(centerx-radius, centery-yradius, centerx+radius, centery+yradius,
                       startangledegrees, angle)
            else:
                path.arc(centerx-radius, centery-yradius, centerx+radius, centery+yradius,
                       startangledegrees, angle)
                path.arcTo(centerx-radius1, centery-yradius1, centerx+radius1, centery+yradius1,
                       endangledegrees, -angle)
            path.close()
            self._canvas.drawPath(path,
                        fill=self._fill,
                        stroke=self._stroke,
                        )

    def drawEllipse(self, ellipse):
        #need to convert to pdfgen's bounding box representation
        x1 = ellipse.cx - ellipse.rx
        x2 = ellipse.cx + ellipse.rx
        y1 = ellipse.cy - ellipse.ry
        y2 = ellipse.cy + ellipse.ry
        self._canvas.ellipse(x1,y1,x2,y2,fill=self._fill,stroke=self._stroke)

    def drawPolygon(self, polygon):
        assert len(polygon.points) >= 2, 'Polyline must have 2 or more points'
        head, tail = polygon.points[0:2], polygon.points[2:],
        path = self._canvas.beginPath()
        path.moveTo(head[0], head[1])
        for i in range(0, len(tail), 2):
            path.lineTo(tail[i], tail[i+1])
        path.close()
        self._canvas.drawPath(
                            path,
                            stroke=self._stroke,
                            fill=self._fill,
                            )

    def drawString(self, stringObj):
        textRenderMode = getattr(stringObj,'textRenderMode',0)
        needFill = textRenderMode in (0,2,4,6) 
        needStroke = textRenderMode in (1,2,5,6) 

        if (self._fill and needFill) or (self._stroke and needStroke):
            S = self._tracker.getState()
            text_anchor, x, y, text, enc = S['textAnchor'], stringObj.x,stringObj.y,stringObj.text, stringObj.encoding
            if not text_anchor in ['start','inherited']:
                font, font_size = S['fontName'], S['fontSize']
                textLen = stringWidth(text, font, font_size, enc)
                if text_anchor=='end':
                    x -= textLen
                elif text_anchor=='middle':
                    x -= textLen*0.5
                elif text_anchor=='numeric':
                    x -= numericXShift(text_anchor,text,textLen,font,font_size,enc)
                else:
                    raise ValueError('bad value for textAnchor '+str(text_anchor))
            self._canvas.drawString(x, y, text, mode=textRenderMode or None)

    def drawPath(self, path):
        from reportlab.graphics.shapes import _renderPath
        pdfPath = self._canvas.beginPath()
        drawFuncs = (pdfPath.moveTo, pdfPath.lineTo, pdfPath.curveTo, pdfPath.close)
        autoclose = getattr(path,'autoclose','')
        fill = self._fill
        stroke = self._stroke
        isClosed = _renderPath(path, drawFuncs, forceClose=fill and autoclose=='pdf')
        dP = self._canvas.drawPath
        cP = self._canvas.clipPath if path.isClipPath else dP
        fillMode = getattr(path,'fillMode',None)
        if autoclose=='svg':
            if fill and stroke and not isClosed:
                cP(pdfPath, fill=fill, stroke=0)
                dP(pdfPath, stroke=stroke, fill=0, fillMode=fillMode)
            else:
                cP(pdfPath, fill=fill, stroke=stroke, fillMode=fillMode)
        elif autoclose=='pdf':
            cP(pdfPath, fill=fill, stroke=stroke, fillMode=fillMode)
        else:
            #our old broken default
            if not isClosed:
                fill = 0
            cP(pdfPath, fill=fill, stroke=stroke, fillMode=fillMode)

    def setStrokeColor(self,c):
        self._canvas.setStrokeColor(c)

    def setFillColor(self,c):
        self._canvas.setFillColor(c)

    def applyStateChanges(self, delta, newState):
        """This takes a set of states, and outputs the PDF operators
        needed to set those properties"""
        for key, value in (sorted(delta.items()) if rl_config.invariant else delta.items()):
            if key == 'transform':
                self._canvas.transform(value[0], value[1], value[2],
                                 value[3], value[4], value[5])
            elif key == 'strokeColor':
                #this has different semantics in PDF to SVG;
                #we always have a color, and either do or do
                #not apply it; in SVG one can have a 'None' color
                if value is None:
                    self._stroke = 0
                else:
                    self._stroke = 1
                    self.setStrokeColor(value)
            elif key == 'strokeWidth':
                self._canvas.setLineWidth(value)
            elif key == 'strokeLineCap':  #0,1,2
                self._canvas.setLineCap(value)
            elif key == 'strokeLineJoin':
                self._canvas.setLineJoin(value)
#            elif key == 'stroke_dasharray':
#                self._canvas.setDash(array=value)
            elif key == 'strokeDashArray':
                if value:
                    if isinstance(value,(list,tuple)) and len(value)==2 and isinstance(value[1],(tuple,list)):
                        phase = value[0]
                        value = value[1]
                    else:
                        phase = 0
                    self._canvas.setDash(value,phase)
                else:
                    self._canvas.setDash()
            elif key == 'fillColor':
                #this has different semantics in PDF to SVG;
                #we always have a color, and either do or do
                #not apply it; in SVG one can have a 'None' color
                if value is None:
                    self._fill = 0
                else:
                    self._fill = 1
                    self.setFillColor(value)
            elif key in ['fontSize', 'fontName']:
                # both need setting together in PDF
                # one or both might be in the deltas,
                # so need to get whichever is missing
                fontname = delta.get('fontName', self._canvas._fontname)
                fontsize = delta.get('fontSize', self._canvas._fontsize)
                self._canvas.setFont(fontname, fontsize)
            elif key=='fillOpacity':
                if value is not None:
                    self._canvas.setFillAlpha(value)
            elif key=='strokeOpacity':
                if value is not None:
                    self._canvas.setStrokeAlpha(value)
            elif key=='fillOverprint':
                self._canvas.setFillOverprint(value)
            elif key=='strokeOverprint':
                self._canvas.setStrokeOverprint(value)
            elif key=='overprintMask':
                self._canvas.setOverprintMask(value)
            elif key=='fillMode':
                self._canvas._fillMode = value

from reportlab.platypus import Flowable
class GraphicsFlowable(Flowable):
    """Flowable wrapper around a Pingo drawing"""
    def __init__(self, drawing):
        self.drawing = drawing
        self.width = self.drawing.width
        self.height = self.drawing.height

    def draw(self):
        draw(self.drawing, self.canv, 0, 0)

def drawToFile(d, fn, msg="", showBoundary=rl_config._unset_, autoSize=1, canvasKwds={}):
    """Makes a one-page PDF with just the drawing.

    If autoSize=1, the PDF will be the same size as
    the drawing; if 0, it will place the drawing on
    an A4 page with a title above it - possibly overflowing
    if too big."""
    d = renderScaledDrawing(d)
    for x in ('Name','Size'):
        a = 'initialFont'+x
        canvasKwds[a] = getattr(d,a,canvasKwds.pop(a,STATE_DEFAULTS['font'+x]))
    c = Canvas(fn,**canvasKwds)
    if msg:
        c.setFont(rl_config.defaultGraphicsFontName, 36)
        c.drawString(80, 750, msg)
    c.setTitle(msg)

    if autoSize:
        c.setPageSize((d.width, d.height))
        draw(d, c, 0, 0, showBoundary=showBoundary)
    else:
        #show with a title
        c.setFont(rl_config.defaultGraphicsFontName, 12)
        y = 740
        i = 1
        y = y - d.height
        draw(d, c, 80, y, showBoundary=showBoundary)

    c.showPage()
    c.save()
    if sys.platform=='mac' and not hasattr(fn, "write"):
        try:
            import macfs, macostools
            macfs.FSSpec(fn).SetCreatorType("CARO", "PDF ")
            macostools.touched(fn)
        except:
            pass

def drawToString(d, msg="", showBoundary=rl_config._unset_,autoSize=1,canvasKwds={}):
    "Returns a PDF as a string in memory, without touching the disk"
    s = BytesIO()
    drawToFile(d, s, msg=msg, showBoundary=showBoundary,autoSize=autoSize, canvasKwds=canvasKwds)
    return s.getvalue()

#########################################################
#
#   test code.  First, define a bunch of drawings.
#   Routine to draw them comes at the end.
#
#########################################################
def test(outDir='pdfout',shout=False):
    from reportlab.graphics.shapes import _baseGFontName, _baseGFontNameBI
    from reportlab.rl_config import verbose
    import os
    if not os.path.isdir(outDir):
        os.mkdir(outDir)
    fn = os.path.join(outDir,'renderPDF.pdf')
    c = Canvas(fn)
    c.setFont(_baseGFontName, 36)
    c.drawString(80, 750, 'Graphics Test')

    # print all drawings and their doc strings from the test
    # file

    #grab all drawings from the test module
    from reportlab.graphics import testshapes
    drawings = []
    for funcname in dir(testshapes):
        if funcname[0:10] == 'getDrawing':
            func = getattr(testshapes,funcname)
            drawing = func()  #execute it
            docstring = getattr(func,'__doc__','')
            drawings.append((drawing, docstring))

    #print in a loop, with their doc strings
    c.setFont(_baseGFontName, 12)
    y = 740
    i = 1
    for (drawing, docstring) in drawings:
        assert (docstring is not None), "Drawing %d has no docstring!" % i
        if y < 300:  #allows 5-6 lines of text
            c.showPage()
            y = 740
        # draw a title
        y = y - 30
        c.setFont(_baseGFontNameBI,12)
        c.drawString(80, y, 'Drawing %d' % i)
        c.setFont(_baseGFontName,12)
        y = y - 14
        textObj = c.beginText(80, y)
        textObj.textLines(docstring)
        c.drawText(textObj)
        y = textObj.getY()
        y = y - drawing.height
        draw(drawing, c, 80, y)
        i = i + 1
    if y!=740: c.showPage()

    c.save()
    if shout or verbose>2:
        print('saved %s' % ascii(fn))

if __name__=='__main__':
    test(shout=True)
    import sys
    if len(sys.argv)>1:
        outdir = sys.argv[1]
    else:
        outdir = 'pdfout'
    test(outdir,shout=True)
    #testFlowable()
