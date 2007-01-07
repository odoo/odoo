#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/docs/userguide/ch6_tables.py
from reportlab.tools.docco.rl_doc_utils import *
from reportlab.platypus import Image
import reportlab

heading1("Tables and TableStyles")
disc("""
The $Table$  and $LongTable$ classes derive from the $Flowable$ class and are intended
as a simple textual gridding mechanisms. The $longTable$ class uses a greedy algorithm
when calculating column widths and is intended for long tables where speed counts.
$Table$ cells can hold anything which can be converted to
a <b>Python</b> $string$ or $Flowables$ (or lists of $Flowables$).
""")

disc("""
Our present tables are a trade-off between efficient drawing and specification
and functionality.  We assume the reader has some familiarity with HTML tables.
In brief, they have the following characteristics:
""")

bullet("""They can contain anything convertible to a string; flowable
objects such as other tables; or entire sub-stories""")

bullet("""They can work out the row heights to fit the data if you don't supply
the row height.  (They can also work out the widths, but generally it is better
for a designer to set the width manually, and it draws faster).""")

bullet("""They can split across pages if needed (see the canSplit attribute).
You can specify that a number of rows at the top and bottom should be
repeated after the split (e.g. show the headers again on page 2,3,4...)""")

bullet("""For very wide tables, they can also split 'by column'.  You can choose
whether tou want to split down-and-across or across-and-down""")

bullet("""They have a simple and powerful notation for specifying shading and
gridlines which works well with financial or database tables, where you
don't know the number of rows up front.  You can easily say 'make the last row
bold and put a line above it'""")

bullet("""The style and data are separated, so you can declare a handful of table
styles and use them for a family of reports.  Styes can also 'inherit', as with
paragraphs.""")

disc("""There is however one main limitation compared to an HTML table.
They define a simple rectangular grid.  There is no simple row or column
spanning; if you need to span cells, you must nest tables inside table cells instead or use a more
complex scheme in which the lead cell of a span contains the actual contents.""")

disc("""
$Tables$ are created by passing the constructor an optional sequence of column widths,
an optional sequence of row heights, and the data in row order.
Drawing of the table can be controlled by using a $TableStyle$ instance. This allows control of the
color and weight of the lines (if any), and the font, alignment and padding of the text.
A primitive automatic row height and or column width calculation mechanism is provided for.
""")

heading2('$Table$ User Methods')
disc("""These are the main methods which are of interest to the client programmer.""")

heading4("""$Table(data, colWidths=None, rowHeights=None, style=None, splitByRow=1,
repeatRows=0, repeatCols=0)$""")

disc("""The $data$ argument is a sequence of sequences of cell values each of which
should be convertible to a string value using the $str$ function or should be a Flowable instance (such as a $Paragraph$) or a list (or tuple) of such instances.
If a cell value is a $Flowable$ or list of $Flowables$ these must either have a determined width
or the containing column must have a fixed width.
The first row of cell values
is in $data[0]$ i.e. the values are in row order. The $i$, $j$<sup>th.</sup> cell value is in
$data[i][j]$. Newline characters $'\\n'$ in cell values are treated as line split characters and
are used at <i>draw</i> time to format the cell into lines.
""")
disc("""The other arguments are fairly obvious, the $colWidths$ argument is a sequence
of numbers or possibly $None$, representing the widths of the columns. The number of elements
in $colWidths$ determines the number of columns in the table.
A value of $None$ means that the corresponding column width should be calculated automatically.""")

disc("""The $rowHeights$ argument is a sequence
of numbers or possibly $None$, representing the heights of the rows. The number of elements
in $rowHeights$ determines the number of rows in the table.
A value of $None$ means that the corresponding row height should be calculated automatically.""")

disc("""The $style$ argument can be an initial style for the table.""")
disc("""The $splitByRow$ argument is only needed for tables both too tall and too wide
to fit in the current context.  In this case you must decide whether to 'tile'
down and across, or across and then down.  This parameter is a Boolean indicating that the
$Table$ should split itself
by row before attempting to split itself by column when too little space is available in
the current drawing area and the caller wants the $Table$ to split.""")

