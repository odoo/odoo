#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/pdfgen/pdfgeom.py
__version__=''' $Id: pdfgeom.py 2385 2004-06-17 15:26:05Z rgbecker $ '''
__doc__="""
This module includes any mathematical methods needed for PIDDLE.
It should have no dependencies beyond the Python library.

So far, just Robert Kern's bezierArc.
"""

from math import sin, cos, pi, ceil


def bezierArc(x1,y1, x2,y2, startAng=0, extent=90):
    """bezierArc(x1,y1, x2,y2, startAng=0, extent=90) --> List of Bezier
curve control points.

(x1, y1) and (x2, y2) are the corners of the enclosing rectangle.  The
coordinate system has coordinates that increase to the right and down.
Angles, measured in degress, start with 0 to the right (the positive X
axis) and increase counter-clockwise.  The arc extends from startAng
to startAng+extent.  I.e. startAng=0 and extent=180 yields an openside-down
semi-circle.

The resulting coordinates are of the form (x1,y1, x2,y2, x3,y3, x4,y4)
such that the curve goes from (x1, y1) to (x4, y4) with (x2, y2) and
(x3, y3) as their respective Bezier control points."""

    x1,y1, x2,y2 = min(x1,x2), max(y1,y2), max(x1,x2), min(y1,y2)

    if abs(extent) <= 90:
        arcList = [startAng]
        fragAngle = float(extent)
        Nfrag = 1
    else:
        arcList = []
        Nfrag = int(ceil(abs(extent)/90.))
        fragAngle = float(extent) / Nfrag

    x_cen = (x1+x2)/2.
    y_cen = (y1+y2)/2.
    rx = (x2-x1)/2.
    ry = (y2-y1)/2.
    halfAng = fragAngle * pi / 360.
    kappa = abs(4. / 3. * (1. - cos(halfAng)) / sin(halfAng))

    if fragAngle < 0:
        sign = -1
    else:
        sign = 1

    pointList = []

    for i in range(Nfrag):
        theta0 = (startAng + i*fragAngle) * pi / 180.
        theta1 = (startAng + (i+1)*fragAngle) *pi / 180.
        if fragAngle > 0:
            pointList.append((x_cen + rx * cos(theta0),
                              y_cen - ry * sin(theta0),
                              x_cen + rx * (cos(theta0) - kappa * sin(theta0)),
                              y_cen - ry * (sin(theta0) + kappa * cos(theta0)),
                              x_cen + rx * (cos(theta1) + kappa * sin(theta1)),
                              y_cen - ry * (sin(theta1) - kappa * cos(theta1)),
                              x_cen + rx * cos(theta1),
                              y_cen - ry * sin(theta1)))
        else:
            pointList.append((x_cen + rx * cos(theta0),
                              y_cen - ry * sin(theta0),
                              x_cen + rx * (cos(theta0) + kappa * sin(theta0)),
                              y_cen - ry * (sin(theta0) - kappa * cos(theta0)),
                              x_cen + rx * (cos(theta1) - kappa * sin(theta1)),
                              y_cen - ry * (sin(theta1) + kappa * cos(theta1)),
                              x_cen + rx * cos(theta1),
                              y_cen - ry * sin(theta1)))

    return pointList