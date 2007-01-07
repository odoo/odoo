#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/tools/docco/stylesheet.py
#standard stylesheet for our manuals
from reportlab.lib.styles import StyleSheet1, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib import colors


def getStyleSheet():
    """Returns a stylesheet object"""
    stylesheet = StyleSheet1()

    stylesheet.add(ParagraphStyle(name='Normal',
                                  fontName='Times-Roman',
                                  fontSize=10,
                                  leading=12,
                                  spaceBefore=6)
                   )

    stylesheet.add(ParagraphStyle(name='Comment',
                                  fontName='Times-Italic')
                   )

    stylesheet.add(ParagraphStyle(name='Indent0',
                                  leftIndent=18,)
                   )

    stylesheet.add(ParagraphStyle(name='Indent1',
                                  leftIndent=36,
                                  firstLineIndent=0,
                                  spaceBefore=1,
                                  spaceAfter=7)
                   )
    
    stylesheet.add(ParagraphStyle(name='Indent2',
                                  leftIndent=50,
                                  firstLineIndent=0,
                                  spaceAfter=100)
                   )

    stylesheet.add(ParagraphStyle(name='BodyText',
                                  parent=stylesheet['Normal'],
                                  spaceBefore=6)
                   )
    stylesheet.add(ParagraphStyle(name='Italic',
                                  parent=stylesheet['BodyText'],
                                  fontName = 'Times-Italic')
                   )

    stylesheet.add(ParagraphStyle(name='Heading1',
                                  parent=stylesheet['Normal'],
                                  fontName = 'Times-Bold',
                                  alignment=TA_CENTER,
                                  fontSize=18,
                                  leading=22,
                                  spaceAfter=6),
                   alias='h1')

    stylesheet.add(ParagraphStyle(name='Heading2',
                                  parent=stylesheet['Normal'],
                                  fontName = 'Times-Bold',
                                  fontSize=14,
                                  leading=17,
                                  spaceBefore=12,
                                  spaceAfter=6),
                   alias='h2')

    stylesheet.add(ParagraphStyle(name='Heading3',
                                  parent=stylesheet['Normal'],
                                  fontName = 'Times-BoldItalic',
                                  fontSize=12,
                                  leading=14,
                                  spaceBefore=12,
                                  spaceAfter=6),
                   alias='h3')

    stylesheet.add(ParagraphStyle(name='Heading4',
                                  parent=stylesheet['Normal'],
                                  fontName = 'Times-BoldItalic',
                                  spaceBefore=10,
                                  spaceAfter=4),
                   alias='h4')

    stylesheet.add(ParagraphStyle(name='Title',
                                  parent=stylesheet['Normal'],
                                  fontName = 'Times-Bold',
                                  fontSize=32,
                                  leading=40,
                                  spaceAfter=36,
                                  alignment=TA_CENTER
                                  ),
                   alias='t')

    stylesheet.add(ParagraphStyle(name='Bullet',
                                  parent=stylesheet['Normal'],
                                  firstLineIndent=0,
                                  leftIndent=54,
                                  bulletIndent=18,
                                  spaceBefore=0,
                                  bulletFontName='Symbol'),
                   alias='bu')

    stylesheet.add(ParagraphStyle(name='Definition',
                                  parent=stylesheet['Normal'],
                                  firstLineIndent=0,
                                  leftIndent=36,
                                  bulletIndent=0,
                                  spaceBefore=6,
                                  bulletFontName='Times-BoldItalic'),
                   alias='df')

    stylesheet.add(ParagraphStyle(name='Code',
                                  parent=stylesheet['Normal'],
                                  fontName='Courier',
                                  textColor=colors.navy,
                                  fontSize=8,
                                  leading=8.8,
                                  leftIndent=36,
                                  firstLineIndent=0))
    
    stylesheet.add(ParagraphStyle(name='Link',
                                  parent=stylesheet['Code'],
                                  spaceAfter=7,
                                  spaceBefore=0,
                                  leftIndent=55))

    stylesheet.add(ParagraphStyle(name='FunctionHeader',
                                  parent=stylesheet['Normal'],
                                  fontName='Courier-Bold',
                                  fontSize=8,
                                  leading=8.8))

    stylesheet.add(ParagraphStyle(name='DocString',
                                  parent=stylesheet['Normal'],
                                  fontName='Courier',
                                  fontSize=8,
                                  leftIndent=18,
                                  leading=8.8))

    stylesheet.add(ParagraphStyle(name='DocStringIndent',
                                  parent=stylesheet['Normal'],
                                  fontName='Courier',
                                  fontSize=8,
                                  leftIndent=36,
                                  leading=8.8))

    stylesheet.add(ParagraphStyle(name='URL',
                                  parent=stylesheet['Normal'],
                                  fontName='Courier',
                                  textColor=colors.navy,
                                  alignment=TA_CENTER),
                   alias='u')

    stylesheet.add(ParagraphStyle(name='Centred',
                                  parent=stylesheet['Normal'],
                                  alignment=TA_CENTER
                                  ))

    stylesheet.add(ParagraphStyle(name='Caption',
                                  parent=stylesheet['Centred'],
                                  fontName='Times-Italic'
                                  ))

    return stylesheet