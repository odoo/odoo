#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/docs/graphguide/ch5_charts.py

from reportlab.tools.docco.rl_doc_utils import *
from reportlab.graphics.shapes import *

heading1("Charts")

disc("""
The motivation for much of this is to create a flexible chart
package.
This chapter presents a treatment of the ideas behind our charting
model, what the design goals are and what components of the chart
package already exist.
""")


heading2("Design Goals")

disc("Here are some of the design goals: ")

disc("<i>Make simple top-level use really simple </i>")
disc("""<para lindent=+36>It should be possible to create a simple chart with minimum lines of
       code, yet have it 'do the right things' with sensible automatic
       settings. The pie chart snippets above do this. If a real chart has
       many subcomponents, you still should not need to interact with them
       unless you want to customize what they do.""")

disc("<i>Allow precise positioning </i>")
disc("""<para lindent=+36>An absolute requirement in publishing and graphic design is to control
       the placing and style of every element. We will try to have properties
       that specify things in fixed sizes and proportions of the drawing,
       rather than having automatic resizing. Thus, the 'inner plot
       rectangle' will not magically change when you make the font size of
       the y labels bigger, even if this means your labels can spill out of
       the left edge of the chart rectangle. It is your job to preview the
       chart and choose sizes and spaces which will work.""")

disc("""<para lindent=+36>Some things do need to be automatic. For example, if you want to fit N
       bars into a 200 point space and don't know N in advance, we specify
       bar separation as a percentage of the width of a bar rather than a
       point size, and let the chart work it out. This is still deterministic
       and controllable.""")

disc("<i>Control child elements individually or as a group</i>")
disc("""<para lindent=+36>We use smart collection classes that let you customize a group of
       things, or just one of them. For example you can do this in our
       experimental pie chart:""")

eg("""
d = Drawing(400,200)
pc = Pie()
pc.x = 150
pc.y = 50
pc.data = [10,20,30,40,50,60]
pc.labels = ['a','b','c','d','e','f']
pc.slices.strokeWidth=0.5
pc.slices[3].popout = 20
pc.slices[3].strokeWidth = 2
pc.slices[3].strokeDashArray = [2,2]
pc.slices[3].labelRadius = 1.75
pc.slices[3].fontColor = colors.red
d.add(pc, '')
""")

disc("""<para lindent=+36>pc.slices[3] actually lazily creates a little object which holds
       information about the slice in question; this will be used to format a
       fourth slice at draw-time if there is one.""")

disc("<i>Only expose things you should change </i>")
disc("""<para lindent=+36>It would be wrong from a statistical viewpoint to let you directly
       adjust the angle of one of the pie wedges in the above example, since
       that is determined by the data. So not everything will be exposed
       through the public properties. There may be 'back doors' to let you
       violate this when you really need to, or methods to provide advanced
       functionality, but in general properties will be orthogonal.""")

disc("<i>Composition and component based </i>")
disc("""<para lindent=+36>Charts are built out of reusable child widgets. A Legend is an
       easy-to-grasp example. If you need a specialized type of legend (e.g.
       circular colour swatches), you should subclass the standard Legend
       widget. Then you could either do something like...""")

eg("""
c = MyChartWithLegend()
c.legend = MyNewLegendClass()    # just change it
c.legend.swatchRadius = 5    # set a property only relevant to the new one
c.data = [10,20,30]   #   and then configure as usual...
""")

disc("""<para lindent=+36>...or create/modify your own chart or drawing class which creates one
       of these by default. This is also very relevant for time series
       charts, where there can be many styles of x axis.""")

disc("""<para lindent=+36>Top level chart classes will create a number of such components, and
       then either call methods or set private properties to tell them their
       height and position - all the stuff which should be done for you and
       which you cannot customise. We are working on modelling what the
       components should be and will publish their APIs here as a consensus
       emerges.""")

disc("<i>Multiples </i>")
disc("""<para lindent=+36>A corollary of the component approach is that you can create diagrams
       with multiple charts, or custom data graphics. Our favourite example
       of what we are aiming for is the weather report in our gallery
       contributed by a user; we'd like to make it easy to create such
       drawings, hook the building blocks up to their legends, and feed that
       data in a consistent way.""")
disc("""<para lindent=+36>(If you want to see the image, it is available on our website at
<font color=blue>http://www.reportlab.com/demos/provencio.pdf</font>)""")


##heading2("Key Concepts and Components")
heading2("Overview")

disc("""A chart or plot is an object which is placed on a drawing; it is not
       itself a drawing. You can thus control where it goes, put several on
       the same drawing, or add annotations.""")

disc("""Charts have two axes; axes may be Value or Category axes. Axes in turn
       have a Labels property which lets you configure all text labels or
       each one individually. Most of the configuration details which vary
       from chart to chart relate to axis properties, or axis labels.""")

disc("""Objects expose properties through the interfaces discussed in the
       previous section; these are all optional and are there to let the end
       user configure the appearance. Things which must be set for a chart to
       work, and essential communication between a chart and its components,
       are handled through methods.""")

disc("""You can subclass any chart component and use your replacement instead
       of the original provided you implement the essential methods and
       properties.""")


