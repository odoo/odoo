#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/lib/validators.py
__version__='3.5.33'
__doc__="""Standard verifying functions used by attrmap."""

import codecs, re
from reportlab.lib.utils import isSeq, isBytes, isStr
from reportlab.lib import colors
try:
    _re_Pattern = re.Pattern
except AttributeError:
    _re_Pattern = re._pattern_type

class Percentage(float):
    pass

class Validator:
    "base validator class"
    def __call__(self,x):
        return self.test(x)

    def __str__(self):
        return getattr(self,'_str',self.__class__.__name__)

    def normalize(self,x):
        return x

    def normalizeTest(self,x):
        try:
            self.normalize(x)
            return True
        except:
            return False

class _isAnything(Validator):
    def test(self,x):
        return True

class _isNothing(Validator):
    def test(self,x):
        return False

class _isBoolean(Validator):
    def test(self,x):
        if isinstance(int,bool): return x in (0,1)
        return self.normalizeTest(x)

    def normalize(self,x):
        if x in (0,1): return x
        try:
            S = x.upper()
        except:
            raise ValueError('Must be boolean not %s' % ascii(s))
        if S in ('YES','TRUE'): return True
        if S in ('NO','FALSE',None): return False
        raise ValueError('Must be boolean not %s' % ascii(s))

class _isString(Validator):
    def test(self,x):
        return isStr(x)

class _isCodec(Validator):
    def test(self,x):
        if not isStr(x):
            return False
        try:
            a,b,c,d = codecs.lookup(x)
            return True
        except LookupError:
            return False

class _isNumber(Validator):
    def test(self,x):
        if isinstance(x,(float,int)): return True
        return self.normalizeTest(x)

    def normalize(self,x):
        try:
            return float(x)
        except:
            return int(x)

class _isInt(Validator):
    def test(self,x):
        if not isinstance(x,int) and not isStr(x): return False
        return self.normalizeTest(x)

    def normalize(self,x):
        return int(x.decode('utf8') if isBytes(x) else x)

class _isNumberOrNone(_isNumber):
    def test(self,x):
        return x is None or isNumber(x)

    def normalize(self,x):
        if x is None: return x
        return _isNumber.normalize(x)

class _isListOfNumbersOrNone(Validator):
    "ListOfNumbersOrNone validator class."
    def test(self, x):
        if x is None: return True
        return isListOfNumbers(x)

class isNumberInRange(_isNumber):
    def __init__(self, min, max):
        self.min = min
        self.max = max

    def test(self, x):
        try:
            n = self.normalize(x)
            if self.min <= n <= self.max:
                return True
        except ValueError:
            pass
        return False


class _isListOfShapes(Validator):
    "ListOfShapes validator class."
    def test(self, x):
        from reportlab.graphics.shapes import Shape
        if isSeq(x):
            answer = 1
            for e in x:
                if not isinstance(e, Shape):
                    answer = 0
            return answer
        else:
            return False

class _isListOfStringsOrNone(Validator):
    "ListOfStringsOrNone validator class."

    def test(self, x):
        if x is None: return True
        return isListOfStrings(x)

class _isTransform(Validator):
    "Transform validator class."
    def test(self, x):
        if isSeq(x):
            if len(x) == 6:
                for element in x:
                    if not isNumber(element):
                        return False
                return True
            else:
                return False
        else:
            return False

class _isColor(Validator):
    "Color validator class."
    def test(self, x):
        return isinstance(x, colors.Color)

class _isColorOrNone(Validator):
    "ColorOrNone validator class."
    def test(self, x):
        if x is None: return True
        return isColor(x)

from reportlab.lib.normalDate import NormalDate
class _isNormalDate(Validator):
    def test(self,x):
        if isinstance(x,NormalDate):
            return True
        return x is not None and self.normalizeTest(x)

    def normalize(self,x):
        return NormalDate(x)

class _isValidChild(Validator):
    "ValidChild validator class."
    def test(self, x):
        """Is this child allowed in a drawing or group?
        I.e. does it descend from Shape or UserNode?
        """

        from reportlab.graphics.shapes import UserNode, Shape
        return isinstance(x, UserNode) or isinstance(x, Shape)

class _isValidChildOrNone(_isValidChild):
    def test(self,x):
        return _isValidChild.test(self,x) or x is None

class _isCallable(Validator):
    def test(self, x):
        return hasattr(x,'__call__')

class OneOf(Validator):
    """Make validator functions for list of choices.

    Usage:
    f = reportlab.lib.validators.OneOf('happy','sad')
    or
    f = reportlab.lib.validators.OneOf(('happy','sad'))
    f('sad'),f('happy'), f('grumpy')
    (1,1,0)
    """
    def __init__(self, enum,*args):
        if isSeq(enum):
            if args!=():
                raise ValueError("Either all singleton args or a single sequence argument")
            self._enum = tuple(enum)+args
        else:
            self._enum = (enum,)+args
        self._patterns = tuple((_ for _ in self._enum if isinstance(_,_re_Pattern)))
        if self._patterns:
            self._enum =  tuple((_ for _ in self._enum if not isinstance(_,_re_Pattern)))
            self.test = self._test_patterns

    def test(self, x):
        return x in self._enum

    def _test_patterns(self, x):
        v = x in self._enum
        #print(f'{x=} {self._enum=!r} {self._patterns=!r} {v=}')
        if v: return True
        for p in self._patterns:
            v = p.match(x)
            if v: return True
        return False

