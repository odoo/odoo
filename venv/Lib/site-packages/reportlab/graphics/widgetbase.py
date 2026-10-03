#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/graphics/widgetbase.py
__version__='3.3.0'
__doc__='''Base class for user-defined graphical widgets'''

from reportlab.graphics import shapes
from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.validators import *
from reportlab.lib.attrmap import *
from weakref import ref as weakref_ref

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
                if key[0] != '_':
                    msg = "Unexpected attribute %s found in %s" % (key, self)
                    assert key in self._attrMap, msg
            for attr, metavalue in self._attrMap.items():
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
            if name[0:1] != '_':
                component = getattr(self, name)

                if recur and isValidChild(component):
                    # child object, get its properties too
                    childProps = component.getProperties(recur=recur)
                    for childKey, childValue in childProps.items():
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
        for name, value in propDict.items():
            parts = name.split('.', 1)
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
        for childName, childPropDict in childPropDicts.items():
            child = getattr(self, childName)
            child.setProperties(childPropDict)


    def dumpProperties(self, prefix=""):
        """Convenience. Lists them on standard output.  You
        may provide a prefix - mostly helps to generate code
        samples for documentation.
        """

        propList = list(self.getProperties().items())
        propList.sort()
        if prefix:
            prefix = prefix + '.'
        for (name, value) in propList:
            print('%s%s = %s' % (prefix, name, value))


class Widget(PropHolder, shapes.UserNode):
    """Base for all user-defined widgets.  Keep as simple as possible. Does
    not inherit from Shape so that we can rewrite shapes without breaking
    widgets and vice versa."""

    def _setKeywords(self,**kw):
        for k,v in kw.items():
            if k not in self.__dict__:
                setattr(self,k,v)

    def draw(self):
        msg = "draw() must be implemented for each Widget!"
        raise NotImplementedError(msg)

    def demo(self):
        msg = "demo() must be implemented for each Widget!"
        raise NotImplementedError(msg)

    def provideNode(self):
        return self.draw()

    def getBounds(self):
        "Return outer boundary as x1,y1,x2,y2.  Can be overridden for efficiency"
        return self.draw().getBounds()

class ScaleWidget(Widget):
    '''Contents with a scale and offset''' 
    _attrMap = AttrMap(
        x = AttrMapValue(isNumber,desc="x offset"),
        y = AttrMapValue(isNumber,desc="y offset"),
        scale = AttrMapValue(isNumber,desc="scale"),
        contents = AttrMapValue(None,desc="Contained drawable elements"),
        )
    def __init__(self,x=0,y=0,scale=1.0,contents=None):
        self.x = x
        self.y = y
        if not contents: contents=[]
        elif not isinstance(contents,(tuple,list)):
            contents = (contents,)
        self.contents = list(contents)
        self.scale = scale
    
    def draw(self):
        return shapes.Group(transform=(self.scale,0,0,self.scale,self.x,self.y),*self.contents)

_ItemWrapper={}

