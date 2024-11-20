#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/graphics/renderPS.py
__version__='3.3.0'
__doc__="""Render drawing objects in Postscript"""

import math
from io import BytesIO, StringIO
from reportlab.pdfbase.pdfmetrics import getFont, stringWidth, unicode2T1 # for font info
from reportlab.lib.utils import asBytes, char2int, rawBytes, asNative, isUnicode
from reportlab.lib.rl_accel import fp_str
from reportlab.graphics.renderbase import Renderer, getStateDelta, renderScaledDrawing
from reportlab.graphics.shapes import STATE_DEFAULTS
from reportlab import rl_config
from reportlab.pdfgen.canvas import FILL_EVEN_ODD

_ESCAPEDICT={}
for c in range(256):
    if c<32 or c>=127:
        _ESCAPEDICT[c]= '\\%03o' % c
    elif c in (ord('\\'),ord('('),ord(')')):
        _ESCAPEDICT[c] = '\\'+chr(c)
    else:
        _ESCAPEDICT[c] = chr(c)
del c

def _escape_and_limit(s):
    s = asBytes(s)
    R = []
    aR = R.append
    n = 0
    for c in s:
        c = _ESCAPEDICT[char2int(c)]
        aR(c)
        n += len(c)
        if n>=200:
            n = 0
            aR('\\\n')
    return ''.join(R)

# we need to create encoding vectors for each font we use, or they will
 # come out in Adobe's old StandardEncoding, which NOBODY uses.
PS_WinAnsiEncoding="""
/RE { %def
  findfont begin
  currentdict dup length dict begin
 { %forall
   1 index /FID ne { def } { pop pop } ifelse
 } forall
 /FontName exch def dup length 0 ne { %if
   /Encoding Encoding 256 array copy def
   0 exch { %forall
     dup type /nametype eq { %ifelse
       Encoding 2 index 2 index put
       pop 1 add
     }{ %else
       exch pop
     } ifelse
   } forall
 } if pop
  currentdict dup end end
  /FontName get exch definefont pop
} bind def

/WinAnsiEncoding [
  39/quotesingle 96/grave 128/euro 130/quotesinglbase/florin/quotedblbase
  /ellipsis/dagger/daggerdbl/circumflex/perthousand
  /Scaron/guilsinglleft/OE 145/quoteleft/quoteright
  /quotedblleft/quotedblright/bullet/endash/emdash
  /tilde/trademark/scaron/guilsinglright/oe/dotlessi
  159/Ydieresis 164/currency 166/brokenbar 168/dieresis/copyright
  /ordfeminine 172/logicalnot 174/registered/macron/ring
  177/plusminus/twosuperior/threesuperior/acute/mu
  183/periodcentered/cedilla/onesuperior/ordmasculine
  188/onequarter/onehalf/threequarters 192/Agrave/Aacute
  /Acircumflex/Atilde/Adieresis/Aring/AE/Ccedilla
  /Egrave/Eacute/Ecircumflex/Edieresis/Igrave/Iacute
  /Icircumflex/Idieresis/Eth/Ntilde/Ograve/Oacute
  /Ocircumflex/Otilde/Odieresis/multiply/Oslash
  /Ugrave/Uacute/Ucircumflex/Udieresis/Yacute/Thorn
  /germandbls/agrave/aacute/acircumflex/atilde/adieresis
  /aring/ae/ccedilla/egrave/eacute/ecircumflex
  /edieresis/igrave/iacute/icircumflex/idieresis
  /eth/ntilde/ograve/oacute/ocircumflex/otilde
  /odieresis/divide/oslash/ugrave/uacute/ucircumflex
  /udieresis/yacute/thorn/ydieresis
] def
"""