heading2("Labels")

disc("""
A label is a string of text attached to some chart element.
They are used on axes, for titles or alongside axes, or attached
to individual data points.
Labels may contain newline characters, but only one font.
""")

disc("""The text and 'origin' of a label are typically set by its parent
       object. They are accessed by methods rather than properties. Thus, the
       X axis decides the 'reference point' for each tickmark label and the
       numeric or date text for each label. However, the end user can set
       properties of the label (or collection of labels) directly to affect
       its position relative to this origin and all of its formatting.""")

eg("""
from reportlab.graphics import shapes
from reportlab.graphics.charts.textlabels import Label

d = Drawing(200, 100)

# mark the origin of the label
d.add(Circle(100,90, 5, fillColor=colors.green))

lab = Label()
lab.setOrigin(100,90)
lab.boxAnchor = 'ne'
lab.angle = 45
lab.dx = 0
lab.dy = -20
lab.boxStrokeColor = colors.green
lab.setText('Some\nMulti-Line\nLabel')

d.add(lab)
""")


from reportlab.graphics import shapes
from reportlab.graphics.charts.textlabels import Label

d = Drawing(200, 100)

# mark the origin of the label
d.add(Circle(100,90, 5, fillColor=colors.green))

lab = Label()
lab.setOrigin(100,90)
lab.boxAnchor = 'ne'
lab.angle = 45
lab.dx = 0
lab.dy = -20
lab.boxStrokeColor = colors.green
lab.setText('Some\nMulti-Line\nLabel')

d.add(lab)

draw(d, 'Label example')



disc("""
In the drawing above, the label is defined relative to the green blob.
The text box should have its north-east corner ten points down from
the origin, and be rotated by 45 degrees about that corner.
""")

disc("""
At present labels have the following properties, which we believe are
sufficient for all charts we have seen to date:
""")

disc("")

data=[["Property", "Meaning"],
      ["dx", """The label's x displacement."""],
      ["dy", """The label's y displacement."""],
      ["angle", """The angle of rotation (counterclockwise) applied to the label."""],
      ["boxAnchor", "The label's box anchor, one of 'n', 'e', 'w', 's', 'ne', 'nw', 'se', 'sw'."],
      ["textAnchor", """The place where to anchor the label's text, one of 'start', 'middle', 'end'."""],
      ["boxFillColor", """The fill color used in the label's box."""],
      ["boxStrokeColor", "The stroke color used in the label's box."],
      ["boxStrokeWidth", """The line width of the label's box."""],
      ["fontName", """The label's font name."""],
      ["fontSize", """The label's font size."""],
      ["leading", """The leading value of the label's text lines."""],
      ["x", """The X-coordinate of the reference point."""],
      ["y", """The Y-coordinate of the reference point."""],
      ["width", """The label's width."""],
      ["height", """The label's height."""]
      ]
t=Table(data, colWidths=(100,330))
t.setStyle(TableStyle([
            ('FONT',(0,0),(-1,0),'Times-Bold',10,12),
            ('FONT',(0,1),(0,-1),'Courier',8,8),
            ('FONT',(1,1),(1,-1),'Times-Roman',10,12),
            ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
            ('BOX', (0,0), (-1,-1), 0.25, colors.black),
            ]))
getStory().append(t)
caption("""Table <seq template="%(Chapter)s-%(Table+)s"/> - Label properties""")

disc("""
To see many more examples of $Label$ objects with different
combinations of properties, please have a look into the
ReportLab test suite in the folder $reportlab/test$, run the
script $test_charts_textlabels.py$ and look at the PDF document
it generates!
""")



heading2("Axes")

disc("""
We identify two basic kinds of axes - <i>Value</i> and <i>Category</i>
ones.
Both come in horizontal and vertical flavors.
Both can be subclassed to make very specific kinds of axis.
For example, if you have complex rules for which dates to display
in a time series application, or want irregular scaling, you override
the axis and make a new one.
""")

disc("""
Axes are responsible for determining the mapping from data to image
coordinates; transforming points on request from the chart; drawing
themselves and their tickmarks, gridlines and axis labels.
""")

disc("""
This drawing shows two axes, one of each kind, which have been created
directly without reference to any chart:
""")


from reportlab.graphics import shapes
from reportlab.graphics.charts.axes import XCategoryAxis,YValueAxis

drawing = Drawing(400, 200)

data = [(10, 20, 30, 40), (15, 22, 37, 42)]

xAxis = XCategoryAxis()
xAxis.setPosition(75, 75, 300)
xAxis.configure(data)
xAxis.categoryNames = ['Beer', 'Wine', 'Meat', 'Cannelloni']
xAxis.labels.boxAnchor = 'n'
xAxis.labels[3].dy = -15
xAxis.labels[3].angle = 30
xAxis.labels[3].fontName = 'Times-Bold'

yAxis = YValueAxis()
yAxis.setPosition(50, 50, 125)
yAxis.configure(data)

drawing.add(xAxis)
drawing.add(yAxis)

draw(drawing, 'Two isolated axes')


disc("Here is the code that created them: ")

