#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/platypus/paraparser.py
__all__ = ('ParaFrag', 'ParaParser')
__version__='3.5.20'
__doc__='''The parser used to process markup within paragraphs'''
import re
import sys
import copy
import unicodedata
import reportlab.lib.sequencer

from reportlab.lib.abag import ABag
from reportlab.lib.utils import ImageReader, annotateException, encode_label, asUnicode
from reportlab.lib.colors import toColor, black
from reportlab.lib.fonts import tt2ps, ps2tt
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.units import inch,mm,cm,pica
from reportlab.rl_config import platypus_link_underline
from html.parser import HTMLParser
from html.entities import name2codepoint

_re_para = re.compile(r'^\s*<\s*para(?:\s+|>|/>)')

sizeDelta = 2       # amount to reduce font size by for super and sub script
subFraction = 0.5   # fraction of font size that a sub script should be lowered
supFraction = 0.5 # fraction of font size that a super script should be raised

DEFAULT_INDEX_NAME='_indexAdd'

def _convnum(s, unit=1, allowRelative=True):
    if s[0] in ('+','-') and allowRelative:
        try:
            return ('relative',int(s)*unit)
        except ValueError:
            return ('relative',float(s)*unit)
    else:
        try:
            return int(s)*unit
        except ValueError:
            return float(s)*unit

def _num(s, unit=1, allowRelative=True,
        _unit_map = {'i':inch,'in':inch,'pt':1,'cm':cm,'mm':mm,'pica':pica },
        _re_unit = re.compile(r'^\s*(.*)(i|in|cm|mm|pt|pica)\s*$'),
        ):
    """Convert a string like '10cm' to an int or float (in points).
       The default unit is point, but optionally you can use other
       default units like mm.
    """
    m = _re_unit.match(s)
    if m:
        unit = _unit_map[m.group(2)]
        s = m.group(1)
    return _convnum(s,unit,allowRelative)

def _int(s):
    try:
        return int(s)
    except:
        raise ValueError('cannot convert %r to int' % s)

def _bool(s):
    s = s.lower()
    if s in ('true','1','yes'):
        return True
    if s in ('false','0','no'):
        return False
    raise ValueError('cannot convert %r to bool value' % s)

def _numpct(s,unit=1,allowRelative=False):
    if s.endswith('%'):
        return _PCT(_convnum(s[:-1],allowRelative=allowRelative))
    else:
        return _num(s,unit,allowRelative)

class _PCT(float):
    def __new__(cls,v):
        self = float.__new__(cls,v*0.01)
        self._normalizer = 1.0
        self._value = v
        return self

    def normalizedValue(self,normalizer):
        if not normalizer:
            normaliser = self._normalizer
        r = _PCT(normalizer*self._value)
        r._value = self._value
        r._normalizer = normalizer
        return r

    def __copy__(self):
        r = _PCT(float(self))
        r._value = self._value
        r._normalizer = normalizer
        return r

    def __deepcopy__(self,mem):
        return self.__copy__()

def fontSizeNormalize(frag,attr,default):
    if not hasattr(frag,attr): return default
    v = _numpct(getattr(frag,attr),allowRelative=True)
    return (v[1]+frag.fontSize) if isinstance(v,tuple) else v.normalizedValue(frag.fontSize) if isinstance(v,_PCT) else v

class _ExValidate:
    '''class for syntax checking attributes
    '''
    def __init__(self,tag,attr):
        self.tag = tag
        self.attr = attr

    def invalid(self,s):
        raise ValueError('<%s> invalid value %r for attribute %s' % (self.tag,s,self.attr))

    def validate(self, parser,s):
        raise ValueError('abstract method called')
        return s

    def __call__(self, parser, s):
        try:
            return self.validate(parser, s)
        except:
            self.invalid(s)

class _CheckSup(_ExValidate):
    '''class for syntax checking <sup|sub> attributes
    if the check succeeds then we always return the string for later evaluation'''
    def validate(self,parser,s):
        self.fontSize = parser._stack[-1].fontSize
        fontSizeNormalize(self,self.attr,'')
        return s

    def __call__(self, parser, s):
        setattr(self,self.attr,s)
        return _ExValidate.__call__(self,parser,s)

_lineRepeats = dict(single=1,double=2,triple=3)
_re_us_value = re.compile(r'^\s*(.*)\s*\*\s*(P|L|f|F)\s*$')
class _CheckUS(_ExValidate):
    '''class for syntax checking <u|strike> width/offset attributes'''
    def validate(self,parser,s):
        s = s.strip()
        if s:
            m = _re_us_value.match(s)
            if m:
                v = float(m.group(1))
                if m.group(2)=='P':
                    return parser._stack[0].fontSize*v
            else:
                _num(s,allowRelative=False)
        return s

def _valignpc(s):
    s = s.lower()
    if s in ('baseline','sub','super','top','text-top','middle','bottom','text-bottom'):
        return s
    if s.endswith('%'):
        n = _convnum(s[:-1])
        if isinstance(n,tuple):
            n = n[1]
        return _PCT(n)
    n = _num(s)
    if isinstance(n,tuple):
        n = n[1]
    return n

def _autoLeading(x):
    x = x.lower()
    if x in ('','min','max','off'):
        return x
    raise ValueError('Invalid autoLeading=%r' % x )

def _align(s):
    s = s.lower()
    if s=='left': return TA_LEFT
    elif s=='right': return TA_RIGHT
    elif s=='justify': return TA_JUSTIFY
    elif s in ('centre','center'): return TA_CENTER
    else: raise ValueError('illegal alignment %r' % s)

def _bAnchor(s):
    s = s.lower()
    if not s in ('start','middle','end','numeric'):
        raise ValueError('illegal bullet anchor %r' % s)
    return s

def _wordWrapConv(s):
    s = s.upper().strip()
    if not s: return None
    if s not in ('CJK','RTL','LTR'):
        raise ValueError('cannot convert wordWrap=%r' % s)
    return s

def _textTransformConv(s):
    s = s.lower().strip()
    if not s: return None
    if s not in ('uppercase','lowercase','capitalize','none'):
        raise ValueError('cannot convert textTransform=%r' % s)
    return s

_paraAttrMap = {'font': ('fontName', None),
                'face': ('fontName', None),
                'fontsize': ('fontSize', _num),
                'size': ('fontSize', _num),
                'leading': ('leading', _num),
                'autoleading': ('autoLeading', _autoLeading),
                'lindent': ('leftIndent', _num),
                'rindent': ('rightIndent', _num),
                'findent': ('firstLineIndent', _num),
                'align': ('alignment', _align),
                'spaceb': ('spaceBefore', _num),
                'spacea': ('spaceAfter', _num),
                'bfont': ('bulletFontName', None),
                'bfontsize': ('bulletFontSize',_num),
                'boffsety': ('bulletOffsetY',_num),
                'bindent': ('bulletIndent',_num),
                'bcolor': ('bulletColor',toColor),
                'banchor': ('bulletAnchor',_bAnchor),
                'color':('textColor',toColor),
                'backcolor':('backColor',toColor),
                'bgcolor':('backColor',toColor),
                'bg':('backColor',toColor),
                'fg': ('textColor',toColor),
                'justifybreaks': ('justifyBreaks',_bool),
                'justifylastline': ('justifyLastLine',_int),
                'wordwrap': ('wordWrap',_wordWrapConv),
                'allowwidows': ('allowWidows',_bool),
                'alloworphans': ('allowOrphans',_bool),
                'splitlongwords': ('splitLongWords',_bool),
                'borderwidth': ('borderWidth',_num),
                'borderpadding': ('borderPadding',_num),
                'bordercolor': ('borderColor',toColor),
                'borderradius': ('borderRadius',_num),
                'texttransform':('textTransform',_textTransformConv),
                'enddots':('endDots',None),
                'underlinewidth':('underlineWidth',_CheckUS('para','underlineWidth')),
                'underlinecolor':('underlineColor',toColor),
                'underlineoffset':('underlineOffset',_CheckUS('para','underlineOffset')),
                'underlinegap':('underlineGap',_CheckUS('para','underlineGap')),
                'strikewidth':('strikeWidth',_CheckUS('para','strikeWidth')),
                'strikecolor':('strikeColor',toColor),
                'strikeoffset':('strikeOffset',_CheckUS('para','strikeOffset')),
                'strikegap':('strikeGap',_CheckUS('para','strikeGap')),
                'spaceshrinkage':('spaceShrinkage',_num),
                'hyphenationLanguage': ('hyphenationLang',None),
                'hyphenationOverflow': ('hyphenationOverflow',_bool),
                'hyphenationMinWordLength': ('hyphenationMinWordLength',_int),
                'uriWasteReduce': ('uriWasteReduce',_num),
                'embeddedHyphenation': ('embeddedHyphenation',_bool),
                }

_bulletAttrMap = {
                'font': ('bulletFontName', None),
                'face': ('bulletFontName', None),
                'size': ('bulletFontSize',_num),
                'fontsize': ('bulletFontSize',_num),
                'offsety': ('bulletOffsetY',_num),
                'indent': ('bulletIndent',_num),
                'color': ('bulletColor',toColor),
                'fg': ('bulletColor',toColor),
                'anchor': ('bulletAnchor',_bAnchor),
                }

#things which are valid font attributes
_fontAttrMap = {'size': ('fontSize', _num),
                'face': ('fontName', None),
                'name': ('fontName', None),
                'fg':   ('textColor', toColor),
                'color':('textColor', toColor),
                'backcolor':('backColor',toColor),
                'bgcolor':('backColor',toColor),
                }
#things which are valid span attributes
_spanAttrMap = {'size': ('fontSize', _num),
                'face': ('fontName', None),
                'name': ('fontName', None),
                'fg':   ('textColor', toColor),
                'color':('textColor', toColor),
                'backcolor':('backColor',toColor),
                'bgcolor':('backColor',toColor),
                'style': ('style',None),
                }
#things which are valid font attributes
_linkAttrMap = {'size': ('fontSize', _num),
                'face': ('fontName', None),
                'name': ('fontName', None),
                'fg':   ('textColor', toColor),
                'color':('textColor', toColor),
                'backcolor':('backColor',toColor),
                'bgcolor':('backColor',toColor),
                'dest': ('link', None),
                'destination': ('link', None),
                'target': ('link', None),
                'href': ('link', None),
                'ucolor': ('underlineColor', toColor),
                'uoffset': ('underlineOffset', _CheckUS('link','underlineOffset')),
                'uwidth': ('underlineWidth', _CheckUS('link','underlineWidth')),
                'ugap': ('underlineGap', _CheckUS('link','underlineGap')),
                'underline': ('underline',_bool),
                'ukind': ('underlineKind',None),
                }
_anchorAttrMap = {
                'name': ('name', None),
                }
_imgAttrMap = {
                'src': ('src', None),
                'width': ('width',_numpct),
                'height':('height',_numpct),
                'valign':('valign',_valignpc),
                }
_indexAttrMap = {
                'name': ('name',None),
                'item': ('item',None),
                'offset': ('offset',None),
                'format': ('format',None),
                }
_supAttrMap = {
                'rise': ('supr', _CheckSup('sup|sub','rise')),
                'size': ('sups', _CheckSup('sup|sub','size')),
                }
_uAttrMap = {
            'color':('underlineColor', toColor),
            'width':('underlineWidth', _CheckUS('underline','underlineWidth')),
            'offset':('underlineOffset', _CheckUS('underline','underlineOffset')),
            'gap':('underlineGap', _CheckUS('underline','underlineGap')),
            'kind':('underlineKind',None),
            }
_strikeAttrMap = {
            'color':('strikeColor', toColor),
            'width':('strikeWidth', _CheckUS('strike','strikeWidth')),
            'offset':('strikeOffset', _CheckUS('strike','strikeOffset')),
            'gap':('strikeGap', _CheckUS('strike','strikeGap')),
            'kind':('strikeKind',None),
            }

def _addAttributeNames(m):
    K = list(m.keys())
    for k in K:
        n = m[k][0]
        if n not in m: m[n] = m[k]
        n = n.lower()
        if n not in m: m[n] = m[k]

_addAttributeNames(_paraAttrMap)
_addAttributeNames(_fontAttrMap)
_addAttributeNames(_spanAttrMap)
_addAttributeNames(_bulletAttrMap)
_addAttributeNames(_anchorAttrMap)
_addAttributeNames(_linkAttrMap)

def _applyAttributes(obj, attr):
    for k, v in attr.items():
        if isinstance(v,(list,tuple)) and v[0]=='relative':
            if hasattr(obj, k):
                v = v[1]+getattr(obj,k)
            else:
                v = v[1]
        setattr(obj,k,v)

