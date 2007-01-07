#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/platypus/paraparser.py
__version__=''' $Id: paraparser.py 2853 2006-05-10 12:56:39Z rgbecker $ '''
import string
import re
from types import TupleType, UnicodeType, StringType
import sys
import os
import copy

import reportlab.lib.sequencer
from reportlab.lib.abag import ABag

from reportlab.lib import xmllib

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
                'backcolor':('backColor',toColor),
                'bgcolor':('backColor',toColor),
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
    'pound': '\xc2\xa3',
    'nbsp': '\xc2\xa0',
    'alefsym': '\xe2\x84\xb5',
    'Alpha': '\xce\x91',
    'alpha': '\xce\xb1',
    'and': '\xe2\x88\xa7',
    'ang': '\xe2\x88\xa0',
    'asymp': '\xe2\x89\x88',
    'Beta': '\xce\x92',
    'beta': '\xce\xb2',
    'bull': '\xe2\x80\xa2',
    'cap': '\xe2\x88\xa9',
    'Chi': '\xce\xa7',
    'chi': '\xcf\x87',
    'clubs': '\xe2\x99\xa3',
    'cong': '\xe2\x89\x85',
    'cup': '\xe2\x88\xaa',
    'darr': '\xe2\x86\x93',
    'dArr': '\xe2\x87\x93',
    'delta': '\xce\xb4',
    'Delta': '\xe2\x88\x86',
    'diams': '\xe2\x99\xa6',
    'empty': '\xe2\x88\x85',
    'Epsilon': '\xce\x95',
    'epsilon': '\xce\xb5',
    'epsiv': '\xce\xb5',
    'equiv': '\xe2\x89\xa1',
    'Eta': '\xce\x97',
    'eta': '\xce\xb7',
    'euro': '\xe2\x82\xac',
    'exist': '\xe2\x88\x83',
    'forall': '\xe2\x88\x80',
    'frasl': '\xe2\x81\x84',
    'Gamma': '\xce\x93',
    'gamma': '\xce\xb3',
    'ge': '\xe2\x89\xa5',
    'harr': '\xe2\x86\x94',
    'hArr': '\xe2\x87\x94',
    'hearts': '\xe2\x99\xa5',
    'hellip': '\xe2\x80\xa6',
    'image': '\xe2\x84\x91',
    'infin': '\xe2\x88\x9e',
    'int': '\xe2\x88\xab',
    'Iota': '\xce\x99',
    'iota': '\xce\xb9',
    'isin': '\xe2\x88\x88',
    'Kappa': '\xce\x9a',
    'kappa': '\xce\xba',
    'Lambda': '\xce\x9b',
    'lambda': '\xce\xbb',
    'lang': '\xe2\x8c\xa9',
    'larr': '\xe2\x86\x90',
    'lArr': '\xe2\x87\x90',
    'lceil': '\xef\xa3\xae',
    'le': '\xe2\x89\xa4',
    'lfloor': '\xef\xa3\xb0',
    'lowast': '\xe2\x88\x97',
    'loz': '\xe2\x97\x8a',
    'minus': '\xe2\x88\x92',
    'mu': '\xc2\xb5',
    'Mu': '\xce\x9c',
    'nabla': '\xe2\x88\x87',
    'ne': '\xe2\x89\xa0',
    'ni': '\xe2\x88\x8b',
    'notin': '\xe2\x88\x89',
    'nsub': '\xe2\x8a\x84',
    'Nu': '\xce\x9d',
    'nu': '\xce\xbd',
    'oline': '\xef\xa3\xa5',
    'omega': '\xcf\x89',
    'Omega': '\xe2\x84\xa6',
    'Omicron': '\xce\x9f',
    'omicron': '\xce\xbf',
    'oplus': '\xe2\x8a\x95',
    'or': '\xe2\x88\xa8',
    'otimes': '\xe2\x8a\x97',
    'part': '\xe2\x88\x82',
    'perp': '\xe2\x8a\xa5',
    'Phi': '\xce\xa6',
    'phi': '\xcf\x95',
    'phis': '\xcf\x86',
    'Pi': '\xce\xa0',
    'pi': '\xcf\x80',
    'piv': '\xcf\x96',
    'prime': '\xe2\x80\xb2',
    'prod': '\xe2\x88\x8f',
    'prop': '\xe2\x88\x9d',
    'Psi': '\xce\xa8',
    'psi': '\xcf\x88',
    'radic': '\xe2\x88\x9a',
    'rang': '\xe2\x8c\xaa',
    'rarr': '\xe2\x86\x92',
    'rArr': '\xe2\x87\x92',
    'rceil': '\xef\xa3\xb9',
    'real': '\xe2\x84\x9c',
    'rfloor': '\xef\xa3\xbb',
    'Rho': '\xce\xa1',
    'rho': '\xcf\x81',
    'sdot': '\xe2\x8b\x85',
    'Sigma': '\xce\xa3',
    'sigma': '\xcf\x83',
    'sigmaf': '\xcf\x82',
    'sigmav': '\xcf\x82',
    'sim': '\xe2\x88\xbc',
    'spades': '\xe2\x99\xa0',
    'sub': '\xe2\x8a\x82',
    'sube': '\xe2\x8a\x86',
    'sum': '\xe2\x88\x91',
    'sup': '\xe2\x8a\x83',
    'supe': '\xe2\x8a\x87',
    'Tau': '\xce\xa4',
    'tau': '\xcf\x84',
    'there4': '\xe2\x88\xb4',
    'Theta': '\xce\x98',
    'theta': '\xce\xb8',
    'thetasym': '\xcf\x91',
    'thetav': '\xcf\x91',
    'trade': '\xef\xa3\xaa',
    'uarr': '\xe2\x86\x91',
    'uArr': '\xe2\x87\x91',
    'upsih': '\xcf\x92',
    'Upsilon': '\xce\xa5',
    'upsilon': '\xcf\x85',
    'weierp': '\xe2\x84\x98',
    'Xi': '\xce\x9e',
    'xi': '\xce\xbe',
    'Zeta': '\xce\x96',
    'zeta': '\xce\xb6',
    }

