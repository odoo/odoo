import operator, string

from reportlab.platypus import *
#from reportlab import rl_config
from reportlab.lib.styles import PropertySet, getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus.paragraph import Paragraph
#from reportlab.lib.utils import fp_str
#from reportlab.pdfbase import pdfmetrics
from reportlab.platypus.flowables import PageBreak


import os

from reportlab.test import unittest
from reportlab.test.utils import makeSuiteForClasses, outputfile, printLocation


from types import TupleType, ListType, StringType


class TableTestCase(unittest.TestCase):


    def getDataBlock(self):
        "Helper - data for our spanned table"
        return [
            # two rows are for headers
            ['Region','Product','Period',None,None,None,'Total'],
            [None,None,'Q1','Q2','Q3','Q4',None],

            # now for data
            ['North','Spam',100,110,120,130,460],
            ['North','Eggs',101,111,121,131,464],
            ['North','Guinness',102,112,122,132,468],

            ['South','Spam',100,110,120,130,460],
            ['South','Eggs',101,111,121,131,464],
            ['South','Guinness',102,112,122,132,468],
            ]

    def test_document(self):

        rowheights = (24, 16, 16, 16, 16)
        rowheights2 = (24, 16, 16, 16, 30)
        colwidths = (50, 32, 32, 32, 32, 32, 32, 32, 32, 32, 32, 32, 32)
        GRID_STYLE = TableStyle(
            [('GRID', (0,0), (-1,-1), 0.25, colors.black),
             ('ALIGN', (1,1), (-1,-1), 'RIGHT')]
            )

        styleSheet = getSampleStyleSheet()
        styNormal = styleSheet['Normal']
        styNormal.spaceBefore = 6
        styNormal.spaceAfter = 6

        data = (
            ('', 'Jan', 'Feb', 'Mar','Apr','May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'),
            ('Mugs', 0, 4, 17, 3, 21, 47, 12, 33, 2, -2, 44, 89),
            ('T-Shirts', 0, 42, 9, -3, 16, 4, 72, 89, 3, 19, 32, 119),
            ('Miscellaneous accessories', 0,0,0,0,0,0,1,0,0,0,2,13),
            ('Hats', 893, 912, '1,212', 643, 789, 159, 888, '1,298', 832, 453, '1,344','2,843')
            )
        data2 = (
            ('', 'Jan', 'Feb', 'Mar','Apr','May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'),
            ('Mugs', 0, 4, 17, 3, 21, 47, 12, 33, 2, -2, 44, 89),
            ('T-Shirts', 0, 42, 9, -3, 16, 4, 72, 89, 3, 19, 32, 119),
            ('Key Ring', 0,0,0,0,0,0,1,0,0,0,2,13),
            ('Hats\nLarge', 893, 912, '1,212', 643, 789, 159, 888, '1,298', 832, 453, '1,344','2,843')
            )


        data3 = (
            ('', 'Jan', 'Feb', 'Mar','Apr','May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'),
            ('Mugs', 0, 4, 17, 3, 21, 47, 12, 33, 2, -2, 44, 89),
            ('T-Shirts', 0, 42, 9, -3, 16, 4, 72, 89, 3, 19, 32, 119),
            ('Key Ring', 0,0,0,0,0,0,1,0,0,0,2,13),
            (Paragraph("Let's <b>really mess things up with a <i>paragraph</i>",styNormal),
                   893, 912, '1,212', 643, 789, 159, 888, '1,298', 832, 453, '1,344','2,843')
            )

        lst = []


        lst.append(Paragraph("""Basics about column sizing and cell contents""", styleSheet['Heading1']))

        t1 = Table(data, colwidths, rowheights)
        t1.setStyle(GRID_STYLE)
        lst.append(Paragraph("This is GRID_STYLE with explicit column widths.  Each cell contains a string or number\n", styleSheet['BodyText']))
        lst.append(t1)
        lst.append(Spacer(18,18))

        t2 = Table(data, None, None)
        t2.setStyle(GRID_STYLE)
        lst.append(Paragraph("""This is GRID_STYLE with no size info. It
                                does the sizes itself, measuring each text string
                                and computing the space it needs.  If the text is
                                too wide for the frame, the table will overflow
                                as seen here.""",
                             styNormal))
        lst.append(t2)
        lst.append(Spacer(18,18))

        t3 = Table(data2, None, None)
        t3.setStyle(GRID_STYLE)
        lst.append(Paragraph("""This demonstrates the effect of adding text strings with
        newlines to a cell. It breaks where you specify, and if rowHeights is None (i.e
        automatic) then you'll see the effect. See bottom left cell.""",
                             styNormal))
        lst.append(t3)
        lst.append(Spacer(18,18))


        colWidths = (None, 32, 32, 32, 32, 32, 32, 32, 32, 32, 32, 32, 32)
        t3 = Table(data3, colWidths, None)
        t3.setStyle(GRID_STYLE)
        lst.append(Paragraph("""This table does not specify the size of the first column,
                                so should work out a sane one.  In this case the element
                                at bottom left is a paragraph, which has no intrinsic size
                                (the height and width are a function of each other).  So,
                                it tots up the extra space in the frame and divides it
                                between any such unsizeable columns.  As a result the
                                table fills the width of the frame (except for the
                                6 point padding on either size).""",
                             styNormal))
        lst.append(t3)
        lst.append(PageBreak())

        lst.append(Paragraph("""Row and Column spanning""", styleSheet['Heading1']))

        lst.append(Paragraph("""This shows a very basic table.  We do a faint pink grid
        to show what's behind it - imagine this is not printed, as we'll overlay it later
        with some black lines.  We're going to "span" some cells, and have put a
        value of None in the data to signify the cells we don't care about.
        (In real life if you want an empty cell, put '' in it rather than None). """, styNormal))

        sty = TableStyle([
            #very faint grid to show what's where
            ('GRID', (0,0), (-1,-1), 0.25, colors.pink),
            ])

        t = Table(self.getDataBlock(), colWidths=None, rowHeights=None, style=sty)
        lst.append(t)



        lst.append(Paragraph("""We now center the text for the "period"
        across the four cells for each quarter.  To do this we add a 'span'
        command to the style to make the cell at row 1 column 3 cover 4 cells,
        and a 'center' command for all cells in the top row. The spanning
        is not immediately evident but trust us, it's happening - the word
        'Period' is centered across the 4 columns.  Note also that the
        underlying grid shows through.  All line drawing commands apply
        to the underlying grid, so you have to take care what you put
        grids through.""", styNormal))
        sty = TableStyle([
            #
            ('GRID', (0,0), (-1,-1), 0.25, colors.pink),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('SPAN', (2,0), (5,0)),
            ])

        t = Table(self.getDataBlock(), colWidths=None, rowHeights=None, style=sty)
        lst.append(t)

        lst.append(Paragraph("""We repeat this for the words 'Region', Product'
        and 'Total', which each span the top 2 rows; and for 'Nprth' and 'South'
        which span 3 rows.  At the moment each cell's alignment is the default
        (bottom), so these words appear to have "dropped down"; in fact they
        are sitting on the bottom of their allocated ranges.  You will just see that
        all the 'None' values vanished, as those cells are not drawn any more.""", styNormal))
        sty = TableStyle([
            #
            ('GRID', (0,0), (-1,-1), 0.25, colors.pink),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('SPAN', (2,0), (5,0)),
            #span the other column heads down 2 rows
            ('SPAN', (0,0), (0,1)),
            ('SPAN', (1,0), (1,1)),
            ('SPAN', (6,0), (6,1)),
            #span the 'north' and 'south' down 3 rows each
            ('SPAN', (0,2), (0,4)),
            ('SPAN', (0,5), (0,7)),
            ])

        t = Table(self.getDataBlock(), colWidths=None, rowHeights=None, style=sty)
        lst.append(t)


        lst.append(PageBreak())


        lst.append(Paragraph("""Now we'll tart things up a bit.  First,
        we set the vertical alignment of each spanned cell to 'middle'.
        Next we add in some line drawing commands which do not slash across
        the spanned cells (this needs a bit of work).
        Finally we'll add some thicker lines to divide it up, and hide the pink.  Voila!
        """, styNormal))
        sty = TableStyle([
            #
#            ('GRID', (0,0), (-1,-1), 0.25, colors.pink),
            ('TOPPADDING', (0,0), (-1,-1), 3),

            #span the 'period'
            ('SPAN', (2,0), (5,0)),
            #span the other column heads down 2 rows
            ('SPAN', (0,0), (0,1)),
            ('SPAN', (1,0), (1,1)),
            ('SPAN', (6,0), (6,1)),
            #span the 'north' and 'south' down 3 rows each
            ('SPAN', (0,2), (0,4)),
            ('SPAN', (0,5), (0,7)),

            #top row headings are centred
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            #everything we span is vertically centred
            #span the other column heads down 2 rows
            ('VALIGN', (0,0), (0,1), 'MIDDLE'),
            ('VALIGN', (1,0), (1,1), 'MIDDLE'),
            ('VALIGN', (6,0), (6,1), 'MIDDLE'),
            #span the 'north' and 'south' down 3 rows each
            ('VALIGN', (0,2), (0,4), 'MIDDLE'),
            ('VALIGN', (0,5), (0,7), 'MIDDLE'),

            #numeric stuff right aligned
            ('ALIGN', (2,1), (-1,-1), 'RIGHT'),

            #draw lines carefully so as not to swipe through
            #any of the 'spanned' cells
           ('GRID', (1,2), (-1,-1), 1.0, colors.black),
            ('BOX', (0,2), (0,4), 1.0, colors.black),
            ('BOX', (0,5), (0,7), 1.0, colors.black),
            ('BOX', (0,0), (0,1), 1.0, colors.black),
            ('BOX', (1,0), (1,1), 1.0, colors.black),

            ('BOX', (2,0), (5,0), 1.0, colors.black),
            ('GRID', (2,1), (5,1), 1.0, colors.black),

            ('BOX', (6,0), (6,1), 1.0, colors.black),

            # do fatter boxes around some cells
            ('BOX', (0,0), (-1,1), 2.0, colors.black),
            ('BOX', (0,2), (-1,4), 2.0, colors.black),
            ('BOX', (0,5), (-1,7), 2.0, colors.black),
            ('BOX', (-1,0), (-1,-1), 2.0, colors.black),

            ])

        t = Table(self.getDataBlock(), colWidths=None, rowHeights=None, style=sty)
        lst.append(t)

        lst.append(Paragraph("""How cells get sized""", styleSheet['Heading1']))

        lst.append(Paragraph("""So far the table has been auto-sized.  This can be
        computationally expensive, and can lead to yucky effects. Imagine a lot of
        numbers, one of which goes to 4 figures - tha numeric column will be wider.
        The best approach is to specify the column
        widths where you know them, and let the system do the heights.  Here we set some
        widths - an inch for the text columns and half an inch for the numeric ones.
        """, styNormal))

        t = Table(self.getDataBlock(),
                    colWidths=(72,72,36,36,36,36,56),
                    rowHeights=None,
                    style=sty)
        lst.append(t)

        lst.append(Paragraph("""The auto-sized example 2 steps back demonstrates
        one advanced feature of the sizing algorithm. In the table below,
        the columns for Q1-Q4 should all be the same width.  We've made
        the text above it a bit longer than "Period".  Note that this text
        is technically in the 3rd column; on our first implementation this
        was sized and column 3 was therefore quite wide.  To get it right,
        we ensure that any cells which span columns, or which are 'overwritten'
        by cells which span columns, are assigned zero width in the cell
        sizing.  Thus, only the string 'Q1' and the numbers below it are
        calculated in estimating the width of column 3, and the phrase
        "What time of year?" is not used.  However, row-spanned cells are
        taken into account. ALL the cells in the leftmost column
        have a vertical span (or are occluded by others which do)
        but it can still work out a sane width for them.

        """, styNormal))

        data = self.getDataBlock()
        data[0][2] = "Which time of year?"
        #data[7][0] = Paragraph("Let's <b>really mess things up with a <i>paragraph</i>",styNormal)
        t = Table(data,
                    #colWidths=(72,72,36,36,36,36,56),
                    rowHeights=None,
                    style=sty)
        lst.append(t)

        lst.append(Paragraph("""Paragraphs and unsizeable objects in table cells.""", styleSheet['Heading1']))

        lst.append(Paragraph("""Paragraphs and other flowable objects make table
        sizing much harder. In general the height of a paragraph is a function
        of its width so you can't ask it how wide it wants to be - and the
        REALLY wide all-on-one-line solution is rarely what is wanted. We
        refer to Paragraphs and their kin as "unsizeable objects". In this example
        we have set the widths of all but the first column.  As you can see
        it uses all the available space across the page for the first column.
        Note also that this fairly large cell does NOT contribute to the
        height calculation for its 'row'.  Under the hood it is in the
        same row as the second Spam, but this row gets a height based on
        its own contents and not the cell with the paragraph.

        """, styNormal))


        data = self.getDataBlock()
        data[5][0] = Paragraph("Let's <b>really mess things up</b> with a <i>paragraph</i>, whose height is a function of the width you give it.",styNormal)
        t = Table(data,
                    colWidths=(None,72,36,36,36,36,56),
                    rowHeights=None,
                    style=sty)
        lst.append(t)


        lst.append(Paragraph("""This one demonstrates that our current algorithm
        does not cover all cases :-(  The height of row 0 is being driven by
        the width of the para, which thinks it should fit in 1 column and not 4.
        To really get this right would involve multiple passes through all the cells
        applying rules until everything which can be sized is sized (possibly
        backtracking), applying increasingly dumb and brutal
        rules on each pass.
        """, styNormal))
        data = self.getDataBlock()
        data[0][2] = Paragraph("Let's <b>really mess things up</b> with a <i>paragraph</i>.",styNormal)
        data[5][0] = Paragraph("Let's <b>really mess things up</b> with a <i>paragraph</i>, whose height is a function of the width you give it.",styNormal)
        t = Table(data,
                    colWidths=(None,72,36,36,36,36,56),
                    rowHeights=None,
                    style=sty)
        lst.append(t)

        lst.append(Paragraph("""To avoid these problems remember the golden rule
        of ReportLab tables:  (1) fix the widths if you can, (2) don't use
        a paragraph when a string will do.
        """, styNormal))
        
        lst.append(Paragraph("""Unsized columns that contain flowables without
        precise widths, such as paragraphs and nested tables,
        still need to try and keep their content within borders and ideally 
        even honor percentage requests.  This can be tricky--and expensive.  
        But sometimes you can't follow the golden rules.
        """, styNormal))

        lst.append(Paragraph("""The code first calculates the minimum width
        for each unsized column by iterating over every flowable in each column
        and remembering the largest minimum width.  It then allocates
        available space to accomodate the minimum widths.  Any remaining space
        is divided up, treating a width of '*' as greedy, a width of None as
        non-greedy, and a percentage as a weight.  If a column is already
        wider than its percentage warrants, it is not further expanded, and
        the other widths accomodate it.
        """, styNormal))
        
        lst.append(Paragraph("""For instance, consider this tortured table.
        It contains four columns, with widths of None, None, 60%, and 20%,
        respectively, and a single row.  The first cell contains a paragraph.
        The second cell contains a table with fixed column widths that total 
        about 50% of the total available table width.  The third cell contains
        a string.  The last cell contains a table with no set widths but a 
        single cell containing a paragraph.
        """, styNormal))
        ministy = TableStyle([
            ('GRID', (0,0), (-1,-1), 1.0, colors.black),
            ])
        nested1 = [Paragraph(
            'This is a paragraph.  The column has a width of None.', 
            styNormal)]
        nested2 = [Table(
            [[Paragraph(
                'This table is set to take up two and a half inches.  The '
                'column that holds it has a width of None.', styNormal)]],
            colWidths=(180,),
            rowHeights=None,
            style=ministy)]
        nested3 = '60% width'
        nested4 = [Table(
            [[[Paragraph(
                "This is a table with a paragraph in it but no width set.  "
                "The column width in the containing table is 20%.", 
                styNormal)]]],
            colWidths=(None,),
            rowHeights=None,
            style=ministy)]
        t = Table([[nested1, nested2, nested3, nested4]],
                  colWidths=(None, None, '60%', '20%'),
                  rowHeights=None,
                  style=ministy)
        lst.append(t)
        
        lst.append(Paragraph("""Notice that the second column does expand to
        account for the minimum size of its contents; and that the remaining
        space goes to the third column, in an attempt to honor the '60%' 
        request as much as possible.  This is reminiscent of the typical HTML
        browser approach to tables.""", styNormal))

        lst.append(Paragraph("""To get an idea of how potentially expensive
        this is, consider the case of the last column: the table gets the
        minimum width of every flowable of every cell in the column.  In this
        case one of the flowables is a table with a column without a set
        width, so the nested table must itself iterate over its flowables. 
        The contained paragraph then calculates the width of every word in it
        to see what the biggest word is, given the set font face and size.  It
        is easy to imagine creating a structure of this sort that took an
        unacceptably large amount of time to calculate.  Remember the golden
        rule, if you can. """, styNormal))
        
        lst.append(Paragraph("""This code does not yet handle spans well.""",
        styNormal))

        SimpleDocTemplate(outputfile('test_table_layout.pdf'), showBoundary=1).build(lst)

def makeSuite():
    return makeSuiteForClasses(TableTestCase)


#noruntests
if __name__ == "__main__":
    unittest.TextTestRunner().run(makeSuite())
    print 'saved '+outputfile('test_table_layout.pdf')
    printLocation()