eg("""
from reportlab.graphics import shapes
from reportlab.graphics.charts.axes import XCategoryAxis,YValueAxis

drawing = Drawing(400, 200)

data = [(10, 20, 30, 40), (15, 22, 37, 42)]

xAxis = XCategoryAxis()
xAxis.setPosition(75, 75, 300)
xAxis.configure(data)
xAxis.categoryNames = ['Beer', 'Wine', 'Meat', 'Cannelloni']
xAxis.labels.boxAnchor = 'n'
xAxis.labels[3].dy = -15
xAxis.labels[3].angle = 30
xAxis.labels[3].fontName = 'Times-Bold'

yAxis = YValueAxis()
yAxis.setPosition(50, 50, 125)
yAxis.configure(data)

drawing.add(xAxis)
drawing.add(yAxis)
""")

disc("""
Remember that, usually, you won't have to create axes directly;
when using a standard chart, it comes with ready-made axes.
The methods are what the chart uses to configure it and take care
of the geometry.
However, we will talk through them in detail below.
The orthogonally dual axes to those we describe have essentially
the same properties, except for those refering to ticks.
""")


heading3("XCategoryAxis class")

disc("""
A Category Axis doesn't really have a scale; it just divides itself
into equal-sized buckets.
It is simpler than a value axis.
The chart (or programmer) sets its location with the method
$setPosition(x, y, length)$.
The next stage is to show it the data so that it can configure
itself.
This is easy for a category axis - it just counts the number of
data points in one of the data series. The $reversed$ attribute (if 1)
indicates that the categories should be reversed.
When the drawing is drawn, the axis can provide some help to the
chart with its $scale()$ method, which tells the chart where
a given category begins and ends on the page.
We have not yet seen any need to let people override the widths
or positions of categories.
""")

disc("An XCategoryAxis has the following editable properties:")

disc("")

data=[["Property", "Meaning"],
      ["visible", """Should the axis be drawn at all? Sometimes you don't want
to display one or both axes, but they still need to be there as
they manage the scaling of points."""],
      ["strokeColor", "Color of the axis"],
      ["strokeDashArray", """Whether to draw axis with a dash and, if so, what kind.
Defaults to None"""],
      ["strokeWidth", "Width of axis in points"],
      ["tickUp", """How far above the axis should the tick marks protrude?
(Note that making this equal to chart height gives you a gridline)"""],
      ["tickDown", """How far below the axis should the tick mark protrude?"""],
      ["categoryNames", """Either None, or a list of strings. This should have the
same length as each data series."""],
      ["labels", """A collection of labels for the tick marks. By default the 'north'
of each text label (i.e top centre) is positioned 5 points down
from the centre of each category on the axis. You may redefine
any property of the whole label group or of any one label. If
categoryNames=None, no labels are drawn."""],
      ["title", """Not Implemented Yet. This needs to be like a label, but also
lets you set the text directly. It would have a default
location below the axis."""]]
t=Table(data, colWidths=(100,330))
t.setStyle(TableStyle([
            ('FONT',(0,0),(-1,0),'Times-Bold',10,12),
            ('FONT',(0,1),(0,-1),'Courier',8,8),
            ('FONT',(1,1),(1,-1),'Times-Roman',10,12),
            ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
            ('BOX', (0,0), (-1,-1), 0.25, colors.black),
            ]))
getStory().append(t)
caption("""Table <seq template="%(Chapter)s-%(Table+)s"/> - XCategoryAxis properties""")


heading3("YValueAxis")

disc("""
The left axis in the diagram is a YValueAxis.
A Value Axis differs from a Category Axis in that each point along
its length corresponds to a y value in chart space.
It is the job of the axis to configure itself, and to convert Y values
from chart space to points on demand to assist the parent chart in
plotting.
""")

disc("""
$setPosition(x, y, length)$ and $configure(data)$ work exactly as
for a category axis.
If you have not fully specified the maximum, minimum and tick
interval, then $configure()$ results in the axis choosing suitable
values.
Once configured, the value axis can convert y data values to drawing
space with the $scale()$ method.
Thus:
""")

eg("""
>>> yAxis = YValueAxis()
>>> yAxis.setPosition(50, 50, 125)
>>> data = [(10, 20, 30, 40),(15, 22, 37, 42)]
>>> yAxis.configure(data)
>>> yAxis.scale(10)  # should be bottom of chart
50.0
>>> yAxis.scale(40)  # should be near the top
167.1875
>>>
""")

disc("""By default, the highest data point is aligned with the top of the
       axis, the lowest with the bottom of the axis, and the axis choose
       'nice round numbers' for its tickmark points. You may override these
       settings with the properties below. """)

disc("")