class CloneMixin:
    def clone(self,**kwds):
        n = self.__class__()
        n.__dict__.clear()
        n.__dict__.update(self.__dict__)
        if kwds: n.__dict__.update(kwds)
        return n

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

    We try and make sensible use of tuple indices.
        line[(3,x)] is backed by line[(3,)] == line[3] & line
    """

    def __init__(self, exampleClass, **kwds):
        #give it same validation rules as what it holds
        self.__dict__['_value'] = exampleClass(**kwds)
        self.__dict__['_children'] = {}

    def wKlassFactory(self,Klass):
        class WKlass(Klass,CloneMixin):
            def __getattr__(self,name):
                try:
                    return self.__class__.__bases__[0].__getattr__(self,name)
                except:
                    parent = self.parent
                    c = parent._children
                    x = self.__propholder_index__
                    while x:
                        if x in c:
                            return getattr(c[x],name)
                        x = x[:-1]
                    return getattr(parent,name)
            @property
            def parent(self):
                return self.__propholder_parent__()
        return WKlass

    def __getitem__(self, x):
        x = tuple(x) if isinstance(x,(tuple,list)) else (x,)
        try:
            return self._children[x]
        except KeyError:
            Klass = self._value.__class__
            if Klass in _ItemWrapper:
                WKlass = _ItemWrapper[Klass]
            else:
                _ItemWrapper[Klass] = WKlass = self.wKlassFactory(Klass)

            child = WKlass()
            
            for i in filter(lambda x,K=list(child.__dict__.keys()): x in K,list(child._attrMap.keys())):
                del child.__dict__[i]
            child.__dict__.update(dict(
                                    __propholder_parent__ = weakref_ref(self),
                                    __propholder_index__ = x[:-1])
                                    )

            self._children[x] = child
            return child

    def __contains__(self,key):
        return (tuple(key) if isinstance(key,(tuple,list)) else (key,)) in self._children

    def __setitem__(self, key, value):
        assert isinstance(value, self._value.__class__), (
            "This collection can only hold objects of type %s" % self._value.__class__.__name__)

    def __len__(self):
        return len(list(self._children.keys()))

    def getProperties(self,recur=1):
        # return any children which are defined and whatever
        # differs from the parent
        props = {}

        for key, value in self._value.getProperties(recur=recur).items():
            props['%s' % key] = value

        for idx in self._children.keys():
            childProps = self._children[idx].getProperties(recur=recur)
            for key, value in childProps.items():
                if not hasattr(self,key) or getattr(self, key)!=value:
                    newKey = '[%s].%s' % (idx if len(idx)>1 else idx[0], key)
                    props[newKey] = value
        return props

    def setVector(self,**kw):
        for name, value in kw.items():
            for i, v in enumerate(value):
                setattr(self[i],name,v)

    def __getattr__(self,name):
        return getattr(self._value,name)

    def __setattr__(self,name,value):
        return setattr(self._value,name,value)

    def checkAttr(self, key, a, default=None):
        return getattr(self[key], a, default) if key in self else default

def tpcGetItem(obj,x):
    '''return obj if it's not a TypedPropertyCollection else obj[x]'''
    return obj[x] if isinstance(obj,TypedPropertyCollection) else obj

def isWKlass(obj):
    if not hasattr(obj,'__propholder_parent__'): return
    ph = obj.__propholder_parent__
    if not isinstance(ph,weakref_ref): return
    return isinstance(ph(),TypedPropertyCollection)

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
        strokeWidth = AttrMapValue(isNumber,desc='width of the stroke line'),
        strokeLineCap = AttrMapValue(isNumber,desc='Line cap 0=butt, 1=round & 2=square',advancedUsage=1),
        strokeLineJoin = AttrMapValue(isNumber,desc='Line join 0=miter, 1=round & 2=bevel',advancedUsage=1),
        strokeMiterLimit = AttrMapValue(None,desc='miter limit control miter line joins',advancedUsage=1),
        strokeDashArray = AttrMapValue(isListOfNumbersOrNone,desc='dashing patterns e.g. (1,3)'),
        strokeOpacity = AttrMapValue(isNumber,desc='level of transparency (alpha) accepts values between 0..1',advancedUsage=1),
        strokeColor = AttrMapValue(isColorOrNone,desc='the color of the stroke'),
        fillColor = AttrMapValue(isColorOrNone,desc='the filling color'),
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
            if name not in list(self._attrMap.keys()):
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

class CandleStickProperties(PropHolder):
    _attrMap = AttrMap(
        strokeWidth = AttrMapValue(isNumber, desc='Width of a line.'),
        strokeColor = AttrMapValue(isColorOrNone, desc='Color of a line or border.'),
        strokeDashArray = AttrMapValue(isListOfNumbersOrNone, desc='Dash array of a line.'),
        crossWidth = AttrMapValue(isNumberOrNone,desc="cross line width",advancedUsage=1),
        crossLo = AttrMapValue(isNumberOrNone,desc="cross line low value",advancedUsage=1),
        crossHi = AttrMapValue(isNumberOrNone,desc="cross line high value",advancedUsage=1),
        boxWidth = AttrMapValue(isNumberOrNone,desc="width of the box part",advancedUsage=1),
        boxFillColor = AttrMapValue(isColorOrNone, desc='fill color of box'),
        boxStrokeColor = AttrMapValue(NotSetOr(isColorOrNone), desc='stroke color of box'),
        boxStrokeDashArray = AttrMapValue(NotSetOr(isListOfNumbersOrNone), desc='Dash array of the box.'),
        boxStrokeWidth = AttrMapValue(NotSetOr(isNumber), desc='Width of the box lines.'),
        boxLo = AttrMapValue(isNumberOrNone,desc="low value of the box",advancedUsage=1),
        boxMid = AttrMapValue(isNumberOrNone,desc="middle box line value",advancedUsage=1),
        boxHi = AttrMapValue(isNumberOrNone,desc="high value of the box",advancedUsage=1),
        boxSides = AttrMapValue(isBoolean,desc="whether to show box sides",advancedUsage=1),
        position = AttrMapValue(isNumberOrNone,desc="position of the candle",advancedUsage=1),
        chart = AttrMapValue(None,desc="our chart",advancedUsage=1),
        candleKind = AttrMapValue(OneOf('vertical','horizontal'),desc="candle direction",advancedUsage=1),
        axes = AttrMapValue(SequenceOf(isString,emptyOK=0,lo=2,hi=2),desc="candle direction",advancedUsage=1),
        )

    def __init__(self,**kwds):
        self.strokeWidth = kwds.pop('strokeWidth',1)
        self.strokeColor = kwds.pop('strokeColor',colors.black)
        self.strokeDashArray = kwds.pop('strokeDashArray',None)
        self.crossWidth = kwds.pop('crossWidth',5)
        self.crossLo = kwds.pop('crossLo',None)
        self.crossHi = kwds.pop('crossHi',None)
        self.boxWidth = kwds.pop('boxWidth',None)
        self.boxFillColor = kwds.pop('boxFillColor',None)
        self.boxStrokeColor =kwds.pop('boxStrokeColor',NotSetOr._not_set) 
        self.boxStrokeWidth =kwds.pop('boxStrokeWidth',NotSetOr._not_set) 
        self.boxStrokeDashArray =kwds.pop('boxStrokeDashArray',NotSetOr._not_set) 
        self.boxLo = kwds.pop('boxLo',None)
        self.boxMid = kwds.pop('boxMid',None)
        self.boxHi = kwds.pop('boxHi',None)
        self.boxSides = kwds.pop('boxSides',True)
        self.position = kwds.pop('position',None)
        self.candleKind = kwds.pop('candleKind','vertical')
        self.axes = kwds.pop('axes',['categoryAxis','valueAxis'])
        chart = kwds.pop('chart',None)
        self.chart = weakref_ref(chart) if chart else (lambda:None)

    def __call__(self,_x,_y,_size,_color):
        '''the symbol interface'''
        chart = self.chart()
        xA = getattr(chart,self.axes[0])
        _xScale = getattr(xA,'midScale',None)
        if not _xScale: _xScale = getattr(xA,'scale')
        xScale = lambda x: _xScale(x) if x is not None else None
        yA = getattr(chart,self.axes[1])
        _yScale = getattr(yA,'midScale',None)
        if not _yScale: _yScale = getattr(yA,'scale')
        yScale = lambda x: _yScale(x) if x is not None else None
        G = shapes.Group().add
        strokeWidth = self.strokeWidth
        strokeColor = self.strokeColor
        strokeDashArray = self.strokeDashArray
        crossWidth = self.crossWidth
        crossLo = yScale(self.crossLo)
        crossHi = yScale(self.crossHi)
        boxWidth = self.boxWidth
        boxFillColor = self.boxFillColor
        boxStrokeColor = NotSetOr.conditionalValue(self.boxStrokeColor,strokeColor)
        boxStrokeWidth = NotSetOr.conditionalValue(self.boxStrokeWidth,strokeWidth)
        boxStrokeDashArray = NotSetOr.conditionalValue(self.boxStrokeDashArray,strokeDashArray)
        boxLo = yScale(self.boxLo)
        boxMid = yScale(self.boxMid)
        boxHi = yScale(self.boxHi)
        position = xScale(self.position)
        candleKind = self.candleKind
        haveBox = None not in (boxWidth,boxLo,boxHi)
        haveLine = None not in (crossLo,crossHi)
        def aLine(x0,y0,x1,y1):
            if candleKind!='vertical':
                x0,y0 = y0,x0
                x1,y1 = y1,x1
            G(shapes.Line(x0,y0,x1,y1,strokeWidth=strokeWidth,strokeColor=strokeColor,strokeDashArray=strokeDashArray))
        if haveBox:
            boxLo, boxHi = min(boxLo,boxHi), max(boxLo,boxHi)
        if haveLine:
            crossLo, crossHi = min(crossLo,crossHi), max(crossLo,crossHi)
            if not haveBox or crossLo>=boxHi or crossHi<=boxLo:
                aLine(position,crossLo,position,crossHi)
                if crossWidth is not None:
                    aLine(position-crossWidth*0.5,crossLo,position+crossWidth*0.5,crossLo)
                    aLine(position-crossWidth*0.5,crossHi,position+crossWidth*0.5,crossHi)
            elif haveBox:
                if crossLo<boxLo:
                    aLine(position,crossLo,position,boxLo)
                    aLine(position-crossWidth*0.5,crossLo,position+crossWidth*0.5,crossLo)
                if crossHi>boxHi:
                    aLine(position,boxHi,position,crossHi)
                    aLine(position-crossWidth*0.5,crossHi,position+crossWidth*0.5,crossHi)
        if haveBox:
            x = position - boxWidth*0.5
            y = boxLo
            h = boxHi - boxLo
            w = boxWidth
            if candleKind!='vertical':
                x, y, w, h = y, x, h, w
            G(shapes.Rect(x,y,w,h,strokeColor=boxStrokeColor if self.boxSides else None,strokeWidth=boxStrokeWidth,strokeDashArray=boxStrokeDashArray,fillColor=boxFillColor))
            if not self.boxSides:
                aLine(position-0.5*boxWidth,boxHi,position+0.5*boxWidth,boxHi)
                aLine(position-0.5*boxWidth,boxLo,position+0.5*boxWidth,boxLo)

            if boxMid is not None:
                aLine(position-0.5*boxWidth,boxMid,position+0.5*boxWidth,boxMid)
        return G.__self__

def CandleSticks(**kwds):
    return TypedPropertyCollection(CandleStickProperties,**kwds)

def test():
    from reportlab.graphics.charts.piecharts import WedgeProperties
    wedges = TypedPropertyCollection(WedgeProperties)
    wedges.fillColor = colors.red
    wedges.setVector(fillColor=(colors.blue,colors.green,colors.white))
    print(len(_ItemWrapper))

    d = shapes.Drawing(400, 200)
    tc = TwoCircles()
    d.add(tc)
    from reportlab.graphics import renderPDF
    renderPDF.drawToFile(d, 'sample_widget.pdf', 'A Sample Widget')
    print('saved sample_widget.pdf')

    d = shapes.Drawing(400, 200)
    f = Face()
    f.skinColor = colors.yellow
    f.mood = "sad"
    d.add(f, name='theFace')
    print('drawing 1 properties:')
    d.dumpProperties()
    renderPDF.drawToFile(d, 'face.pdf', 'A Sample Widget')
    print('saved face.pdf')

    d2 = d.expandUserNodes()
    renderPDF.drawToFile(d2, 'face_copy.pdf', 'An expanded drawing')
    print('saved face_copy.pdf')
    print('drawing 2 properties:')
    d2.dumpProperties()


if __name__=='__main__':
    test()