class PSCanvas:
    def __init__(self,size=(300,300), PostScriptLevel=2):
        self.width, self.height = size
        xtraState = []
        self._xtraState_push = xtraState.append
        self._xtraState_pop = xtraState.pop
        self.comments = 0
        self.code = []
        self.code_append = self.code.append
        self._sep = '\n'
        self._strokeColor = self._fillColor = self._lineWidth = \
            self._font = self._fontSize = self._lineCap = \
            self._lineJoin = self._color = None

        self._fontsUsed =   [] # track them as we go
        self.setFont(STATE_DEFAULTS['fontName'],STATE_DEFAULTS['fontSize'])
        self.setStrokeColor(STATE_DEFAULTS['strokeColor'])
        self.setLineCap(2)
        self.setLineJoin(0)
        self.setLineWidth(1)
        self.PostScriptLevel=PostScriptLevel
        self._fillMode = FILL_EVEN_ODD

    def comment(self,msg):
        if self.comments: self.code_append('%'+msg)

    def drawImage(self, image, x1,y1, width=None,height=None): # Postscript Level2 version
        # select between postscript level 1 or level 2
        if self.PostScriptLevel==1:
            self._drawImageLevel1(image, x1,y1, width, height)
        elif self.PostScriptLevel==2:
            self._drawImageLevel2(image, x1, y1, width, height)
        else :
            raise ValueError('Unsupported Postscript Level %s' % self.PostScriptLevel)

    def clear(self):
        self.code_append('showpage') # ugh, this makes no sense oh well.

    def _t1_re_encode(self):
        if not self._fontsUsed: return
        # for each font used, reencode the vectors
        C = []
        for fontName in self._fontsUsed:
            fontObj = getFont(fontName)
            if not fontObj._dynamicFont and fontObj.encName=='WinAnsiEncoding':
                C.append('WinAnsiEncoding /%s /%s RE' % (fontName, fontName))
        if C:
            C.insert(0,PS_WinAnsiEncoding)
            self.code.insert(1, self._sep.join(C))

    def save(self,f=None):
        if not hasattr(f,'write'):
            _f = open(f,'wb')
        else:
            _f = f
        if self.code[-1]!='showpage': self.clear()
        self.code.insert(0,'''\
%%!PS-Adobe-3.0 EPSF-3.0
%%%%BoundingBox: 0 0 %d %d
%%%% Initialization:
/m {moveto} bind def
/l {lineto} bind def
/c {curveto} bind def
''' % (self.width,self.height))

        self._t1_re_encode()
        _f.write(rawBytes(self._sep.join(self.code)))
        if _f is not f:
            _f.close()
            from reportlab.lib.utils import markfilename
            markfilename(f,creatorcode='XPR3',filetype='EPSF')

    def saveState(self):
        self._xtraState_push((self._fontCodeLoc,))
        self.code_append('gsave')

    def restoreState(self):
        self.code_append('grestore')
        self._fontCodeLoc, = self._xtraState_pop()

    def stringWidth(self, s, font=None, fontSize=None):
        """Return the logical width of the string if it were drawn
        in the current font (defaults to self.font)."""
        font = font or self._font
        fontSize = fontSize or self._fontSize
        return stringWidth(s, font, fontSize)

    def setLineCap(self,v):
        if self._lineCap!=v:
            self._lineCap = v
            self.code_append('%d setlinecap'%v)

    def setLineJoin(self,v):
        if self._lineJoin!=v:
            self._lineJoin = v
            self.code_append('%d setlinejoin'%v)

    def setDash(self, array=[], phase=0):
        """Two notations.  pass two numbers, or an array and phase"""
        # copied and modified from reportlab.canvas
        psoperation = "setdash"
        if isinstance(array,(float,int)):
            self.code_append('[%s %s] 0 %s' % (array, phase, psoperation))
        elif isinstance(array,(tuple,list)):
            assert phase >= 0, "phase is a length in user space"
            textarray = ' '.join(map(str, array))
            self.code_append('[%s] %s %s' % (textarray, phase, psoperation))

    def setStrokeColor(self, color):
        self._strokeColor = color
        self.setColor(color)

    def setColor(self, color):
        if self._color!=color:
            self._color = color
            if color:
                if hasattr(color, "cyan"):
                    self.code_append('%s setcmykcolor' % fp_str(color.cyan, color.magenta, color.yellow, color.black))
                else:
                    self.code_append('%s setrgbcolor' % fp_str(color.red, color.green, color.blue))

    def setFillColor(self, color):
        self._fillColor = color
        self.setColor(color)

    def setFillMode(self, v):
        self._fillMode = v

    def setLineWidth(self, width):
        if width != self._lineWidth:
            self._lineWidth = width
            self.code_append('%s setlinewidth' % width)

    def setFont(self,font,fontSize,leading=None):
        if self._font!=font or self._fontSize!=fontSize:
            self._fontCodeLoc = len(self.code)
            self._font = font
            self._fontSize = fontSize
            self.code_append('')

    def line(self, x1, y1, x2, y2):
        if self._strokeColor != None:
            self.setColor(self._strokeColor)
            self.code_append('%s m %s l stroke' % (fp_str(x1, y1), fp_str(x2, y2)))

    def _escape(self, s):
        '''
        return a copy of string s with special characters in postscript strings
        escaped with backslashes.
        '''
        try:
            return _escape_and_limit(s)
        except:
            raise ValueError("cannot escape %s" % ascii(s))

    def _textOut(self, x, y, s, textRenderMode=0):
        if textRenderMode==3: return
        xy = fp_str(x,y)
        s = self._escape(s)

        if textRenderMode==0: #the standard case
            self.setColor(self._fillColor)
            self.code_append('%s m (%s) show ' % (xy,s))
            return

        fill = textRenderMode==0 or textRenderMode==2 or textRenderMode==4 or textRenderMode==6
        stroke = textRenderMode==1 or textRenderMode==2 or textRenderMode==5 or textRenderMode==6
        addToClip = textRenderMode>=4
        if fill and stroke:
            if self._fillColor is None:
                op = ''
            else:
                op = 'fill '
                self.setColor(self._fillColor)
            self.code_append('%s m (%s) true charpath gsave %s' % (xy,s,op))
            self.code_append('grestore ')
            if self._strokeColor is not None:
                self.setColor(self._strokeColor)
                self.code_append('stroke ')
        else: #can only be stroke alone
            self.setColor(self._strokeColor)
            self.code_append('%s m (%s) true charpath stroke ' % (xy,s))

    def _issueT1String(self,fontObj,x,y,s, textRenderMode=0):
        fc = fontObj
        code_append = self.code_append
        fontSize = self._fontSize
        fontsUsed = self._fontsUsed
        escape = self._escape
        if not isUnicode(s):
            try:
                s = s.decode('utf8')
            except UnicodeDecodeError as e:
                i,j = e.args[2:4]
                raise UnicodeDecodeError(*(e.args[:4]+('%s\n%s-->%s<--%s' % (e.args[4],s[i-10:i],s[i:j],s[j:j+10]),)))

        for f, t in unicode2T1(s,[fontObj]+fontObj.substitutionFonts):
            if f!=fc:
                psName = asNative(f.face.name)
                code_append('(%s) findfont %s scalefont setfont' % (psName,fp_str(fontSize)))
                if psName not in fontsUsed:
                    fontsUsed.append(psName)
                fc = f
            self._textOut(x,y,t,textRenderMode)
            x += f.stringWidth(t.decode(f.encName),fontSize)
        if fontObj!=fc:
            self._font = None
            self.setFont(fontObj.face.name,fontSize)

    def drawString(self, x, y, s, angle=0, text_anchor='left', textRenderMode=0):
        needFill = textRenderMode in (0,2,4,6) 
        needStroke = textRenderMode in (1,2,5,6) 
        if needFill or needStroke:
            if text_anchor!='left':
                textLen = stringWidth(s, self._font,self._fontSize)
                if text_anchor=='end':
                    x -= textLen
                elif text_anchor=='middle':
                    x -= textLen/2.
                elif text_anchor=='numeric':
                    x -= numericXShift(text_anchor,s,textLen,self._font,self._fontSize)
            fontObj = getFont(self._font)
            if not self.code[self._fontCodeLoc]:
                psName = asNative(fontObj.face.name)
                self.code[self._fontCodeLoc]='(%s) findfont %s scalefont setfont' % (psName,fp_str(self._fontSize))
                if psName not in self._fontsUsed:
                    self._fontsUsed.append(psName)
            if angle!=0:
                self.code_append('gsave %s translate %s rotate' % (fp_str(x,y),fp_str(angle)))
                x = y = 0
            oldColor = self._color
            if fontObj._dynamicFont:
                self._textOut(x, y, s, textRenderMode=textRenderMode)
            else:
                self._issueT1String(fontObj,x,y,s, textRenderMode=textRenderMode)
            self.setColor(oldColor)
            if angle!=0:
                self.code_append('grestore')

    def drawCentredString(self, x, y, text, text_anchor='middle', textRenderMode=0):
            self.drawString(x,y,text, text_anchor=text_anchor, textRenderMode=textRenderMode)

    def drawRightString(self, text, x, y, text_anchor='end', textRenderMode=0):
        self.drawString(text,x,y,text_anchor=text_anchor, textRenderMode=textRenderMode)

    def drawCurve(self, x1, y1, x2, y2, x3, y3, x4, y4, closed=0):
        codeline = '%s m %s curveto'
        data = (fp_str(x1, y1), fp_str(x2, y2, x3, y3, x4, y4))
        if self._fillColor != None:
            self.setColor(self._fillColor)
            self.code_append((codeline % data) + ' eofill')
        if self._strokeColor != None:
            self.setColor(self._strokeColor)
            self.code_append((codeline % data)
                            + ((closed and ' closepath') or '')
                            + ' stroke')

    ########################################################################################

    def rect(self, x1,y1, x2,y2, stroke=1, fill=1):
        "Draw a rectangle between x1,y1, and x2,y2"
        # Path is drawn in counter-clockwise direction"

        x1, x2 = min(x1,x2), max(x1, x2) # from piddle.py
        y1, y2 = min(y1,y2), max(y1, y2)
        self.polygon(((x1,y1),(x2,y1),(x2,y2),(x1,y2)), closed=1, stroke=stroke, fill = fill)

    def roundRect(self, x1,y1, x2,y2, rx=8, ry=8):
        """Draw a rounded rectangle between x1,y1, and x2,y2,
        with corners inset as ellipses with x radius rx and y radius ry.
        These should have x1<x2, y1<y2, rx>0, and ry>0."""
        # Path is drawn in counter-clockwise direction

        x1, x2 = min(x1,x2), max(x1, x2) # from piddle.py
        y1, y2 = min(y1,y2), max(y1, y2)

        # Note: arcto command draws a line from current point to beginning of arc
        # save current matrix, translate to center of ellipse, scale by rx ry, and draw
        # a circle of unit radius in counterclockwise dir, return to original matrix
        # arguments are (cx, cy, rx, ry, startAngle, endAngle)
        ellipsePath = 'matrix currentmatrix %s %s translate %s %s scale 0 0 1 %s %s arc setmatrix'

        # choice between newpath and moveTo beginning of arc
        # go with newpath for precision, does this violate any assumptions in code???
        rr = ['newpath'] # Round Rect code path
        a = rr.append
        # upper left corner ellipse is first
        a(ellipsePath % (x1+rx, y1+ry, rx, -ry, 90, 180))
        a(ellipsePath % (x1+rx, y2-ry, rx, -ry, 180, 270))
        a(ellipsePath % (x2-rx, y2-ry, rx, -ry, 270, 360))
        a(ellipsePath % (x2-rx, y1+ry, rx, -ry, 0,  90) )
        a('closepath')

        self._fillAndStroke(rr)

    def ellipse(self, x1,y1, x2,y2):
        """Draw an orthogonal ellipse inscribed within the rectangle x1,y1,x2,y2.
        These should have x1<x2 and y1<y2."""
        #Just invoke drawArc to actually draw the ellipse
        self.drawArc(x1,y1, x2,y2)

    def circle(self, xc, yc, r):
        self.ellipse(xc-r,yc-r, xc+r,yc+r)

    def drawArc(self, x1,y1, x2,y2, startAng=0, extent=360, fromcenter=0):
        """Draw a partial ellipse inscribed within the rectangle x1,y1,x2,y2,
        starting at startAng degrees and covering extent degrees.   Angles
        start with 0 to the right (+x) and increase counter-clockwise.
        These should have x1<x2 and y1<y2."""
        #calculate centre of ellipse
        #print "x1,y1,x2,y2,startAng,extent,fromcenter", x1,y1,x2,y2,startAng,extent,fromcenter
        cx, cy = (x1+x2)/2.0, (y1+y2)/2.0
        rx, ry = (x2-x1)/2.0, (y2-y1)/2.0

        codeline = self._genArcCode(x1, y1, x2, y2, startAng, extent)

        startAngleRadians = math.pi*startAng/180.0
        extentRadians = math.pi*extent/180.0
        endAngleRadians = startAngleRadians + extentRadians

        codelineAppended = 0

        # fill portion

        if self._fillColor != None:
            self.setColor(self._fillColor)
            self.code_append(codeline)
            codelineAppended = 1
            if self._strokeColor!=None: self.code_append('gsave')
            self.lineTo(cx,cy)
            self.code_append('eofill')
            if self._strokeColor!=None: self.code_append('grestore')

        # stroke portion
        if self._strokeColor != None:
            # this is a bit hacked up.  There is certainly a better way...
            self.setColor(self._strokeColor)
            (startx, starty) = (cx+rx*math.cos(startAngleRadians), cy+ry*math.sin(startAngleRadians))
            if not codelineAppended:
                self.code_append(codeline)
            if fromcenter:
                # move to center
                self.lineTo(cx,cy)
                self.lineTo(startx, starty)
                self.code_append('closepath')
            self.code_append('stroke')

    def _genArcCode(self, x1, y1, x2, y2, startAng, extent):
        "Calculate the path for an arc inscribed in rectangle defined by (x1,y1),(x2,y2)"
        #calculate semi-minor and semi-major axes of ellipse
        xScale = abs((x2-x1)/2.0)
        yScale = abs((y2-y1)/2.0)
        #calculate centre of ellipse
        x, y = (x1+x2)/2.0, (y1+y2)/2.0

        codeline = 'matrix currentmatrix %s %s translate %s %s scale 0 0 1 %s %s %s setmatrix'

        if extent >= 0:
            arc='arc'
        else:
            arc='arcn'
        data = (x,y, xScale, yScale, startAng, startAng+extent, arc)

        return codeline % data

    def polygon(self, p, closed=0, stroke=1, fill=1):
        assert len(p) >= 2, 'Polygon must have 2 or more points'

        start = p[0]
        p = p[1:]

        poly = []
        a = poly.append
        a("%s m" % fp_str(start))
        for point in p:
            a("%s l" % fp_str(point))
        if closed:
            a("closepath")

        self._fillAndStroke(poly,stroke=stroke,fill=fill)

    def lines(self, lineList, color=None, width=None):
        if self._strokeColor != None:
            self._setColor(self._strokeColor)
            codeline = '%s m %s l stroke'
            for line in lineList:
                self.code_append(codeline % (fp_str(line[0]),fp_str(line[1])))

    def moveTo(self,x,y):
        self.code_append('%s m' % fp_str(x, y))

    def lineTo(self,x,y):
        self.code_append('%s l' % fp_str(x, y))

    def curveTo(self,x1,y1,x2,y2,x3,y3):
        self.code_append('%s c' % fp_str(x1,y1,x2,y2,x3,y3))

    def closePath(self):
        self.code_append('closepath')

    def polyLine(self, p):
        assert len(p) >= 1, 'Polyline must have 1 or more points'
        if self._strokeColor != None:
            self.setColor(self._strokeColor)
            self.moveTo(p[0][0], p[0][1])
            for t in p[1:]:
                self.lineTo(t[0], t[1])
            self.code_append('stroke')

    def drawFigure(self, partList, closed=0):
        figureCode = []
        a = figureCode.append
        first = 1

        for part in partList:
            op = part[0]
            args = list(part[1:])

            if op == figureLine:
                if first:
                    first = 0
                    a("%s m" % fp_str(args[:2]))
                else:
                    a("%s l" % fp_str(args[:2]))
                a("%s l" % fp_str(args[2:]))

            elif op == figureArc:
                first = 0
                x1,y1,x2,y2,startAngle,extent = args[:6]
                a(self._genArcCode(x1,y1,x2,y2,startAngle,extent))

            elif op == figureCurve:
                if first:
                    first = 0
                    a("%s m" % fp_str(args[:2]))
                else:
                    a("%s l" % fp_str(args[:2]))
                a("%s curveto" % fp_str(args[2:]))
            else:
                raise TypeError("unknown figure operator: "+op)

        if closed:
            a("closepath")
        self._fillAndStroke(figureCode)

    def _fillAndStroke(self,code,clip=0,fill=1,stroke=1,fillMode=None):
        fill = self._fillColor and fill
        stroke = self._strokeColor and stroke
        if fill or stroke or clip:
            self.code.extend(code)
            if fill:
                if fillMode is None:
                    fillMode = self._fillMode
                if stroke or clip: self.code_append("gsave")
                self.setColor(self._fillColor)
                self.code_append("eofill" if fillMode==FILL_EVEN_ODD else "fill")
                if stroke or clip: self.code_append("grestore")
            if stroke:
                if clip: self.code_append("gsave")
                self.setColor(self._strokeColor)
                self.code_append("stroke")
                if clip: self.code_append("grestore")
            if clip:
                self.code_append("clip")
                self.code_append("newpath")

    def translate(self,x,y):
        self.code_append('%s translate' % fp_str(x,y))

    def scale(self,x,y):
        self.code_append('%s scale' % fp_str(x,y))

    def transform(self,a,b,c,d,e,f):
        self.code_append('[%s] concat' % fp_str(a,b,c,d,e,f))

    def _drawTimeResize(self,w,h):
        '''if this is used we're probably in the wrong world'''
        self.width, self.height = w, h

    def _drawImageLevel1(self, image, x1, y1, width=None, height=None):
        # Postscript Level1 version available for fallback mode when Level2 doesn't work
        # For now let's start with 24 bit RGB images (following piddlePDF again)
        component_depth = 8
        myimage = image.convert('RGB')
        imgwidth, imgheight = myimage.size
        if not width:
            width = imgwidth
        if not height:
            height = imgheight
        #print 'Image size (%d, %d); Draw size (%d, %d)' % (imgwidth, imgheight, width, height)
        # now I need to tell postscript how big image is

        # "image operators assume that they receive sample data from
        # their data source in x-axis major index order.  The coordinate
        # of the lower-left corner of the first sample is (0,0), of the
        # second (1,0) and so on" -PS2 ref manual p. 215
        #
        # The ImageMatrix maps unit squre of user space to boundary of the source image
        #

        # The CurrentTransformationMatrix (CTM) maps the unit square of
        # user space to the rect...on the page that is to receive the
        # image. A common ImageMatrix is [width 0 0 -height 0 height]
        # (for a left to right, top to bottom image )

        # first let's map the user coordinates start at offset x1,y1 on page

        self.code.extend([
            'gsave',
            '%s %s translate' % (x1,y1), # need to start are lower left of image
            '%s %s scale' % (width,height),
            '/scanline %d 3 mul string def' % imgwidth  # scanline by multiples of image width
            ])

        # now push the dimensions and depth info onto the stack
        # and push the ImageMatrix to map the source to the target rectangle (see above)
        # finally specify source (PS2 pp. 225 ) and by exmample
        self.code.extend([
            '%s %s %s' % (imgwidth, imgheight, component_depth),
            '[%s %s %s %s %s %s]' % (imgwidth, 0, 0, -imgheight, 0, imgheight),
            '{ currentfile scanline readhexstring pop } false 3',
            'colorimage '
            ])

        # data source output--now we just need to deliver a hex encode
        # series of lines of the right overall size can follow
        # piddlePDF again
        rawimage = (myimage.tobytes if hasattr(myimage,'tobytes') else myimage.tostring)()
        hex_encoded = self._AsciiHexEncode(rawimage)

        # write in blocks of 78 chars per line
        outstream = StringIO(hex_encoded)

        dataline = outstream.read(78)
        while dataline != "":
            self.code_append(dataline)
            dataline= outstream.read(78)
        self.code_append('% end of image data') # for clarity
        self.code_append('grestore') # return coordinates to normal

    # end of drawImage
    def _AsciiHexEncode(self, input):  # also based on piddlePDF
        "Helper function used by images"
        output = StringIO()
        for char in asBytes(input):
            output.write('%02x' % char2int(char))
        return output.getvalue()

    def _drawImageLevel2(self, image, x1,y1, width=None,height=None): # Postscript Level2 version
        '''At present we're handling only PIL'''
        ### what sort of image are we to draw
        if image.mode=='L' :
            imBitsPerComponent = 8
            imNumComponents = 1
            myimage = image
        elif image.mode == '1':
            myimage = image.convert('L')
            imNumComponents = 1
            myimage = image
        else :
            myimage = image.convert('RGB')
            imNumComponents = 3
            imBitsPerComponent = 8

        imwidth, imheight = myimage.size
        if not width:
            width = imwidth
        if not height:
            height = imheight
        self.code.extend([
            'gsave',
            '%s %s translate' % (x1,y1), # need to start are lower left of image
            '%s %s scale' % (width,height)])

        if imNumComponents == 3 :
            self.code_append('/DeviceRGB setcolorspace')
        elif imNumComponents == 1 :
            self.code_append('/DeviceGray setcolorspace')
        # create the image dictionary
        self.code_append("""
<<
/ImageType 1
/Width %d /Height %d  %% dimensions of source image
/BitsPerComponent %d""" % (imwidth, imheight, imBitsPerComponent) )

        if imNumComponents == 1:
            self.code_append('/Decode [0 1]')
        if imNumComponents == 3:
            self.code_append('/Decode [0 1 0 1 0 1]  %% decode color values normally')

        self.code.extend([  '/ImageMatrix [%s 0 0 %s 0 %s]' % (imwidth, -imheight, imheight),
                            '/DataSource currentfile /ASCIIHexDecode filter',
                            '>> % End image dictionary',
                            'image'])
        # after image operator just need to dump image dat to file as hexstring
        rawimage = (myimage.tobytes if hasattr(myimage,'tobytes') else myimage.tostring)()
        hex_encoded = self._AsciiHexEncode(rawimage)

        # write in blocks of 78 chars per line
        outstream = StringIO(hex_encoded)

        dataline = outstream.read(78)
        while dataline != "":
            self.code_append(dataline)
            dataline= outstream.read(78)
        self.code_append('> % end of image data') # > is EOD for hex encoded filterfor clarity
        self.code_append('grestore') # return coordinates to normal

