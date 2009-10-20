# -*- coding: utf-8 -*-
#
# Copyright (C) 2000-2005 by Yasushi Saito (yasushi.saito@gmail.com)
# 
# Jockey is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2, or (at your option) any
# later version.
#
# Jockey is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
import color
import string
import pychart_util
import re
import theme
import afm.dir


__doc__ = """The module for manipulating texts and their attributes.

Pychart supports extensive sets of attributes in texts. All attributes
are specified via "escape sequences", starting from letter "/". For
example, the below examples draws string "Hello" using a 12-point font
at 60-degree angle:

/12/a60{}Hello

List of attributes:

/hA
    Specifies horizontal alignment of the text.  A is one of L (left
    alignment), R (right alignment), or C (center alignment).
/vA
    Specifies vertical alignment of the text.  A is one of "B"
    (bottom), "T" (top), " M" (middle).

/F{FONT}
    Switch to FONT font family.
/T
    Shorthand of /F{Times-Roman}.
/H
    Shorthand of /F{Helvetica}.
/C
    Shorthand of /F{Courier}.
/B
    Shorthand of /F{Bookman-Demi}.
/A
    Shorthand of /F{AvantGarde-Book}.
/P
    Shorthand of /F{Palatino}.
/S
    Shorthand of /F{Symbol}.
/b
    Switch to bold typeface.
/i
    Switch to italic typeface.
/o
    Switch to oblique typeface.
/DD
    Set font size to DD points.

    /20{}2001 space odyssey!

/cDD
    Set gray-scale to 0.DD. Gray-scale of 00 means black, 99 means white.

//, /{, /}
    Display `/', `@', or `@{'.
    
{ ... }
    Limit the effect of escape sequences. For example, the below
    example draws "Foo" at 12pt, "Bar" at 8pt, and "Baz" at 12pt.

    /12Foo{/8Bar}Baz
\n
    Break the line.
"""

# List of fonts for which their absence have been already warned.
_undefined_font_warned = {}

def _intern_afm(font, text):
    global _undefined_font_warned
    font2 = _font_aliases.has_key(font) and _font_aliases[font]
    if afm.dir.afm.has_key(font):
        return afm.dir.afm[font]
    if afm.dir.afm.has_key(font2):
        return afm.dir.afm[font2]

    try:        
        exec("import pychart.afm.%s" % re.sub("-", "_", font))
        return afm.dir.afm[font]
    except:
        if not font2 and not _undefined_font_warned.has_key(font):
            pychart_util.warn("Warning: unknown font '%s' while parsing '%s'" % (font, text))
            _undefined_font_warned[font] = 1
    
    if font2:
        try:
            exec("import pychart.afm.%s" % re.sub("-", "_", font2))
            return afm.dir.afm[font2]
        except:
            if not _undefined_font_warned.has_key(font):
                pychart_util.warn("Warning: unknown font '%s' while parsing '%s'" % (font, text))
                _undefined_font_warned[font] = 1
    return None    
def line_width(font, size, text):
    table = _intern_afm(font, text)
    if not table:
        return 0

    width = 0
    for ch in text:
        code = ord(ch)
        if code < len(table):
            width += table[code]
        else:
            width += 10000
            
    width = float(width) * size / 1000.0
    return width

_font_family_map = {'T': "Times",
                    'H': "Helvetica",
                    'C': "Courier",
                    'N': "Helvetica-Narrow",
                    'B': "Bookman-Demi", 
                    'A': "AvantGarde-Book",
                    'P': "Palatino",
                    'S': "Symbol"}

# Aliases for ghostscript font names.