data=[["Property", "Meaning"],
      ["visible", """Should the axis be drawn at all? Sometimes you don't want
to display one or both axes, but they still need to be there as
they manage the scaling of points."""],
      ["strokeColor", "Color of the axis"],
      ["strokeDashArray", """Whether to draw axis with a dash and, if so, what kind.
Defaults to None"""],
      ["strokeWidth", "Width of axis in points"],
      ["tickLeft", """How far to the left of the axis should the tick marks protrude?
(Note that making this equal to chart height gives you a gridline)"""],
      ["tickRight", """How far to the right of the axis should the tick mark protrude?"""],

      ["valueMin", """The y value to which the bottom of the axis should correspond.
Default value is None in which case the axis sets it to the lowest
actual data point (e.g. 10 in the example above). It is common to set
this to zero to avoid misleading the eye."""],
      ["valueMax", """The y value to which the top of the axis should correspond.
Default value is None in which case the axis sets it to the highest
actual data point (e.g. 42 in the example above). It is common to set
this to a 'round number' so data bars do not quite reach the top."""],
      ["valueStep", """The y change between tick intervals. By default this is
None, and the chart tries to pick 'nice round numbers' which are
just wider than the minimumTickSpacing below."""],

      ["valueSteps", """A list of numbers at which to place ticks."""],

      ["minimumTickSpacing", """This is used when valueStep is set to None, and ignored
otherwise. The designer specified that tick marks should be no
closer than X points apart (based, presumably, on considerations
of the label font size and angle). The chart tries values of the
type 1,2,5,10,20,50,100... (going down below 1 if necessary) until
it finds an interval which is greater than the desired spacing, and
uses this for the step."""],
      ["labelTextFormat", """This determines what goes in the labels. Unlike a category
axis which accepts fixed strings, the labels on a ValueAxis are
supposed to be numbers. You may provide either a 'format string'
like '%0.2f' (show two decimal places), or an arbitrary function
which accepts a number and returns a string. One use for the
latter is to convert a timestamp to a readable year-month-day
format."""],
      ["title", """Not Implemented Yet. This needs to be like a label, but also
lets you set the text directly. It would have a default
location below the axis."""]]
t=Table(data, colWidths=(100,330))
t.setStyle(TableStyle([
            ('FONT',(0,0),(-1,0),'Times-Bold',10,12),
            ('FONT',(0,1),(0,-1),'Courier',8,8),
            ('FONT',(1,1),(1,-1),'Times-Roman',10,12),
            ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
            ('BOX', (0,0), (-1,-1), 0.25, colors.black),
            ]))
getStory().append(t)
caption("""Table <seq template="%(Chapter)s-%(Table+)s"/> - YValueAxis properties""")

disc("""
The $valueSteps$ property lets you explicitly specify the
tick mark locations, so you don't have to follow regular intervals.
Hence, you can plot month ends and month end dates with a couple of
helper functions, and without needing special time series chart
classes.
The following code show how to create a simple $XValueAxis$ with special
tick intervals. Make sure to set the $valueSteps$ attribute before calling
the configure method!
""")

eg("""
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.axes import XValueAxis

drawing = Drawing(400, 100)

data = [(10, 20, 30, 40)]

xAxis = XValueAxis()
xAxis.setPosition(75, 50, 300)
xAxis.valueSteps = [10, 15, 20, 30, 35, 40]
xAxis.configure(data)
xAxis.labels.boxAnchor = 'n'

drawing.add(xAxis)
""")


from reportlab.graphics import shapes
from reportlab.graphics.charts.axes import XValueAxis

drawing = Drawing(400, 100)

data = [(10, 20, 30, 40)]

xAxis = XValueAxis()
xAxis.setPosition(75, 50, 300)
xAxis.valueSteps = [10, 15, 20, 30, 35, 40]
xAxis.configure(data)
xAxis.labels.boxAnchor = 'n'

drawing.add(xAxis)

draw(drawing, 'An axis with non-equidistant tick marks')


disc("""
In addition to these properties, all axes classes have three
properties describing how to join two of them to each other.
Again, this is interesting only if you define your own charts
or want to modify the appearance of an existing chart using
such axes.
These properties are listed here only very briefly for now,
but you can find a host of sample functions in the module
$reportlab/graphics/axes.py$ which you can examine...
""")

disc("""
One axis is joined to another, by calling the method
$joinToAxis(otherAxis, mode, pos)$ on the first axis,
with $mode$ and $pos$ being the properties described by
$joinAxisMode$ and $joinAxisPos$, respectively.
$'points'$ means to use an absolute value, and $'value'$
to use a relative value (both indicated by the the
$joinAxisPos$ property) along the axis.
""")

disc("")

data=[["Property", "Meaning"],
      ["joinAxis", """Join both axes if true."""],
      ["joinAxisMode", """Mode used for connecting axis ('bottom', 'top', 'left', 'right', 'value', 'points', None)."""],
      ["joinAxisPos", """Position at which to join with other axis."""],
      ]
t=Table(data, colWidths=(100,330))
t.setStyle(TableStyle([
            ('FONT',(0,0),(-1,0),'Times-Bold',10,12),
            ('FONT',(0,1),(0,-1),'Courier',8,8),
            ('FONT',(1,1),(1,-1),'Times-Roman',10,12),
            ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
            ('BOX', (0,0), (-1,-1), 0.25, colors.black),
            ]))
getStory().append(t)
caption("""Table <seq template="%(Chapter)s-%(Table+)s"/> - Axes joining properties""")


heading2("Bar Charts")