# renderpdf - draws them onto a canvas
"""Usage:
    from reportlab.graphics import renderPS
    renderPS.draw(drawing, canvas, x, y)
Execute the script to see some test drawings."""
from reportlab.graphics.shapes import *

# hack so we only get warnings once each
#warnOnce = WarnOnce()

# the main entry point for users...
def draw(drawing, canvas, x=0, y=0, showBoundary=rl_config.showBoundary):
    """As it says"""
    R = _PSRenderer()
    R.draw(renderScaledDrawing(drawing), canvas, x, y, showBoundary=showBoundary)

def _pointsFromList(L):
    '''
    given a list of coordinates [x0, y0, x1, y1....]
    produce a list of points [(x0,y0), (y1,y0),....]
    '''
    P=[]
    a = P.append
    for i in range(0,len(L),2):
        a((L[i],L[i+1]))
    return P

class _PSRenderer(Renderer):
    """This draws onto a EPS document.  It needs to be a class
    rather than a function, as some EPS-specific state tracking is
    needed outside of the state info in the SVG model."""

    def drawNode(self, node):
        """This is the recursive method called for each node
        in the tree"""
        self._canvas.comment('begin node %r'%node)
        color = self._canvas._color
        if not (isinstance(node, Path) and node.isClipPath):
            self._canvas.saveState()

        #apply state changes
        deltas = getStateDelta(node)
        self._tracker.push(deltas)
        self.applyStateChanges(deltas, {})

        #draw the object, or recurse
        self.drawNodeDispatcher(node)

        rDeltas = self._tracker.pop()
        if not (isinstance(node, Path) and node.isClipPath):
            self._canvas.restoreState()
        self._canvas.comment('end node %r'%node)
        self._canvas._color = color

        #restore things we might have lost (without actually doing anything).
        for k, v in rDeltas.items():
            if k in self._restores:
                setattr(self._canvas,self._restores[k],v)

