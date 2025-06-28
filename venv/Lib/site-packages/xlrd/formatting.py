# -*- coding: utf-8 -*-
# Copyright (c) 2005-2012 Stephen John Machin, Lingfo Pty Ltd
# This module is part of the xlrd package, which is released under a
# BSD-style licence.
# No part of the content of this file was derived from the works of
# David Giffin.
"""
Module for formatting information.
"""

from __future__ import print_function

import re
from struct import unpack

from .biffh import (
    FDT, FGE, FNU, FTX, FUN, XL_CELL_DATE, XL_CELL_NUMBER, XL_CELL_TEXT,
    XL_FORMAT, XL_FORMAT2, BaseObject, XLRDError, fprintf, unpack_string,
    unpack_unicode, upkbits, upkbitsL,
)
from .timemachine import *

DEBUG = 0

_cellty_from_fmtty = {
    FNU: XL_CELL_NUMBER,
    FUN: XL_CELL_NUMBER,
    FGE: XL_CELL_NUMBER,
    FDT: XL_CELL_DATE,
    FTX: XL_CELL_NUMBER, # Yes, a number can be formatted as text.
}

excel_default_palette_b5 = (
    (  0,   0,   0), (255, 255, 255), (255,   0,   0), (  0, 255,   0),
    (  0,   0, 255), (255, 255,   0), (255,   0, 255), (  0, 255, 255),
    (128,   0,   0), (  0, 128,   0), (  0,   0, 128), (128, 128,   0),
    (128,   0, 128), (  0, 128, 128), (192, 192, 192), (128, 128, 128),
    (153, 153, 255), (153,  51, 102), (255, 255, 204), (204, 255, 255),
    (102,   0, 102), (255, 128, 128), (  0, 102, 204), (204, 204, 255),
    (  0,   0, 128), (255,   0, 255), (255, 255,   0), (  0, 255, 255),
    (128,   0, 128), (128,   0,   0), (  0, 128, 128), (  0,   0, 255),
    (  0, 204, 255), (204, 255, 255), (204, 255, 204), (255, 255, 153),
    (153, 204, 255), (255, 153, 204), (204, 153, 255), (227, 227, 227),
    ( 51, 102, 255), ( 51, 204, 204), (153, 204,   0), (255, 204,   0),
    (255, 153,   0), (255, 102,   0), (102, 102, 153), (150, 150, 150),
    (  0,  51, 102), ( 51, 153, 102), (  0,  51,   0), ( 51,  51,   0),
    (153,  51,   0), (153,  51, 102), ( 51,  51, 153), ( 51,  51,  51),
)

excel_default_palette_b2 = excel_default_palette_b5[:16]

# Following table borrowed from Gnumeric 1.4 source.
# Checked against OOo docs and MS docs.
excel_default_palette_b8 = ( # (red, green, blue)
    (  0,  0,  0), (255,255,255), (255,  0,  0), (  0,255,  0), # 0
    (  0,  0,255), (255,255,  0), (255,  0,255), (  0,255,255), # 4
    (128,  0,  0), (  0,128,  0), (  0,  0,128), (128,128,  0), # 8
    (128,  0,128), (  0,128,128), (192,192,192), (128,128,128), # 12
    (153,153,255), (153, 51,102), (255,255,204), (204,255,255), # 16
    (102,  0,102), (255,128,128), (  0,102,204), (204,204,255), # 20
    (  0,  0,128), (255,  0,255), (255,255,  0), (  0,255,255), # 24
    (128,  0,128), (128,  0,  0), (  0,128,128), (  0,  0,255), # 28
    (  0,204,255), (204,255,255), (204,255,204), (255,255,153), # 32
    (153,204,255), (255,153,204), (204,153,255), (255,204,153), # 36
    ( 51,102,255), ( 51,204,204), (153,204,  0), (255,204,  0), # 40
    (255,153,  0), (255,102,  0), (102,102,153), (150,150,150), # 44
    (  0, 51,102), ( 51,153,102), (  0, 51,  0), ( 51, 51,  0), # 48
    (153, 51,  0), (153, 51,102), ( 51, 51,153), ( 51, 51, 51), # 52
)

default_palette = {
    80: excel_default_palette_b8,
    70: excel_default_palette_b5,
    50: excel_default_palette_b5,
    45: excel_default_palette_b2,
    40: excel_default_palette_b2,
    30: excel_default_palette_b2,
    21: excel_default_palette_b2,
    20: excel_default_palette_b2,
}

# 00H = Normal
# 01H = RowLevel_lv (see next field)
# 02H = ColLevel_lv (see next field)
# 03H = Comma
# 04H = Currency
# 05H = Percent
# 06H = Comma [0] (BIFF4-BIFF8)
# 07H = Currency [0] (BIFF4-BIFF8)
# 08H = Hyperlink (BIFF8)
# 09H = Followed Hyperlink (BIFF8)
built_in_style_names = [
    "Normal",
    "RowLevel_",
    "ColLevel_",
    "Comma",
    "Currency",
    "Percent",
    "Comma [0]",
    "Currency [0]",
    "Hyperlink",
    "Followed Hyperlink",
]

def initialise_colour_map(book):
    book.colour_map = {}
    book.colour_indexes_used = {}
    if not book.formatting_info:
        return
    # Add the 8 invariant colours
    for i in xrange(8):
        book.colour_map[i] = excel_default_palette_b8[i]
    # Add the default palette depending on the version
    dpal = default_palette[book.biff_version]
    ndpal = len(dpal)
    for i in xrange(ndpal):
        book.colour_map[i+8] = dpal[i]
    # Add the specials -- None means the RGB value is not known
    # System window text colour for border lines
    book.colour_map[ndpal+8] = None
    # System window background colour for pattern background
    book.colour_map[ndpal+8+1] = None
    # System ToolTip text colour (used in note objects)
    book.colour_map[0x51] = None
    # 32767, system window text colour for fonts
    book.colour_map[0x7FFF] = None