#------------------------------------------------------------------------
class ParaFrag(ABag):
    """class ParaFrag contains the intermediate representation of string
    segments as they are being parsed by the XMLParser.
    fontname, fontSize, rise, textColor, cbDefn
    """


_greek2Utf8=None
def _greekConvert(data):
    global _greek2Utf8
    if not _greek2Utf8:
        from reportlab.pdfbase.rl_codecs import RL_Codecs
        import codecs
        dm = decoding_map = codecs.make_identity_dict(xrange(32,256))
        for k in xrange(0,32):
            dm[k] = None
        dm.update(RL_Codecs._RL_Codecs__rl_codecs_data['symbol'][0])
        _greek2Utf8 = {}
        for k,v in dm.iteritems():
            if not v:
                u = '\0'
            else:
                u = unichr(v).encode('utf8')
            _greek2Utf8[chr(k)] = u
    return ''.join(map(_greek2Utf8.__getitem__,data))

#------------------------------------------------------------------
# !!! NOTE !!! THIS TEXT IS NOW REPLICATED IN PARAGRAPH.PY !!!
# The ParaFormatter will be able to format the following
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
#       <unichar name="unicode character name"/>
#       <unichar value="unicode code point"/>
#       <greek> - </greek>
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

    #### link
    def start_link(self, attributes):
        self._push(**self.getAttributes(attributes,_linkAttrMap))

    def end_link(self):
        frag = self._stack[-1]
        del self._stack[-1]
        assert frag.link!=None

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
            if name[0]=='x':
                n = int(name[1:],16)
            else:
                n = int(name)
        except ValueError:
            self.unknown_charref(name)
            return
        self.handle_data(unichr(n).encode('utf8'))

    def handle_entityref(self,name):
        if greeks.has_key(name):
            self.handle_data(greeks[name])
        else:
            xmllib.XMLParser.handle_entityref(self,name)

    def syntax_error(self,lineno,message):
        self._syntax_error(message)

    def _syntax_error(self,message):
        if message[:10]=="attribute " and message[-17:]==" value not quoted": return
        self.errors.append(message)

    def start_greek(self, attr):
        self._push(greek=1)

    def end_greek(self):
        self._pop(greek=1)

    def start_unichar(self, attr):
        if attr.has_key('name'):
            if attr.has_key('code'):
                self._syntax_error('<unichar/> invalid with both name and code attributes')
            try:
                v = unicodedata.lookup(attr['name']).encode('utf8')
            except KeyError:
                self._syntax_error('<unichar/> invalid name attribute\n"%s"' % name)
                v = '\0'
        elif attr.has_key('code'):
            try:
                v = unichr(int(eval(attr['code']))).encode('utf8')
            except:
                self._syntax_error('<unichar/> invalid code attribute %s' % attr['code'])
                v = '\0'
        else:
            v = None
            if attr: 
                self._syntax_error('<unichar/> invalid attribute %s' % attr.keys()[0])

        if v is not None:
            self.handle_data(v)
        self._push(_selfClosingTag='unichar')

    def end_unichar(self):
        self._pop()

    def start_font(self,attr):
        self._push(**self.getAttributes(attr,_fontAttrMap))

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
        frag.link = None
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
                    A[j[0]] = (func is None) and v or func(v)
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
        elif hasattr(frag,'_selfClosingTag'):
            if data!='': syntax_error('No content allowed in %s tag' % frag._selfClosingTag)
            return
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

            if frag.greek:
                frag.fontName = 'symbol'
                data = _greekConvert(data)

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
        # AR 20040612 - when we feed Unicode strings in, sgmlop
        # tries to coerce to ASCII.  Must intercept, coerce to
        # any 8-bit encoding which defines most of 256 points,
        # and revert at end.  Yuk.  Preliminary step prior to
        # removal of parser altogether.
        enc = self._enc = 'cp1252' #our legacy default
        self._UNI = type(text) is UnicodeType
        if self._UNI:
            text = text.encode(enc)

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

        if self._UNI:
            #reconvert to unicode
            if fragList:
                for frag in fragList:
                    frag.text = unicode(frag.text, self._enc)
            if bFragList:
                for frag in bFragList:
                    frag.text = unicode(frag.text, self._enc)
            
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
