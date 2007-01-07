#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/docs/graphguide/ch4_widgets.py

from reportlab.tools.docco.rl_doc_utils import *
from reportlab.graphics.shapes import *
from reportlab.graphics.widgets import signsandsymbols

heading1("Widgets")

disc("""
We now describe widgets and how they relate to shapes.
Using many examples it is shown how widgets make reusable
graphics components.
""")


heading2("Shapes vs. Widgets")

disc("""Up until now, Drawings have been 'pure data'. There is no code in them
       to actually do anything, except assist the programmer in checking and
       inspecting the drawing. In fact, that's the cornerstone of the whole
       concept and is what lets us achieve portability - a renderer only
       needs to implement the primitive shapes.""")

disc("""We want to build reusable graphic objects, including a powerful chart
       library. To do this we need to reuse more tangible things than
       rectangles and circles. We should be able to write objects for other
       to reuse - arrows, gears, text boxes, UML diagram nodes, even fully
       fledged charts.""")

disc("""
The Widget standard is a standard built on top of the shapes module.
Anyone can write new widgets, and we can build up libraries of them.
Widgets support the $getProperties()$ and $setProperties()$ methods,
so you can inspect and modify as well as document them in a uniform
way.
""")

bullet("A widget is a reusable shape ")
bullet("""it can be initialized with no arguments
       when its $draw()$ method is called it creates a primitive Shape or a
       Group to represent itself""")
bullet("""It can have any parameters you want, and they can drive the way it is
       drawn""")
bullet("""it has a $demo()$ method which should return an attractively drawn
       example of itself in a 200x100 rectangle. This is the cornerstone of
       the automatic documentation tools. The $demo()$ method should also have
       a well written docstring, since that is printed too!""")

disc("""Widgets run contrary to the idea that a drawing is just a bundle of
       shapes; surely they have their own code? The way they work is that a
       widget can convert itself to a group of primitive shapes. If some of
       its components are themselves widgets, they will get converted too.
       This happens automatically during rendering; the renderer will not see
       your chart widget, but just a collection of rectangles, lines and
       strings. You can also explicitly 'flatten out' a drawing, causing all
       widgets to be converted to primitives.""")


heading2("Using a Widget")

disc("""
Let's imagine a simple new widget.
We will use a widget to draw a face, then show how it was implemented.""")

eg("""
>>> from reportlab.lib import colors
>>> from reportlab.graphics import shapes
>>> from reportlab.graphics import widgetbase
>>> from reportlab.graphics import renderPDF
>>> d = shapes.Drawing(200, 100)
>>> f = widgetbase.Face()
>>> f.skinColor = colors.yellow
>>> f.mood = "sad"
>>> d.add(f)
>>> renderPDF.drawToFile(d, 'face.pdf', 'A Face')
""")

from reportlab.graphics import widgetbase
d = Drawing(200, 120)
f = widgetbase.Face()
f.x = 50
f.y = 10
f.skinColor = colors.yellow
f.mood = "sad"
d.add(f)
draw(d, 'A sample widget')

disc("""
Let's see what properties it has available, using the $setProperties()$
method we have seen earlier:
""")

eg("""
>>> f.dumpProperties()
eyeColor = Color(0.00,0.00,1.00)
mood = sad
size = 80
skinColor = Color(1.00,1.00,0.00)
x = 10
y = 10
>>>
""")

disc("""
One thing which seems strange about the above code is that we did not
set the size or position when we made the face.
This is a necessary trade-off to allow a uniform interface for
constructing widgets and documenting them - they cannot require
arguments in their $__init__()$ method.
Instead, they are generally designed to fit in a 200 x 100
window, and you move or resize them by setting properties such as
x, y, width and so on after creation.
""")

disc("""
In addition, a widget always provides a $demo()$ method.
Simple ones like this always do something sensible before setting
properties, but more complex ones like a chart would not have any
data to plot.
The documentation tool calls $demo()$ so that your fancy new chart
class can create a drawing showing what it can do.
""")

disc("""
Here are a handful of simple widgets available in the module
<i>signsandsymbols.py</i>:
""")

from reportlab.graphics.shapes import Drawing
from reportlab.graphics.widgets import signsandsymbols

d = Drawing(230, 230)

ne = signsandsymbols.NoEntry()
ds = signsandsymbols.DangerSign()
fd = signsandsymbols.FloppyDisk()
ns = signsandsymbols.NoSmoking()

ne.x, ne.y = 10, 10
ds.x, ds.y = 120, 10
fd.x, fd.y = 10, 120
ns.x, ns.y = 120, 120