def nearest_colour_index(colour_map, rgb, debug=0):
    """
    General purpose function. Uses Euclidean distance.
    So far used only for pre-BIFF8 ``WINDOW2`` record.
    Doesn't have to be fast.
    Doesn't have to be fancy.
    """
    best_metric = 3 * 256 * 256
    best_colourx = 0
    for colourx, cand_rgb in colour_map.items():
        if cand_rgb is None:
            continue
        metric = 0
        for v1, v2 in zip(rgb, cand_rgb):
            metric += (v1 - v2) * (v1 - v2)
        if metric < best_metric:
            best_metric = metric
            best_colourx = colourx
            if metric == 0:
                break
    if 0 and debug:
        print("nearest_colour_index for %r is %r -> %r; best_metric is %d"
            % (rgb, best_colourx, colour_map[best_colourx], best_metric))
    return best_colourx

class EqNeAttrs(object):
    """
    This mixin class exists solely so that :class:`Format`, :class:`Font`, and
    :class:`XF` objects can be compared by value of their attributes.
    """

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return self.__dict__ != other.__dict__

class Font(BaseObject, EqNeAttrs):
    """
    An Excel "font" contains the details of not only what is normally
    considered a font, but also several other display attributes.
    Items correspond to those in the Excel UI's Format -> Cells -> Font tab.

    .. versionadded:: 0.6.1
    """

    #: 1 = Characters are bold. Redundant; see "weight" attribute.
    bold = 0

    #: Values::
    #:
    #:   0 = ANSI Latin
    #:   1 = System default
    #:   2 = Symbol,
    #:   77 = Apple Roman,
    #:   128 = ANSI Japanese Shift-JIS,
    #:   129 = ANSI Korean (Hangul),
    #:   130 = ANSI Korean (Johab),
    #:   134 = ANSI Chinese Simplified GBK,
    #:   136 = ANSI Chinese Traditional BIG5,
    #:   161 = ANSI Greek,
    #:   162 = ANSI Turkish,
    #:   163 = ANSI Vietnamese,
    #:   177 = ANSI Hebrew,
    #:   178 = ANSI Arabic,
    #:   186 = ANSI Baltic,
    #:   204 = ANSI Cyrillic,
    #:   222 = ANSI Thai,
    #:   238 = ANSI Latin II (Central European),
    #:   255 = OEM Latin I
    character_set = 0

    #: An explanation of "colour index" is given in :ref:`palette`.
    colour_index = 0

    #: 1 = Superscript, 2 = Subscript.
    escapement = 0

    #: Values::
    #:
    #:   0 = None (unknown or don't care)
    #:   1 = Roman (variable width, serifed)
    #:   2 = Swiss (variable width, sans-serifed)
    #:   3 = Modern (fixed width, serifed or sans-serifed)
    #:   4 = Script (cursive)
    #:   5 = Decorative (specialised, for example Old English, Fraktur)
    family = 0

    #: The 0-based index used to refer to this Font() instance.
    #: Note that index 4 is never used; xlrd supplies a dummy place-holder.
    font_index = 0

    #: Height of the font (in twips). A twip = 1/20 of a point.
    height = 0

    #: 1 = Characters are italic.
    italic = 0

    #: The name of the font. Example: ``"Arial"``.
    name = UNICODE_LITERAL("")

    #: 1 = Characters are struck out.
    struck_out = 0

    #: Values::
    #:
    #:   0 = None
    #:   1 = Single;  0x21 (33) = Single accounting
    #:   2 = Double;  0x22 (34) = Double accounting
    underline_type = 0

    #: 1 = Characters are underlined. Redundant; see
    #: :attr:`underline_type` attribute.
    underlined = 0

    #: Font weight (100-1000). Standard values are 400 for normal text
    #: and 700 for bold text.
    weight = 400

    #: 1 = Font is outline style (Macintosh only)
    outline = 0

    #: 1 = Font is shadow style (Macintosh only)
    shadow = 0

def handle_efont(book, data): # BIFF2 only
    if not book.formatting_info:
        return
    book.font_list[-1].colour_index = unpack('<H', data)[0]

def handle_font(book, data):
    if not book.formatting_info:
        return
    if not book.encoding:
        book.derive_encoding()
    blah = DEBUG or book.verbosity >= 2
    bv = book.biff_version
    k = len(book.font_list)
    if k == 4:
        f = Font()
        f.name = UNICODE_LITERAL('Dummy Font')
        f.font_index = k
        book.font_list.append(f)
        k += 1
    f = Font()
    f.font_index = k
    book.font_list.append(f)
    if bv >= 50:
        (
            f.height, option_flags, f.colour_index, f.weight,
            f.escapement, f.underline_type, f.family,
            f.character_set,
        ) = unpack('<HHHHHBBB', data[0:13])
        f.bold = option_flags & 1
        f.italic = (option_flags & 2) >> 1
        f.underlined = (option_flags & 4) >> 2
        f.struck_out = (option_flags & 8) >> 3
        f.outline = (option_flags & 16) >> 4
        f.shadow = (option_flags & 32) >> 5
        if bv >= 80:
            f.name = unpack_unicode(data, 14, lenlen=1)
        else:
            f.name = unpack_string(data, 14, book.encoding, lenlen=1)
    elif bv >= 30:
        f.height, option_flags, f.colour_index = unpack('<HHH', data[0:6])
        f.bold = option_flags & 1
        f.italic = (option_flags & 2) >> 1
        f.underlined = (option_flags & 4) >> 2
        f.struck_out = (option_flags & 8) >> 3
        f.outline = (option_flags & 16) >> 4
        f.shadow = (option_flags & 32) >> 5
        f.name = unpack_string(data, 6, book.encoding, lenlen=1)
        # Now cook up the remaining attributes ...
        f.weight = [400, 700][f.bold]
        f.escapement = 0 # None
        f.underline_type = f.underlined # None or Single
        f.family = 0 # Unknown / don't care
        f.character_set = 1 # System default (0 means "ANSI Latin")
    else: # BIFF2
        f.height, option_flags = unpack('<HH', data[0:4])
        f.colour_index = 0x7FFF # "system window text colour"
        f.bold = option_flags & 1
        f.italic = (option_flags & 2) >> 1
        f.underlined = (option_flags & 4) >> 2
        f.struck_out = (option_flags & 8) >> 3
        f.outline = 0
        f.shadow = 0
        f.name = unpack_string(data, 4, book.encoding, lenlen=1)
        # Now cook up the remaining attributes ...
        f.weight = [400, 700][f.bold]
        f.escapement = 0 # None
        f.underline_type = f.underlined # None or Single
        f.family = 0 # Unknown / don't care
        f.character_set = 1 # System default (0 means "ANSI Latin")
    if blah:
        f.dump(
            book.logfile,
            header="--- handle_font: font[%d] ---" % f.font_index,
            footer="-------------------",
        )