class SequenceOf(Validator):
    def __init__(self,elemTest,name=None,emptyOK=1, NoneOK=0, lo=0,hi=0x7fffffff):
        self._elemTest = elemTest
        self._emptyOK = emptyOK
        self._NoneOK = NoneOK
        self._lo, self._hi = lo, hi
        if name: self._str = name

    def test(self, x):
        if not isSeq(x):
            if x is None: return self._NoneOK
            return False
        if x==[] or x==():
            return self._emptyOK
        elif not self._lo<=len(x)<=self._hi: return False
        for e in x:
            if not self._elemTest(e): return False
        return True

class EitherOr(Validator):
    def __init__(self,tests,name=None):
        if not isSeq(tests): tests = (tests,)
        self._tests = tests
        if name: self._str = name

    def test(self, x):
        for t in self._tests:
            if t(x): return True
        return False

class NoneOr(EitherOr):
    def test(self, x):
        return x is None or super().test(x)

class NotSetOr(EitherOr):
    _not_set = object()
    def test(self, x):
        return x is NotSetOr._not_set or super().test(x)

    @staticmethod
    def conditionalValue(v,a):
        return a if v is NotSetOr._not_set else v

class _isNotSet(Validator):
    def test(self,x):
        return x is NotSetOr._not_set

class Auto(Validator):
    def __init__(self,**kw):
        self.__dict__.update(kw)

    def test(self,x):
        return x is self.__class__ or isinstance(x,self.__class__)

class AutoOr(EitherOr):
    def test(self,x):
        return isAuto(x) or super().test(x)

class isInstanceOf(Validator):
    def __init__(self,klass=None):
        self._klass = klass
    def test(self,x):
        return isinstance(x,self._klass)

class isSubclassOf(Validator):
    def __init__(self,klass=None):
        self._klass = klass
    def test(self,x):
        return isinstance(x,type) and issubclass(x,self._klass)

class matchesPattern(Validator):
    """Matches value, or its string representation, against regex"""
    def __init__(self, pattern):
        self._pattern = re.compile(pattern)

    def test(self,x):
        x = str(x)
        print('testing %s against %s' % (x, self._pattern))
        return (self._pattern.match(x) != None)

class DerivedValue:
    """This is used for magic values which work themselves out.
    An example would be an "inherit" property, so that one can have

      drawing.chart.categoryAxis.labels.fontName = inherit

    and pick up the value from the top of the drawing.
    Validators will permit this provided that a value can be pulled
    in which satisfies it.  And the renderer will have special
    knowledge of these so they can evaluate themselves.
    """
    def getValue(self, renderer, attr):
        """Override this.  The renderers will pass the renderer,
        and the attribute name.  Algorithms can then backtrack up
        through all the stuff the renderer provides, including
        a correct stack of parent nodes."""
        return None

class Inherit(DerivedValue):
    def __repr__(self):
        return "inherit"

    def getValue(self, renderer, attr):
        return renderer.getStateValue(attr)
inherit = Inherit()

class NumericAlign(str):
    '''for creating the numeric string value for anchors etc etc
    dp is the character to align on (the last occurrence will be used)
    dpLen is the length of characters after the dp
    '''
    def __new__(cls,dp='.',dpLen=0):
        self = str.__new__(cls,'numeric')
        self._dp=dp
        self._dpLen = dpLen
        return self


isAuto = Auto()
isBoolean = _isBoolean()
isString = _isString()
isCodec = _isCodec()
isNumber = _isNumber()
isInt = _isInt()
isNoneOrInt = NoneOr(isInt,'isNoneOrInt')
isNumberOrNone = _isNumberOrNone()
isTextAnchor = OneOf('start','middle','end','boxauto')
isListOfNumbers = SequenceOf(isNumber,'isListOfNumbers')
isListOfNoneOrNumber = SequenceOf(isNumberOrNone,'isListOfNoneOrNumber')
isListOfListOfNoneOrNumber = SequenceOf(isListOfNoneOrNumber,'isListOfListOfNoneOrNumber')
isListOfNumbersOrNone = _isListOfNumbersOrNone()
isListOfShapes = _isListOfShapes()
isListOfStrings = SequenceOf(isString,'isListOfStrings')
isListOfStringsOrNone = _isListOfStringsOrNone()
isTransform = _isTransform()
isColor = _isColor()
isListOfColors = SequenceOf(isColor,'isListOfColors')
isColorOrNone = _isColorOrNone()
isShape = isValidChild = _isValidChild()
isNoneOrShape = isValidChildOrNone = _isValidChildOrNone()
isAnything = _isAnything()
isNothing = _isNothing()
isXYCoord = SequenceOf(isNumber,lo=2,hi=2,emptyOK=0)
isBoxAnchor = OneOf('nw','n','ne','w','c','e','sw','s','se', 'autox', 'autoy')
isNoneOrString = NoneOr(isString,'NoneOrString')
isNoneOrListOfNoneOrStrings=SequenceOf(isNoneOrString,'isNoneOrListOfNoneOrStrings',NoneOK=1)
isListOfNoneOrString=SequenceOf(isNoneOrString,'isListOfNoneOrString',NoneOK=0)
isNoneOrListOfNoneOrNumbers=SequenceOf(isNumberOrNone,'isNoneOrListOfNoneOrNumbers',NoneOK=1)
isCallable = _isCallable()
isNoneOrCallable = NoneOr(isCallable)
isStringOrCallable=EitherOr((isString,isCallable),'isStringOrCallable')
isStringOrCallableOrNone=NoneOr(isStringOrCallable,'isStringOrCallableNone')
isStringOrNone=NoneOr(isString,'isStringOrNone')
isNormalDate=_isNormalDate()
isNotSet=_isNotSet()
