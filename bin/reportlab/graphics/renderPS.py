#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/graphics/renderPS.py
__version__=''' $Id: renderPS.py 2808 2006-03-15 16:47:27Z rgbecker $ '''
import string, types
from reportlab.pdfbase.pdfmetrics import getFont, stringWidth # for font info
from reportlab.lib.utils import fp_str, getStringIO
from reportlab.lib.colors import black
from reportlab.graphics.renderbase import Renderer, StateTracker, getStateDelta, renderScaledDrawing
from reportlab.graphics.shapes import STATE_DEFAULTS
import math
from types import StringType
from operator import getitem
from reportlab import rl_config


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

    def comment(self,msg):
        if self.comments: self.code.append('%'+msg)

    def drawImage(self, image, x1,y1, x2=None,y2=None): # Postscript Level2 version
        # select between postscript level 1 or level 2
        if PostScriptLevel==1:
            self._drawImageLevel1(image, x1,y1, x2=None,y2=None)
        elif PostScriptLevel == 2 :
            self._drawImageLevel2(image, x1,y1, x2=None,y2=None)
        else :
            raise 'PostScriptLevelException'

    def clear(self):
        self.code.append('showpage') # ugh, this makes no sense oh well.

    def save(self,f=None):
        if not hasattr(f,'write'):
            file = open(f,'wb')
        else:
            file = f
        if self.code[-1]!='showpage': self.clear()
        self.code.insert(0,'''\
%%!PS-Adobe-3.0 EPSF-3.0
%%%%BoundingBox: 0 0 %d %d
%%%% Initialization:
/m {moveto} bind def
/l {lineto} bind def
/c {curveto} bind def

%s
''' % (self.width,self.height, PS_WinAnsiEncoding))

        # for each font used, reencode the vectors
        fontReencode = []
        for fontName in self._fontsUsed:
            fontReencode.append('WinAnsiEncoding /%s /%s RE' % (fontName, fontName))
        self.code.insert(1, string.join(fontReencode, self._sep))

        file.write(string.join(self.code,self._sep))
        if file is not f:
            file.close()
            from reportlab.lib.utils import markfilename
            markfilename(f,creatorcode='XPR3',filetype='EPSF')

    def saveState(self):
        self._xtraState_push((self._fontCodeLoc,))
        self.code.append('gsave')

    def restoreState(self):
        self.code.append('grestore')
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
            self.code.append('%d setlinecap'%v)

    def setLineJoin(self,v):
        if self._lineJoin!=v:
            self._lineJoin = v
            self.code.append('%d setlinejoin'%v)

    def setDash(self, array=[], phase=0):
        """Two notations.  pass two numbers, or an array and phase"""
        # copied and modified from reportlab.canvas
        psoperation = "setdash"
        if type(array) == types.IntType or type(array) == types.FloatType:
            self._code.append('[%s %s] 0 %s' % (array, phase, psoperation))
        elif type(array) == types.ListType or type(array) == types.TupleType:
            assert phase >= 0, "phase is a length in user space"
            textarray = string.join(map(str, array))
            self.code.append('[%s] %s %s' % (textarray, phase, psoperation))

    def setStrokeColor(self, color):
        self._strokeColor = color
        self.setColor(color)

    def setColor(self, color):
        if self._color!=color:
            self._color = color
            if color:
                if hasattr(color, "cyan"):
                    self.code.append('%s setcmykcolor' % fp_str(color.cyan, color.magenta, color.yellow, color.black))
                else:
                    self.code.append('%s setrgbcolor' % fp_str(color.red, color.green, color.blue))

    def setFillColor(self, color):
        self._fillColor = color
        self.setColor(color)

    def setLineWidth(self, width):
        if width != self._lineWidth:
            self._lineWidth = width
            self.code.append('%s setlinewidth' % width)

    def setFont(self,font,fontSize,leading=None):
        if self._font!=font or self._fontSize!=fontSize:
            self._fontCodeLoc = len(self.code)
            self._font = font
            self._fontSize = fontSize
            self.code.append('')

    def line(self, x1, y1, x2, y2):
        if self._strokeColor != None:
            self.setColor(self._strokeColor)
            self.code.append('%s m %s l stroke' % (fp_str(x1, y1), fp_str(x2, y2)))

    def _escape(self, s):
        '''
        return a copy of string s with special characters in postscript strings
        escaped with backslashes.
        Have not handled characters that are converted normally in python strings
        i.e. \n -> newline
        '''
        str = string.replace(s, chr(0x5C), r'\\' )
        str = string.replace(str, '(', '\(' )
        str = string.replace(str, ')', '\)')
        return str

    def drawString(self, x, y, s, angle=0):
        if self._fillColor != None:
            if not self.code[self._fontCodeLoc]:
                psName = getFont(self._font).face.name
                self.code[self._fontCodeLoc]='(%s) findfont %s scalefont setfont' % (psName,fp_str(self._fontSize))
                if psName not in self._fontsUsed:
                    self._fontsUsed.append(psName)
            self.setColor(self._fillColor)
            s = self._escape(s)
