#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/lib/styles.py
__version__='3.3.0'
__doc__='''Classes for ParagraphStyle and similar things.

A style is a collection of attributes, but with some extra features
to allow 'inheritance' from a parent, and to ensure nobody makes
changes after construction.

ParagraphStyle shows all the attributes available for formatting
paragraphs.

getSampleStyleSheet()  returns a stylesheet you can use for initial
development, with a few basic heading and text styles.
'''
__all__=(
        'PropertySet',
        'ParagraphStyle',
        'LineStyle',
        'ListStyle',
        'StyleSheet1',
        'getSampleStyleSheet',
        )
from reportlab.lib.colors import black
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.fonts import tt2ps
from reportlab.rl_config import canvas_basefontname as _baseFontName, \
                                underlineWidth as _baseUnderlineWidth, \
                                underlineOffset as _baseUnderlineOffset, \
                                underlineGap as _baseUnderlineGap, \
                                strikeWidth as _baseStrikeWidth, \
                                strikeOffset as _baseStrikeOffset, \
                                strikeGap as _baseStrikeGap, \
                                spaceShrinkage as _spaceShrinkage, \
                                platypus_link_underline as _platypus_link_underline, \
                                hyphenationLang as _hyphenationLang, \
                                hyphenationMinWordLength as _hyphenationMinWordLength, \
                                uriWasteReduce as _uriWasteReduce, \
                                embeddedHyphenation as _embeddedHyphenation
_baseFontNameB = tt2ps(_baseFontName,1,0)
_baseFontNameI = tt2ps(_baseFontName,0,1)
_baseFontNameBI = tt2ps(_baseFontName,1,1)

###########################################################
# This class provides an 'instance inheritance'
# mechanism for its descendants, simpler than acquisition
# but not as far-reaching
###########################################################
class PropertySet:
    defaults = {}

    def __init__(self, name, parent=None, **kw):
        """When initialized, it copies the class defaults;
        then takes a copy of the attributes of the parent
        if any.  All the work is done in init - styles
        should cost little to use at runtime."""
        # step one - validate the hell out of it
        assert 'name' not in self.defaults, "Class Defaults may not contain a 'name' attribute"
        assert 'parent' not in self.defaults, "Class Defaults may not contain a 'parent' attribute"
        if parent:
            assert parent.__class__ == self.__class__, "Parent style %s must have same class as new style %s" % (parent.__class__.__name__,self.__class__.__name__)

        #step two
        self.name = name
        self.parent = parent
        self.__dict__.update(self.defaults)

        #step two - copy from parent if any.  Try to be
        # very strict that only keys in class defaults are
        # allowed, so they cannot inherit
        self.refresh()
        self._setKwds(**kw)

    def _setKwds(self,**kw):
        #step three - copy keywords if any
        for key, value in kw.items():
             self.__dict__[key] = value

    def __repr__(self):
        return "<%s '%s'>" % (self.__class__.__name__, self.name)

    def refresh(self):
        """re-fetches attributes from the parent on demand;
        use if you have been hacking the styles.  This is
        used by __init__"""
        if self.parent:
            for key, value in self.parent.__dict__.items():
                if (key not in ['name','parent']):
                    self.__dict__[key] = value

    def listAttrs(self, indent=''):
        print(indent + 'name =', self.name)
        print(indent + 'parent =', self.parent)
        keylist = list(self.__dict__.keys())
        keylist.sort()
        keylist.remove('name')
        keylist.remove('parent')
        for key in keylist:
            value = self.__dict__.get(key, None)
            print(indent + '%s = %s' % (key, value))

    def clone(self, name, parent=None, **kwds):
        r = self.__class__(name,parent)
        r.__dict__ = self.__dict__.copy()
        r.name = name
        r.parent = parent is None and self or parent
        r._setKwds(**kwds)
        return r

