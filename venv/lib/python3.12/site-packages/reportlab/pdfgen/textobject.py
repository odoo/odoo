#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/pdfgen/textobject.py
__version__='3.3.0'
__doc__="""
PDFTextObject is an efficient way to add text to a Canvas. Do not
instantiate directly, obtain one from the Canvas instead.

Progress Reports:
8.83, 2000-01-13, gmcm: created from pdfgen.py
"""
from reportlab.lib.colors import Color, CMYKColor, CMYKColorSep, toColor
from reportlab.lib.utils import isBytes, isStr, asUnicode
from reportlab.lib.rl_accel import fp_str
from reportlab.pdfbase import pdfmetrics
from reportlab.rl_config import rtlSupport

log2vis = None
def fribidiText(text,direction):
    return text
if rtlSupport:
    try:
        from pyfribidi2 import log2vis, ON as DIR_ON, LTR as DIR_LTR, RTL as DIR_RTL
        directionsMap = dict(LTR=DIR_LTR,RTL=DIR_RTL)
        def fribidiText(text,direction):
            return log2vis(text, directionsMap.get(direction,DIR_ON),clean=True) if direction in ('LTR','RTL') else text
    except:
        import warnings
        warnings.warn('pyfribidi is not installed - RTL not supported')

class _PDFColorSetter:
    '''Abstracts the color setting operations; used in Canvas and Textobject
    asseumes we have a _code object'''
    def _checkSeparation(self,cmyk):
        if isinstance(cmyk,CMYKColorSep):
            name,sname = self._doc.addColor(cmyk)
            if name not in self._colorsUsed:
                self._colorsUsed[name] = sname
            return name

    #if this is set to a callable(color) --> color it can be used to check color setting
    #see eg _enforceCMYK/_enforceRGB
    _enforceColorSpace = None

    def setFillColorCMYK(self, c, m, y, k, alpha=None):
         """set the fill color useing negative color values
         (cyan, magenta, yellow and darkness value).
         Takes 4 arguments between 0.0 and 1.0"""
         self.setFillColor((c,m,y,k),alpha=alpha)

    def setStrokeColorCMYK(self, c, m, y, k, alpha=None):
         """set the stroke color useing negative color values
            (cyan, magenta, yellow and darkness value).
            Takes 4 arguments between 0.0 and 1.0"""
         self.setStrokeColor((c,m,y,k),alpha=alpha)

    def setFillColorRGB(self, r, g, b, alpha=None):
        """Set the fill color using positive color description
           (Red,Green,Blue).  Takes 3 arguments between 0.0 and 1.0"""
        self.setFillColor((r,g,b),alpha=alpha)

    def setStrokeColorRGB(self, r, g, b, alpha=None):
        """Set the stroke color using positive color description
           (Red,Green,Blue).  Takes 3 arguments between 0.0 and 1.0"""
        self.setStrokeColor((r,g,b),alpha=alpha)

    def setFillColor(self, aColor, alpha=None):
        """Takes a color object, allowing colors to be referred to by name"""
        if self._enforceColorSpace:
            aColor = self._enforceColorSpace(aColor)
        if isinstance(aColor, CMYKColor):
            d = aColor.density
            c,m,y,k = (d*aColor.cyan, d*aColor.magenta, d*aColor.yellow, d*aColor.black)
            self._fillColorObj = aColor
            name = self._checkSeparation(aColor)
            if name:
                self._code.append('/%s cs %s scn' % (name,fp_str(d)))
            else:
                self._code.append('%s k' % fp_str(c, m, y, k))
        elif isinstance(aColor, Color):
            rgb = (aColor.red, aColor.green, aColor.blue)
            self._fillColorObj = aColor
            self._code.append('%s rg' % fp_str(rgb) )
        elif isinstance(aColor,(tuple,list)):
            l = len(aColor)
            if l==3:
                self._fillColorObj = aColor
                self._code.append('%s rg' % fp_str(aColor) )
            elif l==4:
                self._fillColorObj = aColor
                self._code.append('%s k' % fp_str(aColor))
            else:
                raise ValueError('Unknown color %r' % aColor)
        elif isStr(aColor):
            self.setFillColor(toColor(aColor))
        else:
            raise ValueError('Unknown color %r' % aColor)
        if alpha is not None:
            self.setFillAlpha(alpha)
        elif getattr(aColor, 'alpha', None) is not None:
            self.setFillAlpha(aColor.alpha)

    def setStrokeColor(self, aColor, alpha=None):
        """Takes a color object, allowing colors to be referred to by name"""
        if self._enforceColorSpace:
            aColor = self._enforceColorSpace(aColor)
        if isinstance(aColor, CMYKColor):
            d = aColor.density
            c,m,y,k = (d*aColor.cyan, d*aColor.magenta, d*aColor.yellow, d*aColor.black)
            self._strokeColorObj = aColor
            name = self._checkSeparation(aColor)
            if name:
                self._code.append('/%s CS %s SCN' % (name,fp_str(d)))
            else:
                self._code.append('%s K' % fp_str(c, m, y, k))
        elif isinstance(aColor, Color):
            rgb = (aColor.red, aColor.green, aColor.blue)
            self._strokeColorObj = aColor
            self._code.append('%s RG' % fp_str(rgb) )
        elif isinstance(aColor,(tuple,list)):
            l = len(aColor)
            if l==3:
                self._strokeColorObj = aColor
                self._code.append('%s RG' % fp_str(aColor) )
            elif l==4:
                self._strokeColorObj = aColor
                self._code.append('%s K' % fp_str(aColor))
            else:
                raise ValueError('Unknown color %r' % aColor)
        elif isStr(aColor):
            self.setStrokeColor(toColor(aColor))
        else:
            raise ValueError('Unknown color %r' % aColor)
        if alpha is not None:
            self.setStrokeAlpha(alpha)
        elif getattr(aColor, 'alpha', None) is not None:
            self.setStrokeAlpha(aColor.alpha)

    def setFillGray(self, gray, alpha=None):
        """Sets the gray level; 0.0=black, 1.0=white"""
        self._fillColorObj = (gray, gray, gray)
        self._code.append('%s g' % fp_str(gray))
        if alpha is not None:
            self.setFillAlpha(alpha)

    def setStrokeGray(self, gray, alpha=None):
        """Sets the gray level; 0.0=black, 1.0=white"""
        self._strokeColorObj = (gray, gray, gray)
        self._code.append('%s G' % fp_str(gray))
        if alpha is not None:
            self.setFillAlpha(alpha)

    def setStrokeAlpha(self,a):
        if not (isinstance(a,(float,int)) and 0<=a<=1):
            raise ValueError('setStrokeAlpha invalid value %r' % a)
        getattr(self,'_setStrokeAlpha',lambda x: None)(a)

    def setFillAlpha(self,a):
        if not (isinstance(a,(float,int)) and 0<=a<=1):
            raise ValueError('setFillAlpha invalid value %r' % a)
        getattr(self,'_setFillAlpha',lambda x: None)(a)

    def setStrokeOverprint(self,a):
        getattr(self,'_setStrokeOverprint',lambda x: None)(a)

    def setFillOverprint(self,a):
        getattr(self,'_setFillOverprint',lambda x: None)(a)

    def setOverprintMask(self,a):
        getattr(self,'_setOverprintMask',lambda x: None)(a)

