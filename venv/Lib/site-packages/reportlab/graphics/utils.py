__all__ = (
        'setFont',
        'pathNumTrunc',
        'processGlyph',
        'text2PathDescription',
        'text2Path',
        'RenderPMError',
        )
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
        from _rl_renderPM import makeT1Font
        try:
            f = getFont(fontName)
            makeT1Font(fontName,f.face.findT1File(),f.encoding.vector,open_and_read)
        except:
            _errorDump(fontName,fontSize)
        gs.setFont(fontName,fontSize)

def pathNumTrunc(n):
    if int(n)==n: return int(n)
    return round(n,5)


def __makeTextPathsCode__(tp=None, _TP = ('freetype','_renderPM')):
    from reportlab.rl_config import textPaths, renderPMBackend
    if tp is not None: textPaths = tp
    if textPaths=='backend':
        tp = 'freetype' if renderPMBackend!='rlPyCairo' else '_renderPM'
    elif textPaths in _TP:
        tp = textPaths
    else:
        raise ValueError(f"textPaths={textPaths!r} should be one of 'backend', 'freetype' or '_renderPM')")
    TP = (tp,) + tuple((_ for _ in _TP if _!=tp))
    for tp in TP:
        if tp=='freetype':
            try:
                import freetype
            except ImportError:
                continue
            import io
            class FTTextPath:
                ftLFlags = freetype.FT_LOAD_DEFAULT | freetype.FT_LOAD_NO_SCALE | freetype.FT_LOAD_NO_BITMAP
                def __init__(self):
                    self.faces = {}

                def setFont(self,fontName):
                    if fontName not in self.faces:
                        font = getFont(fontName)
                        if not font:
                            raise ValueError(f'font {fontName!r} has not been registered')
                        if font._dynamicFont:
                            path_or_stream = font.face._ttf_data
                            #path_or_stream = getattr(font,'_ttfont_data',None)
                            #if not path_or_stream:
                                #path_or_stream = font._ttfont_data
                            path_or_stream = io.BytesIO(path_or_stream)
                        else:
                            path_or_stream = getattr(font.face,'pfbFileName',None)
                            if not path_or_stream:
                                path_or_stream = font.face.findT1File()
                        face = freetype.Face(path_or_stream)
                        self.faces[fontName] = (face,font) 
                    return self.faces[fontName]

                def _text2Path(self, text, x=0, y=0, fontName=_baseGFontName, fontSize=1000, **kwds):
                    face, font = self.setFont(fontName)
                    scale = fontSize/face.units_per_EM  #font scaling
                    __dx__ = x/scale
                    __dy__ = y/scale
                    P = []
                    S = []
                    P_append = P.append
                    truncate = kwds.pop('truncate',0)
                    if truncate:
                        xpt = lambda x: pathNumTrunc(scale*(x+__dx__))
                        ypt = lambda y: pathNumTrunc(scale*(y+__dy__))
                    else:
                        xpt = lambda x: scale*(x + __dx__)
                        ypt = lambda y: scale*(y + __dy__)

                    def move_to(a, ctx):
                        if P: P_append(('closePath',))
                        P_append(('moveTo',xpt(a.x),ypt(a.y)))

                    def line_to(a, ctx):
                        P_append(('lineTo',xpt(a.x),ypt(a.y)))

                    def conic_to(a, b, ctx):
                        '''using the cubic equivalent'''
                        x0,y0 = P[-1][-2:] if P else (a.x, a.y)
                        x1 = xpt(a.x)
                        y1 = ypt(a.y)
                        x2 = xpt(b.x)
                        y2 = ypt(b.y)
                        P_append(('curveTo',x0+((x1-x0)*2)/3,y0+((y1-y0)*2)/3,x1+(x2-x1)/3,y1+(y2-y1)/3,x2,y2))

                    def cubic_to(a, b, c, ctx):
                        P_append(('curveTo',xpt(a.x),ypt(a.y),xpt(b.x),ypt(b.y),xpt(c.x),ypt(c.y)))

                    lineHeight = fontSize*1.2/scale
                    ftLFlags = self.ftLFlags
                    for c in text:
                        if c=='\n':
                            __dx__ = 0
                            __dy__ -= lineHeight
                            continue
                        face.load_char(c, ftLFlags)
                        face.glyph.outline.decompose(self, move_to=move_to, line_to=line_to, conic_to=conic_to, cubic_to=cubic_to)
                        __dx__ = __dx__ + face.glyph.metrics.horiAdvance
                    if P: P_append(('closePath',))
                    return P

            def text2PathDescription(text, x=0, y=0, fontName=_baseGFontName, fontSize=1000,
                                        anchor='start', truncate=1, pathReverse=0, gs=None):
                '''freetype text2PathDescription(text, x=0, y=0, fontName='fontname',
                                    fontSize=1000, font = 'fontName',
                                    anchor='start', truncate=1, pathReverse=0, gs=None)
                '''
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
                    gs = FTTextPath()
                if font._dynamicFont:
                    P_extend(gs._text2Path(text,x=x,y=y,fontName=fontName,fontSize=fontSize, truncate=truncate,pathReverse=pathReverse))
                else:
                    if isBytes(text):
                        try:
                            text = text.decode('utf8')
                        except UnicodeDecodeError as e:
                            i,j = e.args[2:4]
                            raise UnicodeDecodeError(*(e.args[:4]+('%s\n%s-->%s<--%s' % (e.args[4],text[max(i-10,0):i],text[i:j],text[j:j+10]),)))
                    FT = unicode2T1(text,[font]+font.substitutionFonts)
                    nm1 = len(FT)-1
                    for i, (f, t) in enumerate(FT):
                        if isinstance(t,bytes): t = t.decode(f.encName)
                        P_extend(gs._text2Path(t,x=x,y=y,fontName=f.fontName,fontSize=fontSize, truncate=truncate,pathReverse=pathReverse))
                        if i!=nm1:
                            x += f.stringWidth(t, fontSize)
                return P_extend.__self__
            return dict(text2PathDescription=text2PathDescription,FTTextPath=FTTextPath)
        elif tp=='_renderPM':
            try:
                import _rl_renderPM
            except ImportError:
                continue

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
                '''_renderPM text2PathDescription(text, x=0, y=0, fontName='fontname',
                                    fontSize=1000, font = 'fontName',
                                    anchor='start', truncate=1, pathReverse=0, gs=None)
                '''
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
                    from _rl_renderPM import gstate
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
            return dict(text2PathDescription=text2PathDescription,processGlyph=processGlyph,setFont=setFont)
    else:
        def _(*args,**kwds):
            raise RuntimeError(f'''This installation of reportLab has neither PYCAIRO or RENDERPM extras installed.
It cannot create paths from text.
Could not create text2PathDescription for using backends from {TP!a}''')
        return dict(processGlyph=_,setFont=_,FTTextPath=_,text2PathDescription=_)

globals().update(__makeTextPathsCode__())

def text2Path(text, x=0, y=0, fontName=_baseGFontName, fontSize=1000,
                anchor='start', truncate=1, pathReverse=0, gs=None, **kwds):
    t2pd = kwds.pop('text2PathDescription',text2PathDescription)
    return definePath(t2pd(text,x=x,y=y,fontName=fontName,
                    fontSize=fontSize,anchor=anchor,truncate=truncate,pathReverse=pathReverse, gs=gs),**kwds)
