#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/platypus/paragraph.py
__all__=(
        'Paragraph',
        'cleanBlockQuotedText',
        'ParaLines',
        'FragLine',
        )
__version__='3.5.20'
__doc__='''The standard paragraph implementation'''
from string import whitespace
from operator import truth
from unicodedata import category
from reportlab.pdfbase.pdfmetrics import stringWidth, getAscentDescent
from reportlab.platypus.paraparser import ParaParser, _PCT, _num as _parser_num, _re_us_value
from reportlab.platypus.flowables import Flowable
from reportlab.lib.colors import Color
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.geomutils import normalizeTRBL
from reportlab.lib.textsplit import wordSplit, ALL_CANNOT_START
from reportlab.lib.styles import ParagraphStyle
from copy import deepcopy
from reportlab.lib.abag import ABag
from reportlab.rl_config import decimalSymbol, _FUZZ, paraFontSizeHeightOffset,\
    hyphenationMinWordLength
from reportlab.lib.utils import _className, isBytes, isStr
from reportlab.lib.rl_accel import sameFrag
import re
from types import MethodType
try:
    import pyphen
except:
    pyphen = None

#on UTF8/py33 branch, split and strip must be unicode-safe!
#thanks to Dirk Holtwick for helpful discussions/insight
#on this one
_wsc = ''.join((
    u'\u0009',  # HORIZONTAL TABULATION
    u'\u000A',  # LINE FEED
    u'\u000B',  # VERTICAL TABULATION
    u'\u000C',  # FORM FEED
    u'\u000D',  # CARRIAGE RETURN
    u'\u001C',  # FILE SEPARATOR
    u'\u001D',  # GROUP SEPARATOR
    u'\u001E',  # RECORD SEPARATOR
    u'\u001F',  # UNIT SEPARATOR
    u'\u0020',  # SPACE
    u'\u0085',  # NEXT LINE
    #u'\u00A0', # NO-BREAK SPACE
    u'\u1680',  # OGHAM SPACE MARK
    u'\u2000',  # EN QUAD
    u'\u2001',  # EM QUAD
    u'\u2002',  # EN SPACE
    u'\u2003',  # EM SPACE
    u'\u2004',  # THREE-PER-EM SPACE
    u'\u2005',  # FOUR-PER-EM SPACE
    u'\u2006',  # SIX-PER-EM SPACE
    u'\u2007',  # FIGURE SPACE
    u'\u2008',  # PUNCTUATION SPACE
    u'\u2009',  # THIN SPACE
    u'\u200A',  # HAIR SPACE
    u'\u200B',  # ZERO WIDTH SPACE
    u'\u2028',  # LINE SEPARATOR
    u'\u2029',  # PARAGRAPH SEPARATOR
    u'\u202F',  # NARROW NO-BREAK SPACE
    u'\u205F',  # MEDIUM MATHEMATICAL SPACE
    u'\u3000',  # IDEOGRAPHIC SPACE
    ))
_wsc_re_split=re.compile('[%s]+'% re.escape(_wsc)).split
_wsc_end_search=re.compile('[%s]+$'% re.escape(_wsc)).search

def _usConv(s, vMap, default=None):
    '''convert a strike/underline distance to a number'''
    if isStr(s):
        s = s.strip()
        if s:
            m = _re_us_value.match(s)
            if m:
                return float(m.group(1))*vMap[m.group(2)]
            else:
                return _parser_num(s,allowRelative=False)
        elif default:
            return default
    return s

def split(text, delim=None):
    if isBytes(text): text = text.decode('utf8')
    if delim is not None and isBytes(delim): delim = delim.decode('utf8')
    return [uword for uword in (_wsc_re_split(text) if delim is None and u'\xa0' in text else text.split(delim))]

def strip(text):
    if isBytes(text): text = text.decode('utf8')
    return text.strip(_wsc)

def lstrip(text):
    if isBytes(text): text = text.decode('utf8')
    return text.lstrip(_wsc)

def rstrip(text):
    if isBytes(text): text = text.decode('utf8')
    return text.rstrip(_wsc)

class ParaLines(ABag):
    """
    class ParaLines contains the broken into lines representation of Paragraphs
        kind=0  Simple
        fontName, fontSize, textColor apply to whole Paragraph
        lines   [(extraSpace1,words1),....,(extraspaceN,wordsN)]

        kind==1 Complex
        lines   [FragLine1,...,FragLineN]
    """

class FragLine(ABag):
    """
    class FragLine contains a styled line (ie a line with more than one style)::

        extraSpace  unused space for justification only
        wordCount   1+spaces in line for justification purposes
        words       [ParaFrags] style text lumps to be concatenated together
        fontSize    maximum fontSize seen on the line; not used at present,
                    but could be used for line spacing.
    """

def _lineClean(L):
    return ' '.join(list(filter(truth,split(strip(L)))))

def cleanBlockQuotedText(text,joiner=' '):
    """This is an internal utility which takes triple-
    quoted text form within the document and returns
    (hopefully) the paragraph the user intended originally."""
    L=list(filter(truth,list(map(_lineClean, split(text, '\n')))))
    return joiner.join(L)

def setXPos(tx,dx):
    if dx>1e-6 or dx<-1e-6:
        tx.setXPos(dx)

def _nbspCount(w):
    if isBytes(w):
        return w.count(b'\xc2\xa0')
    else:
        return w.count(u'\xa0')

def _leftDrawParaLine( tx, offset, extraspace, words, last=0):
    simple = extraspace>-1e-8 or getattr(tx,'preformatted',False)
    text = ' '.join(words)
    setXPos(tx,offset)
    if not simple:
        nSpaces = len(words)+_nbspCount(text)-1
        simple = nSpaces<=0
    if simple:
        tx._textOut(text,1)
    else:
        tx.setWordSpace(extraspace / float(nSpaces))
        tx._textOut(text,1)
        tx.setWordSpace(0)
    setXPos(tx,-offset)
    return offset

def _centerDrawParaLine( tx, offset, extraspace, words, last=0):
    simple = extraspace>-1e-8 or getattr(tx,'preformatted',False)
    text = ' '.join(words)
    if not simple:
        nSpaces = len(words)+_nbspCount(text)-1
        simple = nSpaces<=0
    if simple:
        m = offset + 0.5 * extraspace
        setXPos(tx,m)
        tx._textOut(text,1)
    else:
        m = offset
        tx.setWordSpace(extraspace / float(nSpaces))
        setXPos(tx,m)
        tx._textOut(text,1)
        tx.setWordSpace(0)
    setXPos(tx,-m)
    return m

def _rightDrawParaLine( tx, offset, extraspace, words, last=0):
    simple = extraspace>-1e-8 or getattr(tx,'preformatted',False)
    text = ' '.join(words)
    if not simple:
        nSpaces = len(words)+_nbspCount(text)-1
        simple = nSpaces<=0
    if simple:
        m = offset + extraspace
        setXPos(tx,m)
        tx._textOut(' '.join(words),1)
    else:
        m = offset
        tx.setWordSpace(extraspace / float(nSpaces))
        setXPos(tx,m)
        tx._textOut(text,1)
        tx.setWordSpace(0)
    setXPos(tx,-m)
    return m

def _justifyDrawParaLine( tx, offset, extraspace, words, last=0):
    setXPos(tx,offset)
    text  = ' '.join(words)
    simple =  getattr(tx,'preformatted',False) or (-1e-8<extraspace<=1e-8) or (last and extraspace>-1e-8)
    if not simple:
        nSpaces = len(words)+_nbspCount(text)-1
        simple = nSpaces<=0
    if simple:
        #last one or no extra space so left align
        tx._textOut(text,1)
    else:
        tx.setWordSpace(extraspace / float(nSpaces))
        tx._textOut(text,1)
        tx.setWordSpace(0)
    setXPos(tx,-offset)
    return offset

def _justifyDrawParaLineRTL( tx, offset, extraspace, words, last=0):
    return (_rightDrawParaLine if last else _justifyDrawParaLine)(tx, offset, extraspace, words, last)

def imgVRange(h,va,fontSize):
    '''return bottom,top offsets relative to baseline(0)'''
    if va=='baseline':
        iyo = 0
    elif va in ('text-top','top'):
        iyo = fontSize-h
    elif va=='middle':
        iyo = fontSize - (1.2*fontSize+h)*0.5
    elif va in ('text-bottom','bottom'):
        iyo = fontSize - 1.2*fontSize
    elif va=='super':
        iyo = 0.5*fontSize
    elif va=='sub':
        iyo = -0.5*fontSize
    elif hasattr(va,'normalizedValue'):
        iyo = va.normalizedValue(fontSize)
    else:
        iyo = va
    return iyo,iyo+h

def imgNormV(v,nv):
    if hasattr(v,'normalizedValue'):
        return v.normalizedValue(nv)
    else:
        return v

def _getDotsInfo(style):
    dots = style.endDots
    if isStr(dots):
        text = dots
        fontName = style.fontName
        fontSize = style.fontSize
        textColor = style.textColor
        backColor = style.backColor
        dy = 0
    else:
        text = getattr(dots,'text','.')
        fontName = getattr(dots,'fontName',style.fontName)
        fontSize = getattr(dots,'fontSize',style.fontSize)
        textColor = getattr(dots,'textColor',style.textColor)
        backColor = getattr(dots,'backColor',style.backColor)
        dy = getattr(dots,'dy',0)
    return text,fontName,fontSize,textColor,backColor,dy

_56=5./6
_16=1./6
def _putFragLine(cur_x, tx, line, last, pKind):
    linkRecord = getattr(tx,'_linkRecord',lambda *args, **kwds: None)
    preformatted = tx.preformatted
    xs = tx.XtraState
    cur_y = xs.cur_y
    x0 = tx._x0
    autoLeading = xs.autoLeading
    leading = xs.leading
    cur_x += xs.leftIndent
    dal = autoLeading in ('min','max')
    if dal:
        if autoLeading=='max':
            ascent = max(_56*leading,line.ascent)
            descent = max(_16*leading,-line.descent)
        else:
            ascent = line.ascent
            descent = -line.descent
        leading = ascent+descent
    if tx._leading!=leading:
        tx.setLeading(leading)
    if dal:
        olb = tx._olb
        if olb is not None:
            xcy = olb-ascent
            if tx._oleading!=leading:
                cur_y += leading - tx._oleading
            if abs(xcy-cur_y)>1e-8:
                cur_y = xcy
                tx.setTextOrigin(x0,cur_y)
                xs.cur_y = cur_y
        tx._olb = cur_y - descent
        tx._oleading = leading
    ws = getattr(tx,'_wordSpace',0)
    nSpaces = 0
    words = line.words
    AL = []
    LL = []
    us_lines = xs.us_lines
    links = xs.links
    for i, f in enumerate(words):
        if hasattr(f,'cbDefn'):
            cbDefn = f.cbDefn
            kind = cbDefn.kind
            if kind=='img':
                #draw image cbDefn,cur_y,cur_x
                txfs = tx._fontsize
                if txfs is None:
                    txfs = xs.style.fontSize
                w = imgNormV(cbDefn.width,xs.paraWidth)
                h = imgNormV(cbDefn.height,txfs)
                iy0,iy1 = imgVRange(h,cbDefn.valign,txfs)
                cur_x_s = cur_x + nSpaces*ws
                tx._canvas.drawImage(cbDefn.image,cur_x_s,cur_y+iy0,w,h,mask='auto')
                cur_x += w
                cur_x_s += w
                setXPos(tx,cur_x_s-tx._x0)
            else:
                name = cbDefn.name
                if kind=='anchor':
                    tx._canvas.bookmarkHorizontal(name,cur_x,cur_y+leading)
                else:
                    func = getattr(tx._canvas,name,None)
                    if not func:
                        raise AttributeError("Missing %s callback attribute '%s'" % (kind,name))
                    tx._canvas._curr_tx_info=dict(tx=tx,cur_x=cur_x,cur_y=cur_y,leading=leading,xs=tx.XtraState)
                    try:
                        func(tx._canvas,kind,getattr(cbDefn,'label',None))
                    finally:
                        del tx._canvas._curr_tx_info
            if f is words[-1]:
                if not tx._fontname:
                    tx.setFont(xs.style.fontName,xs.style.fontSize)
                tx._textOut('',1)
        else:
            cur_x_s = cur_x + nSpaces*ws
            end_x = cur_x_s
            fontSize = f.fontSize
            textColor = f.textColor
            rise = f.rise
            if i > 0:
                end_x = cur_x_s - (0 if preformatted else _trailingSpaceLength(words[i-1].text, tx))
            if (tx._fontname,tx._fontsize)!=(f.fontName,fontSize):
                tx._setFont(f.fontName, fontSize)
            if xs.textColor!=textColor:
                xs.textColor = textColor
                tx.setFillColor(textColor)
            if xs.rise!=rise:
                xs.rise=rise
                tx.setRise(rise)

            #we should end stuff bfore outputting more text so we can record
            #the text code position correctly if needed
            if LL != f.us_lines:
                S = set(LL)
                NS = set(f.us_lines)
                nLL = NS - S #new lines
                eLL = S - NS #ending lines
                for l in eLL:
                    us_lines[l] = us_lines[l],end_x
            if AL != f.link:
                S = set(AL)
                NS = set(f.link)
                nAL = NS - S #new linkis
                eAL = S - NS #ending links
                for l in eAL:
                    links[l] = links[l],end_x
                    linkRecord(l,'end')
            text = f.text
            tx._textOut(text,f is words[-1])    # cheap textOut
            if LL != f.us_lines:
                for l in nLL:
                    us_lines[l] = (l,fontSize,textColor,cur_x_s),fontSize
                LL = f.us_lines
            if LL:
                for l in LL:
                    l0, fsmax = us_lines[l]
                    if fontSize>fsmax:
                        us_lines[l] = l0, fontSize

            nlo = rise - 0.2*fontSize
            nhi = rise + fontSize
            if AL != f.link:
                for l in nAL:
                    links[l] = (l,cur_x),nlo,nhi
                    linkRecord(l,'start')
                AL = f.link
            if AL:
                for l in AL:
                    l0, lo, hi = links[l]
                    if nlo<lo or nhi>hi:
                        links[l] = l0,min(nlo,lo),max(nhi,hi)

            bg = getattr(f,'backColor',None)
            if bg and not xs.backColor:
                xs.backColor = bg
                xs.backColor_x = cur_x_s
            elif xs.backColor:
                if not bg:
                    xs.backColors.append( (xs.backColor_x, end_x, xs.backColor) )
                    xs.backColor = None
                elif f.backColor!=xs.backColor or xs.textColor!=xs.backColor:
                    xs.backColors.append( (xs.backColor_x, end_x, xs.backColor) )
                    xs.backColor = bg
                    xs.backColor_x = cur_x_s
            txtlen = tx._canvas.stringWidth(text, tx._fontname, tx._fontsize)
            cur_x += txtlen
            nSpaces += text.count(' ')+_nbspCount(text)

    cur_x_s = cur_x+(nSpaces-1)*ws
    if last and xs.style.endDots:
        if xs.style.wordWrap!='RTL':    #assume dots left --> right
            if pKind!='right':
                _do_dots_frag(cur_x,cur_x_s,line.maxWidth,xs,tx)
        elif pKind!='left':
            start = tx._x_offset
            _do_dots_frag(start, start, x0 - start, xs, tx, left=False)

    if LL:
        for l in LL:
            us_lines[l] = us_lines[l], cur_x_s

    if AL:
        for l in AL:
            links[l] = links[l], cur_x_s
            linkRecord(l,'end')

    if xs.backColor:
        xs.backColors.append( (xs.backColor_x, cur_x_s, xs.backColor) )
    if tx._x0!=x0:
        setXPos(tx,x0-tx._x0)

