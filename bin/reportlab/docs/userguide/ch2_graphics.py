#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/docs/userguide/ch2_graphics.py
from reportlab.tools.docco.rl_doc_utils import *
from reportlab.lib.codecharts import SingleByteEncodingChart

heading1("Graphics and Text with $pdfgen$")

heading2("Basic Concepts")
disc("""
The $pdfgen$ package is the lowest level interface for
generating PDF documents.  A $pdfgen$ program is essentially
a sequence of instructions for "painting" a document onto
a sequence of pages.  The interface object which provides the
painting operations is the $pdfgen canvas$.
""")

disc("""
The canvas should be thought of as a sheet of white paper
with points on the sheet identified using Cartesian ^(X,Y)^ coordinates
which by default have the ^(0,0)^ origin point at the lower
left corner of the page.  Furthermore the first coordinate ^x^
goes to the right and the second coordinate ^y^ goes up, by
default.""")

disc("""
A simple example
program that uses a canvas follows.
""")

eg("""
    from reportlab.pdfgen import canvas
    def hello(c):
        c.drawString(100,100,"Hello World")
    c = canvas.Canvas("hello.pdf")
    hello(c)
    c.showPage()
    c.save()
""")

disc("""
The above code creates a $canvas$ object which will generate
a PDF file named $hello.pdf$ in the current working directory.
It then calls the $hello$ function passing the $canvas$ as an argument.
Finally the $showPage$ method saves the current page of the canvas
and the $save$ method stores the file and closes the canvas.""")

disc("""
The $showPage$ method causes the $canvas$ to stop drawing on the
current page and any further operations will draw on a subsequent
page (if there are any further operations -- if not no
new page is created).  The $save$ method must be called after the
construction of the document is complete -- it generates the PDF
document, which is the whole purpose of the $canvas$ object.
""")

heading2("More about the Canvas")
disc("""
Before describing the drawing operations, we will digress to cover
some of the things which can be done to configure a canvas.  There
are many different settings available.  If you are new to Python
or can't wait to produce some output, you can skip ahead, but
come back later and read this!""")

disc("""First of all, we will look at the constructor
arguments for the canvas:""")
eg("""    def __init__(self,filename,
                 pagesize=(595.27,841.89),
                 bottomup = 1,
                 pageCompression=0,
                 encoding=rl_config.defaultEncoding,
                 verbosity=0):
                 """)

disc("""The $filename$ argument controls the
name of the final PDF file.  You
may also pass in any open file object (such as $sys.stdout$, the python process standard output)
and the PDF document will be written to that.  Since PDF
is a binary format, you should take care when writing other
stuff before or after it; you can't deliver PDF documents
inline in the middle of an HTML page!""")

disc("""The $pagesize$ argument is a tuple of two numbers
in points (1/72 of an inch). The canvas defaults to $A4$ (an international standard
page size which differs from the American standard page size of $letter$),
but it is better to explicitly specify it.  Most common page
sizes are found in the library module $reportlab.lib.pagesizes$,
so you can use expressions like""")

eg("""from reportlab.lib.pagesizes import letter, A4
myCanvas = Canvas('myfile.pdf', pagesize=letter)
width, height = letter  #keep for later
""")

pencilnote()

disc("""If you have problems printing your document make sure you
are using the right page size (usually either $A4$ or $letter$).
Some printers do not work well with pages that are too large or too small.""")

disc("""Very often, you will want to calculate things based on
the page size.  In the example above we extracted the width and
height.  Later in the program we may use the $width$ variable to
define a right margin as $width - inch$ rather than using
a constant.  By using variables the margin will still make sense even
if the page size changes.""")

disc("""The $bottomup$ argument
switches coordinate systems.  Some graphics systems (like PDF
and PostScript) place (0,0) at the bottom left of the page
others (like many graphical user interfaces [GUI's]) place the origen at the top left.  The
$bottomup$ argument is deprecated and may be dropped in future""")

todo("""Need to see if it really works for all tasks, and if not
     then get rid of it""")

disc("""The $pageCompression$ option determines whether the stream
of PDF operations for each page is compressed.  By default
page streams are not compressed, because the compression slows the file generation process.
If output size is important set $pageCompression=1$, but remember that, compressed documents will
be smaller, but slower to generate.  Note that images are <i>always</i> compressed, and this option
will only save space if you have a very large amount of text and vector graphics
on each page.""")