# === "Number formats" ===

class Format(BaseObject, EqNeAttrs):
    """
    "Number format" information from a ``FORMAT`` record.

    .. versionadded:: 0.6.1
    """

    #: The key into :attr:`~xlrd.book.Book.format_map`
    format_key = 0

    #: A classification that has been inferred from the format string.
    #: Currently, this is used only to distinguish between numbers and dates.
    #: Values::
    #:
    #:   FUN = 0 # unknown
    #:   FDT = 1 # date
    #:   FNU = 2 # number
    #:   FGE = 3 # general
    #:   FTX = 4 # text
    type = FUN

    #: The format string
    format_str = UNICODE_LITERAL('')

    def __init__(self, format_key, ty, format_str):
        self.format_key = format_key
        self.type = ty
        self.format_str = format_str

std_format_strings = {
    # "std" == "standard for US English locale"
    # #### TODO ... a lot of work to tailor these to the user's locale.
    # See e.g. gnumeric-1.x.y/src/formats.c
    0x00: "General",
    0x01: "0",
    0x02: "0.00",
    0x03: "#,##0",
    0x04: "#,##0.00",
    0x05: "$#,##0_);($#,##0)",
    0x06: "$#,##0_);[Red]($#,##0)",
    0x07: "$#,##0.00_);($#,##0.00)",
    0x08: "$#,##0.00_);[Red]($#,##0.00)",
    0x09: "0%",
    0x0a: "0.00%",
    0x0b: "0.00E+00",
    0x0c: "# ?/?",
    0x0d: "# ??/??",
    0x0e: "m/d/yy",
    0x0f: "d-mmm-yy",
    0x10: "d-mmm",
    0x11: "mmm-yy",
    0x12: "h:mm AM/PM",
    0x13: "h:mm:ss AM/PM",
    0x14: "h:mm",
    0x15: "h:mm:ss",
    0x16: "m/d/yy h:mm",
    0x25: "#,##0_);(#,##0)",
    0x26: "#,##0_);[Red](#,##0)",
    0x27: "#,##0.00_);(#,##0.00)",
    0x28: "#,##0.00_);[Red](#,##0.00)",
    0x29: "_(* #,##0_);_(* (#,##0);_(* \"-\"_);_(@_)",
    0x2a: "_($* #,##0_);_($* (#,##0);_($* \"-\"_);_(@_)",
    0x2b: "_(* #,##0.00_);_(* (#,##0.00);_(* \"-\"??_);_(@_)",
    0x2c: "_($* #,##0.00_);_($* (#,##0.00);_($* \"-\"??_);_(@_)",
    0x2d: "mm:ss",
    0x2e: "[h]:mm:ss",
    0x2f: "mm:ss.0",
    0x30: "##0.0E+0",
    0x31: "@",
}

fmt_code_ranges = [ # both-inclusive ranges of "standard" format codes
    # Source: the openoffice.org doc't
    # and the OOXML spec Part 4, section 3.8.30
    ( 0,  0, FGE),
    ( 1, 13, FNU),
    (14, 22, FDT),
    (27, 36, FDT), # CJK date formats
    (37, 44, FNU),
    (45, 47, FDT),
    (48, 48, FNU),
    (49, 49, FTX),
    # Gnumeric assumes (or assumed) that built-in formats finish at 49, not at 163
    (50, 58, FDT), # CJK date formats
    (59, 62, FNU), # Thai number (currency?) formats
    (67, 70, FNU), # Thai number (currency?) formats
    (71, 81, FDT), # Thai date formats
]

std_format_code_types = {}
for lo, hi, ty in fmt_code_ranges:
    for x in xrange(lo, hi+1):
        std_format_code_types[x] = ty
del lo, hi, ty, x

date_chars = UNICODE_LITERAL('ymdhs') # year, month/minute, day, hour, second
date_char_dict = {}
for _c in date_chars + date_chars.upper():
    date_char_dict[_c] = 5
del _c, date_chars

skip_char_dict = {}
for _c in UNICODE_LITERAL('$-+/(): '):
    skip_char_dict[_c] = 1

num_char_dict = {
    UNICODE_LITERAL('0'): 5,
    UNICODE_LITERAL('#'): 5,
    UNICODE_LITERAL('?'): 5,
}

non_date_formats = {
    UNICODE_LITERAL('0.00E+00'):1,
    UNICODE_LITERAL('##0.0E+0'):1,
    UNICODE_LITERAL('General') :1,
    UNICODE_LITERAL('GENERAL') :1, # OOo Calc 1.1.4 does this.
    UNICODE_LITERAL('general') :1,  # pyExcelerator 0.6.3 does this.
    UNICODE_LITERAL('@')       :1,
}

fmt_bracketed_sub = re.compile(r'\[[^]]*\]').sub

# Boolean format strings (actual cases)
# '"Yes";"Yes";"No"'
# '"True";"True";"False"'
# '"On";"On";"Off"'

def is_date_format_string(book, fmt):
    # Heuristics:
    # Ignore "text" and [stuff in square brackets (aarrgghh -- see below)].
    # Handle backslashed-escaped chars properly.
    # E.g. hh\hmm\mss\s should produce a display like 23h59m59s
    # Date formats have one or more of ymdhs (caseless) in them.
    # Numeric formats have # and 0.
    # N.B. 'General"."' hence get rid of "text" first.
    # TODO: Find where formats are interpreted in Gnumeric
    # TODO: '[h]\\ \\h\\o\\u\\r\\s' ([h] means don't care about hours > 23)
    state = 0
    s = ''

    for c in fmt:
        if state == 0:
            if c == UNICODE_LITERAL('"'):
                state = 1
            elif c in UNICODE_LITERAL(r"\_*"):
                state = 2
            elif c in skip_char_dict:
                pass
            else:
                s += c
        elif state == 1:
            if c == UNICODE_LITERAL('"'):
                state = 0
        elif state == 2:
            # Ignore char after backslash, underscore or asterisk
            state = 0
        assert 0 <= state <= 2
    if book.verbosity >= 4:
        print("is_date_format_string: reduced format is %s" % REPR(s), file=book.logfile)
    s = fmt_bracketed_sub('', s)
    if s in non_date_formats:
        return False
    state = 0
    separator = ";"
    got_sep = 0
    date_count = num_count = 0
    for c in s:
        if c in date_char_dict:
            date_count += date_char_dict[c]
        elif c in num_char_dict:
            num_count += num_char_dict[c]
        elif c == separator:
            got_sep = 1
    # print num_count, date_count, repr(fmt)
    if date_count and not num_count:
        return True
    if num_count and not date_count:
        return False
    if date_count:
        if book.verbosity:
            fprintf(book.logfile,
                'WARNING *** is_date_format: ambiguous d=%d n=%d fmt=%r\n',
                date_count, num_count, fmt)
    elif not got_sep:
        if book.verbosity:
            fprintf(book.logfile,
                "WARNING *** format %r produces constant result\n",
                fmt)
    return date_count > num_count

