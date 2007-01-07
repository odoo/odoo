"""This is an example style sheet.  You can create your own, and
have them loaded by the presentation.  A style sheet is just a
dictionary, where they keys are style names and the values are
ParagraphStyle objects.

You must provide a function called "getParagraphStyles()" to
return it.  In future, we can put things like LineStyles,
TableCellStyles etc. in the same modules.

You might wish to have two parallel style sheets, one for colour
and one for black and white, so you can switch your presentations
easily.

A style sheet MUST define a style called 'Normal'.
"""

from reportlab.lib import styles
from reportlab.lib.colors import *
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY


def getParagraphStyles():
    """Returns a dictionary of styles based on Helvetica"""

    stylesheet = {}
    ParagraphStyle = styles.ParagraphStyle

    para = ParagraphStyle('Normal', None)   #the ancestor of all
    para.fontName = 'Helvetica-Bold'
    para.fontSize = 24
    para.leading = 28
    para.textColor = white
    stylesheet['Normal'] = para

    para = ParagraphStyle('BodyText', stylesheet['Normal'])
    para.spaceBefore = 12
    stylesheet['BodyText'] = para

    para = ParagraphStyle('BigCentered', stylesheet['Normal'])
    para.spaceBefore = 12
    para.alignment = TA_CENTER
    stylesheet['BigCentered'] = para

    para = ParagraphStyle('Italic', stylesheet['BodyText'])
    para.fontName = 'Helvetica-Oblique'
    para.textColor = white
    stylesheet['Italic'] = para

    para = ParagraphStyle('Title', stylesheet['Normal'])
    para.fontName = 'Helvetica'
    para.fontSize = 48
    para.Leading = 58
    para.spaceAfter = 36
    para.alignment = TA_CENTER
    stylesheet['Title'] = para

    para = ParagraphStyle('Heading1', stylesheet['Normal'])
    para.fontName = 'Helvetica-Bold'
    para.fontSize = 48# 36
    para.leading = 44
    para.spaceAfter = 36
    para.textColor = green
    para.alignment = TA_LEFT
    stylesheet['Heading1'] = para

    para = ParagraphStyle('Heading2', stylesheet['Normal'])
    para.fontName = 'Helvetica-Bold'
    para.fontSize = 28
    para.leading = 34
    para.spaceBefore = 24
    para.spaceAfter = 12
    stylesheet['Heading2'] = para

    para = ParagraphStyle('Heading3', stylesheet['Normal'])
    para.fontName = 'Helvetica-BoldOblique'
    para.spaceBefore = 24
    para.spaceAfter = 12
    stylesheet['Heading3'] = para

    para = ParagraphStyle('Bullet', stylesheet['Normal'])
    para.firstLineIndent = -18
    para.leftIndent = 72
    para.spaceBefore = 6
    para.bulletFontName = 'Symbol'
    para.bulletFontSize = 24
    para.bulletIndent = 36
    stylesheet['Bullet'] = para

    para = ParagraphStyle('Definition', stylesheet['Normal'])
    #use this for definition lists
    para.firstLineIndent = 0
    para.leftIndent = 72
    para.bulletIndent = 0
    para.spaceBefore = 12
    para.bulletFontName = 'Helvetica-BoldOblique'
    stylesheet['Definition'] = para

    para = ParagraphStyle('Code', stylesheet['Normal'])
    para.fontName = 'Courier-Bold'
    para.fontSize = 16
    para.leading = 18
    para.leftIndent = 36
    para.textColor = chartreuse
    stylesheet['Code'] = para

    return stylesheet