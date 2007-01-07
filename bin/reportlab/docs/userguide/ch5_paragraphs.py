#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/docs/userguide/ch5_paragraphs.py
from reportlab.tools.docco.rl_doc_utils import *

#begin chapter oon paragraphs
heading1("Paragraphs")
disc("""
The $reportlab.platypus.Paragraph$ class is one of the most useful of the Platypus $Flowables$;
it can format fairly arbitrary text and provides for inline font style and colour changes using
an XML style markup. The overall shape of the formatted text can be justified, right or left ragged
or centered. The XML markup can even be used to insert greek characters or to do subscripts.
""")
disc("""The following text creates an instance of the $Paragraph$ class:""")
eg("""Paragraph(text, style, bulletText=None)""")
disc("""The $text$ argument contains the text of the
paragraph; excess white space is removed from the text at the ends and internally after
linefeeds. This allows easy use of indented triple quoted text in <b>Python</b> scripts.
The $bulletText$ argument provides the text of a default bullet for the paragraph.
The font and other properties for the paragraph text and bullet are set using the style argument.
""")
disc("""
The $style$ argument should be an instance of class $ParagraphStyle$ obtained typically
using""")
eg("""
from reportlab.lib.styles import ParagraphStyle
""")
disc("""
this container class provides for the setting of multiple default paragraph attributes
in a structured way. The styles are arranged in a dictionary style object called a $stylesheet$
which allows for the styles to be accessed as $stylesheet['BodyText']$. A sample style
sheet is provided.
""")
eg("""
from reportlab.lib.styles import getSampleStyleSheet
stylesheet=getSampleStyleSheet()
normalStyle = stylesheet['Normal']
""")
disc("""
The options which can be set for a $Paragraph$ can be seen from the $ParagraphStyle$ defaults.
""")
heading4("$class ParagraphStyle$")
eg("""
class ParagraphStyle(PropertySet):
    defaults = {
        'fontName':'Times-Roman',
        'fontSize':10,
        'leading':12,
        'leftIndent':0,
        'rightIndent':0,
        'firstLineIndent':0,
        'alignment':TA_LEFT,
        'spaceBefore':0,
        'spaceAfter':0,
        'bulletFontName':'Times-Roman',
        'bulletFontSize':10,
        'bulletIndent':0,
        'textColor': black
        }
""")

heading2("Using Paragraph Styles")

#this will be used in the ParaBox demos.
sample = """You are hereby charged that on the 28th day of May, 1970, you did
willfully, unlawfully, and with malice of forethought, publish an
alleged English-Hungarian phrase book with intent to cause a breach
of the peace.  How do you plead?"""


disc("""The $Paragraph$ and $ParagraphStyle$ classes together
handle most common formatting needs. The following examples
draw paragraphs in various styles, and add a bounding box
so that you can see exactly what space is taken up.""")

s1 = ParagraphStyle('Normal')
parabox(sample, s1, 'The default $ParagraphStyle$')

disc("""The two attributes $spaceBefore$ and $spaceAfter$ do what they
say, except at the top or bottom of a frame. At the top of a frame,
$spaceBefore$ is ignored, and at the bottom, $spaceAfter$ is ignored.
This means that you could specify that a 'Heading2' style had two
inches of space before when it occurs in mid-page, but will not
get acres of whitespace at the top of a page.  These two attributes
should be thought of as 'requests' to the Frame and are not part
of the space occupied by the Paragraph itself.""")

disc("""The $fontSize$ and $fontName$ tags are obvious, but it is
important to set the $leading$.  This is the spacing between
adjacent lines of text; a good rule of thumb is to make this
20% larger than the point size.  To get double-spaced text,
use a high $leading$.""")

disc("""The figure below shows space before and after and an
increased leading:""")

parabox(sample,
        ParagraphStyle('Spaced',
                       spaceBefore=6,
                       spaceAfter=6,
                       leading=16),
        'Space before and after and increased leading'
        )

disc("""The $leftIndent$ and $rightIndent$ attributes do exactly
what you would expect; $firstLineIndent$ is added to the $leftIndent$ of the
first line. If you want a straight left edge, remember
to set $firstLineIndent$ equal to 0.""")

parabox(sample,
        ParagraphStyle('indented',
                       firstLineIndent=+24,
                       leftIndent=24,
                       rightIndent=24),
        'one third inch indents at left and right, two thirds on first line'
        )

