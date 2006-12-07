#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/platypus/paraparser.py
__version__=''' $Id$ '''
import string
import re
from types import TupleType
import sys
import os
import copy

import reportlab.lib.sequencer
from reportlab.lib.abag import ABag

from reportlab.lib import xmllib
_xmllib_newStyle = 1

from reportlab.lib.colors import toColor, white, black, red, Color
from reportlab.lib.fonts import tt2ps, ps2tt
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.units import inch,mm,cm,pica
_re_para = re.compile(r'^\s*<\s*para(?:\s+|>|/>)')

sizeDelta = 2       # amount to reduce font size by for super and sub script
subFraction = 0.5   # fraction of font size that a sub script should be lowered
superFraction = 0.5 # fraction of font size that a super script should be raised

def _num(s, unit=1):
    """Convert a string like '10cm' to an int or float (in points).
       The default unit is point, but optionally you can use other
       default units like mm.
    """
    if s[-2:]=='cm':
        unit=cm
        s = s[:-2]
    if s[-2:]=='in':
        unit=inch
        s = s[:-2]
    if s[-2:]=='pt':
        unit=1
        s = s[:-2]
    if s[-1:]=='i':
        unit=inch
        s = s[:-1]
    if s[-2:]=='mm':
        unit=mm
        s = s[:-2]
    if s[-4:]=='pica':
        unit=pica
        s = s[:-4]
    if s[0] in ['+','-']:
        try:
            return ('relative',int(s)*unit)
        except ValueError:
            return ('relative',float(s)*unit)
    else:
        try:
            return int(s)*unit
        except ValueError:
            return float(s)*unit

def _align(s):
    s = string.lower(s)
    if s=='left': return TA_LEFT
    elif s=='right': return TA_RIGHT
    elif s=='justify': return TA_JUSTIFY
    elif s in ('centre','center'): return TA_CENTER
    else: raise ValueError

_paraAttrMap = {'font': ('fontName', None),
                'face': ('fontName', None),
                'fontsize': ('fontSize', _num),
                'size': ('fontSize', _num),
                'leading': ('leading', _num),
                'lindent': ('leftIndent', _num),
                'rindent': ('rightIndent', _num),
                'findent': ('firstLineIndent', _num),
                'align': ('alignment', _align),
                'spaceb': ('spaceBefore', _num),
                'spacea': ('spaceAfter', _num),
                'bfont': ('bulletFontName', None),
                'bfontsize': ('bulletFontSize',_num),
                'bindent': ('bulletIndent',_num),
                'bcolor': ('bulletColor',toColor),
                'color':('textColor',toColor),
                'backcolor':('backColor',toColor),
                'bgcolor':('backColor',toColor),
                'bg':('backColor',toColor),
                'fg': ('textColor',toColor),
                }

_bulletAttrMap = {
                'font': ('bulletFontName', None),
                'face': ('bulletFontName', None),
                'size': ('bulletFontSize',_num),
                'fontsize': ('bulletFontSize',_num),
                'indent': ('bulletIndent',_num),
                'color': ('bulletColor',toColor),
                'fg': ('bulletColor',toColor),
                }

#things which are valid font attributes
_fontAttrMap = {'size': ('fontSize', _num),
                'face': ('fontName', None),
                'name': ('fontName', None),
                'fg':   ('textColor', toColor),
                'color':('textColor', toColor),
                }

def _addAttributeNames(m):
    K = m.keys()
    for k in K:
        n = m[k][0]
        if not m.has_key(n): m[n] = m[k]
        n = string.lower(n)
        if not m.has_key(n): m[n] = m[k]

_addAttributeNames(_paraAttrMap)
_addAttributeNames(_fontAttrMap)
_addAttributeNames(_bulletAttrMap)

def _applyAttributes(obj, attr):
    for k, v in attr.items():
        if type(v) is TupleType and v[0]=='relative':
            #AR 20/5/2000 - remove 1.5.2-ism
            #v = v[1]+getattr(obj,k,0)
            if hasattr(obj, k):
                v = v[1]+getattr(obj,k)
            else:
                v = v[1]
        setattr(obj,k,v)