disc("""The $encoding$ argument is largely obsolete in version 2.0 and can
probably be omitted by 99% of users.  Its default value is fine unless you
very specifically need to use one of the 25 or so characters which are present
in MacRoman and not in Winansi.  A useful reference to these is here:
<font color="blue"><u><a href="http://www.alanwood.net/demos/charsetdiffs.html">http://www.alanwood.net/demos/charsetdiffs.html</a></u></font>.

The parameter determines which font encoding is used for the
standard Type 1 fonts; this should correspond to the encoding on your system.
Note that this is the encoding used <i>internally by the font</i>; text you
pass to the ReportLab toolkit for rendering should always either be a Python
unicode string object or a UTF-8 encoded byte string (see the next chapter)!
The font encoding has two values at present: $'WinAnsiEncoding'$ or
$'MacRomanEncoding'$.  The variable $rl_config.defaultEncoding$ above points
to the former, which is standard on Windows, Mac OS X and many Unices
(including Linux). If you are Mac user and don't have OS X, you may want to
make a global change: modify the line at the top of
<i>reportlab/pdfbase/pdfdoc.py</i> to switch it over.  Otherwise, you can
probably just ignore this argument completely and never pass it.  For all TTF
and the commonly-used CID fonts, the encoding you pass in here is ignored,
since the reportlab library itself knows the right encodings in those
cases.""")

disc("""The demo script $reportlab/demos/stdfonts.py$
will print out two test documents showing all code points
in all fonts, so you can look up characters.  Special
characters can be inserted into string commands with
the usual Python escape sequences; for example \\101 = 'A'.""")

disc("""The $verbosity$ argument determines how much log
information is printed.  By default, it is zero to assist
applications which want to capture PDF from standard output.
With a value of 1, you will get a confirmation message
each time a document is generated.  Higher numbers may
give more output in future.""")

todo("to do - all the info functions and other non-drawing stuff")





todo("""Cover all constructor arguments, and setAuthor etc.""")

heading2("Drawing Operations")
disc("""
Suppose the $hello$ function referenced above is implemented as
follows (we will not explain each of the operations in detail
yet).
""")

eg(examples.testhello)

disc("""
Examining this code notice that there are essentially two types
of operations performed using a canvas.  The first type draws something
on the page such as a text string or a rectangle or a line.  The second
type changes the state of the canvas such as
changing the current fill or stroke color or changing the current font
type and size.
""")

disc("""
If we imagine the program as a painter working on
the canvas the "draw" operations apply paint to the canvas using
the current set of tools (colors, line styles, fonts, etcetera)
and the "state change" operations change one of the current tools
(changing the fill color from whatever it was to blue, or changing
the current font to $Times-Roman$ in 15 points, for example).
""")

disc("""
The document generated by the "hello world" program listed above would contain
the following graphics.
""")

illust(examples.hello, '"Hello World" in pdfgen')

heading3("About the demos in this document")

disc("""
This document contains demonstrations of the code discussed like the one shown
in the rectangle above.  These demos are drawn on a "tiny page" embedded
within the real pages of the guide.  The tiny pages are %s inches wide
and %s inches tall. The demo displays show the actual output of the demo code.
For convenience the size of the output has been reduced slightly.
""" % (examplefunctionxinches, examplefunctionyinches))

heading2('The tools: the "draw" operations')

disc("""
This section briefly lists the tools available to the program
for painting information onto a page using the canvas interface.
These will be discussed in detail in later sections.  They are listed
here for easy reference and for summary purposes.
""")

heading3("Line methods")

eg("""canvas.line(x1,y1,x2,y2)""")
eg("""canvas.lines(linelist)""")

disc("""
The line methods draw straight line segments on the canvas.
""")

heading3("Shape methods")

eg("""canvas.grid(xlist, ylist) """)
eg("""canvas.bezier(x1, y1, x2, y2, x3, y3, x4, y4)""")
eg("""canvas.arc(x1,y1,x2,y2) """)
eg("""canvas.rect(x, y, width, height, stroke=1, fill=0) """)
eg("""canvas.ellipse(x1,y1, x2,y2, stroke=1, fill=0)""")
eg("""canvas.wedge(x1,y1, x2,y2, startAng, extent, stroke=1, fill=0) """)
eg("""canvas.circle(x_cen, y_cen, r, stroke=1, fill=0)""")
eg("""canvas.roundRect(x, y, width, height, radius, stroke=1, fill=0) """)

disc("""
The shape methods draw common complex shapes on the canvas.
""")

heading3("String drawing methods")

eg("""canvas.drawString(x, y, text):""")
eg("""canvas.drawRightString(x, y, text) """)
eg("""canvas.drawCentredString(x, y, text)""")

disc("""
The draw string methods draw single lines of text on the canvas.
""")

heading3("The text object methods")
eg("""textobject = canvas.beginText(x, y) """)
eg("""canvas.drawText(textobject) """)

disc("""
Text objects are used to format text in ways that
are not supported directly by the $canvas$ interface.
A program creates a text object from the $canvas$ using $beginText$
and then formats text by invoking $textobject$ methods.
Finally the $textobject$ is drawn onto the canvas using
$drawText$.
""")

