#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/graphics/widgetbase.py
__version__=''' $Id: widgetbase.py 2668 2005-09-05 10:23:51Z rgbecker $ '''
import string

from reportlab.graphics import shapes
from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.validators import *
from reportlab.lib.attrmap import *


class PropHolder:
    '''Base for property holders'''

    _attrMap = None

    def verify(self):
        """If the _attrMap attribute is not None, this
        checks all expected attributes are present; no
        unwanted attributes are present; and (if a
        checking function is found) checks each
        attribute has a valid value.  Either succeeds
        or raises an informative exception.
        """

        if self._attrMap is not None:
            for key in self.__dict__.keys():
                if key[0] <> '_':
                    msg = "Unexpected attribute %s found in %s" % (key, self)
                    assert self._attrMap.has_key(key), msg
            for (attr, metavalue) in self._attrMap.items():
                msg = "Missing attribute %s from %s" % (attr, self)
                assert hasattr(self, attr), msg
                value = getattr(self, attr)
                args = (value, attr, self.__class__.__name__)
                assert metavalue.validate(value), "Invalid value %s for attribute %s in class %s" % args

    if rl_config.shapeChecking:
        """This adds the ability to check every attribute assignment
        as it is made. It slows down shapes but is a big help when
        developing. It does not get defined if rl_config.shapeChecking = 0.
        """

        def __setattr__(self, name, value):
            """By default we verify.  This could be off
            in some parallel base classes."""
            validateSetattr(self,name,value)


    def getProperties(self,recur=1):
        """Returns a list of all properties which can be edited and
        which are not marked as private. This may include 'child
        widgets' or 'primitive shapes'.  You are free to override
        this and provide alternative implementations; the default
        one simply returns everything without a leading underscore.
        """

        from reportlab.lib.validators import isValidChild

        # TODO when we need it, but not before -
        # expose sequence contents?

        props = {}
        for name in self.__dict__.keys():
            if name[0:1] <> '_':
                component = getattr(self, name)

                if recur and isValidChild(component):
                    # child object, get its properties too
                    childProps = component.getProperties(recur=recur)
                    for (childKey, childValue) in childProps.items():
                        #key might be something indexed like '[2].fillColor'
                        #or simple like 'fillColor'; in the former case we
                        #don't need a '.' between me and my child.
                        if childKey[0] == '[':
                            props['%s%s' % (name, childKey)] = childValue
                        else:
                            props['%s.%s' % (name, childKey)] = childValue
                else:
                    props[name] = component

        return props


    def setProperties(self, propDict):
        """Permits bulk setting of properties.  These may include
        child objects e.g. "chart.legend.width = 200".

        All assignments will be validated by the object as if they
        were set individually in python code.

        All properties of a top-level object are guaranteed to be
        set before any of the children, which may be helpful to
        widget designers.
        """

        childPropDicts = {}
        for (name, value) in propDict.items():
            parts = string.split(name, '.', 1)
            if len(parts) == 1:
                #simple attribute, set it now
                setattr(self, name, value)
            else:
                (childName, remains) = parts
                try:
                    childPropDicts[childName][remains] = value
                except KeyError:
                    childPropDicts[childName] = {remains: value}

        # now assign to children
        for (childName, childPropDict) in childPropDicts.items():
            child = getattr(self, childName)
            child.setProperties(childPropDict)


    def dumpProperties(self, prefix=""):
        """Convenience. Lists them on standard output.  You
        may provide a prefix - mostly helps to generate code
        samples for documentation.
        """

        propList = self.getProperties().items()
        propList.sort()
        if prefix:
            prefix = prefix + '.'
        for (name, value) in propList:
            print '%s%s = %s' % (prefix, name, value)


class Widget(PropHolder, shapes.UserNode):
    """Base for all user-defined widgets.  Keep as simple as possible. Does
    not inherit from Shape so that we can rewrite shapes without breaking
    widgets and vice versa."""

    def _setKeywords(self,**kw):
        for k,v in kw.items():
            if not self.__dict__.has_key(k):
                setattr(self,k,v)

    def draw(self):
        msg = "draw() must be implemented for each Widget!"
        raise shapes.NotImplementedError, msg

    def demo(self):
        msg = "demo() must be implemented for each Widget!"
        raise shapes.NotImplementedError, msg

    def provideNode(self):
        return self.draw()

    def getBounds(self):
        "Return outer boundary as x1,y1,x2,y2.  Can be overridden for efficiency"
        return self.draw().getBounds()

_ItemWrapper={}