disc("""Setting $firstLineIndent$ equal to a negative number, $leftIndent$
much higher, and using a
different font (we'll show you how later!) can give you a
definition list:.""")

parabox('<b><i>Judge Pickles: </i></b>' + sample,
        ParagraphStyle('dl',
                       leftIndent=36),
        'Definition Lists'
        )

disc("""There are four possible values of $alignment$, defined as
constants in the module <i>reportlab.lib.enums</i>.  These are
TA_LEFT, TA_CENTER or TA_CENTRE, TA_RIGHT and
TA_JUSTIFY, with values of 0, 1, 2 and 4 respectively.  These
do exactly what you would expect.""")


heading2("Paragraph XML Markup Tags")
disc("""XML markup can be used to modify or specify the
overall paragraph style, and also to specify intra-
paragraph markup.""")

heading3("The outermost &lt; para &gt; tag")


disc("""
The paragraph text may optionally be surrounded by
&lt;para attributes....&gt;
&lt;/para&gt;
tags. The attributes if any of the opening &lt;para&gt; tag affect the style that is used
with the $Paragraph$ $text$ and/or $bulletText$.
""")
disc(" ")

from reportlab.platypus.paraparser import _addAttributeNames, _paraAttrMap, _bulletAttrMap

def getAttrs(A):
    _addAttributeNames(A)
    S={}
    for k, v in A.items():
        a = v[0]
        if not S.has_key(a):
            S[a] = k
        else:
            S[a] = "%s, %s" %(S[a],k)

    K = S.keys()
    K.sort()
    D=[('Attribute','Synonyms')]
    for k in K:
        D.append((k,S[k]))
    cols=2*[None]
    rows=len(D)*[None]
    return D,cols,rows

t=apply(Table,getAttrs(_paraAttrMap))
t.setStyle(TableStyle([
            ('FONT',(0,0),(-1,1),'Times-Bold',10,12),
            ('FONT',(0,1),(-1,-1),'Courier',8,8),
            ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
            ('BOX', (0,0), (-1,-1), 0.25, colors.black),
            ]))
getStory().append(t)
caption("""Table <seq template="%(Chapter)s-%(Table+)s"/> - Synonyms for style attributes""")

disc("""Some useful synonyms have been provided for our Python attribute
names, including lowercase versions, and the equivalent properties
from the HTML standard where they exist.  These additions make
it much easier to build XML-printing applications, since
much intra-paragraph markup may not need translating. The
table below shows the allowed attributes and synonyms in the
outermost paragraph tag.""")


heading2("Intra-paragraph markup")
disc("""'<![CDATA[Within each paragraph, we use a basic set of XML tags
to provide markup.  The most basic of these are bold (<b>...</b>)
and italic (<i>...</i>).  It is also legal to use an underline
tag (<u>...</u> but it has no effect; PostScript fonts don't
support underlining, and neither do we, yet.]]>""")

parabox2("""<b>You are hereby charged</b> that on the 28th day of May, 1970, you did
willfully, unlawfully, and <i>with malice of forethought</i>, publish an
alleged English-Hungarian phrase book with intent to cause a breach
of the peace.  <u>How do you plead</u>?""", "Simple bold and italic tags")

heading3("The $&lt;font&gt;$ tag")
disc("""The $&lt;font&gt;$ tag can be used to change the font name,
size and text color for any substring within the paragraph.
Legal attributes are $size$, $face$, $name$ (which is the same as $face$),
$color$, and $fg$ (which is the same as $color$). The $name$ is
the font family name, without any 'bold' or 'italic' suffixes.
Colors may be
HTML color names or a hex string encoded in a variety of ways;
see ^reportlab.lib.colors^ for the formats allowed.""")

parabox2("""<font face="times" color="red">
You are hereby charged</font> that on the 28th day of May, 1970, you did
willfully, unlawfully, and <font size=14>with malice of forethought</font>,
publish an
alleged English-Hungarian phrase book with intent to cause a breach
of the peace.  How do you plead?""", "The $font$ tag")

heading3("Superscripts and Subscripts")
disc("""Superscripts and subscripts are supported with the
<![CDATA[<super> and <sub> tags, which work exactly
as you might expect.  In addition, most greek letters
can be accessed by using the <greek></greek>
tag, or with mathML entity names.]]>""")