heading3("The path object methods")

eg("""path = canvas.beginPath() """)
eg("""canvas.drawPath(path, stroke=1, fill=0) """)
eg("""canvas.clipPath(path, stroke=1, fill=0) """)

disc("""
Path objects are similar to text objects: they provide dedicated control
for performing complex graphical drawing not directly provided by the
canvas interface.  A program creates a path object using $beginPath$
populates the path with graphics using the methods of the path object
and then draws the path on the canvas using $drawPath$.""")

disc("""It is also possible
to use a path as a "clipping region" using the $clipPath$ method -- for example a circular path
can be used to clip away the outer parts of a rectangular image leaving
only a circular part of the image visible on the page.
""")

heading3("Image methods")
pencilnote()
disc("""
You need the Python Imaging Library (PIL) to use images with the ReportLab package.
Examnples of the techniques below can be found by running the script $test_pdfgen_general.py$
in our $test$ subdirectory and looking at page 7 of the output.
""")

disc("""
There are two similar-sounding ways to draw images.  The preferred one is
the $drawImage$ method.  This implements a caching system so you can
define an image once and draw it many times; it will only be
stored once in the PDF file.  $drawImage$ also exposes one advanced parameter,
a transparency mask, and will expose more in future.  The older technique,
$drawInlineImage$, stores bitmaps within the page stream and is thus very
inefficient if you use the same image more than once in a document; but can result
in PDFs which render faster if the images are very small and not repeated. We'll
discuss the oldest one first:
""")

eg("""canvas.drawInlineImage(self, image, x,y, width=None,height=None) """)

disc("""
The $drawInlineImage$ method places an image on the canvas.  The $image$
parameter may be either a PIL Image object or an image filename.  Many common
file formats are accepted including GIF and JPEG.  It returns the size of the actual
image in pixels as a (width, height) tuple.
""")

eg("""canvas.drawImage(self, image, x,y, width=None,height=None,mask=None) """)
disc("""
The arguments and return value work as for $drawInlineImage$.  However, we use a caching
system; a given image will only be stored the first time it is used, and just referenced
on subsequent use.  If you supply a filename, it assumes that the same filename
means the same image.  If you supply a PIL image, it tests if the content
has actually changed before re-embedding.""")

disc("""
The $mask$ parameter lets you create transparent images.  It takes 6 numbers
and defines the range of RGB values which will be masked out or treated as
transparent. For example with [0,2,40,42,136,139], it will mask out any pixels
with a Red value from 0 or 1, Green from 40 or 41 and Blue of  136, 137 or 138
(on a scale of 0-255). It's currently your job to know which color is the
'transparent' or background one.""")

disc("""PDF allows for many image features and we will expose more of the over
time, probably with extra keyword arguments to $drawImage$.""")

heading3("Ending a page")

eg("""canvas.showPage()""")

disc("""The $showPage$ method finishes the current page.  All additional drawing will
be done on another page.""")

pencilnote()

disc("""Warning!  All state changes (font changes, color settings, geometry transforms, etcetera)
are FORGOTTEN when you advance to a new page in $pdfgen$.  Any state settings you wish to preserve
must be set up again before the program proceeds with drawing!""")

heading2('The toolbox: the "state change" operations')

disc("""
This section briefly lists the ways to switch the tools used by the
program
for painting information onto a page using the $canvas$ interface.
These too will be discussed in detail in later sections.
""")

heading3("Changing Colors")
eg("""canvas.setFillColorCMYK(c, m, y, k) """)
eg("""canvas.setStrikeColorCMYK(c, m, y, k) """)
eg("""canvas.setFillColorRGB(r, g, b) """)
eg("""canvas.setStrokeColorRGB(r, g, b) """)
eg("""canvas.setFillColor(acolor) """)
eg("""canvas.setStrokeColor(acolor) """)
eg("""canvas.setFillGray(gray) """)
eg("""canvas.setStrokeGray(gray) """)

disc("""
PDF supports three different color models: gray level, additive (red/green/blue or RGB), and
subtractive with darkness parameter (cyan/magenta/yellow/darkness or CMYK).
The ReportLab packages also provide named colors such as $lawngreen$.  There are two
basic color parameters in the graphics state: the $Fill$ color for the interior of graphic
figures and the $Stroke$ color for the boundary of graphic figures.  The above methods
support setting the fill or stroke color using any of the four color specifications.
""")

heading3("Changing Fonts")
eg("""canvas.setFont(psfontname, size, leading = None) """)

disc("""
The $setFont$ method changes the current text font to a given type and size.
The $leading$ parameter specifies the distance down to move when advancing from
one text line to the next.
""")

heading3("Changing Graphical Line Styles")