_font_aliases = {
    'Bookman-Demi': "URWBookmanL-DemiBold%I",
    'Bookman-DemiItalic':	"URWBookmanL-DemiBoldItal",
    'Bookman-Demi-Italic':	"URWBookmanL-DemiBoldItal",
    'Bookman-Light':		"URWBookmanL-Ligh",
    'Bookman-LightItalic':		"URWBookmanL-LighItal",
    'Bookman-Light-Italic':		"URWBookmanL-LighItal",
    'Courier':		"NimbusMonL-Regu",
    'Courier-Oblique':	"NimbusMonL-ReguObli",
    'Courier-Bold':		"NimbusMonL-Bold",
    'Courier-BoldOblique':	"NimbusMonL-BoldObli",
    'AvantGarde-Book':	"URWGothicL-Book",
    'AvantGarde-BookOblique':	"URWGothicL-BookObli",
    'AvantGarde-Book-Oblique':	"URWGothicL-BookObli",
    'AvantGarde-Demi':	"URWGothicL-Demi",
    'AvantGarde-DemiOblique':	"URWGothicL-DemiObli",
    'AvantGarde-Demi-Oblique':	"URWGothicL-DemiObli",
    'Helvetica':		"NimbusSanL-Regu",
    'Helvetica-Oblique':	"NimbusSanL-ReguItal",
    'Helvetica-Bold':		"NimbusSanL-Bold",
    'Helvetica-BoldOblique':	"NimbusSanL-BoldItal",
    'Helvetica-Narrow': "NimbusSanL-ReguCond",
    'Helvetica-Narrow-Oblique': "NimbusSanL-ReguCondItal",
    'Helvetica-Narrow-Bold':		"NimbusSanL-BoldCond",
    'Helvetica-Narrow-BoldOblique':	"NimbusSanL-BoldCondItal",
    'Palatino-Roman':			"URWPalladioL-Roma",
    'Palatino':			"URWPalladioL-Roma",
    'Palatino-Italic':		"URWPalladioL-Ital",
    'Palatino-Bold':			"URWPalladioL-Bold",
    'Palatino-BoldItalic':		"URWPalladioL-BoldItal",
    'NewCenturySchlbk-Roman':		"CenturySchL-Roma",
    'NewCenturySchlbk':		"CenturySchL-Roma",
    'NewCenturySchlbk-Italic':	"CenturySchL-Ital",
    'NewCenturySchlbk-Bold':		"CenturySchL-Bold",
    'NewCenturySchlbk-BoldItalic':	"CenturySchL-BoldItal",
    'Times-Roman':			"NimbusRomNo9L-Regu",
    'Times':			"NimbusRomNo9L-Regu",
    'Times-Italic':			"NimbusRomNo9L-ReguItal",
    'Times-Bold':			"NimbusRomNo9L-Medi",
    'Times-BoldItalic':		"NimbusRomNo9L-MediItal",
    'Symbol':				"StandardSymL",
    'ZapfChancery-MediumItalic':	"URWChanceryL-MediItal",
    'ZapfChancery-Medium-Italic':	"URWChanceryL-MediItal",
    'ZapfDingbats':			"Dingbats"
}


class text_state:
    def copy(self):
        ts = text_state()
        ts.family = self.family
        ts.modifiers = list(self.modifiers)
        ts.size = self.size
        ts.line_height = self.line_height
        ts.color = self.color
        ts.halign = self.halign
        ts.valign = self.valign
        ts.angle = self.angle
        return ts
    def __init__(self):
        self.family = theme.default_font_family
        self.modifiers = [] # 'b' for bold, 'i' for italic, 'o' for oblique.
        self.size = theme.default_font_size
        self.line_height = theme.default_line_height or theme.default_font_size
        self.color = color.default
        self.halign = theme.default_font_halign
        self.valign = theme.default_font_valign
        self.angle = theme.default_font_angle
        