class ParagraphStyle(PropertySet):
    defaults = {
        'fontName':_baseFontName,
        'fontSize':10,
        'leading':12,
        'leftIndent':0,
        'rightIndent':0,
        'firstLineIndent':0,
        'alignment':TA_LEFT,
        'spaceBefore':0,
        'spaceAfter':0,
        'bulletFontName':_baseFontName,
        'bulletFontSize':10,
        'bulletIndent':0,
        #'bulletColor':black,
        'textColor': black,
        'backColor':None,
        'wordWrap':None,        #None means do nothing special
                                #CJK use Chinese Line breaking
                                #LTR RTL use left to right / right to left
                                #with support from pyfribi2 if available
        'borderWidth': 0,
        'borderPadding': 0,
        'borderColor': None,
        'borderRadius': None,
        'allowWidows': 1,
        'allowOrphans': 0,
        'textTransform':None,   #uppercase lowercase (captitalize not yet) or None or absent
        'endDots':None,         #dots on the last line of left/right justified paras
                                #string or object with text and optional fontName, fontSize, textColor & backColor
                                #dy
        'splitLongWords':1,     #make best efforts to split long words
        'underlineWidth': _baseUnderlineWidth,  #underline width default
        'bulletAnchor': 'start',    #where the bullet is anchored ie start, middle, end or numeric
        'justifyLastLine': 0,   #n allow justification on the last line for more than n words 0 means don't bother
        'justifyBreaks': 0,     #justify lines broken with <br/>
        'spaceShrinkage': _spaceShrinkage,  #allow shrinkage of percentage of space to fit on line
        'strikeWidth': _baseStrikeWidth,    #stroke width default
        'underlineOffset': _baseUnderlineOffset,    #fraction of fontsize to offset underlines
        'underlineGap': _baseUnderlineGap,      #gap for double/triple underline
        'strikeOffset': _baseStrikeOffset,  #fraction of fontsize to offset strikethrough
        'strikeGap': _baseStrikeGap,        #gap for double/triple strike
        'linkUnderline': _platypus_link_underline,
        'underlineColor':   None,
        'strikeColor': None,
        'hyphenationLang': _hyphenationLang,
        #'hyphenationMinWordLength': _hyphenationMinWordLength,
        'embeddedHyphenation': _embeddedHyphenation,
        'uriWasteReduce': _uriWasteReduce,
        }

class LineStyle(PropertySet):
    defaults = {
        'width':1,
        'color': black
        }
    def prepareCanvas(self, canvas):
        """You can ask a LineStyle to set up the canvas for drawing
        the lines."""
        canvas.setLineWidth(1)
        #etc. etc.

class ListStyle(PropertySet):
    defaults = dict(
                leftIndent=18,
                rightIndent=0,
                bulletAlign='left',
                bulletType='1',
                bulletColor=black,
                bulletFontName='Helvetica',
                bulletFontSize=12,
                bulletOffsetY=0,
                bulletDedent='auto',
                bulletDir='ltr',
                bulletFormat=None,
                start=None,         #starting value for a list; if a list then the start sequence
                )

_stylesheet1_undefined = object()

class StyleSheet1:
    """
    This may or may not be used.  The idea is to:
    
    1. slightly simplify construction of stylesheets;
    
    2. enforce rules to validate styles when added
       (e.g. we may choose to disallow having both
       'heading1' and 'Heading1' - actual rules are
       open to discussion);
       
    3. allow aliases and alternate style lookup
       mechanisms
       
    4. Have a place to hang style-manipulation
       methods (save, load, maybe support a GUI
       editor)
   
    Access is via getitem, so they can be
    compatible with plain old dictionaries.
    """

    def __init__(self):
        self.byName = {}
        self.byAlias = {}

    def __getitem__(self, key):
        try:
            return self.byAlias[key]
        except KeyError:
            try:
                return self.byName[key]
            except KeyError:
                raise KeyError("Style '%s' not found in stylesheet" % key)

    def get(self,key,default=_stylesheet1_undefined):
        try:
            return self[key]
        except KeyError:
            if default!=_stylesheet1_undefined: return default
            raise

    def __contains__(self, key):
        return key in self.byAlias or key in self.byName

    def has_key(self,key):
        return key in self

    def add(self, style, alias=None):
        key = style.name
        if key in self.byName:
            raise KeyError("Style '%s' already defined in stylesheet" % key)
        if key in self.byAlias:
            raise KeyError("Style name '%s' is already an alias in stylesheet" % key)

        if alias:
            if alias in self.byName:
                raise KeyError("Style '%s' already defined in stylesheet" % alias)
            if alias in self.byAlias:
                raise KeyError("Alias name '%s' is already an alias in stylesheet" % alias)
        #passed all tests?  OK, add it
        self.byName[key] = style
        if alias:
            self.byAlias[alias] = style

    def list(self):
        styles = list(self.byName.items())
        styles.sort()
        alii = {}
        for (alias, style) in list(self.byAlias.items()):
            alii[style] = alias
        for (name, style) in styles:
            alias = alii.get(style, None)
            print(name, alias)
            style.listAttrs('    ')
            print()

def testStyles():
    pNormal = ParagraphStyle('Normal',None)
    pNormal.fontName = _baseFontName
    pNormal.fontSize = 12
    pNormal.leading = 14.4

    pNormal.listAttrs()
    print()
    pPre = ParagraphStyle('Literal', pNormal)
    pPre.fontName = 'Courier'
    pPre.listAttrs()
    return pNormal, pPre

