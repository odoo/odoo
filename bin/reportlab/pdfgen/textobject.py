#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/pdfgen/textobject.py
__version__=''' $Id$ '''
__doc__="""
PDFTextObject is an efficient way to add text to a Canvas. Do not
instantiate directly, obtain one from the Canvas instead.

Progress Reports:
8.83, 2000-01-13, gmcm:
    created from pdfgen.py
"""

import string
from types import *
from reportlab.lib import colors
from reportlab.lib.colors import ColorType
from reportlab.lib.utils import fp_str
from reportlab.pdfbase import pdfmetrics

_SeqTypes=(TupleType,ListType)


class PDFTextObject:
    """PDF logically separates text and graphics drawing; text
    operations need to be bracketed between BT (Begin text) and
    ET operators. This class ensures text operations are
    properly encapusalted. Ask the canvas for a text object
    with beginText(x, y).  Do not construct one directly.
    Do not use multiple text objects in parallel; PDF is
    not multi-threaded!

    It keeps track of x and y coordinates relative to its origin."""

    def __init__(self, canvas, x=0,y=0):
        self._code = ['BT']    #no point in [] then append RGB
        self._canvas = canvas  #canvas sets this so it has access to size info
        self._fontname = self._canvas._fontname
        self._fontsize = self._canvas._fontsize
        self._leading = self._canvas._leading
        font = pdfmetrics.getFont(self._fontname)
        self._dynamicFont = getattr(font, '_dynamicFont', 0)
        self._curSubset = -1

        self.setTextOrigin(x, y)

    def getCode(self):
        "pack onto one line; used internally"
        self._code.append('ET')
        return string.join(self._code, ' ')

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
            L = string.split(self._code[-1])
            if len(L)==3:
                del self._code[-1]
            else:
                self._code[-1] = string.join(L[:-4])

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
        self._dynamicFont = getattr(font, '_dynamicFont', 0)
        if self._dynamicFont:
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
        self._dynamicFont = getattr(font, '_dynamicFont', 0)
        if self._dynamicFont:
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
        7 = Add to clipping path"""

        assert mode in (0,1,2,3,4,5,6,7), "mode must be in (0,1,2,3,4,5,6,7)"
        self._textRenderMode = mode
        self._code.append('%d Tr' % mode)

    def setRise(self, rise):
        "Move text baseline up or down to allow superscrip/subscripts"
        self._rise = rise
        self._y = self._y - rise    # + ?  _textLineMatrix?
        self._code.append('%s Ts' % fp_str(rise))

    def setStrokeColorRGB(self, r, g, b):
        self._strokeColorRGB = (r, g, b)
        self._code.append('%s RG' % fp_str(r,g,b))

    def setFillColorRGB(self, r, g, b):
        self._fillColorRGB = (r, g, b)
        self._code.append('%s rg' % fp_str(r,g,b))

    def setFillColorCMYK(self, c, m, y, k):
        """Takes 4 arguments between 0.0 and 1.0"""
        self._fillColorCMYK = (c, m, y, k)
        self._code.append('%s k' % fp_str(c, m, y, k))

    def setStrokeColorCMYK(self, c, m, y, k):
        """Takes 4 arguments between 0.0 and 1.0"""
        self._strokeColorCMYK = (c, m, y, k)
        self._code.append('%s K' % fp_str(c, m, y, k))

    def setFillColor(self, aColor):
        """Takes a color object, allowing colors to be referred to by name"""
        if type(aColor) == ColorType:
            rgb = (aColor.red, aColor.green, aColor.blue)
            self._fillColorRGB = rgb
            self._code.append('%s rg' % fp_str(rgb) )
        elif type(aColor) in _SeqTypes:
            l = len(aColor)
            if l==3:
                self._fillColorRGB = aColor
                self._code.append('%s rg' % fp_str(aColor) )
            elif l==4:
                self.setFillColorCMYK(self, aColor[0], aColor[1], aColor[2], aColor[3])
            else:
                raise 'Unknown color', str(aColor)
        else:
            raise 'Unknown color', str(aColor)

    def setStrokeColor(self, aColor):
        """Takes a color object, allowing colors to be referred to by name"""
        if type(aColor) == ColorType:
            rgb = (aColor.red, aColor.green, aColor.blue)
            self._strokeColorRGB = rgb
            self._code.append('%s RG' % fp_str(rgb) )
        elif type(aColor) in _SeqTypes:
            l = len(aColor)
            if l==3:
                self._strokeColorRGB = aColor
                self._code.append('%s RG' % fp_str(aColor) )
            elif l==4:
                self.setStrokeColorCMYK(self, aColor[0], aColor[1], aColor[2], aColor[3])
            else:
                raise 'Unknown color', str(aColor)
        else:
            raise 'Unknown color', str(aColor)

    def setFillGray(self, gray):
        """Sets the gray level; 0.0=black, 1.0=white"""
        self._fillColorRGB = (gray, gray, gray)
        self._code.append('%s g' % fp_str(gray))

    def setStrokeGray(self, gray):
        """Sets the gray level; 0.0=black, 1.0=white"""
        self._strokeColorRGB = (gray, gray, gray)
        self._code.append('%s G' % fp_str(gray))

    def _formatText(self, text):
        "Generates PDF text output operator(s)"
        if self._dynamicFont:
            #it's a truetype font and should be utf8.  If an error is raised,
            
            results = []
            font = pdfmetrics.getFont(self._fontname)
            try: #assume UTF8
                stuff = font.splitString(text, self._canvas._doc)
            except UnicodeDecodeError:
                #assume latin1 as fallback
                from reportlab.pdfbase.ttfonts import latin1_to_utf8
                from reportlab.lib.logger import warnOnce
                warnOnce('non-utf8 data fed to truetype font, assuming latin-1 data')
                text = latin1_to_utf8(text)
                stuff = font.splitString(text, self._canvas._doc)
            for subset, chunk in stuff:
                if subset != self._curSubset:
                    pdffontname = font.getSubsetInternalName(subset, self._canvas._doc)
                    results.append("%s %s Tf %s TL" % (pdffontname, fp_str(self._fontsize), fp_str(self._leading)))
                    self._curSubset = subset
                chunk = self._canvas._escape(chunk)
                results.append("(%s) Tj" % chunk)
            return string.join(results, ' ')
        else:
            text = self._canvas._escape(text)
            return "(%s) Tj" % text

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
        if type(stuff) == StringType:
            lines = string.split(string.strip(stuff), '\n')
            if trim==1:
                lines = map(string.strip,lines)
        elif type(stuff) == ListType:
            lines = stuff
        elif type(stuff) == TupleType:
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
