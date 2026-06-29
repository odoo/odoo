__doc__="""helper for importing pdf structures into a ReportLab generated document
"""
from reportlab.pdfbase.pdfdoc import format, PDFObject, pdfdocEnc
from reportlab.lib.utils import strTypes

def _patternSequenceCheck(pattern_sequence):
    allowedTypes = strTypes if isinstance(strTypes, tuple) else (strTypes,)
    allowedTypes = allowedTypes + (PDFObject,PDFPatternIf)
    for x in pattern_sequence:
        if not isinstance(x,allowedTypes):
            if len(x)!=1:
                raise ValueError("sequence elts must be strings/bytes/PDFPatternIfs or singletons containing strings: "+ascii(x))
            if not isinstance(x[0],strTypes):
                raise ValueError("Singletons must contain strings/bytes or PDFObject instances only: "+ascii(x[0]))

class PDFPattern(PDFObject):
    __RefOnly__ = 1
    def __init__(self, pattern_sequence, **keywordargs):
        """
        Description of a kind of PDF object using a pattern.

        Pattern sequence should contain strings, singletons of form [string] or
        PDFPatternIf objects.
        Strings are literal strings to be used in the object.
        Singletons are names of keyword arguments to include.
        PDFpatternIf objects allow some conditionality.
        Keyword arguments can be non-instances which are substituted directly in string conversion,
        or they can be object instances in which case they should be pdfdoc.* style
        objects with a x.format(doc) method.
        Keyword arguments may be set on initialization or subsequently using __setitem__, before format.
        "constant object" instances can also be inserted in the patterns.
        """
        _patternSequenceCheck(pattern_sequence)
        self.pattern = pattern_sequence
        self.arguments = keywordargs

    def __setitem__(self, item, value):
        self.arguments[item] = value

    def __getitem__(self, item):
        return self.arguments[item]

    def eval(self,L):
        arguments = self.arguments
        document = self.__document
        for x in L:
            if isinstance(x,strTypes):
                yield pdfdocEnc(x)
            elif isinstance(x,PDFObject):
                yield x.format(document)
            elif isinstance(x,PDFPatternIf):
                result = list(self.eval(x.cond))
                cond = result and result[0]
                for z in self.eval(x.thenPart if cond else x.elsePart):
                    yield z
            else:
                name = x[0]
                value = arguments.get(name, None)
                if value is None:
                    raise ValueError("%s value not defined" % ascii(name))
                if isinstance(value,PDFObject):
                    yield format(value,document)
                elif isinstance(value,strTypes):
                    yield pdfdocEnc(value)
                else:
                    yield pdfdocEnc(str(value))

    def format(self, document):
        self.__document = document
        try:
            return b"".join(self.eval(self.pattern))
        finally:
            del self.__document

    def clone(self):
        c = object.__new__(self.__class__)
        c.pattern = self.pattern
        c.arguments = self.arguments
        return c

class PDFPatternIf:
    '''cond will be evaluated as [cond] in PDFpattern eval.
    It should evaluate to a list with value 0/1 etc etc.
    thenPart is a list to be evaluated if the cond evaulates true,
    elsePart is the false sequence.
    '''
    def __init__(self,cond,thenPart=[],elsePart=[]):
        if not isinstance(cond,list): cond = [cond]
        for x in cond, thenPart, elsePart:
            _patternSequenceCheck(x)
        self.cond = cond
        self.thenPart = thenPart
        self.elsePart = elsePart