def handle_format(self, data, rectype=XL_FORMAT):
    DEBUG = 0
    bv = self.biff_version
    if rectype == XL_FORMAT2:
        bv = min(bv, 30)
    if not self.encoding:
        self.derive_encoding()
    strpos = 2
    if bv >= 50:
        fmtkey = unpack('<H', data[0:2])[0]
    else:
        fmtkey = self.actualfmtcount
        if bv <= 30:
            strpos = 0
    self.actualfmtcount += 1
    if bv >= 80:
        unistrg = unpack_unicode(data, 2)
    else:
        unistrg = unpack_string(data, strpos, self.encoding, lenlen=1)
    blah = DEBUG or self.verbosity >= 3
    if blah:
        fprintf(self.logfile,
            "FORMAT: count=%d fmtkey=0x%04x (%d) s=%r\n",
            self.actualfmtcount, fmtkey, fmtkey, unistrg)
    is_date_s = self.is_date_format_string(unistrg)
    ty = [FGE, FDT][is_date_s]
    if not(fmtkey > 163 or bv < 50):
        # user_defined if fmtkey > 163
        # N.B. Gnumeric incorrectly starts these at 50 instead of 164 :-(
        # if earlier than BIFF 5, standard info is useless
        std_ty = std_format_code_types.get(fmtkey, FUN)
        # print "std ty", std_ty
        is_date_c = std_ty == FDT
        if self.verbosity and 0 < fmtkey < 50 and (is_date_c ^ is_date_s):
            DEBUG = 2
            fprintf(self.logfile,
                "WARNING *** Conflict between "
                "std format key %d and its format string %r\n",
                fmtkey, unistrg)
    if DEBUG == 2:
        fprintf(self.logfile,
            "ty: %d; is_date_c: %r; is_date_s: %r; fmt_strg: %r",
            ty, is_date_c, is_date_s, unistrg)
    fmtobj = Format(fmtkey, ty, unistrg)
    if blah:
        fmtobj.dump(self.logfile,
            header="--- handle_format [%d] ---" % (self.actualfmtcount-1, ))
    self.format_map[fmtkey] = fmtobj
    self.format_list.append(fmtobj)

# =============================================================================

def handle_palette(book, data):
    if not book.formatting_info:
        return
    blah = DEBUG or book.verbosity >= 2
    n_colours, = unpack('<H', data[:2])
    expected_n_colours = (16, 56)[book.biff_version >= 50]
    if (DEBUG or book.verbosity >= 1) and n_colours != expected_n_colours:
        fprintf(book.logfile,
            "NOTE *** Expected %d colours in PALETTE record, found %d\n",
            expected_n_colours, n_colours)
    elif blah:
        fprintf(book.logfile,
            "PALETTE record with %d colours\n", n_colours)
    fmt = '<xx%di' % n_colours # use i to avoid long integers
    expected_size = 4 * n_colours + 2
    actual_size = len(data)
    tolerance = 4
    if not expected_size <= actual_size <= expected_size + tolerance:
        raise XLRDError('PALETTE record: expected size %d, actual size %d' % (expected_size, actual_size))
    colours = unpack(fmt, data[:expected_size])
    assert book.palette_record == [] # There should be only 1 PALETTE record
    # a colour will be 0xbbggrr
    # IOW, red is at the little end
    for i in xrange(n_colours):
        c = colours[i]
        red   =  c        & 0xff
        green = (c >>  8) & 0xff
        blue  = (c >> 16) & 0xff
        old_rgb = book.colour_map[8+i]
        new_rgb = (red, green, blue)
        book.palette_record.append(new_rgb)
        book.colour_map[8+i] = new_rgb
        if blah:
            if new_rgb != old_rgb:
                print("%2d: %r -> %r" % (i, old_rgb, new_rgb), file=book.logfile)

def palette_epilogue(book):
    # Check colour indexes in fonts etc.
    # This must be done here as FONT records
    # come *before* the PALETTE record :-(
    for font in book.font_list:
        if font.font_index == 4: # the missing font record
            continue
        cx = font.colour_index
        if cx == 0x7fff: # system window text colour
            continue
        if cx in book.colour_map:
            book.colour_indexes_used[cx] = 1
        elif book.verbosity:
            print("Size of colour table:", len(book.colour_map), file=book.logfile)
            fprintf(book.logfile, "*** Font #%d (%r): colour index 0x%04x is unknown\n",
                font.font_index, font.name, cx)
    if book.verbosity >= 1:
        used = sorted(book.colour_indexes_used.keys())
        print("\nColour indexes used:\n%r\n" % used, file=book.logfile)