#Named character entities intended to be supported from the special font
#with additions suggested by Christoph Zwerschke who also suggested the
#numeric entity names that follow.
greeks = {
    'Alpha': 'A',
    'Beta': 'B',
    'Chi': 'C',
    'Delta': 'D',
    'Epsilon': 'E',
    'Eta': 'H',
    'Gamma': 'G',
    'Iota': 'I',
    'Kappa': 'K',
    'Lambda': 'L',
    'Mu': 'M',
    'Nu': 'N',
    'Omega': 'W',
    'Omicron': 'O',
    'Phi': 'F',
    'Pi': 'P',
    'Psi': 'Y',
    'Rho': 'R',
    'Sigma': 'S',
    'Tau': 'T',
    'Theta': 'Q',
    'Upsilon': 'U',
    'Xi': 'X',
    'Zeta': 'Z',
    'alefsym': '\xc0',
    'alpha': 'a',
    'and': '\xd9',
    'ang': '\xd0',
    'asymp': '\xbb',
    'beta': 'b',
    'bull': '\xb7',
    'cap': '\xc7',
    'chi': 'c',
    'clubs': '\xa7',
    'cong': '@',
    'cup': '\xc8',
    'dArr': '\xdf',
    'darr': '\xaf',
    'delta': 'd',
    'diams': '\xa8',
    'empty': '\xc6',
    'epsilon': 'e',
    'epsiv': 'e',
    'equiv': '\xba',
    'eta': 'h',
    'euro': '\xa0',
    'exist': '$',
    'forall': '"',
    'frasl': '\xa4',
    'gamma': 'g',
    'ge': '\xb3',
    'hArr': '\xdb',
    'harr': '\xab',
    'hearts': '\xa9',
    'hellip': '\xbc',
    'image': '\xc1',
    'infin': '\xa5',
    'int': '\xf2',
    'iota': 'i',
    'isin': '\xce',
    'kappa': 'k',
    'lArr': '\xdc',
    'lambda': 'l',
    'lang': '\xe1',
    'larr': '\xac',
    'lceil': '\xe9',
    'le': '\xa3',
    'lfloor': '\xeb',
    'lowast': '*',
    'loz': '\xe0',
    'minus': '-',
    'mu': 'm',
    'nabla': '\xd1',
    'ne': '\xb9',
    'ni': "'",
    'notin': '\xcf',
    'nsub': '\xcb',
    'nu': 'n',
    'oline': '`',
    'omega': 'w',
    'omicron': 'o',
    'oplus': '\xc5',
    'or': '\xda',
    'otimes': '\xc4',
    'part': '\xb6',
    'perp': '^',
    'phi': 'j',
    'phis': 'f',
    'pi': 'p',
    'piv': 'v',
    'prime': '\xa2',
    'prod': '\xd5',
    'prop': '\xb5',
    'psi': 'y',
    'rArr': '\xde',
    'radic': '\xd6',
    'rang': '\xf1',
    'rarr': '\xae',
    'rceil': '\xf9',
    'real': '\xc2',
    'rfloor': '\xfb',
    'rho': 'r',
    'sdot': '\xd7',
    'sigma': 's',
    'sigmaf': 'V',
    'sigmav': 'V',
    'sim': '~',
    'spades': '\xaa',
    'sub': '\xcc',
    'sube': '\xcd',
    'sum': '\xe5',
    'sup': '\xc9',
    'supe': '\xca',
    'tau': 't',
    'there4': '\\',
    'theta': 'q',
    'thetasym': 'J',
    'thetav': 'J',
    'trade': '\xe4',
    'uArr': '\xdd',
    'uarr': '\xad',
    'upsih': '\xa1',
    'upsilon': 'u',
    'weierp': '\xc3',
    'xi': 'x',
    'zeta': 'z',
    }