eg("""canvas.setLineWidth(width) """)
eg("""canvas.setLineCap(mode) """)
eg("""canvas.setLineJoin(mode) """)
eg("""canvas.setMiterLimit(limit) """)
eg("""canvas.setDash(self, array=[], phase=0) """)

disc("""
Lines drawn in PDF can be presented in a number of graphical styles.
Lines can have different widths, they can end in differing cap styles,
they can meet in different join styles, and they can be continuous or
they can be dotted or dashed.  The above methods adjust these various parameters.""")

heading3("Changing Geometry")

eg("""canvas.setPageSize(pair) """)
eg("""canvas.transform(a,b,c,d,e,f): """)
eg("""canvas.translate(dx, dy) """)
eg("""canvas.scale(x, y) """)
eg("""canvas.rotate(theta) """)
eg("""canvas.skew(alpha, beta) """)

disc("""
All PDF drawings fit into a specified page size.  Elements drawn outside of the specified
page size are not visible.  Furthermore all drawn elements are passed through an affine
transformation which may adjust their location and/or distort their appearence.  The
$setPageSize$ method adjusts the current page size.  The $transform$, $translate$, $scale$,
$rotate$, and $skew$ methods add additional transformations to the current transformation.
It is important to remember that these transformations are <i>incremental</i> -- a new
transform modifies the current transform (but does not replace it).
""")

heading3("State control")

eg("""canvas.saveState() """)
eg("""canvas.restoreState() """)

disc("""
Very often it is important to save the current font, graphics transform, line styles and
other graphics state in order to restore them later. The $saveState$ method marks the
current graphics state for later restoration by a matching $restoreState$.  Note that
the save and restore method invokation must match -- a restore call restores the state to
the most recently saved state which hasn't been restored yet.
You cannot save the state on one page and restore
it on the next, however -- no state is preserved between pages.""")

heading2("Other $canvas$ methods.")

disc("""
Not all methods of the $canvas$ object fit into the "tool" or "toolbox"
categories.  Below are some of the misfits, included here for completeness.
""")

eg("""
 canvas.setAuthor()
 canvas.addOutlineEntry(title, key, level=0, closed=None)
 canvas.setTitle(title)
 canvas.setSubject(subj)
 canvas.pageHasData()
 canvas.showOutline()
 canvas.bookmarkPage(name)
 canvas.bookmarkHorizontalAbsolute(name, yhorizontal)
 canvas.doForm()
 canvas.beginForm(name, lowerx=0, lowery=0, upperx=None, uppery=None)
 canvas.endForm()
 canvas.linkAbsolute(contents, destinationname, Rect=None, addtopage=1, name=None, **kw)
 canvas.getPageNumber()
 canvas.addLiteral()
 canvas.getAvailableFonts()
 canvas.stringWidth(self, text, fontName, fontSize, encoding=None)
 canvas.setPageCompression(onoff=1)
 canvas.setPageTransition(self, effectname=None, duration=1,
                        direction=0,dimension='H',motion='I')
""")


heading2('Coordinates (default user space)')

disc("""
By default locations on a page are identified by a pair of numbers.
For example the pair $(4.5*inch, 1*inch)$ identifies the location
found on the page by starting at the lower left corner and moving to
the right 4.5 inches and up one inch.
""")

disc("""For example, the following function draws
a number of elements on a $canvas$.""")

eg(examples.testcoords)

disc("""In the default user space the "origin" ^(0,0)^ point is at the lower
left corner.  Executing the $coords$ function in the default user space
(for the "demo minipage") we obtain the following.""")

illust(examples.coords, 'The Coordinate System')

heading3("Moving the origin: the $translate$ method")

disc("""Often it is useful to "move the origin" to a new point off
the lower left corner.  The $canvas.translate(^x,y^)$ method moves the origin
for the current page to the point currently identified by ^(x,y)^.""")

disc("""For example the following translate function first moves
the origin before drawing the same objects as shown above.""")

eg(examples.testtranslate)

disc("""This produces the following.""")

illust(examples.translate, "Moving the origin: the $translate$ method")


#illust(NOP) # execute some code

pencilnote()


disc("""
<i>Note:</i> As illustrated in the example it is perfectly possible to draw objects
or parts of objects "off the page".
In particular a common confusing bug is a translation operation that translates the
entire drawing off the visible area of the page.  If a program produces a blank page
it is possible that all the drawn objects are off the page.
""")

heading3("Shrinking and growing: the scale operation")

disc("""Another important operation is scaling.  The scaling operation $canvas.scale(^dx,dy^)$
stretches or shrinks the ^x^ and ^y^ dimensions by the ^dx^, ^dy^ factors respectively.  Often
^dx^ and ^dy^ are the same -- for example to reduce a drawing by half in all dimensions use
$dx = dy = 0.5$.  However for the purposes of illustration we show an example where
$dx$ and $dy$ are different.
""")