def _do_dots_frag(cur_x, cur_x_s, maxWidth, xs, tx, left=True):
    text,fontName,fontSize,textColor,backColor,dy = _getDotsInfo(xs.style)
    txtlen = tx._canvas.stringWidth(text, fontName, fontSize)
    if cur_x_s+txtlen<=maxWidth:
        if tx._fontname!=fontName or tx._fontsize!=fontSize:
            tx.setFont(fontName,fontSize)
        if left: maxWidth += getattr(tx,'_dotsOffsetX',tx._x0)
        tx.setTextOrigin(0,xs.cur_y+dy)
        setXPos(tx,cur_x_s-cur_x)
        n = int((maxWidth-cur_x_s)/txtlen)
        setXPos(tx,maxWidth - txtlen*n)
        if xs.textColor!=textColor:
            tx.setFillColor(textColor)
        if backColor: xs.backColors.append((cur_x,maxWidth,backColor))
        tx._textOut(n*text,1)
        if dy: tx.setTextOrigin(tx._x0,xs.cur_y-dy)

def _leftDrawParaLineX( tx, offset, line, last=0):
    tx._x_offset = offset
    setXPos(tx,offset)
    extraSpace = line.extraSpace
    simple = extraSpace>-1e-8 or getattr(line,'preformatted',False)
    if not simple:
        nSpaces = line.wordCount+sum([_nbspCount(w.text) for w in line.words if not hasattr(w,'cbDefn')])-1
        simple = nSpaces<=0
    if simple:
        _putFragLine(offset, tx, line, last, 'left')
    else:
        tx.setWordSpace(extraSpace / float(nSpaces))
        _putFragLine(offset, tx, line, last, 'left')
        tx.setWordSpace(0)
    setXPos(tx,-offset)

def _centerDrawParaLineX( tx, offset, line, last=0):
    tx._x_offset = offset
    tx._dotsOffsetX = offset + tx._x0
    try:
        extraSpace = line.extraSpace
        simple = extraSpace>-1e-8 or getattr(line,'preformatted',False)
        if not simple:
            nSpaces = line.wordCount+sum([_nbspCount(w.text) for w in line.words if not hasattr(w,'cbDefn')])-1
            simple = nSpaces<=0
        if simple:
            m = offset+0.5*line.extraSpace
            setXPos(tx,m)
            _putFragLine(m, tx, line, last,'center')
        else:
            m = offset
            tx.setWordSpace(extraSpace / float(nSpaces))
            _putFragLine(m, tx, line, last, 'center')
            tx.setWordSpace(0)
        setXPos(tx,-m)
    finally:
        del tx._dotsOffsetX

def _rightDrawParaLineX( tx, offset, line, last=0):
    tx._x_offset = offset
    extraSpace = line.extraSpace
    simple = extraSpace>-1e-8 or getattr(line,'preformatted',False)
    if not simple:
        nSpaces = line.wordCount+sum([_nbspCount(w.text) for w in line.words if not hasattr(w,'cbDefn')])-1
        simple = nSpaces<=0
    if simple:
        m = offset+line.extraSpace
        setXPos(tx,m)
        _putFragLine(m,tx, line, last, 'right')
    else:
        m = offset
        tx.setWordSpace(extraSpace / float(nSpaces))
        _putFragLine(m, tx, line, last, 'right')
        tx.setWordSpace(0)
    setXPos(tx,-m)

def _justifyDrawParaLineX( tx, offset, line, last=0):
    tx._x_offset = offset
    setXPos(tx,offset)
    extraSpace = line.extraSpace
    simple = line.lineBreak or (-1e-8<extraSpace<=1e-8) or (last and extraSpace>-1e-8)
    if not simple:
        nSpaces = line.wordCount+sum([_nbspCount(w.text) for w in line.words if not hasattr(w,'cbDefn')])-1
        simple = nSpaces<=0
    if not simple:
        tx.setWordSpace(extraSpace / float(nSpaces))
        _putFragLine(offset, tx, line, last, 'justify')
        tx.setWordSpace(0)
    else:
        _putFragLine(offset, tx, line, last, 'justify') #no space modification
    setXPos(tx,-offset)

def _justifyDrawParaLineXRTL( tx, offset, line, last=0):
    return (_rightDrawParaLineX if last else _justifyDrawParaLineX)( tx, offset, line, last)

def _trailingSpaceLength(text, tx):
    ws = _wsc_end_search(text)
    return tx._canvas.stringWidth(ws.group(), tx._fontname, tx._fontsize) if ws else 0

class _HSFrag(list):
    '''a frag that's followed by a space'''
    pass

class _InjectedFrag(list):
    '''a frag that's injected in breaklines and must be removed on reprocessing'''
    pass

class _SplitFrag(list):
    '''a split frag'''
    pass

class _SplitFragH(_SplitFrag):
    '''a split frag that's the head part of the split'''
    pass


class _SplitFragHY(_SplitFragH):
    '''a head split frag that needs '-' removing before rejoining'''
    pass

class _SplitFragHS(_SplitFrag,_HSFrag):
    """a split frag that's followed by a space"""
    pass

class _SplitFragLL(_SplitFragHS):
    """a frag that is forced to end in - because of paragraph split"""
    pass

class _SHYIndexedStr(str):
    def __new__(cls, u, X=None):
        if not X:
            u = u.split(_shy)
            X = []
            a = X.append
            x = 0
            for s in u:
                x += len(s)
                a(x)
            u = u''.join(u)
            X = X[:-1]
        self = str.__new__(cls,u)
        self._shyIndices = X
        return self

def _shyUnsplit(s,ss=None):
    '''rejoin two parts of an original _SHYIndexedStr or str that was split'''
    u = s.rstrip(u'-')
    if isinstance(s,_SHYIndexedStr):
        X = s._shyIndices[:]
        x = X[-1]
        if ss:
            if hasattr(ss,'_shyIndices'):
                X.extend([_+x for _ in ss._shyIndices])
            u += ss
        return _SHYIndexedStr(u,X)
    elif ss:
        u += ss
        if hasattr(ss,'_shyIndices'):
            X.extend([_+x for _ in ss._shyIndices])
            return _SHYIndexedStr(u,X)
    return u

class _SHYWord(list):
    '''a fragword containing soft hyphens some of its strings are _SHYIndexedStr'''
    def shyphenate(self, newWidth, maxWidth):
        ww = self[0]
        self._fsww = 0x7fffffff
        if ww==0: return []
        possible = None
        exceeded = False
        baseWidth = baseWidth0 = newWidth - ww
        fsww = None
        for i,(f,t) in enumerate(self[1:]):
            sW = lambda s: stringWidth(s, f.fontName, f.fontSize)
            if isinstance(t,_SHYIndexedStr):
                # there's a shy in this bit
                shyLen = sW(u'-')
                bw = baseWidth + shyLen
                for j, x in enumerate(t._shyIndices):
                    left, right = t[:x], t[x:]
                    leftw = bw+sW(left)
                    if fsww is None: fsww = leftw
                    exceeded = leftw > maxWidth
                    if exceeded: break
                    possible = i, j, x, leftw, left, right, shyLen
                baseWidth += sW(t)
            else:
                baseWidth += sW(t)
                exceeded = baseWidth > maxWidth
            if exceeded and fsww is not None: break
        self._fsww = fsww-baseWidth0 if fsww is not None else 0x7fffffff
        if not possible: return []
        i, j, x, leftw, left, right, shyLen = possible
        i1 = i+1
        f, t = self[i1] #we're splitting this subfrag
        X = t._shyIndices
        lefts = _SHYIndexedStr(left+u'-',X[:j+1])
        L = self[:i1] + [(f,lefts)]
        L[0] = leftw - baseWidth0
        R = [ww-L[0]+shyLen]+([] if not right else [(f,_SHYIndexedStr(right,[_-x for _ in X[j+1:]]))]) + self[i1+1:]
        return _SplitFragSHY(L), _SHYWordHS(R)

class _SplitFragSHY(_SHYWord, _SplitFragHY):
    '''a head split frag that requires removal of a hyphen at the end before rejoining'''

class _SHYWordHS(_SHYWord,_SplitFragHS):
    '''a fragword containing soft hyphens that's followed by a space'''
    pass

def _processed_frags(frags):
    try:
        return isinstance(frags[0][0],(float,int))
    except:
        return False

_FK_TEXT = 0
_FK_IMG = 1
_FK_APPEND = 2
_FK_BREAK = 3

def _rejoinSplitFragWords(F):
    '''F should be a list of _SplitFrags'''
    R = [0]
    aR = R.append
    wLen = 0
    psty = None
    for f in F:
        wLen += f[0]
        rmhy = isinstance(f,_SplitFragHY)
        for ff in f[1:]:
            sty, t = ff
            if rmhy and ff is f[-1]:
                wLen -= stringWidth(t[-1],sty.fontName,sty.fontSize) + 1e-8
                t = _shyUnsplit(t) #strip the '-'
            if psty is sty:
                R[-1] = (sty, _shyUnsplit(R[-1][1],t))
            else:
                aR((sty,t))
                psty = sty
    R[0] = wLen
    return _reconstructSplitFrags(f)(R)

def _reconstructSplitFrags(f):
    return ((_SHYWordHS if isinstance(f,_HSFrag) else _SHYWord) if isinstance(f,_SHYWord)
            else ((_SplitFragLL if isinstance(f,_SplitFragLL) else _HSFrag) if isinstance(f,_HSFrag) else list))

def _getFragWords(frags,maxWidth=None):
    ''' given a Parafrag list return a list of fragwords
        [[size, (f00,w00), ..., (f0n,w0n)],....,[size, (fm0,wm0), ..., (f0n,wmn)]]
        each pair f,w represents a style and some string
        each sublist represents a word
    '''
    def _rescaleFrag(f):
        w = f[0]
        if isinstance(w,_PCT):
            if w._normalizer!=maxWidth:
                w._normalizer = maxWidth
                w = w.normalizedValue(maxWidth)
                f[0] = w
    R = []
    aR = R.append
    W = []
    if _processed_frags(frags):
        aW = W.append
        #print('\nprocessed frags')
        #for _i,_r in enumerate(frags):
        #   print('%3d: [%d, [%s]](%s)' % (_i,_r[0],', '.join(('%r' % _ff[1] for _ff in _r[1:])), type(_r)))
        if True:
            for f in frags:
                if isinstance(f,_InjectedFrag): continue
                _rescaleFrag(f)
                if isinstance(f,_SplitFrag):
                    aW(f)
                    if isinstance(f, _HSFrag):
                        aR(_rejoinSplitFragWords(W))
                        del W[:]
                else:
                    if W:
                        aR(_rejoinSplitFragWords(W))
                        del W[:]
                    aR(f)
            if W:
                aR(_rejoinSplitFragWords(W))
        else:
            for f in frags:
                if isinstance(f,_InjectedFrag): continue
                _rescaleFrag(f)
                if isinstance(f,_SplitFrag):
                    f0 = f[0]
                    if not W:
                        Wlen = 0
                        sty = None
                    else:
                        if isinstance(lf,_SplitFragHY):
                            sty, t = W[-1]
                            Wlen -= stringWidth(t[-1],sty.fontName,sty.fontSize) + 1e-8
                            W[-1] = (sty,_shyUnsplit(t)) #strip the '-'
                    Wlen += f0
                    for ts,t in f[1:]:
                        if ts is sty:
                            W[-1] = (sty, _shyUnsplit(W[-1][1],t))
                        else:
                            aW((ts,t))
                            sty = ts
                    if isinstance(f, _HSFrag):
                        lf = None
                        aR(_reconstructSplitFrags(f)([Wlen]+W))
                        #aR((((_SHYWordHS if isinstance(f,_HSFrag) else _SHYWord) if isinstance(f,_SHYWord)
                        #       else (_HSFrag if isinstance(f,_HSFrag) else list))
                        #   )([Wlen]+W))
                        del W[:]
                    else:
                        lf = f          #latest f in W
                else:
                    if W:
                        #must end a joining
                        aR(_reconstructSplitFrags(f)([Wlen]+W))
                        #aR((((_SHYWordHS if isinstance(lf,_HSFrag) else _SHYWord) if isinstance(lf,_SHYWord)
                        #       else (_HSFrag if isinstance(lf,_HSFrag) else list))
                        #   )([Wlen]+W))
                        del W[:]
                    aR(f)
            if W:
                #must end a joining
                aR(_reconstructSplitFrags(lf)([Wlen]+W))
                #aR((((_SHYWordHS if isinstance(lf,_HSFrag) else _SHYWord) if isinstance(lf,_SHYWord)
                #       else (_HSFrag if isinstance(lf,_HSFrag) else list))
                #   )([Wlen]+W))
        #print('\nreconstructed frag words')
        #for _i,_r in enumerate(R):
        #   print('%3d: [%d, [%s]](%s)' % (_i,_r[0],', '.join(('%r' % _ff[1] for _ff in _r[1:])), type(_r)))
    else:
        hangingSpace = False
        n = 0
        hangingStrip = True
        shyIndices = False
        for f in frags:
            text = f.text
            if text!='':
                f._fkind = _FK_TEXT
                if hangingStrip:
                    text = lstrip(text)
                    if not text: continue
                    hangingStrip = False
                S = split(text)
                if text[0] in whitespace or not S:
                    if W:
                        W.insert(0,n)   #end preceding word
                        aR(_SHYWord(W) if shyIndices else W)
                        whs = hangingSpace
                        W = []
                        shyIndices = False
                        hangingSpace = False
                        n = 0
                    else:
                        whs = R and isinstance(R[-1],_HSFrag)
                    if not whs:
                        S.insert(0,'')
                    elif not S:
                        continue

                for w in S[:-1]:
                    if _shy in w:
                        w = _SHYIndexedStr(w)
                        shyIndices = True
                    W.append((f,w))
                    n += stringWidth(w, f.fontName, f.fontSize)
                    W.insert(0,n)
                    aR(_SHYWordHS(W) if shyIndices or isinstance(W,_SHYWord) else _HSFrag(W))
                    W = []
                    shyIndices = False
                    n = 0

                hangingSpace = False
                w = S[-1]
                if _shy in w:
                    w = _SHYIndexedStr(w)
                    shyIndices = True
                W.append((f,w))
                n += stringWidth(w, f.fontName, f.fontSize)
                if text and text[-1] in whitespace:
                    W.insert(0,n)
                    aR(_SHYWord(W) if shyIndices or isinstance(W,_SHYWord) else _HSFrag(W))
                    W = []
                    shyIndices = False
                    n = 0
            elif hasattr(f,'cbDefn'):
                cb = f.cbDefn
                w = getattr(cb,'width',0)
                if w:
                    if hasattr(w,'normalizedValue'):
                        w._normalizer = maxWidth
                        w = w.normalizedValue(maxWidth)
                    if W:
                        W.insert(0,n)
                        aR(_HSFrag(W) if hangingSpace else W)
                        W = []
                        shyIndices = False
                        hangingSpace = False
                        n = 0
                    f._fkind = _FK_IMG
                    aR([w,(f,'')])
                    hangingStrip = False
                else:
                    f._fkind = _FK_APPEND
                    if not W and R and isinstance(R[-1],_HSFrag):
                        R[-1].append((f,''))
                    else:
                        W.append((f,''))
            elif hasattr(f, 'lineBreak'):
                #pass the frag through.  The line breaker will scan for it.
                if W:
                    W.insert(0,n)
                    aR(W)
                    W = []
                    n = 0
                    shyIndices = False
                    hangingSpace = False
                f._fkind = _FK_BREAK
                aR([0,(f,'')])
                hangingStrip = True

        if W:
            W.insert(0,n)
            aR(_SHYWord(W) if shyIndices or isinstance(W,_SHYWord) else W)
    if not R:
        if frags:
            f = frags[0]
            f._fkind = _FK_TEXT
            R = [[0,(f,u'')]]

    #print('\nreturned frag words')
    #for _i,_r in enumerate(R):
    #   print('%3d: [%d, [%s]](%s)' % (_i,_r[0],', '.join(('%r' % _ff[1] for _ff in _r[1:])), type(_r)))
    return R