# mapping of xml character entities to symbol encoding
symenc = {
    # greek letters
    913:'A', # Alpha
    914:'B', # Beta
    915:'G', # Gamma
    916:'D', # Delta
    917:'E', # Epsilon
    918:'Z', # Zeta
    919:'H', # Eta
    920:'Q', # Theta
    921:'I', # Iota
    922:'K', # Kappa
    923:'L', # Lambda
    924:'M', # Mu
    925:'N', # Nu
    926:'X', # Xi
    927:'O', # Omicron
    928:'P', # Pi
    929:'R', # Rho
    931:'S', # Sigma
    932:'T', # Tau
    933:'U', # Upsilon
    934:'F', # Phi
    935:'C', # Chi
    936:'Y', # Psi
    937:'W', # Omega
    945:'a', # alpha
    946:'b', # beta
    947:'g', # gamma
    948:'d', # delta
    949:'e', # epsilon
    950:'z', # zeta
    951:'h', # eta
    952:'q', # theta
    953:'i', # iota
    954:'k', # kappa
    955:'l', # lambda
    956:'m', # mu
    957:'n', # nu
    958:'x', # xi
    959:'o', # omicron
    960:'p', # pi
    961:'r', # rho
    962:'V', # sigmaf
    963:'s', # sigma
    964:'t', # tau
    965:'u', # upsilon
    966:'j', # phi
    967:'c', # chi
    968:'y', # psi
    969:'w', # omega
    977:'J', # thetasym
    978:'\241', # upsih
    981:'f', # phis
    982:'v', # piv
    # mathematical symbols
    8704:'"', # forall
    8706:'\266', # part
    8707:'$', # exist
    8709:'\306', # empty
    8711:'\321', # nabla
    8712:'\316', # isin
    8713:'\317', # notin
    8715:'\'', # ni
    8719:'\325', # prod
    8721:'\345', # sum
    8722:'-', # minus
    8727:'*', # lowast
    8730:'\326', # radic
    8733:'\265', # prop
    8734:'\245', # infin
    8736:'\320', # ang
    8869:'\331', # and
    8870:'\332', # or
    8745:'\307', # cap
    8746:'\310', # cup
    8747:'\362', # int
    8756:'\\', # there4
    8764:'~', # sim
    8773:'@', # cong
    8776:'\273', #asymp
    8800:'\271', # ne
    8801:'\272', # equiv
    8804:'\243', # le
    8805:'\263', # ge
    8834:'\314', # sub
    8835:'\311', # sup
    8836:'\313', # nsub
    8838:'\315', # sube
    8839:'\312', # supe
    8853:'\305', # oplus
    8855:'\304', # otimes
    8869:'^', # perp
    8901:'\327', # sdot
    9674:'\340', # loz
    # technical symbols
    8968:'\351', # lceil
    8969:'\371', # rceil
    8970:'\353', # lfloor
    8971:'\373', # rfloor
    9001:'\341', # lang
    9002:'\361', # rang
    # arrow symbols
    8592:'\254', # larr
    8593:'\255', # uarr
    8594:'\256', # rarr
    8595:'\257', # darr
    8596:'\253', # harr
    8656:'\334', # lArr
    8657:'\335', # uArr
    8658:'\336', # rArr
    8659:'\337', # dArr
    8660:'\333', # hArr
    # divers symbols
    8226:'\267', # bull
    8230:'\274', # hellip
    8242:'\242', # prime
    8254:'`', # oline
    8260:'\244', # frasl
    8472:'\303', # weierp
    8465:'\301', # image
    8476:'\302', # real
    8482:'\344', # trade
    8364:'\240', # euro
    8501:'\300', # alefsym
    9824:'\252', # spades
    9827:'\247', # clubs
    9829:'\251', # hearts
    9830:'\250' # diams
    }

#------------------------------------------------------------------------
class ParaFrag(ABag):
    """class ParaFrag contains the intermediate representation of string
    segments as they are being parsed by the XMLParser.
    fontname, fontSize, rise, textColor, cbDefn
    """