disc("""The $repeatRows$ and $repeatCols$ arguments specify the number of leading rows and columns
that should be repeated when the $Table$ is asked to split itself.""")
heading4('$Table.setStyle(tblStyle)$')
disc("""
This method applies a particular instance of class $TableStyle$ (discussed below)
to the $Table$ instance. This is the only way to get $tables$ to appear
in a nicely formatted way.
""")
disc("""
Successive uses of the $setStyle$ method apply the styles in an additive fashion.
That is, later applications override earlier ones where they overlap.
""")

heading2('$TableStyle$')
disc("""
This class is created by passing it a sequence of <i>commands</i>, each command
is a tuple identified by its first element which is a string; the remaining
elements of the command tuple represent the start and stop cell coordinates
of the command and possibly thickness and colors, etc.
""")
heading2("$TableStyle$ User Methods")
heading3("$TableStyle(commandSequence)$")
disc("""The creation method initializes the $TableStyle$ with the argument
command sequence as an example:""")
eg("""
    LIST_STYLE = TableStyle(
        [('LINEABOVE', (0,0), (-1,0), 2, colors.green),
        ('LINEABOVE', (0,1), (-1,-1), 0.25, colors.black),
        ('LINEBELOW', (0,-1), (-1,-1), 2, colors.green),
        ('ALIGN', (1,1), (-1,-1), 'RIGHT')]
        )
""")
heading3("$TableStyle.add(commandSequence)$")
disc("""This method allows you to add commands to an existing
$TableStyle$, i.e. you can build up $TableStyles$ in multiple statements.
""")
eg("""
    LIST_STYLE.add('BACKGROUND', (0,0), (-1,0), colors.Color(0,0.7,0.7))
""")
heading3("$TableStyle.getCommands()$")
disc("""This method returns the sequence of commands of the instance.""")
eg("""
    cmds = LIST_STYLE.getCommands()
""")
heading2("$TableStyle$ Commands")
disc("""The commands passed to $TableStyles$ come in three main groups
which affect the table background, draw lines, or set cell styles.
""")
disc("""The first element of each command is its identifier,
the second and third arguments determine the cell coordinates of
the box of cells which are affected with negative coordinates
counting backwards from the limit values as in <b>Python</b>
indexing. The coordinates are given as
(column, row) which follows the spreadsheet 'A1' model, but not
the more natural (for mathematicians) 'RC' ordering.
The top left cell is (0, 0) the bottom right is (-1, -1). Depending on
the command various extra (???) occur at indices beginning at 3 on.
""")
heading3("""$TableStyle$ Cell Formatting Commands""")
disc("""The cell formatting commands all begin with an identifier, followed by
the start and stop cell definitions and the perhaps other arguments.
the cell formatting commands are:""")
eg("""
FONT                    - takes fontname, optional fontsize and optional leading.
FONTNAME (or FACE)      - takes fontname.
FONTSIZE (or SIZE)      - takes fontsize in points; leading may get out of sync.
LEADING                 - takes leading in points.
TEXTCOLOR               - takes a color name or (R,G,B) tuple.
ALIGNMENT (or ALIGN)    - takes one of LEFT, RIGHT and CENTRE (or CENTER) or DECIMAL.
LEFTPADDING             - takes an integer, defaults to 6.
RIGHTPADDING            - takes an integer, defaults to 6.
BOTTOMPADDING           - takes an integer, defaults to 3.
TOPPADDING              - takes an integer, defaults to 3.
BACKGROUND              - takes a color.
ROWBACKGROUNDS          - takes a list of colors to be used cyclically.
COLBACKGROUNDS          - takes a list of colors to be used cyclically.
VALIGN                  - takes one of TOP, MIDDLE or the default BOTTOM
""")
disc("""This sets the background cell color in the relevant cells.
The following example shows the $BACKGROUND$, and $TEXTCOLOR$ commands in action:""")
EmbeddedCode("""
data=  [['00', '01', '02', '03', '04'],
        ['10', '11', '12', '13', '14'],
        ['20', '21', '22', '23', '24'],
        ['30', '31', '32', '33', '34']]
t=Table(data)
t.setStyle(TableStyle([('BACKGROUND',(1,1),(-2,-2),colors.green),
                        ('TEXTCOLOR',(0,0),(1,-1),colors.red)]))
""")
disc("""To see the effects of the alignment styles we need  some widths
and a grid, but it should be easy to see where the styles come from.""")
EmbeddedCode("""
data=  [['00', '01', '02', '03', '04'],
        ['10', '11', '12', '13', '14'],
        ['20', '21', '22', '23', '24'],
        ['30', '31', '32', '33', '34']]
t=Table(data,5*[0.4*inch], 4*[0.4*inch])
t.setStyle(TableStyle([('ALIGN',(1,1),(-2,-2),'RIGHT'),
                        ('TEXTCOLOR',(1,1),(-2,-2),colors.red),
                        ('VALIGN',(0,0),(0,-1),'TOP'),
                        ('TEXTCOLOR',(0,0),(0,-1),colors.blue),
                        ('ALIGN',(0,-1),(-1,-1),'CENTER'),
                        ('VALIGN',(0,-1),(-1,-1),'MIDDLE'),
                        ('TEXTCOLOR',(0,-1),(-1,-1),colors.green),
                        ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
                        ('BOX', (0,0), (-1,-1), 0.25, colors.black),
                        ]))
""")
heading3("""$TableStyle$ Line Commands""")
disc("""
    Line commands begin with the identifier, the start and stop cell coordinates
    and always follow this with the thickness (in points) and color of the desired lines. Colors can be names,
    or they can be specified as a (R, G, B) tuple, where R, G and B are floats and (0, 0, 0) is black. The line
    command names are: GRID, BOX, OUTLINE, INNERGRID, LINEBELOW, LINEABOVE, LINEBEFORE
    and LINEAFTER. BOX and OUTLINE are equivalent, and GRID is the equivalent of applying both BOX and
    INNERGRID.
""")
CPage(4.0)
disc("""We can see some line commands in action with the following example.
""")
EmbeddedCode("""
data=  [['00', '01', '02', '03', '04'],
        ['10', '11', '12', '13', '14'],
        ['20', '21', '22', '23', '24'],
        ['30', '31', '32', '33', '34']]
t=Table(data,style=[('GRID',(1,1),(-2,-2),1,colors.green),
                    ('BOX',(0,0),(1,-1),2,colors.red),
                    ('LINEABOVE',(1,2),(-2,2),1,colors.blue),
                    ('LINEBEFORE',(2,1),(2,-2),1,colors.pink),
                    ])
""")
disc("""Line commands cause problems for tables when they split; the following example
shows a table being split in various positions""")
EmbeddedCode("""
data=  [['00', '01', '02', '03', '04'],
        ['10', '11', '12', '13', '14'],
        ['20', '21', '22', '23', '24'],
        ['30', '31', '32', '33', '34']]
t=Table(data,style=[
                ('GRID',(0,0),(-1,-1),0.5,colors.grey),
                ('GRID',(1,1),(-2,-2),1,colors.green),
                ('BOX',(0,0),(1,-1),2,colors.red),
                ('BOX',(0,0),(-1,-1),2,colors.black),
                ('LINEABOVE',(1,2),(-2,2),1,colors.blue),
                ('LINEBEFORE',(2,1),(2,-2),1,colors.pink),
                ('BACKGROUND', (0, 0), (0, 1), colors.pink),
                ('BACKGROUND', (1, 1), (1, 2), colors.lavender),
                ('BACKGROUND', (2, 2), (2, 3), colors.orange),
                ])
""")
t=getStory()[-1]
getStory().append(Spacer(0,6))
for s in t.split(4*inch,30):
    getStory().append(s)
    getStory().append(Spacer(0,6))