eg(examples.testscale)

disc("""This produces a "short and fat" reduced version of the previously displayed operations.""")

illust(examples.scale, "Scaling the coordinate system")


#illust(NOP) # execute some code

pencilnote()


disc("""<i>Note:</i> scaling may also move objects or parts of objects off the page,
or may cause objects to "shrink to nothing." """)

disc("""Scaling and translation can be combined, but the order of the
operations are important.""")

eg(examples.testscaletranslate)

disc("""This example function first saves the current $canvas$ state
and then does a $scale$ followed by a $translate$.  Afterward the function
restores the state (effectively removing the effects of the scaling and
translation) and then does the <i>same</i> operations in a different order.
Observe the effect below.""")

illust(examples.scaletranslate, "Scaling and Translating")


#illust(NOP) # execute some code

pencilnote()


disc("""<em>Note:</em> scaling shrinks or grows everything including line widths
so using the canvas.scale method to render a microscopic drawing in
scaled microscopic units
may produce a blob (because all line widths will get expanded a huge amount).
Also rendering an aircraft wing in meters scaled to centimeters may cause the lines
to shrink to the point where they disappear.  For engineering or scientific purposes
such as these scale and translate
the units externally before rendering them using the canvas.""")

heading3("Saving and restoring the $canvas$ state: $saveState$ and $restoreState$")

disc("""
The $scaletranslate$ function used an important feature of the $canvas$ object:
the ability to save and restore the current parameters of the $canvas$.
By enclosing a sequence of operations in a matching pair of $canvas.saveState()$
an $canvas.restoreState()$ operations all changes of font, color, line style,
scaling, translation, or other aspects of the $canvas$ graphics state can be
restored to the state at the point of the $saveState()$.  Remember that the save/restore
calls must match: a stray save or restore operation may cause unexpected
and undesirable behavior.  Also, remember that <i>no</i> $canvas$ state is
preserved across page breaks, and the save/restore mechanism does not work
across page breaks.
""")

heading3("Mirror image")

disc("""
It is interesting although perhaps not terribly useful to note that
scale factors can be negative.  For example the following function
""")

eg(examples.testmirror)

disc("""
creates a mirror image of the elements drawn by the $coord$ function.
""")

illust(examples.mirror, "Mirror Images")

disc("""
Notice that the text strings are painted backwards.
""")

heading2("Colors")

disc("""
There are four ways to specify colors in $pdfgen$: by name (using the $color$
module, by red/green/blue (additive, $RGB$) value,
by cyan/magenta/yellow/darkness (subtractive, $CMYK$), or by gray level.
The $colors$ function below exercises each of the four methods.
""")

eg(examples.testcolors)

disc("""
The $RGB$ or additive color specification follows the way a computer
screen adds different levels of the red, green, or blue light to make
any color, where white is formed by turning all three lights on full
$(1,1,1)$.""")

disc("""The $CMYK$ or subtractive method follows the way a printer
mixes three pigments (cyan, magenta, and yellow) to form colors.
Because mixing chemicals is more difficult than combining light there
is a fourth parameter for darkness.  For example a chemical
combination of the $CMY$ pigments generally never makes a perfect
black -- instead producing a muddy color -- so, to get black printers
don't use the $CMY$ pigments but use a direct black ink.  Because
$CMYK$ maps more directly to the way printer hardware works it may
be the case that colors specified in $CMYK$ will provide better fidelity
and better control when printed.
""")

illust(examples.colors, "Color Models")

heading2('Painting back to front')

disc("""
Objects may be painted over other objects to good effect in $pdfgen$.  As
in painting with oils the object painted last will show up on top.  For
example, the $spumoni$ function below paints up a base of colors and then
paints a white text over the base.
""")

eg(examples.testspumoni)

disc("""
The word "SPUMONI" is painted in white over the colored rectangles,
with the apparent effect of "removing" the color inside the body of
the word.
""")

illust(examples.spumoni, "Painting over colors")

disc("""
The last letters of the word are not visible because the default $canvas$
background is white and painting white letters over a white background
leaves no visible effect.
""")

disc("""
This method of building up complex paintings in layers can be done
in very many layers in $pdfgen$ -- there are fewer physical limitations
than there are when dealing with physical paints.
""")

eg(examples.testspumoni2)

disc("""
The $spumoni2$ function layers an ice cream cone over the
$spumoni$ drawing.  Note that different parts of the cone
and scoops layer over eachother as well.
""")
illust(examples.spumoni2, "building up a drawing in layers")


heading2('Standard fonts and text objects')

disc("""
Text may be drawn in many different colors, fonts, and sizes in $pdfgen$.
The $textsize$ function demonstrates how to change the color and font and
size of text and how to place text on the page.
""")