d.add(ne)
d.add(ds)
d.add(fd)
d.add(ns)

draw(d, 'A few samples from signsandsymbols.py')

disc("""
And this is the code needed to generate them as seen in the drawing above:
""")

eg("""
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.widgets import signsandsymbols

d = Drawing(230, 230)

ne = signsandsymbols.NoEntry()
ds = signsandsymbols.DangerSign()
fd = signsandsymbols.FloppyDisk()
ns = signsandsymbols.NoSmoking()

ne.x, ne.y = 10, 10
ds.x, ds.y = 120, 10
fd.x, fd.y = 10, 120
ns.x, ns.y = 120, 120

d.add(ne)
d.add(ds)
d.add(fd)
d.add(ns)
""")


heading2("Compound Widgets")

disc("""Let's imagine a compound widget which draws two faces side by side.
       This is easy to build when you have the Face widget.""")

eg("""
>>> tf = widgetbase.TwoFaces()
>>> tf.faceOne.mood
'happy'
>>> tf.faceTwo.mood
'sad'
>>> tf.dumpProperties()
faceOne.eyeColor = Color(0.00,0.00,1.00)
faceOne.mood = happy
faceOne.size = 80
faceOne.skinColor = None
faceOne.x = 10
faceOne.y = 10
faceTwo.eyeColor = Color(0.00,0.00,1.00)
faceTwo.mood = sad
faceTwo.size = 80
faceTwo.skinColor = None
faceTwo.x = 100
faceTwo.y = 10
>>>
""")

disc("""The attributes 'faceOne' and 'faceTwo' are deliberately exposed so you
       can get at them directly. There could also be top-level attributes,
       but there aren't in this case.""")


heading2("Verifying Widgets")

disc("""The widget designer decides the policy on verification, but by default
       they work like shapes - checking every assignment - if the designer
       has provided the checking information.""")


heading2("Implementing Widgets")

disc("""We tried to make it as easy to implement widgets as possible. Here's
       the code for a Face widget which does not do any type checking:""")

eg("""
class Face(Widget):
    \"\"\"This draws a face with two eyes, mouth and nose.\"\"\"

    def __init__(self):
        self.x = 10
        self.y = 10
        self.size = 80
        self.skinColor = None
        self.eyeColor = colors.blue
        self.mood = 'happy'

    def draw(self):
        s = self.size  # abbreviate as we will use this a lot
        g = shapes.Group()
        g.transform = [1,0,0,1,self.x, self.y]
        # background
        g.add(shapes.Circle(s * 0.5, s * 0.5, s * 0.5,
                            fillColor=self.skinColor))
        # CODE OMITTED TO MAKE MORE SHAPES
        return g
""")

disc("""We left out all the code to draw the shapes in this document, but you
       can find it in the distribution in $widgetbase.py$.""")

disc("""By default, any attribute without a leading underscore is returned by
       setProperties. This is a deliberate policy to encourage consistent
       coding conventions.""")

disc("""Once your widget works, you probably want to add support for
       verification. This involves adding a dictionary to the class called
       $_verifyMap$, which map from attribute names to 'checking functions'.
       The $widgetbase.py$ module defines a bunch of checking functions with names
       like $isNumber$, $isListOfShapes$ and so on. You can also simply use $None$,
       which means that the attribute must be present but can have any type.
       And you can and should write your own checking functions. We want to
       restrict the "mood" custom attribute to the values "happy", "sad" or
       "ok". So we do this:""")

eg("""
class Face(Widget):
    \"\"\"This draws a face with two eyes.  It exposes a
    couple of properties to configure itself and hides
    all other details\"\"\"
    def checkMood(moodName):
        return (moodName in ('happy','sad','ok'))
    _verifyMap = {
        'x': shapes.isNumber,
        'y': shapes.isNumber,
        'size': shapes.isNumber,
        'skinColor':shapes.isColorOrNone,
        'eyeColor': shapes.isColorOrNone,
        'mood': checkMood
        }
""")

disc("""This checking will be performed on every attribute assignment; or, if
       $config.shapeChecking$ is off, whenever you call $myFace.verify()$.""")


heading2("Documenting Widgets")

disc("""
We are working on a generic tool to document any Python package or
module; this is already checked into ReportLab and will be used to
generate a reference for the ReportLab package.
When it encounters widgets, it adds extra sections to the
manual including:""")