## before inverting...
##            if angle == 0 :   # do special case of angle = 0 first. Avoids a bunch of gsave/grestore ops
##                self.code.append('%s m 1 -1 scale (%s) show 1 -1 scale' % (fp_str(x,y),s))
##            else : # general case, rotated text
##                self.code.append('gsave %s %s translate %s rotate' % (x,y,angle))
##                self.code.append('0 0 m 1 -1 scale (%s) show' % s)
##                self.code.append('grestore')
            if angle == 0 :   # do special case of angle = 0 first. Avoids a bunch of gsave/grestore ops
                self.code.append('%s m (%s) show ' % (fp_str(x,y),s))
            else : # general case, rotated text
                self.code.append('gsave %s %s translate %s rotate' % (x,y,angle))
                self.code.append('0 0 m (%s) show' % s)
                self.code.append('grestore')

    def drawCentredString(self, x, y, text, text_anchor='middle'):
        if self._fillColor is not None:
            textLen = stringWidth(text, self._font,self._fontSize)
            if text_anchor=='end':
                x -= textLen
            elif text_anchor=='middle':
                x -= textLen/2.
            self.drawString(x,y,text)

    def drawRightString(self, text, x, y):
        self.drawCentredString(text,x,y,text_anchor='end')

    def drawCurve(self, x1, y1, x2, y2, x3, y3, x4, y4, closed=0):
        codeline = '%s m %s curveto'
        data = (fp_str(x1, y1), fp_str(x2, y2, x3, y3, x4, y4))
        if self._fillColor != None:
            self.setColor(self._fillColor)
            self.code.append((codeline % data) + ' eofill')
        if self._strokeColor != None:
            self.setColor(self._strokeColor)
            self.code.append((codeline % data)
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
        rrCode = ['newpath'] # Round Rect code path
        # upper left corner ellipse is first
        rrCode.append(ellipsePath % (x1+rx, y1+ry, rx, -ry, 90, 180))
        rrCode.append(ellipsePath % (x1+rx, y2-ry, rx, -ry, 180, 270))
        rrCode.append(ellipsePath % (x2-rx, y2-ry, rx, -ry, 270, 360))
        rrCode.append(ellipsePath % (x2-rx, y1+ry, rx, -ry, 0,  90) )
        rrCode.append('closepath')

        self._fillAndStroke(rrCode)

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
            self.code.append(codeline)
            codelineAppended = 1
            if self._strokeColor!=None: self.code.append('gsave')
            self.lineTo(cx,cy)
            self.code.append('eofill')
            if self._strokeColor!=None: self.code.append('grestore')

        # stroke portion
        if self._strokeColor != None:
            # this is a bit hacked up.  There is certainly a better way...
            self.setColor(self._strokeColor)
            (startx, starty) = (cx+rx*math.cos(startAngleRadians), cy+ry*math.sin(startAngleRadians))
            if not codelineAppended:
                self.code.append(codeline)
            if fromcenter:
                # move to center
                self.lineTo(cx,cy)
                self.lineTo(startx, starty)
                self.code.append('closepath')
            self.code.append('stroke')

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

        polyCode = []
        polyCode.append("%s m" % fp_str(start))
        for point in p:
            polyCode.append("%s l" % fp_str(point))
        if closed:
            polyCode.append("closepath")

        self._fillAndStroke(polyCode,stroke=stroke,fill=fill)

    def lines(self, lineList, color=None, width=None):
        if self._strokeColor != None:
            self._setColor(self._strokeColor)
            codeline = '%s m %s l stroke'
            for line in lineList:
                self.code.append(codeline % (fp_str(line[0]),fp_str(line[1])))

    def moveTo(self,x,y):
        self.code.append('%s m' % fp_str(x, y))

    def lineTo(self,x,y):
        self.code.append('%s l' % fp_str(x, y))

    def curveTo(self,x1,y1,x2,y2,x3,y3):
        self.code.append('%s c' % fp_str(x1,y1,x2,y2,x3,y3))

    def closePath(self):
        self.code.append('closepath')

    def polyLine(self, p):
        assert len(p) >= 1, 'Polyline must have 1 or more points'
        if self._strokeColor != None:
            self.setColor(self._strokeColor)
            self.moveTo(p[0][0], p[0][1])
            for t in p[1:]:
                self.lineTo(t[0], t[1])
            self.code.append('stroke')


    def drawFigure(self, partList, closed=0):
        figureCode = []
        first = 1

        for part in partList:
            op = part[0]
            args = list(part[1:])

            if op == figureLine:
                if first:
                    first = 0
                    figureCode.append("%s m" % fp_str(args[:2]))
                else:
                    figureCode.append("%s l" % fp_str(args[:2]))
                figureCode.append("%s l" % fp_str(args[2:]))

            elif op == figureArc:
                first = 0
                x1,y1,x2,y2,startAngle,extent = args[:6]
                figureCode.append(self._genArcCode(x1,y1,x2,y2,startAngle,extent))

            elif op == figureCurve:
                if first:
                    first = 0
                    figureCode.append("%s m" % fp_str(args[:2]))
                else:
                    figureCode.append("%s l" % fp_str(args[:2]))
                figureCode.append("%s curveto" % fp_str(args[2:]))
            else:
                raise TypeError, "unknown figure operator: "+op

        if closed:
            figureCode.append("closepath")
        self._fillAndStroke(figureCode)

    def _fillAndStroke(self,code,clip=0,fill=1,stroke=1):
        fill = self._fillColor and fill
        stroke = self._strokeColor and stroke
        if fill or stroke or clip:
            self.code.extend(code)
            if fill:
                if stroke or clip: self.code.append("gsave")
                self.setColor(self._fillColor)
                self.code.append("eofill")
                if stroke or clip: self.code.append("grestore")
            if stroke:
                if clip: self.code.append("gsave")
                self.setColor(self._strokeColor)
                self.code.append("stroke")
                if clip: self.code.append("grestore")
            if clip:
                self.code.append("clip")
                self.code.append("newpath")


    def translate(self,x,y):
        self.code.append('%s translate' % fp_str(x,y))

    def scale(self,x,y):
        self.code.append('%s scale' % fp_str(x,y))

    def transform(self,a,b,c,d,e,f):
        self.code.append('[%s] concat' % fp_str(a,b,c,d,e,f))

    def _drawTimeResize(self,w,h):
        '''if this is used we're probably in the wrong world'''
        self.width, self.height = w, h

    ############################################################################################
    # drawImage(self. image, x1, y1, x2=None, y2=None) is now defined by either _drawImageLevel1
    #    ._drawImageLevel2, the choice is made in .__init__ depending on option
    def _drawImageLevel1(self, image, x1, y1, x2=None,y2=None):
        # Postscript Level1 version available for fallback mode when Level2 doesn't work
        """drawImage(self,image,x1,y1,x2=None,y2=None) : If x2 and y2 are ommitted, they are
        calculated from image size. (x1,y1) is upper left of image, (x2,y2) is lower right of
        image in piddle coordinates."""
        # For now let's start with 24 bit RGB images (following piddlePDF again)
        component_depth = 8
        myimage = image.convert('RGB')
        imgwidth, imgheight = myimage.size
        if not x2:
            x2 = imgwidth + x1
        if not y2:
            y2 = y1 + imgheight
        drawwidth = x2 - x1
        drawheight = y2 - y1
        #print 'Image size (%d, %d); Draw size (%d, %d)' % (imgwidth, imgheight, drawwidth, drawheight)
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
            '%s %s translate' % (x1,-y1 - drawheight), # need to start are lower left of image
            '%s %s scale' % (drawwidth,drawheight),
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

        rawimage = myimage.tostring()
        assert(len(rawimage) == imgwidth*imgheight, 'Wrong amount of data for image')
        #compressed = zlib.compress(rawimage) # no zlib at moment
        hex_encoded = self._AsciiHexEncode(rawimage)

        # write in blocks of 78 chars per line
        outstream = getStringIO(hex_encoded)

        dataline = outstream.read(78)
        while dataline <> "":
            self.code.append(dataline)
            dataline= outstream.read(78)
        self.code.append('% end of image data') # for clarity
        self.code.append('grestore') # return coordinates to normal

    # end of drawImage
    def _AsciiHexEncode(self, input):  # also based on piddlePDF
        "Helper function used by images"
        output = getStringIO()
        for char in input:
            output.write('%02x' % ord(char))
        return output.getvalue()

    def _drawImageLevel2(self, image, x1,y1, x2=None,y2=None): # Postscript Level2 version
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
        if not x2:
            x2 = imwidth + x1
        if not y2:
            y2 = y1 + imheight
        drawwidth = x2 - x1
        drawheight = y2 - y1
        self.code.extend([
            'gsave',
            '%s %s translate' % (x1,-y1 - drawheight), # need to start are lower left of image
            '%s %s scale' % (drawwidth,drawheight)])

        if imNumComponents == 3 :
            self.code.append('/DeviceRGB setcolorspace')
        elif imNumComponents == 1 :
            self.code.append('/DeviceGray setcolorspace')
        # create the image dictionary
        self.code.append("""
<<
/ImageType 1
/Width %d /Height %d  %% dimensions of source image
/BitsPerComponent %d""" % (imwidth, imheight, imBitsPerComponent) )

        if imNumComponents == 1:
            self.code.append('/Decode [0 1]')
        if imNumComponents == 3:
            self.code.append('/Decode [0 1 0 1 0 1]  %% decode color values normally')

        self.code.extend([  '/ImageMatrix [%s 0 0 %s 0 %s]' % (imwidth, -imheight, imheight),
                            '/DataSource currentfile /ASCIIHexDecode filter',
                            '>> % End image dictionary',
                            'image'])
        # after image operator just need to dump image dat to file as hexstring
        rawimage = myimage.tostring()
        assert(len(rawimage) == imwidth*imheight, 'Wrong amount of data for image')
        #compressed = zlib.compress(rawimage) # no zlib at moment
        hex_encoded = self._AsciiHexEncode(rawimage)

        # write in blocks of 78 chars per line
        outstream = getStringIO(hex_encoded)

        dataline = outstream.read(78)
        while dataline <> "":
            self.code.append(dataline)
            dataline= outstream.read(78)
        self.code.append('> % end of image data') # > is EOD for hex encoded filterfor clarity
        self.code.append('grestore') # return coordinates to normal

# renderpdf - draws them onto a canvas
"""Usage:
    from reportlab.graphics import renderPS
    renderPS.draw(drawing, canvas, x, y)
Execute the script to see some test drawings."""
from shapes import *

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
    for i in range(0,len(L),2):
        P.append((L[i],L[i+1]))
    return P

class _PSRenderer(Renderer):
    """This draws onto a EPS document.  It needs to be a class
    rather than a function, as some EPS-specific state tracking is
    needed outside of the state info in the SVG model."""

    def __init__(self):
        self._tracker = StateTracker()

    def drawNode(self, node):
        """This is the recursive method called for each node
        in the tree"""
        self._canvas.comment('begin node %s'%`node`)
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
        self._canvas.comment('end node %s'%`node`)
        self._canvas._color = color

        #restore things we might have lost (without actually doing anything).
        for k, v in rDeltas.items():
            if self._restores.has_key(k):
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
        if (radius1==0 or radius1 is None) and (yradius1==0 or yradius1 is None):
            startangledegrees = wedge.startangledegrees
            endangledegrees = wedge.endangledegrees
            centerx= wedge.centerx
            centery = wedge.centery
            radius = wedge.radius
            extent = endangledegrees - startangledegrees
            self._canvas.drawArc(centerx-radius, centery-yradius, centerx+radius, centery+yradius,
                startangledegrees, extent, fromcenter=1)
        else:
            self.drawPolygon(wedge.asPolygon())

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
        if self._canvas._fillColor:
            S = self._tracker.getState()
            text_anchor, x, y, text = S['textAnchor'], stringObj.x,stringObj.y,stringObj.text
            if not text_anchor in ['start','inherited']:
                font, fontSize = S['fontName'], S['fontSize']
                textLen = stringWidth(text, font,fontSize)
                if text_anchor=='end':
                    x = x-textLen
                elif text_anchor=='middle':
                    x = x - textLen/2
                else:
                    raise ValueError, 'bad value for text_anchor '+str(text_anchor)
            self._canvas.drawString(x,y,text)

    def drawPath(self, path):
        from reportlab.graphics.shapes import _renderPath
        c = self._canvas
        drawFuncs = (c.moveTo, c.lineTo, c.curveTo, c.closePath)
        isClosed = _renderPath(path, drawFuncs)
        if not isClosed:
            c._fillColor = None
        c._fillAndStroke([], clip=path.isClipPath)

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
                    self._canvas.setDash(value)
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
        x0 = image.x
        y0 = image.y
        x1 = image.width
        if x1 is not None: x1 += x0
        y1 = image.height
        if y1 is not None: y1 += y0
        self._canvas.drawImage(im._image,x0,y0,x1,y1)

def drawToFile(d,fn, showBoundary=rl_config.showBoundary):
    d = renderScaledDrawing(d)
    c = PSCanvas((d.width,d.height))
    draw(d, c, 0, 0, showBoundary=showBoundary)
    c.save(fn)

def drawToString(d, showBoundary=rl_config.showBoundary):
    "Returns a PS as a string in memory, without touching the disk"
    s = getStringIO()
    drawToFile(d, s, showBoundary=showBoundary)
    return s.getvalue()

#########################################################
#
#   test code.  First, defin a bunch of drawings.
#   Routine to draw them comes at the end.
#
#########################################################
def test(outdir='epsout'):
    import os
    # print all drawings and their doc strings from the test
    # file
    if not os.path.isdir(outdir):
        os.mkdir(outdir)
    #grab all drawings from the test module
    import testshapes
    drawings = []

    for funcname in dir(testshapes):
        #if funcname[0:11] == 'getDrawing2':
        #    print 'hacked to only show drawing 2'
        if funcname[0:10] == 'getDrawing':
            drawing = eval('testshapes.' + funcname + '()')  #execute it
            docstring = eval('testshapes.' + funcname + '.__doc__')
            drawings.append((drawing, docstring))

    i = 0
    for (d, docstring) in drawings:
        filename = outdir + os.sep + 'renderPS_%d.eps'%i
        drawToFile(d,filename)
        print 'saved', filename
        i = i + 1

if __name__=='__main__':
    import sys
    if len(sys.argv)>1:
        outdir = sys.argv[1]
    else:
        outdir = 'epsout'
    test(outdir)