def _fragWordIter(w):
    for f, s in w[1:]:
        if hasattr(f,'cbDefn'):
            yield f, getattr(f.cbDefn,'width',0), s
        elif s:
            if isBytes(s):
                s = s.decode('utf8')    #only encoding allowed
            for c in s:
                yield f, stringWidth(c,f.fontName, f.fontSize), c
        else:
            yield f, 0, s

def _splitFragWord(w,maxWidth,maxWidths,lineno):
    '''given a frag word, w, as returned by getFragWords
    split it into frag words that fit in lines of length
    maxWidth
    maxWidths[lineno+1]
    .....
    maxWidths[lineno+n]

    return the new word list which is either 
    _SplitFrag....._SPlitFrag or
    _SplitFrag....._SplitFragHS if the word is hanging space.
    '''
    R = []
    maxlineno = len(maxWidths)-1
    W = []
    lineWidth = 0
    fragText = u''
    wordWidth = 0
    f = w[1][0]
    for g,cw,c in _fragWordIter(w):
        newLineWidth = lineWidth+cw
        tooLong = newLineWidth>maxWidth
        if g is not f or tooLong:
            f = f.clone()
            if hasattr(f,'text'):
                f.text = fragText
            W.append((f,fragText))
            if tooLong:
                W = _SplitFrag([wordWidth]+W)
                R.append(W)
                lineno += 1
                maxWidth = maxWidths[min(maxlineno,lineno)]
                W = []
                newLineWidth = cw
                wordWidth = 0
            fragText = u''
            f = g
        wordWidth += cw
        fragText += c
        lineWidth = newLineWidth
    W.append((f,fragText))
    W = (_SplitFragHS if isinstance(w,_HSFrag) else _SplitFragH)([wordWidth]+W)

    R.append(W)
    return R


#derived from Django validator
#https://github.com/django/django/blob/master/django/core/validators.py
uri_pat = re.compile(u'(^(?:[a-z0-9\\.\\-\\+]*)://)(?:\\S+(?::\\S*)?@)?(?:(?:25[0-5]|2[0-4]\\d|[0-1]?\\d?\\d)(?:\\.(?:25[0-5]|2[0-4]\\d|[0-1]?\\d?\\d)){3}|\\[[0-9a-f:\\.]+\\]|([a-z\xa1-\uffff0-9](?:[a-z\xa1-\uffff0-9-]{0,61}[a-z\xa1-\uffff0-9])?(?:\\.(?!-)[a-z\xa1-\uffff0-9-]{1,63}(?<!-))*\\.(?!-)(?:[a-z\xa1-\uffff-]{2,63}|xn--[a-z0-9]{1,59})(?<!-)\\.?|localhost))(?::\\d{2,5})?(?:[/?#][^\\s]*)?\\Z', re.I)

def _slash_parts(uri,scheme,slash):
    tail = u''
    while uri.endswith(slash):
        tail += slash
        uri = uri[:-1]

    i = 2
    while True:
        i = uri.find(slash,i)
        if i<0: break
        i += 1
        yield scheme+uri[:i],uri[i:]+tail

def _uri_split_pairs(uri):
    if isBytes(uri): uri = uri.decode('utf8')
    m = uri_pat.match(uri)
    if not m: return None
    scheme = m.group(1)
    uri = uri[len(scheme):]

    slash = (u'\\' if not scheme and u'/' not in uri #might be a microsoft pattern
            else u'/')
    R = ([(scheme, uri)] if scheme and uri else []) + list(_slash_parts(uri,scheme,slash))
    R.reverse()
    return R

#valid letters determined by inspection of
#    https://en.wikipedia.org/wiki/List_of_Unicode_characters#Latin_script
_hy_letters=u'A-Za-z\xc0-\xd6\xd8-\xf6\xf8-\u024f\u1e80-\u1e85\u1e00-\u1eff\u0410-\u044f\u1e02\u1e03\u1e0a\u1e0b\u1e1e\u1e1f\u1e40\u1e41\u1e56\u1e57\u1e60\u1e61\u1e6a\u1e6b\u1e9b\u1ef2\u1ef3'
#explicit hyphens
_shy = u'\xad'
_hy_shy = u'-\xad'

_hy_pfx_pat = re.compile(u'^[\'"([{\xbf\u2018\u201a\u201c\u201e]+')
_hy_sfx_pat = re.compile(u'[]\'")}?!.,;:\u2019\u201b\u201d\u201f]+$')
_hy_letters_pat=re.compile(u''.join((u"^[",_hy_letters,u"]+$")))
_hy_shy_letters_pat=re.compile(u''.join((u"^[",_hy_shy,_hy_letters,"]+$")))
_hy_shy_pat = re.compile(u''.join((u"([",_hy_shy,u"])")))

def _hyGenPair(hyphenator, s, ww, newWidth, maxWidth, fontName, fontSize, uriWasteReduce, embeddedHyphenation, hymwl):
    if isBytes(s): s = s.decode('utf8') #only encoding allowed
    m = _hy_pfx_pat.match(s)
    if m:
        pfx = m.group(0)
        s = s[len(pfx):]
    else:
        pfx = u''
    if isinstance(s,_SplitWordLL) and s[-1]=='-':
        sfx = u'-'
        s = s[:-1]
    else:
        m = _hy_sfx_pat.search(s)
        if m:
            sfx = m.group(0)
            s = s[:-len(sfx)]
        else:
            sfx = u''
    if len(s) < hymwl: return

    w0 = newWidth - ww
    R = _uri_split_pairs(s)
    if R is not None:
        #a uri match was seen
        if ww>maxWidth or (uriWasteReduce and w0 <= (1-uriWasteReduce)*maxWidth):
            #we matched a uri and it makes sense to split
            for h, t in R:
                h = pfx+h
                t = t + sfx
                hw = stringWidth(h,fontName,fontSize)
                tw = w0 + hw
                if tw<=maxWidth:
                    return u'',0,hw,ww-hw,h,t
        return

    H = _hy_shy_pat.split(s)
    if hyphenator and  (_hy_letters_pat.match(s) or (_hy_shy_letters_pat.match(s) and u'' not in H)):
        hylen = stringWidth(u'-',fontName,fontSize)
        for h,t in hyphenator(s):
            h = pfx + h
            if not _hy_shy_pat.match(h[-1]):
                jc = u'-'
                jclen = hylen
            else:
                jc = u''
                jclen = 0
            t = t + sfx
            hw = stringWidth(h,fontName,fontSize)
            tw = hw+w0 + jclen
            if tw<=maxWidth:
                return jc,jclen,hw,ww-hw,h,t

    #even though the above tries for words with '-' it may be that no split ended with '-'
    #so this may succeed where the above does not
    n = len(H)
    if n>=3 and embeddedHyphenation and u'' not in H and _hy_shy_letters_pat.match(s):
        for i in reversed(range(2,n,2)):
            h = pfx + ''.join(H[:i])
            t = ''.join(H[i:]) + sfx
            hw = stringWidth(h,fontName,fontSize)
            tw = hw+w0
            if tw<=maxWidth:
                return u'',0,hw,ww-hw,h,t

def _fragWordSplitRep(FW):
    '''takes a frag word and assembles a unicode word from it
    if a rise is seen or a non-zerowidth cbdefn then we return
    None. Otherwise we return (uword,([i1,c1],[i2,c2],...])
    where each ii is the index of the word fragment in the word
    '''
    cc = plen = 0
    X = []
    eX = X.extend
    U = []
    aU = U.append
    for i in range(1,len(FW)):
        f, t = FW[i]
        if f.rise!=0: return None
        if hasattr(f,'cbDefn') and getattr(f.cbDefn,'width',0): return
        if not t: continue
        if isBytes(t): t = t.decode('utf8')
        aU(t)
        eX(len(t)*[(i,cc)])
        cc += len(t)
    return u''.join(U),tuple(X)

def _rebuildFragWord(F):
    '''F are the frags'''
    return [sum((stringWidth(u,s.fontName,s.fontSize) for s,u in F))]+F

def _hyGenFragsPair(hyphenator, FW, newWidth, maxWidth, uriWasteReduce, embeddedHyphenation, hymwl):
    X = _fragWordSplitRep(FW)
    if not X: return
    s, X = X
    if isBytes(s): s = s.decode('utf8') #only encoding allowed
    m = _hy_pfx_pat.match(s)
    if m:
        pfx = m.group(0)
        s = s[len(pfx):]
    else:
        pfx = u''
    if isinstance(FW,_SplitFragLL) and FW[-1][1][-1]=='-':
        sfx = u'-'
        s = s[:-1]
    else:
        m = _hy_sfx_pat.search(s)
        if m:
            sfx = m.group(0)
            s = s[:-len(sfx)]
        else:
            sfx = u''
    if len(s) < hymwl: return
    ww = FW[0]
    w0 = newWidth - ww

    #try for a uri
    R = _uri_split_pairs(s)
    if R is not None:
        #a uri match was seen
        if ww>maxWidth or (uriWasteReduce and w0 <= (1-uriWasteReduce)*maxWidth):
            #we matched a uri and it makes sense to split
            for h, t in R:
                h = pfx+h
                pos = len(h)
                #FW[fx] is split
                fx, cc = X[pos]
                FL = FW[1:fx]
                ffx, sfx = FW[fx]
                sfxl = sfx[:pos-cc]
                if sfxl: FL.append((ffx,sfxl))
                sfxr = sfx[pos-cc:]
                FR = FW[fx+1:]
                if sfxr: FR.insert(0,(ffx,sfxr))
                h = _rebuildFragWord(FL)
                if w0+h[0]<=maxWidth:
                    return u'',h,_rebuildFragWord(FR)
        return

    H = _hy_shy_pat.split(s)
    if hyphenator and (_hy_letters_pat.match(s) or (_hy_shy_letters_pat.match(s) and u'' not in H)):
        #not too diffcult for now
        for h,t in hyphenator(s):
            h = pfx+h
            pos = len(h)
            #FW[fx] is split
            fx, cc = X[pos]
            FL = FW[1:fx]
            ffx, sfx = FW[fx]
            sfxl = sfx[:pos-cc]
            if not _hy_shy_pat.match(h[-1]):
                jc = u'-'
            else:
                jc = u''
            if sfxl or jc:
                FL.append((ffx,sfxl+jc))
            sfxr = sfx[pos-cc:]
            FR = FW[fx+1:]
            if sfxr: FR.insert(0,(ffx,sfxr))
            h = _rebuildFragWord(FL)
            if w0+h[0]<=maxWidth:
                return jc,h,_rebuildFragWord(FR)

    #even though the above tries for words with '-' it may be that no split ended with '-'
    #so this may succeed where the above does not
    n = len(H)
    if n>=3 and embeddedHyphenation and u'' not in H and _hy_shy_letters_pat.match(s):
        for i in reversed(range(2,n,2)):
            pos = len(pfx + u''.join(H[:i]))
            fx, cc = X[pos]
            #FW[fx] is split
            FL = FW[1:fx]
            ffx, sfx = FW[fx]
            sfxl = sfx[:pos-cc]
            if sfxl: FL.append((ffx,sfxl))
            sfxr = sfx[pos-cc:]
            FR = FW[fx+1:]
            if sfxr: FR.insert(0,(ffx,sfxr))
            h = _rebuildFragWord(FL)
            if w0+h[0]<=maxWidth:
                return u'',h,_rebuildFragWord(FR)