disc("""
This describes our current $VerticalBarChart$ class, which uses the
axes and labels above.
We think it is step in the right direction but is is
far from final.
Note that people we speak to are divided about 50/50 on whether to
call this a 'Vertical' or 'Horizontal' bar chart.
We chose this name because 'Vertical' appears next to 'Bar', so
we take it to mean that the bars rather than the category axis
are vertical.
""")

disc("""
As usual, we will start with an example:
""")

from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart

drawing = Drawing(400, 200)

data = [
        (13, 5, 20, 22, 37, 45, 19, 4),
        (14, 6, 21, 23, 38, 46, 20, 5)
        ]

bc = VerticalBarChart()
bc.x = 50
bc.y = 50
bc.height = 125
bc.width = 300
bc.data = data
bc.strokeColor = colors.black

bc.valueAxis.valueMin = 0
bc.valueAxis.valueMax = 50
bc.valueAxis.valueStep = 10

bc.categoryAxis.labels.boxAnchor = 'ne'
bc.categoryAxis.labels.dx = 8
bc.categoryAxis.labels.dy = -2
bc.categoryAxis.labels.angle = 30
bc.categoryAxis.categoryNames = ['Jan-99','Feb-99','Mar-99',
       'Apr-99','May-99','Jun-99','Jul-99','Aug-99']

drawing.add(bc)

draw(drawing, 'Simple bar chart with two data series')


eg("""
    # code to produce the above chart

    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics.charts.barcharts import VerticalBarChart

    drawing = Drawing(400, 200)

    data = [
            (13, 5, 20, 22, 37, 45, 19, 4),
            (14, 6, 21, 23, 38, 46, 20, 5)
            ]

    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black

    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 50
    bc.valueAxis.valueStep = 10

    bc.categoryAxis.labels.boxAnchor = 'ne'
    bc.categoryAxis.labels.dx = 8
    bc.categoryAxis.labels.dy = -2
    bc.categoryAxis.labels.angle = 30
    bc.categoryAxis.categoryNames = ['Jan-99','Feb-99','Mar-99',
           'Apr-99','May-99','Jun-99','Jul-99','Aug-99']

    drawing.add(bc)
""")

disc("""
Most of this code is concerned with setting up the axes and
labels, which we have already covered.
Here are the top-level properties of the $VerticalBarChart$ class:
""")

disc("")

data=[["Property", "Meaning"],
      ["data", """This should be a "list of lists of numbers" or "list of
tuples of numbers". If you have just one series, write it as
data = [(10,20,30,42),]"""],
      ["x, y, width, height", """These define the inner 'plot rectangle'. We
highlighted this with a yellow border above. Note that it is
your job to place the chart on the drawing in a way which leaves
room for all the axis labels and tickmarks. We specify this 'inner
rectangle' because it makes it very easy to lay out multiple charts
in a consistent manner."""],
      ["strokeColor", """Defaults to None. This will draw a border around the
plot rectangle, which may be useful in debugging. Axes will
overwrite this."""],
      ["fillColor", """Defaults to None. This will fill the plot rectangle with
a solid color. (Note that we could implement dashArray etc.
as for any other solid shape)"""],
      ["barLabelFormat", """This is a format string or function used for displaying
labels above each bar. They are positioned automatically
above the bar for positive values and below for negative ones."""],
      ["useAbsolute", """Defaults to 0. If 1, the three properties below are
absolute values in points (which means you can make a chart
where the bars stick out from the plot rectangle); if 0,
they are relative quantities and indicate the proportional
widths of the elements involved."""],
      ["barWidth", """As it says. Defaults to 10."""],
      ["groupSpacing", """Defaults to 5. This is the space between each group of
bars. If you have only one series, use groupSpacing and not
barSpacing to split them up. Half of the groupSpacing is used
before the first bar in the chart, and another half at the end."""],
      ["barSpacing", """Defaults to 0. This is the spacing between bars in each
group. If you wanted a little gap between green and red bars in
the example above, you would make this non-zero."""],
      ["barLabelFormat", """Defaults to None. As with the YValueAxis, if you supply
a function or format string then labels will be drawn next
to each bar showing the numeric value."""],
      ["barLabels", """A collection of labels used to format all bar labels. Since
this is a two-dimensional array, you may explicitly format the
third label of the second series using this syntax:
  chart.barLabels[(1,2)].fontSize = 12"""],
      ["valueAxis", """The value axis, which may be formatted as described
previously."""],
      ["categoryAxis", """The category axis, which may be formatted as described
previously."""],

      ["title", """Not Implemented Yet. This needs to be like a label, but also
lets you set the text directly. It would have a default
location below the axis."""]]
t=Table(data, colWidths=(100,330))
t.setStyle(TableStyle([
            ('FONT',(0,0),(-1,0),'Times-Bold',10,12),
            ('FONT',(0,1),(0,-1),'Courier',8,8),
            ('FONT',(1,1),(1,-1),'Times-Roman',10,12),
            ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
            ('BOX', (0,0), (-1,-1), 0.25, colors.black),
            ]))
getStory().append(t)
caption("""Table <seq template="%(Chapter)s-%(Table+)s"/> - VerticalBarChart properties""")


