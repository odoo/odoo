#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/docs/graphguide/ch2_concepts.py
from reportlab.tools.docco.rl_doc_utils import *

heading1("General Concepts")

disc("""
In this chapter we will present some of the more fundamental principles of
the graphics library, which will show-up later in various places.
""")


heading2("Drawings and Renderers")

disc("""
A <i>Drawing</i> is a platform-independent description of a collection of
shapes.
It is not directly associated with PDF, Postscript or any other output
format.
Fortunately, most vector graphics systems have followed the Postscript
model and it is possible to describe shapes unambiguously.
""")

disc("""
A drawing contains a number of primitive <i>Shapes</i>.
Normal shapes are those widely known as rectangles, circles, lines,
etc.
One special (logic) shape is a <i>Group</i>, which can hold other
shapes and apply a transformation to them.
Groups represent composites of shapes and allow to treat the
composite as if it were a single shape.
Just about anything can be built up from a small number of basic
shapes.
""")

disc("""
The package provides several <i>Renderers</i> which know how to draw a
drawing into different formats.
These include PDF (of course), Postscript, and bitmap output.
The bitmap renderer uses Raph Levien's <i>libart</i> rasterizer
and Fredrik Lundh's <i>Python Imaging Library</i> (PIL).
Very recently, an experimental SVG renderer was also added.
It makes use of Python's standard library XML modules, so you don't
need to install the XML-SIG's additional package named PyXML.
If you have the right extensions installed, you can generate drawings
in bitmap form for the web as well as vector form for PDF documents,
and get "identical output".
""")

disc("""
The PDF renderer has special "privileges" - a Drawing object is also
a <i>Flowable</i> and, hence, can be placed directly in the story
of any Platypus document, or drawn directly on a <i>Canvas</i> with
one line of code.
In addition, the PDF renderer has a utility function to make
a one-page PDF document quickly.
""")

disc("""
The SVG renderer is special as it is still pretty experimental.
The SVG code it generates is not really optimised in any way and
maps only the features available in ReportLab Graphics (RLG) to
SVG. This means there is no support for SVG animation, interactivity,
scripting or more sophisticated clipping, masking or graduation
shapes.
So, be careful, and please report any bugs you find!
""")

disc("""
We expect to add both input and output filters for many vector
graphics formats in future.
SVG was the most prominent first one to start with for which there
is now an output filter in the graphics package.
An SVG input filter will probably become available in Summer 2002
as an additional module.
GUIs will be able to obtain screen images from the bitmap output
filter working with PIL, so a chart could appear in a Tkinter
GUI window.
""")


heading2("Coordinate System")

disc("""
The Y-direction in our X-Y coordinate system points from the
bottom <i>up</i>.
This is consistent with PDF, Postscript and mathematical notation.
It also appears to be more natural for people, especially when
working with charts.
Note that in other graphics models (such as SVG) the Y-coordinate
points <i>down</i>.
For the SVG renderer this is actually no problem as it will take
your drawings and flip things as needed, so your SVG output looks
just as expected.
""")

disc("""
The X-coordinate points, as usual, from left to right.
So far there doesn't seem to be any model advocating the opposite
direction - at least not yet (with interesting exceptions, as it
seems, for Arabs looking at time series charts...).
""")


heading2("Getting Started")

disc("""
Let's create a simple drawing containing the string "Hello World",
displayed on top of a coloured rectangle.
After creating it we will save the drawing to a standalone PDF file.
""")

eg("""
    from reportlab.lib import colors
    from reportlab.graphics.shapes import *

    d = Drawing(400, 200)
    d.add(Rect(50, 50, 300, 100, fillColor=colors.yellow))
    d.add(String(150,100, 'Hello World',
                 fontSize=18, fillColor=colors.red))

    from reportlab.graphics import renderPDF
    renderPDF.drawToFile(d, 'example1.pdf', 'My First Drawing')
""")

disc("This will produce a PDF file containing the following graphic:")

from reportlab.graphics.shapes import *
from reportlab.graphics import testshapes
t = testshapes.getDrawing01()
draw(t, "'Hello World'")

disc("""
Each renderer is allowed to do whatever is appropriate for its format,
and may have whatever API is needed.
If it refers to a file format, it usually has a $drawToFile$ function,
and that's all you need to know about the renderer.
Let's save the same drawing in Encapsulated Postscript format:
""")

##eg("""
##    from reportlab.graphics import renderPS
##    renderPS.drawToFile(D, 'example1.eps', 'My First Drawing')
##""")
eg("""
    from reportlab.graphics import renderPS
    renderPS.drawToFile(d, 'example1.eps')
""")

disc("""
This will produce an EPS file with the identical drawing, which
may be imported into publishing tools such as Quark Express.
If we wanted to generate the same drawing as a bitmap file for
a website, say, all we need to do is write code like this:
""")

eg("""
    from reportlab.graphics import renderPM
    renderPM.saveToFile(d, 'example1.png', 'PNG')
""")

disc("""
Many other bitmap formats, like GIF, JPG, TIFF, BMP and PPN are
genuinely available, making it unlikely you'll need to add external
postprocessing steps to convert to the final format you need.
""")

disc("""
To produce an SVG file containing the identical drawing, which
may be imported into graphical editing tools such as Illustrator
all we need to do is write code like this:
""")

eg("""
    from reportlab.graphics import renderSVG
    renderSVG.drawToFile(d, 'example1.svg')
""")


heading2("Attribute Verification")