def getSampleStyleSheet():
    """Returns a stylesheet object"""
    stylesheet = StyleSheet1()

    stylesheet.add(ParagraphStyle(name='Normal',
                                  fontName=_baseFontName,
                                  fontSize=10,
                                  leading=12)
                   )

    stylesheet.add(ParagraphStyle(name='BodyText',
                                  parent=stylesheet['Normal'],
                                  spaceBefore=6)
                   )
    stylesheet.add(ParagraphStyle(name='Italic',
                                  parent=stylesheet['BodyText'],
                                  fontName = _baseFontNameI)
                   )

    stylesheet.add(ParagraphStyle(name='Heading1',
                                  parent=stylesheet['Normal'],
                                  fontName = _baseFontNameB,
                                  fontSize=18,
                                  leading=22,
                                  spaceAfter=6),
                   alias='h1')

    stylesheet.add(ParagraphStyle(name='Title',
                                  parent=stylesheet['Normal'],
                                  fontName = _baseFontNameB,
                                  fontSize=18,
                                  leading=22,
                                  alignment=TA_CENTER,
                                  spaceAfter=6),
                   alias='title')

    stylesheet.add(ParagraphStyle(name='Heading2',
                                  parent=stylesheet['Normal'],
                                  fontName = _baseFontNameB,
                                  fontSize=14,
                                  leading=18,
                                  spaceBefore=12,
                                  spaceAfter=6),
                   alias='h2')

    stylesheet.add(ParagraphStyle(name='Heading3',
                                  parent=stylesheet['Normal'],
                                  fontName = _baseFontNameBI,
                                  fontSize=12,
                                  leading=14,
                                  spaceBefore=12,
                                  spaceAfter=6),
                   alias='h3')

    stylesheet.add(ParagraphStyle(name='Heading4',
                                  parent=stylesheet['Normal'],
                                  fontName = _baseFontNameBI,
                                  fontSize=10,
                                  leading=12,
                                  spaceBefore=10,
                                  spaceAfter=4),
                   alias='h4')

    stylesheet.add(ParagraphStyle(name='Heading5',
                                  parent=stylesheet['Normal'],
                                  fontName = _baseFontNameB,
                                  fontSize=9,
                                  leading=10.8,
                                  spaceBefore=8,
                                  spaceAfter=4),
                   alias='h5')

    stylesheet.add(ParagraphStyle(name='Heading6',
                                  parent=stylesheet['Normal'],
                                  fontName = _baseFontNameB,
                                  fontSize=7,
                                  leading=8.4,
                                  spaceBefore=6,
                                  spaceAfter=2),
                   alias='h6')

    stylesheet.add(ParagraphStyle(name='Bullet',
                                  parent=stylesheet['Normal'],
                                  firstLineIndent=0,
                                  spaceBefore=3),
                   alias='bu')

    stylesheet.add(ParagraphStyle(name='Definition',
                                  parent=stylesheet['Normal'],
                                  firstLineIndent=0,
                                  leftIndent=36,
                                  bulletIndent=0,
                                  spaceBefore=6,
                                  bulletFontName=_baseFontNameBI),
                   alias='df')

    stylesheet.add(ParagraphStyle(name='Code',
                                  parent=stylesheet['Normal'],
                                  fontName='Courier',
                                  fontSize=8,
                                  leading=8.8,
                                  firstLineIndent=0,
                                  leftIndent=36,
                                  hyphenationLang=''))

    stylesheet.add(ListStyle(name='UnorderedList',
                                parent=None,
                                leftIndent=18,
                                rightIndent=0,
                                bulletAlign='left',
                                bulletType='1',
                                bulletColor=black,
                                bulletFontName='Helvetica',
                                bulletFontSize=12,
                                bulletOffsetY=0,
                                bulletDedent='auto',
                                bulletDir='ltr',
                                bulletFormat=None,
                                #start='circle square blackstar sparkle disc diamond'.split(),
                                start=None,
                            ),
                   alias='ul')

    stylesheet.add(ListStyle(name='OrderedList',
                                parent=None,
                                leftIndent=18,
                                rightIndent=0,
                                bulletAlign='left',
                                bulletType='1',
                                bulletColor=black,
                                bulletFontName='Helvetica',
                                bulletFontSize=12,
                                bulletOffsetY=0,
                                bulletDedent='auto',
                                bulletDir='ltr',
                                bulletFormat=None,
                                #start='1 a A i I'.split(),
                                start=None,
                            ),
                   alias='ol')
    return stylesheet