getStory().append(Spacer(0,6))
for s in t.split(4*inch,36):
    getStory().append(s)
    getStory().append(Spacer(0,6))

disc("""When unsplit and split at the first or second row.""")

CPage(4.0)
heading3("""Complex Cell Values""")
disc("""
As mentioned above we can have complicated cell values including $Paragraphs$, $Images$ and other $Flowables$
or lists of the same. To see this in operation consider the following code and the table it produces.
Note that the $Image$ has a white background which will obscure any background you choose for the cell.
To get better results you should use a transparent background.
""")
import os, reportlab.platypus
I = '../images/replogo.gif'
EmbeddedCode("""
I = Image('%s')
I.drawHeight = 1.25*inch*I.drawHeight / I.drawWidth
I.drawWidth = 1.25*inch
P0 = Paragraph('''
               <b>A pa<font color=red>r</font>a<i>graph</i></b>
               <super><font color=yellow>1</font></super>''',
               styleSheet["BodyText"])
P = Paragraph('''
       <para align=center spaceb=3>The <b>ReportLab Left
       <font color=red>Logo</font></b>
       Image</para>''',
       styleSheet["BodyText"])
data=  [['A',   'B', 'C',     P0, 'D'],
        ['00', '01', '02', [I,P], '04'],
        ['10', '11', '12', [P,I], '14'],
        ['20', '21', '22',  '23', '24'],
        ['30', '31', '32',  '33', '34']]

t=Table(data,style=[('GRID',(1,1),(-2,-2),1,colors.green),
                    ('BOX',(0,0),(1,-1),2,colors.red),
                    ('LINEABOVE',(1,2),(-2,2),1,colors.blue),
                    ('LINEBEFORE',(2,1),(2,-2),1,colors.pink),
                    ('BACKGROUND', (0, 0), (0, 1), colors.pink),
                    ('BACKGROUND', (1, 1), (1, 2), colors.lavender),
                    ('BACKGROUND', (2, 2), (2, 3), colors.orange),
                    ('BOX',(0,0),(-1,-1),2,colors.black),
                    ('GRID',(0,0),(-1,-1),0.5,colors.black),
                    ('VALIGN',(3,0),(3,0),'BOTTOM'),
                    ('BACKGROUND',(3,0),(3,0),colors.limegreen),
                    ('BACKGROUND',(3,1),(3,1),colors.khaki),
                    ('ALIGN',(3,1),(3,1),'CENTER'),
                    ('BACKGROUND',(3,2),(3,2),colors.beige),
                    ('ALIGN',(3,2),(3,2),'LEFT'),
                    ])

t._argW[3]=1.5*inch
"""%I)
heading3("""$TableStyle$ Span Commands""")
disc("""Our $Table$ classes support the concept of spanning, but it isn't specified in the same way
as html. The style specification
""")
eg("""
SPAN, (sc,sr), (ec,er)
""")
disc("""indicates that the cells in columns $sc$ - $ec$ and rows $sr$ - $er$ should be combined into a super cell
with contents determined by the cell $(sc, sr)$. The other cells should be present, but should contain empty strings 
or you may get unexpected results.
""")
EmbeddedCode("""
data=  [['Top\\nLeft', '', '02', '03', '04'],
        ['', '', '12', '13', '14'],
        ['20', '21', '22', 'Bottom\\nRight', ''],
        ['30', '31', '32', '', '']]
t=Table(data,style=[
                ('GRID',(0,0),(-1,-1),0.5,colors.grey),
                ('BACKGROUND',(0,0),(1,1),colors.palegreen),
                ('SPAN',(0,0),(1,1)),
                ('BACKGROUND',(-2,-2),(-1,-1), colors.pink),
                ('SPAN',(-2,-2),(-1,-1)),
                ])
""")

