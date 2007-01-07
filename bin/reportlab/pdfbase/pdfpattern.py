"""
helper for importing pdf structures into a ReportLab generated document
"""
from reportlab.pdfbase.pdfdoc import format

import string

class PDFPattern:
    __RefOnly__ = 1
    def __init__(self, pattern_sequence, **keywordargs):
        """
        Description of a kind of PDF object using a pattern.

        Pattern sequence should contain strings or singletons of form [string].
        Strings are literal strings to be used in the object.
        Singletons are names of keyword arguments to include.
        Keyword arguments can be non-instances which are substituted directly in string conversion,
        or they can be object instances in which case they should be pdfdoc.* style
        objects with a x.format(doc) method.
        Keyword arguments may be set on initialization or subsequently using __setitem__, before format.
        "constant object" instances can also be inserted in the patterns.
        """
        self.pattern = pattern_sequence
        self.arguments = keywordargs
        from types import StringType, InstanceType
        toptypes = (StringType, InstanceType)
        for x in pattern_sequence:
            if type(x) not in toptypes:
                if len(x)!=1:
                    raise ValueError, "sequence elts must be strings or singletons containing strings: "+repr(x)
                if type(x[0]) is not StringType:
                    raise ValueError, "Singletons must contain strings or instances only: "+repr(x[0])
    def __setitem__(self, item, value):
        self.arguments[item] = value
    def __getitem__(self, item):
        return self.arguments[item]
    def format(self, document):
        L = []
        arguments = self.arguments
        from types import StringType, InstanceType
        for x in self.pattern:
            tx = type(x)
            if tx is StringType:
                L.append(x)
            elif tx is InstanceType:
                L.append( x.format(document) )
            else:
                name = x[0]
                value = arguments.get(name, None)
                if value is None:
                    raise ValueError, "%s value not defined" % repr(name)
                if type(value) is InstanceType:
                    #L.append( value.format(document) )
                    L.append(format(value, document))
                else:
                    L.append( str(value) )
        return string.join(L, "")