def _hyphenateFragWord(hyphenator,FW,newWidth,maxWidth,uriWasteReduce,embeddedHyphenation,
                        hymwl=hyphenationMinWordLength):
    ww = FW[0]
    if ww==0: return []
    if len(FW)==2:
        f, s = FW[1]
        if isinstance(FW,_SplitFragLL):
            s = _SplitWordLL(s)
        R = _hyGenPair(hyphenator, s, ww, newWidth, maxWidth, f.fontName, f.fontSize,uriWasteReduce,embeddedHyphenation, hymwl)
        if R:
            jc, hylen, hw, tw, h, t = R
            return [(_SplitFragHY if jc else _SplitFragH)([hw+hylen,(f,h+jc)]),(_SplitFragHS if isinstance(FW,_HSFrag) else _SplitFrag)([tw,(f,t)])]
    else:
        R = _hyGenFragsPair(hyphenator, FW, newWidth, maxWidth,uriWasteReduce,embeddedHyphenation, hymwl)
        if R:
            jc, h, t = R
            return [(_SplitFragHY if jc else _SplitFragH)(h),(_SplitFragHS if isinstance(FW,_HSFrag) else _SplitFrag)(t)]

    return None

class _SplitWord(str):
    pass

class _SplitWordEnd(_SplitWord):
    pass

class _SplitWordH(_SplitWord):
    pass

class _SplitWordHY(_SplitWordH):
    '''head part of a hyphenation word pair'''
    pass

class _SplitWordLL(str):
    '''a word that's forced to end with - because of paragraph split'''
    pass

class _SHYStr(str):
    '''for simple soft hyphenated words'''
    def __new__(cls,s):
        S = s.split(_shy)
        if len(S)>1:
            self = str.__new__(cls, u''.join(S))
            sp = [0]
            asp = sp.append
            for ss in S:
                asp(sp[-1]+len(ss))
            self.__sp__ = sp[1:-1]
        else:
            self = str.__new__(cls, s)
            self.__sp__ = []
        return self

    def __shysplit__(self, fontName, fontSize, baseWidth, limWidth, encoding='utf8'):
            '''
            baseWidth = currentWidth + spaceWidth + hyphenWidth
            limWidth = maxWidth + spaceShrink
            '''
            self._fsww = 0x7fffffff
            for i, sp in reversed(list(enumerate(self.__sp__))):
                #we iterate backwards so that we return the longest that fits
                #else we will end up with the shortest value in self._fsww
                sw = self[:sp]
                sww = stringWidth(sw, fontName, fontSize, encoding)
                if not i: self._fsww = sww
                swnw = baseWidth + sww
                if swnw <= limWidth:
                    #we found a suitable split in a soft-hyphenated word
                    T = self.__sp__[i:] + [len(self)]
                    S = [self[T[j]:T[j+1]] for j in range(len(T)-1)]
                    sw = _SHYStr(sw+u'-')
                    sw.__sp__ = self.__sp__[:i]
                    return [sw,_SHYStr(_shy.join(S))]

class _SHYSplitHY(_SHYStr,_SplitWordHY):
    pass

class _SHYSplit(_SHYStr,_SplitWord):
    pass

def _hyphenateWord(hyphenator,fontName,fontSize,w,ww,newWidth,maxWidth, uriWasteReduce,embeddedHyphenation,
                    hymwl=hyphenationMinWordLength):
    if ww==0: return []
    R = _hyGenPair(hyphenator, w, ww, newWidth, maxWidth, fontName, fontSize, uriWasteReduce,embeddedHyphenation, hymwl)
    if R:
        hy, hylen, hw, tw, h, t = R
        return [(_SplitWordHY if hy else _SplitWordH)(h+hy),_SplitWordEnd(t)]

def _splitWord(w, lineWidth, maxWidths, lineno, fontName, fontSize, encoding='utf8'):
    '''
    split w into words that fit in lines of length
    maxWidth
    maxWidths[lineno+1]
    .....
    maxWidths[lineno+n]

    then push those new words onto words
    '''
    #TODO fix this to use binary search for the split points
    R = []
    aR = R.append
    maxlineno = len(maxWidths)-1
    wordText = u''
    maxWidth = maxWidths[min(maxlineno,lineno)]
    if isBytes(w):
        w = w.decode(encoding)
    for c in w:
        cw = stringWidth(c,fontName,fontSize,encoding)
        newLineWidth = lineWidth+cw
        if newLineWidth>maxWidth:
            aR(_SplitWord(wordText))
            lineno += 1
            maxWidth = maxWidths[min(maxlineno,lineno)]
            newLineWidth = cw
            wordText = u''
        wordText += c
        lineWidth = newLineWidth
    aR(_SplitWordEnd(wordText))
    return R

def _rejoinSplitWords(R):
    '''R can be a list of pure _SplitWord or _SHYStr'''
    if isinstance(R[0],_SHYStr):
        r = R[0]
        for _ in R[:]:
            r = _shyUnsplit(r,_)
        return r
    elif isinstance(R[0],_SplitWordHY):
        cf = str if isinstance(R[-1], _SplitWordEnd) else _SplitWordHY
        s = u''.join((_[:-1] if isinstance(_,_SplitWordHY) else _ for _ in R))
        return s if isinstance(R[-1], _SplitWordEnd) else _SplitWordHY(s+u'-')
    else:
        return ''.join(R)

def _yieldBLParaWords(blPara,start,stop):
    R = []
    aR = R.append
    for l in blPara.lines[start:stop]:
        for w in l[1]:
            if isinstance(w,_SplitWord):
                aR(w)
                if isinstance(w,_SplitWordEnd):
                    yield _rejoinSplitWords(R)
                    del R[:]
                continue
            else:
                if R:
                    yield _rejoinSplitWords(R)
                    del R[:]
            yield w
    if R:
        yield _rejoinSplitWords(R)

def _split_blParaSimple(blPara,start,stop):
    f = blPara.clone()
    for a in ('lines', 'kind', 'text'):
        if hasattr(f,a): delattr(f,a)
    f.words = list(_yieldBLParaWords(blPara,start,stop))
    if isinstance(f.words[-1],_SplitWordHY):
        f.words[-1].__class__ = _SHYSplit if isinstance(f.words[-1],_SHYStr) else _SplitWordLL
    return [f]

def _split_blParaHard(blPara,start,stop):
    f = []
    lines = blPara.lines[start:stop]
    for l in lines:
        for w in l.words:
            f.append(w)
        if l is not lines[-1]:
            i = len(f)-1
            while i>=0 and hasattr(f[i],'cbDefn') and not getattr(f[i].cbDefn,'width',0): i -= 1
            if i>=0:
                g = f[i]
                if not g.text: g.text = ' '
                elif g.text[-1]!=' ': g.text += ' '
    return f

def _drawBullet(canvas, offset, cur_y, bulletText, style, rtl):
    '''draw a bullet text could be a simple string or a frag list'''
    bulletAnchor = style.bulletAnchor
    if rtl or style.bulletAnchor!='start':
        numeric = bulletAnchor=='numeric'
        if isStr(bulletText):
            t =  bulletText
            q = numeric and decimalSymbol in t
            if q: t = t[:t.index(decimalSymbol)]
            bulletWidth = stringWidth(t, style.bulletFontName, style.bulletFontSize)
            if q: bulletWidth += 0.5 * stringWidth(decimalSymbol, style.bulletFontName, style.bulletFontSize)
        else:
            #it's a list of fragments
            bulletWidth = 0
            for f in bulletText:
                t = f.text
                q = numeric and decimalSymbol in t
                if q:
                    t = t[:t.index(decimalSymbol)]
                    bulletWidth += 0.5 * stringWidth(decimalSymbol, f.fontName, f.fontSize)
                bulletWidth += stringWidth(t, f.fontName, f.fontSize)
                if q:
                    break
    else:
        bulletWidth = 0
    if bulletAnchor=='middle': bulletWidth *= 0.5
    cur_y += getattr(style,"bulletOffsetY",0)
    if not rtl:
        tx2 = canvas.beginText(style.bulletIndent-bulletWidth,cur_y)
    else:
        width = rtl[0]
        bulletStart = width+style.rightIndent-(style.bulletIndent+bulletWidth)
        tx2 = canvas.beginText(bulletStart, cur_y)
    tx2.setFont(style.bulletFontName, style.bulletFontSize)
    tx2.setFillColor(getattr(style,'bulletColor',style.textColor))
    if isStr(bulletText):
        tx2.textOut(bulletText)
    else:
        for f in bulletText:
            tx2.setFont(f.fontName, f.fontSize)
            tx2.setFillColor(f.textColor)
            tx2.textOut(f.text)

    canvas.drawText(tx2)
    if not rtl:
        #AR making definition lists a bit less ugly
        #bulletEnd = tx2.getX()
        bulletEnd = tx2.getX() + style.bulletFontSize * 0.6
        offset = max(offset,bulletEnd - style.leftIndent)
    return offset

def _handleBulletWidth(bulletText,style,maxWidths):
    '''work out bullet width and adjust maxWidths[0] if neccessary
    '''
    if bulletText:
        if isStr(bulletText):
            bulletWidth = stringWidth( bulletText, style.bulletFontName, style.bulletFontSize)
        else:
            #it's a list of fragments
            bulletWidth = 0
            for f in bulletText:
                bulletWidth += stringWidth(f.text, f.fontName, f.fontSize)
        bulletLen = style.bulletIndent + bulletWidth + 0.6 * style.bulletFontSize
        if style.wordWrap=='RTL':
            indent = style.rightIndent+style.firstLineIndent
        else:
            indent = style.leftIndent+style.firstLineIndent
        if bulletLen > indent:
            #..then it overruns, and we have less space available on line 1
            maxWidths[0] -= (bulletLen - indent)

def splitLines0(frags,widths):
    '''
    given a list of ParaFrags we return a list of ParaLines

    each ParaLine has
    1)  ExtraSpace
    2)  blankCount
    3)  [textDefns....]
    each text definition is a (ParaFrag, start, limit) triplet
    '''
    #initialise the algorithm
    lines   = []
    lineNum = 0
    maxW    = widths[lineNum]
    i       = -1
    l       = len(frags)
    lim     = start = 0
    while 1:
        #find a non whitespace character
        while i<l:
            while start<lim and text[start]==' ': start += 1
            if start==lim:
                i += 1
                if i==l: break
                start = 0
                f = frags[i]
                text = f.text
                lim = len(text)
            else:
                break   # we found one

        if start==lim: break    #if we didn't find one we are done

        #start of a line
        g       = (None,None,None)
        line    = []
        cLen    = 0
        nSpaces = 0
        while cLen<maxW:
            j = text.find(' ',start)
            if j<0: j==lim
            w = stringWidth(text[start:j],f.fontName,f.fontSize)
            cLen += w
            if cLen>maxW and line!=[]:
                cLen = cLen-w
                #this is the end of the line
                while g.text[lim]==' ':
                    lim = lim - 1
                    nSpaces = nSpaces-1
                break
            if j<0: j = lim
            if g[0] is f: g[2] = j  #extend
            else:
                g = (f,start,j)
                line.append(g)
            if j==lim:
                i += 1

def _do_line(tx, x1, y1, x2, y2, nlw, nsc):
    canv = tx._canvas
    olw = canv._lineWidth
    if nlw!=olw:
        canv.setLineWidth(nlw)
    osc = canv._strokeColorObj
    if nsc!=osc:
        canv.setStrokeColor(nsc)
    canv.line(x1, y1, x2, y2)

def _do_under_line(i, x1, ws, tx, us_lines):
    xs = tx.XtraState
    style = xs.style
    y0 = xs.cur_y - i*style.leading
    f = xs.f
    fs = f.fontSize
    tc = f.textColor
    values = dict(L=fs,F=fs,f=fs)
    dw = tx._defaultLineWidth
    x2 = x1 + tx._canvas.stringWidth(' '.join(tx.XtraState.lines[i][1]), tx._fontname, fs) + ws
    for n,k,c,w,o,r,m,g in us_lines:
        underline = k=='underline'
        lw = _usConv(w,values,default=tx._defaultLineWidth)
        lg = _usConv(g,values,default=1)
        dy = lg+lw
        if not underline: dy = -dy
        y = y0 + r + _usConv(('-0.125*L' if underline else '0.25*L') if o=='' else o,values)
        if not c: c = tc
        while m>0:
            tx._do_line(x1, y, x2, y, lw, c)
            y -= dy
            m -= 1

_scheme_re = re.compile('^[a-zA-Z][-+a-zA-Z0-9]+$')
def _doLink(tx,link,rect):
    if not link: return
    if link.startswith('#'):
        tx._canvas.linkRect("", link[1:], rect, relative=1)
    else:
        parts = link.split(':',1)
        scheme = len(parts)==2 and parts[0].lower() or ''
        if scheme=='document':
            tx._canvas.linkRect("", parts[1], rect, relative=1)
        elif _scheme_re.match(scheme):
            kind=scheme.lower()=='pdf' and 'GoToR' or 'URI'
            if kind=='GoToR': link = parts[1]
            tx._canvas.linkURL(link, rect, relative=1, kind=kind)
        else:
            tx._canvas.linkURL(link, rect, relative=1, kind='URI')

def _do_link_line(i, t_off, ws, tx):
    xs = tx.XtraState
    leading = xs.style.leading
    y = xs.cur_y - i*leading - xs.f.fontSize/8.0 # 8.0 factor copied from para.py
    text = ' '.join(xs.lines[i][1])
    textlen = tx._canvas.stringWidth(text, tx._fontname, tx._fontsize)
    for n, link in xs.link:
        _doLink(tx, link, (t_off, y, t_off+textlen, y+leading))

def _do_post_text(tx):
    xs = tx.XtraState
    y0 = xs.cur_y
    f = xs.f
    leading = xs.style.leading
    autoLeading = xs.autoLeading
    fontSize = f.fontSize
    if autoLeading=='max':
        leading = max(leading,1.2*fontSize)
    elif autoLeading=='min':
        leading = 1.2*fontSize

    if xs.backColors:
        yl = y0 + fontSize
        ydesc = yl - leading

        for x1,x2,c in xs.backColors:
            tx._canvas.setFillColor(c)
            tx._canvas.rect(x1,ydesc,x2-x1,leading,stroke=0,fill=1)
        xs.backColors=[]
        xs.backColor=None

    for (((n,link),x1),lo,hi),x2 in sorted(xs.links.values()):
        _doLink(tx, link, (x1, y0+lo, x2, y0+hi))
    xs.links = {}

    if xs.us_lines:
        #print 'lines'
        dw = tx._defaultLineWidth
        values = dict(L=fontSize)
        for (((n,k,c,w,o,r,m,g),fs,tc,x1),fsmax),x2 in sorted(xs.us_lines.values()):
            underline = k=='underline'
            values['f'] = fs
            values['F'] = fsmax
            lw = _usConv(w,values,default=tx._defaultLineWidth)
            lg = _usConv(g,values,default=1)
            dy = lg+lw
            if not underline: dy = -dy
            y = y0 + r + _usConv(o if o!='' else ('-0.125*L' if underline else '0.25*L'),values)
            #print 'n=%s k=%s x1=%s x2=%s r=%s c=%s w=%r o=%r fs=%r tc=%s y=%s lw=%r offs=%r' % (n,k,x1,x2,r,(c.hexval() if c else ''),w,o,fs,tc.hexval(),y,lw,y-y0-r)
            if not c: c = tc
            while m>0:
                tx._do_line(x1, y, x2, y, lw, c)
                y -= dy
                m -= 1
        xs.us_lines = {}

    xs.cur_y -= leading