disc("""
From this table we deduce that adding the following lines to our code
above should double the spacing between bar groups (the $groupSpacing$
attribute has a default value of five points) and we should also see
some tiny space between bars of the same group ($barSpacing$).
""")

eg("""
    bc.groupSpacing = 10
    bc.barSpacing = 2.5
""")

disc("""
And, in fact, this is exactly what we can see after adding these
lines to the code above.
Notice how the width of the individual bars has changed as well.
This is because the space added between the bars has to be 'taken'
from somewhere as the total chart width stays unchanged.
""")

from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart

drawing = Drawing(400, 200)

data = [
        (13, 5, 20, 22, 37, 45, 19, 4),
        (14, 6, 21, 23, 38, 46, 20, 5)
        ]

bc = VerticalBarChart()
bc.x = 50
bc.y = 50
bc.height = 125
bc.width = 300
bc.data = data
bc.strokeColor = colors.black

bc.groupSpacing = 10
bc.barSpacing = 2.5

bc.valueAxis.valueMin = 0
bc.valueAxis.valueMax = 50
bc.valueAxis.valueStep = 10

bc.categoryAxis.labels.boxAnchor = 'ne'
bc.categoryAxis.labels.dx = 8
bc.categoryAxis.labels.dy = -2
bc.categoryAxis.labels.angle = 30
bc.categoryAxis.categoryNames = ['Jan-99','Feb-99','Mar-99',
       'Apr-99','May-99','Jun-99','Jul-99','Aug-99']

drawing.add(bc)

draw(drawing, 'Like before, but with modified spacing')

disc("""
Bars labels are automatically displayed for negative values
<i>below</i> the lower end of the bar for positive values
<i>above</i> the upper end of the other ones.
""")


##Property Value
##data This should be a "list of lists of numbers" or "list of tuples of numbers". If you have just one series, write it as
##data = [(10,20,30,42),]
##
##x, y, width, height These define the inner 'plot rectangle'. We highlighted this with a yellow border above. Note that it is your job to place the chart on the drawing in a way which leaves room for all the axis labels and tickmarks. We specify this 'inner rectangle' because it makes it very easy to lay out multiple charts in a consistent manner.
##strokeColor Defaults to None. This will draw a border around the plot rectangle, which may be useful in debugging. Axes will overwrite this.
##fillColor Defaults to None. This will fill the plot rectangle with a solid color. (Note that we could implement dashArray etc. as for any other solid shape)
##barLabelFormat This is a format string or function used for displaying labels above each bar. We're working on ways to position these labels so that they work for positive and negative bars.
##useAbsolute Defaults to 0. If 1, the three properties below are absolute values in points (which means you can make a chart where the bars stick out from the plot rectangle); if 0, they are relative quantities and indicate the proportional widths of the elements involved.
##barWidth As it says. Defaults to 10.
##groupSpacing Defaults to 5. This is the space between each group of bars. If you have only one series, use groupSpacing and not barSpacing to split them up. Half of the groupSpacing is used before the first bar in the chart, and another half at the end.
##barSpacing Defaults to 0. This is the spacing between bars in each group. If you wanted a little gap between green and red bars in the example above, you would make this non-zero.
##barLabelFormat Defaults to None. As with the YValueAxis, if you supply a function or format string then labels will be drawn next to each bar showing the numeric value.
##barLabels A collection of labels used to format all bar labels. Since this is a two-dimensional array, you may explicitly format the third label of the second series using this syntax:
##    chart.barLabels[(1,2)].fontSize = 12
##
##valueAxis The value axis, which may be formatted as described previously
##categoryAxis The categoryAxis, which may be formatted as described previously
##title, subTitle Not implemented yet. These would be label-like objects whose text could be set directly and which would appear in sensible locations. For now, you can just place extra strings on the drawing.


heading2("Line Charts")

disc("""
We consider "Line Charts" to be essentially the same as
"Bar Charts", but with lines instead of bars.
Both share the same pair of Category/Value axes pairs.
This is in contrast to "Line Plots", where both axes are
<i>Value</i> axes.
""")

disc("""
The following code and its output shall serve as a simple
example.
More explanation will follow.
For the time being you can also study the output of running
the tool $reportlab/lib/graphdocpy.py$ withough any arguments
and search the generated PDF document for examples of
Line Charts.
""")

eg("""
from reportlab.graphics.charts.linecharts import HorizontalLineChart

drawing = Drawing(400, 200)

data = [
    (13, 5, 20, 22, 37, 45, 19, 4),
    (5, 20, 46, 38, 23, 21, 6, 14)
]

lc = HorizontalLineChart()
lc.x = 50
lc.y = 50
lc.height = 125
lc.width = 300
lc.data = data
lc.joinedLines = 1
catNames = string.split('Jan Feb Mar Apr May Jun Jul Aug', ' ')
lc.categoryAxis.categoryNames = catNames
lc.categoryAxis.labels.boxAnchor = 'n'
lc.valueAxis.valueMin = 0
lc.valueAxis.valueMax = 60
lc.valueAxis.valueStep = 15
lc.lines[0].strokeWidth = 2
lc.lines[1].strokeWidth = 1.5
drawing.add(lc)
""")

