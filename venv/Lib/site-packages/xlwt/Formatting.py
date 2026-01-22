'''
Formatting
==========

The  XF  record is able to store explicit cell formatting attributes or the
attributes  of  a cell style. Explicit formatting includes the reference to
a  cell  style  XF  record. This allows to extend a defined cell style with
some  explicit  attributes.  The  formatting  attributes  are  divided into
6 groups:

=============   ==========================================================
Group           Attributes
=============   ==========================================================
Number format   Number format index (index to FORMAT record)
Font            Font index (index to FONT record)
Alignment       Horizontal and vertical alignment, text wrap, indentation,
                orientation/rotation, text direction
Border          Border line styles and colours
Background      Background area style and colours
Protection      Cell locked, formula hidden
=============   ==========================================================

For  each  group  a flag in the cell XF record specifies whether to use the
attributes  contained  in  that  XF  record  or  in  the  referenced  style
XF  record. In style XF records, these flags specify whether the attributes
will  overwrite  explicit  cell  formatting  when  the  style is applied to
a  cell. Changing a cell style (without applying this style to a cell) will
change  all  cells which already use that style and do not contain explicit
cell  attributes for the changed style attributes. If a cell XF record does
not  contain  explicit  attributes  in a group (if the attribute group flag
is not set), it repeats the attributes of its style XF record.

'''

from . import BIFFRecords

class Font(object):

    ESCAPEMENT_NONE         = 0x00
    ESCAPEMENT_SUPERSCRIPT  = 0x01
    ESCAPEMENT_SUBSCRIPT    = 0x02

    UNDERLINE_NONE          = 0x00
    UNDERLINE_SINGLE        = 0x01
    UNDERLINE_SINGLE_ACC    = 0x21
    UNDERLINE_DOUBLE        = 0x02
    UNDERLINE_DOUBLE_ACC    = 0x22

    FAMILY_NONE         = 0x00
    FAMILY_ROMAN        = 0x01
    FAMILY_SWISS        = 0x02
    FAMILY_MODERN       = 0x03
    FAMILY_SCRIPT       = 0x04
    FAMILY_DECORATIVE   = 0x05

    CHARSET_ANSI_LATIN          = 0x00
    CHARSET_SYS_DEFAULT         = 0x01
    CHARSET_SYMBOL              = 0x02
    CHARSET_APPLE_ROMAN         = 0x4D
    CHARSET_ANSI_JAP_SHIFT_JIS  = 0x80
    CHARSET_ANSI_KOR_HANGUL     = 0x81
    CHARSET_ANSI_KOR_JOHAB      = 0x82
    CHARSET_ANSI_CHINESE_GBK    = 0x86
    CHARSET_ANSI_CHINESE_BIG5   = 0x88
    CHARSET_ANSI_GREEK          = 0xA1
    CHARSET_ANSI_TURKISH        = 0xA2
    CHARSET_ANSI_VIETNAMESE     = 0xA3
    CHARSET_ANSI_HEBREW         = 0xB1
    CHARSET_ANSI_ARABIC         = 0xB2
    CHARSET_ANSI_BALTIC         = 0xBA
    CHARSET_ANSI_CYRILLIC       = 0xCC
    CHARSET_ANSI_THAI           = 0xDE
    CHARSET_ANSI_LATIN_II       = 0xEE
    CHARSET_OEM_LATIN_I         = 0xFF

    def __init__(self):
        # twip = 1/20 of a point = 1/1440 of a inch
        # usually resolution == 96 pixels per 1 inch
        # (rarely 120 pixels per 1 inch or another one)

        self.height = 0x00C8 # 200: this is font with height 10 points
        self.italic = False
        self.struck_out = False
        self.outline = False
        self.shadow = False
        self.colour_index = 0x7FFF
        self.bold = False
        self._weight = 0x0190 # 0x02BC gives bold font
        self.escapement = self.ESCAPEMENT_NONE
        self.underline = self.UNDERLINE_NONE
        self.family = self.FAMILY_NONE
        self.charset = self.CHARSET_SYS_DEFAULT
        self.name = 'Arial'

    def get_biff_record(self):
        height = self.height

        options = 0x00
        if self.bold:
            options |= 0x01
            self._weight = 0x02BC
        if self.italic:
            options |= 0x02
        if self.underline != self.UNDERLINE_NONE:
            options |= 0x04
        if self.struck_out:
            options |= 0x08
        if self.outline:
            options |= 0x010
        if self.shadow:
            options |= 0x020

        colour_index = self.colour_index
        weight = self._weight
        escapement = self.escapement
        underline = self.underline
        family = self.family
        charset = self.charset
        name = self.name

        return BIFFRecords.FontRecord(height, options, colour_index, weight, escapement,
                    underline, family, charset,
                    name)

    def _search_key(self):
        return (
            self.height,
            self.italic,
            self.struck_out,
            self.outline,
            self.shadow,
            self.colour_index,
            self.bold,
            self._weight,
            self.escapement,
            self.underline,
            self.family,
            self.charset,
            self.name,
            )