class TypedPropertyCollection(PropHolder):
    """A container with properties for objects of the same kind.

    This makes it easy to create lists of objects. You initialize
    it with a class of what it is to contain, and that is all you
    can add to it.  You can assign properties to the collection
    as a whole, or to a numeric index within it; if so it creates
    a new child object to hold that data.

    So:
        wedges = TypedPropertyCollection(WedgeProperties)
        wedges.strokeWidth = 2                # applies to all
        wedges.strokeColor = colors.red       # applies to all
        wedges[3].strokeColor = colors.blue   # only to one

    The last line should be taken as a prescription of how to
    create wedge no. 3 if one is needed; no error is raised if
    there are only two data points.

    We try and make sensible use of tuple indeces.
        line[(3,x)] is backed by line[(3,)], line[3] & line
    """

    def __init__(self, exampleClass):
        #give it same validation rules as what it holds
        self.__dict__['_value'] = exampleClass()
        self.__dict__['_children'] = {}

    def wKlassFactory(self,Klass):
        class WKlass(Klass):
            def __getattr__(self,name):
                try:
                    return self.__class__.__bases__[0].__getattr__(self,name)
                except:
                    i = self._index
                    if i:
                        c = self._parent._children
                        if c.has_key(i) and c[i].__dict__.has_key(name):
                            return getattr(c[i],name)
                        elif len(i)==1:
                            i = i[0]
                            if c.has_key(i) and c[i].__dict__.has_key(name):
                                return getattr(c[i],name)
                    return getattr(self._parent,name)
        return WKlass

    def __getitem__(self, index):
        try:
            return self._children[index]
        except KeyError:
            Klass = self._value.__class__
            if _ItemWrapper.has_key(Klass):
                WKlass = _ItemWrapper[Klass]
            else:
                _ItemWrapper[Klass] = WKlass = self.wKlassFactory(Klass)

            child = WKlass()
            child._parent = self
            if type(index) in (type(()),type([])):
                index = tuple(index)
                if len(index)>1:
                    child._index = tuple(index[:-1])
                else:
                    child._index = None
            else:
                child._index = None
            for i in filter(lambda x,K=child.__dict__.keys(): x in K,child._attrMap.keys()):
                del child.__dict__[i]

            self._children[index] = child
            return child

    def has_key(self,key):
        if type(key) in (type(()),type([])): key = tuple(key)
        return self._children.has_key(key)

    def __setitem__(self, key, value):
        msg = "This collection can only hold objects of type %s" % self._value.__class__.__name__
        assert isinstance(value, self._value.__class__), msg

    def __len__(self):
        return len(self._children.keys())

    def getProperties(self,recur=1):
        # return any children which are defined and whatever
        # differs from the parent
        props = {}

        for (key, value) in self._value.getProperties(recur=recur).items():
            props['%s' % key] = value

        for idx in self._children.keys():
            childProps = self._children[idx].getProperties(recur=recur)
            for (key, value) in childProps.items():
                if not hasattr(self,key) or getattr(self, key)<>value:
                    newKey = '[%s].%s' % (idx, key)
                    props[newKey] = value
        return props

    def setVector(self,**kw):
        for name, value in kw.items():
            for i in xrange(len(value)):
                setattr(self[i],name,value[i])

    def __getattr__(self,name):
        return getattr(self._value,name)

    def __setattr__(self,name,value):
        return setattr(self._value,name,value)

## No longer needed!
class StyleProperties(PropHolder):
    """A container class for attributes used in charts and legends.

    Attributes contained can be those for any graphical element
    (shape?) in the ReportLab graphics package. The idea for this
    container class is to be useful in combination with legends
    and/or the individual appearance of data series in charts.

    A legend could be as simple as a wrapper around a list of style
    properties, where the 'desc' attribute contains a descriptive
    string and the rest could be used by the legend e.g. to draw
    something like a color swatch. The graphical presentation of
    the legend would be its own business, though.

    A chart could be inspecting a legend or, more directly, a list
    of style properties to pick individual attributes that it knows
    about in order to render a particular row of the data. A bar
    chart e.g. could simply use 'strokeColor' and 'fillColor' for
    drawing the bars while a line chart could also use additional
    ones like strokeWidth.
    """

    _attrMap = AttrMap(
        strokeWidth = AttrMapValue(isNumber),
        strokeLineCap = AttrMapValue(isNumber),
        strokeLineJoin = AttrMapValue(isNumber),
        strokeMiterLimit = AttrMapValue(None),
        strokeDashArray = AttrMapValue(isListOfNumbersOrNone),
        strokeOpacity = AttrMapValue(isNumber),
        strokeColor = AttrMapValue(isColorOrNone),
        fillColor = AttrMapValue(isColorOrNone),
        desc = AttrMapValue(isString),
        )

    def __init__(self, **kwargs):
        "Initialize with attributes if any."

        for k, v in kwargs.items():
            setattr(self, k, v)


    def __setattr__(self, name, value):
        "Verify attribute name and value, before setting it."
        validateSetattr(self,name,value)


class TwoCircles(Widget):
    def __init__(self):
        self.leftCircle = shapes.Circle(100,100,20, fillColor=colors.red)
        self.rightCircle = shapes.Circle(300,100,20, fillColor=colors.red)

    def draw(self):
        return shapes.Group(self.leftCircle, self.rightCircle)