##  _restores = {'stroke':'_stroke','stroke_width': '_lineWidth','stroke_linecap':'_lineCap',
##              'stroke_linejoin':'_lineJoin','fill':'_fill','font_family':'_font',
##              'font_size':'_fontSize'}
    _restores = {'strokeColor':'_strokeColor','strokeWidth': '_lineWidth','strokeLineCap':'_lineCap',
                'strokeLineJoin':'_lineJoin','fillColor':'_fillColor','fontName':'_font',
                'fontSize':'_fontSize'}

    def drawRect(self, rect):
        if rect.rx == rect.ry == 0:
            #plain old rectangle
            self._canvas.rect(
                    rect.x, rect.y,
                    rect.x+rect.width, rect.y+rect.height)
        else:
            #cheat and assume ry = rx; better to generalize
            #pdfgen roundRect function.  TODO
            self._canvas.roundRect(
                    rect.x, rect.y,
                    rect.x+rect.width, rect.y+rect.height, rect.rx, rect.ry
                    )

    def drawLine(self, line):
        if self._canvas._strokeColor:
            self._canvas.line(line.x1, line.y1, line.x2, line.y2)

    def drawCircle(self, circle):
        self._canvas.circle( circle.cx, circle.cy, circle.r)

    def drawWedge(self, wedge):
        yradius, radius1, yradius1 = wedge._xtraRadii()
        if (radius1==0 or radius1 is None) and (yradius1==0 or yradius1 is None) and not wedge.annular:
            startangledegrees = wedge.startangledegrees
            endangledegrees = wedge.endangledegrees
            centerx= wedge.centerx
            centery = wedge.centery
            radius = wedge.radius
            extent = endangledegrees - startangledegrees
            self._canvas.drawArc(centerx-radius, centery-yradius, centerx+radius, centery+yradius,
                startangledegrees, extent, fromcenter=1)
        else:
            P = wedge.asPolygon()
            if isinstance(P,Path):
                self.drawPath(P)
            else:
                self.drawPolygon(P)

    def drawPolyLine(self, p):
        if self._canvas._strokeColor:
            self._canvas.polyLine(_pointsFromList(p.points))

    def drawEllipse(self, ellipse):
        #need to convert to pdfgen's bounding box representation
        x1 = ellipse.cx - ellipse.rx
        x2 = ellipse.cx + ellipse.rx
        y1 = ellipse.cy - ellipse.ry
        y2 = ellipse.cy + ellipse.ry
        self._canvas.ellipse(x1,y1,x2,y2)

    def drawPolygon(self, p):
        self._canvas.polygon(_pointsFromList(p.points), closed=1)

    def drawString(self, stringObj):
        textRenderMode = getattr(stringObj,'textRenderMode',0)
        if self._canvas._fillColor or textRenderMode:
            S = self._tracker.getState()
            text_anchor, x, y, text = S['textAnchor'], stringObj.x,stringObj.y,stringObj.text
            if not text_anchor in ['start','inherited']:
                font, fontSize = S['fontName'], S['fontSize']
                textLen = stringWidth(text, font,fontSize)
                if text_anchor=='end':
                    x -= textLen
                elif text_anchor=='middle':
                    x -= textLen/2
                elif text_anchor=='numeric':
                    x -= numericXShift(text_anchor,text,textLen,font,fontSize,encoding='winansi')
                else:
                    raise ValueError('bad value for text_anchor '+str(text_anchor))
            self._canvas.drawString(x,y,text, textRenderMode=textRenderMode)

    def drawPath(self, path, fillMode=None):
        from reportlab.graphics.shapes import _renderPath
        c = self._canvas
        drawFuncs = (c.moveTo, c.lineTo, c.curveTo, c.closePath)
        autoclose = getattr(path,'autoclose','')
        def rP(**kwds):
            return _renderPath(path, drawFuncs, **kwds)
        if fillMode is None:
            fillMode = getattr(path,'fillMode',c._fillMode)
        fill = c._fillColor is not None
        stroke = c._strokeColor is not None
        clip = path.isClipPath
        fas = lambda **kwds: c._fillAndStroke([], fillMode=fillMode, **kwds)
        pathFill = lambda : c._fillAndStroke([], stroke=0, fillMode=fillMode)
        pathStroke = lambda : c._fillAndStroke([], fill=0)
        if autoclose=='svg':
            rP()
            fas(stroke=stroke,fill=fill,clip=clip)
        elif autoclose=='pdf':
            if fill:
                rP(forceClose=True)
                fas(stroke=stroke,fill=fill,clip=clip)
            elif stroke or clip:
                rP()
                fas(stroke=stroke,fill=0,clip=clip)
        else:
            if fill and rP(countOnly=True):
                rP()
            elif stroke or clip:
                rP()
                fas(stroke=stroke,fill=0,clip=clip)

    def applyStateChanges(self, delta, newState):
        """This takes a set of states, and outputs the operators
        needed to set those properties"""
        for key, value in delta.items():
            if key == 'transform':
                self._canvas.transform(value[0], value[1], value[2],
                                 value[3], value[4], value[5])
            elif key == 'strokeColor':
                #this has different semantics in PDF to SVG;
                #we always have a color, and either do or do
                #not apply it; in SVG one can have a 'None' color
                self._canvas.setStrokeColor(value)
            elif key == 'strokeWidth':
                self._canvas.setLineWidth(value)
            elif key == 'strokeLineCap':  #0,1,2
                self._canvas.setLineCap(value)
            elif key == 'strokeLineJoin':
                self._canvas.setLineJoin(value)
            elif key == 'strokeDashArray':
                if value:
                    if isinstance(value,(list,tuple)) and len(value)==2 and isinstance(value[1],(tuple,list)):
                        phase = value[0]
                        value = value[1]
                    else:
                        phase = 0
                    self._canvas.setDash(value,phase)
                else:
                    self._canvas.setDash()