def handle_style(book, data):
    if not book.formatting_info:
        return
    blah = DEBUG or book.verbosity >= 2
    bv = book.biff_version
    flag_and_xfx, built_in_id, level = unpack('<HBB', data[:4])
    xf_index = flag_and_xfx & 0x0fff
    if data == b"\0\0\0\0" and "Normal" not in book.style_name_map:
        # Erroneous record (doesn't have built-in bit set).
        # Example file supplied by Jeff Bell.
        built_in = 1
        built_in_id = 0
        xf_index = 0
        name = "Normal"
        level = 255
    elif flag_and_xfx & 0x8000:
        # built-in style
        built_in = 1
        name = built_in_style_names[built_in_id]
        if 1 <= built_in_id <= 2:
            name += str(level + 1)
    else:
        # user-defined style
        built_in = 0
        built_in_id = 0
        level = 0
        if bv >= 80:
            try:
                name = unpack_unicode(data, 2, lenlen=2)
            except UnicodeDecodeError:
                print("STYLE: built_in=%d xf_index=%d built_in_id=%d level=%d"
                    % (built_in, xf_index, built_in_id, level), file=book.logfile)
                print("raw bytes:", repr(data[2:]), file=book.logfile)
                raise
        else:
            name = unpack_string(data, 2, book.encoding, lenlen=1)
        if blah and not name:
            print("WARNING *** A user-defined style has a zero-length name", file=book.logfile)
    book.style_name_map[name] = (built_in, xf_index)
    if blah:
        fprintf(book.logfile, "STYLE: built_in=%d xf_index=%d built_in_id=%d level=%d name=%r\n",
            built_in, xf_index, built_in_id, level, name)

def check_colour_indexes_in_obj(book, obj, orig_index):
    alist = sorted(obj.__dict__.items())
    for attr, nobj in alist:
        if hasattr(nobj, 'dump'):
            check_colour_indexes_in_obj(book, nobj, orig_index)
        elif attr.find('colour_index') >= 0:
            if nobj in book.colour_map:
                book.colour_indexes_used[nobj] = 1
                continue
            oname = obj.__class__.__name__
            print("*** xf #%d : %s.%s =  0x%04x (unknown)"
                % (orig_index, oname, attr, nobj), file=book.logfile)

def fill_in_standard_formats(book):
    for x in std_format_code_types.keys():
        if x not in book.format_map:
            ty = std_format_code_types[x]
            # Note: many standard format codes (mostly CJK date formats) have
            # format strings that vary by locale; xlrd does not (yet)
            # handle those; the type (date or numeric) is recorded but the fmt_str will be None.
            fmt_str = std_format_strings.get(x)
            fmtobj = Format(x, ty, fmt_str)
            book.format_map[x] = fmtobj