#Named character entities intended to be supported from the special font
#with additions suggested by Christoph Zwerschke who also suggested the
#numeric entity names that follow.
greeks = {
    'Aacute': u'\xc1',                            #LATIN CAPITAL LETTER A WITH ACUTE
    'aacute': u'\xe1',                            #LATIN SMALL LETTER A WITH ACUTE
    'Abreve': u'\u0102',                          #LATIN CAPITAL LETTER A WITH BREVE
    'abreve': u'\u0103',                          #LATIN SMALL LETTER A WITH BREVE
    'ac': u'\u223e',                              #INVERTED LAZY S
    'acd': u'\u223f',                             #SINE WAVE
    'acE': u'\u223e\u0333',                       #INVERTED LAZY S with double underline
    'Acirc': u'\xc2',                             #LATIN CAPITAL LETTER A WITH CIRCUMFLEX
    'acirc': u'\xe2',                             #LATIN SMALL LETTER A WITH CIRCUMFLEX
    'acute': u'\xb4',                             #ACUTE ACCENT
    'Acy': u'\u0410',                             #CYRILLIC CAPITAL LETTER A
    'acy': u'\u0430',                             #CYRILLIC SMALL LETTER A
    'AElig': u'\xc6',                             #LATIN CAPITAL LETTER AE
    'aelig': u'\xe6',                             #LATIN SMALL LETTER AE
    'af': u'\u2061',                              #FUNCTION APPLICATION
    'Afr': u'\U0001d504',                         #MATHEMATICAL FRAKTUR CAPITAL A
    'afr': u'\U0001d51e',                         #MATHEMATICAL FRAKTUR SMALL A
    'Agrave': u'\xc0',                            #LATIN CAPITAL LETTER A WITH GRAVE
    'agrave': u'\xe0',                            #LATIN SMALL LETTER A WITH GRAVE
    'alefsym': u'\u2135',                         #ALEF SYMBOL
    'aleph': u'\u2135',                           #ALEF SYMBOL
    'Alpha': u'\u0391',                           #GREEK CAPITAL LETTER ALPHA
    'alpha': u'\u03b1',                           #GREEK SMALL LETTER ALPHA
    'Amacr': u'\u0100',                           #LATIN CAPITAL LETTER A WITH MACRON
    'amacr': u'\u0101',                           #LATIN SMALL LETTER A WITH MACRON
    'amalg': u'\u2a3f',                           #AMALGAMATION OR COPRODUCT
    'AMP': u'\x26',                               #AMPERSAND
    'amp': u'\x26',                               #AMPERSAND
    'And': u'\u2a53',                             #DOUBLE LOGICAL AND
    'and': u'\u2227',                             #LOGICAL AND
    'andand': u'\u2a55',                          #TWO INTERSECTING LOGICAL AND
    'andd': u'\u2a5c',                            #LOGICAL AND WITH HORIZONTAL DASH
    'andslope': u'\u2a58',                        #SLOPING LARGE AND
    'andv': u'\u2a5a',                            #LOGICAL AND WITH MIDDLE STEM
    'ang': u'\u2220',                             #ANGLE
    'ange': u'\u29a4',                            #ANGLE WITH UNDERBAR
    'angle': u'\u2220',                           #ANGLE
    'angmsd': u'\u2221',                          #MEASURED ANGLE
    'angmsdaa': u'\u29a8',                        #MEASURED ANGLE WITH OPEN ARM ENDING IN ARROW POINTING UP AND RIGHT
    'angmsdab': u'\u29a9',                        #MEASURED ANGLE WITH OPEN ARM ENDING IN ARROW POINTING UP AND LEFT
    'angmsdac': u'\u29aa',                        #MEASURED ANGLE WITH OPEN ARM ENDING IN ARROW POINTING DOWN AND RIGHT
    'angmsdad': u'\u29ab',                        #MEASURED ANGLE WITH OPEN ARM ENDING IN ARROW POINTING DOWN AND LEFT
    'angmsdae': u'\u29ac',                        #MEASURED ANGLE WITH OPEN ARM ENDING IN ARROW POINTING RIGHT AND UP
    'angmsdaf': u'\u29ad',                        #MEASURED ANGLE WITH OPEN ARM ENDING IN ARROW POINTING LEFT AND UP
    'angmsdag': u'\u29ae',                        #MEASURED ANGLE WITH OPEN ARM ENDING IN ARROW POINTING RIGHT AND DOWN
    'angmsdah': u'\u29af',                        #MEASURED ANGLE WITH OPEN ARM ENDING IN ARROW POINTING LEFT AND DOWN
    'angrt': u'\u221f',                           #RIGHT ANGLE
    'angrtvb': u'\u22be',                         #RIGHT ANGLE WITH ARC
    'angrtvbd': u'\u299d',                        #MEASURED RIGHT ANGLE WITH DOT
    'angsph': u'\u2222',                          #SPHERICAL ANGLE
    'angst': u'\xc5',                             #LATIN CAPITAL LETTER A WITH RING ABOVE
    'angzarr': u'\u237c',                         #RIGHT ANGLE WITH DOWNWARDS ZIGZAG ARROW
    'Aogon': u'\u0104',                           #LATIN CAPITAL LETTER A WITH OGONEK
    'aogon': u'\u0105',                           #LATIN SMALL LETTER A WITH OGONEK
    'Aopf': u'\U0001d538',                        #MATHEMATICAL DOUBLE-STRUCK CAPITAL A
    'aopf': u'\U0001d552',                        #MATHEMATICAL DOUBLE-STRUCK SMALL A
    'ap': u'\u2248',                              #ALMOST EQUAL TO
    'apacir': u'\u2a6f',                          #ALMOST EQUAL TO WITH CIRCUMFLEX ACCENT
    'apE': u'\u2a70',                             #APPROXIMATELY EQUAL OR EQUAL TO
    'ape': u'\u224a',                             #ALMOST EQUAL OR EQUAL TO
    'apid': u'\u224b',                            #TRIPLE TILDE
    'apos': "'",                                 #APOSTROPHE
    'ApplyFunction': u'\u2061',                   #FUNCTION APPLICATION
    'approx': u'\u2248',                          #ALMOST EQUAL TO
    'approxeq': u'\u224a',                        #ALMOST EQUAL OR EQUAL TO
    'Aring': u'\xc5',                             #LATIN CAPITAL LETTER A WITH RING ABOVE
    'aring': u'\xe5',                             #LATIN SMALL LETTER A WITH RING ABOVE
    'Ascr': u'\U0001d49c',                        #MATHEMATICAL SCRIPT CAPITAL A
    'ascr': u'\U0001d4b6',                        #MATHEMATICAL SCRIPT SMALL A
    'Assign': u'\u2254',                          #COLON EQUALS
    'ast': u'*',                                  #ASTERISK
    'asymp': u'\u2248',                           #ALMOST EQUAL TO
    'asympeq': u'\u224d',                         #EQUIVALENT TO
    'Atilde': u'\xc3',                            #LATIN CAPITAL LETTER A WITH TILDE
    'atilde': u'\xe3',                            #LATIN SMALL LETTER A WITH TILDE
    'Auml': u'\xc4',                              #LATIN CAPITAL LETTER A WITH DIAERESIS
    'auml': u'\xe4',                              #LATIN SMALL LETTER A WITH DIAERESIS
    'awconint': u'\u2233',                        #ANTICLOCKWISE CONTOUR INTEGRAL
    'awint': u'\u2a11',                           #ANTICLOCKWISE INTEGRATION
    'backcong': u'\u224c',                        #ALL EQUAL TO
    'backepsilon': u'\u03f6',                     #GREEK REVERSED LUNATE EPSILON SYMBOL
    'backprime': u'\u2035',                       #REVERSED PRIME
    'backsim': u'\u223d',                         #REVERSED TILDE
    'backsimeq': u'\u22cd',                       #REVERSED TILDE EQUALS
    'Backslash': u'\u2216',                       #SET MINUS
    'Barv': u'\u2ae7',                            #SHORT DOWN TACK WITH OVERBAR
    'barvee': u'\u22bd',                          #NOR
    'Barwed': u'\u2306',                          #PERSPECTIVE
    'barwed': u'\u2305',                          #PROJECTIVE
    'barwedge': u'\u2305',                        #PROJECTIVE
    'bbrk': u'\u23b5',                            #BOTTOM SQUARE BRACKET
    'bbrktbrk': u'\u23b6',                        #BOTTOM SQUARE BRACKET OVER TOP SQUARE BRACKET
    'bcong': u'\u224c',                           #ALL EQUAL TO
    'Bcy': u'\u0411',                             #CYRILLIC CAPITAL LETTER BE
    'bcy': u'\u0431',                             #CYRILLIC SMALL LETTER BE
    'bdquo': u'\u201e',                           #DOUBLE LOW-9 QUOTATION MARK
    'becaus': u'\u2235',                          #BECAUSE
    'Because': u'\u2235',                         #BECAUSE
    'because': u'\u2235',                         #BECAUSE
    'bemptyv': u'\u29b0',                         #REVERSED EMPTY SET
    'bepsi': u'\u03f6',                           #GREEK REVERSED LUNATE EPSILON SYMBOL
    'bernou': u'\u212c',                          #SCRIPT CAPITAL B
    'Bernoullis': u'\u212c',                      #SCRIPT CAPITAL B
    'Beta': u'\u0392',                            #GREEK CAPITAL LETTER BETA
    'beta': u'\u03b2',                            #GREEK SMALL LETTER BETA
    'beth': u'\u2136',                            #BET SYMBOL
    'between': u'\u226c',                         #BETWEEN
    'Bfr': u'\U0001d505',                         #MATHEMATICAL FRAKTUR CAPITAL B
    'bfr': u'\U0001d51f',                         #MATHEMATICAL FRAKTUR SMALL B
    'bigcap': u'\u22c2',                          #N-ARY INTERSECTION
    'bigcirc': u'\u25ef',                         #LARGE CIRCLE
    'bigcup': u'\u22c3',                          #N-ARY UNION
    'bigodot': u'\u2a00',                         #N-ARY CIRCLED DOT OPERATOR
    'bigoplus': u'\u2a01',                        #N-ARY CIRCLED PLUS OPERATOR
    'bigotimes': u'\u2a02',                       #N-ARY CIRCLED TIMES OPERATOR
    'bigsqcup': u'\u2a06',                        #N-ARY SQUARE UNION OPERATOR
    'bigstar': u'\u2605',                         #BLACK STAR
    'bigtriangledown': u'\u25bd',                 #WHITE DOWN-POINTING TRIANGLE
    'bigtriangleup': u'\u25b3',                   #WHITE UP-POINTING TRIANGLE
    'biguplus': u'\u2a04',                        #N-ARY UNION OPERATOR WITH PLUS
    'bigvee': u'\u22c1',                          #N-ARY LOGICAL OR
    'bigwedge': u'\u22c0',                        #N-ARY LOGICAL AND
    'bkarow': u'\u290d',                          #RIGHTWARDS DOUBLE DASH ARROW
    'blacklozenge': u'\u29eb',                    #BLACK LOZENGE
    'blacksquare': u'\u25aa',                     #BLACK SMALL SQUARE
    'blacktriangle': u'\u25b4',                   #BLACK UP-POINTING SMALL TRIANGLE
    'blacktriangledown': u'\u25be',               #BLACK DOWN-POINTING SMALL TRIANGLE
    'blacktriangleleft': u'\u25c2',               #BLACK LEFT-POINTING SMALL TRIANGLE
    'blacktriangleright': u'\u25b8',              #BLACK RIGHT-POINTING SMALL TRIANGLE
    'blank': u'\u2423',                           #OPEN BOX
    'blk12': u'\u2592',                           #MEDIUM SHADE
    'blk14': u'\u2591',                           #LIGHT SHADE
    'blk34': u'\u2593',                           #DARK SHADE
    'block': u'\u2588',                           #FULL BLOCK
    'bne': u'=\u20e5',                            #EQUALS SIGN with reverse slash
    'bnequiv': u'\u2261\u20e5',                   #IDENTICAL TO with reverse slash
    'bNot': u'\u2aed',                            #REVERSED DOUBLE STROKE NOT SIGN
    'bnot': u'\u2310',                            #REVERSED NOT SIGN
    'Bopf': u'\U0001d539',                        #MATHEMATICAL DOUBLE-STRUCK CAPITAL B
    'bopf': u'\U0001d553',                        #MATHEMATICAL DOUBLE-STRUCK SMALL B
    'bot': u'\u22a5',                             #UP TACK
    'bottom': u'\u22a5',                          #UP TACK
    'bowtie': u'\u22c8',                          #BOWTIE
    'boxbox': u'\u29c9',                          #TWO JOINED SQUARES
    'boxDL': u'\u2557',                           #BOX DRAWINGS DOUBLE DOWN AND LEFT
    'boxDl': u'\u2556',                           #BOX DRAWINGS DOWN DOUBLE AND LEFT SINGLE
    'boxdL': u'\u2555',                           #BOX DRAWINGS DOWN SINGLE AND LEFT DOUBLE
    'boxdl': u'\u2510',                           #BOX DRAWINGS LIGHT DOWN AND LEFT
    'boxDR': u'\u2554',                           #BOX DRAWINGS DOUBLE DOWN AND RIGHT
    'boxDr': u'\u2553',                           #BOX DRAWINGS DOWN DOUBLE AND RIGHT SINGLE
    'boxdR': u'\u2552',                           #BOX DRAWINGS DOWN SINGLE AND RIGHT DOUBLE
    'boxdr': u'\u250c',                           #BOX DRAWINGS LIGHT DOWN AND RIGHT
    'boxH': u'\u2550',                            #BOX DRAWINGS DOUBLE HORIZONTAL
    'boxh': u'\u2500',                            #BOX DRAWINGS LIGHT HORIZONTAL
    'boxHD': u'\u2566',                           #BOX DRAWINGS DOUBLE DOWN AND HORIZONTAL
    'boxHd': u'\u2564',                           #BOX DRAWINGS DOWN SINGLE AND HORIZONTAL DOUBLE
    'boxhD': u'\u2565',                           #BOX DRAWINGS DOWN DOUBLE AND HORIZONTAL SINGLE
    'boxhd': u'\u252c',                           #BOX DRAWINGS LIGHT DOWN AND HORIZONTAL
    'boxHU': u'\u2569',                           #BOX DRAWINGS DOUBLE UP AND HORIZONTAL
    'boxHu': u'\u2567',                           #BOX DRAWINGS UP SINGLE AND HORIZONTAL DOUBLE
    'boxhU': u'\u2568',                           #BOX DRAWINGS UP DOUBLE AND HORIZONTAL SINGLE
    'boxhu': u'\u2534',                           #BOX DRAWINGS LIGHT UP AND HORIZONTAL
    'boxminus': u'\u229f',                        #SQUARED MINUS
    'boxplus': u'\u229e',                         #SQUARED PLUS
    'boxtimes': u'\u22a0',                        #SQUARED TIMES
    'boxUL': u'\u255d',                           #BOX DRAWINGS DOUBLE UP AND LEFT
    'boxUl': u'\u255c',                           #BOX DRAWINGS UP DOUBLE AND LEFT SINGLE
    'boxuL': u'\u255b',                           #BOX DRAWINGS UP SINGLE AND LEFT DOUBLE
    'boxul': u'\u2518',                           #BOX DRAWINGS LIGHT UP AND LEFT
    'boxUR': u'\u255a',                           #BOX DRAWINGS DOUBLE UP AND RIGHT
    'boxUr': u'\u2559',                           #BOX DRAWINGS UP DOUBLE AND RIGHT SINGLE
    'boxuR': u'\u2558',                           #BOX DRAWINGS UP SINGLE AND RIGHT DOUBLE
    'boxur': u'\u2514',                           #BOX DRAWINGS LIGHT UP AND RIGHT
    'boxV': u'\u2551',                            #BOX DRAWINGS DOUBLE VERTICAL
    'boxv': u'\u2502',                            #BOX DRAWINGS LIGHT VERTICAL
    'boxVH': u'\u256c',                           #BOX DRAWINGS DOUBLE VERTICAL AND HORIZONTAL
    'boxVh': u'\u256b',                           #BOX DRAWINGS VERTICAL DOUBLE AND HORIZONTAL SINGLE
    'boxvH': u'\u256a',                           #BOX DRAWINGS VERTICAL SINGLE AND HORIZONTAL DOUBLE
    'boxvh': u'\u253c',                           #BOX DRAWINGS LIGHT VERTICAL AND HORIZONTAL
    'boxVL': u'\u2563',                           #BOX DRAWINGS DOUBLE VERTICAL AND LEFT
    'boxVl': u'\u2562',                           #BOX DRAWINGS VERTICAL DOUBLE AND LEFT SINGLE
    'boxvL': u'\u2561',                           #BOX DRAWINGS VERTICAL SINGLE AND LEFT DOUBLE
    'boxvl': u'\u2524',                           #BOX DRAWINGS LIGHT VERTICAL AND LEFT
    'boxVR': u'\u2560',                           #BOX DRAWINGS DOUBLE VERTICAL AND RIGHT
    'boxVr': u'\u255f',                           #BOX DRAWINGS VERTICAL DOUBLE AND RIGHT SINGLE
    'boxvR': u'\u255e',                           #BOX DRAWINGS VERTICAL SINGLE AND RIGHT DOUBLE
    'boxvr': u'\u251c',                           #BOX DRAWINGS LIGHT VERTICAL AND RIGHT
    'bprime': u'\u2035',                          #REVERSED PRIME
    'Breve': u'\u02d8',                           #BREVE
    'breve': u'\u02d8',                           #BREVE
    'brvbar': u'\xa6',                            #BROKEN BAR
    'Bscr': u'\u212c',                            #SCRIPT CAPITAL B
    'bscr': u'\U0001d4b7',                        #MATHEMATICAL SCRIPT SMALL B
    'bsemi': u'\u204f',                           #REVERSED SEMICOLON
    'bsim': u'\u223d',                            #REVERSED TILDE
    'bsime': u'\u22cd',                           #REVERSED TILDE EQUALS
    'bsol': u'\\',                                #REVERSE SOLIDUS
    'bsolb': u'\u29c5',                           #SQUARED FALLING DIAGONAL SLASH
    'bsolhsub': u'\u27c8',                        #REVERSE SOLIDUS PRECEDING SUBSET
    'bull': u'\u2022',                            #BULLET
    'bullet': u'\u2022',                          #BULLET
    'bump': u'\u224e',                            #GEOMETRICALLY EQUIVALENT TO
    'bumpE': u'\u2aae',                           #EQUALS SIGN WITH BUMPY ABOVE
    'bumpe': u'\u224f',                           #DIFFERENCE BETWEEN
    'Bumpeq': u'\u224e',                          #GEOMETRICALLY EQUIVALENT TO
    'bumpeq': u'\u224f',                          #DIFFERENCE BETWEEN
    'Cacute': u'\u0106',                          #LATIN CAPITAL LETTER C WITH ACUTE
    'cacute': u'\u0107',                          #LATIN SMALL LETTER C WITH ACUTE
    'Cap': u'\u22d2',                             #DOUBLE INTERSECTION
    'cap': u'\u2229',                             #INTERSECTION
    'capand': u'\u2a44',                          #INTERSECTION WITH LOGICAL AND
    'capbrcup': u'\u2a49',                        #INTERSECTION ABOVE BAR ABOVE UNION
    'capcap': u'\u2a4b',                          #INTERSECTION BESIDE AND JOINED WITH INTERSECTION
    'capcup': u'\u2a47',                          #INTERSECTION ABOVE UNION
    'capdot': u'\u2a40',                          #INTERSECTION WITH DOT
    'CapitalDifferentialD': u'\u2145',            #DOUBLE-STRUCK ITALIC CAPITAL D
    'caps': u'\u2229\ufe00',                      #INTERSECTION with serifs
    'caret': u'\u2041',                           #CARET INSERTION POINT
    'caron': u'\u02c7',                           #CARON
    'Cayleys': u'\u212d',                         #BLACK-LETTER CAPITAL C
    'ccaps': u'\u2a4d',                           #CLOSED INTERSECTION WITH SERIFS
    'Ccaron': u'\u010c',                          #LATIN CAPITAL LETTER C WITH CARON
    'ccaron': u'\u010d',                          #LATIN SMALL LETTER C WITH CARON
    'Ccedil': u'\xc7',                            #LATIN CAPITAL LETTER C WITH CEDILLA
    'ccedil': u'\xe7',                            #LATIN SMALL LETTER C WITH CEDILLA
    'Ccirc': u'\u0108',                           #LATIN CAPITAL LETTER C WITH CIRCUMFLEX
    'ccirc': u'\u0109',                           #LATIN SMALL LETTER C WITH CIRCUMFLEX
    'Cconint': u'\u2230',                         #VOLUME INTEGRAL
    'ccups': u'\u2a4c',                           #CLOSED UNION WITH SERIFS
    'ccupssm': u'\u2a50',                         #CLOSED UNION WITH SERIFS AND SMASH PRODUCT
    'Cdot': u'\u010a',                            #LATIN CAPITAL LETTER C WITH DOT ABOVE
    'cdot': u'\u010b',                            #LATIN SMALL LETTER C WITH DOT ABOVE
    'cedil': u'\xb8',                             #CEDILLA
    'Cedilla': u'\xb8',                           #CEDILLA
    'cemptyv': u'\u29b2',                         #EMPTY SET WITH SMALL CIRCLE ABOVE
    'cent': u'\xa2',                              #CENT SIGN
    'CenterDot': u'\xb7',                         #MIDDLE DOT
    'centerdot': u'\xb7',                         #MIDDLE DOT
    'Cfr': u'\u212d',                             #BLACK-LETTER CAPITAL C
    'cfr': u'\U0001d520',                         #MATHEMATICAL FRAKTUR SMALL C
    'CHcy': u'\u0427',                            #CYRILLIC CAPITAL LETTER CHE
    'chcy': u'\u0447',                            #CYRILLIC SMALL LETTER CHE
    'check': u'\u2713',                           #CHECK MARK
    'checkmark': u'\u2713',                       #CHECK MARK
    'Chi': u'\u03a7',                             #GREEK CAPITAL LETTER CHI
    'chi': u'\u03c7',                             #GREEK SMALL LETTER CHI
    'cir': u'\u25cb',                             #WHITE CIRCLE
    'circ': u'\u02c6',                            #MODIFIER LETTER CIRCUMFLEX ACCENT
    'circeq': u'\u2257',                          #RING EQUAL TO
    'circlearrowleft': u'\u21ba',                 #ANTICLOCKWISE OPEN CIRCLE ARROW
    'circlearrowright': u'\u21bb',                #CLOCKWISE OPEN CIRCLE ARROW
    'circledast': u'\u229b',                      #CIRCLED ASTERISK OPERATOR
    'circledcirc': u'\u229a',                     #CIRCLED RING OPERATOR
    'circleddash': u'\u229d',                     #CIRCLED DASH
    'CircleDot': u'\u2299',                       #CIRCLED DOT OPERATOR
    'circledR': u'\xae',                          #REGISTERED SIGN
    'circledS': u'\u24c8',                        #CIRCLED LATIN CAPITAL LETTER S
    'CircleMinus': u'\u2296',                     #CIRCLED MINUS
    'CirclePlus': u'\u2295',                      #CIRCLED PLUS
    'CircleTimes': u'\u2297',                     #CIRCLED TIMES
    'cirE': u'\u29c3',                            #CIRCLE WITH TWO HORIZONTAL STROKES TO THE RIGHT
    'cire': u'\u2257',                            #RING EQUAL TO
    'cirfnint': u'\u2a10',                        #CIRCULATION FUNCTION
    'cirmid': u'\u2aef',                          #VERTICAL LINE WITH CIRCLE ABOVE
    'cirscir': u'\u29c2',                         #CIRCLE WITH SMALL CIRCLE TO THE RIGHT
    'ClockwiseContourIntegral': u'\u2232',        #CLOCKWISE CONTOUR INTEGRAL
    'CloseCurlyDoubleQuote': u'\u201d',           #RIGHT DOUBLE QUOTATION MARK
    'CloseCurlyQuote': u'\u2019',                 #RIGHT SINGLE QUOTATION MARK
    'clubs': u'\u2663',                           #BLACK CLUB SUIT
    'clubsuit': u'\u2663',                        #BLACK CLUB SUIT
    'Colon': u'\u2237',                           #PROPORTION
    'colon': u':',                                #COLON
    'Colone': u'\u2a74',                          #DOUBLE COLON EQUAL
    'colone': u'\u2254',                          #COLON EQUALS
    'coloneq': u'\u2254',                         #COLON EQUALS
    'comma': u',',                                #COMMA
    'commat': u'@',                               #COMMERCIAL AT
    'comp': u'\u2201',                            #COMPLEMENT
    'compfn': u'\u2218',                          #RING OPERATOR
    'complement': u'\u2201',                      #COMPLEMENT
    'complexes': u'\u2102',                       #DOUBLE-STRUCK CAPITAL C
    'cong': u'\u2245',                            #APPROXIMATELY EQUAL TO
    'congdot': u'\u2a6d',                         #CONGRUENT WITH DOT ABOVE
    'Congruent': u'\u2261',                       #IDENTICAL TO
    'Conint': u'\u222f',                          #SURFACE INTEGRAL
    'conint': u'\u222e',                          #CONTOUR INTEGRAL
    'ContourIntegral': u'\u222e',                 #CONTOUR INTEGRAL
    'Copf': u'\u2102',                            #DOUBLE-STRUCK CAPITAL C
    'copf': u'\U0001d554',                        #MATHEMATICAL DOUBLE-STRUCK SMALL C
    'coprod': u'\u2210',                          #N-ARY COPRODUCT
    'Coproduct': u'\u2210',                       #N-ARY COPRODUCT
    'COPY': u'\xa9',                              #COPYRIGHT SIGN
    'copy': u'\xa9',                              #COPYRIGHT SIGN
    'copysr': u'\u2117',                          #SOUND RECORDING COPYRIGHT
    'CounterClockwiseContourIntegral': u'\u2233', #ANTICLOCKWISE CONTOUR INTEGRAL
    'crarr': u'\u21b5',                           #DOWNWARDS ARROW WITH CORNER LEFTWARDS
    'Cross': u'\u2a2f',                           #VECTOR OR CROSS PRODUCT
    'cross': u'\u2717',                           #BALLOT X
    'Cscr': u'\U0001d49e',                        #MATHEMATICAL SCRIPT CAPITAL C
    'cscr': u'\U0001d4b8',                        #MATHEMATICAL SCRIPT SMALL C
    'csub': u'\u2acf',                            #CLOSED SUBSET
    'csube': u'\u2ad1',                           #CLOSED SUBSET OR EQUAL TO
    'csup': u'\u2ad0',                            #CLOSED SUPERSET
    'csupe': u'\u2ad2',                           #CLOSED SUPERSET OR EQUAL TO
    'ctdot': u'\u22ef',                           #MIDLINE HORIZONTAL ELLIPSIS
    'cudarrl': u'\u2938',                         #RIGHT-SIDE ARC CLOCKWISE ARROW
    'cudarrr': u'\u2935',                         #ARROW POINTING RIGHTWARDS THEN CURVING DOWNWARDS
    'cuepr': u'\u22de',                           #EQUAL TO OR PRECEDES
    'cuesc': u'\u22df',                           #EQUAL TO OR SUCCEEDS
    'cularr': u'\u21b6',                          #ANTICLOCKWISE TOP SEMICIRCLE ARROW
    'cularrp': u'\u293d',                         #TOP ARC ANTICLOCKWISE ARROW WITH PLUS
    'Cup': u'\u22d3',                             #DOUBLE UNION
    'cup': u'\u222a',                             #UNION
    'cupbrcap': u'\u2a48',                        #UNION ABOVE BAR ABOVE INTERSECTION
    'CupCap': u'\u224d',                          #EQUIVALENT TO
    'cupcap': u'\u2a46',                          #UNION ABOVE INTERSECTION
    'cupcup': u'\u2a4a',                          #UNION BESIDE AND JOINED WITH UNION
    'cupdot': u'\u228d',                          #MULTISET MULTIPLICATION
    'cupor': u'\u2a45',                           #UNION WITH LOGICAL OR
    'cups': u'\u222a\ufe00',                      #UNION with serifs
    'curarr': u'\u21b7',                          #CLOCKWISE TOP SEMICIRCLE ARROW
    'curarrm': u'\u293c',                         #TOP ARC CLOCKWISE ARROW WITH MINUS
    'curlyeqprec': u'\u22de',                     #EQUAL TO OR PRECEDES
    'curlyeqsucc': u'\u22df',                     #EQUAL TO OR SUCCEEDS
    'curlyvee': u'\u22ce',                        #CURLY LOGICAL OR
    'curlywedge': u'\u22cf',                      #CURLY LOGICAL AND
    'curren': u'\xa4',                            #CURRENCY SIGN
    'curvearrowleft': u'\u21b6',                  #ANTICLOCKWISE TOP SEMICIRCLE ARROW
    'curvearrowright': u'\u21b7',                 #CLOCKWISE TOP SEMICIRCLE ARROW
    'cuvee': u'\u22ce',                           #CURLY LOGICAL OR
    'cuwed': u'\u22cf',                           #CURLY LOGICAL AND
    'cwconint': u'\u2232',                        #CLOCKWISE CONTOUR INTEGRAL
    'cwint': u'\u2231',                           #CLOCKWISE INTEGRAL
    'cylcty': u'\u232d',                          #CYLINDRICITY
    'Dagger': u'\u2021',                          #DOUBLE DAGGER
    'dagger': u'\u2020',                          #DAGGER
    'daleth': u'\u2138',                          #DALET SYMBOL
    'Darr': u'\u21a1',                            #DOWNWARDS TWO HEADED ARROW
    'dArr': u'\u21d3',                            #DOWNWARDS DOUBLE ARROW
    'darr': u'\u2193',                            #DOWNWARDS ARROW
    'dash': u'\u2010',                            #HYPHEN
    'Dashv': u'\u2ae4',                           #VERTICAL BAR DOUBLE LEFT TURNSTILE
    'dashv': u'\u22a3',                           #LEFT TACK
    'dbkarow': u'\u290f',                         #RIGHTWARDS TRIPLE DASH ARROW
    'dblac': u'\u02dd',                           #DOUBLE ACUTE ACCENT
    'Dcaron': u'\u010e',                          #LATIN CAPITAL LETTER D WITH CARON
    'dcaron': u'\u010f',                          #LATIN SMALL LETTER D WITH CARON
    'Dcy': u'\u0414',                             #CYRILLIC CAPITAL LETTER DE
    'dcy': u'\u0434',                             #CYRILLIC SMALL LETTER DE
    'DD': u'\u2145',                              #DOUBLE-STRUCK ITALIC CAPITAL D
    'dd': u'\u2146',                              #DOUBLE-STRUCK ITALIC SMALL D
    'ddagger': u'\u2021',                         #DOUBLE DAGGER
    'ddarr': u'\u21ca',                           #DOWNWARDS PAIRED ARROWS
    'DDotrahd': u'\u2911',                        #RIGHTWARDS ARROW WITH DOTTED STEM
    'ddotseq': u'\u2a77',                         #EQUALS SIGN WITH TWO DOTS ABOVE AND TWO DOTS BELOW
    'deg': u'\xb0',                               #DEGREE SIGN
    'Del': u'\u2207',                             #NABLA
    'Delta': u'\u0394',                           #GREEK CAPITAL LETTER DELTA
    'delta': u'\u03b4',                           #GREEK SMALL LETTER DELTA
    'demptyv': u'\u29b1',                         #EMPTY SET WITH OVERBAR
    'dfisht': u'\u297f',                          #DOWN FISH TAIL
    'Dfr': u'\U0001d507',                         #MATHEMATICAL FRAKTUR CAPITAL D
    'dfr': u'\U0001d521',                         #MATHEMATICAL FRAKTUR SMALL D
    'dHar': u'\u2965',                            #DOWNWARDS HARPOON WITH BARB LEFT BESIDE DOWNWARDS HARPOON WITH BARB RIGHT
    'dharl': u'\u21c3',                           #DOWNWARDS HARPOON WITH BARB LEFTWARDS
    'dharr': u'\u21c2',                           #DOWNWARDS HARPOON WITH BARB RIGHTWARDS
    'DiacriticalAcute': u'\xb4',                  #ACUTE ACCENT
    'DiacriticalDot': u'\u02d9',                  #DOT ABOVE
    'DiacriticalDoubleAcute': u'\u02dd',          #DOUBLE ACUTE ACCENT
    'DiacriticalGrave': u'`',                     #GRAVE ACCENT
    'DiacriticalTilde': u'\u02dc',                #SMALL TILDE
    'diam': u'\u22c4',                            #DIAMOND OPERATOR
    'Diamond': u'\u22c4',                         #DIAMOND OPERATOR
    'diamond': u'\u22c4',                         #DIAMOND OPERATOR
    'diamondsuit': u'\u2666',                     #BLACK DIAMOND SUIT
    'diams': u'\u2666',                           #BLACK DIAMOND SUIT
    'die': u'\xa8',                               #DIAERESIS
    'DifferentialD': u'\u2146',                   #DOUBLE-STRUCK ITALIC SMALL D
    'digamma': u'\u03dd',                         #GREEK SMALL LETTER DIGAMMA
    'disin': u'\u22f2',                           #ELEMENT OF WITH LONG HORIZONTAL STROKE
    'div': u'\xf7',                               #DIVISION SIGN
    'divide': u'\xf7',                            #DIVISION SIGN
    'divideontimes': u'\u22c7',                   #DIVISION TIMES
    'divonx': u'\u22c7',                          #DIVISION TIMES
    'DJcy': u'\u0402',                            #CYRILLIC CAPITAL LETTER DJE
    'djcy': u'\u0452',                            #CYRILLIC SMALL LETTER DJE
    'dlcorn': u'\u231e',                          #BOTTOM LEFT CORNER
    'dlcrop': u'\u230d',                          #BOTTOM LEFT CROP
    'dollar': u'$',                               #DOLLAR SIGN
    'Dopf': u'\U0001d53b',                        #MATHEMATICAL DOUBLE-STRUCK CAPITAL D
    'dopf': u'\U0001d555',                        #MATHEMATICAL DOUBLE-STRUCK SMALL D
    'Dot': u'\xa8',                               #DIAERESIS
    'dot': u'\u02d9',                             #DOT ABOVE
    'doteq': u'\u2250',                           #APPROACHES THE LIMIT
    'doteqdot': u'\u2251',                        #GEOMETRICALLY EQUAL TO
    'DotEqual': u'\u2250',                        #APPROACHES THE LIMIT
    'dotminus': u'\u2238',                        #DOT MINUS
    'dotplus': u'\u2214',                         #DOT PLUS
    'dotsquare': u'\u22a1',                       #SQUARED DOT OPERATOR
    'doublebarwedge': u'\u2306',                  #PERSPECTIVE
    'DoubleContourIntegral': u'\u222f',           #SURFACE INTEGRAL
    'DoubleDot': u'\xa8',                         #DIAERESIS
    'DoubleDownArrow': u'\u21d3',                 #DOWNWARDS DOUBLE ARROW
    'DoubleLeftArrow': u'\u21d0',                 #LEFTWARDS DOUBLE ARROW
    'DoubleLeftRightArrow': u'\u21d4',            #LEFT RIGHT DOUBLE ARROW
    'DoubleLeftTee': u'\u2ae4',                   #VERTICAL BAR DOUBLE LEFT TURNSTILE
    'DoubleLongLeftArrow': u'\u27f8',             #LONG LEFTWARDS DOUBLE ARROW
    'DoubleLongLeftRightArrow': u'\u27fa',        #LONG LEFT RIGHT DOUBLE ARROW
    'DoubleLongRightArrow': u'\u27f9',            #LONG RIGHTWARDS DOUBLE ARROW
    'DoubleRightArrow': u'\u21d2',                #RIGHTWARDS DOUBLE ARROW
    'DoubleRightTee': u'\u22a8',                  #TRUE
    'DoubleUpArrow': u'\u21d1',                   #UPWARDS DOUBLE ARROW
    'DoubleUpDownArrow': u'\u21d5',               #UP DOWN DOUBLE ARROW
    'DoubleVerticalBar': u'\u2225',               #PARALLEL TO
    'DownArrow': u'\u2193',                       #DOWNWARDS ARROW
    'Downarrow': u'\u21d3',                       #DOWNWARDS DOUBLE ARROW
    'downarrow': u'\u2193',                       #DOWNWARDS ARROW
    'DownArrowBar': u'\u2913',                    #DOWNWARDS ARROW TO BAR
    'DownArrowUpArrow': u'\u21f5',                #DOWNWARDS ARROW LEFTWARDS OF UPWARDS ARROW
    'downdownarrows': u'\u21ca',                  #DOWNWARDS PAIRED ARROWS
    'downharpoonleft': u'\u21c3',                 #DOWNWARDS HARPOON WITH BARB LEFTWARDS
    'downharpoonright': u'\u21c2',                #DOWNWARDS HARPOON WITH BARB RIGHTWARDS
    'DownLeftRightVector': u'\u2950',             #LEFT BARB DOWN RIGHT BARB DOWN HARPOON
    'DownLeftTeeVector': u'\u295e',               #LEFTWARDS HARPOON WITH BARB DOWN FROM BAR
    'DownLeftVector': u'\u21bd',                  #LEFTWARDS HARPOON WITH BARB DOWNWARDS
    'DownLeftVectorBar': u'\u2956',               #LEFTWARDS HARPOON WITH BARB DOWN TO BAR
    'DownRightTeeVector': u'\u295f',              #RIGHTWARDS HARPOON WITH BARB DOWN FROM BAR
    'DownRightVector': u'\u21c1',                 #RIGHTWARDS HARPOON WITH BARB DOWNWARDS
    'DownRightVectorBar': u'\u2957',              #RIGHTWARDS HARPOON WITH BARB DOWN TO BAR
    'DownTee': u'\u22a4',                         #DOWN TACK
    'DownTeeArrow': u'\u21a7',                    #DOWNWARDS ARROW FROM BAR
    'drbkarow': u'\u2910',                        #RIGHTWARDS TWO-HEADED TRIPLE DASH ARROW
    'drcorn': u'\u231f',                          #BOTTOM RIGHT CORNER
    'drcrop': u'\u230c',                          #BOTTOM RIGHT CROP
    'Dscr': u'\U0001d49f',                        #MATHEMATICAL SCRIPT CAPITAL D
    'dscr': u'\U0001d4b9',                        #MATHEMATICAL SCRIPT SMALL D
    'DScy': u'\u0405',                            #CYRILLIC CAPITAL LETTER DZE
    'dscy': u'\u0455',                            #CYRILLIC SMALL LETTER DZE
    'dsol': u'\u29f6',                            #SOLIDUS WITH OVERBAR
    'Dstrok': u'\u0110',                          #LATIN CAPITAL LETTER D WITH STROKE
    'dstrok': u'\u0111',                          #LATIN SMALL LETTER D WITH STROKE
    'dtdot': u'\u22f1',                           #DOWN RIGHT DIAGONAL ELLIPSIS
    'dtri': u'\u25bf',                            #WHITE DOWN-POINTING SMALL TRIANGLE
    'dtrif': u'\u25be',                           #BLACK DOWN-POINTING SMALL TRIANGLE
    'duarr': u'\u21f5',                           #DOWNWARDS ARROW LEFTWARDS OF UPWARDS ARROW
    'duhar': u'\u296f',                           #DOWNWARDS HARPOON WITH BARB LEFT BESIDE UPWARDS HARPOON WITH BARB RIGHT
    'dwangle': u'\u29a6',                         #OBLIQUE ANGLE OPENING UP
    'DZcy': u'\u040f',                            #CYRILLIC CAPITAL LETTER DZHE
    'dzcy': u'\u045f',                            #CYRILLIC SMALL LETTER DZHE
    'dzigrarr': u'\u27ff',                        #LONG RIGHTWARDS SQUIGGLE ARROW
    'Eacute': u'\xc9',                            #LATIN CAPITAL LETTER E WITH ACUTE
    'eacute': u'\xe9',                            #LATIN SMALL LETTER E WITH ACUTE
    'easter': u'\u2a6e',                          #EQUALS WITH ASTERISK
    'Ecaron': u'\u011a',                          #LATIN CAPITAL LETTER E WITH CARON
    'ecaron': u'\u011b',                          #LATIN SMALL LETTER E WITH CARON
    'ecir': u'\u2256',                            #RING IN EQUAL TO
    'Ecirc': u'\xca',                             #LATIN CAPITAL LETTER E WITH CIRCUMFLEX
    'ecirc': u'\xea',                             #LATIN SMALL LETTER E WITH CIRCUMFLEX
    'ecolon': u'\u2255',                          #EQUALS COLON
    'Ecy': u'\u042d',                             #CYRILLIC CAPITAL LETTER E
    'ecy': u'\u044d',                             #CYRILLIC SMALL LETTER E
    'eDDot': u'\u2a77',                           #EQUALS SIGN WITH TWO DOTS ABOVE AND TWO DOTS BELOW
    'Edot': u'\u0116',                            #LATIN CAPITAL LETTER E WITH DOT ABOVE
    'eDot': u'\u2251',                            #GEOMETRICALLY EQUAL TO
    'edot': u'\u0117',                            #LATIN SMALL LETTER E WITH DOT ABOVE
    'ee': u'\u2147',                              #DOUBLE-STRUCK ITALIC SMALL E
    'efDot': u'\u2252',                           #APPROXIMATELY EQUAL TO OR THE IMAGE OF
    'Efr': u'\U0001d508',                         #MATHEMATICAL FRAKTUR CAPITAL E
    'efr': u'\U0001d522',                         #MATHEMATICAL FRAKTUR SMALL E
    'eg': u'\u2a9a',                              #DOUBLE-LINE EQUAL TO OR GREATER-THAN
    'Egrave': u'\xc8',                            #LATIN CAPITAL LETTER E WITH GRAVE
    'egrave': u'\xe8',                            #LATIN SMALL LETTER E WITH GRAVE
    'egs': u'\u2a96',                             #SLANTED EQUAL TO OR GREATER-THAN
    'egsdot': u'\u2a98',                          #SLANTED EQUAL TO OR GREATER-THAN WITH DOT INSIDE
    'el': u'\u2a99',                              #DOUBLE-LINE EQUAL TO OR LESS-THAN
    'Element': u'\u2208',                         #ELEMENT OF
    'elinters': u'\u23e7',                        #ELECTRICAL INTERSECTION
    'ell': u'\u2113',                             #SCRIPT SMALL L
    'els': u'\u2a95',                             #SLANTED EQUAL TO OR LESS-THAN
    'elsdot': u'\u2a97',                          #SLANTED EQUAL TO OR LESS-THAN WITH DOT INSIDE
    'Emacr': u'\u0112',                           #LATIN CAPITAL LETTER E WITH MACRON
    'emacr': u'\u0113',                           #LATIN SMALL LETTER E WITH MACRON
    'empty': u'\u2205',                           #EMPTY SET
    'emptyset': u'\u2205',                        #EMPTY SET
    'EmptySmallSquare': u'\u25fb',                #WHITE MEDIUM SQUARE
    'emptyv': u'\u2205',                          #EMPTY SET
    'EmptyVerySmallSquare': u'\u25ab',            #WHITE SMALL SQUARE
    'emsp': u'\u2003',                            #EM SPACE
    'emsp13': u'\u2004',                          #THREE-PER-EM SPACE
    'emsp14': u'\u2005',                          #FOUR-PER-EM SPACE
    'ENG': u'\u014a',                             #LATIN CAPITAL LETTER ENG
    'eng': u'\u014b',                             #LATIN SMALL LETTER ENG
    'ensp': u'\u2002',                            #EN SPACE
    'Eogon': u'\u0118',                           #LATIN CAPITAL LETTER E WITH OGONEK
    'eogon': u'\u0119',                           #LATIN SMALL LETTER E WITH OGONEK
    'Eopf': u'\U0001d53c',                        #MATHEMATICAL DOUBLE-STRUCK CAPITAL E
    'eopf': u'\U0001d556',                        #MATHEMATICAL DOUBLE-STRUCK SMALL E
    'epar': u'\u22d5',                            #EQUAL AND PARALLEL TO
    'eparsl': u'\u29e3',                          #EQUALS SIGN AND SLANTED PARALLEL
    'eplus': u'\u2a71',                           #EQUALS SIGN ABOVE PLUS SIGN
    'epsi': u'\u03b5',                            #GREEK SMALL LETTER EPSILON
    'Epsilon': u'\u0395',                         #GREEK CAPITAL LETTER EPSILON
    'epsilon': u'\u03b5',                         #GREEK SMALL LETTER EPSILON
    'epsiv': u'\u03f5',                           #GREEK LUNATE EPSILON SYMBOL
    'eqcirc': u'\u2256',                          #RING IN EQUAL TO
    'eqcolon': u'\u2255',                         #EQUALS COLON
    'eqsim': u'\u2242',                           #MINUS TILDE
    'eqslantgtr': u'\u2a96',                      #SLANTED EQUAL TO OR GREATER-THAN
    'eqslantless': u'\u2a95',                     #SLANTED EQUAL TO OR LESS-THAN
    'Equal': u'\u2a75',                           #TWO CONSECUTIVE EQUALS SIGNS
    'equals': u'=',                               #EQUALS SIGN
    'EqualTilde': u'\u2242',                      #MINUS TILDE
    'equest': u'\u225f',                          #QUESTIONED EQUAL TO
    'Equilibrium': u'\u21cc',                     #RIGHTWARDS HARPOON OVER LEFTWARDS HARPOON
    'equiv': u'\u2261',                           #IDENTICAL TO
    'equivDD': u'\u2a78',                         #EQUIVALENT WITH FOUR DOTS ABOVE
    'eqvparsl': u'\u29e5',                        #IDENTICAL TO AND SLANTED PARALLEL
    'erarr': u'\u2971',                           #EQUALS SIGN ABOVE RIGHTWARDS ARROW
    'erDot': u'\u2253',                           #IMAGE OF OR APPROXIMATELY EQUAL TO
    'Escr': u'\u2130',                            #SCRIPT CAPITAL E
    'escr': u'\u212f',                            #SCRIPT SMALL E
    'esdot': u'\u2250',                           #APPROACHES THE LIMIT
    'Esim': u'\u2a73',                            #EQUALS SIGN ABOVE TILDE OPERATOR
    'esim': u'\u2242',                            #MINUS TILDE
    'Eta': u'\u0397',                             #GREEK CAPITAL LETTER ETA
    'eta': u'\u03b7',                             #GREEK SMALL LETTER ETA
    'ETH': u'\xd0',                               #LATIN CAPITAL LETTER ETH
    'eth': u'\xf0',                               #LATIN SMALL LETTER ETH
    'Euml': u'\xcb',                              #LATIN CAPITAL LETTER E WITH DIAERESIS
    'euml': u'\xeb',                              #LATIN SMALL LETTER E WITH DIAERESIS
    'euro': u'\u20ac',                            #EURO SIGN
    'excl': u'!',                                 #EXCLAMATION MARK
    'exist': u'\u2203',                           #THERE EXISTS
    'Exists': u'\u2203',                          #THERE EXISTS
    'expectation': u'\u2130',                     #SCRIPT CAPITAL E
    'ExponentialE': u'\u2147',                    #DOUBLE-STRUCK ITALIC SMALL E
    'exponentiale': u'\u2147',                    #DOUBLE-STRUCK ITALIC SMALL E
    'fallingdotseq': u'\u2252',                   #APPROXIMATELY EQUAL TO OR THE IMAGE OF
    'Fcy': u'\u0424',                             #CYRILLIC CAPITAL LETTER EF
    'fcy': u'\u0444',                             #CYRILLIC SMALL LETTER EF
    'female': u'\u2640',                          #FEMALE SIGN
    'ffilig': u'\ufb03',                          #LATIN SMALL LIGATURE FFI
    'fflig': u'\ufb00',                           #LATIN SMALL LIGATURE FF
    'ffllig': u'\ufb04',                          #LATIN SMALL LIGATURE FFL
    'Ffr': u'\U0001d509',                         #MATHEMATICAL FRAKTUR CAPITAL F
    'ffr': u'\U0001d523',                         #MATHEMATICAL FRAKTUR SMALL F
    'filig': u'\ufb01',                           #LATIN SMALL LIGATURE FI
    'FilledSmallSquare': u'\u25fc',               #BLACK MEDIUM SQUARE
    'FilledVerySmallSquare': u'\u25aa',           #BLACK SMALL SQUARE
    'fjlig': u'fj',                               #fj ligature
    'flat': u'\u266d',                            #MUSIC FLAT SIGN
    'fllig': u'\ufb02',                           #LATIN SMALL LIGATURE FL
    'fltns': u'\u25b1',                           #WHITE PARALLELOGRAM
    'fnof': u'\u0192',                            #LATIN SMALL LETTER F WITH HOOK
    'Fopf': u'\U0001d53d',                        #MATHEMATICAL DOUBLE-STRUCK CAPITAL F
    'fopf': u'\U0001d557',                        #MATHEMATICAL DOUBLE-STRUCK SMALL F
    'ForAll': u'\u2200',                          #FOR ALL
    'forall': u'\u2200',                          #FOR ALL
    'fork': u'\u22d4',                            #PITCHFORK
    'forkv': u'\u2ad9',                           #ELEMENT OF OPENING DOWNWARDS
    'Fouriertrf': u'\u2131',                      #SCRIPT CAPITAL F
    'fpartint': u'\u2a0d',                        #FINITE PART INTEGRAL
    'frac12': u'\xbd',                            #VULGAR FRACTION ONE HALF
    'frac13': u'\u2153',                          #VULGAR FRACTION ONE THIRD
    'frac14': u'\xbc',                            #VULGAR FRACTION ONE QUARTER
    'frac15': u'\u2155',                          #VULGAR FRACTION ONE FIFTH
    'frac16': u'\u2159',                          #VULGAR FRACTION ONE SIXTH
    'frac18': u'\u215b',                          #VULGAR FRACTION ONE EIGHTH
    'frac23': u'\u2154',                          #VULGAR FRACTION TWO THIRDS
    'frac25': u'\u2156',                          #VULGAR FRACTION TWO FIFTHS
    'frac34': u'\xbe',                            #VULGAR FRACTION THREE QUARTERS
    'frac35': u'\u2157',                          #VULGAR FRACTION THREE FIFTHS
    'frac38': u'\u215c',                          #VULGAR FRACTION THREE EIGHTHS
    'frac45': u'\u2158',                          #VULGAR FRACTION FOUR FIFTHS
    'frac56': u'\u215a',                          #VULGAR FRACTION FIVE SIXTHS
    'frac58': u'\u215d',                          #VULGAR FRACTION FIVE EIGHTHS
    'frac78': u'\u215e',                          #VULGAR FRACTION SEVEN EIGHTHS
    'frasl': u'\u2044',                           #FRACTION SLASH
    'frown': u'\u2322',                           #FROWN
    'Fscr': u'\u2131',                            #SCRIPT CAPITAL F
    'fscr': u'\U0001d4bb',                        #MATHEMATICAL SCRIPT SMALL F
    'gacute': u'\u01f5',                          #LATIN SMALL LETTER G WITH ACUTE
    'Gamma': u'\u0393',                           #GREEK CAPITAL LETTER GAMMA
    'gamma': u'\u03b3',                           #GREEK SMALL LETTER GAMMA
    'Gammad': u'\u03dc',                          #GREEK LETTER DIGAMMA
    'gammad': u'\u03dd',                          #GREEK SMALL LETTER DIGAMMA
    'gap': u'\u2a86',                             #GREATER-THAN OR APPROXIMATE
    'Gbreve': u'\u011e',                          #LATIN CAPITAL LETTER G WITH BREVE
    'gbreve': u'\u011f',                          #LATIN SMALL LETTER G WITH BREVE
    'Gcedil': u'\u0122',                          #LATIN CAPITAL LETTER G WITH CEDILLA
    'Gcirc': u'\u011c',                           #LATIN CAPITAL LETTER G WITH CIRCUMFLEX
    'gcirc': u'\u011d',                           #LATIN SMALL LETTER G WITH CIRCUMFLEX
    'Gcy': u'\u0413',                             #CYRILLIC CAPITAL LETTER GHE
    'gcy': u'\u0433',                             #CYRILLIC SMALL LETTER GHE
    'Gdot': u'\u0120',                            #LATIN CAPITAL LETTER G WITH DOT ABOVE
    'gdot': u'\u0121',                            #LATIN SMALL LETTER G WITH DOT ABOVE
    'gE': u'\u2267',                              #GREATER-THAN OVER EQUAL TO
    'ge': u'\u2265',                              #GREATER-THAN OR EQUAL TO
    'gEl': u'\u2a8c',                             #GREATER-THAN ABOVE DOUBLE-LINE EQUAL ABOVE LESS-THAN
    'gel': u'\u22db',                             #GREATER-THAN EQUAL TO OR LESS-THAN
    'geq': u'\u2265',                             #GREATER-THAN OR EQUAL TO
    'geqq': u'\u2267',                            #GREATER-THAN OVER EQUAL TO
    'geqslant': u'\u2a7e',                        #GREATER-THAN OR SLANTED EQUAL TO
    'ges': u'\u2a7e',                             #GREATER-THAN OR SLANTED EQUAL TO
    'gescc': u'\u2aa9',                           #GREATER-THAN CLOSED BY CURVE ABOVE SLANTED EQUAL
    'gesdot': u'\u2a80',                          #GREATER-THAN OR SLANTED EQUAL TO WITH DOT INSIDE
    'gesdoto': u'\u2a82',                         #GREATER-THAN OR SLANTED EQUAL TO WITH DOT ABOVE
    'gesdotol': u'\u2a84',                        #GREATER-THAN OR SLANTED EQUAL TO WITH DOT ABOVE LEFT
    'gesl': u'\u22db\ufe00',                      #GREATER-THAN slanted EQUAL TO OR LESS-THAN
    'gesles': u'\u2a94',                          #GREATER-THAN ABOVE SLANTED EQUAL ABOVE LESS-THAN ABOVE SLANTED EQUAL
    'Gfr': u'\U0001d50a',                         #MATHEMATICAL FRAKTUR CAPITAL G
    'gfr': u'\U0001d524',                         #MATHEMATICAL FRAKTUR SMALL G
    'Gg': u'\u22d9',                              #VERY MUCH GREATER-THAN
    'gg': u'\u226b',                              #MUCH GREATER-THAN
    'ggg': u'\u22d9',                             #VERY MUCH GREATER-THAN
    'gimel': u'\u2137',                           #GIMEL SYMBOL
    'GJcy': u'\u0403',                            #CYRILLIC CAPITAL LETTER GJE
    'gjcy': u'\u0453',                            #CYRILLIC SMALL LETTER GJE
    'gl': u'\u2277',                              #GREATER-THAN OR LESS-THAN
    'gla': u'\u2aa5',                             #GREATER-THAN BESIDE LESS-THAN
    'glE': u'\u2a92',                             #GREATER-THAN ABOVE LESS-THAN ABOVE DOUBLE-LINE EQUAL
    'glj': u'\u2aa4',                             #GREATER-THAN OVERLAPPING LESS-THAN
    'gnap': u'\u2a8a',                            #GREATER-THAN AND NOT APPROXIMATE
    'gnapprox': u'\u2a8a',                        #GREATER-THAN AND NOT APPROXIMATE
    'gnE': u'\u2269',                             #GREATER-THAN BUT NOT EQUAL TO
    'gne': u'\u2a88',                             #GREATER-THAN AND SINGLE-LINE NOT EQUAL TO
    'gneq': u'\u2a88',                            #GREATER-THAN AND SINGLE-LINE NOT EQUAL TO
    'gneqq': u'\u2269',                           #GREATER-THAN BUT NOT EQUAL TO
    'gnsim': u'\u22e7',                           #GREATER-THAN BUT NOT EQUIVALENT TO
    'Gopf': u'\U0001d53e',                        #MATHEMATICAL DOUBLE-STRUCK CAPITAL G
    'gopf': u'\U0001d558',                        #MATHEMATICAL DOUBLE-STRUCK SMALL G
    'grave': u'`',                                #GRAVE ACCENT
    'GreaterEqual': u'\u2265',                    #GREATER-THAN OR EQUAL TO
    'GreaterEqualLess': u'\u22db',                #GREATER-THAN EQUAL TO OR LESS-THAN
    'GreaterFullEqual': u'\u2267',                #GREATER-THAN OVER EQUAL TO
    'GreaterGreater': u'\u2aa2',                  #DOUBLE NESTED GREATER-THAN
    'GreaterLess': u'\u2277',                     #GREATER-THAN OR LESS-THAN
    'GreaterSlantEqual': u'\u2a7e',               #GREATER-THAN OR SLANTED EQUAL TO
    'GreaterTilde': u'\u2273',                    #GREATER-THAN OR EQUIVALENT TO
    'Gscr': u'\U0001d4a2',                        #MATHEMATICAL SCRIPT CAPITAL G
    'gscr': u'\u210a',                            #SCRIPT SMALL G
    'gsim': u'\u2273',                            #GREATER-THAN OR EQUIVALENT TO
    'gsime': u'\u2a8e',                           #GREATER-THAN ABOVE SIMILAR OR EQUAL
    'gsiml': u'\u2a90',                           #GREATER-THAN ABOVE SIMILAR ABOVE LESS-THAN
    'GT': u'>',                                   #GREATER-THAN SIGN
    'Gt': u'\u226b',                              #MUCH GREATER-THAN
    'gt': u'>',                                   #GREATER-THAN SIGN
    'gtcc': u'\u2aa7',                            #GREATER-THAN CLOSED BY CURVE
    'gtcir': u'\u2a7a',                           #GREATER-THAN WITH CIRCLE INSIDE
    'gtdot': u'\u22d7',                           #GREATER-THAN WITH DOT
    'gtlPar': u'\u2995',                          #DOUBLE LEFT ARC GREATER-THAN BRACKET
    'gtquest': u'\u2a7c',                         #GREATER-THAN WITH QUESTION MARK ABOVE
    'gtrapprox': u'\u2a86',                       #GREATER-THAN OR APPROXIMATE
    'gtrarr': u'\u2978',                          #GREATER-THAN ABOVE RIGHTWARDS ARROW
    'gtrdot': u'\u22d7',                          #GREATER-THAN WITH DOT
    'gtreqless': u'\u22db',                       #GREATER-THAN EQUAL TO OR LESS-THAN
    'gtreqqless': u'\u2a8c',                      #GREATER-THAN ABOVE DOUBLE-LINE EQUAL ABOVE LESS-THAN
    'gtrless': u'\u2277',                         #GREATER-THAN OR LESS-THAN
    'gtrsim': u'\u2273',                          #GREATER-THAN OR EQUIVALENT TO
    'gvertneqq': u'\u2269\ufe00',                 #GREATER-THAN BUT NOT EQUAL TO - with vertical stroke
    'gvnE': u'\u2269\ufe00',                      #GREATER-THAN BUT NOT EQUAL TO - with vertical stroke
    'Hacek': u'\u02c7',                           #CARON
    'hairsp': u'\u200a',                          #HAIR SPACE
    'half': u'\xbd',                              #VULGAR FRACTION ONE HALF
    'hamilt': u'\u210b',                          #SCRIPT CAPITAL H
    'HARDcy': u'\u042a',                          #CYRILLIC CAPITAL LETTER HARD SIGN
    'hardcy': u'\u044a',                          #CYRILLIC SMALL LETTER HARD SIGN
    'hArr': u'\u21d4',                            #LEFT RIGHT DOUBLE ARROW
    'harr': u'\u2194',                            #LEFT RIGHT ARROW
    'harrcir': u'\u2948',                         #LEFT RIGHT ARROW THROUGH SMALL CIRCLE
    'harrw': u'\u21ad',                           #LEFT RIGHT WAVE ARROW
    'Hat': u'^',                                  #CIRCUMFLEX ACCENT
    'hbar': u'\u210f',                            #PLANCK CONSTANT OVER TWO PI
    'Hcirc': u'\u0124',                           #LATIN CAPITAL LETTER H WITH CIRCUMFLEX
    'hcirc': u'\u0125',                           #LATIN SMALL LETTER H WITH CIRCUMFLEX
    'hearts': u'\u2665',                          #BLACK HEART SUIT
    'heartsuit': u'\u2665',                       #BLACK HEART SUIT
    'hellip': u'\u2026',                          #HORIZONTAL ELLIPSIS
    'hercon': u'\u22b9',                          #HERMITIAN CONJUGATE MATRIX
    'Hfr': u'\u210c',                             #BLACK-LETTER CAPITAL H
    'hfr': u'\U0001d525',                         #MATHEMATICAL FRAKTUR SMALL H
    'HilbertSpace': u'\u210b',                    #SCRIPT CAPITAL H
    'hksearow': u'\u2925',                        #SOUTH EAST ARROW WITH HOOK
    'hkswarow': u'\u2926',                        #SOUTH WEST ARROW WITH HOOK
    'hoarr': u'\u21ff',                           #LEFT RIGHT OPEN-HEADED ARROW
    'homtht': u'\u223b',                          #HOMOTHETIC
    'hookleftarrow': u'\u21a9',                   #LEFTWARDS ARROW WITH HOOK
    'hookrightarrow': u'\u21aa',                  #RIGHTWARDS ARROW WITH HOOK
    'Hopf': u'\u210d',                            #DOUBLE-STRUCK CAPITAL H
    'hopf': u'\U0001d559',                        #MATHEMATICAL DOUBLE-STRUCK SMALL H
    'horbar': u'\u2015',                          #HORIZONTAL BAR
    'HorizontalLine': u'\u2500',                  #BOX DRAWINGS LIGHT HORIZONTAL
    'Hscr': u'\u210b',                            #SCRIPT CAPITAL H
    'hscr': u'\U0001d4bd',                        #MATHEMATICAL SCRIPT SMALL H
    'hslash': u'\u210f',                          #PLANCK CONSTANT OVER TWO PI
    'Hstrok': u'\u0126',                          #LATIN CAPITAL LETTER H WITH STROKE
    'hstrok': u'\u0127',                          #LATIN SMALL LETTER H WITH STROKE
    'HumpDownHump': u'\u224e',                    #GEOMETRICALLY EQUIVALENT TO
    'HumpEqual': u'\u224f',                       #DIFFERENCE BETWEEN
    'hybull': u'\u2043',                          #HYPHEN BULLET
    'hyphen': u'\u2010',                          #HYPHEN
    'Iacute': u'\xcd',                            #LATIN CAPITAL LETTER I WITH ACUTE
    'iacute': u'\xed',                            #LATIN SMALL LETTER I WITH ACUTE
    'ic': u'\u2063',                              #INVISIBLE SEPARATOR
    'Icirc': u'\xce',                             #LATIN CAPITAL LETTER I WITH CIRCUMFLEX
    'icirc': u'\xee',                             #LATIN SMALL LETTER I WITH CIRCUMFLEX
    'Icy': u'\u0418',                             #CYRILLIC CAPITAL LETTER I
    'icy': u'\u0438',                             #CYRILLIC SMALL LETTER I
    'Idot': u'\u0130',                            #LATIN CAPITAL LETTER I WITH DOT ABOVE
    'IEcy': u'\u0415',                            #CYRILLIC CAPITAL LETTER IE
    'iecy': u'\u0435',                            #CYRILLIC SMALL LETTER IE
    'iexcl': u'\xa1',                             #INVERTED EXCLAMATION MARK
    'iff': u'\u21d4',                             #LEFT RIGHT DOUBLE ARROW
    'Ifr': u'\u2111',                             #BLACK-LETTER CAPITAL I
    'ifr': u'\U0001d526',                         #MATHEMATICAL FRAKTUR SMALL I
    'Igrave': u'\xcc',                            #LATIN CAPITAL LETTER I WITH GRAVE
    'igrave': u'\xec',                            #LATIN SMALL LETTER I WITH GRAVE
    'ii': u'\u2148',                              #DOUBLE-STRUCK ITALIC SMALL I
    'iiiint': u'\u2a0c',                          #QUADRUPLE INTEGRAL OPERATOR
    'iiint': u'\u222d',                           #TRIPLE INTEGRAL
    'iinfin': u'\u29dc',                          #INCOMPLETE INFINITY
    'iiota': u'\u2129',                           #TURNED GREEK SMALL LETTER IOTA
    'IJlig': u'\u0132',                           #LATIN CAPITAL LIGATURE IJ
    'ijlig': u'\u0133',                           #LATIN SMALL LIGATURE IJ
    'Im': u'\u2111',                              #BLACK-LETTER CAPITAL I
    'Imacr': u'\u012a',                           #LATIN CAPITAL LETTER I WITH MACRON
    'imacr': u'\u012b',                           #LATIN SMALL LETTER I WITH MACRON
    'image': u'\u2111',                           #BLACK-LETTER CAPITAL I
    'ImaginaryI': u'\u2148',                      #DOUBLE-STRUCK ITALIC SMALL I
    'imagline': u'\u2110',                        #SCRIPT CAPITAL I
    'imagpart': u'\u2111',                        #BLACK-LETTER CAPITAL I
    'imath': u'\u0131',                           #LATIN SMALL LETTER DOTLESS I
    'imof': u'\u22b7',                            #IMAGE OF
    'imped': u'\u01b5',                           #LATIN CAPITAL LETTER Z WITH STROKE
    'Implies': u'\u21d2',                         #RIGHTWARDS DOUBLE ARROW
    'in': u'\u2208',                              #ELEMENT OF
    'incare': u'\u2105',                          #CARE OF
    'infin': u'\u221e',                           #INFINITY
    'infintie': u'\u29dd',                        #TIE OVER INFINITY
    'inodot': u'\u0131',                          #LATIN SMALL LETTER DOTLESS I
    'Int': u'\u222c',                             #DOUBLE INTEGRAL
    'int': u'\u222b',                             #INTEGRAL
    'intcal': u'\u22ba',                          #INTERCALATE
    'integers': u'\u2124',                        #DOUBLE-STRUCK CAPITAL Z
    'Integral': u'\u222b',                        #INTEGRAL
    'intercal': u'\u22ba',                        #INTERCALATE
    'Intersection': u'\u22c2',                    #N-ARY INTERSECTION
    'intlarhk': u'\u2a17',                        #INTEGRAL WITH LEFTWARDS ARROW WITH HOOK
    'intprod': u'\u2a3c',                         #INTERIOR PRODUCT
    'InvisibleComma': u'\u2063',                  #INVISIBLE SEPARATOR
    'InvisibleTimes': u'\u2062',                  #INVISIBLE TIMES
    'IOcy': u'\u0401',                            #CYRILLIC CAPITAL LETTER IO
    'iocy': u'\u0451',                            #CYRILLIC SMALL LETTER IO
    'Iogon': u'\u012e',                           #LATIN CAPITAL LETTER I WITH OGONEK
    'iogon': u'\u012f',                           #LATIN SMALL LETTER I WITH OGONEK
    'Iopf': u'\U0001d540',                        #MATHEMATICAL DOUBLE-STRUCK CAPITAL I
    'iopf': u'\U0001d55a',                        #MATHEMATICAL DOUBLE-STRUCK SMALL I
    'Iota': u'\u0399',                            #GREEK CAPITAL LETTER IOTA
    'iota': u'\u03b9',                            #GREEK SMALL LETTER IOTA
    'iprod': u'\u2a3c',                           #INTERIOR PRODUCT
    'iquest': u'\xbf',                            #INVERTED QUESTION MARK
    'Iscr': u'\u2110',                            #SCRIPT CAPITAL I
    'iscr': u'\U0001d4be',                        #MATHEMATICAL SCRIPT SMALL I
    'isin': u'\u2208',                            #ELEMENT OF
    'isindot': u'\u22f5',                         #ELEMENT OF WITH DOT ABOVE
    'isinE': u'\u22f9',                           #ELEMENT OF WITH TWO HORIZONTAL STROKES
    'isins': u'\u22f4',                           #SMALL ELEMENT OF WITH VERTICAL BAR AT END OF HORIZONTAL STROKE
    'isinsv': u'\u22f3',                          #ELEMENT OF WITH VERTICAL BAR AT END OF HORIZONTAL STROKE
    'isinv': u'\u2208',                           #ELEMENT OF
    'it': u'\u2062',                              #INVISIBLE TIMES
    'Itilde': u'\u0128',                          #LATIN CAPITAL LETTER I WITH TILDE
    'itilde': u'\u0129',                          #LATIN SMALL LETTER I WITH TILDE
    'Iukcy': u'\u0406',                           #CYRILLIC CAPITAL LETTER BYELORUSSIAN-UKRAINIAN I
    'iukcy': u'\u0456',                           #CYRILLIC SMALL LETTER BYELORUSSIAN-UKRAINIAN I
    'Iuml': u'\xcf',                              #LATIN CAPITAL LETTER I WITH DIAERESIS
    'iuml': u'\xef',                              #LATIN SMALL LETTER I WITH DIAERESIS
    'Jcirc': u'\u0134',                           #LATIN CAPITAL LETTER J WITH CIRCUMFLEX
    'jcirc': u'\u0135',                           #LATIN SMALL LETTER J WITH CIRCUMFLEX
    'Jcy': u'\u0419',                             #CYRILLIC CAPITAL LETTER SHORT I
    'jcy': u'\u0439',                             #CYRILLIC SMALL LETTER SHORT I
    'Jfr': u'\U0001d50d',                         #MATHEMATICAL FRAKTUR CAPITAL J
    'jfr': u'\U0001d527',                         #MATHEMATICAL FRAKTUR SMALL J
    'jmath': u'\u0237',                           #LATIN SMALL LETTER DOTLESS J
    'Jopf': u'\U0001d541',                        #MATHEMATICAL DOUBLE-STRUCK CAPITAL J
    'jopf': u'\U0001d55b',                        #MATHEMATICAL DOUBLE-STRUCK SMALL J
    'Jscr': u'\U0001d4a5',                        #MATHEMATICAL SCRIPT CAPITAL J
    'jscr': u'\U0001d4bf',                        #MATHEMATICAL SCRIPT SMALL J
    'Jsercy': u'\u0408',                          #CYRILLIC CAPITAL LETTER JE
    'jsercy': u'\u0458',                          #CYRILLIC SMALL LETTER JE
    'Jukcy': u'\u0404',                           #CYRILLIC CAPITAL LETTER UKRAINIAN IE
    'jukcy': u'\u0454',                           #CYRILLIC SMALL LETTER UKRAINIAN IE
    'Kappa': u'\u039a',                           #GREEK CAPITAL LETTER KAPPA
    'kappa': u'\u03ba',                           #GREEK SMALL LETTER KAPPA
    'kappav': u'\u03f0',                          #GREEK KAPPA SYMBOL
    'Kcedil': u'\u0136',                          #LATIN CAPITAL LETTER K WITH CEDILLA
    'kcedil': u'\u0137',                          #LATIN SMALL LETTER K WITH CEDILLA
    'Kcy': u'\u041a',                             #CYRILLIC CAPITAL LETTER KA
    'kcy': u'\u043a',                             #CYRILLIC SMALL LETTER KA
    'Kfr': u'\U0001d50e',                         #MATHEMATICAL FRAKTUR CAPITAL K
    'kfr': u'\U0001d528',                         #MATHEMATICAL FRAKTUR SMALL K
    'kgreen': u'\u0138',                          #LATIN SMALL LETTER KRA
    'KHcy': u'\u0425',                            #CYRILLIC CAPITAL LETTER HA
    'khcy': u'\u0445',                            #CYRILLIC SMALL LETTER HA
    'KJcy': u'\u040c',                            #CYRILLIC CAPITAL LETTER KJE
    'kjcy': u'\u045c',                            #CYRILLIC SMALL LETTER KJE
    'Kopf': u'\U0001d542',                        #MATHEMATICAL DOUBLE-STRUCK CAPITAL K
    'kopf': u'\U0001d55c',                        #MATHEMATICAL DOUBLE-STRUCK SMALL K
    'Kscr': u'\U0001d4a6',                        #MATHEMATICAL SCRIPT CAPITAL K
    'kscr': u'\U0001d4c0',                        #MATHEMATICAL SCRIPT SMALL K
    'lAarr': u'\u21da',                           #LEFTWARDS TRIPLE ARROW
    'Lacute': u'\u0139',                          #LATIN CAPITAL LETTER L WITH ACUTE
    'lacute': u'\u013a',                          #LATIN SMALL LETTER L WITH ACUTE
    'laemptyv': u'\u29b4',                        #EMPTY SET WITH LEFT ARROW ABOVE
    'lagran': u'\u2112',                          #SCRIPT CAPITAL L
    'Lambda': u'\u039b',                          #GREEK CAPITAL LETTER LAMDA
    'lambda': u'\u03bb',                          #GREEK SMALL LETTER LAMDA
    'Lang': u'\u27ea',                            #MATHEMATICAL LEFT DOUBLE ANGLE BRACKET
    'lang': u'\u27e8',                            #MATHEMATICAL LEFT ANGLE BRACKET
    'langd': u'\u2991',                           #LEFT ANGLE BRACKET WITH DOT
    'langle': u'\u27e8',                          #MATHEMATICAL LEFT ANGLE BRACKET
    'lap': u'\u2a85',                             #LESS-THAN OR APPROXIMATE
    'Laplacetrf': u'\u2112',                      #SCRIPT CAPITAL L
    'laquo': u'\xab',                             #LEFT-POINTING DOUBLE ANGLE QUOTATION MARK
    'Larr': u'\u219e',                            #LEFTWARDS TWO HEADED ARROW
    'lArr': u'\u21d0',                            #LEFTWARDS DOUBLE ARROW
    'larr': u'\u2190',                            #LEFTWARDS ARROW
    'larrb': u'\u21e4',                           #LEFTWARDS ARROW TO BAR
    'larrbfs': u'\u291f',                         #LEFTWARDS ARROW FROM BAR TO BLACK DIAMOND
    'larrfs': u'\u291d',                          #LEFTWARDS ARROW TO BLACK DIAMOND
    'larrhk': u'\u21a9',                          #LEFTWARDS ARROW WITH HOOK
    'larrlp': u'\u21ab',                          #LEFTWARDS ARROW WITH LOOP
    'larrpl': u'\u2939',                          #LEFT-SIDE ARC ANTICLOCKWISE ARROW
    'larrsim': u'\u2973',                         #LEFTWARDS ARROW ABOVE TILDE OPERATOR
    'larrtl': u'\u21a2',                          #LEFTWARDS ARROW WITH TAIL
    'lat': u'\u2aab',                             #LARGER THAN
    'lAtail': u'\u291b',                          #LEFTWARDS DOUBLE ARROW-TAIL
    'latail': u'\u2919',                          #LEFTWARDS ARROW-TAIL
    'late': u'\u2aad',                            #LARGER THAN OR EQUAL TO
    'lates': u'\u2aad\ufe00',                     #LARGER THAN OR slanted EQUAL
    'lBarr': u'\u290e',                           #LEFTWARDS TRIPLE DASH ARROW
    'lbarr': u'\u290c',                           #LEFTWARDS DOUBLE DASH ARROW
    'lbbrk': u'\u2772',                           #LIGHT LEFT TORTOISE SHELL BRACKET ORNAMENT
    'lbrace': u'{',                               #LEFT CURLY BRACKET
    'lbrack': u'[',                               #LEFT SQUARE BRACKET
    'lbrke': u'\u298b',                           #LEFT SQUARE BRACKET WITH UNDERBAR
    'lbrksld': u'\u298f',                         #LEFT SQUARE BRACKET WITH TICK IN BOTTOM CORNER
    'lbrkslu': u'\u298d',                         #LEFT SQUARE BRACKET WITH TICK IN TOP CORNER
    'Lcaron': u'\u013d',                          #LATIN CAPITAL LETTER L WITH CARON
    'lcaron': u'\u013e',                          #LATIN SMALL LETTER L WITH CARON
    'Lcedil': u'\u013b',                          #LATIN CAPITAL LETTER L WITH CEDILLA
    'lcedil': u'\u013c',                          #LATIN SMALL LETTER L WITH CEDILLA
    'lceil': u'\u2308',                           #LEFT CEILING
    'lcub': u'{',                                 #LEFT CURLY BRACKET
    'Lcy': u'\u041b',                             #CYRILLIC CAPITAL LETTER EL
    'lcy': u'\u043b',                             #CYRILLIC SMALL LETTER EL
    'ldca': u'\u2936',                            #ARROW POINTING DOWNWARDS THEN CURVING LEFTWARDS
    'ldquo': u'\u201c',                           #LEFT DOUBLE QUOTATION MARK
    'ldquor': u'\u201e',                          #DOUBLE LOW-9 QUOTATION MARK
    'ldrdhar': u'\u2967',                         #LEFTWARDS HARPOON WITH BARB DOWN ABOVE RIGHTWARDS HARPOON WITH BARB DOWN
    'ldrushar': u'\u294b',                        #LEFT BARB DOWN RIGHT BARB UP HARPOON
    'ldsh': u'\u21b2',                            #DOWNWARDS ARROW WITH TIP LEFTWARDS
    'lE': u'\u2266',                              #LESS-THAN OVER EQUAL TO
    'le': u'\u2264',                              #LESS-THAN OR EQUAL TO
    'LeftAngleBracket': u'\u27e8',                #MATHEMATICAL LEFT ANGLE BRACKET
    'LeftArrow': u'\u2190',                       #LEFTWARDS ARROW
    'Leftarrow': u'\u21d0',                       #LEFTWARDS DOUBLE ARROW
    'leftarrow': u'\u2190',                       #LEFTWARDS ARROW
    'LeftArrowBar': u'\u21e4',                    #LEFTWARDS ARROW TO BAR
    'LeftArrowRightArrow': u'\u21c6',             #LEFTWARDS ARROW OVER RIGHTWARDS ARROW
    'leftarrowtail': u'\u21a2',                   #LEFTWARDS ARROW WITH TAIL
    'LeftCeiling': u'\u2308',                     #LEFT CEILING
    'LeftDoubleBracket': u'\u27e6',               #MATHEMATICAL LEFT WHITE SQUARE BRACKET
    'LeftDownTeeVector': u'\u2961',               #DOWNWARDS HARPOON WITH BARB LEFT FROM BAR
    'LeftDownVector': u'\u21c3',                  #DOWNWARDS HARPOON WITH BARB LEFTWARDS
    'LeftDownVectorBar': u'\u2959',               #DOWNWARDS HARPOON WITH BARB LEFT TO BAR
    'LeftFloor': u'\u230a',                       #LEFT FLOOR
    'leftharpoondown': u'\u21bd',                 #LEFTWARDS HARPOON WITH BARB DOWNWARDS
    'leftharpoonup': u'\u21bc',                   #LEFTWARDS HARPOON WITH BARB UPWARDS
    'leftleftarrows': u'\u21c7',                  #LEFTWARDS PAIRED ARROWS
    'LeftRightArrow': u'\u2194',                  #LEFT RIGHT ARROW
    'Leftrightarrow': u'\u21d4',                  #LEFT RIGHT DOUBLE ARROW
    'leftrightarrow': u'\u2194',                  #LEFT RIGHT ARROW
    'leftrightarrows': u'\u21c6',                 #LEFTWARDS ARROW OVER RIGHTWARDS ARROW
    'leftrightharpoons': u'\u21cb',               #LEFTWARDS HARPOON OVER RIGHTWARDS HARPOON
    'leftrightsquigarrow': u'\u21ad',             #LEFT RIGHT WAVE ARROW
    'LeftRightVector': u'\u294e',                 #LEFT BARB UP RIGHT BARB UP HARPOON
    'LeftTee': u'\u22a3',                         #LEFT TACK
    'LeftTeeArrow': u'\u21a4',                    #LEFTWARDS ARROW FROM BAR
    'LeftTeeVector': u'\u295a',                   #LEFTWARDS HARPOON WITH BARB UP FROM BAR
    'leftthreetimes': u'\u22cb',                  #LEFT SEMIDIRECT PRODUCT
    'LeftTriangle': u'\u22b2',                    #NORMAL SUBGROUP OF
    'LeftTriangleBar': u'\u29cf',                 #LEFT TRIANGLE BESIDE VERTICAL BAR
    'LeftTriangleEqual': u'\u22b4',               #NORMAL SUBGROUP OF OR EQUAL TO
    'LeftUpDownVector': u'\u2951',                #UP BARB LEFT DOWN BARB LEFT HARPOON
    'LeftUpTeeVector': u'\u2960',                 #UPWARDS HARPOON WITH BARB LEFT FROM BAR
    'LeftUpVector': u'\u21bf',                    #UPWARDS HARPOON WITH BARB LEFTWARDS
    'LeftUpVectorBar': u'\u2958',                 #UPWARDS HARPOON WITH BARB LEFT TO BAR
    'LeftVector': u'\u21bc',                      #LEFTWARDS HARPOON WITH BARB UPWARDS
    'LeftVectorBar': u'\u2952',                   #LEFTWARDS HARPOON WITH BARB UP TO BAR
    'lEg': u'\u2a8b',                             #LESS-THAN ABOVE DOUBLE-LINE EQUAL ABOVE GREATER-THAN
    'leg': u'\u22da',                             #LESS-THAN EQUAL TO OR GREATER-THAN
    'leq': u'\u2264',                             #LESS-THAN OR EQUAL TO
    'leqq': u'\u2266',                            #LESS-THAN OVER EQUAL TO
    'leqslant': u'\u2a7d',                        #LESS-THAN OR SLANTED EQUAL TO
    'les': u'\u2a7d',                             #LESS-THAN OR SLANTED EQUAL TO
    'lescc': u'\u2aa8',                           #LESS-THAN CLOSED BY CURVE ABOVE SLANTED EQUAL
    'lesdot': u'\u2a7f',                          #LESS-THAN OR SLANTED EQUAL TO WITH DOT INSIDE
    'lesdoto': u'\u2a81',                         #LESS-THAN OR SLANTED EQUAL TO WITH DOT ABOVE
    'lesdotor': u'\u2a83',                        #LESS-THAN OR SLANTED EQUAL TO WITH DOT ABOVE RIGHT
    'lesg': u'\u22da\ufe00',                      #LESS-THAN slanted EQUAL TO OR GREATER-THAN
    'lesges': u'\u2a93',                          #LESS-THAN ABOVE SLANTED EQUAL ABOVE GREATER-THAN ABOVE SLANTED EQUAL
    'lessapprox': u'\u2a85',                      #LESS-THAN OR APPROXIMATE
    'lessdot': u'\u22d6',                         #LESS-THAN WITH DOT
    'lesseqgtr': u'\u22da',                       #LESS-THAN EQUAL TO OR GREATER-THAN
    'lesseqqgtr': u'\u2a8b',                      #LESS-THAN ABOVE DOUBLE-LINE EQUAL ABOVE GREATER-THAN
    'LessEqualGreater': u'\u22da',                #LESS-THAN EQUAL TO OR GREATER-THAN
    'LessFullEqual': u'\u2266',                   #LESS-THAN OVER EQUAL TO
    'LessGreater': u'\u2276',                     #LESS-THAN OR GREATER-THAN
    'lessgtr': u'\u2276',                         #LESS-THAN OR GREATER-THAN
    'LessLess': u'\u2aa1',                        #DOUBLE NESTED LESS-THAN
    'lesssim': u'\u2272',                         #LESS-THAN OR EQUIVALENT TO
    'LessSlantEqual': u'\u2a7d',                  #LESS-THAN OR SLANTED EQUAL TO
    'LessTilde': u'\u2272',                       #LESS-THAN OR EQUIVALENT TO
    'lfisht': u'\u297c',                          #LEFT FISH TAIL
    'lfloor': u'\u230a',                          #LEFT FLOOR
    'Lfr': u'\U0001d50f',                         #MATHEMATICAL FRAKTUR CAPITAL L
    'lfr': u'\U0001d529',                         #MATHEMATICAL FRAKTUR SMALL L
    'lg': u'\u2276',                              #LESS-THAN OR GREATER-THAN
    'lgE': u'\u2a91',                             #LESS-THAN ABOVE GREATER-THAN ABOVE DOUBLE-LINE EQUAL
    'lHar': u'\u2962',                            #LEFTWARDS HARPOON WITH BARB UP ABOVE LEFTWARDS HARPOON WITH BARB DOWN
    'lhard': u'\u21bd',                           #LEFTWARDS HARPOON WITH BARB DOWNWARDS
    'lharu': u'\u21bc',                           #LEFTWARDS HARPOON WITH BARB UPWARDS
    'lharul': u'\u296a',                          #LEFTWARDS HARPOON WITH BARB UP ABOVE LONG DASH
    'lhblk': u'\u2584',                           #LOWER HALF BLOCK
    'LJcy': u'\u0409',                            #CYRILLIC CAPITAL LETTER LJE
    'ljcy': u'\u0459',                            #CYRILLIC SMALL LETTER LJE
    'Ll': u'\u22d8',                              #VERY MUCH LESS-THAN
    'll': u'\u226a',                              #MUCH LESS-THAN
    'llarr': u'\u21c7',                           #LEFTWARDS PAIRED ARROWS
    'llcorner': u'\u231e',                        #BOTTOM LEFT CORNER
    'Lleftarrow': u'\u21da',                      #LEFTWARDS TRIPLE ARROW
    'llhard': u'\u296b',                          #LEFTWARDS HARPOON WITH BARB DOWN BELOW LONG DASH
    'lltri': u'\u25fa',                           #LOWER LEFT TRIANGLE
    'Lmidot': u'\u013f',                          #LATIN CAPITAL LETTER L WITH MIDDLE DOT
    'lmidot': u'\u0140',                          #LATIN SMALL LETTER L WITH MIDDLE DOT
    'lmoust': u'\u23b0',                          #UPPER LEFT OR LOWER RIGHT CURLY BRACKET SECTION
    'lmoustache': u'\u23b0',                      #UPPER LEFT OR LOWER RIGHT CURLY BRACKET SECTION
    'lnap': u'\u2a89',                            #LESS-THAN AND NOT APPROXIMATE
    'lnapprox': u'\u2a89',                        #LESS-THAN AND NOT APPROXIMATE
    'lnE': u'\u2268',                             #LESS-THAN BUT NOT EQUAL TO
    'lne': u'\u2a87',                             #LESS-THAN AND SINGLE-LINE NOT EQUAL TO
    'lneq': u'\u2a87',                            #LESS-THAN AND SINGLE-LINE NOT EQUAL TO
    'lneqq': u'\u2268',                           #LESS-THAN BUT NOT EQUAL TO
    'lnsim': u'\u22e6',                           #LESS-THAN BUT NOT EQUIVALENT TO
    'loang': u'\u27ec',                           #MATHEMATICAL LEFT WHITE TORTOISE SHELL BRACKET
    'loarr': u'\u21fd',                           #LEFTWARDS OPEN-HEADED ARROW
    'lobrk': u'\u27e6',                           #MATHEMATICAL LEFT WHITE SQUARE BRACKET
    'LongLeftArrow': u'\u27f5',                   #LONG LEFTWARDS ARROW
    'Longleftarrow': u'\u27f8',                   #LONG LEFTWARDS DOUBLE ARROW
    'longleftarrow': u'\u27f5',                   #LONG LEFTWARDS ARROW
    'LongLeftRightArrow': u'\u27f7',              #LONG LEFT RIGHT ARROW
    'Longleftrightarrow': u'\u27fa',              #LONG LEFT RIGHT DOUBLE ARROW
    'longleftrightarrow': u'\u27f7',              #LONG LEFT RIGHT ARROW
    'longmapsto': u'\u27fc',                      #LONG RIGHTWARDS ARROW FROM BAR
    'LongRightArrow': u'\u27f6',                  #LONG RIGHTWARDS ARROW
    'Longrightarrow': u'\u27f9',                  #LONG RIGHTWARDS DOUBLE ARROW
    'longrightarrow': u'\u27f6',                  #LONG RIGHTWARDS ARROW
    'looparrowleft': u'\u21ab',                   #LEFTWARDS ARROW WITH LOOP
    'looparrowright': u'\u21ac',                  #RIGHTWARDS ARROW WITH LOOP
    'lopar': u'\u2985',                           #LEFT WHITE PARENTHESIS
    'Lopf': u'\U0001d543',                        #MATHEMATICAL DOUBLE-STRUCK CAPITAL L
    'lopf': u'\U0001d55d',                        #MATHEMATICAL DOUBLE-STRUCK SMALL L
    'loplus': u'\u2a2d',                          #PLUS SIGN IN LEFT HALF CIRCLE
    'lotimes': u'\u2a34',                         #MULTIPLICATION SIGN IN LEFT HALF CIRCLE
    'lowast': u'\u2217',                          #ASTERISK OPERATOR
    'lowbar': u'_',                               #LOW LINE
    'LowerLeftArrow': u'\u2199',                  #SOUTH WEST ARROW
    'LowerRightArrow': u'\u2198',                 #SOUTH EAST ARROW
    'loz': u'\u25ca',                             #LOZENGE
    'lozenge': u'\u25ca',                         #LOZENGE
    'lozf': u'\u29eb',                            #BLACK LOZENGE
    'lpar': u'(',                                 #LEFT PARENTHESIS
    'lparlt': u'\u2993',                          #LEFT ARC LESS-THAN BRACKET
    'lrarr': u'\u21c6',                           #LEFTWARDS ARROW OVER RIGHTWARDS ARROW
    'lrcorner': u'\u231f',                        #BOTTOM RIGHT CORNER
    'lrhar': u'\u21cb',                           #LEFTWARDS HARPOON OVER RIGHTWARDS HARPOON
    'lrhard': u'\u296d',                          #RIGHTWARDS HARPOON WITH BARB DOWN BELOW LONG DASH
    'lrm': u'\u200e',                             #LEFT-TO-RIGHT MARK
    'lrtri': u'\u22bf',                           #RIGHT TRIANGLE
    'lsaquo': u'\u2039',                          #SINGLE LEFT-POINTING ANGLE QUOTATION MARK
    'Lscr': u'\u2112',                            #SCRIPT CAPITAL L
    'lscr': u'\U0001d4c1',                        #MATHEMATICAL SCRIPT SMALL L
    'Lsh': u'\u21b0',                             #UPWARDS ARROW WITH TIP LEFTWARDS
    'lsh': u'\u21b0',                             #UPWARDS ARROW WITH TIP LEFTWARDS
    'lsim': u'\u2272',                            #LESS-THAN OR EQUIVALENT TO
    'lsime': u'\u2a8d',                           #LESS-THAN ABOVE SIMILAR OR EQUAL
    'lsimg': u'\u2a8f',                           #LESS-THAN ABOVE SIMILAR ABOVE GREATER-THAN
    'lsqb': u'[',                                 #LEFT SQUARE BRACKET
    'lsquo': u'\u2018',                           #LEFT SINGLE QUOTATION MARK
    'lsquor': u'\u201a',                          #SINGLE LOW-9 QUOTATION MARK
    'Lstrok': u'\u0141',                          #LATIN CAPITAL LETTER L WITH STROKE
    'lstrok': u'\u0142',                          #LATIN SMALL LETTER L WITH STROKE
    'LT': u'\x3c',                                    #LESS-THAN SIGN
    'Lt': u'\u226a',                              #MUCH LESS-THAN
    'lt': u'\x3c',                                    #LESS-THAN SIGN
    'ltcc': u'\u2aa6',                            #LESS-THAN CLOSED BY CURVE
    'ltcir': u'\u2a79',                           #LESS-THAN WITH CIRCLE INSIDE
    'ltdot': u'\u22d6',                           #LESS-THAN WITH DOT
    'lthree': u'\u22cb',                          #LEFT SEMIDIRECT PRODUCT
    'ltimes': u'\u22c9',                          #LEFT NORMAL FACTOR SEMIDIRECT PRODUCT
    'ltlarr': u'\u2976',                          #LESS-THAN ABOVE LEFTWARDS ARROW
    'ltquest': u'\u2a7b',                         #LESS-THAN WITH QUESTION MARK ABOVE
    'ltri': u'\u25c3',                            #WHITE LEFT-POINTING SMALL TRIANGLE
    'ltrie': u'\u22b4',                           #NORMAL SUBGROUP OF OR EQUAL TO
    'ltrif': u'\u25c2',                           #BLACK LEFT-POINTING SMALL TRIANGLE
    'ltrPar': u'\u2996',                          #DOUBLE RIGHT ARC LESS-THAN BRACKET
    'lurdshar': u'\u294a',                        #LEFT BARB UP RIGHT BARB DOWN HARPOON
    'luruhar': u'\u2966',                         #LEFTWARDS HARPOON WITH BARB UP ABOVE RIGHTWARDS HARPOON WITH BARB UP
    'lvertneqq': u'\u2268\ufe00',                 #LESS-THAN BUT NOT EQUAL TO - with vertical stroke
    'lvnE': u'\u2268\ufe00',                      #LESS-THAN BUT NOT EQUAL TO - with vertical stroke
    'macr': u'\xaf',                              #MACRON
    'male': u'\u2642',                            #MALE SIGN
    'malt': u'\u2720',                            #MALTESE CROSS
    'maltese': u'\u2720',                         #MALTESE CROSS
    'Map': u'\u2905',                             #RIGHTWARDS TWO-HEADED ARROW FROM BAR
    'map': u'\u21a6',                             #RIGHTWARDS ARROW FROM BAR
    'mapsto': u'\u21a6',                          #RIGHTWARDS ARROW FROM BAR
    'mapstodown': u'\u21a7',                      #DOWNWARDS ARROW FROM BAR
    'mapstoleft': u'\u21a4',                      #LEFTWARDS ARROW FROM BAR
    'mapstoup': u'\u21a5',                        #UPWARDS ARROW FROM BAR
    'marker': u'\u25ae',                          #BLACK VERTICAL RECTANGLE
    'mcomma': u'\u2a29',                          #MINUS SIGN WITH COMMA ABOVE
    'Mcy': u'\u041c',                             #CYRILLIC CAPITAL LETTER EM
    'mcy': u'\u043c',                             #CYRILLIC SMALL LETTER EM
    'mdash': u'\u2014',                           #EM DASH
    'mDDot': u'\u223a',                           #GEOMETRIC PROPORTION
    'measuredangle': u'\u2221',                   #MEASURED ANGLE
    'MediumSpace': u'\u205f',                     #MEDIUM MATHEMATICAL SPACE
    'Mellintrf': u'\u2133',                       #SCRIPT CAPITAL M
    'Mfr': u'\U0001d510',                         #MATHEMATICAL FRAKTUR CAPITAL M
    'mfr': u'\U0001d52a',                         #MATHEMATICAL FRAKTUR SMALL M
    'mho': u'\u2127',                             #INVERTED OHM SIGN
    'micro': u'\xb5',                             #MICRO SIGN
    'mid': u'\u2223',                             #DIVIDES
    'midast': u'*',                               #ASTERISK
    'midcir': u'\u2af0',                          #VERTICAL LINE WITH CIRCLE BELOW
    'middot': u'\xb7',                            #MIDDLE DOT
    'minus': u'\u2212',                           #MINUS SIGN
    'minusb': u'\u229f',                          #SQUARED MINUS
    'minusd': u'\u2238',                          #DOT MINUS
    'minusdu': u'\u2a2a',                         #MINUS SIGN WITH DOT BELOW
    'MinusPlus': u'\u2213',                       #MINUS-OR-PLUS SIGN
    'mlcp': u'\u2adb',                            #TRANSVERSAL INTERSECTION
    'mldr': u'\u2026',                            #HORIZONTAL ELLIPSIS
    'mnplus': u'\u2213',                          #MINUS-OR-PLUS SIGN
    'models': u'\u22a7',                          #MODELS
    'Mopf': u'\U0001d544',                        #MATHEMATICAL DOUBLE-STRUCK CAPITAL M
    'mopf': u'\U0001d55e',                        #MATHEMATICAL DOUBLE-STRUCK SMALL M
    'mp': u'\u2213',                              #MINUS-OR-PLUS SIGN
    'Mscr': u'\u2133',                            #SCRIPT CAPITAL M
    'mscr': u'\U0001d4c2',                        #MATHEMATICAL SCRIPT SMALL M
    'mstpos': u'\u223e',                          #INVERTED LAZY S
    'Mu': u'\u039c',                              #GREEK CAPITAL LETTER MU
    'mu': u'\u03bc',                              #GREEK SMALL LETTER MU
    'multimap': u'\u22b8',                        #MULTIMAP
    'mumap': u'\u22b8',                           #MULTIMAP
    'nabla': u'\u2207',                           #NABLA
    'Nacute': u'\u0143',                          #LATIN CAPITAL LETTER N WITH ACUTE
    'nacute': u'\u0144',                          #LATIN SMALL LETTER N WITH ACUTE
    'nang': u'\u2220\u20d2',                      #ANGLE with vertical line
    'nap': u'\u2249',                             #NOT ALMOST EQUAL TO
    'napE': u'\u2a70\u0338',                      #APPROXIMATELY EQUAL OR EQUAL TO with slash
    'napid': u'\u224b\u0338',                     #TRIPLE TILDE with slash
    'napos': u'\u0149',                           #LATIN SMALL LETTER N PRECEDED BY APOSTROPHE
    'napprox': u'\u2249',                         #NOT ALMOST EQUAL TO
    'natur': u'\u266e',                           #MUSIC NATURAL SIGN
    'natural': u'\u266e',                         #MUSIC NATURAL SIGN
    'naturals': u'\u2115',                        #DOUBLE-STRUCK CAPITAL N
    'nbsp': u'\xa0',                              #NO-BREAK SPACE
    'nbump': u'\u224e\u0338',                     #GEOMETRICALLY EQUIVALENT TO with slash
    'nbumpe': u'\u224f\u0338',                    #DIFFERENCE BETWEEN with slash
    'ncap': u'\u2a43',                            #INTERSECTION WITH OVERBAR
    'Ncaron': u'\u0147',                          #LATIN CAPITAL LETTER N WITH CARON
    'ncaron': u'\u0148',                          #LATIN SMALL LETTER N WITH CARON
    'Ncedil': u'\u0145',                          #LATIN CAPITAL LETTER N WITH CEDILLA
    'ncedil': u'\u0146',                          #LATIN SMALL LETTER N WITH CEDILLA
    'ncong': u'\u2247',                           #NEITHER APPROXIMATELY NOR ACTUALLY EQUAL TO
    'ncongdot': u'\u2a6d\u0338',                  #CONGRUENT WITH DOT ABOVE with slash
    'ncup': u'\u2a42',                            #UNION WITH OVERBAR
    'Ncy': u'\u041d',                             #CYRILLIC CAPITAL LETTER EN
    'ncy': u'\u043d',                             #CYRILLIC SMALL LETTER EN
    'ndash': u'\u2013',                           #EN DASH
    'ne': u'\u2260',                              #NOT EQUAL TO
    'nearhk': u'\u2924',                          #NORTH EAST ARROW WITH HOOK
    'neArr': u'\u21d7',                           #NORTH EAST DOUBLE ARROW
    'nearr': u'\u2197',                           #NORTH EAST ARROW
    'nearrow': u'\u2197',                         #NORTH EAST ARROW
    'nedot': u'\u2250\u0338',                     #APPROACHES THE LIMIT with slash
    'NegativeMediumSpace': u'\u200b',             #ZERO WIDTH SPACE
    'NegativeThickSpace': u'\u200b',              #ZERO WIDTH SPACE
    'NegativeThinSpace': u'\u200b',               #ZERO WIDTH SPACE
    'NegativeVeryThinSpace': u'\u200b',           #ZERO WIDTH SPACE
    'nequiv': u'\u2262',                          #NOT IDENTICAL TO
    'nesear': u'\u2928',                          #NORTH EAST ARROW AND SOUTH EAST ARROW
    'nesim': u'\u2242\u0338',                     #MINUS TILDE with slash
    'NestedGreaterGreater': u'\u226b',            #MUCH GREATER-THAN
    'NestedLessLess': u'\u226a',                  #MUCH LESS-THAN
    'NewLine': u'\n',                             #LINE FEED (LF)
    'nexist': u'\u2204',                          #THERE DOES NOT EXIST
    'nexists': u'\u2204',                         #THERE DOES NOT EXIST
    'Nfr': u'\U0001d511',                         #MATHEMATICAL FRAKTUR CAPITAL N
    'nfr': u'\U0001d52b',                         #MATHEMATICAL FRAKTUR SMALL N
    'ngE': u'\u2267\u0338',                       #GREATER-THAN OVER EQUAL TO with slash
    'nge': u'\u2271',                             #NEITHER GREATER-THAN NOR EQUAL TO
    'ngeq': u'\u2271',                            #NEITHER GREATER-THAN NOR EQUAL TO
    'ngeqq': u'\u2267\u0338',                     #GREATER-THAN OVER EQUAL TO with slash
    'ngeqslant': u'\u2a7e\u0338',                 #GREATER-THAN OR SLANTED EQUAL TO with slash
    'nges': u'\u2a7e\u0338',                      #GREATER-THAN OR SLANTED EQUAL TO with slash
    'nGg': u'\u22d9\u0338',                       #VERY MUCH GREATER-THAN with slash
    'ngsim': u'\u2275',                           #NEITHER GREATER-THAN NOR EQUIVALENT TO
    'nGt': u'\u226b\u20d2',                       #MUCH GREATER THAN with vertical line
    'ngt': u'\u226f',                             #NOT GREATER-THAN
    'ngtr': u'\u226f',                            #NOT GREATER-THAN
    'nGtv': u'\u226b\u0338',                      #MUCH GREATER THAN with slash
    'nhArr': u'\u21ce',                           #LEFT RIGHT DOUBLE ARROW WITH STROKE
    'nharr': u'\u21ae',                           #LEFT RIGHT ARROW WITH STROKE
    'nhpar': u'\u2af2',                           #PARALLEL WITH HORIZONTAL STROKE
    'ni': u'\u220b',                              #CONTAINS AS MEMBER
    'nis': u'\u22fc',                             #SMALL CONTAINS WITH VERTICAL BAR AT END OF HORIZONTAL STROKE
    'nisd': u'\u22fa',                            #CONTAINS WITH LONG HORIZONTAL STROKE
    'niv': u'\u220b',                             #CONTAINS AS MEMBER
    'NJcy': u'\u040a',                            #CYRILLIC CAPITAL LETTER NJE
    'njcy': u'\u045a',                            #CYRILLIC SMALL LETTER NJE
    'nlArr': u'\u21cd',                           #LEFTWARDS DOUBLE ARROW WITH STROKE
    'nlarr': u'\u219a',                           #LEFTWARDS ARROW WITH STROKE
    'nldr': u'\u2025',                            #TWO DOT LEADER
    'nlE': u'\u2266\u0338',                       #LESS-THAN OVER EQUAL TO with slash
    'nle': u'\u2270',                             #NEITHER LESS-THAN NOR EQUAL TO
    'nLeftarrow': u'\u21cd',                      #LEFTWARDS DOUBLE ARROW WITH STROKE
    'nleftarrow': u'\u219a',                      #LEFTWARDS ARROW WITH STROKE
    'nLeftrightarrow': u'\u21ce',                 #LEFT RIGHT DOUBLE ARROW WITH STROKE
    'nleftrightarrow': u'\u21ae',                 #LEFT RIGHT ARROW WITH STROKE
    'nleq': u'\u2270',                            #NEITHER LESS-THAN NOR EQUAL TO
    'nleqq': u'\u2266\u0338',                     #LESS-THAN OVER EQUAL TO with slash
    'nleqslant': u'\u2a7d\u0338',                 #LESS-THAN OR SLANTED EQUAL TO with slash
    'nles': u'\u2a7d\u0338',                      #LESS-THAN OR SLANTED EQUAL TO with slash
    'nless': u'\u226e',                           #NOT LESS-THAN
    'nLl': u'\u22d8\u0338',                       #VERY MUCH LESS-THAN with slash
    'nlsim': u'\u2274',                           #NEITHER LESS-THAN NOR EQUIVALENT TO
    'nLt': u'\u226a\u20d2',                       #MUCH LESS THAN with vertical line
    'nlt': u'\u226e',                             #NOT LESS-THAN
    'nltri': u'\u22ea',                           #NOT NORMAL SUBGROUP OF
    'nltrie': u'\u22ec',                          #NOT NORMAL SUBGROUP OF OR EQUAL TO
    'nLtv': u'\u226a\u0338',                      #MUCH LESS THAN with slash
    'nmid': u'\u2224',                            #DOES NOT DIVIDE
    'NoBreak': u'\u2060',                         #WORD JOINER
    'NonBreakingSpace': u'\xa0',                  #NO-BREAK SPACE
    'Nopf': u'\u2115',                            #DOUBLE-STRUCK CAPITAL N
    'nopf': u'\U0001d55f',                        #MATHEMATICAL DOUBLE-STRUCK SMALL N
    'Not': u'\u2aec',                             #DOUBLE STROKE NOT SIGN
    'not': u'\xac',                               #NOT SIGN
    'NotCongruent': u'\u2262',                    #NOT IDENTICAL TO
    'NotCupCap': u'\u226d',                       #NOT EQUIVALENT TO
    'NotDoubleVerticalBar': u'\u2226',            #NOT PARALLEL TO
    'NotElement': u'\u2209',                      #NOT AN ELEMENT OF
    'NotEqual': u'\u2260',                        #NOT EQUAL TO
    'NotEqualTilde': u'\u2242\u0338',             #MINUS TILDE with slash
    'NotExists': u'\u2204',                       #THERE DOES NOT EXIST
    'NotGreater': u'\u226f',                      #NOT GREATER-THAN
    'NotGreaterEqual': u'\u2271',                 #NEITHER GREATER-THAN NOR EQUAL TO
    'NotGreaterFullEqual': u'\u2267\u0338',       #GREATER-THAN OVER EQUAL TO with slash
    'NotGreaterGreater': u'\u226b\u0338',         #MUCH GREATER THAN with slash
    'NotGreaterLess': u'\u2279',                  #NEITHER GREATER-THAN NOR LESS-THAN
    'NotGreaterSlantEqual': u'\u2a7e\u0338',      #GREATER-THAN OR SLANTED EQUAL TO with slash
    'NotGreaterTilde': u'\u2275',                 #NEITHER GREATER-THAN NOR EQUIVALENT TO
    'NotHumpDownHump': u'\u224e\u0338',           #GEOMETRICALLY EQUIVALENT TO with slash
    'NotHumpEqual': u'\u224f\u0338',              #DIFFERENCE BETWEEN with slash
    'notin': u'\u2209',                           #NOT AN ELEMENT OF
    'notindot': u'\u22f5\u0338',                  #ELEMENT OF WITH DOT ABOVE with slash
    'notinE': u'\u22f9\u0338',                    #ELEMENT OF WITH TWO HORIZONTAL STROKES with slash
    'notinva': u'\u2209',                         #NOT AN ELEMENT OF
    'notinvb': u'\u22f7',                         #SMALL ELEMENT OF WITH OVERBAR
    'notinvc': u'\u22f6',                         #ELEMENT OF WITH OVERBAR
    'NotLeftTriangle': u'\u22ea',                 #NOT NORMAL SUBGROUP OF
    'NotLeftTriangleBar': u'\u29cf\u0338',        #LEFT TRIANGLE BESIDE VERTICAL BAR with slash
    'NotLeftTriangleEqual': u'\u22ec',            #NOT NORMAL SUBGROUP OF OR EQUAL TO
    'NotLess': u'\u226e',                         #NOT LESS-THAN
    'NotLessEqual': u'\u2270',                    #NEITHER LESS-THAN NOR EQUAL TO
    'NotLessGreater': u'\u2278',                  #NEITHER LESS-THAN NOR GREATER-THAN
    'NotLessLess': u'\u226a\u0338',               #MUCH LESS THAN with slash
    'NotLessSlantEqual': u'\u2a7d\u0338',         #LESS-THAN OR SLANTED EQUAL TO with slash
    'NotLessTilde': u'\u2274',                    #NEITHER LESS-THAN NOR EQUIVALENT TO
    'NotNestedGreaterGreater': u'\u2aa2\u0338',   #DOUBLE NESTED GREATER-THAN with slash
    'NotNestedLessLess': u'\u2aa1\u0338',         #DOUBLE NESTED LESS-THAN with slash
    'notni': u'\u220c',                           #DOES NOT CONTAIN AS MEMBER
    'notniva': u'\u220c',                         #DOES NOT CONTAIN AS MEMBER
    'notnivb': u'\u22fe',                         #SMALL CONTAINS WITH OVERBAR
    'notnivc': u'\u22fd',                         #CONTAINS WITH OVERBAR
    'NotPrecedes': u'\u2280',                     #DOES NOT PRECEDE
    'NotPrecedesEqual': u'\u2aaf\u0338',          #PRECEDES ABOVE SINGLE-LINE EQUALS SIGN with slash
    'NotPrecedesSlantEqual': u'\u22e0',           #DOES NOT PRECEDE OR EQUAL
    'NotReverseElement': u'\u220c',               #DOES NOT CONTAIN AS MEMBER
    'NotRightTriangle': u'\u22eb',                #DOES NOT CONTAIN AS NORMAL SUBGROUP
    'NotRightTriangleBar': u'\u29d0\u0338',       #VERTICAL BAR BESIDE RIGHT TRIANGLE with slash
    'NotRightTriangleEqual': u'\u22ed',           #DOES NOT CONTAIN AS NORMAL SUBGROUP OR EQUAL
    'NotSquareSubset': u'\u228f\u0338',           #SQUARE IMAGE OF with slash
    'NotSquareSubsetEqual': u'\u22e2',            #NOT SQUARE IMAGE OF OR EQUAL TO
    'NotSquareSuperset': u'\u2290\u0338',         #SQUARE ORIGINAL OF with slash
    'NotSquareSupersetEqual': u'\u22e3',          #NOT SQUARE ORIGINAL OF OR EQUAL TO
    'NotSubset': u'\u2282\u20d2',                 #SUBSET OF with vertical line
    'NotSubsetEqual': u'\u2288',                  #NEITHER A SUBSET OF NOR EQUAL TO
    'NotSucceeds': u'\u2281',                     #DOES NOT SUCCEED
    'NotSucceedsEqual': u'\u2ab0\u0338',          #SUCCEEDS ABOVE SINGLE-LINE EQUALS SIGN with slash
    'NotSucceedsSlantEqual': u'\u22e1',           #DOES NOT SUCCEED OR EQUAL
    'NotSucceedsTilde': u'\u227f\u0338',          #SUCCEEDS OR EQUIVALENT TO with slash
    'NotSuperset': u'\u2283\u20d2',               #SUPERSET OF with vertical line
    'NotSupersetEqual': u'\u2289',                #NEITHER A SUPERSET OF NOR EQUAL TO
    'NotTilde': u'\u2241',                        #NOT TILDE
    'NotTildeEqual': u'\u2244',                   #NOT ASYMPTOTICALLY EQUAL TO
    'NotTildeFullEqual': u'\u2247',               #NEITHER APPROXIMATELY NOR ACTUALLY EQUAL TO
    'NotTildeTilde': u'\u2249',                   #NOT ALMOST EQUAL TO
    'NotVerticalBar': u'\u2224',                  #DOES NOT DIVIDE
    'npar': u'\u2226',                            #NOT PARALLEL TO
    'nparallel': u'\u2226',                       #NOT PARALLEL TO
    'nparsl': u'\u2afd\u20e5',                    #DOUBLE SOLIDUS OPERATOR with reverse slash
    'npart': u'\u2202\u0338',                     #PARTIAL DIFFERENTIAL with slash
    'npolint': u'\u2a14',                         #LINE INTEGRATION NOT INCLUDING THE POLE
    'npr': u'\u2280',                             #DOES NOT PRECEDE
    'nprcue': u'\u22e0',                          #DOES NOT PRECEDE OR EQUAL
    'npre': u'\u2aaf\u0338',                      #PRECEDES ABOVE SINGLE-LINE EQUALS SIGN with slash
    'nprec': u'\u2280',                           #DOES NOT PRECEDE
    'npreceq': u'\u2aaf\u0338',                   #PRECEDES ABOVE SINGLE-LINE EQUALS SIGN with slash
    'nrArr': u'\u21cf',                           #RIGHTWARDS DOUBLE ARROW WITH STROKE
    'nrarr': u'\u219b',                           #RIGHTWARDS ARROW WITH STROKE
    'nrarrc': u'\u2933\u0338',                    #WAVE ARROW POINTING DIRECTLY RIGHT with slash
    'nrarrw': u'\u219d\u0338',                    #RIGHTWARDS WAVE ARROW with slash
    'nRightarrow': u'\u21cf',                     #RIGHTWARDS DOUBLE ARROW WITH STROKE
    'nrightarrow': u'\u219b',                     #RIGHTWARDS ARROW WITH STROKE
    'nrtri': u'\u22eb',                           #DOES NOT CONTAIN AS NORMAL SUBGROUP
    'nrtrie': u'\u22ed',                          #DOES NOT CONTAIN AS NORMAL SUBGROUP OR EQUAL
    'nsc': u'\u2281',                             #DOES NOT SUCCEED
    'nsccue': u'\u22e1',                          #DOES NOT SUCCEED OR EQUAL
    'nsce': u'\u2ab0\u0338',                      #SUCCEEDS ABOVE SINGLE-LINE EQUALS SIGN with slash
    'Nscr': u'\U0001d4a9',                        #MATHEMATICAL SCRIPT CAPITAL N
    'nscr': u'\U0001d4c3',                        #MATHEMATICAL SCRIPT SMALL N
    'nshortmid': u'\u2224',                       #DOES NOT DIVIDE
    'nshortparallel': u'\u2226',                  #NOT PARALLEL TO
    'nsim': u'\u2241',                            #NOT TILDE
    'nsime': u'\u2244',                           #NOT ASYMPTOTICALLY EQUAL TO
    'nsimeq': u'\u2244',                          #NOT ASYMPTOTICALLY EQUAL TO
    'nsmid': u'\u2224',                           #DOES NOT DIVIDE
    'nspar': u'\u2226',                           #NOT PARALLEL TO
    'nsqsube': u'\u22e2',                         #NOT SQUARE IMAGE OF OR EQUAL TO
    'nsqsupe': u'\u22e3',                         #NOT SQUARE ORIGINAL OF OR EQUAL TO
    'nsub': u'\u2284',                            #NOT A SUBSET OF
    'nsubE': u'\u2ac5\u0338',                     #SUBSET OF ABOVE EQUALS SIGN with slash
    'nsube': u'\u2288',                           #NEITHER A SUBSET OF NOR EQUAL TO
    'nsubset': u'\u2282\u20d2',                   #SUBSET OF with vertical line
    'nsubseteq': u'\u2288',                       #NEITHER A SUBSET OF NOR EQUAL TO
    'nsubseteqq': u'\u2ac5\u0338',                #SUBSET OF ABOVE EQUALS SIGN with slash
    'nsucc': u'\u2281',                           #DOES NOT SUCCEED
    'nsucceq': u'\u2ab0\u0338',                   #SUCCEEDS ABOVE SINGLE-LINE EQUALS SIGN with slash
    'nsup': u'\u2285',                            #NOT A SUPERSET OF
    'nsupE': u'\u2ac6\u0338',                     #SUPERSET OF ABOVE EQUALS SIGN with slash
    'nsupe': u'\u2289',                           #NEITHER A SUPERSET OF NOR EQUAL TO
    'nsupset': u'\u2283\u20d2',                   #SUPERSET OF with vertical line
    'nsupseteq': u'\u2289',                       #NEITHER A SUPERSET OF NOR EQUAL TO
    'nsupseteqq': u'\u2ac6\u0338',                #SUPERSET OF ABOVE EQUALS SIGN with slash
    'ntgl': u'\u2279',                            #NEITHER GREATER-THAN NOR LESS-THAN
    'Ntilde': u'\xd1',                            #LATIN CAPITAL LETTER N WITH TILDE
    'ntilde': u'\xf1',                            #LATIN SMALL LETTER N WITH TILDE
    'ntlg': u'\u2278',                            #NEITHER LESS-THAN NOR GREATER-THAN
    'ntriangleleft': u'\u22ea',                   #NOT NORMAL SUBGROUP OF
    'ntrianglelefteq': u'\u22ec',                 #NOT NORMAL SUBGROUP OF OR EQUAL TO
    'ntriangleright': u'\u22eb',                  #DOES NOT CONTAIN AS NORMAL SUBGROUP
    'ntrianglerighteq': u'\u22ed',                #DOES NOT CONTAIN AS NORMAL SUBGROUP OR EQUAL
    'Nu': u'\u039d',                              #GREEK CAPITAL LETTER NU
    'nu': u'\u03bd',                              #GREEK SMALL LETTER NU
    'num': u'#',                                  #NUMBER SIGN
    'numero': u'\u2116',                          #NUMERO SIGN
    'numsp': u'\u2007',                           #FIGURE SPACE
    'nvap': u'\u224d\u20d2',                      #EQUIVALENT TO with vertical line
    'nVDash': u'\u22af',                          #NEGATED DOUBLE VERTICAL BAR DOUBLE RIGHT TURNSTILE
    'nVdash': u'\u22ae',                          #DOES NOT FORCE
    'nvDash': u'\u22ad',                          #NOT TRUE
    'nvdash': u'\u22ac',                          #DOES NOT PROVE
    'nvge': u'\u2265\u20d2',                      #GREATER-THAN OR EQUAL TO with vertical line
    'nvgt': u'>\u20d2',                           #GREATER-THAN SIGN with vertical line
    'nvHarr': u'\u2904',                          #LEFT RIGHT DOUBLE ARROW WITH VERTICAL STROKE
    'nvinfin': u'\u29de',                         #INFINITY NEGATED WITH VERTICAL BAR
    'nvlArr': u'\u2902',                          #LEFTWARDS DOUBLE ARROW WITH VERTICAL STROKE
    'nvle': u'\u2264\u20d2',                      #LESS-THAN OR EQUAL TO with vertical line
    'nvlt': u'\x3c\u20d2',                            #LESS-THAN SIGN with vertical line
    'nvltrie': u'\u22b4\u20d2',                   #NORMAL SUBGROUP OF OR EQUAL TO with vertical line
    'nvrArr': u'\u2903',                          #RIGHTWARDS DOUBLE ARROW WITH VERTICAL STROKE
    'nvrtrie': u'\u22b5\u20d2',                   #CONTAINS AS NORMAL SUBGROUP OR EQUAL TO with vertical line
    'nvsim': u'\u223c\u20d2',                     #TILDE OPERATOR with vertical line
    'nwarhk': u'\u2923',                          #NORTH WEST ARROW WITH HOOK
    'nwArr': u'\u21d6',                           #NORTH WEST DOUBLE ARROW
    'nwarr': u'\u2196',                           #NORTH WEST ARROW
    'nwarrow': u'\u2196',                         #NORTH WEST ARROW
    'nwnear': u'\u2927',                          #NORTH WEST ARROW AND NORTH EAST ARROW
    'Oacute': u'\xd3',                            #LATIN CAPITAL LETTER O WITH ACUTE
    'oacute': u'\xf3',                            #LATIN SMALL LETTER O WITH ACUTE
    'oast': u'\u229b',                            #CIRCLED ASTERISK OPERATOR
    'ocir': u'\u229a',                            #CIRCLED RING OPERATOR
    'Ocirc': u'\xd4',                             #LATIN CAPITAL LETTER O WITH CIRCUMFLEX
    'ocirc': u'\xf4',                             #LATIN SMALL LETTER O WITH CIRCUMFLEX
    'Ocy': u'\u041e',                             #CYRILLIC CAPITAL LETTER O
    'ocy': u'\u043e',                             #CYRILLIC SMALL LETTER O
    'odash': u'\u229d',                           #CIRCLED DASH
    'Odblac': u'\u0150',                          #LATIN CAPITAL LETTER O WITH DOUBLE ACUTE
    'odblac': u'\u0151',                          #LATIN SMALL LETTER O WITH DOUBLE ACUTE
    'odiv': u'\u2a38',                            #CIRCLED DIVISION SIGN
    'odot': u'\u2299',                            #CIRCLED DOT OPERATOR
    'odsold': u'\u29bc',                          #CIRCLED ANTICLOCKWISE-ROTATED DIVISION SIGN
    'OElig': u'\u0152',                           #LATIN CAPITAL LIGATURE OE
    'oelig': u'\u0153',                           #LATIN SMALL LIGATURE OE
    'ofcir': u'\u29bf',                           #CIRCLED BULLET
    'Ofr': u'\U0001d512',                         #MATHEMATICAL FRAKTUR CAPITAL O
    'ofr': u'\U0001d52c',                         #MATHEMATICAL FRAKTUR SMALL O
    'ogon': u'\u02db',                            #OGONEK
    'Ograve': u'\xd2',                            #LATIN CAPITAL LETTER O WITH GRAVE
    'ograve': u'\xf2',                            #LATIN SMALL LETTER O WITH GRAVE
    'ogt': u'\u29c1',                             #CIRCLED GREATER-THAN
    'ohbar': u'\u29b5',                           #CIRCLE WITH HORIZONTAL BAR
    'ohm': u'\u03a9',                             #GREEK CAPITAL LETTER OMEGA
    'oint': u'\u222e',                            #CONTOUR INTEGRAL
    'olarr': u'\u21ba',                           #ANTICLOCKWISE OPEN CIRCLE ARROW
    'olcir': u'\u29be',                           #CIRCLED WHITE BULLET
    'olcross': u'\u29bb',                         #CIRCLE WITH SUPERIMPOSED X
    'oline': u'\u203e',                           #OVERLINE
    'olt': u'\u29c0',                             #CIRCLED LESS-THAN
    'Omacr': u'\u014c',                           #LATIN CAPITAL LETTER O WITH MACRON
    'omacr': u'\u014d',                           #LATIN SMALL LETTER O WITH MACRON
    'Omega': u'\u03a9',                           #GREEK CAPITAL LETTER OMEGA
    'omega': u'\u03c9',                           #GREEK SMALL LETTER OMEGA
    'Omicron': u'\u039f',                         #GREEK CAPITAL LETTER OMICRON
    'omicron': u'\u03bf',                         #GREEK SMALL LETTER OMICRON
    'omid': u'\u29b6',                            #CIRCLED VERTICAL BAR
    'ominus': u'\u2296',                          #CIRCLED MINUS
    'Oopf': u'\U0001d546',                        #MATHEMATICAL DOUBLE-STRUCK CAPITAL O
    'oopf': u'\U0001d560',                        #MATHEMATICAL DOUBLE-STRUCK SMALL O
    'opar': u'\u29b7',                            #CIRCLED PARALLEL
    'OpenCurlyDoubleQuote': u'\u201c',            #LEFT DOUBLE QUOTATION MARK
    'OpenCurlyQuote': u'\u2018',                  #LEFT SINGLE QUOTATION MARK
    'operp': u'\u29b9',                           #CIRCLED PERPENDICULAR
    'oplus': u'\u2295',                           #CIRCLED PLUS
    'Or': u'\u2a54',                              #DOUBLE LOGICAL OR
    'or': u'\u2228',                              #LOGICAL OR
    'orarr': u'\u21bb',                           #CLOCKWISE OPEN CIRCLE ARROW
    'ord': u'\u2a5d',                             #LOGICAL OR WITH HORIZONTAL DASH
    'order': u'\u2134',                           #SCRIPT SMALL O
    'orderof': u'\u2134',                         #SCRIPT SMALL O
    'ordf': u'\xaa',                              #FEMININE ORDINAL INDICATOR
    'ordm': u'\xba',                              #MASCULINE ORDINAL INDICATOR
    'origof': u'\u22b6',                          #ORIGINAL OF
    'oror': u'\u2a56',                            #TWO INTERSECTING LOGICAL OR
    'orslope': u'\u2a57',                         #SLOPING LARGE OR
    'orv': u'\u2a5b',                             #LOGICAL OR WITH MIDDLE STEM
    'oS': u'\u24c8',                              #CIRCLED LATIN CAPITAL LETTER S
    'Oscr': u'\U0001d4aa',                        #MATHEMATICAL SCRIPT CAPITAL O
    'oscr': u'\u2134',                            #SCRIPT SMALL O
    'Oslash': u'\xd8',                            #LATIN CAPITAL LETTER O WITH STROKE
    'oslash': u'\xf8',                            #LATIN SMALL LETTER O WITH STROKE
    'osol': u'\u2298',                            #CIRCLED DIVISION SLASH
    'Otilde': u'\xd5',                            #LATIN CAPITAL LETTER O WITH TILDE
    'otilde': u'\xf5',                            #LATIN SMALL LETTER O WITH TILDE
    'Otimes': u'\u2a37',                          #MULTIPLICATION SIGN IN DOUBLE CIRCLE
    'otimes': u'\u2297',                          #CIRCLED TIMES
    'otimesas': u'\u2a36',                        #CIRCLED MULTIPLICATION SIGN WITH CIRCUMFLEX ACCENT
    'Ouml': u'\xd6',                              #LATIN CAPITAL LETTER O WITH DIAERESIS
    'ouml': u'\xf6',                              #LATIN SMALL LETTER O WITH DIAERESIS
    'ovbar': u'\u233d',                           #APL FUNCTIONAL SYMBOL CIRCLE STILE
    'OverBar': u'\u203e',                         #OVERLINE
    'OverBrace': u'\u23de',                       #TOP CURLY BRACKET
    'OverBracket': u'\u23b4',                     #TOP SQUARE BRACKET
    'OverParenthesis': u'\u23dc',                 #TOP PARENTHESIS
    'par': u'\u2225',                             #PARALLEL TO
    'para': u'\xb6',                              #PILCROW SIGN
    'parallel': u'\u2225',                        #PARALLEL TO
    'parsim': u'\u2af3',                          #PARALLEL WITH TILDE OPERATOR
    'parsl': u'\u2afd',                           #DOUBLE SOLIDUS OPERATOR
    'part': u'\u2202',                            #PARTIAL DIFFERENTIAL
    'PartialD': u'\u2202',                        #PARTIAL DIFFERENTIAL
    'Pcy': u'\u041f',                             #CYRILLIC CAPITAL LETTER PE
    'pcy': u'\u043f',                             #CYRILLIC SMALL LETTER PE
    'percnt': u'%',                               #PERCENT SIGN
    'period': u'.',                               #FULL STOP
    'permil': u'\u2030',                          #PER MILLE SIGN
    'perp': u'\u22a5',                            #UP TACK
    'pertenk': u'\u2031',                         #PER TEN THOUSAND SIGN
    'Pfr': u'\U0001d513',                         #MATHEMATICAL FRAKTUR CAPITAL P
    'pfr': u'\U0001d52d',                         #MATHEMATICAL FRAKTUR SMALL P
    'Phi': u'\u03a6',                             #GREEK CAPITAL LETTER PHI
    'phi': u'\u03c6',                             #GREEK SMALL LETTER PHI
    'phiv': u'\u03d5',                            #GREEK PHI SYMBOL
    'phmmat': u'\u2133',                          #SCRIPT CAPITAL M
    'phone': u'\u260e',                           #BLACK TELEPHONE
    'Pi': u'\u03a0',                              #GREEK CAPITAL LETTER PI
    'pi': u'\u03c0',                              #GREEK SMALL LETTER PI
    'pitchfork': u'\u22d4',                       #PITCHFORK
    'piv': u'\u03d6',                             #GREEK PI SYMBOL
    'planck': u'\u210f',                          #PLANCK CONSTANT OVER TWO PI
    'planckh': u'\u210e',                         #PLANCK CONSTANT
    'plankv': u'\u210f',                          #PLANCK CONSTANT OVER TWO PI
    'plus': u'+',                                 #PLUS SIGN
    'plusacir': u'\u2a23',                        #PLUS SIGN WITH CIRCUMFLEX ACCENT ABOVE
    'plusb': u'\u229e',                           #SQUARED PLUS
    'pluscir': u'\u2a22',                         #PLUS SIGN WITH SMALL CIRCLE ABOVE
    'plusdo': u'\u2214',                          #DOT PLUS
    'plusdu': u'\u2a25',                          #PLUS SIGN WITH DOT BELOW
    'pluse': u'\u2a72',                           #PLUS SIGN ABOVE EQUALS SIGN
    'PlusMinus': u'\xb1',                         #PLUS-MINUS SIGN
    'plusmn': u'\xb1',                            #PLUS-MINUS SIGN
    'plussim': u'\u2a26',                         #PLUS SIGN WITH TILDE BELOW
    'plustwo': u'\u2a27',                         #PLUS SIGN WITH SUBSCRIPT TWO
    'pm': u'\xb1',                                #PLUS-MINUS SIGN
    'Poincareplane': u'\u210c',                   #BLACK-LETTER CAPITAL H
    'pointint': u'\u2a15',                        #INTEGRAL AROUND A POINT OPERATOR
    'Popf': u'\u2119',                            #DOUBLE-STRUCK CAPITAL P
    'popf': u'\U0001d561',                        #MATHEMATICAL DOUBLE-STRUCK SMALL P
    'pound': u'\xa3',                             #POUND SIGN
    'Pr': u'\u2abb',                              #DOUBLE PRECEDES
    'pr': u'\u227a',                              #PRECEDES
    'prap': u'\u2ab7',                            #PRECEDES ABOVE ALMOST EQUAL TO
    'prcue': u'\u227c',                           #PRECEDES OR EQUAL TO
    'prE': u'\u2ab3',                             #PRECEDES ABOVE EQUALS SIGN
    'pre': u'\u2aaf',                             #PRECEDES ABOVE SINGLE-LINE EQUALS SIGN
    'prec': u'\u227a',                            #PRECEDES
    'precapprox': u'\u2ab7',                      #PRECEDES ABOVE ALMOST EQUAL TO
    'preccurlyeq': u'\u227c',                     #PRECEDES OR EQUAL TO
    'Precedes': u'\u227a',                        #PRECEDES
    'PrecedesEqual': u'\u2aaf',                   #PRECEDES ABOVE SINGLE-LINE EQUALS SIGN
    'PrecedesSlantEqual': u'\u227c',              #PRECEDES OR EQUAL TO
    'PrecedesTilde': u'\u227e',                   #PRECEDES OR EQUIVALENT TO
    'preceq': u'\u2aaf',                          #PRECEDES ABOVE SINGLE-LINE EQUALS SIGN
    'precnapprox': u'\u2ab9',                     #PRECEDES ABOVE NOT ALMOST EQUAL TO
    'precneqq': u'\u2ab5',                        #PRECEDES ABOVE NOT EQUAL TO
    'precnsim': u'\u22e8',                        #PRECEDES BUT NOT EQUIVALENT TO
    'precsim': u'\u227e',                         #PRECEDES OR EQUIVALENT TO
    'Prime': u'\u2033',                           #DOUBLE PRIME
    'prime': u'\u2032',                           #PRIME
    'primes': u'\u2119',                          #DOUBLE-STRUCK CAPITAL P
    'prnap': u'\u2ab9',                           #PRECEDES ABOVE NOT ALMOST EQUAL TO
    'prnE': u'\u2ab5',                            #PRECEDES ABOVE NOT EQUAL TO
    'prnsim': u'\u22e8',                          #PRECEDES BUT NOT EQUIVALENT TO
    'prod': u'\u220f',                            #N-ARY PRODUCT
    'Product': u'\u220f',                         #N-ARY PRODUCT
    'profalar': u'\u232e',                        #ALL AROUND-PROFILE
    'profline': u'\u2312',                        #ARC
    'profsurf': u'\u2313',                        #SEGMENT
    'prop': u'\u221d',                            #PROPORTIONAL TO
    'Proportion': u'\u2237',                      #PROPORTION
    'Proportional': u'\u221d',                    #PROPORTIONAL TO
    'propto': u'\u221d',                          #PROPORTIONAL TO
    'prsim': u'\u227e',                           #PRECEDES OR EQUIVALENT TO
    'prurel': u'\u22b0',                          #PRECEDES UNDER RELATION
    'Pscr': u'\U0001d4ab',                        #MATHEMATICAL SCRIPT CAPITAL P
    'pscr': u'\U0001d4c5',                        #MATHEMATICAL SCRIPT SMALL P
    'Psi': u'\u03a8',                             #GREEK CAPITAL LETTER PSI
    'psi': u'\u03c8',                             #GREEK SMALL LETTER PSI
    'puncsp': u'\u2008',                          #PUNCTUATION SPACE
    'Qfr': u'\U0001d514',                         #MATHEMATICAL FRAKTUR CAPITAL Q
    'qfr': u'\U0001d52e',                         #MATHEMATICAL FRAKTUR SMALL Q
    'qint': u'\u2a0c',                            #QUADRUPLE INTEGRAL OPERATOR
    'Qopf': u'\u211a',                            #DOUBLE-STRUCK CAPITAL Q
    'qopf': u'\U0001d562',                        #MATHEMATICAL DOUBLE-STRUCK SMALL Q
    'qprime': u'\u2057',                          #QUADRUPLE PRIME
    'Qscr': u'\U0001d4ac',                        #MATHEMATICAL SCRIPT CAPITAL Q
    'qscr': u'\U0001d4c6',                        #MATHEMATICAL SCRIPT SMALL Q
    'quaternions': u'\u210d',                     #DOUBLE-STRUCK CAPITAL H
    'quatint': u'\u2a16',                         #QUATERNION INTEGRAL OPERATOR
    'quest': u'?',                                #QUESTION MARK
    'questeq': u'\u225f',                         #QUESTIONED EQUAL TO
    'QUOT': u'"',                                 #QUOTATION MARK
    'quot': u'"',                                 #QUOTATION MARK
    'rAarr': u'\u21db',                           #RIGHTWARDS TRIPLE ARROW
    'race': u'\u223d\u0331',                      #REVERSED TILDE with underline
    'Racute': u'\u0154',                          #LATIN CAPITAL LETTER R WITH ACUTE
    'racute': u'\u0155',                          #LATIN SMALL LETTER R WITH ACUTE
    'radic': u'\u221a',                           #SQUARE ROOT
    'raemptyv': u'\u29b3',                        #EMPTY SET WITH RIGHT ARROW ABOVE
    'Rang': u'\u27eb',                            #MATHEMATICAL RIGHT DOUBLE ANGLE BRACKET
    'rang': u'\u27e9',                            #MATHEMATICAL RIGHT ANGLE BRACKET
    'rangd': u'\u2992',                           #RIGHT ANGLE BRACKET WITH DOT
    'range': u'\u29a5',                           #REVERSED ANGLE WITH UNDERBAR
    'rangle': u'\u27e9',                          #MATHEMATICAL RIGHT ANGLE BRACKET
    'raquo': u'\xbb',                             #RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK
    'Rarr': u'\u21a0',                            #RIGHTWARDS TWO HEADED ARROW
    'rArr': u'\u21d2',                            #RIGHTWARDS DOUBLE ARROW
    'rarr': u'\u2192',                            #RIGHTWARDS ARROW
    'rarrap': u'\u2975',                          #RIGHTWARDS ARROW ABOVE ALMOST EQUAL TO
    'rarrb': u'\u21e5',                           #RIGHTWARDS ARROW TO BAR
    'rarrbfs': u'\u2920',                         #RIGHTWARDS ARROW FROM BAR TO BLACK DIAMOND
    'rarrc': u'\u2933',                           #WAVE ARROW POINTING DIRECTLY RIGHT
    'rarrfs': u'\u291e',                          #RIGHTWARDS ARROW TO BLACK DIAMOND
    'rarrhk': u'\u21aa',                          #RIGHTWARDS ARROW WITH HOOK
    'rarrlp': u'\u21ac',                          #RIGHTWARDS ARROW WITH LOOP
    'rarrpl': u'\u2945',                          #RIGHTWARDS ARROW WITH PLUS BELOW
    'rarrsim': u'\u2974',                         #RIGHTWARDS ARROW ABOVE TILDE OPERATOR
    'Rarrtl': u'\u2916',                          #RIGHTWARDS TWO-HEADED ARROW WITH TAIL
    'rarrtl': u'\u21a3',                          #RIGHTWARDS ARROW WITH TAIL
    'rarrw': u'\u219d',                           #RIGHTWARDS WAVE ARROW
    'rAtail': u'\u291c',                          #RIGHTWARDS DOUBLE ARROW-TAIL
    'ratail': u'\u291a',                          #RIGHTWARDS ARROW-TAIL
    'ratio': u'\u2236',                           #RATIO
    'rationals': u'\u211a',                       #DOUBLE-STRUCK CAPITAL Q
    'RBarr': u'\u2910',                           #RIGHTWARDS TWO-HEADED TRIPLE DASH ARROW
    'rBarr': u'\u290f',                           #RIGHTWARDS TRIPLE DASH ARROW
    'rbarr': u'\u290d',                           #RIGHTWARDS DOUBLE DASH ARROW
    'rbbrk': u'\u2773',                           #LIGHT RIGHT TORTOISE SHELL BRACKET ORNAMENT
    'rbrace': u'}',                               #RIGHT CURLY BRACKET
    'rbrack': u']',                               #RIGHT SQUARE BRACKET
    'rbrke': u'\u298c',                           #RIGHT SQUARE BRACKET WITH UNDERBAR
    'rbrksld': u'\u298e',                         #RIGHT SQUARE BRACKET WITH TICK IN BOTTOM CORNER
    'rbrkslu': u'\u2990',                         #RIGHT SQUARE BRACKET WITH TICK IN TOP CORNER
    'Rcaron': u'\u0158',                          #LATIN CAPITAL LETTER R WITH CARON
    'rcaron': u'\u0159',                          #LATIN SMALL LETTER R WITH CARON
    'Rcedil': u'\u0156',                          #LATIN CAPITAL LETTER R WITH CEDILLA
    'rcedil': u'\u0157',                          #LATIN SMALL LETTER R WITH CEDILLA
    'rceil': u'\u2309',                           #RIGHT CEILING
    'rcub': u'}',                                 #RIGHT CURLY BRACKET
    'Rcy': u'\u0420',                             #CYRILLIC CAPITAL LETTER ER
    'rcy': u'\u0440',                             #CYRILLIC SMALL LETTER ER
    'rdca': u'\u2937',                            #ARROW POINTING DOWNWARDS THEN CURVING RIGHTWARDS
    'rdldhar': u'\u2969',                         #RIGHTWARDS HARPOON WITH BARB DOWN ABOVE LEFTWARDS HARPOON WITH BARB DOWN
    'rdquo': u'\u201d',                           #RIGHT DOUBLE QUOTATION MARK
    'rdquor': u'\u201d',                          #RIGHT DOUBLE QUOTATION MARK
    'rdsh': u'\u21b3',                            #DOWNWARDS ARROW WITH TIP RIGHTWARDS
    'Re': u'\u211c',                              #BLACK-LETTER CAPITAL R
    'real': u'\u211c',                            #BLACK-LETTER CAPITAL R
    'realine': u'\u211b',                         #SCRIPT CAPITAL R
    'realpart': u'\u211c',                        #BLACK-LETTER CAPITAL R
    'reals': u'\u211d',                           #DOUBLE-STRUCK CAPITAL R
    'rect': u'\u25ad',                            #WHITE RECTANGLE
    'REG': u'\xae',                               #REGISTERED SIGN
    'reg': u'\xae',                               #REGISTERED SIGN
    'ReverseElement': u'\u220b',                  #CONTAINS AS MEMBER
    'ReverseEquilibrium': u'\u21cb',              #LEFTWARDS HARPOON OVER RIGHTWARDS HARPOON
    'ReverseUpEquilibrium': u'\u296f',            #DOWNWARDS HARPOON WITH BARB LEFT BESIDE UPWARDS HARPOON WITH BARB RIGHT
    'rfisht': u'\u297d',                          #RIGHT FISH TAIL
    'rfloor': u'\u230b',                          #RIGHT FLOOR
    'Rfr': u'\u211c',                             #BLACK-LETTER CAPITAL R
    'rfr': u'\U0001d52f',                         #MATHEMATICAL FRAKTUR SMALL R
    'rHar': u'\u2964',                            #RIGHTWARDS HARPOON WITH BARB UP ABOVE RIGHTWARDS HARPOON WITH BARB DOWN
    'rhard': u'\u21c1',                           #RIGHTWARDS HARPOON WITH BARB DOWNWARDS
    'rharu': u'\u21c0',                           #RIGHTWARDS HARPOON WITH BARB UPWARDS
    'rharul': u'\u296c',                          #RIGHTWARDS HARPOON WITH BARB UP ABOVE LONG DASH
    'Rho': u'\u03a1',                             #GREEK CAPITAL LETTER RHO
    'rho': u'\u03c1',                             #GREEK SMALL LETTER RHO
    'rhov': u'\u03f1',                            #GREEK RHO SYMBOL
    'RightAngleBracket': u'\u27e9',               #MATHEMATICAL RIGHT ANGLE BRACKET
    'RightArrow': u'\u2192',                      #RIGHTWARDS ARROW
    'Rightarrow': u'\u21d2',                      #RIGHTWARDS DOUBLE ARROW
    'rightarrow': u'\u2192',                      #RIGHTWARDS ARROW
    'RightArrowBar': u'\u21e5',                   #RIGHTWARDS ARROW TO BAR
    'RightArrowLeftArrow': u'\u21c4',             #RIGHTWARDS ARROW OVER LEFTWARDS ARROW
    'rightarrowtail': u'\u21a3',                  #RIGHTWARDS ARROW WITH TAIL
    'RightCeiling': u'\u2309',                    #RIGHT CEILING
    'RightDoubleBracket': u'\u27e7',              #MATHEMATICAL RIGHT WHITE SQUARE BRACKET
    'RightDownTeeVector': u'\u295d',              #DOWNWARDS HARPOON WITH BARB RIGHT FROM BAR
    'RightDownVector': u'\u21c2',                 #DOWNWARDS HARPOON WITH BARB RIGHTWARDS
    'RightDownVectorBar': u'\u2955',              #DOWNWARDS HARPOON WITH BARB RIGHT TO BAR
    'RightFloor': u'\u230b',                      #RIGHT FLOOR
    'rightharpoondown': u'\u21c1',                #RIGHTWARDS HARPOON WITH BARB DOWNWARDS
    'rightharpoonup': u'\u21c0',                  #RIGHTWARDS HARPOON WITH BARB UPWARDS
    'rightleftarrows': u'\u21c4',                 #RIGHTWARDS ARROW OVER LEFTWARDS ARROW
    'rightleftharpoons': u'\u21cc',               #RIGHTWARDS HARPOON OVER LEFTWARDS HARPOON
    'rightrightarrows': u'\u21c9',                #RIGHTWARDS PAIRED ARROWS
    'rightsquigarrow': u'\u219d',                 #RIGHTWARDS WAVE ARROW
    'RightTee': u'\u22a2',                        #RIGHT TACK
    'RightTeeArrow': u'\u21a6',                   #RIGHTWARDS ARROW FROM BAR
    'RightTeeVector': u'\u295b',                  #RIGHTWARDS HARPOON WITH BARB UP FROM BAR
    'rightthreetimes': u'\u22cc',                 #RIGHT SEMIDIRECT PRODUCT
    'RightTriangle': u'\u22b3',                   #CONTAINS AS NORMAL SUBGROUP
    'RightTriangleBar': u'\u29d0',                #VERTICAL BAR BESIDE RIGHT TRIANGLE
    'RightTriangleEqual': u'\u22b5',              #CONTAINS AS NORMAL SUBGROUP OR EQUAL TO
    'RightUpDownVector': u'\u294f',               #UP BARB RIGHT DOWN BARB RIGHT HARPOON
    'RightUpTeeVector': u'\u295c',                #UPWARDS HARPOON WITH BARB RIGHT FROM BAR
    'RightUpVector': u'\u21be',                   #UPWARDS HARPOON WITH BARB RIGHTWARDS
    'RightUpVectorBar': u'\u2954',                #UPWARDS HARPOON WITH BARB RIGHT TO BAR
    'RightVector': u'\u21c0',                     #RIGHTWARDS HARPOON WITH BARB UPWARDS
    'RightVectorBar': u'\u2953',                  #RIGHTWARDS HARPOON WITH BARB UP TO BAR
    'ring': u'\u02da',                            #RING ABOVE
    'risingdotseq': u'\u2253',                    #IMAGE OF OR APPROXIMATELY EQUAL TO
    'rlarr': u'\u21c4',                           #RIGHTWARDS ARROW OVER LEFTWARDS ARROW
    'rlhar': u'\u21cc',                           #RIGHTWARDS HARPOON OVER LEFTWARDS HARPOON
    'rlm': u'\u200f',                             #RIGHT-TO-LEFT MARK
    'rmoust': u'\u23b1',                          #UPPER RIGHT OR LOWER LEFT CURLY BRACKET SECTION
    'rmoustache': u'\u23b1',                      #UPPER RIGHT OR LOWER LEFT CURLY BRACKET SECTION
    'rnmid': u'\u2aee',                           #DOES NOT DIVIDE WITH REVERSED NEGATION SLASH
    'roang': u'\u27ed',                           #MATHEMATICAL RIGHT WHITE TORTOISE SHELL BRACKET
    'roarr': u'\u21fe',                           #RIGHTWARDS OPEN-HEADED ARROW
    'robrk': u'\u27e7',                           #MATHEMATICAL RIGHT WHITE SQUARE BRACKET
    'ropar': u'\u2986',                           #RIGHT WHITE PARENTHESIS
    'Ropf': u'\u211d',                            #DOUBLE-STRUCK CAPITAL R
    'ropf': u'\U0001d563',                        #MATHEMATICAL DOUBLE-STRUCK SMALL R
    'roplus': u'\u2a2e',                          #PLUS SIGN IN RIGHT HALF CIRCLE
    'rotimes': u'\u2a35',                         #MULTIPLICATION SIGN IN RIGHT HALF CIRCLE
    'RoundImplies': u'\u2970',                    #RIGHT DOUBLE ARROW WITH ROUNDED HEAD
    'rpar': u')',                                 #RIGHT PARENTHESIS
    'rpargt': u'\u2994',                          #RIGHT ARC GREATER-THAN BRACKET
    'rppolint': u'\u2a12',                        #LINE INTEGRATION WITH RECTANGULAR PATH AROUND POLE
    'rrarr': u'\u21c9',                           #RIGHTWARDS PAIRED ARROWS
    'Rrightarrow': u'\u21db',                     #RIGHTWARDS TRIPLE ARROW
    'rsaquo': u'\u203a',                          #SINGLE RIGHT-POINTING ANGLE QUOTATION MARK
    'Rscr': u'\u211b',                            #SCRIPT CAPITAL R
    'rscr': u'\U0001d4c7',                        #MATHEMATICAL SCRIPT SMALL R
    'Rsh': u'\u21b1',                             #UPWARDS ARROW WITH TIP RIGHTWARDS
    'rsh': u'\u21b1',                             #UPWARDS ARROW WITH TIP RIGHTWARDS
    'rsqb': u']',                                 #RIGHT SQUARE BRACKET
    'rsquo': u'\u2019',                           #RIGHT SINGLE QUOTATION MARK
    'rsquor': u'\u2019',                          #RIGHT SINGLE QUOTATION MARK
    'rthree': u'\u22cc',                          #RIGHT SEMIDIRECT PRODUCT
    'rtimes': u'\u22ca',                          #RIGHT NORMAL FACTOR SEMIDIRECT PRODUCT
    'rtri': u'\u25b9',                            #WHITE RIGHT-POINTING SMALL TRIANGLE
    'rtrie': u'\u22b5',                           #CONTAINS AS NORMAL SUBGROUP OR EQUAL TO
    'rtrif': u'\u25b8',                           #BLACK RIGHT-POINTING SMALL TRIANGLE
    'rtriltri': u'\u29ce',                        #RIGHT TRIANGLE ABOVE LEFT TRIANGLE
    'RuleDelayed': u'\u29f4',                     #RULE-DELAYED
    'ruluhar': u'\u2968',                         #RIGHTWARDS HARPOON WITH BARB UP ABOVE LEFTWARDS HARPOON WITH BARB UP
    'rx': u'\u211e',                              #PRESCRIPTION TAKE
    'Sacute': u'\u015a',                          #LATIN CAPITAL LETTER S WITH ACUTE
    'sacute': u'\u015b',                          #LATIN SMALL LETTER S WITH ACUTE
    'sbquo': u'\u201a',                           #SINGLE LOW-9 QUOTATION MARK
    'Sc': u'\u2abc',                              #DOUBLE SUCCEEDS
    'sc': u'\u227b',                              #SUCCEEDS
    'scap': u'\u2ab8',                            #SUCCEEDS ABOVE ALMOST EQUAL TO
    'Scaron': u'\u0160',                          #LATIN CAPITAL LETTER S WITH CARON
    'scaron': u'\u0161',                          #LATIN SMALL LETTER S WITH CARON
    'sccue': u'\u227d',                           #SUCCEEDS OR EQUAL TO
    'scE': u'\u2ab4',                             #SUCCEEDS ABOVE EQUALS SIGN
    'sce': u'\u2ab0',                             #SUCCEEDS ABOVE SINGLE-LINE EQUALS SIGN
    'Scedil': u'\u015e',                          #LATIN CAPITAL LETTER S WITH CEDILLA
    'scedil': u'\u015f',                          #LATIN SMALL LETTER S WITH CEDILLA
    'Scirc': u'\u015c',                           #LATIN CAPITAL LETTER S WITH CIRCUMFLEX
    'scirc': u'\u015d',                           #LATIN SMALL LETTER S WITH CIRCUMFLEX
    'scnap': u'\u2aba',                           #SUCCEEDS ABOVE NOT ALMOST EQUAL TO
    'scnE': u'\u2ab6',                            #SUCCEEDS ABOVE NOT EQUAL TO
    'scnsim': u'\u22e9',                          #SUCCEEDS BUT NOT EQUIVALENT TO
    'scpolint': u'\u2a13',                        #LINE INTEGRATION WITH SEMICIRCULAR PATH AROUND POLE
    'scsim': u'\u227f',                           #SUCCEEDS OR EQUIVALENT TO
    'Scy': u'\u0421',                             #CYRILLIC CAPITAL LETTER ES
    'scy': u'\u0441',                             #CYRILLIC SMALL LETTER ES
    'sdot': u'\u22c5',                            #DOT OPERATOR
    'sdotb': u'\u22a1',                           #SQUARED DOT OPERATOR
    'sdote': u'\u2a66',                           #EQUALS SIGN WITH DOT BELOW
    'searhk': u'\u2925',                          #SOUTH EAST ARROW WITH HOOK
    'seArr': u'\u21d8',                           #SOUTH EAST DOUBLE ARROW
    'searr': u'\u2198',                           #SOUTH EAST ARROW
    'searrow': u'\u2198',                         #SOUTH EAST ARROW
    'sect': u'\xa7',                              #SECTION SIGN
    'semi': u';',                                 #SEMICOLON
    'seswar': u'\u2929',                          #SOUTH EAST ARROW AND SOUTH WEST ARROW
    'setminus': u'\u2216',                        #SET MINUS
    'setmn': u'\u2216',                           #SET MINUS
    'sext': u'\u2736',                            #SIX POINTED BLACK STAR
    'Sfr': u'\U0001d516',                         #MATHEMATICAL FRAKTUR CAPITAL S
    'sfr': u'\U0001d530',                         #MATHEMATICAL FRAKTUR SMALL S
    'sfrown': u'\u2322',                          #FROWN
    'sharp': u'\u266f',                           #MUSIC SHARP SIGN
    'SHCHcy': u'\u0429',                          #CYRILLIC CAPITAL LETTER SHCHA
    'shchcy': u'\u0449',                          #CYRILLIC SMALL LETTER SHCHA
    'SHcy': u'\u0428',                            #CYRILLIC CAPITAL LETTER SHA
    'shcy': u'\u0448',                            #CYRILLIC SMALL LETTER SHA
    'ShortDownArrow': u'\u2193',                  #DOWNWARDS ARROW
    'ShortLeftArrow': u'\u2190',                  #LEFTWARDS ARROW
    'shortmid': u'\u2223',                        #DIVIDES
    'shortparallel': u'\u2225',                   #PARALLEL TO
    'ShortRightArrow': u'\u2192',                 #RIGHTWARDS ARROW
    'ShortUpArrow': u'\u2191',                    #UPWARDS ARROW
    'shy': u'\xad',                               #SOFT HYPHEN
    'Sigma': u'\u03a3',                           #GREEK CAPITAL LETTER SIGMA
    'sigma': u'\u03c3',                           #GREEK SMALL LETTER SIGMA
    'sigmaf': u'\u03c2',                          #GREEK SMALL LETTER FINAL SIGMA
    'sigmav': u'\u03c2',                          #GREEK SMALL LETTER FINAL SIGMA
    'sim': u'\u223c',                             #TILDE OPERATOR
    'simdot': u'\u2a6a',                          #TILDE OPERATOR WITH DOT ABOVE
    'sime': u'\u2243',                            #ASYMPTOTICALLY EQUAL TO
    'simeq': u'\u2243',                           #ASYMPTOTICALLY EQUAL TO
    'simg': u'\u2a9e',                            #SIMILAR OR GREATER-THAN
    'simgE': u'\u2aa0',                           #SIMILAR ABOVE GREATER-THAN ABOVE EQUALS SIGN
    'siml': u'\u2a9d',                            #SIMILAR OR LESS-THAN
    'simlE': u'\u2a9f',                           #SIMILAR ABOVE LESS-THAN ABOVE EQUALS SIGN
    'simne': u'\u2246',                           #APPROXIMATELY BUT NOT ACTUALLY EQUAL TO
    'simplus': u'\u2a24',                         #PLUS SIGN WITH TILDE ABOVE
    'simrarr': u'\u2972',                         #TILDE OPERATOR ABOVE RIGHTWARDS ARROW
    'slarr': u'\u2190',                           #LEFTWARDS ARROW
    'SmallCircle': u'\u2218',                     #RING OPERATOR
    'smallsetminus': u'\u2216',                   #SET MINUS
    'smashp': u'\u2a33',                          #SMASH PRODUCT
    'smeparsl': u'\u29e4',                        #EQUALS SIGN AND SLANTED PARALLEL WITH TILDE ABOVE
    'smid': u'\u2223',                            #DIVIDES
    'smile': u'\u2323',                           #SMILE
    'smt': u'\u2aaa',                             #SMALLER THAN
    'smte': u'\u2aac',                            #SMALLER THAN OR EQUAL TO
    'smtes': u'\u2aac\ufe00',                     #SMALLER THAN OR slanted EQUAL
    'SOFTcy': u'\u042c',                          #CYRILLIC CAPITAL LETTER SOFT SIGN
    'softcy': u'\u044c',                          #CYRILLIC SMALL LETTER SOFT SIGN
    'sol': u'/',                                  #SOLIDUS
    'solb': u'\u29c4',                            #SQUARED RISING DIAGONAL SLASH
    'solbar': u'\u233f',                          #APL FUNCTIONAL SYMBOL SLASH BAR
    'Sopf': u'\U0001d54a',                        #MATHEMATICAL DOUBLE-STRUCK CAPITAL S
    'sopf': u'\U0001d564',                        #MATHEMATICAL DOUBLE-STRUCK SMALL S
    'spades': u'\u2660',                          #BLACK SPADE SUIT
    'spadesuit': u'\u2660',                       #BLACK SPADE SUIT
    'spar': u'\u2225',                            #PARALLEL TO
    'sqcap': u'\u2293',                           #SQUARE CAP
    'sqcaps': u'\u2293\ufe00',                    #SQUARE CAP with serifs
    'sqcup': u'\u2294',                           #SQUARE CUP
    'sqcups': u'\u2294\ufe00',                    #SQUARE CUP with serifs
    'Sqrt': u'\u221a',                            #SQUARE ROOT
    'sqsub': u'\u228f',                           #SQUARE IMAGE OF
    'sqsube': u'\u2291',                          #SQUARE IMAGE OF OR EQUAL TO
    'sqsubset': u'\u228f',                        #SQUARE IMAGE OF
    'sqsubseteq': u'\u2291',                      #SQUARE IMAGE OF OR EQUAL TO
    'sqsup': u'\u2290',                           #SQUARE ORIGINAL OF
    'sqsupe': u'\u2292',                          #SQUARE ORIGINAL OF OR EQUAL TO
    'sqsupset': u'\u2290',                        #SQUARE ORIGINAL OF
    'sqsupseteq': u'\u2292',                      #SQUARE ORIGINAL OF OR EQUAL TO
    'squ': u'\u25a1',                             #WHITE SQUARE
    'Square': u'\u25a1',                          #WHITE SQUARE
    'square': u'\u25a1',                          #WHITE SQUARE
    'SquareIntersection': u'\u2293',              #SQUARE CAP
    'SquareSubset': u'\u228f',                    #SQUARE IMAGE OF
    'SquareSubsetEqual': u'\u2291',               #SQUARE IMAGE OF OR EQUAL TO
    'SquareSuperset': u'\u2290',                  #SQUARE ORIGINAL OF
    'SquareSupersetEqual': u'\u2292',             #SQUARE ORIGINAL OF OR EQUAL TO
    'SquareUnion': u'\u2294',                     #SQUARE CUP
    'squarf': u'\u25aa',                          #BLACK SMALL SQUARE
    'squf': u'\u25aa',                            #BLACK SMALL SQUARE
    'srarr': u'\u2192',                           #RIGHTWARDS ARROW
    'Sscr': u'\U0001d4ae',                        #MATHEMATICAL SCRIPT CAPITAL S
    'sscr': u'\U0001d4c8',                        #MATHEMATICAL SCRIPT SMALL S
    'ssetmn': u'\u2216',                          #SET MINUS
    'ssmile': u'\u2323',                          #SMILE
    'sstarf': u'\u22c6',                          #STAR OPERATOR
    'Star': u'\u22c6',                            #STAR OPERATOR
    'star': u'\u2606',                            #WHITE STAR
    'starf': u'\u2605',                           #BLACK STAR
    'straightepsilon': u'\u03f5',                 #GREEK LUNATE EPSILON SYMBOL
    'straightphi': u'\u03d5',                     #GREEK PHI SYMBOL
    'strns': u'\xaf',                             #MACRON
    'Sub': u'\u22d0',                             #DOUBLE SUBSET
    'sub': u'\u2282',                             #SUBSET OF
    'subdot': u'\u2abd',                          #SUBSET WITH DOT
    'subE': u'\u2ac5',                            #SUBSET OF ABOVE EQUALS SIGN
    'sube': u'\u2286',                            #SUBSET OF OR EQUAL TO
    'subedot': u'\u2ac3',                         #SUBSET OF OR EQUAL TO WITH DOT ABOVE
    'submult': u'\u2ac1',                         #SUBSET WITH MULTIPLICATION SIGN BELOW
    'subnE': u'\u2acb',                           #SUBSET OF ABOVE NOT EQUAL TO
    'subne': u'\u228a',                           #SUBSET OF WITH NOT EQUAL TO
    'subplus': u'\u2abf',                         #SUBSET WITH PLUS SIGN BELOW
    'subrarr': u'\u2979',                         #SUBSET ABOVE RIGHTWARDS ARROW
    'Subset': u'\u22d0',                          #DOUBLE SUBSET
    'subset': u'\u2282',                          #SUBSET OF
    'subseteq': u'\u2286',                        #SUBSET OF OR EQUAL TO
    'subseteqq': u'\u2ac5',                       #SUBSET OF ABOVE EQUALS SIGN
    'SubsetEqual': u'\u2286',                     #SUBSET OF OR EQUAL TO
    'subsetneq': u'\u228a',                       #SUBSET OF WITH NOT EQUAL TO
    'subsetneqq': u'\u2acb',                      #SUBSET OF ABOVE NOT EQUAL TO
    'subsim': u'\u2ac7',                          #SUBSET OF ABOVE TILDE OPERATOR
    'subsub': u'\u2ad5',                          #SUBSET ABOVE SUBSET
    'subsup': u'\u2ad3',                          #SUBSET ABOVE SUPERSET
    'succ': u'\u227b',                            #SUCCEEDS
    'succapprox': u'\u2ab8',                      #SUCCEEDS ABOVE ALMOST EQUAL TO
    'succcurlyeq': u'\u227d',                     #SUCCEEDS OR EQUAL TO
    'Succeeds': u'\u227b',                        #SUCCEEDS
    'SucceedsEqual': u'\u2ab0',                   #SUCCEEDS ABOVE SINGLE-LINE EQUALS SIGN
    'SucceedsSlantEqual': u'\u227d',              #SUCCEEDS OR EQUAL TO
    'SucceedsTilde': u'\u227f',                   #SUCCEEDS OR EQUIVALENT TO
    'succeq': u'\u2ab0',                          #SUCCEEDS ABOVE SINGLE-LINE EQUALS SIGN
    'succnapprox': u'\u2aba',                     #SUCCEEDS ABOVE NOT ALMOST EQUAL TO
    'succneqq': u'\u2ab6',                        #SUCCEEDS ABOVE NOT EQUAL TO
    'succnsim': u'\u22e9',                        #SUCCEEDS BUT NOT EQUIVALENT TO
    'succsim': u'\u227f',                         #SUCCEEDS OR EQUIVALENT TO
    'SuchThat': u'\u220b',                        #CONTAINS AS MEMBER
    'Sum': u'\u2211',                             #N-ARY SUMMATION
    'sum': u'\u2211',                             #N-ARY SUMMATION
    'sung': u'\u266a',                            #EIGHTH NOTE
    'Sup': u'\u22d1',                             #DOUBLE SUPERSET
    'sup': u'\u2283',                             #SUPERSET OF
    'sup1': u'\xb9',                              #SUPERSCRIPT ONE
    'sup2': u'\xb2',                              #SUPERSCRIPT TWO
    'sup3': u'\xb3',                              #SUPERSCRIPT THREE
    'supdot': u'\u2abe',                          #SUPERSET WITH DOT
    'supdsub': u'\u2ad8',                         #SUPERSET BESIDE AND JOINED BY DASH WITH SUBSET
    'supE': u'\u2ac6',                            #SUPERSET OF ABOVE EQUALS SIGN
    'supe': u'\u2287',                            #SUPERSET OF OR EQUAL TO
    'supedot': u'\u2ac4',                         #SUPERSET OF OR EQUAL TO WITH DOT ABOVE
    'Superset': u'\u2283',                        #SUPERSET OF
    'SupersetEqual': u'\u2287',                   #SUPERSET OF OR EQUAL TO
    'suphsol': u'\u27c9',                         #SUPERSET PRECEDING SOLIDUS
    'suphsub': u'\u2ad7',                         #SUPERSET BESIDE SUBSET
    'suplarr': u'\u297b',                         #SUPERSET ABOVE LEFTWARDS ARROW
    'supmult': u'\u2ac2',                         #SUPERSET WITH MULTIPLICATION SIGN BELOW
    'supnE': u'\u2acc',                           #SUPERSET OF ABOVE NOT EQUAL TO
    'supne': u'\u228b',                           #SUPERSET OF WITH NOT EQUAL TO
    'supplus': u'\u2ac0',                         #SUPERSET WITH PLUS SIGN BELOW
    'Supset': u'\u22d1',                          #DOUBLE SUPERSET
    'supset': u'\u2283',                          #SUPERSET OF
    'supseteq': u'\u2287',                        #SUPERSET OF OR EQUAL TO
    'supseteqq': u'\u2ac6',                       #SUPERSET OF ABOVE EQUALS SIGN
    'supsetneq': u'\u228b',                       #SUPERSET OF WITH NOT EQUAL TO
    'supsetneqq': u'\u2acc',                      #SUPERSET OF ABOVE NOT EQUAL TO
    'supsim': u'\u2ac8',                          #SUPERSET OF ABOVE TILDE OPERATOR
    'supsub': u'\u2ad4',                          #SUPERSET ABOVE SUBSET
    'supsup': u'\u2ad6',                          #SUPERSET ABOVE SUPERSET
    'swarhk': u'\u2926',                          #SOUTH WEST ARROW WITH HOOK
    'swArr': u'\u21d9',                           #SOUTH WEST DOUBLE ARROW
    'swarr': u'\u2199',                           #SOUTH WEST ARROW
    'swarrow': u'\u2199',                         #SOUTH WEST ARROW
    'swnwar': u'\u292a',                          #SOUTH WEST ARROW AND NORTH WEST ARROW
    'szlig': u'\xdf',                             #LATIN SMALL LETTER SHARP S
    'Tab': u'\t',                                 #CHARACTER TABULATION
    'target': u'\u2316',                          #POSITION INDICATOR
    'Tau': u'\u03a4',                             #GREEK CAPITAL LETTER TAU
    'tau': u'\u03c4',                             #GREEK SMALL LETTER TAU
    'tbrk': u'\u23b4',                            #TOP SQUARE BRACKET
    'Tcaron': u'\u0164',                          #LATIN CAPITAL LETTER T WITH CARON
    'tcaron': u'\u0165',                          #LATIN SMALL LETTER T WITH CARON
    'Tcedil': u'\u0162',                          #LATIN CAPITAL LETTER T WITH CEDILLA
    'tcedil': u'\u0163',                          #LATIN SMALL LETTER T WITH CEDILLA
    'Tcy': u'\u0422',                             #CYRILLIC CAPITAL LETTER TE
    'tcy': u'\u0442',                             #CYRILLIC SMALL LETTER TE
    'telrec': u'\u2315',                          #TELEPHONE RECORDER
    'Tfr': u'\U0001d517',                         #MATHEMATICAL FRAKTUR CAPITAL T
    'tfr': u'\U0001d531',                         #MATHEMATICAL FRAKTUR SMALL T
    'there4': u'\u2234',                          #THEREFORE
    'Therefore': u'\u2234',                       #THEREFORE
    'therefore': u'\u2234',                       #THEREFORE
    'Theta': u'\u0398',                           #GREEK CAPITAL LETTER THETA
    'theta': u'\u03b8',                           #GREEK SMALL LETTER THETA
    'thetasym': u'\u03d1',                        #GREEK THETA SYMBOL
    'thetav': u'\u03d1',                          #GREEK THETA SYMBOL
    'thickapprox': u'\u2248',                     #ALMOST EQUAL TO
    'thicksim': u'\u223c',                        #TILDE OPERATOR
    'ThickSpace': u'\u205f\u200a',                #space of width 5/18 em
    'thinsp': u'\u2009',                          #THIN SPACE
    'ThinSpace': u'\u2009',                       #THIN SPACE
    'thkap': u'\u2248',                           #ALMOST EQUAL TO
    'thksim': u'\u223c',                          #TILDE OPERATOR
    'THORN': u'\xde',                             #LATIN CAPITAL LETTER THORN
    'thorn': u'\xfe',                             #LATIN SMALL LETTER THORN
    'Tilde': u'\u223c',                           #TILDE OPERATOR
    'tilde': u'\u02dc',                           #SMALL TILDE
    'TildeEqual': u'\u2243',                      #ASYMPTOTICALLY EQUAL TO
    'TildeFullEqual': u'\u2245',                  #APPROXIMATELY EQUAL TO
    'TildeTilde': u'\u2248',                      #ALMOST EQUAL TO
    'times': u'\xd7',                             #MULTIPLICATION SIGN
    'timesb': u'\u22a0',                          #SQUARED TIMES
    'timesbar': u'\u2a31',                        #MULTIPLICATION SIGN WITH UNDERBAR
    'timesd': u'\u2a30',                          #MULTIPLICATION SIGN WITH DOT ABOVE
    'tint': u'\u222d',                            #TRIPLE INTEGRAL
    'toea': u'\u2928',                            #NORTH EAST ARROW AND SOUTH EAST ARROW
    'top': u'\u22a4',                             #DOWN TACK
    'topbot': u'\u2336',                          #APL FUNCTIONAL SYMBOL I-BEAM
    'topcir': u'\u2af1',                          #DOWN TACK WITH CIRCLE BELOW
    'Topf': u'\U0001d54b',                        #MATHEMATICAL DOUBLE-STRUCK CAPITAL T
    'topf': u'\U0001d565',                        #MATHEMATICAL DOUBLE-STRUCK SMALL T
    'topfork': u'\u2ada',                         #PITCHFORK WITH TEE TOP
    'tosa': u'\u2929',                            #SOUTH EAST ARROW AND SOUTH WEST ARROW
    'tprime': u'\u2034',                          #TRIPLE PRIME
    'TRADE': u'\u2122',                           #TRADE MARK SIGN
    'trade': u'\u2122',                           #TRADE MARK SIGN
    'triangle': u'\u25b5',                        #WHITE UP-POINTING SMALL TRIANGLE
    'triangledown': u'\u25bf',                    #WHITE DOWN-POINTING SMALL TRIANGLE
    'triangleleft': u'\u25c3',                    #WHITE LEFT-POINTING SMALL TRIANGLE
    'trianglelefteq': u'\u22b4',                  #NORMAL SUBGROUP OF OR EQUAL TO
    'triangleq': u'\u225c',                       #DELTA EQUAL TO
    'triangleright': u'\u25b9',                   #WHITE RIGHT-POINTING SMALL TRIANGLE
    'trianglerighteq': u'\u22b5',                 #CONTAINS AS NORMAL SUBGROUP OR EQUAL TO
    'tridot': u'\u25ec',                          #WHITE UP-POINTING TRIANGLE WITH DOT
    'trie': u'\u225c',                            #DELTA EQUAL TO
    'triminus': u'\u2a3a',                        #MINUS SIGN IN TRIANGLE
    'triplus': u'\u2a39',                         #PLUS SIGN IN TRIANGLE
    'trisb': u'\u29cd',                           #TRIANGLE WITH SERIFS AT BOTTOM
    'tritime': u'\u2a3b',                         #MULTIPLICATION SIGN IN TRIANGLE
    'trpezium': u'\u23e2',                        #WHITE TRAPEZIUM
    'Tscr': u'\U0001d4af',                        #MATHEMATICAL SCRIPT CAPITAL T
    'tscr': u'\U0001d4c9',                        #MATHEMATICAL SCRIPT SMALL T
    'TScy': u'\u0426',                            #CYRILLIC CAPITAL LETTER TSE
    'tscy': u'\u0446',                            #CYRILLIC SMALL LETTER TSE
    'TSHcy': u'\u040b',                           #CYRILLIC CAPITAL LETTER TSHE
    'tshcy': u'\u045b',                           #CYRILLIC SMALL LETTER TSHE
    'Tstrok': u'\u0166',                          #LATIN CAPITAL LETTER T WITH STROKE
    'tstrok': u'\u0167',                          #LATIN SMALL LETTER T WITH STROKE
    'twixt': u'\u226c',                           #BETWEEN
    'twoheadleftarrow': u'\u219e',                #LEFTWARDS TWO HEADED ARROW
    'twoheadrightarrow': u'\u21a0',               #RIGHTWARDS TWO HEADED ARROW
    'Uacute': u'\xda',                            #LATIN CAPITAL LETTER U WITH ACUTE
    'uacute': u'\xfa',                            #LATIN SMALL LETTER U WITH ACUTE
    'Uarr': u'\u219f',                            #UPWARDS TWO HEADED ARROW
    'uArr': u'\u21d1',                            #UPWARDS DOUBLE ARROW
    'uarr': u'\u2191',                            #UPWARDS ARROW
    'Uarrocir': u'\u2949',                        #UPWARDS TWO-HEADED ARROW FROM SMALL CIRCLE
    'Ubrcy': u'\u040e',                           #CYRILLIC CAPITAL LETTER SHORT U
    'ubrcy': u'\u045e',                           #CYRILLIC SMALL LETTER SHORT U
    'Ubreve': u'\u016c',                          #LATIN CAPITAL LETTER U WITH BREVE
    'ubreve': u'\u016d',                          #LATIN SMALL LETTER U WITH BREVE
    'Ucirc': u'\xdb',                             #LATIN CAPITAL LETTER U WITH CIRCUMFLEX
    'ucirc': u'\xfb',                             #LATIN SMALL LETTER U WITH CIRCUMFLEX
    'Ucy': u'\u0423',                             #CYRILLIC CAPITAL LETTER U
    'ucy': u'\u0443',                             #CYRILLIC SMALL LETTER U
    'udarr': u'\u21c5',                           #UPWARDS ARROW LEFTWARDS OF DOWNWARDS ARROW
    'Udblac': u'\u0170',                          #LATIN CAPITAL LETTER U WITH DOUBLE ACUTE
    'udblac': u'\u0171',                          #LATIN SMALL LETTER U WITH DOUBLE ACUTE
    'udhar': u'\u296e',                           #UPWARDS HARPOON WITH BARB LEFT BESIDE DOWNWARDS HARPOON WITH BARB RIGHT
    'ufisht': u'\u297e',                          #UP FISH TAIL
    'Ufr': u'\U0001d518',                         #MATHEMATICAL FRAKTUR CAPITAL U
    'ufr': u'\U0001d532',                         #MATHEMATICAL FRAKTUR SMALL U
    'Ugrave': u'\xd9',                            #LATIN CAPITAL LETTER U WITH GRAVE
    'ugrave': u'\xf9',                            #LATIN SMALL LETTER U WITH GRAVE
    'uHar': u'\u2963',                            #UPWARDS HARPOON WITH BARB LEFT BESIDE UPWARDS HARPOON WITH BARB RIGHT
    'uharl': u'\u21bf',                           #UPWARDS HARPOON WITH BARB LEFTWARDS
    'uharr': u'\u21be',                           #UPWARDS HARPOON WITH BARB RIGHTWARDS
    'uhblk': u'\u2580',                           #UPPER HALF BLOCK
    'ulcorn': u'\u231c',                          #TOP LEFT CORNER
    'ulcorner': u'\u231c',                        #TOP LEFT CORNER
    'ulcrop': u'\u230f',                          #TOP LEFT CROP
    'ultri': u'\u25f8',                           #UPPER LEFT TRIANGLE
    'Umacr': u'\u016a',                           #LATIN CAPITAL LETTER U WITH MACRON
    'umacr': u'\u016b',                           #LATIN SMALL LETTER U WITH MACRON
    'uml': u'\xa8',                               #DIAERESIS
    'UnderBar': u'_',                             #LOW LINE
    'UnderBrace': u'\u23df',                      #BOTTOM CURLY BRACKET
    'UnderBracket': u'\u23b5',                    #BOTTOM SQUARE BRACKET
    'UnderParenthesis': u'\u23dd',                #BOTTOM PARENTHESIS
    'Union': u'\u22c3',                           #N-ARY UNION
    'UnionPlus': u'\u228e',                       #MULTISET UNION
    'Uogon': u'\u0172',                           #LATIN CAPITAL LETTER U WITH OGONEK
    'uogon': u'\u0173',                           #LATIN SMALL LETTER U WITH OGONEK
    'Uopf': u'\U0001d54c',                        #MATHEMATICAL DOUBLE-STRUCK CAPITAL U
    'uopf': u'\U0001d566',                        #MATHEMATICAL DOUBLE-STRUCK SMALL U
    'UpArrow': u'\u2191',                         #UPWARDS ARROW
    'Uparrow': u'\u21d1',                         #UPWARDS DOUBLE ARROW
    'uparrow': u'\u2191',                         #UPWARDS ARROW
    'UpArrowBar': u'\u2912',                      #UPWARDS ARROW TO BAR
    'UpArrowDownArrow': u'\u21c5',                #UPWARDS ARROW LEFTWARDS OF DOWNWARDS ARROW
    'UpDownArrow': u'\u2195',                     #UP DOWN ARROW
    'Updownarrow': u'\u21d5',                     #UP DOWN DOUBLE ARROW
    'updownarrow': u'\u2195',                     #UP DOWN ARROW
    'UpEquilibrium': u'\u296e',                   #UPWARDS HARPOON WITH BARB LEFT BESIDE DOWNWARDS HARPOON WITH BARB RIGHT
    'upharpoonleft': u'\u21bf',                   #UPWARDS HARPOON WITH BARB LEFTWARDS
    'upharpoonright': u'\u21be',                  #UPWARDS HARPOON WITH BARB RIGHTWARDS
    'uplus': u'\u228e',                           #MULTISET UNION
    'UpperLeftArrow': u'\u2196',                  #NORTH WEST ARROW
    'UpperRightArrow': u'\u2197',                 #NORTH EAST ARROW
    'Upsi': u'\u03d2',                            #GREEK UPSILON WITH HOOK SYMBOL
    'upsi': u'\u03c5',                            #GREEK SMALL LETTER UPSILON
    'upsih': u'\u03d2',                           #GREEK UPSILON WITH HOOK SYMBOL
    'Upsilon': u'\u03a5',                         #GREEK CAPITAL LETTER UPSILON
    'upsilon': u'\u03c5',                         #GREEK SMALL LETTER UPSILON
    'UpTee': u'\u22a5',                           #UP TACK
    'UpTeeArrow': u'\u21a5',                      #UPWARDS ARROW FROM BAR
    'upuparrows': u'\u21c8',                      #UPWARDS PAIRED ARROWS
    'urcorn': u'\u231d',                          #TOP RIGHT CORNER
    'urcorner': u'\u231d',                        #TOP RIGHT CORNER
    'urcrop': u'\u230e',                          #TOP RIGHT CROP
    'Uring': u'\u016e',                           #LATIN CAPITAL LETTER U WITH RING ABOVE
    'uring': u'\u016f',                           #LATIN SMALL LETTER U WITH RING ABOVE
    'urtri': u'\u25f9',                           #UPPER RIGHT TRIANGLE
    'Uscr': u'\U0001d4b0',                        #MATHEMATICAL SCRIPT CAPITAL U
    'uscr': u'\U0001d4ca',                        #MATHEMATICAL SCRIPT SMALL U
    'utdot': u'\u22f0',                           #UP RIGHT DIAGONAL ELLIPSIS
    'Utilde': u'\u0168',                          #LATIN CAPITAL LETTER U WITH TILDE
    'utilde': u'\u0169',                          #LATIN SMALL LETTER U WITH TILDE
    'utri': u'\u25b5',                            #WHITE UP-POINTING SMALL TRIANGLE
    'utrif': u'\u25b4',                           #BLACK UP-POINTING SMALL TRIANGLE
    'uuarr': u'\u21c8',                           #UPWARDS PAIRED ARROWS
    'Uuml': u'\xdc',                              #LATIN CAPITAL LETTER U WITH DIAERESIS
    'uuml': u'\xfc',                              #LATIN SMALL LETTER U WITH DIAERESIS
    'uwangle': u'\u29a7',                         #OBLIQUE ANGLE OPENING DOWN
    'vangrt': u'\u299c',                          #RIGHT ANGLE VARIANT WITH SQUARE
    'varepsilon': u'\u03f5',                      #GREEK LUNATE EPSILON SYMBOL
    'varkappa': u'\u03f0',                        #GREEK KAPPA SYMBOL
    'varnothing': u'\u2205',                      #EMPTY SET
    'varphi': u'\u03d5',                          #GREEK PHI SYMBOL
    'varpi': u'\u03d6',                           #GREEK PI SYMBOL
    'varpropto': u'\u221d',                       #PROPORTIONAL TO
    'vArr': u'\u21d5',                            #UP DOWN DOUBLE ARROW
    'varr': u'\u2195',                            #UP DOWN ARROW
    'varrho': u'\u03f1',                          #GREEK RHO SYMBOL
    'varsigma': u'\u03c2',                        #GREEK SMALL LETTER FINAL SIGMA
    'varsubsetneq': u'\u228a\ufe00',              #SUBSET OF WITH NOT EQUAL TO - variant with stroke through bottom members
    'varsubsetneqq': u'\u2acb\ufe00',             #SUBSET OF ABOVE NOT EQUAL TO - variant with stroke through bottom members
    'varsupsetneq': u'\u228b\ufe00',              #SUPERSET OF WITH NOT EQUAL TO - variant with stroke through bottom members
    'varsupsetneqq': u'\u2acc\ufe00',             #SUPERSET OF ABOVE NOT EQUAL TO - variant with stroke through bottom members
    'vartheta': u'\u03d1',                        #GREEK THETA SYMBOL
    'vartriangleleft': u'\u22b2',                 #NORMAL SUBGROUP OF
    'vartriangleright': u'\u22b3',                #CONTAINS AS NORMAL SUBGROUP
    'Vbar': u'\u2aeb',                            #DOUBLE UP TACK
    'vBar': u'\u2ae8',                            #SHORT UP TACK WITH UNDERBAR
    'vBarv': u'\u2ae9',                           #SHORT UP TACK ABOVE SHORT DOWN TACK
    'Vcy': u'\u0412',                             #CYRILLIC CAPITAL LETTER VE
    'vcy': u'\u0432',                             #CYRILLIC SMALL LETTER VE
    'VDash': u'\u22ab',                           #DOUBLE VERTICAL BAR DOUBLE RIGHT TURNSTILE
    'Vdash': u'\u22a9',                           #FORCES
    'vDash': u'\u22a8',                           #TRUE
    'vdash': u'\u22a2',                           #RIGHT TACK
    'Vdashl': u'\u2ae6',                          #LONG DASH FROM LEFT MEMBER OF DOUBLE VERTICAL
    'Vee': u'\u22c1',                             #N-ARY LOGICAL OR
    'vee': u'\u2228',                             #LOGICAL OR
    'veebar': u'\u22bb',                          #XOR
    'veeeq': u'\u225a',                           #EQUIANGULAR TO
    'vellip': u'\u22ee',                          #VERTICAL ELLIPSIS
    'Verbar': u'\u2016',                          #DOUBLE VERTICAL LINE
    'verbar': u'|',                               #VERTICAL LINE
    'Vert': u'\u2016',                            #DOUBLE VERTICAL LINE
    'vert': u'|',                                 #VERTICAL LINE
    'VerticalBar': u'\u2223',                     #DIVIDES
    'VerticalLine': u'|',                         #VERTICAL LINE
    'VerticalSeparator': u'\u2758',               #LIGHT VERTICAL BAR
    'VerticalTilde': u'\u2240',                   #WREATH PRODUCT
    'VeryThinSpace': u'\u200a',                   #HAIR SPACE
    'Vfr': u'\U0001d519',                         #MATHEMATICAL FRAKTUR CAPITAL V
    'vfr': u'\U0001d533',                         #MATHEMATICAL FRAKTUR SMALL V
    'vltri': u'\u22b2',                           #NORMAL SUBGROUP OF
    'vnsub': u'\u2282\u20d2',                     #SUBSET OF with vertical line
    'vnsup': u'\u2283\u20d2',                     #SUPERSET OF with vertical line
    'Vopf': u'\U0001d54d',                        #MATHEMATICAL DOUBLE-STRUCK CAPITAL V
    'vopf': u'\U0001d567',                        #MATHEMATICAL DOUBLE-STRUCK SMALL V
    'vprop': u'\u221d',                           #PROPORTIONAL TO
    'vrtri': u'\u22b3',                           #CONTAINS AS NORMAL SUBGROUP
    'Vscr': u'\U0001d4b1',                        #MATHEMATICAL SCRIPT CAPITAL V
    'vscr': u'\U0001d4cb',                        #MATHEMATICAL SCRIPT SMALL V
    'vsubnE': u'\u2acb\ufe00',                    #SUBSET OF ABOVE NOT EQUAL TO - variant with stroke through bottom members
    'vsubne': u'\u228a\ufe00',                    #SUBSET OF WITH NOT EQUAL TO - variant with stroke through bottom members
    'vsupnE': u'\u2acc\ufe00',                    #SUPERSET OF ABOVE NOT EQUAL TO - variant with stroke through bottom members
    'vsupne': u'\u228b\ufe00',                    #SUPERSET OF WITH NOT EQUAL TO - variant with stroke through bottom members
    'Vvdash': u'\u22aa',                          #TRIPLE VERTICAL BAR RIGHT TURNSTILE
    'vzigzag': u'\u299a',                         #VERTICAL ZIGZAG LINE
    'Wcirc': u'\u0174',                           #LATIN CAPITAL LETTER W WITH CIRCUMFLEX
    'wcirc': u'\u0175',                           #LATIN SMALL LETTER W WITH CIRCUMFLEX
    'wedbar': u'\u2a5f',                          #LOGICAL AND WITH UNDERBAR
    'Wedge': u'\u22c0',                           #N-ARY LOGICAL AND
    'wedge': u'\u2227',                           #LOGICAL AND
    'wedgeq': u'\u2259',                          #ESTIMATES
    'weierp': u'\u2118',                          #SCRIPT CAPITAL P
    'Wfr': u'\U0001d51a',                         #MATHEMATICAL FRAKTUR CAPITAL W
    'wfr': u'\U0001d534',                         #MATHEMATICAL FRAKTUR SMALL W
    'Wopf': u'\U0001d54e',                        #MATHEMATICAL DOUBLE-STRUCK CAPITAL W
    'wopf': u'\U0001d568',                        #MATHEMATICAL DOUBLE-STRUCK SMALL W
    'wp': u'\u2118',                              #SCRIPT CAPITAL P
    'wr': u'\u2240',                              #WREATH PRODUCT
    'wreath': u'\u2240',                          #WREATH PRODUCT
    'Wscr': u'\U0001d4b2',                        #MATHEMATICAL SCRIPT CAPITAL W
    'wscr': u'\U0001d4cc',                        #MATHEMATICAL SCRIPT SMALL W
    'xcap': u'\u22c2',                            #N-ARY INTERSECTION
    'xcirc': u'\u25ef',                           #LARGE CIRCLE
    'xcup': u'\u22c3',                            #N-ARY UNION
    'xdtri': u'\u25bd',                           #WHITE DOWN-POINTING TRIANGLE
    'Xfr': u'\U0001d51b',                         #MATHEMATICAL FRAKTUR CAPITAL X
    'xfr': u'\U0001d535',                         #MATHEMATICAL FRAKTUR SMALL X
    'xhArr': u'\u27fa',                           #LONG LEFT RIGHT DOUBLE ARROW
    'xharr': u'\u27f7',                           #LONG LEFT RIGHT ARROW
    'Xi': u'\u039e',                              #GREEK CAPITAL LETTER XI
    'xi': u'\u03be',                              #GREEK SMALL LETTER XI
    'xlArr': u'\u27f8',                           #LONG LEFTWARDS DOUBLE ARROW
    'xlarr': u'\u27f5',                           #LONG LEFTWARDS ARROW
    'xmap': u'\u27fc',                            #LONG RIGHTWARDS ARROW FROM BAR
    'xnis': u'\u22fb',                            #CONTAINS WITH VERTICAL BAR AT END OF HORIZONTAL STROKE
    'xodot': u'\u2a00',                           #N-ARY CIRCLED DOT OPERATOR
    'Xopf': u'\U0001d54f',                        #MATHEMATICAL DOUBLE-STRUCK CAPITAL X
    'xopf': u'\U0001d569',                        #MATHEMATICAL DOUBLE-STRUCK SMALL X
    'xoplus': u'\u2a01',                          #N-ARY CIRCLED PLUS OPERATOR
    'xotime': u'\u2a02',                          #N-ARY CIRCLED TIMES OPERATOR
    'xrArr': u'\u27f9',                           #LONG RIGHTWARDS DOUBLE ARROW
    'xrarr': u'\u27f6',                           #LONG RIGHTWARDS ARROW
    'Xscr': u'\U0001d4b3',                        #MATHEMATICAL SCRIPT CAPITAL X
    'xscr': u'\U0001d4cd',                        #MATHEMATICAL SCRIPT SMALL X
    'xsqcup': u'\u2a06',                          #N-ARY SQUARE UNION OPERATOR
    'xuplus': u'\u2a04',                          #N-ARY UNION OPERATOR WITH PLUS
    'xutri': u'\u25b3',                           #WHITE UP-POINTING TRIANGLE
    'xvee': u'\u22c1',                            #N-ARY LOGICAL OR
    'xwedge': u'\u22c0',                          #N-ARY LOGICAL AND
    'Yacute': u'\xdd',                            #LATIN CAPITAL LETTER Y WITH ACUTE
    'yacute': u'\xfd',                            #LATIN SMALL LETTER Y WITH ACUTE
    'YAcy': u'\u042f',                            #CYRILLIC CAPITAL LETTER YA
    'yacy': u'\u044f',                            #CYRILLIC SMALL LETTER YA
    'Ycirc': u'\u0176',                           #LATIN CAPITAL LETTER Y WITH CIRCUMFLEX
    'ycirc': u'\u0177',                           #LATIN SMALL LETTER Y WITH CIRCUMFLEX
    'Ycy': u'\u042b',                             #CYRILLIC CAPITAL LETTER YERU
    'ycy': u'\u044b',                             #CYRILLIC SMALL LETTER YERU
    'yen': u'\xa5',                               #YEN SIGN
    'Yfr': u'\U0001d51c',                         #MATHEMATICAL FRAKTUR CAPITAL Y
    'yfr': u'\U0001d536',                         #MATHEMATICAL FRAKTUR SMALL Y
    'YIcy': u'\u0407',                            #CYRILLIC CAPITAL LETTER YI
    'yicy': u'\u0457',                            #CYRILLIC SMALL LETTER YI
    'Yopf': u'\U0001d550',                        #MATHEMATICAL DOUBLE-STRUCK CAPITAL Y
    'yopf': u'\U0001d56a',                        #MATHEMATICAL DOUBLE-STRUCK SMALL Y
    'Yscr': u'\U0001d4b4',                        #MATHEMATICAL SCRIPT CAPITAL Y
    'yscr': u'\U0001d4ce',                        #MATHEMATICAL SCRIPT SMALL Y
    'YUcy': u'\u042e',                            #CYRILLIC CAPITAL LETTER YU
    'yucy': u'\u044e',                            #CYRILLIC SMALL LETTER YU
    'Yuml': u'\u0178',                            #LATIN CAPITAL LETTER Y WITH DIAERESIS
    'yuml': u'\xff',                              #LATIN SMALL LETTER Y WITH DIAERESIS
    'Zacute': u'\u0179',                          #LATIN CAPITAL LETTER Z WITH ACUTE
    'zacute': u'\u017a',                          #LATIN SMALL LETTER Z WITH ACUTE
    'Zcaron': u'\u017d',                          #LATIN CAPITAL LETTER Z WITH CARON
    'zcaron': u'\u017e',                          #LATIN SMALL LETTER Z WITH CARON
    'Zcy': u'\u0417',                             #CYRILLIC CAPITAL LETTER ZE
    'zcy': u'\u0437',                             #CYRILLIC SMALL LETTER ZE
    'Zdot': u'\u017b',                            #LATIN CAPITAL LETTER Z WITH DOT ABOVE
    'zdot': u'\u017c',                            #LATIN SMALL LETTER Z WITH DOT ABOVE
    'zeetrf': u'\u2128',                          #BLACK-LETTER CAPITAL Z
    'ZeroWidthSpace': u'\u200b',                  #ZERO WIDTH SPACE
    'Zeta': u'\u0396',                            #GREEK CAPITAL LETTER ZETA
    'zeta': u'\u03b6',                            #GREEK SMALL LETTER ZETA
    'Zfr': u'\u2128',                             #BLACK-LETTER CAPITAL Z
    'zfr': u'\U0001d537',                         #MATHEMATICAL FRAKTUR SMALL Z
    'ZHcy': u'\u0416',                            #CYRILLIC CAPITAL LETTER ZHE
    'zhcy': u'\u0436',                            #CYRILLIC SMALL LETTER ZHE
    'zigrarr': u'\u21dd',                         #RIGHTWARDS SQUIGGLE ARROW
    'Zopf': u'\u2124',                            #DOUBLE-STRUCK CAPITAL Z
    'zopf': u'\U0001d56b',                        #MATHEMATICAL DOUBLE-STRUCK SMALL Z
    'Zscr': u'\U0001d4b5',                        #MATHEMATICAL SCRIPT CAPITAL Z
    'zscr': u'\U0001d4cf',                        #MATHEMATICAL SCRIPT SMALL Z
    'zwj': u'\u200d',                             #ZERO WIDTH JOINER
    'zwnj': u'\u200c',                            #ZERO WIDTH NON-JOINER
    }