disc("""notice that we don't need to be conservative with our $GRID$ command. The spanned cells are not drawn through.
""")
heading3("""Special $TableStyle$ Indeces""")
disc("""In any style command the first row index may be set to one of the special strings
$'splitlast'$ or $'splitfirst'$ to indicate that the style should be used only for the last row of
a split table, or the first row of a continuation. This allows splitting tables with nicer effects around the split.""")  

heading1("""Other Useful $Flowables$""")
heading2("""$Preformatted(text, style, bulletText = None, dedent=0)$""")
disc("""
Creates a preformatted paragraph which does no wrapping, line splitting or other manipulations.
No $XML$ style tags are taken account of in the text.
If dedent is non zero $dedent$ common leading
spaces will be removed from the front of each line.
""")
heading2("""$XPreformatted(text, style, bulletText = None, dedent=0, frags=None)$""")
disc("""
This is a non rearranging form of the $Paragraph$ class; $XML$ tags are allowed in
$text$ and have the same meanings as for the $Paragraph$ class.
As for $Preformatted$, if dedent is non zero $dedent$ common leading
spaces will be removed from the front of each line.
""")
EmbeddedCode("""
from reportlab.lib.styles import getSampleStyleSheet
stylesheet=getSampleStyleSheet()
normalStyle = stylesheet['Normal']
text='''

   This is a non rearranging form of the <b>Paragraph</b> class;
   <b><font color=red>XML</font></b> tags are allowed in <i>text</i> and have the same

      meanings as for the <b>Paragraph</b> class.
   As for <b>Preformatted</b>, if dedent is non zero <font color=red size=+1>dedent</font>
       common leading spaces will be removed from the
   front of each line.
   You can have &amp;amp; style entities as well for &amp; &lt; &gt; and &quot;.

'''
t=XPreformatted(text,normalStyle,dedent=3)
""")
heading2("""$Image(filename, width=None, height=None)$""")
disc("""Create a flowable which will contain the image defined by the data in file $filename$.
The default <b>PDF</b> image type <i>jpeg</i> is supported and if the <b>PIL</b> extension to <b>Python</b>
is installed the other image types can also be handled. If $width$ and or $height$ are specified
then they determine the dimension of the displayed image in <i>points</i>. If either dimension is
not specified (or specified as $None$) then the corresponding pixel dimension of the image is assumed
to be in <i>points</i> and used.
""")
I=os.path.join(os.path.dirname(reportlab.__file__),'docs','images','lj8100.jpg')
eg("""
Image("lj8100.jpg")
""",after=0.1)
disc("""will display as""")
try:
    getStory().append(Image(I))