def handle_xf(self, data):
    # self is a Book instance
    # DEBUG = 0
    blah = DEBUG or self.verbosity >= 3
    bv = self.biff_version
    xf = XF()
    xf.alignment = XFAlignment()
    xf.alignment.indent_level = 0
    xf.alignment.shrink_to_fit = 0
    xf.alignment.text_direction = 0
    xf.border = XFBorder()
    xf.border.diag_up = 0
    xf.border.diag_down = 0
    xf.border.diag_colour_index = 0
    xf.border.diag_line_style = 0 # no line
    xf.background = XFBackground()
    xf.protection = XFProtection()
    # fill in the known standard formats
    if bv >= 50 and not self.xfcount:
        # i.e. do this once before we process the first XF record
        fill_in_standard_formats(self)
    if bv >= 80:
        unpack_fmt = '<HHHBBBBIiH'
        (
            xf.font_index, xf.format_key, pkd_type_par,
            pkd_align1, xf.alignment.rotation, pkd_align2,
            pkd_used, pkd_brdbkg1, pkd_brdbkg2, pkd_brdbkg3,
        ) = unpack(unpack_fmt, data[0:20])
        upkbits(xf.protection, pkd_type_par, (
            (0, 0x01, 'cell_locked'),
            (1, 0x02, 'formula_hidden'),
        ))
        upkbits(xf, pkd_type_par, (
            (2, 0x0004, 'is_style'),
            # Following is not in OOo docs, but is mentioned
            # in Gnumeric source and also in (deep breath)
            # org.apache.poi.hssf.record.ExtendedFormatRecord.java
            (3, 0x0008, 'lotus_123_prefix'), # Meaning is not known.
            (4, 0xFFF0, 'parent_style_index'),
        ))
        upkbits(xf.alignment, pkd_align1, (
            (0, 0x07, 'hor_align'),
            (3, 0x08, 'text_wrapped'),
            (4, 0x70, 'vert_align'),
        ))
        upkbits(xf.alignment, pkd_align2, (
            (0, 0x0f, 'indent_level'),
            (4, 0x10, 'shrink_to_fit'),
            (6, 0xC0, 'text_direction'),
        ))
        reg = pkd_used >> 2
        attr_stems = [
            'format',
            'font',
            'alignment',
            'border',
            'background',
            'protection',
        ]
        for attr_stem in attr_stems:
            attr = "_" + attr_stem + "_flag"
            setattr(xf, attr, reg & 1)
            reg >>= 1
        upkbitsL(xf.border, pkd_brdbkg1, (
            (0,  0x0000000f,  'left_line_style'),
            (4,  0x000000f0,  'right_line_style'),
            (8,  0x00000f00,  'top_line_style'),
            (12, 0x0000f000,  'bottom_line_style'),
            (16, 0x007f0000,  'left_colour_index'),
            (23, 0x3f800000,  'right_colour_index'),
            (30, 0x40000000,  'diag_down'),
            (31, 0x80000000, 'diag_up'),
        ))
        upkbits(xf.border, pkd_brdbkg2, (
            (0,  0x0000007F, 'top_colour_index'),
            (7,  0x00003F80, 'bottom_colour_index'),
            (14, 0x001FC000, 'diag_colour_index'),
            (21, 0x01E00000, 'diag_line_style'),
        ))
        upkbitsL(xf.background, pkd_brdbkg2, (
            (26, 0xFC000000, 'fill_pattern'),
        ))
        upkbits(xf.background, pkd_brdbkg3, (
            (0, 0x007F, 'pattern_colour_index'),
            (7, 0x3F80, 'background_colour_index'),
        ))
    elif bv >= 50:
        unpack_fmt = '<HHHBBIi'
        (
            xf.font_index, xf.format_key, pkd_type_par,
            pkd_align1, pkd_orient_used,
            pkd_brdbkg1, pkd_brdbkg2,
        ) = unpack(unpack_fmt, data[0:16])
        upkbits(xf.protection, pkd_type_par, (
            (0, 0x01, 'cell_locked'),
            (1, 0x02, 'formula_hidden'),
        ))
        upkbits(xf, pkd_type_par, (
            (2, 0x0004, 'is_style'),
            (3, 0x0008, 'lotus_123_prefix'), # Meaning is not known.
            (4, 0xFFF0, 'parent_style_index'),
        ))
        upkbits(xf.alignment, pkd_align1, (
            (0, 0x07, 'hor_align'),
            (3, 0x08, 'text_wrapped'),
            (4, 0x70, 'vert_align'),
        ))
        orientation = pkd_orient_used & 0x03
        xf.alignment.rotation = [0, 255, 90, 180][orientation]
        reg = pkd_orient_used >> 2
        attr_stems = [
            'format',
            'font',
            'alignment',
            'border',
            'background',
            'protection',
        ]
        for attr_stem in attr_stems:
            attr = "_" + attr_stem + "_flag"
            setattr(xf, attr, reg & 1)
            reg >>= 1
        upkbitsL(xf.background, pkd_brdbkg1, (
            ( 0, 0x0000007F, 'pattern_colour_index'),
            ( 7, 0x00003F80, 'background_colour_index'),
            (16, 0x003F0000, 'fill_pattern'),
        ))
        upkbitsL(xf.border, pkd_brdbkg1, (
            (22, 0x01C00000,  'bottom_line_style'),
            (25, 0xFE000000, 'bottom_colour_index'),
        ))
        upkbits(xf.border, pkd_brdbkg2, (
            ( 0, 0x00000007, 'top_line_style'),
            ( 3, 0x00000038, 'left_line_style'),
            ( 6, 0x000001C0, 'right_line_style'),
            ( 9, 0x0000FE00, 'top_colour_index'),
            (16, 0x007F0000, 'left_colour_index'),
            (23, 0x3F800000, 'right_colour_index'),
        ))
    elif bv >= 40:
        unpack_fmt = '<BBHBBHI'
        (
            xf.font_index, xf.format_key, pkd_type_par,
            pkd_align_orient, pkd_used,
            pkd_bkg_34, pkd_brd_34,
        ) = unpack(unpack_fmt, data[0:12])
        upkbits(xf.protection, pkd_type_par, (
            (0, 0x01, 'cell_locked'),
            (1, 0x02, 'formula_hidden'),
        ))
        upkbits(xf, pkd_type_par, (
            (2, 0x0004, 'is_style'),
            (3, 0x0008, 'lotus_123_prefix'), # Meaning is not known.
            (4, 0xFFF0, 'parent_style_index'),
        ))
        upkbits(xf.alignment, pkd_align_orient, (
            (0, 0x07, 'hor_align'),
            (3, 0x08, 'text_wrapped'),
            (4, 0x30, 'vert_align'),
        ))
        orientation = (pkd_align_orient & 0xC0) >> 6
        xf.alignment.rotation = [0, 255, 90, 180][orientation]
        reg = pkd_used >> 2
        attr_stems = [
            'format',
            'font',
            'alignment',
            'border',
            'background',
            'protection',
        ]
        for attr_stem in attr_stems:
            attr = "_" + attr_stem + "_flag"
            setattr(xf, attr, reg & 1)
            reg >>= 1
        upkbits(xf.background, pkd_bkg_34, (
            ( 0, 0x003F, 'fill_pattern'),
            ( 6, 0x07C0, 'pattern_colour_index'),
            (11, 0xF800, 'background_colour_index'),
        ))
        upkbitsL(xf.border, pkd_brd_34, (
            ( 0, 0x00000007,  'top_line_style'),
            ( 3, 0x000000F8,  'top_colour_index'),
            ( 8, 0x00000700,  'left_line_style'),
            (11, 0x0000F800,  'left_colour_index'),
            (16, 0x00070000,  'bottom_line_style'),
            (19, 0x00F80000,  'bottom_colour_index'),
            (24, 0x07000000,  'right_line_style'),
            (27, 0xF8000000, 'right_colour_index'),
        ))
    elif bv == 30:
        unpack_fmt = '<BBBBHHI'
        (
            xf.font_index, xf.format_key, pkd_type_prot,
            pkd_used, pkd_align_par,
            pkd_bkg_34, pkd_brd_34,
        ) = unpack(unpack_fmt, data[0:12])
        upkbits(xf.protection, pkd_type_prot, (
            (0, 0x01, 'cell_locked'),
            (1, 0x02, 'formula_hidden'),
        ))
        upkbits(xf, pkd_type_prot, (
            (2, 0x0004, 'is_style'),
            (3, 0x0008, 'lotus_123_prefix'), # Meaning is not known.
        ))
        upkbits(xf.alignment, pkd_align_par, (
            (0, 0x07, 'hor_align'),
            (3, 0x08, 'text_wrapped'),
        ))
        upkbits(xf, pkd_align_par, (
            (4, 0xFFF0, 'parent_style_index'),
        ))
        reg = pkd_used >> 2
        attr_stems = [
            'format',
            'font',
            'alignment',
            'border',
            'background',
            'protection',
        ]
        for attr_stem in attr_stems:
            attr = "_" + attr_stem + "_flag"
            setattr(xf, attr, reg & 1)
            reg >>= 1
        upkbits(xf.background, pkd_bkg_34, (
            ( 0, 0x003F, 'fill_pattern'),
            ( 6, 0x07C0, 'pattern_colour_index'),
            (11, 0xF800, 'background_colour_index'),
        ))
        upkbitsL(xf.border, pkd_brd_34, (
            ( 0, 0x00000007,  'top_line_style'),
            ( 3, 0x000000F8,  'top_colour_index'),
            ( 8, 0x00000700,  'left_line_style'),
            (11, 0x0000F800,  'left_colour_index'),
            (16, 0x00070000,  'bottom_line_style'),
            (19, 0x00F80000,  'bottom_colour_index'),
            (24, 0x07000000,  'right_line_style'),
            (27, 0xF8000000, 'right_colour_index'),
        ))
        xf.alignment.vert_align = 2 # bottom
        xf.alignment.rotation = 0
    elif bv == 21:
        ## Warning: incomplete treatment; formatting_info not fully supported.
        ## Probably need to offset incoming BIFF2 XF[n] to BIFF8-like XF[n+16],
        ## and create XF[0:16] like the standard ones in BIFF8 *AND* add 16 to
        ## all XF references in cell records :-(
        (xf.font_index, format_etc, halign_etc) = unpack('<BxBB', data)
        xf.format_key = format_etc & 0x3F
        upkbits(xf.protection, format_etc, (
            (6, 0x40, 'cell_locked'),
            (7, 0x80, 'formula_hidden'),
        ))
        upkbits(xf.alignment, halign_etc, (
            (0, 0x07, 'hor_align'),
        ))
        for mask, side in ((0x08, 'left'), (0x10, 'right'), (0x20, 'top'), (0x40, 'bottom')):
            if halign_etc & mask:
                colour_index, line_style = 8, 1 # black, thin
            else:
                colour_index, line_style = 0, 0 # none, none
            setattr(xf.border, side + '_colour_index', colour_index)
            setattr(xf.border, side + '_line_style', line_style)
        bg = xf.background
        if halign_etc & 0x80:
            bg.fill_pattern = 17
        else:
            bg.fill_pattern = 0
        bg.background_colour_index = 9 # white
        bg.pattern_colour_index = 8 # black
        xf.parent_style_index = 0 # ???????????
        xf.alignment.vert_align = 2 # bottom
        xf.alignment.rotation = 0
        attr_stems = [
            'format',
            'font',
            'alignment',
            'border',
            'background',
            'protection',
        ]
        for attr_stem in attr_stems:
            attr = "_" + attr_stem + "_flag"
            setattr(xf, attr, 1)
    else:
        raise XLRDError('programmer stuff-up: bv=%d' % bv)

    xf.xf_index = len(self.xf_list)
    self.xf_list.append(xf)
    self.xfcount += 1
    if blah:
        xf.dump(
            self.logfile,
            header="--- handle_xf: xf[%d] ---" % xf.xf_index,
            footer=" ",
        )
    try:
        fmt = self.format_map[xf.format_key]
        cellty = _cellty_from_fmtty[fmt.type]
    except KeyError:
        cellty = XL_CELL_NUMBER
    self._xf_index_to_xl_type_map[xf.xf_index] = cellty

    # Now for some assertions ...
    if self.formatting_info:
        if self.verbosity and xf.is_style and xf.parent_style_index != 0x0FFF:
            msg = "WARNING *** XF[%d] is a style XF but parent_style_index is 0x%04x, not 0x0fff\n"
            fprintf(self.logfile, msg, xf.xf_index, xf.parent_style_index)
        check_colour_indexes_in_obj(self, xf, xf.xf_index)
    if xf.format_key not in self.format_map:
        msg = "WARNING *** XF[%d] unknown (raw) format key (%d, 0x%04x)\n"
        if self.verbosity:
            fprintf(self.logfile, msg,
                xf.xf_index, xf.format_key, xf.format_key)
        xf.format_key = 0

