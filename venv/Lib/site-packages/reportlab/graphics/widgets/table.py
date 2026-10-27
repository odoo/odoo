#!/usr/bin/env python
#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/graphics/widgets/table.py
__version__='3.3.0'

from reportlab.graphics.widgetbase import Widget
from reportlab.graphics import shapes
from reportlab.lib import colors
from reportlab.lib.validators import *
from reportlab.lib.attrmap import *

from reportlab.graphics.shapes import Drawing

class TableWidget(Widget):
    """A two dimensions table of labels
    """

    _attrMap = AttrMap(
        x = AttrMapValue(isNumber, desc="x position of left edge of table"),
        y = AttrMapValue(isNumber, desc="y position of bottom edge of table"),
        width = AttrMapValue(isNumber, desc="table width"),
        height = AttrMapValue(isNumber, desc="table height"),
        borderStrokeColor = AttrMapValue(isColorOrNone, desc="table border color"),
        fillColor = AttrMapValue(isColorOrNone, desc="table fill color"),
        borderStrokeWidth = AttrMapValue(isNumber, desc="border line width"),
        horizontalDividerStrokeColor = AttrMapValue(isColorOrNone, desc="table inner horizontal lines color"),
        verticalDividerStrokeColor = AttrMapValue(isColorOrNone, desc="table inner vertical lines color"),
        horizontalDividerStrokeWidth = AttrMapValue(isNumber, desc="table inner horizontal lines width"),
        verticalDividerStrokeWidth = AttrMapValue(isNumber, desc="table inner vertical lines width"),
        dividerDashArray = AttrMapValue(isListOfNumbersOrNone, desc='Dash array for dividerLines.'),
        data = AttrMapValue(None, desc="a list of list of strings to be displayed in the cells"),
        boxAnchor = AttrMapValue(isBoxAnchor, desc="location of the table anchoring point"),
        fontName = AttrMapValue(isString, desc="text font in the table"),
        fontSize = AttrMapValue(isNumber, desc="font size of the table"),
        fontColor = AttrMapValue(isColorOrNone, desc="font color"),
        alignment = AttrMapValue(OneOf("left", "right"), desc="Alignment of text within cells"),
        textAnchor = AttrMapValue(OneOf('start','middle','end','numeric'), desc="Alignment of text within cells"),
    )

    def __init__(self, x=10, y=10, **kw):

        self.x = x
        self.y = y
        self.width = 200
        self.height = 100
        self.borderStrokeColor = colors.black
        self.fillColor = None
        self.borderStrokeWidth = 0.5
        self.horizontalDividerStrokeColor = colors.black
        self.verticalDividerStrokeColor = colors.black
        self.horizontalDividerStrokeWidth = 0.5
        self.verticalDividerStrokeWidth = 0.25
        self.dividerDashArray = None
        self.data = [['North','South','East','West'],[100,110,120,130],['A','B','C','D']] # list of rows each row is a list of columns
        self.boxAnchor = 'nw'
        #self.fontName = None
        self.fontSize = 8
        self.fontColor = colors.black
        self.alignment = 'right'
        self.textAnchor = 'start'


        for k, v in kw.items():
            if k in list(self.__class__._attrMap.keys()):
                setattr(self, k, v)
            else:
                raise ValueError('invalid argument supplied for class %s'%self.__class__)

    def demo(self):
        """ returns a sample of this widget with data
        """
        d = Drawing(400, 200)
        t = TableWidget()
        d.add(t, name='table')
        d.table.dividerDashArray = (1, 3, 2)
        d.table.verticalDividerStrokeColor = None
        d.table.borderStrokeWidth = 0
        d.table.borderStrokeColor = colors.red
        return d

    def draw(self):
        """ returns a group of shapes
        """
        g = shapes.Group()

        #overall border and fill
        if self.borderStrokeColor or self.fillColor: # adds border and filling color
            rect = shapes.Rect(self.x, self.y, self.width, self.height)
            rect.fillColor = self.fillColor
            rect.strokeColor = self.borderStrokeColor
            rect.strokeWidth = self.borderStrokeWidth
            g.add(rect)

        #special case - for an empty table we want to avoid divide-by-zero
        data = self.preProcessData(self.data)
        rows = len(self.data)
        cols = len(self.data[0])
        #print "(rows,cols)=(%s, %s)"%(rows,cols)
        row_step = self.height / float(rows)
        col_step = self.width / float(cols)
        #print "(row_step,col_step)=(%s, %s)"%(row_step,col_step)
        # draw the grid
        if self.horizontalDividerStrokeColor:
            for i in range(rows): # make horizontal lines
                x1 = self.x
                x2 = self.x + self.width
                y = self.y + row_step*i
                #print 'line (%s, %s), (%s, %s)'%(x1, y, x2, y)
                line = shapes.Line(x1, y, x2, y)
                line.strokeDashArray = self.dividerDashArray
                line.strokeWidth = self.horizontalDividerStrokeWidth
                line.strokeColor = self.horizontalDividerStrokeColor
                g.add(line)
        if self.verticalDividerStrokeColor:
            for i in range(cols): # make vertical lines
                x = self.x+col_step*i
                y1 = self.y
                y2 = self.y + self.height
                #print 'line (%s, %s), (%s, %s)'%(x, y1, x, y2)
                line = shapes.Line(x, y1, x, y2)
                line.strokeDashArray = self.dividerDashArray
                line.strokeWidth = self.verticalDividerStrokeWidth
                line.strokeColor = self.verticalDividerStrokeColor
                g.add(line)

        # since we plot data from down up, we reverse the list
        self.data.reverse()
        for (j, row) in enumerate(self.data):
            y = self.y + j*row_step + 0.5*row_step - 0.5 * self.fontSize
            for (i, datum) in enumerate(row):
                if datum:
                    x = self.x + i*col_step + 0.5*col_step
                    s = shapes.String(x, y, str(datum), textAnchor=self.textAnchor)
                    s.fontName = self.fontName
                    s.fontSize = self.fontSize
                    s.fillColor = self.fontColor
                    g.add(s)
        return g

    def preProcessData(self, data):
        """preprocess and return a new array with at least one row
        and column (use a None) if needed, and all rows the same
        length (adding Nones if needed)

        """
        if not data:
            return [[None]]
        #make all rows have similar number of cells, append None when needed
        max_row = max( [len(x) for x in data] )
        for rowNo, row in enumerate(data):
            if len(row) < max_row:
                row.extend([None]*(max_row-len(row)))
        return data

#test
if __name__ == '__main__':
    d = TableWidget().demo()
    import os
    d.save(formats=['pdf'],outDir=os.getcwd(),fnRoot=None)