except:
    disc("""An image should have appeared here.""")
disc("""whereas""")
eg("""
im = Image("lj8100.jpg", width=2*inch, height=2*inch)
im.hAlign = 'CENTER'
""", after=0.1)
disc('produces')
try:
    im = Image(I, width=2*inch, height=2*inch)
    im.hAlign = 'CENTER'
    getStory().append(Image(I, width=2*inch, height=2*inch))
except:
    disc("""An image should have appeared here.""")
heading2("""$Spacer(width, height)$""")
disc("""This does exactly as would be expected; it adds a certain amount of space into the story.
At present this only works for vertical space.
""")
CPage(1)
heading2("""$PageBreak()$""")
disc("""This $Flowable$ represents a page break. It works by effectively consuming all vertical
space given to it. This is sufficient for a single $Frame$ document, but would only be a
frame break for multiple frames so the $BaseDocTemplate$ mechanism
detects $pageBreaks$ internally and handles them specially.
""")
CPage(1)
heading2("""$CondPageBreak(height)$""")
disc("""This $Flowable$ attempts to force a $Frame$ break if insufficient vertical space remains
in the current $Frame$. It is thus probably wrongly named and should probably be renamed as
$CondFrameBreak$.
""")
CPage(1)
heading2("""$KeepTogether(flowables)$""")
disc("""
This compound $Flowable$ takes a list of $Flowables$ and attempts to keep them in the same $Frame$.
If the total height of the $Flowables$ in the list $flowables$ exceeds the current frame's available
space then all the space is used and a frame break is forced.
""")