from reportlab.graphics.charts.linecharts import HorizontalLineChart

drawing = Drawing(400, 200)

data = [
    (13, 5, 20, 22, 37, 45, 19, 4),
    (5, 20, 46, 38, 23, 21, 6, 14)
]

lc = HorizontalLineChart()
lc.x = 50
lc.y = 50
lc.height = 125
lc.width = 300
lc.data = data
lc.joinedLines = 1
catNames = string.split('Jan Feb Mar Apr May Jun Jul Aug', ' ')
lc.categoryAxis.categoryNames = catNames
lc.categoryAxis.labels.boxAnchor = 'n'
lc.valueAxis.valueMin = 0
lc.valueAxis.valueMax = 60
lc.valueAxis.valueStep = 15
lc.lines[0].strokeWidth = 2
lc.lines[1].strokeWidth = 1.5
drawing.add(lc)

draw(drawing, 'HorizontalLineChart sample')


disc("")
todo("Add properties table.")


heading2("Line Plots")

disc("""
Below we show a more complex example of a Line Plot that
also uses some experimental features like line markers
placed at each data point.
""")

eg("""
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.widgets.markers import makeMarker

drawing = Drawing(400, 200)

data = [
    ((1,1), (2,2), (2.5,1), (3,3), (4,5)),
    ((1,2), (2,3), (2.5,2), (3.5,5), (4,6))
]

lp = LinePlot()
lp.x = 50
lp.y = 50
lp.height = 125
lp.width = 300
lp.data = data
lp.joinedLines = 1
lp.lines[0].symbol = makeMarker('FilledCircle')
lp.lines[1].symbol = makeMarker('Circle')
lp.lineLabelFormat = '%2.0f'
lp.strokeColor = colors.black
lp.xValueAxis.valueMin = 0
lp.xValueAxis.valueMax = 5
lp.xValueAxis.valueSteps = [1, 2, 2.5, 3, 4, 5]
lp.xValueAxis.labelTextFormat = '%2.1f'
lp.yValueAxis.valueMin = 0
lp.yValueAxis.valueMax = 7
lp.yValueAxis.valueSteps = [1, 2, 3, 5, 6]

drawing.add(lp)
""")


from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.widgets.markers import makeMarker

drawing = Drawing(400, 200)

data = [
    ((1,1), (2,2), (2.5,1), (3,3), (4,5)),
    ((1,2), (2,3), (2.5,2), (3.5,5), (4,6))
]

lp = LinePlot()
lp.x = 50
lp.y = 50
lp.height = 125
lp.width = 300
lp.data = data
lp.joinedLines = 1
lp.lines[0].symbol = makeMarker('FilledCircle')
lp.lines[1].symbol = makeMarker('Circle')
lp.lineLabelFormat = '%2.0f'
lp.strokeColor = colors.black
lp.xValueAxis.valueMin = 0
lp.xValueAxis.valueMax = 5
lp.xValueAxis.valueSteps = [1, 2, 2.5, 3, 4, 5]
lp.xValueAxis.labelTextFormat = '%2.1f'
lp.yValueAxis.valueMin = 0
lp.yValueAxis.valueMax = 7
lp.yValueAxis.valueSteps = [1, 2, 3, 5, 6]

drawing.add(lp)

draw(drawing, 'LinePlot sample')



disc("")
todo("Add properties table.")



heading2("Pie Charts")

disc("""
We've already seen a pie chart example above.
This is provisional but seems to do most things.
At the very least we need to change the name.
For completeness we will cover it here.
""")

eg("""
from reportlab.graphics.charts.piecharts import Pie

d = Drawing(200, 100)

pc = Pie()
pc.x = 65
pc.y = 15
pc.width = 70
pc.height = 70
pc.data = [10,20,30,40,50,60]
pc.labels = ['a','b','c','d','e','f']

pc.slices.strokeWidth=0.5
pc.slices[3].popout = 10
pc.slices[3].strokeWidth = 2
pc.slices[3].strokeDashArray = [2,2]
pc.slices[3].labelRadius = 1.75
pc.slices[3].fontColor = colors.red

d.add(pc)
""")

from reportlab.graphics.charts.piecharts import Pie

d = Drawing(200, 100)

pc = Pie()
pc.x = 65
pc.y = 15
pc.width = 70
pc.height = 70
pc.data = [10,20,30,40,50,60]
pc.labels = ['a','b','c','d','e','f']

pc.slices.strokeWidth=0.5
pc.slices[3].popout = 10
pc.slices[3].strokeWidth = 2
pc.slices[3].strokeDashArray = [2,2]
pc.slices[3].labelRadius = 1.75
pc.slices[3].fontColor = colors.red

d.add(pc)

draw(d, 'A bare bones pie chart')

disc("""
Properties are covered below.
The pie has a 'wedges' collection and we document wedge properties
in the same table.
This was invented before we finished the $Label$ class and will
probably be reworked to use such labels shortly.
""")

disc("")
todo("Add properties table.")