#------------------------------------------------------------------
# !!! NOTE !!! THIS TEXT IS NOW REPLICATED IN PARAGRAPH.PY !!!
# The ParaFormatter will be able to format the following xml
# tags:
#       < /b > - bold
#       < /i > - italics
#       < u > < /u > - underline
#       < super > < /super > - superscript
#       < sup > < /sup > - superscript
#       < sub > < /sub > - subscript
#       <font name=fontfamily/fontname color=colorname size=float>
#       < bullet > </bullet> - bullet text (at head of para only)
#       <onDraw name=callable label="a label">
#
#       The whole may be surrounded by <para> </para> tags
#
# It will also be able to handle any MathML specified Greek characters.
#------------------------------------------------------------------
class ParaParser(xmllib.XMLParser):

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
        raise AttributeError, attrName

    #### bold
    def start_b( self, attributes ):
        self._push(bold=1)

    def end_b( self ):
        self._pop(bold=1)

    def start_strong( self, attributes ):
        self._push(bold=1)

    def end_strong( self ):
        self._pop(bold=1)

    #### italics
    def start_i( self, attributes ):
        self._push(italic=1)

    def end_i( self ):
        self._pop(italic=1)

    def start_em( self, attributes ):
        self._push(italic=1)

    def end_em( self ):
        self._pop(italic=1)

    #### underline
    def start_u( self, attributes ):
        self._push(underline=1)

    def end_u( self ):
        self._pop(underline=1)

    #### super script
    def start_super( self, attributes ):
        self._push(super=1)

    def end_super( self ):
        self._pop(super=1)

    start_sup = start_super
    end_sup = end_super

    #### sub script
    def start_sub( self, attributes ):
        self._push(sub=1)

    def end_sub( self ):
        self._pop(sub=1)

    #### greek script
    #### add symbol encoding
    def handle_charref(self, name):
        try:
            if name[0] == 'x':
                n = string.atoi(name[1:], 16)
            else:
                n = string.atoi(name)
        except string.atoi_error:
            self.unknown_charref(name)
            return
        if 0 <=n<=255:
            self.handle_data(chr(n))
        elif symenc.has_key(n):
            self._push(greek=1)
            self.handle_data(symenc[n])
            self._pop(greek=1)
        else:
            self.unknown_charref(name)

    def handle_entityref(self,name):
        if greeks.has_key(name):
            self._push(greek=1)
            self.handle_data(greeks[name])
            self._pop(greek=1)
        else:
            xmllib.XMLParser.handle_entityref(self,name)

    def syntax_error(self,lineno,message):
        self._syntax_error(message)

    def _syntax_error(self,message):
        if message[:10]=="attribute " and message[-17:]==" value not quoted": return
        self.errors.append(message)

    def start_greek(self, attributes):
        self._push(greek=1)

    def end_greek(self):
        self._pop(greek=1)

    def start_font(self,attr):
        apply(self._push,(),self.getAttributes(attr,_fontAttrMap))

    def end_font(self):
        self._pop()

    def _initial_frag(self,attr,attrMap,bullet=0):
        style = self._style
        if attr!={}:
            style = copy.deepcopy(style)
            _applyAttributes(style,self.getAttributes(attr,attrMap))
            self._style = style

        # initialize semantic values
        frag = ParaFrag()
        frag.sub = 0
        frag.super = 0
        frag.rise = 0
        frag.underline = 0
        frag.greek = 0
        if bullet:
            frag.fontName, frag.bold, frag.italic = ps2tt(style.bulletFontName)
            frag.fontSize = style.bulletFontSize
            frag.textColor = hasattr(style,'bulletColor') and style.bulletColor or style.textColor
        else:
            frag.fontName, frag.bold, frag.italic = ps2tt(style.fontName)
            frag.fontSize = style.fontSize
            frag.textColor = style.textColor
        return frag

    def start_para(self,attr):
        self._stack = [self._initial_frag(attr,_paraAttrMap)]

    def end_para(self):
        self._pop()

    def start_bullet(self,attr):
        if hasattr(self,'bFragList'):
            self._syntax_error('only one <bullet> tag allowed')
        self.bFragList = []
        frag = self._initial_frag(attr,_bulletAttrMap,1)
        frag.isBullet = 1
        self._stack.append(frag)

    def end_bullet(self):
        self._pop()

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
        if attr.has_key('template'):
            templ = attr['template']
            self.handle_data(templ % self._seq)
            return
        elif attr.has_key('id'):
            id = attr['id']
        else:
            id = None
        output = self._seq.nextf(id)
        self.handle_data(output)

    def end_seq(self):
        pass

    def start_onDraw(self,attr):
        defn = ABag()
        if attr.has_key('name'): defn.name = attr['name']
        else: self._syntax_error('<onDraw> needs at least a name attribute')

        if attr.has_key('label'): defn.label = attr['label']
        defn.kind='onDraw'
        self._push(cbDefn=defn)
        self.handle_data('')
        self._pop()

    #---------------------------------------------------------------
    def _push(self,**attr):
        frag = copy.copy(self._stack[-1])
        _applyAttributes(frag,attr)
        self._stack.append(frag)

    def _pop(self,**kw):
        frag = self._stack[-1]
        del self._stack[-1]
        for k, v in kw.items():
            assert getattr(frag,k)==v
        return frag

    def getAttributes(self,attr,attrMap):
        A = {}
        for k, v in attr.items():
            if not self.caseSensitive:
                k = string.lower(k)
            if k in attrMap.keys():
                j = attrMap[k]
                func = j[1]
                try:
                    A[j[0]] = (func is None) and v or apply(func,(v,))
                except:
                    self._syntax_error('%s: invalid value %s'%(k,v))
            else:
                self._syntax_error('invalid attribute name %s'%k)
        return A

    #----------------------------------------------------------------

    def __init__(self,verbose=0):
        self.caseSensitive = 0
        xmllib.XMLParser.__init__(self,verbose=verbose)

    def _iReset(self):
        self.fragList = []
        if hasattr(self, 'bFragList'): delattr(self,'bFragList')

    def _reset(self, style):
        '''reset the parser'''
        xmllib.XMLParser.reset(self)

        # initialize list of string segments to empty
        self.errors = []
        self._style = style
        self._iReset()

    #----------------------------------------------------------------
    def handle_data(self,data):
        "Creates an intermediate representation of string segments."

        frag = copy.copy(self._stack[-1])
        if hasattr(frag,'cbDefn'):
            if data!='': syntax_error('Only <onDraw> tag allowed')
        else:
            # if sub and super are both on they will cancel each other out
            if frag.sub == 1 and frag.super == 1:
                frag.sub = 0
                frag.super = 0

            if frag.sub:
                frag.rise = -frag.fontSize*subFraction
                frag.fontSize = max(frag.fontSize-sizeDelta,3)
            elif frag.super:
                frag.rise = frag.fontSize*superFraction
                frag.fontSize = max(frag.fontSize-sizeDelta,3)

            if frag.greek: frag.fontName = 'symbol'

        # bold, italic, and underline
        x = frag.fontName = tt2ps(frag.fontName,frag.bold,frag.italic)

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

    def parse(self, text, style):
        """Given a formatted string will return a list of
        ParaFrag objects with their calculated widths.
        If errors occur None will be returned and the
        self.errors holds a list of the error messages.
        """
        self._setup_for_parse(style)
        # the xmlparser requires that all text be surrounded by xml
        # tags, therefore we must throw some unused flags around the
        # given string
        if not(len(text)>=6 and text[0]=='<' and _re_para.match(text)):
            text = "<para>"+text+"</para>"
        self.feed(text)
        self.close()    # force parsing to complete
        return self._complete_parse()

    def _complete_parse(self):
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

    def _tt_parse(self,tt):
        tag = tt[0]
        try:
            start = getattr(self,'start_'+tag)
            end = getattr(self,'end_'+tag)
        except AttributeError:
            raise ValueError('Invalid tag "%s"' % tag)
        start(tt[1] or {})
        C = tt[2]
        if C:
            M = self._tt_handlers
            for c in C:
                M[type(c) is TupleType](c)
        end()

    def tt_parse(self,tt,style):
        '''parse from tupletree form'''
        self._setup_for_parse(style)
        self._tt_handlers = self.handle_data,self._tt_parse
        self._tt_parse(tt)
        return self._complete_parse()

if __name__=='__main__':
    from reportlab.platypus import cleanBlockQuotedText
    _parser=ParaParser()
    def check_text(text,p=_parser):
        print '##########'
        text = cleanBlockQuotedText(text)
        l,rv,bv = p.parse(text,style)
        if rv is None:
            for l in _parser.errors:
                print l
        else:
            print 'ParaStyle', l.fontName,l.fontSize,l.textColor
            for l in rv:
                print l.fontName,l.fontSize,l.textColor,l.bold, l.rise, '|%s|'%l.text[:25],
                if hasattr(l,'cbDefn'):
                    print 'cbDefn',l.cbDefn.name,l.cbDefn.label,l.cbDefn.kind
                else: print

    style=ParaFrag()
    style.fontName='Times-Roman'
    style.fontSize = 12
    style.textColor = black
    style.bulletFontName = black
    style.bulletFontName='Times-Roman'
    style.bulletFontSize=12

    text='''
    <b><i><greek>a</greek>D</i></b>&beta;
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
    check_text('<para font="times-bold" size=24 leading=28.8 spaceAfter=72>ReportLab -- Reporting for the Internet Age</para>')
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
but listen while I tell you the prophecy that Teiresias made me, and
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