bullet("the doc string for your widget class ")
bullet("the code snippet from your <i>demo()</i> method, so people can see how to use it")
bullet("the drawing produced by the <i>demo()</i> method ")
bullet("the property dump for the widget in the drawing. ")

disc("""
This tool will mean that we can have guaranteed up-to-date
documentation on our widgets and charts, both on the web site
and in print; and that you can do the same for your own widgets,
too!
""")


heading2("Widget Design Strategies")

disc("""We could not come up with a consistent architecture for designing
       widgets, so we are leaving that problem to the authors! If you do not
       like the default verification strategy, or the way
       $setProperties/getProperties$ works, you can override them yourself.""")

disc("""For simple widgets it is recommended that you do what we did above:
       select non-overlapping properties, initialize every property on
       $__init__$ and construct everything when $draw()$ is called. You can
       instead have $__setattr__$ hooks and have things updated when certain
       attributes are set. Consider a pie chart. If you want to expose the
       individual wedges, you might write code like this:""")

eg("""
from reportlab.graphics.charts import piecharts
pc = piecharts.Pie()
pc.defaultColors = [navy, blue, skyblue] #used in rotation
pc.data = [10,30,50,25]
pc.slices[7].strokeWidth = 5
""")
#removed 'pc.backColor = yellow' from above code example

disc("""The last line is problematic as we have only created four wedges - in
       fact we might not have created them yet. Does $pc.wedges[7]$ raise an
       error? Is it a prescription for what should happen if a seventh wedge
       is defined, used to override the default settings? We dump this
       problem squarely on the widget author for now, and recommend that you
       get a simple one working before exposing 'child objects' whose
       existence depends on other properties' values :-)""")

disc("""We also discussed rules by which parent widgets could pass properties
       to their children. There seems to be a general desire for a global way
       to say that 'all wedges get their lineWidth from the lineWidth of
       their parent' without a lot of repetitive coding. We do not have a
       universal solution, so again leave that to widget authors. We hope
       people will experiment with push-down, pull-down and pattern-matching
       approaches and come up with something nice. In the meantime, we
       certainly can write monolithic chart widgets which work like the ones
       in, say, Visual Basic and Delphi.""")

disc("""For now have a look at the following sample code using an early
       version of a pie chart widget and the output it generates:""")

eg("""
from reportlab.lib.colors import *
from reportlab.graphics import shapes,renderPDF
from reportlab.graphics.charts.piecharts import Pie

d = Drawing(400,200)
d.add(String(100,175,"Without labels", textAnchor="middle"))
d.add(String(300,175,"With labels", textAnchor="middle"))

pc = Pie()
pc.x = 25
pc.y = 50
pc.data = [10,20,30,40,50,60]
pc.slices[0].popout = 5
d.add(pc, 'pie1')

pc2 = Pie()
pc2.x = 150
pc2.y = 50
pc2.data = [10,20,30,40,50,60]
pc2.labels = ['a','b','c','d','e','f']
d.add(pc2, 'pie2')

pc3 = Pie()
pc3.x = 275
pc3.y = 50
pc3.data = [10,20,30,40,50,60]
pc3.labels = ['a','b','c','d','e','f']
pc3.wedges.labelRadius = 0.65
pc3.wedges.fontName = "Helvetica-Bold"
pc3.wedges.fontSize = 16
pc3.wedges.fontColor = colors.yellow
d.add(pc3, 'pie3')
""")

# Hack to force a new paragraph before the todo() :-(
disc("")

from reportlab.lib.colors import *
from reportlab.graphics import shapes,renderPDF
from reportlab.graphics.charts.piecharts import Pie

d = Drawing(400,200)
d.add(String(100,175,"Without labels", textAnchor="middle"))
d.add(String(300,175,"With labels", textAnchor="middle"))

pc = Pie()
pc.x = 25
pc.y = 50
pc.data = [10,20,30,40,50,60]
pc.slices[0].popout = 5
d.add(pc, 'pie1')

pc2 = Pie()
pc2.x = 150
pc2.y = 50
pc2.data = [10,20,30,40,50,60]
pc2.labels = ['a','b','c','d','e','f']
d.add(pc2, 'pie2')

pc3 = Pie()
pc3.x = 275
pc3.y = 50
pc3.data = [10,20,30,40,50,60]
pc3.labels = ['a','b','c','d','e','f']
pc3.slices.labelRadius = 0.65
pc3.slices.fontName = "Helvetica-Bold"
pc3.slices.fontSize = 16
pc3.slices.fontColor = colors.yellow
d.add(pc3, 'pie3')

draw(d, 'Some sample Pies')