###############################################################################
#
# Format - A class for writing the Excel XLSX Worksheet file.
#
# Copyright 2013-2018, John McNamara, jmcnamara@cpan.org
#

# Package imports.
from . import xmlwriter
from warnings import warn


class Format(xmlwriter.XMLwriter):
    """
    A class for writing the Excel XLSX Format file.


    """

    ###########################################################################
    #
    # Public API.
    #
    ###########################################################################

    def __init__(self, properties=None, xf_indices=None, dxf_indices=None):
        """
        Constructor.

        """
        if properties is None:
            properties = {}

        super(Format, self).__init__()

        self.xf_format_indices = xf_indices
        self.dxf_format_indices = dxf_indices
        self.xf_index = None
        self.dxf_index = None

        self.num_format = 0
        self.num_format_index = 0
        self.font_index = 0
        self.has_font = 0
        self.has_dxf_font = 0

        self.bold = 0
        self.underline = 0
        self.italic = 0
        self.font_name = 'Calibri'
        self.font_size = 11
        self.font_color = 0x0
        self.font_strikeout = 0
        self.font_outline = 0
        self.font_shadow = 0
        self.font_script = 0
        self.font_family = 2
        self.font_charset = 0
        self.font_scheme = 'minor'
        self.font_condense = 0
        self.font_extend = 0
        self.theme = 0
        self.hyperlink = False
        self.xf_id = 0

        self.hidden = 0
        self.locked = 1

        self.text_h_align = 0
        self.text_wrap = 0
        self.text_v_align = 0
        self.text_justlast = 0
        self.rotation = 0

        self.fg_color = 0
        self.bg_color = 0
        self.pattern = 0
        self.has_fill = 0
        self.has_dxf_fill = 0
        self.fill_index = 0
        self.fill_count = 0

        self.border_index = 0
        self.has_border = 0
        self.has_dxf_border = 0
        self.border_count = 0

        self.bottom = 0
        self.bottom_color = 0
        self.diag_border = 0
        self.diag_color = 0
        self.diag_type = 0
        self.left = 0
        self.left_color = 0
        self.right = 0
        self.right_color = 0
        self.top = 0
        self.top_color = 0

        self.indent = 0
        self.shrink = 0
        self.merge_range = 0
        self.reading_order = 0
        self.just_distrib = 0
        self.color_indexed = 0
        self.font_only = 0

        # Convert properties in the constructor to method calls.
        for key, value in properties.items():
            getattr(self, 'set_' + key)(value)

        self._format_key = None

    ###########################################################################
    #
    # Format properties.
    #
    ###########################################################################

    def set_font_name(self, font_name):
        """
        Set the Format font_name property such as 'Time New Roman'. The
        default Excel font is 'Calibri'.

        Args:
            font_name: String with the font name. No default.

        Returns:
            Nothing.

        """
        self.font_name = font_name

    def set_font_size(self, font_size=11):
        """
        Set the Format font_size property. The default Excel font size is 11.

        Args:
            font_size: Int with font size. No default.

        Returns:
            Nothing.

        """
        self.font_size = font_size

    def set_font_color(self, font_color):
        """
        Set the Format font_color property. The Excel default is black.

        Args:
            font_color: String with the font color. No default.

        Returns:
            Nothing.

        """
        self.font_color = self._get_color(font_color)

    def set_bold(self, bold=True):
        """
        Set the Format bold property.

        Args:
            bold: Default is True, turns property on.

        Returns:
            Nothing.

        """
        self.bold = bold

    def set_italic(self, italic=True):
        """
        Set the Format italic property.

        Args:
            italic: Default is True, turns property on.

        Returns:
            Nothing.

        """
        self.italic = italic

    def set_underline(self, underline=1):
        """
        Set the Format underline property.

        Args:
            underline: Default is 1, single underline.

        Returns:
            Nothing.

        """
        self.underline = underline

    def set_font_strikeout(self, font_strikeout=True):
        """
        Set the Format font_strikeout property.

        Args:
            font_strikeout: Default is True, turns property on.

        Returns:
            Nothing.

        """
        self.font_strikeout = font_strikeout

    def set_font_script(self, font_script=1):
        """
        Set the Format font_script property.

        Args:
            font_script: Default is 1, superscript.

        Returns:
            Nothing.

        """
        self.font_script = font_script

    def set_font_outline(self, font_outline=True):
        """
        Set the Format font_outline property.

        Args:
            font_outline: Default is True, turns property on.

        Returns:
            Nothing.

        """
        self.font_outline = font_outline

    def set_font_shadow(self, font_shadow=True):
        """
        Set the Format font_shadow property.

        Args:
            font_shadow: Default is True, turns property on.

        Returns:
            Nothing.

        """
        self.font_shadow = font_shadow

    def set_num_format(self, num_format):
        """
        Set the Format num_format property such as '#,##0'.

        Args:
            num_format: String representing the number format. No default.

        Returns:
            Nothing.

        """
        self.num_format = num_format

    def set_locked(self, locked=True):
        """
        Set the Format locked property.

        Args:
            locked: Default is True, turns property on.

        Returns:
            Nothing.

        """
        self.locked = locked

    def set_hidden(self, hidden=True):
        """
        Set the Format hidden property.

        Args:
            hidden: Default is True, turns property on.

        Returns:
            Nothing.

        """
        self.hidden = hidden

    def set_align(self, alignment):
        """
        Set the Format cell alignment.

        Args:
            alignment: String representing alignment. No default.

        Returns:
            Nothing.
        """
        alignment = alignment.lower()

        # Set horizontal alignment properties.
        if alignment == 'left':
            self.set_text_h_align(1)
        if alignment == 'centre':
            self.set_text_h_align(2)
        if alignment == 'center':
            self.set_text_h_align(2)
        if alignment == 'right':
            self.set_text_h_align(3)
        if alignment == 'fill':
            self.set_text_h_align(4)
        if alignment == 'justify':
            self.set_text_h_align(5)
        if alignment == 'center_across':
            self.set_text_h_align(6)
        if alignment == 'centre_across':
            self.set_text_h_align(6)
        if alignment == 'distributed':
            self.set_text_h_align(7)
        if alignment == 'justify_distributed':
            self.set_text_h_align(7)

        if alignment == 'justify_distributed':
            self.just_distrib = 1

        # Set vertical alignment properties.
        if alignment == 'top':
            self.set_text_v_align(1)
        if alignment == 'vcentre':
            self.set_text_v_align(2)
        if alignment == 'vcenter':
            self.set_text_v_align(2)
        if alignment == 'bottom':
            self.set_text_v_align(3)
        if alignment == 'vjustify':
            self.set_text_v_align(4)
        if alignment == 'vdistributed':
            self.set_text_v_align(5)

    def set_center_across(self, align_type=None):
        """
        Set the Format center_across property.

        Returns:
            Nothing.

        """
        self.set_text_h_align(6)

    def set_text_wrap(self, text_wrap=True):
        """
        Set the Format text_wrap property.

        Args:
            text_wrap: Default is True, turns property on.

        Returns:
            Nothing.

        """
        self.text_wrap = text_wrap

    def set_rotation(self, rotation):
        """
        Set the Format rotation property.

        Args:
            rotation: Rotation angle. No default.

        Returns:
            Nothing.

        """
        rotation = int(rotation)

        # Map user angle to Excel angle.
        if rotation == 270:
            rotation = 255
        elif -90 <= rotation <= 90:
            if rotation < 0:
                rotation = -rotation + 90
        else:
            warn("Rotation rotation outside range: -90 <= angle <= 90")
            return

        self.rotation = rotation

    def set_indent(self, indent=1):
        """
        Set the Format indent property.

        Args:
            indent: Default is 1, first indentation level.

        Returns:
            Nothing.

        """
        self.indent = indent

    def set_shrink(self, shrink=True):
        """
        Set the Format shrink property.

        Args:
            shrink: Default is True, turns property on.

        Returns:
            Nothing.

        """
        self.shrink = shrink

    def set_text_justlast(self, text_justlast=True):
        """
        Set the Format text_justlast property.

        Args:
            text_justlast: Default is True, turns property on.

        Returns:
            Nothing.

        """
        self.text_justlast = text_justlast

    def set_pattern(self, pattern=1):
        """
        Set the Format pattern property.

        Args:
            pattern: Default is 1, solid fill.

        Returns:
            Nothing.

        """
        self.pattern = pattern

    def set_bg_color(self, bg_color):
        """
        Set the Format bg_color property.

        Args:
            bg_color: Background color. No default.

        Returns:
            Nothing.

        """
        self.bg_color = self._get_color(bg_color)

    def set_fg_color(self, fg_color):
        """
        Set the Format fg_color property.

        Args:
            fg_color: Foreground color. No default.

        Returns:
            Nothing.

        """
        self.fg_color = self._get_color(fg_color)

    # set_border(style) Set cells borders to the same style
    def set_border(self, style=1):
        """
        Set the Format bottom property.

        Args:
            bottom: Default is 1, border type 1.

        Returns:
            Nothing.

        """
        self.set_bottom(style)
        self.set_top(style)
        self.set_left(style)
        self.set_right(style)

    # set_border_color(color) Set cells border to the same color
    def set_border_color(self, color):
        """
        Set the Format bottom property.

        Args:
            color: Color string. No default.

        Returns:
            Nothing.

        """
        self.set_bottom_color(color)
        self.set_top_color(color)
        self.set_left_color(color)
        self.set_right_color(color)

    def set_bottom(self, bottom=1):
        """
        Set the Format bottom property.

        Args:
            bottom: Default is 1, border type 1.

        Returns:
            Nothing.

        """
        self.bottom = bottom

    def set_bottom_color(self, bottom_color):
        """
        Set the Format bottom_color property.

        Args:
            bottom_color: Color string. No default.

        Returns:
            Nothing.

        """
        self.bottom_color = self._get_color(bottom_color)

    def set_diag_type(self, diag_type=1):
        """
        Set the Format diag_type property.

        Args:
            diag_type: Default is 1, border type 1.

        Returns:
            Nothing.

        """
        self.diag_type = diag_type

    def set_left(self, left=1):
        """
        Set the Format left property.

        Args:
            left: Default is 1, border type 1.

        Returns:
            Nothing.

        """
        self.left = left

    def set_left_color(self, left_color):
        """
        Set the Format left_color property.

        Args:
            left_color: Color string. No default.

        Returns:
            Nothing.

        """
        self.left_color = self._get_color(left_color)

    def set_right(self, right=1):
        """
        Set the Format right property.

        Args:
            right: Default is 1, border type 1.

        Returns:
            Nothing.

        """
        self.right = right

    def set_right_color(self, right_color):
        """
        Set the Format right_color property.

        Args:
            right_color: Color string. No default.

        Returns:
            Nothing.

        """
        self.right_color = self._get_color(right_color)

    def set_top(self, top=1):
        """
        Set the Format top property.

        Args:
            top: Default is 1, border type 1.

        Returns:
            Nothing.

        """
        self.top = top

    def set_top_color(self, top_color):
        """
        Set the Format top_color property.

        Args:
            top_color: Color string. No default.

        Returns:
            Nothing.

        """
        self.top_color = self._get_color(top_color)

    def set_diag_color(self, diag_color):
        """
        Set the Format diag_color property.

        Args:
            diag_color: Color string. No default.

        Returns:
            Nothing.

        """
        self.diag_color = self._get_color(diag_color)

    def set_diag_border(self, diag_border=1):
        """
        Set the Format diag_border property.

        Args:
            diag_border: Default is 1, border type 1.

        Returns:
            Nothing.

        """
        self.diag_border = diag_border

    ###########################################################################
    #
    # Internal Format properties. These aren't documented since they are
    # either only used internally or else are unlikely to be set by the user.
    #
    ###########################################################################

    def set_has_font(self, has_font=True):
        # Set the has_font property.
        self.has_font = has_font

    def set_has_fill(self, has_fill=True):
        # Set the has_fill property.
        self.has_fill = has_fill

    def set_font_index(self, font_index):
        # Set the font_index property.
        self.font_index = font_index

    def set_xf_index(self, xf_index):
        # Set the xf_index property.
        self.xf_index = xf_index

    def set_dxf_index(self, dxf_index):
        # Set the xf_index property.
        self.dxf_index = dxf_index

    def set_num_format_index(self, num_format_index):
        # Set the num_format_index property.
        self.num_format_index = num_format_index

    def set_text_h_align(self, text_h_align):
        # Set the text_h_align property.
        self.text_h_align = text_h_align

    def set_text_v_align(self, text_v_align):
        # Set the text_v_align property.
        self.text_v_align = text_v_align

    def set_reading_order(self, direction=0):
        # Set the reading_order property.
        self.reading_order = direction

    def set_valign(self, align):
        # Set vertical cell alignment. This is required by the constructor
        # properties dict to differentiate between the vertical and horizontal
        # properties.
        self.set_align(align)

    def set_font_family(self, font_family):
        # Set the Format font_family property.
        self.font_family = font_family

    def set_font_charset(self, font_charset):
        # Set the Format font_charset property.
        self.font_charset = font_charset

    def set_font_scheme(self, font_scheme):
        # Set the Format font_scheme property.
        self.font_scheme = font_scheme

    def set_font_condense(self, font_condense):
        # Set the Format font_condense property.
        self.font_condense = font_condense

    def set_font_extend(self, font_extend):
        # Set the Format font_extend property.
        self.font_extend = font_extend

    def set_theme(self, theme):
        # Set the Format theme property.
        self.theme = theme

    def set_hyperlink(self, hyperlink=True):
        # Set the properties for the hyperlink style. This isn't
        # currently public. To be fixed when styles are supported.
        self.xf_id = 1
        self.set_underline(1)
        self.set_theme(10)
        self.hyperlink = hyperlink

    def set_color_indexed(self, color_index):
        # Used in the cell comment format.
        self.color_indexed = color_index

    def set_font_only(self, font_only=True):
        # Used in the cell comment format.
        self.font_only = font_only

    # Compatibility methods.
    def set_font(self, font_name):
        #  For compatibility with Excel::Writer::XLSX.
        self.font_name = font_name

    def set_size(self, font_size):
        #  For compatibility with Excel::Writer::XLSX.
        self.font_size = font_size

    def set_color(self, font_color):
        #  For compatibility with Excel::Writer::XLSX.
        self.font_color = self._get_color(font_color)

    ###########################################################################
    #
    # Private API.
    #
    ###########################################################################

    def _get_align_properties(self):
        # Return properties for an Style xf <alignment> sub-element.
        changed = 0
        align = []

        # Check if any alignment options in the format have been changed.
        if (self.text_h_align or self.text_v_align or self.indent
                or self.rotation or self.text_wrap or self.shrink
                or self.reading_order):
            changed = 1
        else:
            return changed, align

        # Indent is only allowed for horizontal left, right and distributed.
        # If it is defined for any other alignment or no alignment has
        # been set then default to left alignment.
        if (self.indent
                and self.text_h_align != 1
                and self.text_h_align != 3
                and self.text_h_align != 7):
            self.text_h_align = 1

        # Check for properties that are mutually exclusive.
        if self.text_wrap:
            self.shrink = 0
        if self.text_h_align == 4:
            self.shrink = 0
        if self.text_h_align == 5:
            self.shrink = 0
        if self.text_h_align == 7:
            self.shrink = 0
        if self.text_h_align != 7:
            self.just_distrib = 0
        if self.indent:
            self.just_distrib = 0

        continuous = 'centerContinuous'

        if self.text_h_align == 1:
            align.append(('horizontal', 'left'))
        if self.text_h_align == 2:
            align.append(('horizontal', 'center'))
        if self.text_h_align == 3:
            align.append(('horizontal', 'right'))
        if self.text_h_align == 4:
            align.append(('horizontal', 'fill'))
        if self.text_h_align == 5:
            align.append(('horizontal', 'justify'))
        if self.text_h_align == 6:
            align.append(('horizontal', continuous))
        if self.text_h_align == 7:
            align.append(('horizontal', 'distributed'))

        if self.just_distrib:
            align.append(('justifyLastLine', 1))

        # Property 'vertical' => 'bottom' is a default. It sets applyAlignment
        # without an alignment sub-element.
        if self.text_v_align == 1:
            align.append(('vertical', 'top'))
        if self.text_v_align == 2:
            align.append(('vertical', 'center'))
        if self.text_v_align == 4:
            align.append(('vertical', 'justify'))
        if self.text_v_align == 5:
            align.append(('vertical', 'distributed'))

        if self.indent:
            align.append(('indent', self.indent))
        if self.rotation:
            align.append(('textRotation', self.rotation))

        if self.text_wrap:
            align.append(('wrapText', 1))
        if self.shrink:
            align.append(('shrinkToFit', 1))

        if self.reading_order == 1:
            align.append(('readingOrder', 1))
        if self.reading_order == 2:
            align.append(('readingOrder', 2))

        return changed, align

    def _get_protection_properties(self):
        # Return properties for an Excel XML <Protection> element.
        attribs = []

        if not self.locked:
            attribs.append(('locked', 0))
        if self.hidden:
            attribs.append(('hidden', 1))

        return attribs

    def _get_format_key(self):
        # Returns a unique hash key for a font. Used by Workbook.
        if self._format_key is None:
            self._format_key = ':'.join(self._to_string(x) for x in (
                self._get_font_key(),
                self._get_border_key(),
                self._get_fill_key(),
                self._get_alignment_key(),
                self.num_format,
                self.locked,
                self.hidden))

        return self._format_key

    def _get_font_key(self):
        # Returns a unique hash key for a font. Used by Workbook.
        key = ':'.join(self._to_string(x) for x in (
            self.bold,
            self.font_color,
            self.font_charset,
            self.font_family,
            self.font_outline,
            self.font_script,
            self.font_shadow,
            self.font_strikeout,
            self.font_name,
            self.italic,
            self.font_size,
            self.underline,
            self.theme))

        return key

    def _get_border_key(self):
        # Returns a unique hash key for a border style. Used by Workbook.
        key = ':'.join(self._to_string(x) for x in (
            self.bottom,
            self.bottom_color,
            self.diag_border,
            self.diag_color,
            self.diag_type,
            self.left,
            self.left_color,
            self.right,
            self.right_color,
            self.top,
            self.top_color))

        return key

    def _get_fill_key(self):
        # Returns a unique hash key for a fill style. Used by Workbook.
        key = ':'.join(self._to_string(x) for x in (
            self.pattern,
            self.bg_color,
            self.fg_color))

        return key

    def _get_alignment_key(self):
        # Returns a unique hash key for alignment formats.

        key = ':'.join(self._to_string(x) for x in (
            self.text_h_align,
            self.text_v_align,
            self.indent,
            self.rotation,
            self.text_wrap,
            self.shrink,
            self.reading_order))

        return key

    def _get_xf_index(self):
        # Returns the XF index number used by Excel to identify a format.
        if self.xf_index is not None:
            # Format already has an index number so return it.
            return self.xf_index
        else:
            # Format doesn't have an index number so assign one.
            key = self._get_format_key()

            if key in self.xf_format_indices:
                # Format matches existing format with an index.
                return self.xf_format_indices[key]
            else:
                # New format requiring an index. Note. +1 since Excel
                # has an implicit "General" format at index 0.
                index = 1 + len(self.xf_format_indices)
                self.xf_format_indices[key] = index
                self.xf_index = index
                return index

    def _get_dxf_index(self):
        # Returns the DXF index number used by Excel to identify a format.
        if self.dxf_index is not None:
            # Format already has an index number so return it.
            return self.dxf_index
        else:
            # Format doesn't have an index number so assign one.
            key = self._get_format_key()

            if key in self.dxf_format_indices:
                # Format matches existing format with an index.
                return self.dxf_format_indices[key]
            else:
                # New format requiring an index.
                index = len(self.dxf_format_indices)
                self.dxf_format_indices[key] = index
                self.dxf_index = index
                return index

    def _get_color(self, color):
        # Used in conjunction with the set_xxx_color methods to convert a
        # color name into an RGB formatted string. These colors are for
        # backward compatibility with older versions of Excel.
        named_colors = {
            'black': '#000000',
            'blue': '#0000FF',
            'brown': '#800000',
            'cyan': '#00FFFF',
            'gray': '#808080',
            'green': '#008000',
            'lime': '#00FF00',
            'magenta': '#FF00FF',
            'navy': '#000080',
            'orange': '#FF6600',
            'pink': '#FF00FF',
            'purple': '#800080',
            'red': '#FF0000',
            'silver': '#C0C0C0',
            'white': '#FFFFFF',
            'yellow': '#FFFF00',
        }

        if color in named_colors:
            color = named_colors[color]

        return color

    def _to_string(self, value):
        # Convert number to a string but allow for utf-8 strings in Python 2.
        try:
            return str(value)
        except UnicodeEncodeError:
            return value.encode('utf-8')

    ###########################################################################
    #
    # XML methods.
    #
    ###########################################################################
