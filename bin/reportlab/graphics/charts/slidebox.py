from reportlab.lib.colors import Color, white, black
from reportlab.graphics.charts.textlabels import Label
from reportlab.graphics.shapes import Polygon, Line, Circle, String, Drawing, PolyLine, Group, Rect
from reportlab.graphics.widgetbase import Widget, TypedPropertyCollection
from reportlab.lib.attrmap import *
from reportlab.lib.validators import *
from reportlab.lib.units import cm
from reportlab.pdfbase.pdfmetrics import stringWidth, getFont
from reportlab.graphics.widgets.grids import ShadedRect, Grid

class SlideBox(Widget):
    """Returns a slidebox widget"""
    _attrMap = AttrMap(
        labelFontName = AttrMapValue(isString, desc="Name of font used for the labels"),
        labelFontSize = AttrMapValue(isNumber, desc="Size of font used for the labels"),
        labelStrokeColor = AttrMapValue(isColorOrNone, desc="Colour for for number outlines"),
        labelFillColor = AttrMapValue(isColorOrNone, desc="Colour for number insides"),
        startColor = AttrMapValue(isColor, desc='Color of first box'),
        endColor = AttrMapValue(isColor, desc='Color of last box'),
        numberOfBoxes = AttrMapValue(isInt, desc='How many boxes there are'),
        trianglePosition = AttrMapValue(isInt, desc='Which box is highlighted by the triangles'),
        triangleHeight = AttrMapValue(isNumber, desc="Height of indicator triangles"),
        triangleWidth = AttrMapValue(isNumber, desc="Width of indicator triangles"),
        triangleFillColor = AttrMapValue(isColor, desc="Colour of indicator triangles"),
        triangleStrokeColor = AttrMapValue(isColorOrNone, desc="Colour of indicator triangle outline"),
        triangleStrokeWidth = AttrMapValue(isNumber, desc="Colour of indicator triangle outline"),
        boxHeight = AttrMapValue(isNumber, desc="Height of the boxes"),
        boxWidth = AttrMapValue(isNumber, desc="Width of the boxes"),
        boxSpacing = AttrMapValue(isNumber, desc="Space between the boxes"),
        boxOutlineColor = AttrMapValue(isColorOrNone, desc="Colour used to outline the boxes (if any)"),
        boxOutlineWidth = AttrMapValue(isNumberOrNone, desc="Width of the box outline (if any)"),
        leftPadding = AttrMapValue(isNumber, desc='Padding on left of drawing'),
        rightPadding = AttrMapValue(isNumber, desc='Padding on right of drawing'),
        topPadding = AttrMapValue(isNumber, desc='Padding at top of drawing'),
        bottomPadding = AttrMapValue(isNumber, desc='Padding at bottom of drawing'),
        background = AttrMapValue(isColorOrNone, desc='Colour of the background to the drawing (if any)'),
        sourceLabelText = AttrMapValue(isNoneOrString, desc="Text used for the 'source' label (can be empty)"),
        sourceLabelOffset = AttrMapValue(isNumber, desc='Padding at bottom of drawing'),
        sourceLabelFontName = AttrMapValue(isString, desc="Name of font used for the 'source' label"),
        sourceLabelFontSize = AttrMapValue(isNumber, desc="Font size for the 'source' label"),
        sourceLabelFillColor = AttrMapValue(isColorOrNone, desc="Colour ink for the 'source' label (bottom right)"),
        )

    def __init__(self):
        self.labelFontName = "Helvetica-Bold"
        self.labelFontSize = 10
        self.labelStrokeColor = black
        self.labelFillColor = white
        self.startColor = colors.Color(232/255.0,224/255.0,119/255.0)
        self.endColor = colors.Color(25/255.0,77/255.0,135/255.0)
        self.numberOfBoxes = 7
        self.trianglePosition = 7
        self.triangleHeight = 0.12*cm
        self.triangleWidth = 0.38*cm
        self.triangleFillColor = white
        self.triangleStrokeColor = black
        self.triangleStrokeWidth = 0.58
        self.boxHeight = 0.55*cm
        self.boxWidth = 0.73*cm
        self.boxSpacing = 0.075*cm
        self.boxOutlineColor = black
        self.boxOutlineWidth = 0.58
        self.leftPadding=5
        self.rightPadding=5
        self.topPadding=5
        self.bottomPadding=5
        self.background=None
        self.sourceLabelText = "Source: ReportLab"
        self.sourceLabelOffset = 0.2*cm
        self.sourceLabelFontName = "Helvetica-Oblique"
        self.sourceLabelFontSize = 6
        self.sourceLabelFillColor = black

    def _getDrawingDimensions(self):
        tx=(self.numberOfBoxes*self.boxWidth)
        if self.numberOfBoxes>1: tx=tx+((self.numberOfBoxes-1)*self.boxSpacing)
        tx=tx+self.leftPadding+self.rightPadding
        ty=self.boxHeight+self.triangleHeight
        ty=ty+self.topPadding+self.bottomPadding+self.sourceLabelOffset+self.sourceLabelFontSize
        return (tx,ty)

    def _getColors(self):
        # for calculating intermediate colors...
        numShades = self.numberOfBoxes+1
        fillColorStart = self.startColor
        fillColorEnd = self.endColor
        colorsList =[]

        for i in range(0,numShades):
            colorsList.append(colors.linearlyInterpolatedColor(fillColorStart, fillColorEnd, 0, numShades-1, i))
        return colorsList

    def demo(self,drawing=None):
        from reportlab.lib import colors
        if not drawing:
            tx,ty=self._getDrawingDimensions()
            drawing = Drawing(tx,ty)
        drawing.add(self.draw())
        return drawing

    def draw(self):
        g = Group()
        ys = self.bottomPadding+(self.triangleHeight/2)+self.sourceLabelOffset+self.sourceLabelFontSize
        if self.background:
            x,y = self._getDrawingDimensions()
            g.add(Rect(-self.leftPadding,-ys,x,y,
                       strokeColor=None,
                       strokeWidth=0,
                       fillColor=self.background))

        ascent=getFont(self.labelFontName).face.ascent/1000.
        if ascent==0: ascent=0.718 # default (from helvetica)
        ascent=ascent*self.labelFontSize # normalize

        colorsList = self._getColors()

        # Draw the boxes - now uses ShadedRect from grids
        x=0
        for f in range (0,self.numberOfBoxes):
            sr=ShadedRect()
            sr.x=x
            sr.y=0
            sr.width=self.boxWidth
            sr.height=self.boxHeight
            sr.orientation = 'vertical'
            sr.numShades = 30
            sr.fillColorStart = colorsList[f]
            sr.fillColorEnd = colorsList[f+1]
            sr.strokeColor = None
            sr.strokeWidth = 0

            g.add(sr)

            g.add(Rect(x,0,self.boxWidth,self.boxHeight,
                   strokeColor=self.boxOutlineColor,
                   strokeWidth=self.boxOutlineWidth,
                   fillColor=None))

            g.add(String(x+self.boxWidth/2.,(self.boxHeight-ascent)/2.,
                   text = str(f+1),
                   fillColor = self.labelFillColor,
                   strokeColor=self.labelStrokeColor,
                   textAnchor = 'middle',
                   fontName = self.labelFontName,
                   fontSize = self.labelFontSize))
            x=x+self.boxWidth+self.boxSpacing

        #do triangles
        xt = (self.trianglePosition*self.boxWidth)
        if self.trianglePosition>1:
            xt = xt+(self.trianglePosition-1)*self.boxSpacing
        xt = xt-(self.boxWidth/2)
        g.add(Polygon(
            strokeColor = self.triangleStrokeColor,
            strokeWidth = self.triangleStrokeWidth,
            fillColor = self.triangleFillColor,
            points=[xt,self.boxHeight-(self.triangleHeight/2),
                    xt-(self.triangleWidth/2),self.boxHeight+(self.triangleHeight/2),
                    xt+(self.triangleWidth/2),self.boxHeight+(self.triangleHeight/2),
                        xt,self.boxHeight-(self.triangleHeight/2)]))
        g.add(Polygon(
            strokeColor = self.triangleStrokeColor,
            strokeWidth = self.triangleStrokeWidth,
            fillColor = self.triangleFillColor,
            points=[xt,0+(self.triangleHeight/2),
                    xt-(self.triangleWidth/2),0-(self.triangleHeight/2),
                    xt+(self.triangleWidth/2),0-(self.triangleHeight/2),
                    xt,0+(self.triangleHeight/2)]))

        #source label
        if self.sourceLabelText != None:
            g.add(String(x-self.boxSpacing,0-(self.triangleHeight/2)-self.sourceLabelOffset-(self.sourceLabelFontSize),
                       text = self.sourceLabelText,
                       fillColor = self.sourceLabelFillColor,
                       textAnchor = 'end',
                       fontName = self.sourceLabelFontName,
                       fontSize = self.sourceLabelFontSize))

        g.shift(self.leftPadding, ys)

        return g


if __name__ == "__main__":
    d = SlideBox()
    d.demo().save(fnRoot="slidebox")
