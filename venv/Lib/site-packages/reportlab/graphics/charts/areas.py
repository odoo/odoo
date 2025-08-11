#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/graphics/charts/areas.py

__version__='3.3.0'
__doc__='''This module defines a Area mixin classes'''

from reportlab.lib.validators import isNumber, isColorOrNone, isNoneOrShape
from reportlab.graphics.widgetbase import Widget
from reportlab.graphics.shapes import Rect, Group, Line, Polygon
from reportlab.lib.attrmap import AttrMap, AttrMapValue
from reportlab.lib.colors import grey

class PlotArea(Widget):
    "Abstract base class representing a chart's plot area, pretty unusable by itself."
    _attrMap = AttrMap(
        x = AttrMapValue(isNumber, desc='X position of the lower-left corner of the chart.'),
        y = AttrMapValue(isNumber, desc='Y position of the lower-left corner of the chart.'),
        width = AttrMapValue(isNumber, desc='Width of the chart.'),
        height = AttrMapValue(isNumber, desc='Height of the chart.'),
        strokeColor = AttrMapValue(isColorOrNone, desc='Color of the plot area border.'),
        strokeWidth = AttrMapValue(isNumber, desc='Width plot area border.'),
        fillColor = AttrMapValue(isColorOrNone, desc='Color of the plot area interior.'),
        background = AttrMapValue(isNoneOrShape, desc='Handle to background object e.g. Rect(0,0,width,height).'),
        debug = AttrMapValue(isNumber, desc='Used only for debugging.'),
        )

    def __init__(self):
        self.x = 20
        self.y = 10
        self.height = 85
        self.width = 180
        self.strokeColor = None
        self.strokeWidth = 1
        self.fillColor = None
        self.background = None
        self.debug = 0

    def makeBackground(self):
        if self.background is not None:
            BG = self.background
            if isinstance(BG,Group):
                g = BG
                for bg in g.contents:
                    bg.x = self.x
                    bg.y = self.y
                    bg.width = self.width
                    bg.height = self.height
            else:
                g = Group()
                if type(BG) not in (type(()),type([])): BG=(BG,)
                for bg in BG:
                    bg.x = self.x
                    bg.y = self.y
                    bg.width = self.width
                    bg.height = self.height
                    g.add(bg)
            return g
        else:
            strokeColor,strokeWidth,fillColor=self.strokeColor, self.strokeWidth, self.fillColor
            if (strokeWidth and strokeColor) or fillColor:
                g = Group()
                _3d_dy = getattr(self,'_3d_dy',None)
                x = self.x
                y = self.y
                h = self.height
                w = self.width
                if _3d_dy is not None:
                    _3d_dx = self._3d_dx
                    if fillColor and not strokeColor:
                        from reportlab.lib.colors import Blacker
                        c = Blacker(fillColor, getattr(self,'_3d_blacken',0.7))
                    else:
                        c = strokeColor
                    if not strokeWidth: strokeWidth = 0.5
                    if fillColor or strokeColor or c:
                        bg = Polygon([x,y,x,y+h,x+_3d_dx,y+h+_3d_dy,x+w+_3d_dx,y+h+_3d_dy,x+w+_3d_dx,y+_3d_dy,x+w,y],
                            strokeColor=strokeColor or c or grey, strokeWidth=strokeWidth, fillColor=fillColor)
                        g.add(bg)
                        g.add(Line(x,y,x+_3d_dx,y+_3d_dy, strokeWidth=0.5, strokeColor=c))
                        g.add(Line(x+_3d_dx,y+_3d_dy, x+_3d_dx,y+h+_3d_dy,strokeWidth=0.5, strokeColor=c))
                        fc = Blacker(c, getattr(self,'_3d_blacken',0.8))
                        g.add(Polygon([x,y,x+_3d_dx,y+_3d_dy,x+w+_3d_dx,y+_3d_dy,x+w,y],
                            strokeColor=strokeColor or c or grey, strokeWidth=strokeWidth, fillColor=fc))
                        bg = Line(x+_3d_dx,y+_3d_dy, x+w+_3d_dx,y+_3d_dy,strokeWidth=0.5, strokeColor=c)
                    else:
                        bg = None
                else:
                    bg = Rect(x, y, w, h,
                        strokeColor=strokeColor, strokeWidth=strokeWidth, fillColor=fillColor)
                if bg: g.add(bg)
                return g
            else:
                return None
