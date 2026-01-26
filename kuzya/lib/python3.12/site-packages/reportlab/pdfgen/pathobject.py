#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/pdfgen/pathobject.py
__version__='3.3.0'
__doc__="""
PDFPathObject is an efficient way to draw paths on a Canvas. Do not
instantiate directly, obtain one from the Canvas instead.

Progress Reports:
8.83, 2000-01-13, gmcm: created from pdfgen.py

"""

from reportlab.pdfgen import pdfgeom
from reportlab.lib.rl_accel import fp_str


class PDFPathObject:
    """Represents a graphic path.  There are certain 'modes' to PDF
    drawing, and making a separate object to expose Path operations
    ensures they are completed with no run-time overhead.  Ask
    the Canvas for a PDFPath with getNewPathObject(); moveto/lineto/
    curveto wherever you want; add whole shapes; and then add it back
    into the canvas with one of the relevant operators.

    Path objects are probably not long, so we pack onto one line

    the code argument allows a canvas to get the operations appended directly so
    avoiding the final getCode
    """
    def __init__(self,code=None):
        self._code = (code,[])[code is None]
        self._code_append = self._init_code_append

    def _init_code_append(self,c):
        assert c.endswith(' m') or c.endswith(' re'), 'path must start with a moveto or rect'
        code_append = self._code.append
        code_append('n')
        code_append(c)
        self._code_append = code_append

    def getCode(self):
        "pack onto one line; used internally"
        return ' '.join(self._code)

    def moveTo(self, x, y):
        self._code_append('%s m' % fp_str(x,y))

    def lineTo(self, x, y):
        self._code_append('%s l' % fp_str(x,y))

    def curveTo(self, x1, y1, x2, y2, x3, y3):
        self._code_append('%s c' % fp_str(x1, y1, x2, y2, x3, y3))

    def arc(self, x1,y1, x2,y2, startAng=0, extent=90):
        """Contributed to piddlePDF by Robert Kern, 28/7/99.
        Draw a partial ellipse inscribed within the rectangle x1,y1,x2,y2,
        starting at startAng degrees and covering extent degrees.   Angles
        start with 0 to the right (+x) and increase counter-clockwise.
        These should have x1<x2 and y1<y2.

        The algorithm is an elliptical generalization of the formulae in
        Jim Fitzsimmon's TeX tutorial <URL: http://www.tinaja.com/bezarc1.pdf>."""

        self._curves(pdfgeom.bezierArc(x1,y1, x2,y2, startAng, extent))

    def arcTo(self, x1,y1, x2,y2, startAng=0, extent=90):
        """Like arc, but draws a line from the current point to
        the start if the start is not the current point."""
        self._curves(pdfgeom.bezierArc(x1,y1, x2,y2, startAng, extent),'lineTo')

    def rect(self, x, y, width, height):
        """Adds a rectangle to the path"""
        self._code_append('%s re' % fp_str((x, y, width, height)))

    def ellipse(self, x, y, width, height):
        """adds an ellipse to the path"""
        self._curves(pdfgeom.bezierArc(x, y, x + width,y + height, 0, 360))

    def _curves(self,curves,initial='moveTo'):
        getattr(self,initial)(*curves[0][:2])
        for curve in curves:
            self.curveTo(*curve[2:])

    def circle(self, x_cen, y_cen, r):
        """adds a circle to the path"""
        x1 = x_cen - r
        y1 = y_cen - r
        width = height = 2*r
        self.ellipse(x1, y1, width, height)

    def roundRect(self, x, y, width, height, radius):
        """Draws a rectangle with rounded corners. The corners are
        approximately quadrants of a circle, with the given radius."""
        #use a precomputed set of factors for the bezier approximation
        #to a circle. There are six relevant points on the x axis and y axis.
        #sketch them and it should all make sense!
        m = 0.4472  #radius multiplier
        xhi = x,x+width
        xlo, xhi = min(xhi), max(xhi)
        yhi = y,y+height
        ylo, yhi = min(yhi), max(yhi)
        if isinstance(radius,(list,tuple)):
            r = [max(0,r) for r in radius]
            if len(r)<4: r += (4-len(r))*[0]
            self.moveTo(xlo + r[2], ylo)    #start at bottom left
            self.lineTo(xhi - r[3], ylo)    #bottom row
            if r[3]>0:
                t = m*r[3]
                self.curveTo(xhi - t, ylo, xhi, ylo + t, xhi, ylo + r[3]) #bottom right
            self.lineTo(xhi, yhi - r[1]) #right edge
            if r[1]>0:
                t = m*r[1]
                self.curveTo(xhi, yhi - t, xhi - t, yhi, xhi - r[1], yhi) #top right
            self.lineTo(xlo + r[0], yhi) #top row
            if r[0]>0:
                t = m*r[0]
                self.curveTo(xlo + t, yhi, xlo, yhi - t, xlo, yhi - r[0]) #top left
            self.lineTo(xlo, ylo + r[2]) #left edge
            if r[2]>0:
                t = m*r[2]
                self.curveTo(xlo, ylo + t, xlo + t, ylo, xlo + r[2], ylo) #bottom left
            # 4 radii top left top right bittom left bottom right
        else:
            t = m * radius
            self.moveTo(xlo + radius, ylo)
            self.lineTo(xhi - radius, ylo) #bottom row
            self.curveTo(xhi - t, ylo, xhi, ylo + t, xhi, ylo + radius) #bottom right
            self.lineTo(xhi, yhi - radius) #right edge
            self.curveTo(xhi, yhi - t, xhi - t, yhi, xhi - radius, yhi) #top right
            self.lineTo(xlo + radius, yhi) #top row
            self.curveTo(xlo + t, yhi, xlo, yhi - t, xlo, yhi - radius) #top left
            self.lineTo(xlo, ylo + radius) #left edge
            self.curveTo(xlo, ylo + t, xlo + t, ylo, xlo + radius, ylo) #bottom left
        self.close()

    def close(self):
        "draws a line back to where it started"
        self._code_append('h')