known_entities = dict([(k,chr(v)) for k,v in name2codepoint.items()])
for k in greeks:
    if k not in known_entities:
        known_entities[k] = greeks[k]
#K = list(known_entities.keys())
#for k in K:
#   known_entities[asBytes(k)] = known_entities[k]
#del k, f, K

#------------------------------------------------------------------------
class ParaFrag(ABag):
    """class ParaFrag contains the intermediate representation of string
    segments as they are being parsed by the ParaParser.
    fontname, fontSize, rise, textColor, cbDefn
    """

_greek2Utf8=None
def _greekConvert(data):
    global _greek2Utf8
    if not _greek2Utf8:
        from reportlab.pdfbase.rl_codecs import RL_Codecs
        import codecs
        #our decoding map
        dm = codecs.make_identity_dict(range(32,256))
        for k in range(0,32):
            dm[k] = None
        dm.update(RL_Codecs._RL_Codecs__rl_codecs_data['symbol'][0])
        _greek2Utf8 = {}
        for k,v in dm.items():
            if not v:
                u = '\0'
            else:
                u = chr(v)
            _greek2Utf8[chr(k)] = u
    return ''.join(map(_greek2Utf8.__getitem__,data))

#------------------------------------------------------------------
# !!! NOTE !!! THIS TEXT IS NOW REPLICATED IN PARAGRAPH.PY !!!
# The ParaFormatter will be able to format the following
# tags:
#       < /b > - bold
#       < /i > - italics
#       < u [color="red"] [width="pts"] [offset="pts"]> < /u > - underline
#           width and offset can be empty meaning use existing canvas line width
#           or with an f/F suffix regarded as a fraction of the font size
#       < strike > < /strike > - strike through has the same parameters as underline
#       < super [size="pts"] [rise="pts"]> < /super > - superscript
#       < sup ="pts"] [rise="pts"]> < /sup > - superscript
#       < sub ="pts"] [rise="pts"]> < /sub > - subscript
#       <font name=fontfamily/fontname color=colorname size=float>
#        <span name=fontfamily/fontname color=colorname backcolor=colorname size=float style=stylename>
#       < bullet > </bullet> - bullet text (at head of para only)
#       <onDraw name=callable label="a label"/>
#       <index [name="callablecanvasattribute"] label="a label"/>
#       <link>link text</link>
#           attributes of links
#               size/fontSize/uwidth/uoffset=num
#               name/face/fontName=name
#               fg/textColor/color/ucolor=color
#               backcolor/backColor/bgcolor=color
#               dest/destination/target/href/link=target
#               underline=bool turn on underline
#       <a>anchor text</a>
#           attributes of anchors
#               fontSize=num
#               fontName=name
#               fg/textColor/color=color
#               backcolor/backColor/bgcolor=color
#               href=href
#       <a name="anchorpoint"/>
#       <unichar name="unicode character name"/>
#       <unichar value="unicode code point"/>
#       <img src="path" width="1in" height="1in" valign="bottom"/>
#               width="w%" --> fontSize*w/100   idea from Roberto Alsina
#               height="h%" --> linewidth*h/100 <ralsina@netmanagers.com.ar>
#       <greek> - </greek>
#       <nobr> ... </nobr> turn off word breaking and hyphenation
#
#       The whole may be surrounded by <para> </para> tags
#
# It will also be able to handle any MathML specified Greek characters.
#------------------------------------------------------------------
class ParaParser(HTMLParser):

    #----------------------------------------------------------
    # First we will define all of the xml tag handler functions.
    #
    # start_<tag>(attributes)
    # end_<tag>()
    #
    # While parsing the xml ParaFormatter will call these
    # functions to handle the string formatting tags.
    # At the start of each tag the corresponding field will
    # be set to 1 and at the end tag the corresponding field will
    # be set to 0.  Then when handle_data is called the options
    # for that data will be aparent by the current settings.
    #----------------------------------------------------------

    def __getattr__( self, attrName ):
        """This way we can handle <TAG> the same way as <tag> (ignoring case)."""
        if attrName!=attrName.lower() and attrName!="caseSensitive" and not self.caseSensitive and \
            (attrName.startswith("start_") or attrName.startswith("end_")):
                return getattr(self,attrName.lower())
        raise AttributeError(attrName)

    #### bold
    def start_b( self, attributes ):
        self._push('b',bold=1)

    def end_b( self ):
        self._pop('b')

    def start_strong( self, attributes ):
        self._push('strong',bold=1)

    def end_strong( self ):
        self._pop('strong')

    #### italics
    def start_i( self, attributes ):
        self._push('i',italic=1)

    def end_i( self ):
        self._pop('i')

    def start_em( self, attributes ):
        self._push('em', italic=1)

    def end_em( self ):
        self._pop('em')

    def _new_line(self,k):
        frag = self._stack[-1]
        frag.us_lines = frag.us_lines + [(
                    self.nlines,
                    k,
                    getattr(frag,k+'Color',self._defaultLineColors[k]),
                    getattr(frag,k+'Width',self._defaultLineWidths[k]),
                    getattr(frag,k+'Offset',self._defaultLineOffsets[k]),
                    frag.rise,
                    _lineRepeats[getattr(frag,k+'Kind','single')],
                    getattr(frag,k+'Gap',self._defaultLineGaps[k]),
                    )]
        self.nlines += 1

    #### underline
    def start_u( self, attributes ):
        A = self.getAttributes(attributes,_uAttrMap)
        self._push('u',**A)
        self._new_line('underline')

    def end_u( self ):
        self._pop('u')

    #### strike
    def start_strike( self, attributes ):
        A = self.getAttributes(attributes,_strikeAttrMap)
        self._push('strike',strike=1,**A)
        self._new_line('strike')

    def end_strike( self ):
        self._pop('strike')

    #### link
    def _handle_link(self, tag, attributes):
        A = self.getAttributes(attributes,_linkAttrMap)
        underline = A.pop('underline',self._defaultLinkUnderline)
        A['link'] = self._stack[-1].link + [(
                        self.nlinks,
                        A.pop('link','').strip(),
                        )]
        self.nlinks += 1
        self._push(tag,**A)
        if underline:
            self._new_line('underline')

    def start_link(self,attributes):
        self._handle_link('link',attributes)

    def end_link(self):
        if self._pop('link').link is None:
            raise ValueError('<link> has no target or href')

    #### anchor
    def start_a(self, attributes):
        anchor = 'name' in attributes
        if anchor:
            A = self.getAttributes(attributes,_anchorAttrMap)
            name = A.get('name',None)
            name = name.strip()
            if not name:
                self._syntax_error('<a name="..."/> anchor variant requires non-blank name')
            if len(A)>1:
                self._syntax_error('<a name="..."/> anchor variant only allows name attribute')
                A = dict(name=A['name'])
            A['_selfClosingTag'] = 'anchor'
            self._push('a',**A)
        else:
            self._handle_link('a',attributes)

    def end_a(self):
        frag = self._stack[-1]
        sct = getattr(frag,'_selfClosingTag','')
        if sct:
            if not (sct=='anchor' and frag.name):
                raise ValueError('Parser failure in <a/>')
            defn = frag.cbDefn = ABag()
            defn.label = defn.kind = 'anchor'
            defn.name = frag.name
            del frag.name, frag._selfClosingTag
            self.handle_data('')
            self._pop('a')
        else:
            if self._pop('a').link is None:
                raise ValueError('<link> has no href')

    def start_img(self,attributes):
        A = self.getAttributes(attributes,_imgAttrMap)
        if not A.get('src'):
            self._syntax_error('<img> needs src attribute')
        A['_selfClosingTag'] = 'img'
        self._push('img',**A)

    def end_img(self):
        frag = self._stack[-1]
        if not getattr(frag,'_selfClosingTag',''):
            raise ValueError('Parser failure in <img/>')
        defn = frag.cbDefn = ABag()
        defn.kind = 'img'
        defn.src = getattr(frag,'src',None)
        defn.image = ImageReader(defn.src)
        size = defn.image.getSize()
        defn.width = getattr(frag,'width',size[0])
        defn.height = getattr(frag,'height',size[1])
        defn.valign = getattr(frag,'valign','bottom')
        del frag._selfClosingTag
        self.handle_data('')
        self._pop('img')

    #### super script
    def start_super( self, attributes ):
        A = self.getAttributes(attributes,_supAttrMap)
        #A['sup']=1
        self._push('super',**A)
        frag = self._stack[-1]
        frag.rise += fontSizeNormalize(frag,'supr',frag.fontSize*supFraction)
        frag.fontSize = fontSizeNormalize(frag,'sups',frag.fontSize-min(sizeDelta,0.2*frag.fontSize))

    def end_super( self ):
        self._pop('super')

    start_sup = start_super
    end_sup = end_super

    #### sub script
    def start_sub( self, attributes ):
        A = self.getAttributes(attributes,_supAttrMap)
        self._push('sub',**A)
        frag = self._stack[-1]
        frag.rise -= fontSizeNormalize(frag,'supr',frag.fontSize*subFraction)
        frag.fontSize = fontSizeNormalize(frag,'sups',frag.fontSize-min(sizeDelta,0.2*frag.fontSize))

    def end_sub( self ):
        self._pop('sub')

    def start_nobr(self, attrs):
        self.getAttributes(attrs,{})
        self._push('nobr',nobr=True)

    def end_nobr(self ):
        self._pop('nobr')

    #### greek script
    #### add symbol encoding
    def handle_charref(self, name):
        try:
            if name[0]=='x':
                n = int(name[1:],16)
            else:
                n = int(name)
        except ValueError:
            self.unknown_charref(name)
            return
        self.handle_data(chr(n))   #.encode('utf8'))

    def syntax_error(self,lineno,message):
        self._syntax_error(message)

    def _syntax_error(self,message):
        if message[:10]=="attribute " and message[-17:]==" value not quoted": return
        if self._crashOnError:
            raise ValueError('paraparser: syntax error: %s' % message)
        self.errors.append(message)

    def start_greek(self, attr):
        self._push('greek',greek=1)

    def end_greek(self):
        self._pop('greek')

    def start_unichar(self, attr):
        if 'name' in attr:
            if 'code' in attr:
                self._syntax_error('<unichar/> invalid with both name and code attributes')
            try:
                v = unicodedata.lookup(attr['name'])
            except KeyError:
                self._syntax_error('<unichar/> invalid name attribute\n"%s"' % ascii(attr['name']))
                v = '\0'
        elif 'code' in attr:
            try:
                v = attr['code'].lower()
                if v.startswith('0x'):
                    v = int(v,16)
                else:
                    v = int(v,0)    #treat as a python literal would be
                v = chr(v)
            except:
                self._syntax_error('<unichar/> invalid code attribute %s' % ascii(attr['code']))
                v = '\0'
        else:
            v = None
            if attr:
                self._syntax_error('<unichar/> invalid attribute %s' % list(attr.keys())[0])

        if v is not None:
            self.handle_data(v)
        self._push('unichar',_selfClosingTag='unichar')

    def end_unichar(self):
        self._pop('unichar')

    def start_font(self,attr):
        A = self.getAttributes(attr,_spanAttrMap)
        if 'fontName' in A:
            A['fontName'], A['bold'], A['italic'] = ps2tt(A['fontName'])
        self._push('font',**A)

    def end_font(self):
        self._pop('font')

    def start_span(self,attr):
        A = self.getAttributes(attr,_spanAttrMap)
        if 'style' in A:
            style = self.findSpanStyle(A.pop('style'))
            D = {}
            for k in 'fontName fontSize textColor backColor'.split():
                v = getattr(style,k,self)
                if v is self: continue
                D[k] = v
            D.update(A)
            A = D
        if 'fontName' in A:
            A['fontName'], A['bold'], A['italic'] = ps2tt(A['fontName'])
        self._push('span',**A)

    def end_span(self):
        self._pop('span')

    def start_br(self, attr):
        self._push('br',_selfClosingTag='br',lineBreak=True,text='')

    def end_br(self):
        #print('\nend_br called, %d frags in list' % len(self.fragList))
        frag = self._stack[-1]
        if not (frag._selfClosingTag=='br' and frag.lineBreak):
                raise ValueError('Parser failure in <br/>')
        del frag._selfClosingTag
        self.handle_data('')
        self._pop('br')

    def _initial_frag(self,attr,attrMap,bullet=0):
        style = self._style
        if attr!={}:
            style = copy.deepcopy(style)
            _applyAttributes(style,self.getAttributes(attr,attrMap))
            self._style = style

        # initialize semantic values
        frag = ParaFrag()
        frag.rise = 0
        frag.greek = 0
        frag.link = []
        try:
            if bullet:
                frag.fontName, frag.bold, frag.italic = ps2tt(style.bulletFontName)
                frag.fontSize = style.bulletFontSize
                frag.textColor = hasattr(style,'bulletColor') and style.bulletColor or style.textColor
            else:
                frag.fontName, frag.bold, frag.italic = ps2tt(style.fontName)
                frag.fontSize = style.fontSize
                frag.textColor = style.textColor
        except:
            annotateException('error with style name=%s'%style.name)
        frag.us_lines = []
        self.nlinks = self.nlines = 0
        self._defaultLineWidths = dict(
                                    underline = getattr(style,'underlineWidth',''),
                                    strike = getattr(style,'strikeWidth',''),
                                    )
        self._defaultLineColors = dict(
                                    underline = getattr(style,'underlineColor',''),
                                    strike = getattr(style,'strikeColor',''),
                                    )
        self._defaultLineOffsets = dict(
                                    underline = getattr(style,'underlineOffset',''),
                                    strike = getattr(style,'strikeOffset',''),
                                    )
        self._defaultLineGaps = dict(
                                    underline = getattr(style,'underlineGap',''),
                                    strike = getattr(style,'strikeGap',''),
                                    )
        self._defaultLinkUnderline = getattr(style,'linkUnderline',platypus_link_underline)
        return frag

    def start_para(self,attr):
        frag = self._initial_frag(attr,_paraAttrMap)
        frag.__tag__ = 'para'
        self._stack = [frag]

    def end_para(self):
        self._pop('para')

    def start_bullet(self,attr):
        if hasattr(self,'bFragList'):
            self._syntax_error('only one <bullet> tag allowed')
        self.bFragList = []
        frag = self._initial_frag(attr,_bulletAttrMap,1)
        frag.isBullet = 1
        frag.__tag__ = 'bullet'
        self._stack.append(frag)

    def end_bullet(self):
        self._pop('bullet')

    #---------------------------------------------------------------
    def start_seqdefault(self, attr):
        try:
            default = attr['id']
        except KeyError:
            default = None
        self._seq.setDefaultCounter(default)

    def end_seqdefault(self):
        pass

    def start_seqreset(self, attr):
        try:
            id = attr['id']
        except KeyError:
            id = None
        try:
            base = int(attr['base'])
        except:
            base=0
        self._seq.reset(id, base)

    def end_seqreset(self):
        pass

    def start_seqchain(self, attr):
        try:
            order = attr['order']
        except KeyError:
            order = ''
        order = order.split()
        seq = self._seq
        for p,c in zip(order[:-1],order[1:]):
            seq.chain(p, c)
    end_seqchain = end_seqreset

    def start_seqformat(self, attr):
        try:
            id = attr['id']
        except KeyError:
            id = None
        try:
            value = attr['value']
        except KeyError:
            value = '1'
        self._seq.setFormat(id,value)
    end_seqformat = end_seqreset

    # AR hacking in aliases to allow the proper casing for RML.
    # the above ones should be deprecated over time. 2001-03-22
    start_seqDefault = start_seqdefault
    end_seqDefault = end_seqdefault
    start_seqReset = start_seqreset
    end_seqReset = end_seqreset
    start_seqChain = start_seqchain
    end_seqChain = end_seqchain
    start_seqFormat = start_seqformat
    end_seqFormat = end_seqformat

    def start_seq(self, attr):
        #if it has a template, use that; otherwise try for id;
        #otherwise take default sequence
        if 'template' in attr:
            templ = attr['template']
            self.handle_data(templ % self._seq)
            return
        elif 'id' in attr:
            id = attr['id']
        else:
            id = None
        increment = attr.get('inc', None)
        if not increment:
            output = self._seq.nextf(id)
        else:
            #accepts "no" for do not increment, or an integer.
            #thus, 0 and 1 increment by the right amounts.
            if increment.lower() == 'no':
                output = self._seq.thisf(id)
            else:
                incr = int(increment)
                output = self._seq.thisf(id)
                self._seq.reset(id, self._seq._this() + incr)
        self.handle_data(output)

    def end_seq(self):
        pass

    def start_ondraw(self,attr):
        defn = ABag()
        if 'name' in attr: defn.name = attr['name']
        else: self._syntax_error('<onDraw> needs at least a name attribute')

        defn.label = attr.get('label',None)
        defn.kind='onDraw'
        self._push('ondraw',cbDefn=defn)
        self.handle_data('')
        self._pop('ondraw')
    start_onDraw=start_ondraw
    end_onDraw=end_ondraw=end_seq

    def start_index(self,attr):
        attr=self.getAttributes(attr,_indexAttrMap)
        defn = ABag()
        if 'item' in attr:
            label = attr['item']
        else:
            self._syntax_error('<index> needs at least an item attribute')
        if 'name' in attr:
            name = attr['name']
        else:
            name = DEFAULT_INDEX_NAME
        format = attr.get('format',None)
        if format is not None and format not in ('123','I','i','ABC','abc'):
            raise ValueError('index tag format is %r not valid 123 I i ABC or abc' % offset)
        offset = attr.get('offset',None)
        if offset is not None:
            try:
                offset = int(offset)
            except:
                raise ValueError('index tag offset is %r not an int' % offset)
        defn.label = encode_label((label,format,offset))
        defn.name = name
        defn.kind='index'
        self._push('index',cbDefn=defn)
        self.handle_data('')
        self._pop('index',)
    end_index=end_seq

    def start_unknown(self,attr):
        pass
    end_unknown=end_seq

    #---------------------------------------------------------------
    def _push(self,tag,**attr):
        frag = copy.copy(self._stack[-1])
        frag.__tag__ = tag
        _applyAttributes(frag,attr)
        self._stack.append(frag)

    def _pop(self,tag):
        frag = self._stack.pop()
        if tag==frag.__tag__: return frag
        raise ValueError('Parse error: saw </%s> instead of expected </%s>' % (tag,frag.__tag__))

    def getAttributes(self,attr,attrMap):
        A = {}
        for k, v in attr.items():
            if not self.caseSensitive:
                k = k.lower()
            if k in attrMap:
                j = attrMap[k]
                func = j[1]
                if func is not None:
                    #it's a function
                    v = func(self,v) if isinstance(func,_ExValidate) else func(v)
                A[j[0]] = v
            else:
                self._syntax_error('invalid attribute name %s attrMap=%r'% (k,list(sorted(attrMap.keys()))))
        return A

    #----------------------------------------------------------------

    def __init__(self,verbose=0, caseSensitive=0, ignoreUnknownTags=1, crashOnError=True):
        HTMLParser.__init__(self, **(dict(convert_charrefs=False)))
        self.verbose = verbose
        #HTMLParser is case insenstive anyway, but the rml interface still needs this
        #all start/end_ methods should have a lower case version for HMTMParser
        self.caseSensitive = caseSensitive
        self.ignoreUnknownTags = ignoreUnknownTags
        self._crashOnError = crashOnError

    def _iReset(self):
        self.fragList = []
        if hasattr(self, 'bFragList'): delattr(self,'bFragList')

    def _reset(self, style):
        '''reset the parser'''

        HTMLParser.reset(self)
        # initialize list of string segments to empty
        self.errors = []
        self._style = style
        self._iReset()

    #----------------------------------------------------------------
    def handle_data(self,data):
        "Creates an intermediate representation of string segments."

        #The old parser would only 'see' a string after all entities had
        #been processed.  Thus, 'Hello &trade; World' would emerge as one
        #fragment.    HTMLParser processes these separately.  We want to ensure
        #that successive calls like this are concatenated, to prevent too many
        #fragments being created.

        frag = copy.copy(self._stack[-1])
        if hasattr(frag,'cbDefn'):
            kind = frag.cbDefn.kind
            if data: self._syntax_error('Only empty <%s> tag allowed' % kind)
        elif hasattr(frag,'_selfClosingTag'):
            if data!='': self._syntax_error('No content allowed in %s tag' % frag._selfClosingTag)
            return
        else:
            #get the right parameters for the
            if frag.greek:
                frag.fontName = 'symbol'
                data = _greekConvert(data)

        # bold, italic
        frag.fontName = tt2ps(frag.fontName,frag.bold,frag.italic)

        #save our data
        frag.text = data

        if hasattr(frag,'isBullet'):
            delattr(frag,'isBullet')
            self.bFragList.append(frag)
        else:
            self.fragList.append(frag)

    def handle_cdata(self,data):
        self.handle_data(data)

    def _setup_for_parse(self,style):
        self._seq = reportlab.lib.sequencer.getSequencer()
        self._reset(style)  # reinitialise the parser

    def _complete_parse(self):
        "Reset after parsing, to be ready for next paragraph"
        if self._stack:
            self._syntax_error('parse ended with %d unclosed tags\n %s' % (len(self._stack),'\n '.join((x.__tag__ for x in reversed(self._stack)))))
        del self._seq
        style = self._style
        del self._style
        if len(self.errors)==0:
            fragList = self.fragList
            bFragList = hasattr(self,'bFragList') and self.bFragList or None
            self._iReset()
        else:
            fragList = bFragList = None

        return style, fragList, bFragList

    def _tt_handle(self,tt):
        "Iterate through a pre-parsed tuple tree (e.g. from pyrxp)"
        #import pprint
        #pprint.pprint(tt)
        #find the corresponding start_tagname and end_tagname methods.
        #These must be defined.
        tag = tt[0]
        try:
            start = getattr(self,'start_'+tag)
            end = getattr(self,'end_'+tag)
        except AttributeError:
            if not self.ignoreUnknownTags:
                raise ValueError('Invalid tag "%s"' % tag)
            start = self.start_unknown
            end = self.end_unknown

        #call the start_tagname method
        start(tt[1] or {})
        #if tree node has any children, they will either be further nodes,
        #or text.  Accordingly, call either this function, or handle_data.
        C = tt[2]
        if C:
            M = self._tt_handlers
            for c in C:
                M[isinstance(c,(list,tuple))](c)

        #call the end_tagname method
        end()

    def _tt_start(self,tt):
        self._tt_handlers = self.handle_data,self._tt_handle
        self._tt_handle(tt)

    def tt_parse(self,tt,style):
        '''parse from tupletree form'''
        self._setup_for_parse(style)
        self._tt_start(tt)
        return self._complete_parse()

    def findSpanStyle(self,style):
        raise ValueError('findSpanStyle not implemented in this parser')

    #HTMLParser interface
    def parse(self, text, style):
        "attempt replacement for parse"
        self._setup_for_parse(style)
        text = asUnicode(text)
        if not(len(text)>=6 and text[0]=='<' and _re_para.match(text)):
            text = u"<para>"+text+u"</para>"
        try:
            self.feed(text)
        except:
            annotateException('\nparagraph text %s caused exception' % ascii(text))
        return self._complete_parse()

    def handle_starttag(self, tag, attrs):
        "Called by HTMLParser when a tag starts"

        #tuple tree parser used to expect a dict.  HTML parser
        #gives list of two-element tuples
        if isinstance(attrs, list):
            d = {}
            for (k,  v) in attrs:
                d[k] = v
            attrs = d
        if not self.caseSensitive: tag = tag.lower()
        try:
            start = getattr(self,'start_'+tag)
        except AttributeError:
            if not self.ignoreUnknownTags:
                raise ValueError('Invalid tag "%s"' % tag)
            start = self.start_unknown
        #call it
        start(attrs or {})

    def handle_endtag(self, tag):
        "Called by HTMLParser when a tag ends"
        #find the existing end_tagname method
        if not self.caseSensitive: tag = tag.lower()
        try:
            end = getattr(self,'end_'+tag)
        except AttributeError:
            if not self.ignoreUnknownTags:
                raise ValueError('Invalid tag "%s"' % tag)
            end = self.end_unknown
        #call it
        end()

    def handle_entityref(self, name):
        "Handles a named entity.  "
        try:
            v = known_entities[name]
        except:
            v = u'&%s;' % name
        self.handle_data(v)