##          elif key == 'stroke_opacity':
##              warnOnce('Stroke Opacity not supported yet')
            elif key == 'fillColor':
                #this has different semantics in PDF to SVG;
                #we always have a color, and either do or do
                #not apply it; in SVG one can have a 'None' color
                self._canvas.setFillColor(value)
##          elif key == 'fill_rule':
##              warnOnce('Fill rules not done yet')
##          elif key == 'fill_opacity':
##              warnOnce('Fill opacity not done yet')
            elif key in ['fontSize', 'fontName']:
                # both need setting together in PDF
                # one or both might be in the deltas,
                # so need to get whichever is missing
                fontname = delta.get('fontName', self._canvas._font)
                fontsize = delta.get('fontSize', self._canvas._fontSize)
                self._canvas.setFont(fontname, fontsize)

    def drawImage(self, image):
        from reportlab.lib.utils import ImageReader
        im = ImageReader(image.path)
        self._canvas.drawImage(im._image,image.x,image.y,image.width,image.height)

def drawToFile(d,fn, showBoundary=rl_config.showBoundary,**kwd):
    d = renderScaledDrawing(d)
    c = PSCanvas((d.width,d.height))
    draw(d, c, 0, 0, showBoundary=showBoundary)
    c.save(fn)

def drawToString(d, showBoundary=rl_config.showBoundary):
    "Returns a PS as a string in memory, without touching the disk"
    s = BytesIO()
    drawToFile(d, s, showBoundary=showBoundary)
    return s.getvalue()

