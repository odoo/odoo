__all__ = (
        'setFont',
        'pathNumTrunc',
        'processGlyph',
        'text2PathDescription',
        'text2Path',
        'RenderPMError',
        )
from . _renderPM import makeT1Font
from reportlab.pdfbase.pdfmetrics import getFont, unicode2T1
from reportlab.lib.utils import open_and_read, isBytes, rl_exec
from .shapes import _baseGFontName, _PATH_OP_ARG_COUNT, _PATH_OP_NAMES, definePath
from sys import exc_info

class RenderPMError(Exception):
    pass

def _errorDump(fontName, fontSize):
    s1, s2 = list(map(str,exc_info()[:2]))
    from reportlab import rl_config
    if rl_config.verbose>=2:
        import os
        _ = os.path.join(os.path.dirname(rl_config.__file__),'fonts')
        print('!!!!! %s: %s' % (_,os.listdir(_)))
        for _ in ('T1SearchPath','TTFSearchPath'):
            print('!!!!! rl_config.%s = %s' % (_,repr(getattr(rl_config,_))))
    code = 'raise RenderPMError("Error in setFont(%s,%s) missing the T1 files?\\nOriginally %s: %s")' % (repr(fontName),repr(fontSize),s1,s2)
    code += ' from None'
    rl_exec(code,dict(RenderPMError=RenderPMError))

def setFont(gs,fontName,fontSize):
    try:
        gs.setFont(fontName,fontSize)
    except ValueError as e:
        if not e.args[0].endswith("Can't find font!"):
            _errorDump(fontName,fontSize)
        #here's where we try to add a font to the canvas
        try:
            f = getFont(fontName)
            makeT1Font(fontName,f.face.findT1File(),f.encoding.vector,open_and_read)
        except:
            _errorDump(fontName,fontSize)
        gs.setFont(fontName,fontSize)

def pathNumTrunc(n):
    if int(n)==n: return int(n)
    return round(n,5)

def processGlyph(G, truncate=1, pathReverse=0):
    O = []
    P = []
    R_append = [].append
    if G and len(G)==1 and G[0][0]=='lineTo':
        G = (('moveToClosed',)+G[0][1:],)+G #hack fix for some errors
    for g in (G or ())+(('end',),):
        op = g[0]
        if O and op in ['moveTo', 'moveToClosed','end']:
            if O[0]=='moveToClosed':
                del O[0]
                if pathReverse:
                    P[1::2],P[0::2] = P[0::2],P[1::2]   #exchange x and y
                    P.reverse()
                    O.reverse()
                O.insert(0,'moveTo')
                O.append('closePath')
            i = 0
            if truncate: P = list(map(pathNumTrunc,P))
            for o in O:
                j = i + _PATH_OP_ARG_COUNT[_PATH_OP_NAMES.index(o)]
                R_append((o,)+ tuple(P[i:j]))
                i = j
            O = []
            P = []
        O.append(op)
        P.extend(g[1:])
    return R_append.__self__

def text2PathDescription(text, x=0, y=0, fontName=_baseGFontName, fontSize=1000,
                            anchor='start', truncate=1, pathReverse=0, gs=None):
    font = getFont(fontName)
    if font._multiByte and not font._dynamicFont:
        raise ValueError("text2PathDescription doesn't support multi byte fonts like %r" % fontName)
    P_extend = [].extend
    if not anchor=='start':
        textLen = stringWidth(text, fontName, fontSize)
        if anchor=='end':
            x = x-textLen
        elif anchor=='middle':
            x = x - textLen/2.
    if gs is None:
        from ._renderPM import gstate
        gs = gstate(1,1)
    setFont(gs,fontName,fontSize)
    if font._dynamicFont:
        for g in gs._stringPath(text,x,y):
            P_extend(processGlyph(g,truncate=truncate,pathReverse=pathReverse))
    else:
        if isBytes(text):
            try:
                text = text.decode('utf8')
            except UnicodeDecodeError as e:
                i,j = e.args[2:4]
                raise UnicodeDecodeError(*(e.args[:4]+('%s\n%s-->%s<--%s' % (e.args[4],text[max(i-10,0):i],text[i:j],text[j:j+10]),)))
        fc = font
        FT = unicode2T1(text,[font]+font.substitutionFonts)
        nm1 = len(FT)-1
        for i, (f, t) in enumerate(FT):
            if f!=fc:
                setFont(gs,f.fontName,fontSize)
                fc = f
            for g in gs._stringPath(t,x,y):
                P_extend(processGlyph(g,truncate=truncate,pathReverse=pathReverse))
            if i!=nm1:
                x += f.stringWidth(t.decode(f.encName), fontSize)
    return P_extend.__self__

def text2Path(text, x=0, y=0, fontName=_baseGFontName, fontSize=1000,
                anchor='start', truncate=1, pathReverse=0, gs=None, **kwds):
    return definePath(text2PathDescription(text,x=x,y=y,fontName=fontName,
                    fontSize=fontSize,anchor=anchor,truncate=truncate,pathReverse=pathReverse, gs=gs),**kwds)