if __name__=='__main__':
    from reportlab.platypus import cleanBlockQuotedText
    from reportlab.lib.styles import _baseFontName
    _parser=ParaParser()
    def check_text(text,p=_parser):
        print('##########')
        text = cleanBlockQuotedText(text)
        l,rv,bv = p.parse(text,style)
        if rv is None:
            for l in _parser.errors:
                print(l)
        else:
            print('ParaStyle', l.fontName,l.fontSize,l.textColor)
            for l in rv:
                sys.stdout.write(l.fontName,l.fontSize,l.textColor,l.bold, l.rise, '|%s|'%l.text[:25])
                if hasattr(l,'cbDefn'):
                    print('cbDefn',getattr(l.cbDefn,'name',''),getattr(l.cbDefn,'label',''),l.cbDefn.kind)
                else: print()

    style=ParaFrag()
    style.fontName=_baseFontName
    style.fontSize = 12
    style.textColor = black
    style.bulletFontName = black
    style.bulletFontName=_baseFontName
    style.bulletFontSize=12

    text='''
    <b><i><greek>a</greek>D</i></b>&beta;<unichr value="0x394"/>
    <font name="helvetica" size="15" color=green>
    Tell me, O muse, of that ingenious hero who travelled far and wide
    after</font> he had sacked the famous town of Troy. Many cities did he visit,
    and many were the nations with whose manners and customs he was acquainted;
    moreover he suffered much by sea while trying to save his own life
    and bring his men safely home; but do what he might he could not save
    his men, for they perished through their own sheer folly in eating
    the cattle of the Sun-god Hyperion; so the god prevented them from
    ever reaching home. Tell me, too, about all these things, O daughter
    of Jove, from whatsoever source you<super>1</super> may know them.
    '''
    check_text(text)
    check_text('<para> </para>')
    check_text('<para font="%s" size=24 leading=28.8 spaceAfter=72>ReportLab -- Reporting for the Internet Age</para>'%_baseFontName)
    check_text('''
    <font color=red>&tau;</font>Tell me, O muse, of that ingenious hero who travelled far and wide
    after he had sacked the famous town of Troy. Many cities did he visit,
    and many were the nations with whose manners and customs he was acquainted;
    moreover he suffered much by sea while trying to save his own life
    and bring his men safely home; but do what he might he could not save
    his men, for they perished through their own sheer folly in eating
    the cattle of the Sun-god Hyperion; so the god prevented them from
    ever reaching home. Tell me, too, about all these things, O daughter
    of Jove, from whatsoever source you may know them.''')
    check_text('''
    Telemachus took this speech as of good omen and rose at once, for
    he was bursting with what he had to say. He stood in the middle of
    the assembly and the good herald Pisenor brought him his staff. Then,
    turning to Aegyptius, "Sir," said he, "it is I, as you will shortly
    learn, who have convened you, for it is I who am the most aggrieved.
    I have not got wind of any host approaching about which I would warn
    you, nor is there any matter of public moment on which I would speak.
    My grieveance is purely personal, and turns on two great misfortunes
    which have fallen upon my house. The first of these is the loss of
    my excellent father, who was chief among all you here present, and
    was like a father to every one of you; the second is much more serious,
    and ere long will be the utter ruin of my estate. The sons of all
    the chief men among you are pestering my mother to marry them against
    her will. They are afraid to go to her father Icarius, asking him
    to choose the one he likes best, and to provide marriage gifts for
    his daughter, but day by day they keep hanging about my father's house,
    sacrificing our oxen, sheep, and fat goats for their banquets, and
    never giving so much as a thought to the quantity of wine they drink.
    No estate can stand such recklessness; we have now no Ulysses to ward
    off harm from our doors, and I cannot hold my own against them. I
    shall never all my days be as good a man as he was, still I would
    indeed defend myself if I had power to do so, for I cannot stand such
    treatment any longer; my house is being disgraced and ruined. Have
    respect, therefore, to your own consciences and to public opinion.
    Fear, too, the wrath of heaven, lest the gods should be displeased
    and turn upon you. I pray you by Jove and Themis, who is the beginning
    and the end of councils, [do not] hold back, my friends, and leave
    me singlehanded- unless it be that my brave father Ulysses did some
    wrong to the Achaeans which you would now avenge on me, by aiding
    and abetting these suitors. Moreover, if I am to be eaten out of house
    and home at all, I had rather you did the eating yourselves, for I
    could then take action against you to some purpose, and serve you
    with notices from house to house till I got paid in full, whereas
    now I have no remedy."''')

    check_text('''
But as the sun was rising from the fair sea into the firmament of
heaven to shed light on mortals and immortals, they reached Pylos
the city of Neleus. Now the people of Pylos were gathered on the sea
shore to offer sacrifice of black bulls to Neptune lord of the Earthquake.
There were nine guilds with five hundred men in each, and there were
nine bulls to each guild. As they were eating the inward meats and
burning the thigh bones [on the embers] in the name of Neptune, Telemachus
and his crew arrived, furled their sails, brought their ship to anchor,
and went ashore. ''')
    check_text('''
So the neighbours and kinsmen of Menelaus were feasting and making
merry in his house. There was a bard also to sing to them and play
his lyre, while two tumblers went about performing in the midst of
them when the man struck up with his tune.]''')
    check_text('''
"When we had passed the [Wandering] rocks, with Scylla and terrible
Charybdis, we reached the noble island of the sun-god, where were
the goodly cattle and sheep belonging to the sun Hyperion. While still
at sea in my ship I could bear the cattle lowing as they came home
to the yards, and the sheep bleating. Then I remembered what the blind
Theban prophet Teiresias had told me, and how carefully Aeaean Circe
had warned me to shun the island of the blessed sun-god. So being
much troubled I said to the men, 'My men, I know you are hard pressed,
but listen while I <strike>tell you the prophecy that</strike> Teiresias made me, and
how carefully Aeaean Circe warned me to shun the island of the blessed
sun-god, for it was here, she said, that our worst danger would lie.
Head the ship, therefore, away from the island.''')
    check_text('''A&lt;B&gt;C&amp;D&quot;E&apos;F''')
    check_text('''A&lt; B&gt; C&amp; D&quot; E&apos; F''')
    check_text('''<![CDATA[<>&'"]]>''')
    check_text('''<bullet face=courier size=14 color=green>+</bullet>
There was a bard also to sing to them and play
his lyre, while two tumblers went about performing in the midst of
them when the man struck up with his tune.]''')
    check_text('''<onDraw name="myFunc" label="aaa   bbb">A paragraph''')
    check_text('''<para><onDraw name="myFunc" label="aaa   bbb">B paragraph</para>''')
    # HVB, 30.05.2003: Test for new features
    _parser.caseSensitive=0
    check_text('''Here comes <FONT FACE="Helvetica" SIZE="14pt">Helvetica 14</FONT> with <STRONG>strong</STRONG> <EM>emphasis</EM>.''')
    check_text('''Here comes <font face="Helvetica" size="14pt">Helvetica 14</font> with <Strong>strong</Strong> <em>emphasis</em>.''')
    check_text('''Here comes <font face="Courier" size="3cm">Courier 3cm</font> and normal again.''')
    check_text('''Before the break <br/>the middle line <br/> and the last line.''')
    check_text('''This should be an inline image <img src='../../../docs/images/testimg.gif'/>!''')
    check_text('''aaa&nbsp;bbbb <u>underline&#32;</u> cccc''')