eg(examples.testtextsize)

disc("""
The $textsize$ function generates the following page.
""")

illust(examples.textsize, "text in different fonts and sizes")

disc("""
A number of different fonts are always available in $pdfgen$.
""")

eg(examples.testfonts)

disc("""
The $fonts$ function lists the fonts that are always available.
These don't need to be stored in a PDF document, since they
are guaranteed to be present in Acrobat Reader.
""")

illust(examples.fonts, "the 14 standard fonts")

disc("""
For information on how to use arbitrary fonts, see the next chapter.
""")


heading2("Text object methods")

disc("""
For the dedicated presentation of text in a PDF document, use a text object.
The text object interface provides detailed control of text layout parameters
not available directly at the $canvas$ level.  In addition, it results in smaller
PDF that will render faster than many separate calls to the $drawString$ methods.
""")

eg("""textobject.setTextOrigin(x,y)""")
eg("""textobject.setTextTransform(a,b,c,d,e,f)""")
eg("""textobject.moveCursor(dx, dy) # from start of current LINE""")
eg("""(x,y) = textobject.getCursor()""")
eg("""x = textobject.getX(); y = textobject.getY()""")
eg("""textobject.setFont(psfontname, size, leading = None)""")
eg("""textobject.textOut(text)""")
eg("""textobject.textLine(text='')""")
eg("""textobject.textLines(stuff, trim=1)""")

disc("""
The text object methods shown above relate to basic text geometry.
""")

disc("""
A text object maintains a text cursor which moves about the page when
text is drawn.  For example the $setTextOrigin$ places the cursor
in a known position and the $textLine$ and $textLines$ methods move
the text cursor down past the lines that have been missing.
""")

eg(examples.testcursormoves1)

disc("""
The $cursormoves$ function relies on the automatic
movement of the text cursor for placing text after the origin
has been set.
""")

illust(examples.cursormoves1, "How the text cursor moves")

disc("""
It is also possible to control the movement of the cursor
more explicitly by using the $moveCursor$ method (which moves
the cursor as an offset from the start of the current <i>line</i>
NOT the current cursor, and which also has positive ^y^ offsets
move <i>down</i> (in contrast to the normal geometry where
positive ^y^ usually moves up.
""")

eg(examples.testcursormoves2)

disc("""
Here the $textOut$ does not move the down a line in contrast
to the $textLine$ function which does move down.
""")

illust(examples.cursormoves2, "How the text cursor moves again")

heading3("Character Spacing")

eg("""textobject.setCharSpace(charSpace)""")

disc("""The $setCharSpace$ method adjusts one of the parameters of text -- the inter-character
spacing.""")

eg(examples.testcharspace)

disc("""The
$charspace$ function exercises various spacing settings.
It produces the following page.""")

illust(examples.charspace, "Adjusting inter-character spacing")

heading3("Word Spacing")

eg("""textobject.setWordSpace(wordSpace)""")

disc("The $setWordSpace$ method adjusts the space between words.")

eg(examples.testwordspace)

disc("""The $wordspace$ function shows what various word space settings
look like below.""")

illust(examples.wordspace, "Adjusting word spacing")

heading3("Horizontal Scaling")

eg("""textobject.setHorizScale(horizScale)""")

disc("""Lines of text can be stretched or shrunken horizontally by the
$setHorizScale$ method.""")

eg(examples.testhorizontalscale)

disc("""The horizontal scaling parameter ^horizScale^
is given in percentages (with 100 as the default), so the 80 setting
shown below looks skinny.
""")
illust(examples.horizontalscale, "adjusting horizontal text scaling")

heading3("Interline spacing (Leading)")

eg("""textobject.setLeading(leading)""")

disc("""The vertical offset between the point at which one
line starts and where the next starts is called the leading
offset.  The $setLeading$ method adjusts the leading offset.
""")

eg(examples.testleading)

disc("""As shown below if the leading offset is set too small
characters of one line my write over the bottom parts of characters
in the previous line.""")

illust(examples.leading, "adjusting the leading")

heading3("Other text object methods")

eg("""textobject.setTextRenderMode(mode)""")

disc("""The $setTextRenderMode$ method allows text to be used
as a forground for clipping background drawings, for example.""")

eg("""textobject.setRise(rise)""")

disc("""
The $setRise$ method <super>raises</super> or <sub>lowers</sub> text on the line
(for creating superscripts or subscripts, for example).
""")

eg("""textobject.setFillColor(aColor);
textobject.setStrokeColor(self, aColor)
# and similar""")

disc("""
These color change operations change the <font color=darkviolet>color</font> of the text and are otherwise
similar to the color methods for the $canvas$ object.""")

heading2('Paths and Lines')