#########################################################
#
#   test code.  First, define a bunch of drawings.
#   Routine to draw them comes at the end.
#
#########################################################
def test(outDir='epsout',shout=False):
    from reportlab.graphics import testshapes
    from reportlab.rl_config import verbose
    OLDFONTS = testshapes._FONTS[:]
    testshapes._FONTS[:] = ['Times-Roman','Times-Bold','Times-Italic', 'Times-BoldItalic','Courier']
    try:
        import os
        # save all drawings and their doc strings from the test file
        if not os.path.isdir(outDir):
            os.mkdir(outDir)
        #grab all drawings from the test module
        drawings = []

        for funcname in dir(testshapes):
            if funcname[0:10] == 'getDrawing':
                func = getattr(testshapes,funcname)
                drawing = func()
                docstring = getattr(func,'__doc__','')
                drawings.append((drawing, docstring))

        i = 0
        for (d, docstring) in drawings:
            filename = outDir + os.sep + 'renderPS_%d.eps'%i
            drawToFile(d,filename)
            if shout or verbose>2: print('renderPS test saved %s' % ascii(filename))
            i += 1
    finally:
        testshapes._FONTS[:] = OLDFONTS

if __name__=='__main__':
    import sys
    if len(sys.argv)>1:
        outdir = sys.argv[1]
    else:
        outdir = 'epsout'
    test(outdir,shout=True)