class Face(Widget):
    """This draws a face with two eyes.

    It exposes a couple of properties
    to configure itself and hides all other details.
    """

    _attrMap = AttrMap(
        x = AttrMapValue(isNumber),
        y = AttrMapValue(isNumber),
        size = AttrMapValue(isNumber),
        skinColor = AttrMapValue(isColorOrNone),
        eyeColor = AttrMapValue(isColorOrNone),
        mood = AttrMapValue(OneOf('happy','sad','ok')),
        )

    def __init__(self):
        self.x = 10
        self.y = 10
        self.size = 80
        self.skinColor = None
        self.eyeColor = colors.blue
        self.mood = 'happy'

    def demo(self):
        pass

    def draw(self):
        s = self.size  # abbreviate as we will use this a lot
        g = shapes.Group()
        g.transform = [1,0,0,1,self.x, self.y]

        # background
        g.add(shapes.Circle(s * 0.5, s * 0.5, s * 0.5, fillColor=self.skinColor))

        # left eye
        g.add(shapes.Circle(s * 0.35, s * 0.65, s * 0.1, fillColor=colors.white))
        g.add(shapes.Circle(s * 0.35, s * 0.65, s * 0.05, fillColor=self.eyeColor))

        # right eye
        g.add(shapes.Circle(s * 0.65, s * 0.65, s * 0.1, fillColor=colors.white))
        g.add(shapes.Circle(s * 0.65, s * 0.65, s * 0.05, fillColor=self.eyeColor))

        # nose
        g.add(shapes.Polygon(
            points=[s * 0.5, s * 0.6, s * 0.4, s * 0.3, s * 0.6, s * 0.3],
            fillColor=None))

        # mouth
        if self.mood == 'happy':
            offset = -0.05
        elif self.mood == 'sad':
            offset = +0.05
        else:
            offset = 0

        g.add(shapes.Polygon(
            points = [
                s * 0.3, s * 0.2, #left of mouth
                s * 0.7, s * 0.2, #right of mouth
                s * 0.6, s * (0.2 + offset), # the bit going up or down
                s * 0.4, s * (0.2 + offset) # the bit going up or down
                ],
            fillColor = colors.pink,
            strokeColor = colors.red,
            strokeWidth = s * 0.03
            ))

        return g


class TwoFaces(Widget):
    def __init__(self):
        self.faceOne = Face()
        self.faceOne.mood = "happy"
        self.faceTwo = Face()
        self.faceTwo.x = 100
        self.faceTwo.mood = "sad"

    def draw(self):
        """Just return a group"""
        return shapes.Group(self.faceOne, self.faceTwo)

    def demo(self):
        """The default case already looks good enough,
        no implementation needed here"""
        pass

class Sizer(Widget):
    "Container to show size of all enclosed objects"

    _attrMap = AttrMap(BASE=shapes.SolidShape,
        contents = AttrMapValue(isListOfShapes,desc="Contained drawable elements"),
        )
    def __init__(self, *elements):
        self.contents = []
        self.fillColor = colors.cyan
        self.strokeColor = colors.magenta

        for elem in elements:
            self.add(elem)

    def _addNamedNode(self,name,node):
        'if name is not None add an attribute pointing to node and add to the attrMap'
        if name:
            if name not in self._attrMap.keys():
                self._attrMap[name] = AttrMapValue(isValidChild)
            setattr(self, name, node)

    def add(self, node, name=None):
        """Appends non-None child node to the 'contents' attribute. In addition,
        if a name is provided, it is subsequently accessible by name
        """
        # propagates properties down
        if node is not None:
            assert isValidChild(node), "Can only add Shape or UserNode objects to a Group"
            self.contents.append(node)
            self._addNamedNode(name,node)

    def getBounds(self):
        # get bounds of each object
        if self.contents:
            b = []
            for elem in self.contents:
                b.append(elem.getBounds())
            return shapes.getRectsBounds(b)
        else:
            return (0,0,0,0)

    def draw(self):
        g = shapes.Group()
        (x1, y1, x2, y2) = self.getBounds()
        r = shapes.Rect(
            x = x1,
            y = y1,
            width = x2-x1,
            height = y2-y1,
            fillColor = self.fillColor,
            strokeColor = self.strokeColor
            )
        g.add(r)
        for elem in self.contents:
            g.add(elem)
        return g

def test():
    from reportlab.graphics.charts.piecharts import WedgeProperties
    wedges = TypedPropertyCollection(WedgeProperties)
    wedges.fillColor = colors.red
    wedges.setVector(fillColor=(colors.blue,colors.green,colors.white))
    print len(_ItemWrapper)

    d = shapes.Drawing(400, 200)
    tc = TwoCircles()
    d.add(tc)
    import renderPDF
    renderPDF.drawToFile(d, 'sample_widget.pdf', 'A Sample Widget')
    print 'saved sample_widget.pdf'

    d = shapes.Drawing(400, 200)
    f = Face()
    f.skinColor = colors.yellow
    f.mood = "sad"
    d.add(f, name='theFace')
    print 'drawing 1 properties:'
    d.dumpProperties()
    renderPDF.drawToFile(d, 'face.pdf', 'A Sample Widget')
    print 'saved face.pdf'

    d2 = d.expandUserNodes()
    renderPDF.drawToFile(d2, 'face_copy.pdf', 'An expanded drawing')
    print 'saved face_copy.pdf'
    print 'drawing 2 properties:'
    d2.dumpProperties()


if __name__=='__main__':
    test()