class PDFTextObject(_PDFColorSetter):
    """PDF logically separates text and graphics drawing; text
    operations need to be bracketed between BT (Begin text) and
    ET operators. This class ensures text operations are
    properly encapusalted. Ask the canvas for a text object
    with beginText(x, y).  Do not construct one directly.
    Do not use multiple text objects in parallel; PDF is
    not multi-threaded!

    It keeps track of x and y coordinates relative to its origin."""

    def __init__(self, canvas, x=0,y=0, direction=None):
        self._code = ['BT']    #no point in [] then append RGB
        self._canvas = canvas  #canvas sets this so it has access to size info
        self._fontname = self._canvas._fontname
        self._fontsize = self._canvas._fontsize
        self._leading = self._canvas._leading
        self._doc = self._canvas._doc
        self._colorsUsed = self._canvas._colorsUsed
        self._enforceColorSpace = getattr(canvas,'_enforceColorSpace',None)
        font = pdfmetrics.getFont(self._fontname)
        self._curSubset = -1
        self.direction = direction
        self.setTextOrigin(x, y)
        self._textRenderMode = 0
        self._clipping = 0

    def getCode(self):
        "pack onto one line; used internally"
        self._code.append('ET')
        if self._clipping:
            self._code.append('%d Tr' % (self._textRenderMode^4))
        return ' '.join(self._code)

    def setTextOrigin(self, x, y):
        if self._canvas.bottomup:
            self._code.append('1 0 0 1 %s Tm' % fp_str(x, y)) #bottom up
        else:
            self._code.append('1 0 0 -1 %s Tm' % fp_str(x, y))  #top down

        # The current cursor position is at the text origin
        self._x0 = self._x = x
        self._y0 = self._y = y

    def setTextTransform(self, a, b, c, d, e, f):
        "Like setTextOrigin, but does rotation, scaling etc."
        if not self._canvas.bottomup:
            c = -c    #reverse bottom row of the 2D Transform
            d = -d
        self._code.append('%s Tm' % fp_str(a, b, c, d, e, f))

        # The current cursor position is at the text origin Note that
        # we aren't keeping track of all the transform on these
        # coordinates: they are relative to the rotations/sheers
        # defined in the matrix.
        self._x0 = self._x = e
        self._y0 = self._y = f

    def moveCursor(self, dx, dy):
        """Starts a new line at an offset dx,dy from the start of the
        current line. This does not move the cursor relative to the
        current position, and it changes the current offset of every
        future line drawn (i.e. if you next do a textLine() call, it
        will move the cursor to a position one line lower than the
        position specificied in this call.  """

        # Check if we have a previous move cursor call, and combine
        # them if possible.
        if self._code and self._code[-1][-3:]==' Td':
            L = self._code[-1].split()
            if len(L)==3:
                del self._code[-1]
            else:
                self._code[-1] = ''.join(L[:-4])

            # Work out the last movement
            lastDx = float(L[-3])
            lastDy = float(L[-2])

            # Combine the two movement
            dx += lastDx
            dy -= lastDy

            # We will soon add the movement to the line origin, so if
            # we've already done this for lastDx, lastDy, remove it
            # first (so it will be right when added back again).
            self._x0 -= lastDx
            self._y0 -= lastDy

        # Output the move text cursor call.
        self._code.append('%s Td' % fp_str(dx, -dy))

        # Keep track of the new line offsets and the cursor position
        self._x0 += dx
        self._y0 += dy
        self._x = self._x0
        self._y = self._y0

    def setXPos(self, dx):
        """Starts a new line dx away from the start of the
        current line - NOT from the current point! So if
        you call it in mid-sentence, watch out."""
        self.moveCursor(dx,0)

    def getCursor(self):
        """Returns current text position relative to the last origin."""
        return (self._x, self._y)

    def getStartOfLine(self):
        """Returns a tuple giving the text position of the start of the
        current line."""
        return (self._x0, self._y0)

    def getX(self):
        """Returns current x position relative to the last origin."""
        return self._x

    def getY(self):
        """Returns current y position relative to the last origin."""
        return self._y

    def _setFont(self, psfontname, size):
        """Sets the font and fontSize
        Raises a readable exception if an illegal font
        is supplied.  Font names are case-sensitive! Keeps track
        of font anme and size for metrics."""
        self._fontname = psfontname
        self._fontsize = size
        font = pdfmetrics.getFont(self._fontname)

        if font._dynamicFont:
            self._curSubset = -1
        else:
            pdffontname = self._canvas._doc.getInternalFontName(psfontname)
            self._code.append('%s %s Tf' % (pdffontname, fp_str(size)))

    def setFont(self, psfontname, size, leading = None):
        """Sets the font.  If leading not specified, defaults to 1.2 x
        font size. Raises a readable exception if an illegal font
        is supplied.  Font names are case-sensitive! Keeps track
        of font anme and size for metrics."""
        self._fontname = psfontname
        self._fontsize = size
        if leading is None:
            leading = size * 1.2
        self._leading = leading
        font = pdfmetrics.getFont(self._fontname)
        if font._dynamicFont:
            self._curSubset = -1
        else:
            pdffontname = self._canvas._doc.getInternalFontName(psfontname)
            self._code.append('%s %s Tf %s TL' % (pdffontname, fp_str(size), fp_str(leading)))

    def setCharSpace(self, charSpace):
         """Adjusts inter-character spacing"""
         self._charSpace = charSpace
         self._code.append('%s Tc' % fp_str(charSpace))

    def setWordSpace(self, wordSpace):
        """Adjust inter-word spacing.  This can be used
        to flush-justify text - you get the width of the
        words, and add some space between them."""
        self._wordSpace = wordSpace
        self._code.append('%s Tw' % fp_str(wordSpace))

    def setHorizScale(self, horizScale):
        "Stretches text out horizontally"
        self._horizScale = 100 + horizScale
        self._code.append('%s Tz' % fp_str(horizScale))

    def setLeading(self, leading):
        "How far to move down at the end of a line."
        self._leading = leading
        self._code.append('%s TL' % fp_str(leading))

    def setTextRenderMode(self, mode):
        """Set the text rendering mode.

        0 = Fill text
        1 = Stroke text
        2 = Fill then stroke
        3 = Invisible
        4 = Fill text and add to clipping path
        5 = Stroke text and add to clipping path
        6 = Fill then stroke and add to clipping path
        7 = Add to clipping path

        after we start clipping we mustn't change the mode back until after the ET
        """

        assert mode in (0,1,2,3,4,5,6,7), "mode must be in (0,1,2,3,4,5,6,7)"
        if (mode & 4)!=self._clipping:
            mode |= 4
            self._clipping = mode & 4
        if self._textRenderMode!=mode:
            self._textRenderMode = mode
            self._code.append('%d Tr' % mode)

    def setRise(self, rise):
        "Move text baseline up or down to allow superscript/subscripts"
        self._rise = rise
        self._y = self._y - rise    # + ?  _textLineMatrix?
        self._code.append('%s Ts' % fp_str(rise))

    def _formatText(self, text):
        "Generates PDF text output operator(s)"
        if log2vis and self.direction in ('LTR','RTL'):
            # Use pyfribidi to write the text in the correct visual order.
            text = log2vis(text, directionsMap.get(self.direction,DIR_ON),clean=True)
        canv = self._canvas
        font = pdfmetrics.getFont(self._fontname)
        R = []
        if font._dynamicFont:
            #it's a truetype font and should be utf8.  If an error is raised,
            for subset, t in font.splitString(text, canv._doc):
                if subset!=self._curSubset:
                    pdffontname = font.getSubsetInternalName(subset, canv._doc)
                    R.append("%s %s Tf %s TL" % (pdffontname, fp_str(self._fontsize), fp_str(self._leading)))
                    self._curSubset = subset
                R.append("(%s) Tj" % canv._escape(t))
        elif font._multiByte:
            #all the fonts should really work like this - let them know more about PDF...
            R.append("%s %s Tf %s TL" % (
                canv._doc.getInternalFontName(font.fontName),
                fp_str(self._fontsize),
                fp_str(self._leading)
                ))
            R.append("(%s) Tj" % font.formatForPdf(text))
        else:
            #convert to T1  coding
            fc = font
            if isBytes(text):
                try:
                    text = text.decode('utf8')
                except UnicodeDecodeError as e:
                    i,j = e.args[2:4]
                    raise UnicodeDecodeError(*(e.args[:4]+('%s\n%s-->%s<--%s' % (e.args[4],text[max(i-10,0):i],text[i:j],text[j:j+10]),)))

            for f, t in pdfmetrics.unicode2T1(text,[font]+font.substitutionFonts):
                if f!=fc:
                    R.append("%s %s Tf %s TL" % (canv._doc.getInternalFontName(f.fontName), fp_str(self._fontsize), fp_str(self._leading)))
                    fc = f
                R.append("(%s) Tj" % canv._escape(t))
            if font!=fc:
                R.append("%s %s Tf %s TL" % (canv._doc.getInternalFontName(self._fontname), fp_str(self._fontsize), fp_str(self._leading)))
        return ' '.join(R)

    def _textOut(self, text, TStar=0):
        "prints string at current point, ignores text cursor"
        self._code.append('%s%s' % (self._formatText(text), (TStar and ' T*' or '')))

    def textOut(self, text):
        """prints string at current point, text cursor moves across."""
        self._x = self._x + self._canvas.stringWidth(text, self._fontname, self._fontsize)
        self._code.append(self._formatText(text))

    def textLine(self, text=''):
        """prints string at current point, text cursor moves down.
        Can work with no argument to simply move the cursor down."""
        # Update the coordinates of the cursor
        self._x = self._x0
        if self._canvas.bottomup:
            self._y = self._y - self._leading
        else:
            self._y = self._y + self._leading

        # Update the location of the start of the line
        # self._x0 is unchanged
        self._y0 = self._y

        # Output the text followed by a PDF newline command
        self._code.append('%s T*' % self._formatText(text))

    def textLines(self, stuff, trim=1):
        """prints multi-line or newlined strings, moving down.  One
        comon use is to quote a multi-line block in your Python code;
        since this may be indented, by default it trims whitespace
        off each line and from the beginning; set trim=0 to preserve
        whitespace."""
        if isStr(stuff):
            lines = asUnicode(stuff).strip().split(u'\n')
            if trim==1:
                lines = [s.strip() for s in lines]
        elif isinstance(stuff,(tuple,list)):
            lines = stuff
        else:
            assert 1==0, "argument to textlines must be string,, list or tuple"

        # Output each line one at a time. This used to be a long-hand
        # copy of the textLine code, now called as a method.
        for line in lines:
            self.textLine(line)

    def __nonzero__(self):
        'PDFTextObject is true if it has something done after the init'
        return self._code != ['BT']

    def _setFillAlpha(self,v):
        self._canvas._doc.ensureMinPdfVersion('transparency')
        self._canvas._extgstate.set(self,'ca',v)

    def _setStrokeOverprint(self,v):
        self._canvas._extgstate.set(self,'OP',v)

    def _setFillOverprint(self,v):
        self._canvas._extgstate.set(self,'op',v)

    def _setOverprintMask(self,v):
        self._canvas._extgstate.set(self,'OPM',v and 1 or 0)