def xf_epilogue(self):
    # self is a Book instance.
    self._xf_epilogue_done = 1
    num_xfs = len(self.xf_list)
    blah = DEBUG or self.verbosity >= 3
    blah1 = DEBUG or self.verbosity >= 1
    if blah:
        fprintf(self.logfile, "xf_epilogue called ...\n")

    def check_same(book_arg, xf_arg, parent_arg, attr):
        # the _arg caper is to avoid a Warning msg from Python 2.1 :-(
        if getattr(xf_arg, attr) != getattr(parent_arg, attr):
            fprintf(book_arg.logfile,
                "NOTE !!! XF[%d] parent[%d] %s different\n",
                xf_arg.xf_index, parent_arg.xf_index, attr)

    for xfx in xrange(num_xfs):
        xf = self.xf_list[xfx]

        try:
            fmt = self.format_map[xf.format_key]
            cellty = _cellty_from_fmtty[fmt.type]
        except KeyError:
            cellty = XL_CELL_TEXT
        self._xf_index_to_xl_type_map[xf.xf_index] = cellty
        # Now for some assertions etc
        if not self.formatting_info:
            continue
        if xf.is_style:
            continue
        if not(0 <= xf.parent_style_index < num_xfs):
            if blah1:
                fprintf(self.logfile,
                    "WARNING *** XF[%d]: is_style=%d but parent_style_index=%d\n",
                    xf.xf_index, xf.is_style, xf.parent_style_index)
            # make it conform
            xf.parent_style_index = 0
        if self.biff_version >= 30:
            if blah1:
                if xf.parent_style_index == xf.xf_index:
                    fprintf(self.logfile,
                        "NOTE !!! XF[%d]: parent_style_index is also %d\n",
                        xf.xf_index, xf.parent_style_index)
                elif not self.xf_list[xf.parent_style_index].is_style:
                    fprintf(self.logfile,
                        "NOTE !!! XF[%d]: parent_style_index is %d; style flag not set\n",
                        xf.xf_index, xf.parent_style_index)
            if blah1 and xf.parent_style_index > xf.xf_index:
                fprintf(self.logfile,
                    "NOTE !!! XF[%d]: parent_style_index is %d; out of order?\n",
                    xf.xf_index, xf.parent_style_index)
            parent = self.xf_list[xf.parent_style_index]
            if not xf._alignment_flag and not parent._alignment_flag:
                if blah1: check_same(self, xf, parent, 'alignment')
            if not xf._background_flag and not parent._background_flag:
                if blah1: check_same(self, xf, parent, 'background')
            if not xf._border_flag and not parent._border_flag:
                if blah1: check_same(self, xf, parent, 'border')
            if not xf._protection_flag and not parent._protection_flag:
                if blah1: check_same(self, xf, parent, 'protection')
            if not xf._format_flag and not parent._format_flag:
                if blah1 and xf.format_key != parent.format_key:
                    fprintf(self.logfile,
                        "NOTE !!! XF[%d] fmtk=%d, parent[%d] fmtk=%r\n%r / %r\n",
                        xf.xf_index, xf.format_key, parent.xf_index, parent.format_key,
                        self.format_map[xf.format_key].format_str,
                        self.format_map[parent.format_key].format_str)
            if not xf._font_flag and not parent._font_flag:
                if blah1 and xf.font_index != parent.font_index:
                    fprintf(self.logfile,
                        "NOTE !!! XF[%d] fontx=%d, parent[%d] fontx=%r\n",
                        xf.xf_index, xf.font_index, parent.xf_index, parent.font_index)

def initialise_book(book):
    initialise_colour_map(book)
    book._xf_epilogue_done = 0
    methods = (
        handle_font,
        handle_efont,
        handle_format,
        is_date_format_string,
        handle_palette,
        palette_epilogue,
        handle_style,
        handle_xf,
        xf_epilogue,
    )
    for method in methods:
        setattr(book.__class__, method.__name__, method)