##parabox2("""<greek>epsilon</greek><super><greek>iota</greek>
##<greek>pi</greek></super> = -1""", "Greek letters and subscripts")

parabox2("""Equation (&alpha;): <greek>e</greek> <super><greek>ip</greek></super>  = -1""",
         "Greek letters and superscripts")

heading3("Numbering Paragraphs and Lists")
disc("""The $&lt;seq&gt;$ tag provides comprehensive support
for numbering lists, chapter headings and so on.  It acts as
an interface to the $Sequencer$ class in ^reportlab.lib.sequencer^.
These are used to number headings and figures throughout this
document.
You may create as many separate 'counters' as you wish, accessed
with the $id$ attribute; these will be incremented by one each
time they are accessed.  The $seqreset$ tag resets a counter.
If you want it to resume from a number other than 1, use
the syntax &lt;seqreset id="mycounter" base="42"&gt;.
Let's have a go:""")

parabox2("""<seq id="spam"/>, <seq id="spam"/>, <seq id="spam"/>.
Reset<seqreset id="spam"/>.  <seq id="spam"/>, <seq id="spam"/>,
<seq id="spam"/>.""",  "Basic sequences")

disc("""You can save specifying an ID by designating a counter ID
as the <i>default</i> using the &lt;seqdefault id="Counter"&gt;
tag; it will then be used whenever a counter ID
is not specified.  This saves some typing, especially when
doing multi-level lists; you just change counter ID when
stepping in or out a level.""")

parabox2("""<seqdefault id="spam"/>Continued... <seq/>,
<seq/>, <seq/>, <seq/>, <seq/>, <seq/>, <seq/>.""",
"The default sequence")

disc("""Finally, one can access multi-level sequences using
a variation of Python string formatting and the $template$
attribute in a &lt;seq&gt; tags.  This is used to do the
captions in all of the figures, as well as the level two
headings.  The substring $%(counter)s$ extracts the current
value of a counter without incrementing it; appending a
plus sign as in $%(counter)s$ increments the counter.
The figure captions use a pattern like the one below:""")

parabox2("""Figure <seq template="%(Chapter)s-%(FigureNo+)s"/> - Multi-level templates""",
"Multi-level templates")

disc("""We cheated a little - the real document used 'Figure',
but the text above uses 'FigureNo' - otherwise we would have
messed up our numbering!""")

heading2("Bullets and Paragraph Numbering")
disc("""In addition to the three indent properties, some other
parameters are needed to correctly handle bulleted and numbered
lists.  We discuss this here because you have now seen how
to handle numbering.  A paragraph may have an optional
^bulletText^ argument passed to its constructor; alternatively,
bullet text may be placed in a $<![CDATA[<bullet>..</bullet>]]>$
tag at its head.  The text will be drawn on the first line of
the paragraph, with its x origin determined by the $bulletIndent$
attribute of the style, and in the font given in the
$bulletFontName$ attribute.  For genuine bullets, a good
idea is to select the Times-Roman font in the style, and
use a character such as $\\xe2\\x80\\xa2)$:""")

t=apply(Table,getAttrs(_bulletAttrMap))
t.setStyle([
            ('FONT',(0,0),(-1,1),'Times-Bold',10,12),
            ('FONT',(0,1),(-1,-1),'Courier',8,8),
            ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
            ('BOX', (0,0), (-1,-1), 0.25, colors.black),
            ])
getStory().append(t)

caption("""Table <seq template="%(Chapter)s-%(Table+)s"/> - &lt;bullet&gt; attributes &amp; synonyms""")
disc("""The &lt;bullet&gt; tag is only allowed once in a given paragraph and its use
overrides the implied bullet style and ^bulletText^ specified in the  ^Paragraph^
creation.
""")
parabox("""<bullet>\xe2\x80\xa2</bullet>this is a bullet point.  Spam
spam spam spam spam spam spam spam spam spam spam spam
spam spam spam spam spam spam spam spam spam spam """,
        styleSheet['Bullet'],
        'Basic use of bullet points')

disc("""Exactly the same technique is used for numbers,
except that a sequence tag is used.  It is also possible
to put  a multi-character string in the bullet; with a deep
indent and bold bullet font, you can make a compact
definition list.""")