def textTransformFrags(frags,style):
    tt = style.textTransform
    if tt:
        tt=tt.lower()
        if tt=='lowercase':
            tt = str.lower
        elif tt=='uppercase':
            tt = str.upper
        elif  tt=='capitalize':
            tt = str.title
        elif tt=='none':
            return
        else:
            raise ValueError('ParaStyle.textTransform value %r is invalid' % style.textTransform)
        n = len(frags)
        if n==1:
            #single fragment the easy case
            frags[0].text = tt(frags[0].text)
        elif tt is str.title:
            pb = True
            for f in frags:
                u = f.text
                if not u: continue
                if u.startswith(u' ') or pb:
                    u = tt(u)
                else:
                    i = u.find(u' ')
                    if i>=0:
                        u = u[:i]+tt(u[i:])
                pb = u.endswith(u' ')
                f.text = u
        else:
            for f in frags:
                u = f.text
                if not u: continue
                f.text = tt(u)

class cjkU(str):
    '''simple class to hold the frag corresponding to a str'''
    def __new__(cls,value,frag,encoding):
        self = str.__new__(cls,value)
        self._frag = frag
        if hasattr(frag,'cbDefn'):
            w = getattr(frag.cbDefn,'width',0)
            self._width = w
        else:
            self._width = stringWidth(value,frag.fontName,frag.fontSize)
        return self
    frag = property(lambda self: self._frag)
    width = property(lambda self: self._width)

def makeCJKParaLine(U,maxWidth,widthUsed,extraSpace,lineBreak,calcBounds):
    words = []
    CW = []
    f0 = FragLine()
    maxSize = maxAscent = minDescent = 0
    for u in U:
        f = u.frag
        fontSize = f.fontSize
        if calcBounds:
            cbDefn = getattr(f,'cbDefn',None)
            if getattr(cbDefn,'width',0):
                descent, ascent = imgVRange(imgNormV(cbDefn.height,fontSize),cbDefn.valign,fontSize)
            else:
                ascent, descent = getAscentDescent(f.fontName,fontSize)
        else:
            ascent, descent = getAscentDescent(f.fontName,fontSize)
        maxSize = max(maxSize,fontSize)
        maxAscent = max(maxAscent,ascent)
        minDescent = min(minDescent,descent)
        if not sameFrag(f0,f):
            f0=f0.clone()
            f0.text = u''.join(CW)
            words.append(f0)
            CW = []
            f0 = f
        CW.append(u)
    if CW:
        f0=f0.clone()
        f0.text = u''.join(CW)
        words.append(f0)
    return FragLine(kind=1,extraSpace=extraSpace,wordCount=1,words=words[1:],fontSize=maxSize,ascent=maxAscent,descent=minDescent,maxWidth=maxWidth,currentWidth=widthUsed,lineBreak=lineBreak)

def cjkFragSplit(frags, maxWidths, calcBounds, encoding='utf8'):
    '''This attempts to be wordSplit for frags using the dumb algorithm'''
    U = []  #get a list of single glyphs with their widths etc etc
    for f in frags:
        text = f.text
        if isBytes(text):
            text = text.decode(encoding)
        if text:
            U.extend([cjkU(t,f,encoding) for t in text])
        else:
            U.append(cjkU(text,f,encoding))
    lines = []
    i = widthUsed = lineStartPos = 0
    maxWidth = maxWidths[0]
    nU = len(U)
    while i<nU:
        u = U[i]
        i += 1
        w = u.width
        if hasattr(w,'normalizedValue'):
            w._normalizer = maxWidth
            w = w.normalizedValue(maxWidth)
        widthUsed += w
        lineBreak = hasattr(u.frag,'lineBreak')
        endLine = (widthUsed>maxWidth + _FUZZ and widthUsed>0) or lineBreak
        if endLine:
            extraSpace = maxWidth - widthUsed
            if not lineBreak:
                if ord(u)<0x3000:
                    # we appear to be inside a non-Asian script section.
                    # (this is a very crude test but quick to compute).
                    # This is likely to be quite rare so the speed of the
                    # code below is hopefully not a big issue.  The main
                    # situation requiring this is that a document title
                    # with an english product name in it got cut.


                    # we count back and look for
                    #  - a space-like character
                    #  - reversion to Kanji (which would be a good split point)
                    #  - in the worst case, roughly half way back along the line
                    limitCheck = (lineStartPos+i)>>1        #(arbitrary taste issue)
                    for j in range(i-1,limitCheck,-1):
                        uj = U[j]
                        if uj and category(uj)=='Zs' or ord(uj)>=0x3000:
                            k = j+1
                            if k<i:
                                j = k+1
                                extraSpace += sum(U[ii].width for ii in range(j,i))
                                w = U[k].width
                                u = U[k]
                                i = j
                                break

                #we are pushing this character back, but
                #the most important of the Japanese typography rules
                #if this character cannot start a line, wrap it up to this line so it hangs
                #in the right margin. We won't do two or more though - that's unlikely and
                #would result in growing ugliness.
                #and increase the extra space
                #bug fix contributed by Alexander Vasilenko <alexs.vasilenko@gmail.com>
                if u not in ALL_CANNOT_START and i>lineStartPos+1:
                    #otherwise we need to push the character back
                    #the i>lineStart+1 condition ensures progress
                    i -= 1
                    extraSpace += w
            lines.append(makeCJKParaLine(U[lineStartPos:i],maxWidth,widthUsed,extraSpace,lineBreak,calcBounds))
            try:
                maxWidth = maxWidths[len(lines)]
            except IndexError:
                maxWidth = maxWidths[-1]  # use the last one

            lineStartPos = i
            widthUsed = 0

    #any characters left?
    if widthUsed > 0:
        lines.append(makeCJKParaLine(U[lineStartPos:],maxWidth,widthUsed,maxWidth-widthUsed,False,calcBounds))

    return ParaLines(kind=1,lines=lines)

def _setTXLineProps(tx, canvas, style):
    tx._defaultLineWidth = canvas._lineWidth
    tx._underlineColor = getattr(style,'underlineColor','')
    tx._underlineWidth = getattr(style,'underlineWidth','')
    tx._underlineOffset = getattr(style,'underlineOffset','') or '-0.125f'
    tx._strikeColor = getattr(style,'strikeColor','')
    tx._strikeWidth = getattr(style,'strikeWidth','')
    tx._strikeOffset = getattr(style,'strikeOffset','') or '0.25f'