disc("""Just as textobjects are designed for the dedicated presentation
of text, path objects are designed for the dedicated construction of
graphical figures.  When path objects are drawn onto a $canvas$ they
are drawn as one figure (like a rectangle) and the mode of drawing
for the entire figure can be adjusted: the lines of the figure can
be drawn (stroked) or not; the interior of the figure can be filled or
not; and so forth.""")

disc("""
For example the $star$ function uses a path object
to draw a star
""")

eg(examples.teststar)

disc("""
The $star$ function has been designed to be useful in illustrating
various line style parameters supported by $pdfgen$.
""")

illust(examples.star, "line style parameters")

heading3("Line join settings")

disc("""
The $setLineJoin$ method can adjust whether line segments meet in a point
a square or a rounded vertex.
""")

eg(examples.testjoins)

disc("""
The line join setting is only really of interest for thick lines because
it cannot be seen clearly for thin lines.
""")

illust(examples.joins, "different line join styles")

heading3("Line cap settings")

disc("""The line cap setting, adjusted using the $setLineCap$ method,
determines whether a terminating line
ends in a square exactly at the vertex, a square over the vertex
or a half circle over the vertex.
""")

eg(examples.testcaps)

disc("""The line cap setting, like the line join setting, is only clearly
visible when the lines are thick.""")

illust(examples.caps, "line cap settings")

heading3("Dashes and broken lines")

disc("""
The $setDash$ method allows lines to be broken into dots or dashes.
""")

eg(examples.testdashes)

disc("""
The patterns for the dashes or dots can be in a simple on/off repeating pattern
or they can be specified in a complex repeating pattern.
""")

illust(examples.dashes, "some dash patterns")

heading3("Creating complex figures with path objects")

disc("""
Combinations of lines, curves, arcs and other figures
can be combined into a single figure using path objects.
For example the function shown below constructs two path
objects using lines and curves.
This function will be used later on as part of a
pencil icon construction.
""")

eg(examples.testpenciltip)

disc("""
Note that the interior of the pencil tip is filled
as one object even though it is constructed from
several lines and curves.  The pencil lead is then
drawn over it using a new path object.
""")

illust(examples.penciltip, "a pencil tip")

heading2('Rectangles, circles, ellipses')

disc("""
The $pdfgen$ module supports a number of generally useful shapes
such as rectangles, rounded rectangles, ellipses, and circles.
Each of these figures can be used in path objects or can be drawn
directly on a $canvas$.  For example the $pencil$ function below
draws a pencil icon using rectangles and rounded rectangles with
various fill colors and a few other annotations.
""")

eg(examples.testpencil)

pencilnote()

disc("""
Note that this function is used to create the "margin pencil" to the left.
Also note that the order in which the elements are drawn are important
because, for example, the white rectangles "erase" parts of a black rectangle
and the "tip" paints over part of the yellow rectangle.
""")

illust(examples.pencil, "a whole pencil")

heading2('Bezier curves')

disc("""
Programs that wish to construct figures with curving borders
generally use Bezier curves to form the borders.
""")

eg(examples.testbezier)

disc("""
A Bezier curve is specified by four control points
$(x1,y1)$, $(x2,y2)$, $(x3,y3)$, $(x4,y4)$.
The curve starts at $(x1,y1)$ and ends at $(x4,y4)$
and the line segment from $(x1,y1)$ to $(x2,y2)$
and the line segment from $(x3,y3)$ to $(x4,y4)$
both form tangents to the curve.  Furthermore the
curve is entirely contained in the convex figure with vertices
at the control points.
""")

illust(examples.bezier, "basic bezier curves")

disc("""
The drawing above (the output of $testbezier$) shows
a bezier curves, the tangent lines defined by the control points
and the convex figure with vertices at the control points.
""")

heading3("Smoothly joining bezier curve sequences")

disc("""
It is often useful to join several bezier curves to form a
single smooth curve.  To construct a larger smooth curve from
several bezier curves make sure that the tangent lines to adjacent
bezier curves that join at a control point lie on the same line.
""")

eg(examples.testbezier2)

disc("""
The figure created by $testbezier2$ describes a smooth
complex curve because adjacent tangent lines "line up" as
illustrated below.
""")

illust(examples.bezier2, "bezier curves")

heading2("Path object methods")

disc("""
Path objects build complex graphical figures by setting
the "pen" or "brush" at a start point on the canvas and drawing
lines or curves to additional points on the canvas.  Most operations
apply paint on the canvas starting at the end point of the last
operation and leave the brush at a new end point.
""")

eg("""pathobject.moveTo(x,y)""")

disc("""
The $moveTo$ method lifts the brush (ending any current sequence
of lines or curves if there is one) and replaces the brush at the
new ^(x,y)^ location on the canvas to start a new path sequence.
""")

