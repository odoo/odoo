#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/graphics/renderPDF.py
# renderPDF - draws Drawings onto a canvas
"""Usage:
    import renderpdf
    renderpdf.draw(drawing, canvas, x, y)
Execute the script to see some test drawings.
changed
"""
__version__=''' $Id$ '''

from reportlab.graphics.shapes import *
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.utils import getStringIO
from reportlab import rl_config

# the main entry point for users...
def draw(drawing, canvas, x, y, showBoundary=rl_config._unset_):
    """As it says"""
    R = _PDFRenderer()
    R.draw(drawing, canvas, x, y, showBoundary=showBoundary)

from renderbase import Renderer, StateTracker, getStateDelta

class _PDFRenderer(Renderer):
    """This draws onto a PDF document.  It needs to be a class
    rather than a function, as some PDF-specific state tracking is
    needed outside of the state info in the SVG model."""

    def __init__(self):
        self._stroke = 0
        self._fill = 0
        self._tracker = StateTracker()

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
        # currently not implemented in other renderers
        if image.path and os.path.exists(image.path):
            self._canvas.drawInlineImage(
                    image.path,
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
                    stroke=self._stroke
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
                    stroke=self._stroke)

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
                            fill=self._fill
                            )

    def drawString(self, stringObj):
        if self._fill:
            S = self._tracker.getState()
            text_anchor, x, y, text = S['textAnchor'], stringObj.x,stringObj.y,stringObj.text
            if not text_anchor in ['start','inherited']:
                font, font_size = S['fontName'], S['fontSize']
                textLen = stringWidth(text, font,font_size)
                if text_anchor=='end':
                    x = x-textLen
                elif text_anchor=='middle':
                    x = x - textLen/2
                else:
                    raise ValueError, 'bad value for textAnchor '+str(text_anchor)
            t = self._canvas.beginText(x,y)
            t.textLine(text)
            self._canvas.drawText(t)

    def drawPath(self, path):
        from reportlab.graphics.shapes import _renderPath
        pdfPath = self._canvas.beginPath()
        drawFuncs = (pdfPath.moveTo, pdfPath.lineTo, pdfPath.curveTo, pdfPath.close)
        isClosed = _renderPath(path, drawFuncs)
        if isClosed:
            fill = self._fill
        else:
            fill = 0
        if path.isClipPath:
            self._canvas.clipPath(pdfPath, fill=fill, stroke=self._stroke)
        else:
            self._canvas.drawPath(pdfPath,
                        fill=fill,
                        stroke=self._stroke)

    def applyStateChanges(self, delta, newState):
        """This takes a set of states, and outputs the PDF operators
        needed to set those properties"""
        for key, value in delta.items():
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
                    self._canvas.setStrokeColor(value)
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
                    self._canvas.setDash(value)
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
                    self._canvas.setFillColor(value)
            elif key in ['fontSize', 'fontName']:
                # both need setting together in PDF
                # one or both might be in the deltas,
                # so need to get whichever is missing
                fontname = delta.get('fontName', self._canvas._fontname)
                fontsize = delta.get('fontSize', self._canvas._fontsize)
                self._canvas.setFont(fontname, fontsize)

from reportlab.platypus import Flowable

class GraphicsFlowable(Flowable):
    """Flowable wrapper around a Pingo drawing"""
    def __init__(self, drawing):
        self.drawing = drawing
        self.width = self.drawing.width
        self.height = self.drawing.height

    def draw(self):
        draw(self.drawing, self.canv, 0, 0)

def drawToFile(d, fn, msg="", showBoundary=rl_config._unset_, autoSize=1):
    """Makes a one-page PDF with just the drawing.

    If autoSize=1, the PDF will be the same size as
    the drawing; if 0, it will place the drawing on
    an A4 page with a title above it - possibly overflowing
    if too big."""
    c = Canvas(fn)
    c.setFont('Times-Roman', 36)
    c.drawString(80, 750, msg)
    c.setTitle(msg)

    if autoSize:
        c.setPageSize((d.width, d.height))
        draw(d, c, 0, 0, showBoundary=showBoundary)
    else:
    #show with a title
        c.setFont('Times-Roman', 12)
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


def drawToString(d, msg="", showBoundary=rl_config._unset_,autoSize=1):
    "Returns a PDF as a string in memory, without touching the disk"
    s = getStringIO()
    drawToFile(d, s, msg=msg, showBoundary=showBoundary,autoSize=autoSize)
    return s.getvalue()


#########################################################
#
#   test code.  First, defin a bunch of drawings.
#   Routine to draw them comes at the end.
#
#########################################################


def test():
    c = Canvas('renderPDF.pdf')
    c.setFont('Times-Roman', 36)
    c.drawString(80, 750, 'Graphics Test')

    # print all drawings and their doc strings from the test
    # file

    #grab all drawings from the test module
    from reportlab.graphics import testshapes
    drawings = []
    for funcname in dir(testshapes):
        if funcname[0:10] == 'getDrawing':
            drawing = eval('testshapes.' + funcname + '()')  #execute it
            docstring = eval('testshapes.' + funcname + '.__doc__')
            drawings.append((drawing, docstring))

    #print in a loop, with their doc strings
    c.setFont('Times-Roman', 12)
    y = 740
    i = 1
    for (drawing, docstring) in drawings:
        assert (docstring is not None), "Drawing %d has no docstring!" % i
        if y < 300:  #allows 5-6 lines of text
            c.showPage()
            y = 740
        # draw a title
        y = y - 30
        c.setFont('Times-BoldItalic',12)
        c.drawString(80, y, 'Drawing %d' % i)
        c.setFont('Times-Roman',12)
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
    print 'saved renderPDF.pdf'

##def testFlowable():
##    """Makes a platypus document"""
##    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
##    from reportlab.lib.styles import getSampleStyleSheet
##    styles = getSampleStyleSheet()
##    styNormal = styles['Normal']
##
##    doc = SimpleDocTemplate('test_flowable.pdf')
##    story = []
##    story.append(Paragraph("This sees is a drawing can work as a flowable", styNormal))
##
##    import testdrawings
##    drawings = []
##
##    for funcname in dir(testdrawings):
##        if funcname[0:10] == 'getDrawing':
##            drawing = eval('testdrawings.' + funcname + '()')  #execute it
##            docstring = eval('testdrawings.' + funcname + '.__doc__')
##            story.append(Paragraph(docstring, styNormal))
##            story.append(Spacer(18,18))
##            story.append(drawing)
##            story.append(Spacer(36,36))
##
##    doc.build(story)
##    print 'saves test_flowable.pdf'

if __name__=='__main__':
    test()
    #testFlowable()