class Paragraph(Flowable):
    """ Paragraph(text, style, bulletText=None, caseSensitive=1)
        text a string of stuff to go into the paragraph.
        style is a style definition as in reportlab.lib.styles.
        bulletText is an optional bullet defintion.
        caseSensitive set this to 0 if you want the markup tags and their attributes to be case-insensitive.

        This class is a flowable that can format a block of text
        into a paragraph with a given style.

        The paragraph Text can contain XML-like markup including the tags:
        <b> ... </b> - bold
        < u [color="red"] [width="pts"] [offset="pts"]> < /u > - underline
            width and offset can be empty meaning use existing canvas line width
            or with an f/F suffix regarded as a fraction of the font size
        < strike > < /strike > - strike through has the same parameters as underline
        <i> ... </i> - italics
        <u> ... </u> - underline
        <strike> ... </strike> - strike through
        <super> ... </super> - superscript
        <sub> ... </sub> - subscript
        <font name=fontfamily/fontname color=colorname size=float>
        <span name=fontfamily/fontname color=colorname backcolor=colorname size=float style=stylename>
        <onDraw name=callable label="a label"/>
        <index [name="callablecanvasattribute"] label="a label"/>
        <link>link text</link>
            attributes of links
                size/fontSize/uwidth/uoffset=num
                name/face/fontName=name
                fg/textColor/color/ucolor=color
                backcolor/backColor/bgcolor=color
                dest/destination/target/href/link=target
                underline=bool turn on underline
        <a>anchor text</a>
            attributes of anchors
                size/fontSize/uwidth/uoffset=num
                fontName=name
                fg/textColor/color/ucolor=color
                backcolor/backColor/bgcolor=color
                href=href
                underline="yes|no"
        <a name="anchorpoint"/>
        <unichar name="unicode character name"/>
        <unichar value="unicode code point"/>
        <img src="path" width="1in" height="1in" valign="bottom"/>
                width="w%" --> fontSize*w/100   idea from Roberto Alsina
                height="h%" --> linewidth*h/100 <ralsina@netmanagers.com.ar>

        The whole may be surrounded by <para> </para> tags

        The <b> and <i> tags will work for the built-in fonts (Helvetica
        /Times / Courier).  For other fonts you need to register a family
        of 4 fonts using reportlab.pdfbase.pdfmetrics.registerFont; then
        use the addMapping function to tell the library that these 4 fonts
        form a family e.g.
        from reportlab.lib.fonts import addMapping
        addMapping('Vera', 0, 0, 'Vera')    #normal
        addMapping('Vera', 0, 1, 'Vera-Italic')    #italic
        addMapping('Vera', 1, 0, 'Vera-Bold')    #bold
        addMapping('Vera', 1, 1, 'Vera-BoldItalic')    #italic and bold

        It will also be able to handle any MathML specified Greek characters.
    """
    def __init__(self, text, style=None, bulletText = None, frags=None, caseSensitive=1, encoding='utf8'):
        if style is None:
            style = ParagraphStyle(name='paragraphImplicitDefaultStyle')
        self.caseSensitive = caseSensitive
        self.encoding = encoding
        self._setup(text, style, bulletText or getattr(style,'bulletText',None), frags, cleanBlockQuotedText)


    def __repr__(self):
        n = self.__class__.__name__
        L = [n+"("]
        keys = list(self.__dict__.keys())
        for k in keys:
            L.append('%s: %s' % (repr(k).replace("\n", " ").replace("  "," "),repr(getattr(self, k)).replace("\n", " ").replace("  "," ")))
        L.append(") #"+n)
        return '\n'.join(L)

    def _setup(self, text, style, bulletText, frags, cleaner):

        #This used to be a global parser to save overhead.
        #In the interests of thread safety it is being instantiated per paragraph.
        #On the next release, we'll replace with a cElementTree parser
        if frags is None:
            text = cleaner(text)
            _parser = ParaParser()
            _parser.caseSensitive = self.caseSensitive
            style, frags, bulletTextFrags = _parser.parse(text,style)
            if frags is None:
                raise ValueError("xml parser error (%s) in paragraph beginning\n'%s'"\
                    % (_parser.errors[0],text[:min(30,len(text))]))
            textTransformFrags(frags,style)
            if bulletTextFrags: bulletText = bulletTextFrags

        #AR hack
        self.text = text
        self.frags = frags  #either the parse fragments or frag word list
        self.style = style
        self.bulletText = bulletText
        self.debug = 0  #turn this on to see a pretty one with all the margins etc.

    def wrap(self, availWidth, availHeight):
        if availWidth<_FUZZ:
            #we cannot fit here
            return 0, 0x7fffffff
        # work out widths array for breaking
        self.width = availWidth
        style = self.style
        leftIndent = style.leftIndent
        first_line_width = availWidth - (leftIndent+style.firstLineIndent) - style.rightIndent
        later_widths = availWidth - leftIndent - style.rightIndent
        self._wrapWidths = [first_line_width, later_widths]
        if style.wordWrap == 'CJK':
            #use Asian text wrap algorithm to break characters
            blPara = self.breakLinesCJK(self._wrapWidths)
        else:
            blPara = self.breakLines(self._wrapWidths)
        self.blPara = blPara
        autoLeading = getattr(self,'autoLeading',getattr(style,'autoLeading',''))
        leading = style.leading
        if blPara.kind==1:
            if autoLeading not in ('','off'):
                height = 0
                if autoLeading=='max':
                    for l in blPara.lines:
                        height += max(l.ascent-l.descent,leading)
                elif autoLeading=='min':
                    for l in blPara.lines:
                        height += l.ascent - l.descent
                else:
                    raise ValueError('invalid autoLeading value %r' % autoLeading)
            else:
                height = len(blPara.lines) * leading
        else:
            if autoLeading=='max':
                leading = max(leading,blPara.ascent-blPara.descent)
            elif autoLeading=='min':
                leading = blPara.ascent-blPara.descent
            height = len(blPara.lines) * leading
        self.height = height
        return self.width, height

    def minWidth(self):
        'Attempt to determine a minimum sensible width'
        frags = self.frags
        nFrags= len(frags)
        if not nFrags: return 0
        if nFrags==1 and not _processed_frags(frags):
            f = frags[0]
            fS = f.fontSize
            fN = f.fontName
            return max(stringWidth(w,fN,fS) for w in (split(f.text, ' ') if hasattr(f,'text') else f.words))
        else:
            return max(w[0] for w in _getFragWords(frags))

    def _split_blParaProcessed(self,blPara,start,stop):
        if not stop: return []
        lines = blPara.lines
        sFW = lines[start].sFW
        sFWN = lines[stop].sFW if stop!=len(lines) else len(self.frags)
        F = self.frags[sFW:sFWN]
        while F and isinstance(F[-1],_InjectedFrag): del F[-1]
        if isinstance(F[-1],_SplitFragHY):
            F[-1].__class__ = _SHYWordHS if isinstance(F[-1],_SHYWord) else _SplitFragLL
        return F

    def _get_split_blParaFunc(self):
        return (_split_blParaSimple if self.blPara.kind==0 
                    else (_split_blParaHard if not _processed_frags(self.frags)
                        else self._split_blParaProcessed))

    def split(self,availWidth, availHeight):
        if len(self.frags)<=0 or availWidth<_FUZZ or availHeight<_FUZZ: return []

        #the split information is all inside self.blPara
        if not hasattr(self,'blPara'):
            self.wrap(availWidth,availHeight)
        blPara = self.blPara
        style = self.style
        autoLeading = getattr(self,'autoLeading',getattr(style,'autoLeading',''))
        leading = style.leading
        lines = blPara.lines
        if blPara.kind==1 and autoLeading not in ('','off'):
            s = height = 0
            if autoLeading=='max':
                for i,l in enumerate(blPara.lines):
                    h = max(l.ascent-l.descent,leading)
                    n = height+h
                    if n>availHeight+1e-8:
                        break
                    height = n
                    s = i+1
            elif autoLeading=='min':
                for i,l in enumerate(blPara.lines):
                    n = height+l.ascent-l.descent
                    if n>availHeight+1e-8:
                        break
                    height = n
                    s = i+1
            else:
                raise ValueError('invalid autoLeading value %r' % autoLeading)
        else:
            l = leading
            if autoLeading=='max':
                l = max(leading,1.2*style.fontSize)
            elif autoLeading=='min':
                l = 1.2*style.fontSize
            s = int(availHeight/float(l))
            height = s*l

        allowOrphans = getattr(self,'allowOrphans',getattr(style,'allowOrphans',0))
        if (not allowOrphans and s<=1) or s==0: #orphan or not enough room
            del self.blPara
            return []
        n = len(lines)
        allowWidows = getattr(self,'allowWidows',getattr(style,'allowWidows',1))
        if n<=s:
            return [self]
        if not allowWidows:
            if n==s+1: #widow?
                if (allowOrphans and n==3) or n>3:
                    s -= 1  #give the widow some company
                else:
                    del self.blPara #no room for adjustment; force the whole para onwards
                    return []
        func = self._get_split_blParaFunc()

        if style.endDots:
            style1 = deepcopy(style)
            style1.endDots = None
        else:
            style1 = style
        P1=self.__class__(None,style1,bulletText=self.bulletText,frags=func(blPara,0,s))
        #this is a major hack
        P1.blPara = ParaLines(kind=1,lines=blPara.lines[0:s],aH=availHeight,aW=availWidth)
        #do not justify text if linebreak was inserted after the text
        #bug reported and fix contributed by Niharika Singh <nsingh@shoobx.com>
        P1._JustifyLast = not (isinstance(blPara.lines[s-1],FragLine)
                                and hasattr(blPara.lines[s-1], 'lineBreak')
                                and blPara.lines[s-1].lineBreak)
        P1._splitpara = 1
        P1.height = height
        P1.width = availWidth
        if style.firstLineIndent != 0:
            style = deepcopy(style)
            style.firstLineIndent = 0
        P2=self.__class__(None,style,bulletText=None,frags=func(blPara,s,n))
        #propagate attributes that might be on self; suggestion from Dirk Holtwick
        for a in ('autoLeading',    #possible attributes that might be directly on self.
                ):
            if hasattr(self,a):
                setattr(P1,a,getattr(self,a))
                setattr(P2,a,getattr(self,a))

        return [P1,P2]

    def draw(self):
        #call another method for historical reasons.  Besides, I
        #suspect I will be playing with alternate drawing routines
        #so not doing it here makes it easier to switch.
        self.drawPara(self.debug)

    def breakLines(self, width):
        """
        Returns a broken line structure. There are two cases

        A) For the simple case of a single formatting input fragment the output is
            A fragment specifier with
                - kind = 0
                - fontName, fontSize, leading, textColor
                - lines=  A list of lines

                        Each line has two items.

                        1. unused width in points
                        2. word list

        B) When there is more than one input formatting fragment the output is
            A fragment specifier with
               - kind = 1
               - lines=  A list of fragments each having fields
                            - extraspace (needed for justified)
                            - fontSize
                            - words=word list
                                each word is itself a fragment with
                                various settings
            in addition frags becomes a frag word list

        This structure can be used to easily draw paragraphs with the various alignments.
        You can supply either a single width or a list of widths; the latter will have its
        last item repeated until necessary. A 2-element list is useful when there is a
        different first line indent; a longer list could be created to facilitate custom wraps
        around irregular objects."""

        self._width_max = 0
        if not isinstance(width,(tuple,list)): maxWidths = [width]
        else: maxWidths = width
        lines = []
        self.height = lineno = 0
        maxlineno = len(maxWidths)-1
        style = self.style
        hyphenator = getattr(style,'hyphenationLang','')
        if hyphenator:
            if isStr(hyphenator):
                hyphenator = hyphenator.strip()
                if hyphenator and pyphen:
                    hyphenator = pyphen.Pyphen(lang=hyphenator).iterate
                else:
                    hyphenator = None
            elif not callable(hyphenator):
                raise ValueError('hyphenator should be a language spec or a callable unicode -->  pairs not %r' % hyphenator) 
        else:
            hyphenator = None
        uriWasteReduce = style.uriWasteReduce
        embeddedHyphenation = style.embeddedHyphenation
        hyphenation2 = embeddedHyphenation>1
        spaceShrinkage = style.spaceShrinkage
        splitLongWords = style.splitLongWords
        attemptHyphenation = hyphenator or uriWasteReduce or embeddedHyphenation
        if attemptHyphenation:
            hymwl = getattr(style,'hyphenationMinWordLength',hyphenationMinWordLength)
        self._splitLongWordCount = self._hyphenations = 0

        #for bullets, work out width and ensure we wrap the right amount onto line one
        _handleBulletWidth(self.bulletText,style,maxWidths)

        maxWidth = maxWidths[0]

        autoLeading = getattr(self,'autoLeading',getattr(style,'autoLeading',''))
        calcBounds = autoLeading not in ('','off')
        frags = self.frags
        nFrags= len(frags)
        if (nFrags==1 
                and not (style.endDots or hasattr(frags[0],'cbDefn') or hasattr(frags[0],'backColor')
                            or _processed_frags(frags))):
            f = frags[0]
            fontSize = f.fontSize
            fontName = f.fontName
            ascent, descent = getAscentDescent(fontName,fontSize)
            if hasattr(f,'text'):
                text = strip(f.text)
                if not text:
                    return f.clone(kind=0, lines=[],ascent=ascent,descent=descent,fontSize=fontSize)
                else:
                    words = split(text)
            else:
                words = f.words[:]
                for w in words:
                    if strip(w): break
                else:
                    return f.clone(kind=0, lines=[],ascent=ascent,descent=descent,fontSize=fontSize)
            spaceWidth = stringWidth(' ', fontName, fontSize, self.encoding)
            dSpaceShrink = spaceShrinkage*spaceWidth
            cLine = []
            currentWidth = -spaceWidth   # hack to get around extra space for word 1
            hyw = stringWidth('-', fontName, fontSize, self.encoding)
            forcedSplit = 0
            while words:
                word = words.pop(0)
                if not word and isinstance(word,_SplitWord):
                    forcedSplit = 1
                elif _shy in word:
                    word = _SHYStr(word)    #allow for soft hyphenation
                #this underscores my feeling that Unicode throughout would be easier!
                wordWidth = stringWidth(word, fontName, fontSize, self.encoding)
                newWidth = currentWidth + spaceWidth + wordWidth
                limWidth = maxWidth + dSpaceShrink*len(cLine)
                #print(f's: {currentWidth=} spaceShrink={limWidth-maxWidth} {newWidth=} {limWidth=} {newWidth>limWidth} cond={newWidth>limWidth and not (isinstance(word,_SplitWordH) or forcedSplit)} {word=}')
                if newWidth>limWidth and not (isinstance(word,_SplitWordH) or forcedSplit):
                    if isinstance(word,_SHYStr):
                        hsw = word.__shysplit__(
                                fontName, fontSize,
                                currentWidth + spaceWidth + hyw - 1e-8,
                                limWidth,
                                encoding = self.encoding,
                                )
                        if hsw:
                            words[0:0] = hsw
                            self._hyphenations += 1
                            forcedSplit = 1
                            continue
                        elif len(cLine):
                            nMW = maxWidths[min(maxlineno,lineno)]
                            if hyphenation2 or (word._fsww+hyw+1e-8)<=nMW:
                                hsw = word.__shysplit__(
                                    fontName, fontSize,
                                    0 + hyw - 1e-8,
                                    nMW,
                                    encoding = self.encoding,
                                    )
                                if hsw:
                                    words[0:0] = [word]
                                    forcedSplit = 1
                                    word = None
                                    newWidth = currentWidth
                    elif attemptHyphenation:
                        hyOk = not getattr(f,'nobr',False)
                        hsw = _hyphenateWord(hyphenator if hyOk else None,
                                fontName, fontSize, word, wordWidth, newWidth, limWidth,
                                    uriWasteReduce if hyOk else False,
                                    embeddedHyphenation and hyOk, hymwl)
                        if hsw:
                            words[0:0] = hsw
                            self._hyphenations += 1
                            forcedSplit = 1
                            continue
                        elif hyphenation2 and len(cLine):
                            hsw = _hyphenateWord(hyphenator if hyOk else None,
                                fontName, fontSize, word, wordWidth, wordWidth, maxWidth,
                                    uriWasteReduce if hyOk else False,
                                    embeddedHyphenation and hyOk, hymwl)
                            if hsw:
                                words[0:0] = [word]
                                forcedSplit = 1
                                newWidth = currentWidth
                                word = None
                    if splitLongWords and not (isinstance(word,_SplitWord) or forcedSplit):
                        nmw = min(lineno,maxlineno)
                        if wordWidth>max(maxWidths[nmw:nmw+1]):
                            #a long word
                            words[0:0] = _splitWord(word,currentWidth+spaceWidth,maxWidths,lineno,fontName,fontSize,self.encoding)
                            self._splitLongWordCount += 1
                            forcedSplit = 1
                            continue
                if newWidth<=limWidth or not len(cLine) or forcedSplit:
                    # fit one more on this line
                    if word: cLine.append(word)
                    #print(f's: |line|={len(cLine)} {newWidth=} spaceShrink={limWidth-maxWidth}')
                    if forcedSplit:
                        forcedSplit = 0
                        if newWidth > self._width_max: self._width_max = newWidth
                        lines.append((maxWidth - newWidth, cLine))
                        cLine = []
                        currentWidth = -spaceWidth
                        lineno += 1
                        maxWidth = maxWidths[min(maxlineno,lineno)]
                    else:
                        currentWidth = newWidth
                else:
                    if currentWidth > self._width_max: self._width_max = currentWidth
                    #end of line
                    lines.append((maxWidth - currentWidth, cLine))
                    cLine = [word]
                    currentWidth = wordWidth
                    lineno += 1
                    maxWidth = maxWidths[min(maxlineno,lineno)]

            #deal with any leftovers on the final line
            if cLine!=[]:
                if currentWidth>self._width_max: self._width_max = currentWidth
                lines.append((maxWidth - currentWidth, cLine))

            return f.clone(kind=0, lines=lines,ascent=ascent,descent=descent,fontSize=fontSize)
        elif nFrags<=0:
            return ParaLines(kind=0, fontSize=style.fontSize, fontName=style.fontName,
                            textColor=style.textColor, ascent=style.fontSize,descent=-0.2*style.fontSize,
                            lines=[])
        else:
            njlbv = not style.justifyBreaks
            words = []
            FW = []
            aFW = FW.append
            _words = _getFragWords(frags,maxWidth)
            sFW = 0
            while _words:
                w = _words.pop(0)
                aFW(w)
                f = w[-1][0]
                fontName = f.fontName
                fontSize = f.fontSize

                if not words:
                    n = spaceWidth = currentWidth = 0
                    maxSize = fontSize
                    maxAscent, minDescent = getAscentDescent(fontName,fontSize)

                wordWidth = w[0]
                f = w[1][0]
                if wordWidth>0:
                    newWidth = currentWidth + spaceWidth + wordWidth
                else:
                    newWidth = currentWidth

                #test to see if this frag is a line break. If it is we will only act on it
                #if the current width is non-negative or the previous thing was a deliberate lineBreak
                lineBreak = f._fkind==_FK_BREAK
                limWidth = maxWidth
                if spaceShrinkage:
                    spaceShrink = spaceWidth
                    for wi in words:
                        if wi._fkind==_FK_TEXT:
                            ns = wi.text.count(' ')
                            if ns:
                                spaceShrink += ns*stringWidth(' ',wi.fontName,wi.fontSize)
                    spaceShrink *= spaceShrinkage
                    limWidth += spaceShrink
                #print(f'c: {currentWidth=} {spaceShrink=} {newWidth=} {limWidth=} {newWidth>(maxWidth+spaceShrink)} cond={not lineBreak and newWidth>limWidth and not isinstance(w,_SplitFragH) and not hasattr(f,"cbDefn")} word={w[1][1]}')
                if not lineBreak and newWidth>limWidth and not isinstance(w,_SplitFragH) and not hasattr(f,'cbDefn'):
                    if isinstance(w,_SHYWord):
                        hsw = w.shyphenate(newWidth, limWidth)
                        if hsw:
                            _words[0:0] = hsw
                            _words.insert(1,_InjectedFrag([0,(f.clone(_fkind=_FK_BREAK,text=''),'')]))
                            FW.pop(-1)  #remove this as we are doing this one again
                            self._hyphenations += 1
                            continue
                        elif len(FW)>1: #only if we are not the first word on the line
                            nMW = maxWidths[min(maxlineno,lineno)]  #next maxWidth or current one
                            if hyphenation2 or w._fsww+1e-8<=nMW:
                                hsw = w.shyphenate(wordWidth, nMW)
                                if hsw:
                                    _words[0:0] = [_InjectedFrag([0,(f.clone(_fkind=_FK_BREAK,text=''),'')]),w]
                                    FW.pop(-1)  #remove this as we are doing this one again
                                    continue
                        #else: try to split an overlong word
                    elif attemptHyphenation:
                        hyOk = not getattr(f,'nobr',False)
                        hsw = _hyphenateFragWord(hyphenator if hyOk else None,
                                    w,newWidth,limWidth,
                                    uriWasteReduce if hyOk else False,
                                    embeddedHyphenation and hyOk, hymwl)
                        if hsw:
                            _words[0:0] = hsw
                            _words.insert(1,_InjectedFrag([0,(f.clone(_fkind=_FK_BREAK,text=''),'')]))
                            FW.pop(-1)  #remove this as we are doing this one again
                            self._hyphenations += 1
                            continue
                        elif hyphenation2 and len(FW)>1:
                            hsw = _hyphenateFragWord(hyphenator if hyOk else None,
                                        w,wordWidth,maxWidth,
                                        uriWasteReduce if hyOk else False,
                                        embeddedHyphenation and hyOk, hymwl)
                            if hsw:
                                _words[0:0] = [_InjectedFrag([0,(f.clone(_fkind=_FK_BREAK,text=''),'')]),w]
                                FW.pop(-1)  #remove this as we are doing this one again
                                continue
                        #else: try to split an overlong word
                    if splitLongWords and not isinstance(w,_SplitFrag):
                        nmw = min(lineno,maxlineno)
                        if wordWidth>max(maxWidths[nmw:nmw+1]):
                            #a long word
                            _words[0:0] = _splitFragWord(w,maxWidth-spaceWidth-currentWidth,maxWidths,lineno)
                            _words.insert(1,_InjectedFrag([0,(f.clone(_fkind=_FK_BREAK,text=''),'')]))
                            FW.pop(-1)  #remove this as we are doing this one again
                            self._splitLongWordCount += 1
                            continue
                endLine = (newWidth>limWidth and n>0) or lineBreak
                if not endLine:
                    #print(f'c: |line|={len(words)} {newWidth=} spaceShrink={limWidth-maxWidth}')
                    if lineBreak: continue      #throw it away
                    nText = w[1][1]
                    if nText: n += 1
                    fontSize = f.fontSize
                    if calcBounds:
                        if f._fkind==_FK_IMG:
                            descent,ascent = imgVRange(imgNormV(f.cbDefn.height,fontSize),f.cbDefn.valign,fontSize)
                        else:
                            ascent, descent = getAscentDescent(f.fontName,fontSize)
                    else:
                        ascent, descent = getAscentDescent(f.fontName,fontSize)
                    maxSize = max(maxSize,fontSize)
                    maxAscent = max(maxAscent,ascent)
                    minDescent = min(minDescent,descent)
                    if not words:
                        g = f.clone()
                        words = [g]
                        g.text = nText
                    elif not sameFrag(g,f):
                        if spaceWidth:
                            i = len(words)-1
                            while i>=0:
                                wi = words[i]
                                i -= 1
                                if wi._fkind==_FK_TEXT:
                                    if not wi.text.endswith(' '):
                                        wi.text += ' '
                                    break
                        g = f.clone()
                        words.append(g)
                        g.text = nText
                    elif spaceWidth:
                        if not g.text.endswith(' '):
                            g.text += ' ' + nText
                        else:
                            g.text += nText
                    else:
                        g.text += nText

                    spaceWidth = stringWidth(' ',fontName,fontSize) if isinstance(w,_HSFrag) else 0 #of the space following this word

                    ni = 0
                    for i in w[2:]:
                        g = i[0].clone()
                        g.text=i[1]
                        if g.text: ni = 1
                        words.append(g)
                        fontSize = g.fontSize
                        if calcBounds:
                            if g._fkind==_FK_IMG:
                                descent,ascent = imgVRange(imgNormV(g.cbDefn.height,fontSize),g.cbDefn.valign,fontSize)
                            else:
                                ascent, descent = getAscentDescent(g.fontName,fontSize)
                        else:
                            ascent, descent = getAscentDescent(g.fontName,fontSize)
                        maxSize = max(maxSize,fontSize)
                        maxAscent = max(maxAscent,ascent)
                        minDescent = min(minDescent,descent)
                    if not nText and ni:
                        #one bit at least of the word was real
                        n+=1
                    #print(f'{n=} words={[_.text for _ in words]!r}')
                    currentWidth = newWidth
                else:  #either it won't fit, or it's a lineBreak tag
                    if lineBreak:
                        g = f.clone()
                        #del g.lineBreak
                        words.append(g)
                        llb = njlbv and not isinstance(w,_InjectedFrag)
                    else:
                        llb = False

                    if currentWidth>self._width_max: self._width_max = currentWidth
                    #end of line
                    lines.append(FragLine(extraSpace=maxWidth-currentWidth, wordCount=n,
                                        lineBreak=llb, words=words, fontSize=maxSize, ascent=maxAscent, descent=minDescent, maxWidth=maxWidth,
                                        sFW=sFW))
                    sFW = len(FW)-1

                    #start new line
                    lineno += 1
                    maxWidth = maxWidths[min(maxlineno,lineno)]

                    if lineBreak:
                        words = []
                        continue

                    spaceWidth = stringWidth(' ',fontName,fontSize) if isinstance(w,_HSFrag) else 0 #of the space following this word
                    dSpaceShrink = spaceWidth*spaceShrinkage
                    currentWidth = wordWidth
                    n = 1
                    g = f.clone()
                    maxSize = g.fontSize
                    if calcBounds:
                        if g._fkind==_FK_IMG:
                            descent,ascent = imgVRange(imgNormV(g.cbDefn.height,fontSize),g.cbDefn.valign,fontSize)
                        else:
                            maxAscent, minDescent = getAscentDescent(g.fontName,maxSize)
                    else:
                        maxAscent, minDescent = getAscentDescent(g.fontName,maxSize)
                    words = [g]
                    g.text = w[1][1]

                    for i in w[2:]:
                        g = i[0].clone()
                        g.text=i[1]
                        words.append(g)
                        fontSize = g.fontSize
                        if calcBounds:
                            if g._fkind==_FK_IMG:
                                descent,ascent = imgVRange(imgNormV(g.cbDefn.height,fontSize),g.cbDefn.valign,fontSize)
                            else:
                                ascent, descent = getAscentDescent(g.fontName,fontSize)
                        else:
                            ascent, descent = getAscentDescent(g.fontName,fontSize)
                        maxSize = max(maxSize,fontSize)
                        maxAscent = max(maxAscent,ascent)
                        minDescent = min(minDescent,descent)

            #deal with any leftovers on the final line
            if words:
                if currentWidth>self._width_max: self._width_max = currentWidth
                lines.append(ParaLines(extraSpace=(maxWidth - currentWidth),wordCount=n,lineBreak=False,
                                    words=words, fontSize=maxSize,ascent=maxAscent,descent=minDescent,maxWidth=maxWidth,sFW=sFW))
            self.frags = FW
            return ParaLines(kind=1, lines=lines)

    def breakLinesCJK(self, maxWidths):
        """Initially, the dumbest possible wrapping algorithm.
        Cannot handle font variations."""

        if not isinstance(maxWidths,(list,tuple)): maxWidths = [maxWidths]
        style = self.style
        self.height = 0

        #for bullets, work out width and ensure we wrap the right amount onto line one
        _handleBulletWidth(self.bulletText, style, maxWidths)
        frags = self.frags
        nFrags = len(frags)
        if nFrags==1 and not hasattr(frags[0],'cbDefn') and not style.endDots:
            f = frags[0]
            if hasattr(self,'blPara') and getattr(self,'_splitpara',0):
                return f.clone(kind=0, lines=self.blPara.lines)
            #single frag case
            lines = []
            lineno = 0
            if hasattr(f,'text'):
                text = f.text
            else:
                text = ''.join(getattr(f,'words',[]))

            lines = wordSplit(text, maxWidths, f.fontName, f.fontSize)
            #the paragraph drawing routine assumes multiple frags per line, so we need an
            #extra list like this
            #  [space, [text]]
            #
            wrappedLines = [(sp, [line]) for (sp, line) in lines]
            return f.clone(kind=0, lines=wrappedLines, ascent=f.fontSize, descent=-0.2*f.fontSize)
        elif nFrags<=0:
            return ParaLines(kind=0, fontSize=style.fontSize, fontName=style.fontName,
                            textColor=style.textColor, lines=[],ascent=style.fontSize,descent=-0.2*style.fontSize)

        #general case nFrags>1 or special
        if hasattr(self,'blPara') and getattr(self,'_splitpara',0):
            return self.blPara
        autoLeading = getattr(self,'autoLeading',getattr(style,'autoLeading',''))
        calcBounds = autoLeading not in ('','off')
        return cjkFragSplit(frags, maxWidths, calcBounds)

    def beginText(self, x, y):
        return self.canv.beginText(x, y)

    def drawPara(self,debug=0):
        """Draws a paragraph according to the given style.
        Returns the final y position at the bottom. Not safe for
        paragraphs without spaces e.g. Japanese; wrapping
        algorithm will go infinite."""

        #stash the key facts locally for speed
        canvas = self.canv
        style = self.style
        blPara = self.blPara
        lines = blPara.lines
        leading = style.leading
        autoLeading = getattr(self,'autoLeading',getattr(style,'autoLeading',''))

        #work out the origin for line 1
        leftIndent = style.leftIndent
        cur_x = leftIndent

        if debug:
            bw = 0.5
            bc = Color(1,1,0)
            bg = Color(0.9,0.9,0.9)
        else:
            bw = getattr(style,'borderWidth',None)
            bc = getattr(style,'borderColor',None)
            bg = style.backColor

        #if has a background or border, draw it
        if bg or (bc and bw):
            canvas.saveState()
            op = canvas.rect
            kwds = dict(fill=0,stroke=0)
            if bc and bw:
                canvas.setStrokeColor(bc)
                canvas.setLineWidth(bw)
                kwds['stroke'] = 1
                br = getattr(style,'borderRadius',0)
                if br and not debug:
                    op = canvas.roundRect
                    kwds['radius'] = br
            if bg:
                canvas.setFillColor(bg)
                kwds['fill'] = 1
            bp = getattr(style,'borderPadding',0)
            tbp, rbp, bbp, lbp = normalizeTRBL(bp)
            op(leftIndent - lbp,
                        -bbp,
                        self.width - (leftIndent+style.rightIndent) + lbp+rbp,
                        self.height + tbp+bbp,
                        **kwds)
            canvas.restoreState()

        nLines = len(lines)
        bulletText = self.bulletText
        if nLines > 0:
            _offsets = getattr(self,'_offsets',[0])
            _offsets += (nLines-len(_offsets))*[_offsets[-1]]
            canvas.saveState()
            #canvas.addLiteral('%% %s.drawPara' % _className(self))
            alignment = style.alignment
            offset = style.firstLineIndent+_offsets[0]
            lim = nLines-1
            noJustifyLast = not getattr(self,'_JustifyLast',False)
            jllwc = style.justifyLastLine
            isRTL = style.wordWrap=='RTL'
            bRTL = isRTL and self._wrapWidths or False

            if blPara.kind==0:
                if alignment == TA_LEFT:
                    dpl = _leftDrawParaLine
                elif alignment == TA_CENTER:
                    dpl = _centerDrawParaLine
                elif alignment == TA_RIGHT:
                    dpl = _rightDrawParaLine
                elif alignment == TA_JUSTIFY:
                    dpl = _justifyDrawParaLineRTL if isRTL else _justifyDrawParaLine
                f = blPara
                if paraFontSizeHeightOffset:
                    cur_y = self.height - f.fontSize
                else:
                    cur_y = self.height - getattr(f,'ascent',f.fontSize)
                if bulletText:
                    offset = _drawBullet(canvas,offset,cur_y,bulletText,style,rtl=bRTL)

                #set up the font etc.
                canvas.setFillColor(f.textColor)

                tx = self.beginText(cur_x, cur_y)
                tx.preformatted = 'preformatted' in self.__class__.__name__.lower()
                if autoLeading=='max':
                    leading = max(leading,blPara.ascent-blPara.descent)
                elif autoLeading=='min':
                    leading = blPara.ascent-blPara.descent

                # set the paragraph direction
                tx.direction = self.style.wordWrap

                #now the font for the rest of the paragraph
                tx.setFont(f.fontName, f.fontSize, leading)
                ws = lines[0][0]
                words = lines[0][1]
                lastLine = noJustifyLast and nLines==1
                if lastLine and jllwc and len(words)>jllwc:
                    lastLine=False
                t_off = dpl( tx, offset, ws, words, lastLine)
                if f.us_lines or f.link:# or style.endDots:
                    tx._do_line = MethodType(_do_line,tx)
                    tx.xs = xs = tx.XtraState = ABag()
                    _setTXLineProps(tx, canvas, style)
                    xs.cur_y = cur_y
                    xs.f = f
                    xs.style = style
                    xs.lines = lines
                    xs.link=f.link
                    xs.textColor = f.textColor
                    xs.backColors = []
                    dx = t_off+leftIndent
                    if alignment!=TA_JUSTIFY or lastLine: ws = 0
                    if f.us_lines:
                        _do_under_line(0, dx, ws, tx, f.us_lines)
                    if f.link: _do_link_line(0, dx, ws, tx)
                    #if lastLine and style.endDots and dpl!=_rightDrawParaLine: _do_dots(0, dx, ws, xs, tx, dpl)

                    #now the middle of the paragraph, aligned with the left margin which is our origin.
                    for i in range(1, nLines):
                        ws = lines[i][0]
                        words = lines[i][1]
                        lastLine = noJustifyLast and i==lim
                        if lastLine and jllwc and len(words)>jllwc:
                            lastLine=False
                        t_off = dpl( tx, _offsets[i], ws, words, lastLine)
                        dx = t_off+leftIndent
                        if alignment!=TA_JUSTIFY or lastLine: ws = 0
                        if f.us_lines:
                            _do_under_line(i, t_off, ws, tx, f.us_lines)
                        if f.link: _do_link_line(i, dx, ws, tx)
                        #if lastLine and style.endDots and dpl!=_rightDrawParaLine: _do_dots(i, dx, ws, xs, tx, dpl)
                else:
                    for i in range(1, nLines):
                        words = lines[i][1]
                        lastLine = noJustifyLast and i==lim
                        if lastLine and jllwc and len(words)>jllwc:
                            lastLine=False
                        dpl( tx, _offsets[i], lines[i][0], words, lastLine)
            else:
                if isRTL:
                    for line in lines:
                        line.words = line.words[::-1]
                f = lines[0]
                if paraFontSizeHeightOffset:
                    cur_y = self.height - f.fontSize
                else:
                    cur_y = self.height - getattr(f,'ascent',f.fontSize)
                # default?
                dpl = _leftDrawParaLineX
                if bulletText:
                    oo = offset
                    offset = _drawBullet(canvas,offset,cur_y,bulletText,style, rtl=bRTL)
                if alignment == TA_LEFT:
                    dpl = _leftDrawParaLineX
                elif alignment == TA_CENTER:
                    dpl = _centerDrawParaLineX
                elif alignment == TA_RIGHT:
                    dpl = _rightDrawParaLineX
                elif alignment == TA_JUSTIFY:
                    dpl = _justifyDrawParaLineXRTL if isRTL else _justifyDrawParaLineX
                else:
                    raise ValueError("bad align %s" % repr(alignment))

                #set up the font etc.
                tx = self.beginText(cur_x, cur_y)
                tx.preformatted = 'preformatted' in self.__class__.__name__.lower()
                _setTXLineProps(tx, canvas, style)
                tx._do_line = MethodType(_do_line,tx)
                # set the paragraph direction
                tx.direction = self.style.wordWrap

                xs = tx.XtraState=ABag()
                xs.textColor=None
                xs.backColor=None
                xs.rise=0
                xs.backColors=[]
                xs.us_lines = {}
                xs.links = {}
                xs.link={}
                xs.leading = style.leading
                xs.leftIndent = leftIndent
                tx._leading = None
                tx._olb = None
                xs.cur_y = cur_y
                xs.f = f
                xs.style = style
                xs.autoLeading = autoLeading
                xs.paraWidth = self.width

                tx._fontname,tx._fontsize = None, None
                line = lines[0]
                lastLine = noJustifyLast and nLines==1
                if lastLine and jllwc and line.wordCount>jllwc:
                    lastLine=False
                dpl( tx, offset, line, lastLine)
                _do_post_text(tx)

                #now the middle of the paragraph, aligned with the left margin which is our origin.
                for i in range(1, nLines):
                    line = lines[i]
                    lastLine = noJustifyLast and i==lim
                    if lastLine and jllwc and line.wordCount>jllwc:
                        lastLine=False
                    dpl( tx, _offsets[i], line, lastLine)
                    _do_post_text(tx)

            canvas.drawText(tx)
            canvas.restoreState()

    def getPlainText(self,identify=None):
        """Convenience function for templates which want access
        to the raw text, without XML tags. """
        frags = getattr(self,'frags',None)
        if frags:
            plains = []
            plains_append = plains.append
            if _processed_frags(frags):
                for word in frags:
                    for style,text in word[1:]:
                        plains_append(text)
                    if isinstance(word,_HSFrag):
                        plains_append(' ')
            else:
                for frag in frags:
                    if hasattr(frag, 'text'):
                        plains_append(frag.text)
            return ''.join(plains)
        elif identify:
            text = getattr(self,'text',None)
            if text is None: text = repr(self)
            return text
        else:
            return ''

    def getActualLineWidths0(self):
        """Convenience function; tells you how wide each line
        actually is.  For justified styles, this will be
        the same as the wrap width; for others it might be
        useful for seeing if paragraphs will fit in spaces."""
        assert hasattr(self, 'width'), "Cannot call this method before wrap()"
        if self.blPara.kind:
            func = lambda frag, w=self.width: w - frag.extraSpace
        else:
            func = lambda frag, w=self.width: w - frag[0]
        return list(map(func,self.blPara.lines))

    @staticmethod
    def dumpFrags(frags,indent=4,full=False):
        R = ['[']
        aR = R.append
        for i,f in enumerate(frags):
            if full:
                aR('    [%r,' % f[0])
                for fx in f[1:]:
                    aR('        (%s,)' % repr(fx[0]))
                    aR('        %r),' % fx[1])
                    aR('    ], #%d %s' % (i,f.__class__.__name__))
                aR('    ]')
            else:
                aR('[%r, %s], #%d %s' % (f[0],', '.join(('(%s,%r)' % (fx[0].__class__.__name__,fx[1]) for fx in f[1:])),i,f.__class__.__name__))
        i = indent*' '
        return i + ('\n'+i).join(R)