class XFBorder(BaseObject, EqNeAttrs):
    """
    A collection of the border-related attributes of an ``XF`` record.
    Items correspond to those in the Excel UI's Format -> Cells -> Border tab.

    An explanations of "colour index" is given in :ref:`palette`.

    There are five line style attributes; possible values and the
    associated meanings are::

      0 = No line,
      1 = Thin,
      2 = Medium,
      3 = Dashed,
      4 = Dotted,
      5 = Thick,
      6 = Double,
      7 = Hair,
      8 = Medium dashed,
      9 = Thin dash-dotted,
      10 = Medium dash-dotted,
      11 = Thin dash-dot-dotted,
      12 = Medium dash-dot-dotted,
      13 = Slanted medium dash-dotted.

    The line styles 8 to 13 appear in BIFF8 files (Excel 97 and later) only.
    For pictures of the line styles, refer to OOo docs s3.10 (p22)
    "Line Styles for Cell Borders (BIFF3-BIFF8)".</p>

    .. versionadded:: 0.6.1
    """

    #: The colour index for the cell's top line
    top_colour_index = 0
    #: The colour index for the cell's bottom line
    bottom_colour_index = 0

    #: The colour index for the cell's left line
    left_colour_index = 0

    #: The colour index for the cell's right line
    right_colour_index = 0

    #: The colour index for the cell's diagonal lines, if any
    diag_colour_index = 0

    #: The line style for the cell's top line
    top_line_style = 0

    #: The line style for the cell's bottom line
    bottom_line_style = 0

    #: The line style for the cell's left line
    left_line_style = 0

    #: The line style for the cell's right line
    right_line_style = 0

    #: The line style for the cell's diagonal lines, if any
    diag_line_style = 0

    #: 1 = draw a diagonal from top left to bottom right
    diag_down = 0

    #: 1 = draw a diagonal from bottom left to top right
    diag_up = 0

class XFBackground(BaseObject, EqNeAttrs):
    """
    A collection of the background-related attributes of an ``XF`` record.
    Items correspond to those in the Excel UI's Format -> Cells -> Patterns tab.

    An explanations of "colour index" is given in :ref:`palette`.

    .. versionadded:: 0.6.1
    """

    #: See section 3.11 of the OOo docs.
    fill_pattern = 0

    #: See section 3.11 of the OOo docs.
    background_colour_index = 0

    #: See section 3.11 of the OOo docs.
    pattern_colour_index = 0


class XFAlignment(BaseObject, EqNeAttrs):
    """
    A collection of the alignment and similar attributes of an ``XF`` record.
    Items correspond to those in the Excel UI's Format -> Cells -> Alignment tab.

    .. versionadded:: 0.6.1
    """

    #: Values: section 6.115 (p 214) of OOo docs
    hor_align = 0

    #: Values: section 6.115 (p 215) of OOo docs
    vert_align = 0

    #: Values: section 6.115 (p 215) of OOo docs.
    #:
    #: .. note::
    #:   file versions BIFF7 and earlier use the documented
    #:   :attr:`orientation` attribute; this will be mapped (without loss)
    #:   into :attr:`rotation`.
    rotation = 0

    #: 1 = text is wrapped at right margin
    text_wrapped = 0

    #: A number in ``range(15)``.
    indent_level = 0

    #: 1 = shrink font size to fit text into cell.
    shrink_to_fit = 0

    #: 0 = according to context; 1 = left-to-right; 2 = right-to-left
    text_direction = 0

class XFProtection(BaseObject, EqNeAttrs):
    """
    A collection of the protection-related attributes of an ``XF`` record.
    Items correspond to those in the Excel UI's Format -> Cells -> Protection tab.
    Note the OOo docs include the "cell or style" bit in this bundle of
    attributes. This is incorrect; the bit is used in determining which bundles
    to use.

    .. versionadded:: 0.6.1
    """

    #: 1 = Cell is prevented from being changed, moved, resized, or deleted
    #: (only if the sheet is protected).
    cell_locked = 0

    #: 1 = Hide formula so that it doesn't appear in the formula bar when
    #: the cell is selected (only if the sheet is protected).
    formula_hidden = 0

class XF(BaseObject):
    """
    eXtended Formatting information for cells, rows, columns and styles.

    Each of the 6 flags below describes the validity of
    a specific group of attributes.

    In cell XFs:

    - ``flag==0`` means the attributes of the parent style ``XF`` are
      used, (but only if the attributes are valid there);

    - ``flag==1`` means the attributes of this ``XF`` are used.

    In style XFs:

    - ``flag==0`` means the attribute setting is valid;
    - ``flag==1`` means the attribute should be ignored.

    .. note::
      the API provides both "raw" XFs and "computed" XFs. In the latter case,
      cell XFs have had the above inheritance mechanism applied.

    .. versionadded:: 0.6.1
    """

    #: 0 = cell XF, 1 = style XF
    is_style = 0

    #: cell XF: Index into Book.xf_list of this XF's style XF
    #:
    #: style XF: 0xFFF
    parent_style_index = 0

    #
    _format_flag = 0

    #
    _font_flag = 0

    #
    _alignment_flag = 0

    #
    _border_flag = 0

    #
    _background_flag = 0

    _protection_flag = 0

    #: Index into :attr:`~xlrd.book.Book.xf_list`
    xf_index = 0

    #: Index into :attr:`~xlrd.book.Book.font_list`
    font_index = 0

    #: Key into :attr:`~xlrd.book.Book.format_map`
    #:
    #: .. warning::
    #:   OOo docs on the XF record call this "Index to FORMAT record".
    #:   It is not an index in the Python sense. It is a key to a map.
    #:   It is true *only* for Excel 4.0 and earlier files
    #:   that the key into format_map from an XF instance
    #:   is the same as the index into format_list, and *only*
    #:   if the index is less than 164.
    format_key = 0

    #: An instance of an :class:`XFProtection` object.
    protection = None

    #: An instance of an :class:`XFBackground` object.
    background = None

    #: An instance of an :class:`XFAlignment` object.
    alignment = None

    #: An instance of an :class:`XFBorder` object.
    border = None
