from reportlab.lib import styles
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import Preformatted, Paragraph, Frame, \
     Image, Table, TableStyle, Spacer


def getParagraphStyles():
    """Returns a dictionary of styles to get you started.

    We will provide a way to specify a module of these.  Note that
    this just includes TableStyles as well as ParagraphStyles for any
    tables you wish to use.
    """

    stylesheet = {}
    ParagraphStyle = styles.ParagraphStyle

    para = ParagraphStyle('Normal', None)   #the ancestor of all
    para.fontName = 'Times-Roman'
    para.fontSize = 24
    para.leading = 28
    stylesheet['Normal'] = para

    #This one is spaced out a bit...
    para = ParagraphStyle('BodyText', stylesheet['Normal'])
    para.spaceBefore = 12
    stylesheet['BodyText'] = para

    #Indented, for lists
    para = ParagraphStyle('Indent', stylesheet['Normal'])
    para.leftIndent = 36
    para.firstLineIndent = 0
    stylesheet['Indent'] = para

    para = ParagraphStyle('Centered', stylesheet['Normal'])
    para.alignment = TA_CENTER
    stylesheet['Centered'] = para

    para = ParagraphStyle('BigCentered', stylesheet['Normal'])
    para.spaceBefore = 12
    para.alignment = TA_CENTER
    stylesheet['BigCentered'] = para

    para = ParagraphStyle('Italic', stylesheet['BodyText'])
    para.fontName = 'Times-Italic'
    stylesheet['Italic'] = para

    para = ParagraphStyle('Title', stylesheet['Normal'])
    para.fontName = 'Times-Roman'
    para.fontSize = 48
    para.leading = 58
    para.alignment = TA_CENTER
    stylesheet['Title'] = para

    para = ParagraphStyle('Heading1', stylesheet['Normal'])
    para.fontName = 'Times-Bold'
    para.fontSize = 36
    para.leading = 44
    para.alignment = TA_CENTER
    stylesheet['Heading1'] = para

    para = ParagraphStyle('Heading2', stylesheet['Normal'])
    para.fontName = 'Times-Bold'
    para.fontSize = 28
    para.leading = 34
    para.spaceBefore = 24
    stylesheet['Heading2'] = para

    para = ParagraphStyle('Heading3', stylesheet['Normal'])
    para.fontName = 'Times-BoldItalic'
    para.spaceBefore = 24
    stylesheet['Heading3'] = para

    para = ParagraphStyle('Heading4', stylesheet['Normal'])
    para.fontName = 'Times-BoldItalic'
    para.spaceBefore = 6
    stylesheet['Heading4'] = para

    para = ParagraphStyle('Bullet', stylesheet['Normal'])
    para.firstLineIndent = 0
    para.leftIndent = 56
    para.spaceBefore = 6
    para.bulletFontName = 'Symbol'
    para.bulletFontSize = 24
    para.bulletIndent = 20
    stylesheet['Bullet'] = para

    para = ParagraphStyle('Definition', stylesheet['Normal'])
    #use this for definition lists
    para.firstLineIndent = 0
    para.leftIndent = 72
    para.bulletIndent = 0
    para.spaceBefore = 12
    para.bulletFontName = 'Helvetica-BoldOblique'
    para.bulletFontSize = 24
    stylesheet['Definition'] = para

    para = ParagraphStyle('Code', stylesheet['Normal'])
    para.fontName = 'Courier'
    para.fontSize = 16
    para.leading = 18
    para.leftIndent = 36
    stylesheet['Code'] = para

    para = ParagraphStyle('PythonCode', stylesheet['Normal'])
    para.fontName = 'Courier'
    para.fontSize = 16
    para.leading = 18
    para.leftIndent = 36
    stylesheet['PythonCode'] = para

    para = ParagraphStyle('Small', stylesheet['Normal'])
    para.fontSize = 12
    para.leading = 14
    stylesheet['Small'] = para

    #now for a table
    ts = TableStyle([
         ('FONT', (0,0), (-1,-1), 'Times-Roman', 24),
         ('LINEABOVE', (0,0), (-1,0), 2, colors.green),
         ('LINEABOVE', (0,1), (-1,-1), 0.25, colors.black),
         ('LINEBELOW', (0,-1), (-1,-1), 2, colors.green),
         ('LINEBEFORE', (-1,0), (-1,-1), 2, colors.black),
         ('ALIGN', (1,1), (-1,-1), 'RIGHT'),   #all numeric cells right aligned
         ('TEXTCOLOR', (0,1), (0,-1), colors.red),
         ('BACKGROUND', (0,0), (-1,0), colors.Color(0,0.7,0.7))
         ])
    stylesheet['table1'] = ts

    return stylesheet