class text_iterator:
    def __init__(self, s):
        self.str = str(s)
        self.i = 0
        self.ts = text_state()
        self.stack = []
    def reset(self, s):
	self.str = str(s)
	self.i = 0

    def __return_state(self, ts, str):
	font_name = ts.family

        if ts.modifiers != []:
            is_bold = 0
            if 'b' in ts.modifiers:
                is_bold = 1
                font_name += "-Bold"
            if 'o' in ts.modifiers:
                if not is_bold:
                    font_name += "-"
                font_name += "Oblique"
            elif 'i' in ts.modifiers:
                if not is_bold:
                    font_name += "-"
                font_name += "Italic"
        elif font_name in ("Palatino", "Times", "NewCenturySchlbk"):
            font_name += "-Roman"
                
	return (font_name, ts.size, ts.line_height, ts.color,
                ts.halign, ts.valign, ts.angle, str)
    def __parse_float(self):
        istart = self.i
        while self.i < len(self.str) and self.str[self.i] in string.digits or self.str[self.i] == '.':
            self.i += 1
        return float(self.str[istart:self.i])
            
    def __parse_int(self):
        istart = self.i
        while self.i < len(self.str) and \
              (self.str[self.i] in string.digits or
               self.str[self.i] == '-'):
            self.i += 1
        return int(self.str[istart:self.i])
    def next(self):
        "Get the next text segment. Return an 8-element array: (FONTNAME, SIZE, LINEHEIGHT, COLOR, H_ALIGN, V_ALIGN, ANGLE, STR."
        l = []
        changed = 0
	self.old_state = self.ts.copy()
        
        while self.i < len(self.str):
            if self.str[self.i] == '/':
                self.i = self.i+1
                ch = self.str[self.i]
                self.i = self.i+1
		self.old_state = self.ts.copy()
                if ch == '/' or ch == '{' or ch == '}':
                    l.append(ch)
                elif _font_family_map.has_key(ch):
                    self.ts.family = _font_family_map[ch]
                    changed = 1
                elif ch == 'F':
                    # /F{font-family}
                    if self.str[self.i] != '{':
                        raise Exception, "'{' must follow /F in \"%s\"" % self.str
                    self.i += 1
                    istart = self.i
                    while self.str[self.i] != '}':
                        self.i += 1
                        if self.i >= len(self.str):
                            raise Exception, "Expecting /F{...}. in \"%s\"" % self.str
                    self.ts.family = self.str[istart:self.i]
                    self.i += 1
                    changed = 1
                    
                elif ch in string.digits:
                    self.i -= 1
                    self.ts.size = self.__parse_int()
                    self.ts.line_height = self.ts.size
                    changed = 1
                elif ch == 'l':
                    self.ts.line_height = self.__parse_int()
                    changed = 1
                elif ch == 'b':
                    self.ts.modifiers.append('b')
                    changed = 1
                elif ch == 'i':
                    self.ts.modifiers.append('i')
                    changed = 1
                elif ch == 'o':
                    self.ts.modifiers.append('q')
                    changed = 1
                elif ch == 'c':
                    self.ts.color = color.gray_scale(self.__parse_float())
                elif ch == 'v':
                    if self.str[self.i] not in "BTM":
                        raise Exception, "Undefined escape sequence: /v%c (%s)" % (self.str[self.i], self.str)
                    self.ts.valign = self.str[self.i]
                    self.i += 1
                    changed = 1
                elif ch == 'h':
                    if self.str[self.i] not in "LRC":
                        raise Exception, "Undefined escape sequence: /h%c (%s)" % (self.str[self.i], self.str)
                    self.ts.halign = self.str[self.i]
                    self.i += 1
                    changed = 1
                elif ch == 'a':
                    self.ts.angle = self.__parse_int()
                    changed = 1
                else:
                    raise Exception, "Undefined escape sequence: /%c (%s)" % (ch, self.str)
            elif self.str[self.i] == '{':
                self.stack.append(self.ts.copy())
                self.i += 1
            elif self.str[self.i] == '}':
                if len(self.stack) == 0:
                    raise ValueError, "unmatched '}' in \"%s\"" % (self.str)
                self.ts = self.stack[-1]
                del self.stack[-1]
                self.i += 1
		changed = 1
            else:
                l.append(self.str[self.i])
                self.i += 1

            if changed and len(l) > 0:
                return self.__return_state(self.old_state, ''.join(l))
            else:
                # font change in the beginning of the sequence doesn't count.
                self.old_state = self.ts.copy()
                changed = 0
        if len(l) > 0:
	    return self.__return_state(self.old_state, ''.join(l))
        else:
            return None