eg("""pathobject.lineTo(x,y)""")

disc("""
The $lineTo$ method paints straight line segment from the current brush
location to the new ^(x,y)^ location.
""")

eg("""pathobject.curveTo(x1, y1, x2, y2, x3, y3) """)

disc("""
The $curveTo$ method starts painting a Bezier curve beginning at
the current brush location, using ^(x1,y1)^, ^(x2,y2)^, and ^(x3,y3)^
as the other three control points, leaving the brush on ^(x3,y3)^.
""")

eg("""pathobject.arc(x1,y1, x2,y2, startAng=0, extent=90) """)

eg("""pathobject.arcTo(x1,y1, x2,y2, startAng=0, extent=90) """)

disc("""
The $arc$ and $arcTo$ methods paint partial ellipses.  The $arc$ method first "lifts the brush"
and starts a new shape sequence.  The $arcTo$ method joins the start of
the partial ellipse to the current
shape sequence by line segment before drawing the partial ellipse.  The points
^(x1,y1)^ and ^(x2,y2)^ define opposite corner points of a rectangle enclosing
the ellipse.  The $startAng$ is an angle (in degrees) specifying where to begin
the partial ellipse where the 0 angle is the midpoint of the right border of the enclosing
rectangle (when ^(x1,y1)^ is the lower left corner and ^(x2,y2)^ is the upper
right corner).  The $extent$ is the angle in degrees to traverse on the ellipse.
""")

eg(examples.testarcs)

disc("""The $arcs$ function above exercises the two partial ellipse methods.
It produces the following drawing.""")

illust(examples.arcs, "arcs in path objects")

eg("""pathobject.rect(x, y, width, height) """)

disc("""The $rect$ method draws a rectangle with lower left corner
at ^(x,y)^ of the specified ^width^ and ^height^.""")

eg("""pathobject.ellipse(x, y, width, height)""")

disc("""The $ellipse$ method
draws an ellipse enclosed in the rectange with lower left corner
at ^(x,y)^ of the specified ^width^ and ^height^.
""")

eg("""pathobject.circle(x_cen, y_cen, r) """)

disc("""The $circle$ method
draws a circle centered at ^(x_cen, y_cen)^ with radius ^r^.
""")

eg(examples.testvariousshapes)

disc("""
The $variousshapes$ function above shows a rectangle, circle and ellipse
placed in a frame of reference grid.
""")

illust(examples.variousshapes, "rectangles, circles, ellipses in path objects")

eg("""pathobject.close() """)

disc("""
The $close$ method closes the current graphical figure
by painting a line segment from the last point of the figure
to the starting point of the figure (the the most
recent point where the brush was placed on the paper by $moveTo$
or $arc$ or other placement operations).
""")

eg(examples.testclosingfigures)

disc("""
The $closingfigures$ function illustrates the
effect of closing or not closing figures including a line
segment and a partial ellipse.
""")

illust(examples.closingfigures, "closing and not closing pathobject figures")

disc("""
Closing or not closing graphical figures effects only the stroked outline
of a figure, not the filling of the figure as illustrated above.
""")


disc("""
For a more extensive example of drawing using a path object
examine the $hand$ function.
""")

eg(examples.testhand)

disc("""
In debug mode (the default) the $hand$ function shows the tangent line segments
to the bezier curves used to compose the figure.  Note that where the segments
line up the curves join smoothly, but where they do not line up the curves show
a "sharp edge".
""")

illust(examples.hand, "an outline of a hand using bezier curves")

disc("""
Used in non-debug mode the $hand$ function only shows the
Bezier curves.  With the $fill$ parameter set the figure is
filled using the current fill color.
""")

eg(examples.testhand2)

disc("""
Note that the "stroking" of the border draws over the interior fill where
they overlap.
""")

illust(examples.hand2, "the finished hand, filled")



heading2("Further Reading: The ReportLab Graphics Library")

disc("""
So far the graphics we have seen was created on a fairly low level.
It should be noted, though, that there is another way of creating
much more sophisticated graphics using the emerging dedicated
high-level <i>ReportLab Graphics Library</i>.
""")

disc("""
It can be used to produce high-quality, platform-independant,
reusable graphics for different output formats (vector and bitmap)
like PDF, EPS and soon others like SVG.
""")

disc("""
A thorough description of its philsophy and features is beyond the
scope of this general user guide and the reader is recommended to
continue with the <i>"ReportLab Graphics Guide"</i>.
There she will find information about the existing components and
how to create customized ones.
""")

disc("""
Also, the graphics guide contains a presentation of an emerging
charting package and its components (labels, axes, legends and
different types of charts like bar, line and pie charts) that
builds directly on the graphics library.
""")


##### FILL THEM IN