if __name__=='__main__':    #NORUNTESTS
    def dumpParagraphLines(P):
        print('dumpParagraphLines(<Paragraph @ %d>)' % id(P))
        lines = P.blPara.lines
        outw = sys.stdout.write
        for l,line in enumerate(lines):
            line = lines[l]
            if hasattr(line,'words'):
                words = line.words
            else:
                words = line[1]
            nwords = len(words)
            outw('line%d: %d(%s)\n  ' % (l,nwords,str(getattr(line,'wordCount','Unknown'))))
            for w in range(nwords):
                outw(" %d:'%s'"%(w,getattr(words[w],'text',words[w])))
            print()

    def fragDump(w):
        R= ["'%s'" % w[1]]
        for a in ('fontName', 'fontSize', 'textColor', 'rise', 'underline', 'strike', 'link', 'cbDefn','lineBreak'):
            if hasattr(w[0],a):
                R.append('%s=%r' % (a,getattr(w[0],a)))
        return ', '.join(R)

    def dumpParagraphFrags(P):
        print('dumpParagraphFrags(<Paragraph @ %d>) minWidth() = %.2f' % (id(P), P.minWidth()))
        frags = P.frags
        n =len(frags)
        for l in range(n):
            print("frag%d: '%s' %s" % (l, frags[l].text,' '.join(['%s=%s' % (k,getattr(frags[l],k)) for k in frags[l].__dict__ if k!=text])))

        outw = sys.stdout.write
        l = 0
        cum = 0
        for W in _getFragWords(frags,360):
            cum += W[0]
            outw("fragword%d: cum=%3d size=%d" % (l, cum, W[0]))
            for w in W[1:]:
                outw(' (%s)' % fragDump(w))
            print()
            l += 1

    def dumpProcessedFrags(P,label='processed_frags'):
        if isinstance(P2.frags[0],list):
            _F = {}
            _S = [].append
            def _showWord(w):
                t = [].append
                for _ in w[1:]:
                    fid = id(_[0])
                    if fid not in _F:
                        _F[fid] = (len(_F),_[0])
                    t('(__frag_%s__, %r)' % (_F[fid][0],_[1]))
                return '\x20\x20%s([%s, %s]),' % (w.__class__.__name__, w[0], ', '.join(t.__self__))
            for _ in P2.frags:
                _S(_showWord(_))
            print('from reportlab.platypus.paragraph import _HSFrag, _SplitFragHS, _SplitFragHY, _SplitFrag, _getFragWords\nfrom reportlab.platypus.paraparser import ParaFrag\nfrom reportlab.lib.colors import Color')
            print('\n'.join(('__frag_%s__ = %r' % _ for _ in sorted(_F.values()))))
            print('%s=[\n%s\x20\x20]' % (processed_frags,'\n'.join(_S.__self__)))
            print('print(_getFragWords(processed_frags))')


    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    import sys
    TESTS = sys.argv[1:]
    if TESTS==[]: TESTS=['4']
    def flagged(i,TESTS=TESTS):
        return 'all' in TESTS or '*' in TESTS or str(i) in TESTS

    styleSheet = getSampleStyleSheet()
    B = styleSheet['BodyText']
    style = ParagraphStyle("discussiontext", parent=B)
    style.fontName= 'Helvetica'
    if flagged(1):
        text='''The <font name=courier color=green>CMYK</font> or subtractive method follows the way a printer
mixes three pigments (cyan, magenta, and yellow) to form colors.
Because mixing chemicals is more difficult than combining light there
is a fourth parameter for darkness.  For example a chemical
combination of the <font name=courier color=green>CMY</font> pigments generally never makes a perfect
black -- instead producing a muddy color -- so, to get black printers
don't use the <font name=courier color=green>CMY</font> pigments but use a direct black ink.  Because
<font name=courier color=green>CMYK</font> maps more directly to the way printer hardware works it may
be the case that &amp;| &amp; | colors specified in <font name=courier color=green>CMYK</font> will provide better fidelity
and better control when printed.
'''
        P=Paragraph(text,style)
        dumpParagraphFrags(P)
        aW, aH = 456.0, 42.8
        w,h = P.wrap(aW, aH)
        dumpParagraphLines(P)
        S = P.split(aW,aH)
        for s in S:
            s.wrap(aW,aH)
            dumpParagraphLines(s)
            aH = 500

    if flagged(2):
        P=Paragraph("""Price<super><font color="red">*</font></super>""", styleSheet['Normal'])
        dumpParagraphFrags(P)
        w,h = P.wrap(24, 200)
        dumpParagraphLines(P)

    if flagged(3):
        text = """Dieses Kapitel bietet eine schnelle <b><font color=red>Programme :: starten</font></b>
<onDraw name=myIndex label="Programme :: starten">
<b><font color=red>Eingabeaufforderung :: (&gt;&gt;&gt;)</font></b>
<onDraw name=myIndex label="Eingabeaufforderung :: (&gt;&gt;&gt;)">
<b><font color=red>&gt;&gt;&gt; (Eingabeaufforderung)</font></b>
<onDraw name=myIndex label="&gt;&gt;&gt; (Eingabeaufforderung)">
Einf&#xfc;hrung in Python <b><font color=red>Python :: Einf&#xfc;hrung</font></b>
<onDraw name=myIndex label="Python :: Einf&#xfc;hrung">.
Das Ziel ist, die grundlegenden Eigenschaften von Python darzustellen, ohne
sich zu sehr in speziellen Regeln oder Details zu verstricken. Dazu behandelt
dieses Kapitel kurz die wesentlichen Konzepte wie Variablen, Ausdr&#xfc;cke,
Kontrollfluss, Funktionen sowie Ein- und Ausgabe. Es erhebt nicht den Anspruch,
umfassend zu sein."""
        P=Paragraph(text, styleSheet['Code'])
        dumpParagraphFrags(P)
        w,h = P.wrap(6*72, 9.7*72)
        dumpParagraphLines(P)

    if flagged(4):
        text='''Die eingebaute Funktion <font name=Courier>range(i, j [, stride])</font><onDraw name=myIndex label="eingebaute Funktionen::range()"><onDraw name=myIndex label="range() (Funktion)"><onDraw name=myIndex label="Funktionen::range()"> erzeugt eine Liste von Ganzzahlen und f&#xfc;llt sie mit Werten <font name=Courier>k</font>, f&#xfc;r die gilt: <font name=Courier>i &lt;= k &lt; j</font>. Man kann auch eine optionale Schrittweite angeben. Die eingebaute Funktion <font name=Courier>range()</font><onDraw name=myIndex label="eingebaute Funktionen::range()"><onDraw name=myIndex label="range() (Funktion)"><onDraw name=myIndex label="Funktionen::range()"> erf&#xfc;llt einen &#xe4;hnlichen Zweck, gibt aber eine unver&#xe4;nderliche Sequenz vom Typ <font name=Courier>RangeType</font><onDraw name=myIndex label="RangeType"> zur&#xfc;ck. Anstatt alle Werte in der Liste abzuspeichern, berechnet diese Liste ihre Werte, wann immer sie angefordert werden. Das ist sehr viel speicherschonender, wenn mit sehr langen Listen von Ganzzahlen gearbeitet wird. <font name=Courier>RangeType</font> kennt eine einzige Methode, <font name=Courier>s.tolist()</font><onDraw name=myIndex label="RangeType::tolist() (Methode)"><onDraw name=myIndex label="s.tolist() (Methode)"><onDraw name=myIndex label="Methoden::s.tolist()">, die seine Werte in eine Liste umwandelt.'''
        aW = 420
        aH = 64.4
        P=Paragraph(text, B)
        dumpParagraphFrags(P)
        w,h = P.wrap(aW,aH)
        print('After initial wrap',w,h)
        dumpParagraphLines(P)
        S = P.split(aW,aH)
        dumpParagraphFrags(S[0])
        w0,h0 = S[0].wrap(aW,aH)
        print('After split wrap',w0,h0)
        dumpParagraphLines(S[0])

    if flagged(5):
        text = '<para> %s <![CDATA[</font></b>& %s < >]]></para>' % (chr(163),chr(163))
        P=Paragraph(text, styleSheet['Code'])
        dumpParagraphFrags(P)
        w,h = P.wrap(6*72, 9.7*72)
        dumpParagraphLines(P)

    if flagged(6):
        for text in ['''Here comes <FONT FACE="Helvetica" SIZE="14pt">Helvetica 14</FONT> with <STRONG>strong</STRONG> <EM>emphasis</EM>.''',
                     '''Here comes <font face="Helvetica" size="14pt">Helvetica 14</font> with <Strong>strong</Strong> <em>emphasis</em>.''',
                     '''Here comes <font face="Courier" size="3cm">Courier 3cm</font> and normal again.''',
                     ]:
            P=Paragraph(text, styleSheet['Normal'], caseSensitive=0)
            dumpParagraphFrags(P)
            w,h = P.wrap(6*72, 9.7*72)
            dumpParagraphLines(P)

    if flagged(7):
        text = """<para align="CENTER" fontSize="24" leading="30"><b>Generated by:</b>Dilbert</para>"""
        P=Paragraph(text, styleSheet['Code'])
        dumpParagraphFrags(P)
        w,h = P.wrap(6*72, 9.7*72)
        dumpParagraphLines(P)

    if flagged(8):
        text ="""- bullet 0<br/>- bullet 1<br/>- bullet 2<br/>- bullet 3<br/>- bullet 4<br/>- bullet 5"""
        P=Paragraph(text, styleSheet['Normal'])
        dumpParagraphFrags(P)
        w,h = P.wrap(6*72, 9.7*72)
        dumpParagraphLines(P)
        S = P.split(6*72,h/2.0)
        print(len(S))
        dumpParagraphFrags(S[0])
        dumpParagraphLines(S[0])
        S[1].wrap(6*72, 9.7*72)
        dumpParagraphFrags(S[1])
        dumpParagraphLines(S[1])


    if flagged(9):
        text="""Furthermore, the fundamental error of
regarding <img src="../docs/images/testimg.gif" width="3" height="7"/> functional notions as
categorial delimits a general
convention regarding the forms of the<br/>
grammar. I suggested that these results
would follow from the assumption that"""
        P=Paragraph(text,ParagraphStyle('aaa',parent=styleSheet['Normal'],align=TA_JUSTIFY))
        dumpParagraphFrags(P)
        w,h = P.wrap(6*cm-12, 9.7*72)
        dumpParagraphLines(P)

    if flagged(10):
        text="""a b c\xc2\xa0d e f"""
        P=Paragraph(text,ParagraphStyle('aaa',parent=styleSheet['Normal'],align=TA_JUSTIFY))
        dumpParagraphFrags(P)
        w,h = P.wrap(6*cm-12, 9.7*72)
        dumpParagraphLines(P)

    if flagged(11):
        text="""This page tests out a number of attributes of the <b>paraStyle</b><onDraw name="_indexAdd" label="paraStyle"/> tag.
This paragraph is in a style we have called "style1". It should be a normal <onDraw name="_indexAdd" label="normal"/> paragraph, set in Courier 12 pt.
It should be a normal<onDraw name="_indexAdd" label="normal"/> paragraph, set in Courier (not bold).
It should be a normal<onDraw name="_indexAdd" label="normal"/> paragraph, set in Courier 12 pt."""
        P=Paragraph(text,style=ParagraphStyle('style1',fontName="Courier",fontSize=10))
        dumpParagraphFrags(P)
        w,h = P.wrap(6.27*72-12,10000)
        dumpParagraphLines(P)