class Alignment(object):
    HORZ_GENERAL                = 0x00
    HORZ_LEFT                   = 0x01
    HORZ_CENTER                 = 0x02
    HORZ_RIGHT                  = 0x03
    HORZ_FILLED                 = 0x04
    HORZ_JUSTIFIED              = 0x05 # BIFF4-BIFF8X
    HORZ_CENTER_ACROSS_SEL      = 0x06 # Centred across selection (BIFF4-BIFF8X)
    HORZ_DISTRIBUTED            = 0x07 # Distributed (BIFF8X)

    VERT_TOP                    = 0x00
    VERT_CENTER                 = 0x01
    VERT_BOTTOM                 = 0x02
    VERT_JUSTIFIED              = 0x03 # Justified (BIFF5-BIFF8X)
    VERT_DISTRIBUTED            = 0x04 # Distributed (BIFF8X)

    DIRECTION_GENERAL           = 0x00 # BIFF8X
    DIRECTION_LR                = 0x01
    DIRECTION_RL                = 0x02

    ORIENTATION_NOT_ROTATED     = 0x00
    ORIENTATION_STACKED         = 0x01
    ORIENTATION_90_CC           = 0x02
    ORIENTATION_90_CW           = 0x03

    ROTATION_0_ANGLE            = 0x00
    ROTATION_STACKED            = 0xFF

    WRAP_AT_RIGHT               = 0x01
    NOT_WRAP_AT_RIGHT           = 0x00

    SHRINK_TO_FIT               = 0x01
    NOT_SHRINK_TO_FIT           = 0x00

    def __init__(self):
        self.horz = self.HORZ_GENERAL
        self.vert = self.VERT_BOTTOM
        self.dire = self.DIRECTION_GENERAL
        self.orie = self.ORIENTATION_NOT_ROTATED
        self.rota = self.ROTATION_0_ANGLE
        self.wrap = self.NOT_WRAP_AT_RIGHT
        self.shri = self.NOT_SHRINK_TO_FIT
        self.inde = 0
        self.merg = 0

    def _search_key(self):
        return (
            self.horz, self.vert, self.dire, self.orie, self.rota,
            self.wrap, self.shri, self.inde, self.merg,
            )

class Borders(object):
    NO_LINE = 0x00
    THIN    = 0x01
    MEDIUM  = 0x02
    DASHED  = 0x03
    DOTTED  = 0x04
    THICK   = 0x05
    DOUBLE  = 0x06
    HAIR    = 0x07
    #The following for BIFF8
    MEDIUM_DASHED               = 0x08
    THIN_DASH_DOTTED            = 0x09
    MEDIUM_DASH_DOTTED          = 0x0A
    THIN_DASH_DOT_DOTTED        = 0x0B
    MEDIUM_DASH_DOT_DOTTED      = 0x0C
    SLANTED_MEDIUM_DASH_DOTTED  = 0x0D

    NEED_DIAG1      = 0x01
    NEED_DIAG2      = 0x01
    NO_NEED_DIAG1   = 0x00
    NO_NEED_DIAG2   = 0x00

    def __init__(self):
        self.left   = self.NO_LINE
        self.right  = self.NO_LINE
        self.top    = self.NO_LINE
        self.bottom = self.NO_LINE
        self.diag   = self.NO_LINE

        self.left_colour   = 0x40
        self.right_colour  = 0x40
        self.top_colour    = 0x40
        self.bottom_colour = 0x40
        self.diag_colour   = 0x40

        self.need_diag1 = self.NO_NEED_DIAG1
        self.need_diag2 = self.NO_NEED_DIAG2

    def _search_key(self):
        return (
             self.left, self.right, self.top, self.bottom, self.diag,
             self.left_colour, self.right_colour, self.top_colour,
             self.bottom_colour, self.diag_colour,
             self.need_diag1, self.need_diag2,
            )

class Pattern(object):
    # patterns 0x00 - 0x12
    NO_PATTERN      = 0x00
    SOLID_PATTERN   = 0x01

    def __init__(self):
        self.pattern = self.NO_PATTERN
        self.pattern_fore_colour = 0x40
        self.pattern_back_colour = 0x41

    def _search_key(self):
        return (
            self.pattern,
            self.pattern_fore_colour,
            self.pattern_back_colour,
            )

class Protection(object):
    def __init__(self):
        self.cell_locked = 1
        self.formula_hidden = 0

    def _search_key(self):
        return (
            self.cell_locked,
            self.formula_hidden,
            )