#
#

def unaligned_get_dimension(text):
    """Return the bounding box of the text, assuming that the left-bottom corner
    of the first letter of the text is at (0, 0). This procedure ignores
    /h, /v, and /a directives when calculating the BB; it just returns the
    alignment specifiers as a part of the return value. The return value is a
    tuple (width, height, halign, valign, angle)."""

    xmax = 0
    ymax = 0
    ymax = 0
    angle = None
    halign = None
    valign = None

    itr = text_iterator(None)
    for line in str(text).split("\n"):
        cur_height = 0
        cur_width = 0
	itr.reset(line)
        while 1:
            elem = itr.next()
            if not elem:
                break
            (font, size, line_height, color, new_h, new_v, new_a, chunk) = elem
            if halign != None and new_h != halign:
                raise Exception, "Only one /h can appear in string '%s'." % str(text)
            if valign != None and new_v != valign:
                raise Exception, "Only one /v can appear in string '%s'." % str(text)
            if angle != None and new_a != angle:
                raise Exception, "Only one /a can appear in string '%s'." % str(text)
            halign = new_h
            valign = new_v
            angle = new_a
            cur_width += line_width(font, size, chunk)
            cur_height = max(cur_height, line_height)
        xmax = max(cur_width, xmax)
        ymax += cur_height
    return (xmax, ymax,
            halign or theme.default_font_halign,
            valign or theme.default_font_valign,
            angle or theme.default_font_angle)

def get_dimension(text):
    """Return the bounding box of the <text>,
    assuming that the left-bottom corner
    of the first letter of the text is at (0, 0). This procedure ignores
    /h, /v, and /a directives when calculating the boundingbox; it just returns the
    alignment specifiers as a part of the return value. The return value is a
    tuple (width, height, halign, valign, angle)."""
    (xmax, ymax, halign, valign, angle) = unaligned_get_dimension(text)
    xmin = ymin = 0
    if halign == "C":
        xmin = -xmax / 2.0
        xmax = xmax / 2.0
    elif halign == "R":
        xmin = -xmax
        xmax = 0
    if valign == "M":
        ymin = -ymax / 2.0
        ymax = ymax / 2.0
    elif valign == "T":
        ymin = -ymax
        ymax = 0
    if angle != 0:
        (x0, y0) = pychart_util.rotate(xmin, ymin, angle)
        (x1, y1) = pychart_util.rotate(xmax, ymin, angle)
        (x2, y2) = pychart_util.rotate(xmin, ymax, angle)
        (x3, y3) = pychart_util.rotate(xmax, ymax, angle)
        xmax = max(x0, x1, x2, x3)
        xmin = min(x0, x1, x2, x3)
        ymax = max(y0, y1, y2, y3)
        ymin = min(y0, y1, y2, y3)
        return (xmin, xmax, ymin, ymax)
    return (xmin, xmax, ymin, ymax)

def unaligned_text_width(text):
    x = unaligned_get_dimension(text)
    return x[0]

def text_width(text):
    """Return the width of the <text> in points."""
    (xmin, xmax, d1, d2) = get_dimension(text)
    return xmax-xmin

def unaligned_text_height(text):
    x = unaligned_get_dimension(text)
    return x[1]

def text_height(text):
    """Return the total height of the <text> and the length from the
    base point to the top of the text box."""
    (d1, d2, ymin, ymax) = get_dimension(text)
    return (ymax-ymin, ymax)

def get_align(text):
    "Return (halign, valign, angle) of the <text>."
    (x1, x2, h, v, a) = unaligned_get_dimension(text)
    return (h, v, a)

def quotemeta(text):
    """Quote letters with special meanings in pychart so that <text> will display
    as-is when passed to canvas.show(). 

>>> font.quotemeta("foo/bar")
"foo//bar"
"""
    text = re.sub("/", "//", text)
    text = re.sub("\\{", "/{", text)
    text = re.sub("\\}", "/}", text)
    return text
