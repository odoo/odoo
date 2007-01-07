#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/pdfgen/pathobject.py
__version__=''' $Id: pathobject.py 2537 2005-03-15 14:19:29Z rgbecker $ '''
__doc__="""
PDFPathObject is an efficient way to draw paths on a Canvas. Do not
instantiate directly, obtain one from the Canvas instead.

Progress Reports:
8.83, 2000-01-13, gmcm:
    created from pdfgen.py
"""

import string
from reportlab.pdfgen import pdfgeom
from reportlab.lib.utils import fp_str


class PDFPathObject:
    """Represents a graphic path.  There are certain 'modes' to PDF
    drawing, and making a separate object to expose Path operations
    ensures they are completed with no run-time overhead.  Ask
    the Canvas for a PDFPath with getNewPathObject(); moveto/lineto/
    curveto wherever you want; add whole shapes; and then add it back
    into the canvas with one of the relevant operators.

    Path objects are probably not long, so we pack onto one line"""

    def __init__(self):
        self._code = []
        #self._code.append('n')  #newpath
        self._code_append = self._init_code_append

    def _init_code_append(self,c):
        assert c.endswith(' m') or c.endswith(' re'), 'path must start with a moveto or rect'
        code_append = self._code.append
        code_append('n')
        code_append(c)
        self._code_append = code_append

    def getCode(self):
        "pack onto one line; used internally"
        return string.join(self._code, ' ')

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

        pointList = pdfgeom.bezierArc(x1,y1, x2,y2, startAng, extent)
        #move to first point
        self._code_append('%s m' % fp_str(pointList[0][:2]))
        for curve in pointList:
            self._code_append('%s c' % fp_str(curve[2:]))

    def arcTo(self, x1,y1, x2,y2, startAng=0, extent=90):
        """Like arc, but draws a line from the current point to
        the start if the start is not the current point."""
        pointList = pdfgeom.bezierArc(x1,y1, x2,y2, startAng, extent)
        self._code_append('%s l' % fp_str(pointList[0][:2]))
        for curve in pointList:
            self._code_append('%s c' % fp_str(curve[2:]))

    def rect(self, x, y, width, height):
        """Adds a rectangle to the path"""
        self._code_append('%s re' % fp_str((x, y, width, height)))

    def ellipse(self, x, y, width, height):
        """adds an ellipse to the path"""
        pointList = pdfgeom.bezierArc(x, y, x + width,y + height, 0, 360)
        self._code_append('%s m' % fp_str(pointList[0][:2]))
        for curve in pointList:
            self._code_append('%s c' % fp_str(curve[2:]))

    def circle(self, x_cen, y_cen, r):
        """adds a circle to the path"""
        x1 = x_cen - r
        #x2 = x_cen + r
        y1 = y_cen - r
        #y2 = y_cen + r
        width = height = 2*r
        #self.ellipse(x_cen - r, y_cen - r, x_cen + r, y_cen + r)
        self.ellipse(x1, y1, width, height)

    def close(self):
        "draws a line back to where it started"
        self._code_append('h')