##Property Value
##data a list or tuple of numbers
##x, y, width, height Bounding box of the pie. Note that x and y do NOT specify the centre but the bottom left corner, and that width and height do not have to be equal; pies may be elliptical and wedges will be drawn correctly.
##labels None, or a list of strings. Make it None if you don't want labels around the edge of the pie. Since it is impossible to know the size of slices, we generally discourage placing labels in or around pies; it is much better to put them in a legend alongside.
##startAngle Where is the start angle of the first pie slice? The default is '90' which is twelve o'clock.
##direction Which direction do slices progress in? The default is 'clockwise'.
##wedges Collection of wedges. This lets you customise each wedge, or individual ones. See below
##wedges.strokeWidth Border width for wedge
##wedges.strokeColor Border color
##wedges.strokeDashArray Solid or dashed line configuration for
##wedges.popout How far out should the slice(s) stick from the centre of
##the pie? default is zero.
##wedges.fontName
##wedges.fontSize
##wedges.fontColor Used for text labels
##wedges.labelRadius This controls the anchor point for a text label. It
##is a fraction of the radius; 0.7 will place the text inside the pie,
##1.2 will place it slightly outside. (note that if we add labels, we
##will keep this to specify their anchor point)
##


heading2("Legends")

disc("""
Various preliminary legend classes can be found but need a
cleanup to be consistent with the rest of the charting
model.
Legends are the natural place to specify the colors and line
styles of charts; we propose that each chart is created with
a $legend$ attribute which is invisible.
One would then do the following to specify colors:
""")

eg("""
myChart.legend.defaultColors = [red, green, blue]
""")

disc("""
One could also define a group of charts sharing the same legend:
""")

eg("""
myLegend = Legend()
myLegend.defaultColor = [red, green.....] #yuck!
myLegend.columns = 2
# etc.
chart1.legend = myLegend
chart2.legend = myLegend
chart3.legend = myLegend
""")

# Hack to force a new paragraph before the todo() :-(
disc("")

todo("""Does this work? Is it an acceptable complication over specifying chart
colors directly?""")



heading2("Remaining Issues")

disc("""
There are several issues that are <i>almost</i> solved, but for which
is is a bit too early to start making them really public.
Nevertheless, here is a list of things that are under way:
""")

list("""
Color specification - right now the chart has an undocumented property
$defaultColors$, which provides a list of colors to cycle through,
such that each data series gets its own color.
Right now, if you introduce a legend, you need to make sure it shares
the same list of colors.
Most likely, this will be replaced with a scheme to specify a kind
of legend containing attributes with different values for each data
series.
This legend can then also be shared by several charts, but need not
be visible itself.
""")

list("""
Additional chart types - when the current design will have become
more stable, we expect to add variants of bar charts to deal with stacked
and percentile bars as well as the side-by-side variant seen here.
""")


heading2("Outlook")

disc("""
It will take some time to deal with the full range of chart types.
We expect to finalize bars and pies first and to produce trial
implementations of more general plots, thereafter.
""")


heading3("X-Y Plots")

disc("""
Most other plots involve two value axes and directly plotting
x-y data in some form.
The series can be plotted as lines, marker symbols, both, or
custom graphics such as open-high-low-close graphics.
All share the concepts of scaling and axis/title formatting.
At a certain point, a routine will loop over the data series and
'do something' with the data points at given x-y locations.
Given a basic line plot, it should be very easy to derive a
custom chart type just by overriding a single method - say,
$drawSeries()$.
""")


heading3("Marker customisation and custom shapes")

disc("""
Well known plotting packages such as excel, Mathematica and Excel
offer ranges of marker types to add to charts.
We can do better - you can write any kind of chart widget you
want and just tell the chart to use it as an example.
""")


heading4("Combination plots")

disc("""
Combining multiple plot types is really easy.
You can just draw several charts (bar, line or whatever) in
the same rectangle, suppressing axes as needed.
So a chart could correlate a line with Scottish typhoid cases
over a 15 year period on the left axis with a set of bars showing
inflation rates on the right axis.
If anyone can remind us where this example came from we'll
attribute it, and happily show the well-known graph as an
example.
""")


heading3("Interactive editors")

disc("""
One principle of the Graphics package is to make all 'interesting'
properties of its graphic components accessible and changeable by
setting apropriate values of corresponding public attributes.
This makes it very tempting to build a tool like a GUI editor that
that helps you with doing that interactively.
""")

disc("""
ReportLab has built such a tool using the Tkinter toolkit that
loads pure Python code describing a drawing and records your
property editing operations.
This "change history" is then used to create code for a subclass
of that chart, say, that can be saved and used instantly just
like any other chart or as a new starting point for another
interactive editing session.
""")

disc("""
This is still work in progress, though, and the conditions for
releasing this need to be further elaborated.
""")


heading3("Misc.")

disc("""
This has not been an exhaustive look at all the chart classes.
Those classes are constantly being worked on.
To see exactly what is in the current distribution, use the
$graphdocpy.py$ utility.
By default, it will run on reportlab/graphics, and produce a full
report.
(If you want to run it on other modules or packages,
$graphdocpy.py -h$ prints a help message that will tell you
how.)
""")

disc("""
This is the tool that was mentioned in the section on 'Documenting
Widgets'.
""")