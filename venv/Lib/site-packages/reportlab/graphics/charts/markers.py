#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/graphics/charts/markers.py

__version__='3.3.0'
__doc__="""This modules defines a collection of markers used in charts.

The make* functions return a simple shape or a widget as for
the smiley.
"""

from reportlab.lib import colors
from reportlab.graphics.shapes import Rect, Circle, Polygon
from reportlab.graphics.widgets.signsandsymbols import SmileyFace


def makeEmptySquare(x, y, size, color):
    "Make an empty square marker."

    d = size/2.0
    rect = Rect(x-d, y-d, 2*d, 2*d)
    rect.strokeColor = color
    rect.fillColor = None

    return rect


def makeFilledSquare(x, y, size, color):
    "Make a filled square marker."

    d = size/2.0
    rect = Rect(x-d, y-d, 2*d, 2*d)
    rect.strokeColor = color
    rect.fillColor = color

    return rect


def makeFilledDiamond(x, y, size, color):
    "Make a filled diamond marker."

    d = size/2.0
    poly = Polygon((x-d,y, x,y+d, x+d,y, x,y-d))
    poly.strokeColor = color
    poly.fillColor = color

    return poly


def makeEmptyCircle(x, y, size, color):
    "Make a hollow circle marker."

    d = size/2.0
    circle = Circle(x, y, d)
    circle.strokeColor = color
    circle.fillColor = colors.white

    return circle


def makeFilledCircle(x, y, size, color):
    "Make a hollow circle marker."

    d = size/2.0
    circle = Circle(x, y, d)
    circle.strokeColor = color
    circle.fillColor = color

    return circle


def makeSmiley(x, y, size, color):
    "Make a smiley marker."

    d = size
    s = SmileyFace()
    s.fillColor = color
    s.x = x-d
    s.y = y-d
    s.size = d*2

    return s