disc("""
Python is very dynamic and lets us execute statements at run time that
can easily be the source for unexpected behaviour.
One subtle 'error' is when assigning to an attribute that the framework
doesn't know about because the used attribute's name contains a typo.
Python lets you get away with it (adding a new attribute to an object,
say), but the graphics framework will not detect this 'typo' without
taking special counter-measures.
""")

disc("""
There are two verification techniques to avoid this situation.
The default is for every object to check every assignment at run
time, such that you can only assign to 'legal' attributes.
This is what happens by default.
As this imposes a small performance penalty, this behaviour can
be turned off when you need it to be.
""")

eg("""
>>> r = Rect(10,10,200,100, fillColor=colors.red)
>>>
>>> r.fullColor = colors.green # note the typo
>>> r.x = 'not a number'       # illegal argument type
>>> del r.width                # that should confuse it
""")

disc("""
These statements would be caught by the compiler in a statically
typed language, but Python lets you get away with it.
The first error could leave you staring at the picture trying to
figure out why the colors were wrong.
The second error would probably become clear only later, when
some back-end tries to draw the rectangle.
The third, though less likely, results in an invalid object that
would not know how to draw itself.
""")

eg("""
>>> r = shapes.Rect(10,10,200,80)
>>> r.fullColor = colors.green
Traceback (most recent call last):
  File "<interactive input>", line 1, in ?
  File "C:\code\users\andy\graphics\shapes.py", line 254, in __setattr__
    validateSetattr(self,attr,value)    #from reportlab.lib.attrmap
  File "C:\code\users\andy\lib\attrmap.py", line 74, in validateSetattr
    raise AttributeError, "Illegal attribute '%s' in class %s" % (name, obj.__class__.__name__)
AttributeError: Illegal attribute 'fullColor' in class Rect
>>>
""")

disc("""
This imposes a performance penalty, so this behaviour can be turned
off when you need it to be.
To do this, you should use the following lines of code before you
first import reportlab.graphics.shapes:
""")

eg("""
>>> import reportlab.rl_config
>>> reportlab.rl_config.shapeChecking = 0
>>> from reportlab.graphics import shapes
>>>
""")

disc("""
Once you turn off $shapeChecking$, the classes are actually built
without the verification hook; code should get faster, then.
Currently the penalty seems to be about 25% on batches of charts,
so it is hardly worth disabling.
However, if we move the renderers to C in future (which is eminently
possible), the remaining 75% would shrink to almost nothing and
the saving from verification would be significant.
""")

disc("""
Each object, including the drawing itself, has a $verify()$ method.
This either succeeds, or raises an exception.
If you turn off automatic verification, then you should explicitly
call $verify()$ in testing when developing the code, or perhaps
once in a batch process.
""")


heading2("Property Editing")

disc("""
A cornerstone of the reportlab/graphics which we will cover below is
that you can automatically document widgets.
This means getting hold of all of their editable properties,
including those of their subcomponents.
""")

disc("""
Another goal is to be able to create GUIs and config files for
drawings.
A generic GUI can be built to show all editable properties
of a drawing, and let you modify them and see the results.
The Visual Basic or Delphi development environment are good
examples of this kind of thing.
In a batch charting application, a file could list all the
properties of all the components in a chart, and be merged
with a database query to make a batch of charts.
""")

disc("""
To support these applications we have two interfaces, $getProperties$
and $setProperties$, as well as a convenience method $dumpProperties$.
The first returns a dictionary of the editable properties of an
object; the second sets them en masse.
If an object has publicly exposed 'children' then one can recursively
set and get their properties too.
This will make much more sense when we look at <i>Widgets</i> later on,
but we need to put the support into the base of the framework.
""")

eg("""
>>> r = shapes.Rect(0,0,200,100)
>>> import pprint
>>> pprint.pprint(r.getProperties())
{'fillColor': Color(0.00,0.00,0.00),
 'height': 100,
 'rx': 0,
 'ry': 0,
 'strokeColor': Color(0.00,0.00,0.00),
 'strokeDashArray': None,
 'strokeLineCap': 0,
 'strokeLineJoin': 0,
 'strokeMiterLimit': 0,
 'strokeWidth': 1,
 'width': 200,
 'x': 0,
 'y': 0}
>>> r.setProperties({'x':20, 'y':30, 'strokeColor': colors.red})
>>> r.dumpProperties()
fillColor = Color(0.00,0.00,0.00)
height = 100
rx = 0
ry = 0
strokeColor = Color(1.00,0.00,0.00)
strokeDashArray = None
strokeLineCap = 0
strokeLineJoin = 0
strokeMiterLimit = 0
strokeWidth = 1
width = 200
x = 20
y = 30
>>>  """)

disc("""
<i>Note: $pprint$ is the standard Python library module that allows
you to 'pretty print' output over multiple lines rather than having
one very long line.</i>
""")

disc("""
These three methods don't seem to do much here, but as we will see
they make our widgets framework much more powerful when dealing with
non-primitive objects.
""")


heading2("Naming Children")

disc("""
You can add objects to the $Drawing$ and $Group$ objects.
These normally go into a list of contents.
However, you may also give objects a name when adding them.
This allows you to refer to and possibly change any element
of a drawing after constructing it.
""")

eg("""
>>> d = shapes.Drawing(400, 200)
>>> s = shapes.String(10, 10, 'Hello World')
>>> d.add(s, 'caption')
>>> s.caption.text
'Hello World'
>>>
""")

disc("""
Note that you can use the same shape instance in several contexts
in a drawing; if you choose to use the same $Circle$ object in many
locations (e.g. a scatter plot) and use different names to access
it, it will still be a shared object and the changes will be
global.
""")

disc("""
This provides one paradigm for creating and modifying interactive
drawings.
""")