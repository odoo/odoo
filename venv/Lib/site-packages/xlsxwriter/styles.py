###############################################################################
#
# Styles - A class for writing the Excel XLSX Worksheet file.
#
# Copyright 2013-2018, John McNamara, jmcnamara@cpan.org
#

# Package imports.
from . import xmlwriter


class Styles(xmlwriter.XMLwriter):
    """
    A class for writing the Excel XLSX Styles file.


    """

    ###########################################################################
    #
    # Public API.
    #
    ###########################################################################

    def __init__(self):
        """
        Constructor.

        """

        super(Styles, self).__init__()

        self.xf_formats = []
        self.palette = []
        self.font_count = 0
        self.num_format_count = 0
        self.border_count = 0
        self.fill_count = 0
        self.custom_colors = []
        self.dxf_formats = []
        self.has_hyperlink = False
        self.hyperlink_font_id = 0

    ###########################################################################
    #
    # Private API.
    #
    ###########################################################################

    def _assemble_xml_file(self):
        # Assemble and write the XML file.

        # Write the XML declaration.
        self._xml_declaration()

        # Add the style sheet.
        self._write_style_sheet()

        # Write the number formats.
        self._write_num_fmts()

        # Write the fonts.
        self._write_fonts()

        # Write the fills.
        self._write_fills()

        # Write the borders element.
        self._write_borders()

        # Write the cellStyleXfs element.
        self._write_cell_style_xfs()

        # Write the cellXfs element.
        self._write_cell_xfs()

        # Write the cellStyles element.
        self._write_cell_styles()

        # Write the dxfs element.
        self._write_dxfs()

        # Write the tableStyles element.
        self._write_table_styles()

        # Write the colors element.
        self._write_colors()

        # Close the style sheet tag.
        self._xml_end_tag('styleSheet')

        # Close the file.
        self._xml_close()

    def _set_style_properties(self, properties):
        # Pass in the Format objects and other properties used in the styles.

        self.xf_formats = properties[0]
        self.palette = properties[1]
        self.font_count = properties[2]
        self.num_format_count = properties[3]
        self.border_count = properties[4]
        self.fill_count = properties[5]
        self.custom_colors = properties[6]
        self.dxf_formats = properties[7]

    def _get_palette_color(self, color):
        # Convert the RGB color.
        if color[0] == '#':
            color = color[1:]

        return "FF" + color.upper()

    ###########################################################################
    #
    # XML methods.
    #
    ###########################################################################

    def _write_style_sheet(self):
        # Write the <styleSheet> element.
        xmlns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'

        attributes = [('xmlns', xmlns)]
        self._xml_start_tag('styleSheet', attributes)

    def _write_num_fmts(self):
        # Write the <numFmts> element.
        if not self.num_format_count:
            return

        attributes = [('count', self.num_format_count)]
        self._xml_start_tag('numFmts', attributes)

        # Write the numFmts elements.
        for xf_format in self.xf_formats:
            # Ignore built-in number formats, i.e., < 164.
            if xf_format.num_format_index >= 164:
                self._write_num_fmt(xf_format.num_format_index,
                                    xf_format.num_format)

        self._xml_end_tag('numFmts')

    def _write_num_fmt(self, num_fmt_id, format_code):
        # Write the <numFmt> element.
        format_codes = {
            0: 'General',
            1: '0',
            2: '0.00',
            3: '#,##0',
            4: '#,##0.00',
            5: '($#,##0_);($#,##0)',
            6: '($#,##0_);[Red]($#,##0)',
            7: '($#,##0.00_);($#,##0.00)',
            8: '($#,##0.00_);[Red]($#,##0.00)',
            9: '0%',
            10: '0.00%',
            11: '0.00E+00',
            12: '# ?/?',
            13: '# ??/??',
            14: 'm/d/yy',
            15: 'd-mmm-yy',
            16: 'd-mmm',
            17: 'mmm-yy',
            18: 'h:mm AM/PM',
            19: 'h:mm:ss AM/PM',
            20: 'h:mm',
            21: 'h:mm:ss',
            22: 'm/d/yy h:mm',
            37: '(#,##0_);(#,##0)',
            38: '(#,##0_);[Red](#,##0)',
            39: '(#,##0.00_);(#,##0.00)',
            40: '(#,##0.00_);[Red](#,##0.00)',
            41: '_(* #,##0_);_(* (#,##0);_(* "-"_);_(_)',
            42: '_($* #,##0_);_($* (#,##0);_($* "-"_);_(_)',
            43: '_(* #,##0.00_);_(* (#,##0.00);_(* "-"??_);_(_)',
            44: '_($* #,##0.00_);_($* (#,##0.00);_($* "-"??_);_(_)',
            45: 'mm:ss',
            46: '[h]:mm:ss',
            47: 'mm:ss.0',
            48: '##0.0E+0',
            49: '@'}

        # Set the format code for built-in number formats.
        if num_fmt_id < 164:
            if num_fmt_id in format_codes:
                format_code = format_codes[num_fmt_id]
            else:
                format_code = 'General'

        attributes = [
            ('numFmtId', num_fmt_id),
            ('formatCode', format_code),
        ]

        self._xml_empty_tag('numFmt', attributes)

    def _write_fonts(self):
        # Write the <fonts> element.
        attributes = [('count', self.font_count)]
        self._xml_start_tag('fonts', attributes)

        # Write the font elements for xf_format objects that have them.
        for xf_format in self.xf_formats:
            if xf_format.has_font:
                self._write_font(xf_format)

        self._xml_end_tag('fonts')

    def _write_font(self, xf_format, is_dxf_format=False):
        # Write the <font> element.
        self._xml_start_tag('font')

        # The condense and extend elements are mainly used in dxf formats.
        if xf_format.font_condense:
            self._write_condense()

        if xf_format.font_extend:
            self._write_extend()

        if xf_format.bold:
            self._xml_empty_tag('b')

        if xf_format.italic:
            self._xml_empty_tag('i')

        if xf_format.font_strikeout:
            self._xml_empty_tag('strike')

        if xf_format.font_outline:
            self._xml_empty_tag('outline')

        if xf_format.font_shadow:
            self._xml_empty_tag('shadow')

        # Handle the underline variants.
        if xf_format.underline:
            self._write_underline(xf_format.underline)

        if xf_format.font_script == 1:
            self._write_vert_align('superscript')

        if xf_format.font_script == 2:
            self._write_vert_align('subscript')

        if not is_dxf_format:
            self._xml_empty_tag('sz', [('val', xf_format.font_size)])

        if xf_format.theme == -1:
            # Ignore for excel2003_style.
            pass
        elif xf_format.theme:
            self._write_color('theme', xf_format.theme)
        elif xf_format.color_indexed:
            self._write_color('indexed', xf_format.color_indexed)
        elif xf_format.font_color:
            color = self._get_palette_color(xf_format.font_color)
            self._write_color('rgb', color)
        elif not is_dxf_format:
            self._write_color('theme', 1)

        if not is_dxf_format:
            self._xml_empty_tag('name', [('val', xf_format.font_name)])

            if xf_format.font_family:
                self._xml_empty_tag('family', [('val', xf_format.font_family)])

            if xf_format.font_charset:
                self._xml_empty_tag('charset',
                                    [('val', xf_format.font_charset)])

            if xf_format.font_name == 'Calibri' and not xf_format.hyperlink:
                self._xml_empty_tag(
                    'scheme',
                    [('val', xf_format.font_scheme)])

            if xf_format.hyperlink:
                self.has_hyperlink = True
                if self.hyperlink_font_id == 0:
                    self.hyperlink_font_id = xf_format.font_index

        self._xml_end_tag('font')

    def _write_underline(self, underline):
        # Write the underline font element.

        if underline == 2:
            attributes = [('val', 'double')]
        elif underline == 33:
            attributes = [('val', 'singleAccounting')]
        elif underline == 34:
            attributes = [('val', 'doubleAccounting')]
        else:
            # Default to single underline.
            attributes = []

        self._xml_empty_tag('u', attributes)

    def _write_vert_align(self, val):
        # Write the <vertAlign> font sub-element.
        attributes = [('val', val)]

        self._xml_empty_tag('vertAlign', attributes)

    def _write_color(self, name, value):
        # Write the <color> element.
        attributes = [(name, value)]

        self._xml_empty_tag('color', attributes)

    def _write_fills(self):
        # Write the <fills> element.
        attributes = [('count', self.fill_count)]

        self._xml_start_tag('fills', attributes)

        # Write the default fill element.
        self._write_default_fill('none')
        self._write_default_fill('gray125')

        # Write the fill elements for xf_format objects that have them.
        for xf_format in self.xf_formats:
            if xf_format.has_fill:
                self._write_fill(xf_format)

        self._xml_end_tag('fills')

    def _write_default_fill(self, pattern_type):
        # Write the <fill> element for the default fills.
        self._xml_start_tag('fill')
        self._xml_empty_tag('patternFill', [('patternType', pattern_type)])
        self._xml_end_tag('fill')

    def _write_fill(self, xf_format, is_dxf_format=False):
        # Write the <fill> element.
        pattern = xf_format.pattern
        bg_color = xf_format.bg_color
        fg_color = xf_format.fg_color

        # Colors for dxf formats are handled differently from normal formats
        # since the normal xf_format reverses the meaning of BG and FG for
        # solid fills.
        if is_dxf_format:
            bg_color = xf_format.dxf_bg_color
            fg_color = xf_format.dxf_fg_color

        patterns = (
            'none',
            'solid',
            'mediumGray',
            'darkGray',
            'lightGray',
            'darkHorizontal',
            'darkVertical',
            'darkDown',
            'darkUp',
            'darkGrid',
            'darkTrellis',
            'lightHorizontal',
            'lightVertical',
            'lightDown',
            'lightUp',
            'lightGrid',
            'lightTrellis',
            'gray125',
            'gray0625',
        )

        self._xml_start_tag('fill')

        # The "none" pattern is handled differently for dxf formats.
        if is_dxf_format and pattern <= 1:
            self._xml_start_tag('patternFill')
        else:
            self._xml_start_tag(
                'patternFill',
                [('patternType', patterns[pattern])])

        if fg_color:
            fg_color = self._get_palette_color(fg_color)
            self._xml_empty_tag('fgColor', [('rgb', fg_color)])

        if bg_color:
            bg_color = self._get_palette_color(bg_color)
            self._xml_empty_tag('bgColor', [('rgb', bg_color)])
        else:
            if not is_dxf_format:
                self._xml_empty_tag('bgColor', [('indexed', 64)])

        self._xml_end_tag('patternFill')
        self._xml_end_tag('fill')

    def _write_borders(self):
        # Write the <borders> element.
        attributes = [('count', self.border_count)]

        self._xml_start_tag('borders', attributes)

        # Write the border elements for xf_format objects that have them.
        for xf_format in self.xf_formats:
            if xf_format.has_border:
                self._write_border(xf_format)

        self._xml_end_tag('borders')

    def _write_border(self, xf_format, is_dxf_format=False):
        # Write the <border> element.
        attributes = []

        # Diagonal borders add attributes to the <border> element.
        if xf_format.diag_type == 1:
            attributes.append(('diagonalUp', 1))
        elif xf_format.diag_type == 2:
            attributes.append(('diagonalDown', 1))
        elif xf_format.diag_type == 3:
            attributes.append(('diagonalUp', 1))
            attributes.append(('diagonalDown', 1))

        # Ensure that a default diag border is set if the diag type is set.
        if xf_format.diag_type and not xf_format.diag_border:
            xf_format.diag_border = 1

        # Write the start border tag.
        self._xml_start_tag('border', attributes)

        # Write the <border> sub elements.
        self._write_sub_border(
            'left',
            xf_format.left,
            xf_format.left_color)

        self._write_sub_border(
            'right',
            xf_format.right,
            xf_format.right_color)

        self._write_sub_border(
            'top',
            xf_format.top,
            xf_format.top_color)

        self._write_sub_border(
            'bottom',
            xf_format.bottom,
            xf_format.bottom_color)

        # Condition DXF formats don't allow diagonal borders.
        if not is_dxf_format:
            self._write_sub_border(
                'diagonal',
                xf_format.diag_border,
                xf_format.diag_color)

        if is_dxf_format:
            self._write_sub_border('vertical', None, None)
            self._write_sub_border('horizontal', None, None)

        self._xml_end_tag('border')

    def _write_sub_border(self, border_type, style, color):
        # Write the <border> sub elements such as <right>, <top>, etc.
        attributes = []

        if not style:
            self._xml_empty_tag(border_type)
            return

        border_styles = (
            'none',
            'thin',
            'medium',
            'dashed',
            'dotted',
            'thick',
            'double',
            'hair',
            'mediumDashed',
            'dashDot',
            'mediumDashDot',
            'dashDotDot',
            'mediumDashDotDot',
            'slantDashDot',
        )

        attributes.append(('style', border_styles[style]))

        self._xml_start_tag(border_type, attributes)

        if color:
            color = self._get_palette_color(color)
            self._xml_empty_tag('color', [('rgb', color)])
        else:
            self._xml_empty_tag('color', [('auto', 1)])

        self._xml_end_tag(border_type)

    def _write_cell_style_xfs(self):
        # Write the <cellStyleXfs> element.
        count = 1

        if self.has_hyperlink:
            count = 2

        attributes = [('count', count)]

        self._xml_start_tag('cellStyleXfs', attributes)
        self._write_style_xf()

        if self.has_hyperlink:
            self._write_style_xf(True, self.hyperlink_font_id)

        self._xml_end_tag('cellStyleXfs')

    def _write_cell_xfs(self):
        # Write the <cellXfs> element.
        formats = self.xf_formats

        # Workaround for when the last xf_format is used for the comment font
        # and shouldn't be used for cellXfs.
        last_format = formats[-1]
        if last_format.font_only:
            formats.pop()

        attributes = [('count', len(formats))]
        self._xml_start_tag('cellXfs', attributes)

        # Write the xf elements.
        for xf_format in formats:
            self._write_xf(xf_format)

        self._xml_end_tag('cellXfs')

    def _write_style_xf(self, has_hyperlink=False, font_id=0):
        # Write the style <xf> element.
        num_fmt_id = 0
        fill_id = 0
        border_id = 0

        attributes = [
            ('numFmtId', num_fmt_id),
            ('fontId', font_id),
            ('fillId', fill_id),
            ('borderId', border_id),
        ]

        if has_hyperlink:
            attributes.append(('applyNumberFormat', 0))
            attributes.append(('applyFill', 0))
            attributes.append(('applyBorder', 0))
            attributes.append(('applyAlignment', 0))
            attributes.append(('applyProtection', 0))

            self._xml_start_tag('xf', attributes)
            self._xml_empty_tag('alignment', [('vertical', 'top')])
            self._xml_empty_tag('protection', [('locked', 0)])
            self._xml_end_tag('xf')

        else:
            self._xml_empty_tag('xf', attributes)

    def _write_xf(self, xf_format):
        # Write the <xf> element.
        num_fmt_id = xf_format.num_format_index
        font_id = xf_format.font_index
        fill_id = xf_format.fill_index
        border_id = xf_format.border_index
        xf_id = xf_format.xf_id
        has_align = 0
        has_protect = 0

        attributes = [
            ('numFmtId', num_fmt_id),
            ('fontId', font_id),
            ('fillId', fill_id),
            ('borderId', border_id),
            ('xfId', xf_id),
        ]

        if xf_format.num_format_index > 0:
            attributes.append(('applyNumberFormat', 1))

        # Add applyFont attribute if XF format uses a font element.
        if xf_format.font_index > 0 and not xf_format.hyperlink:
            attributes.append(('applyFont', 1))

        # Add applyFill attribute if XF format uses a fill element.
        if xf_format.fill_index > 0:
            attributes.append(('applyFill', 1))

        # Add applyBorder attribute if XF format uses a border element.
        if xf_format.border_index > 0:
            attributes.append(('applyBorder', 1))

        # Check if XF format has alignment properties set.
        (apply_align, align) = xf_format._get_align_properties()

        # Check if an alignment sub-element should be written.
        if apply_align and align:
            has_align = 1

        # We can also have applyAlignment without a sub-element.
        if apply_align or xf_format.hyperlink:
            attributes.append(('applyAlignment', 1))

        # Check for cell protection properties.
        protection = xf_format._get_protection_properties()

        if protection or xf_format.hyperlink:
            attributes.append(('applyProtection', 1))

            if not xf_format.hyperlink:
                has_protect = 1

        # Write XF with sub-elements if required.
        if has_align or has_protect:
            self._xml_start_tag('xf', attributes)
            if has_align:
                self._xml_empty_tag('alignment', align)
            if has_protect:
                self._xml_empty_tag('protection', protection)
            self._xml_end_tag('xf')
        else:
            self._xml_empty_tag('xf', attributes)

    def _write_cell_styles(self):
        # Write the <cellStyles> element.
        count = 1

        if self.has_hyperlink:
            count = 2

        attributes = [('count', count)]

        self._xml_start_tag('cellStyles', attributes)

        if self.has_hyperlink:
            self._write_cell_style('Hyperlink', 1, 8)

        self._write_cell_style()

        self._xml_end_tag('cellStyles')

    def _write_cell_style(self, name='Normal', xf_id=0, builtin_id=0):
        # Write the <cellStyle> element.
        attributes = [
            ('name', name),
            ('xfId', xf_id),
            ('builtinId', builtin_id),
        ]

        self._xml_empty_tag('cellStyle', attributes)

    def _write_dxfs(self):
        # Write the <dxfs> element.
        formats = self.dxf_formats
        count = len(formats)

        attributes = [('count', len(formats))]

        if count:
            self._xml_start_tag('dxfs', attributes)

            # Write the font elements for xf_format objects that have them.
            for xf_format in self.dxf_formats:
                self._xml_start_tag('dxf')
                if xf_format.has_dxf_font:
                    self._write_font(xf_format, True)

                if xf_format.num_format_index:
                    self._write_num_fmt(xf_format.num_format_index,
                                        xf_format.num_format)

                if xf_format.has_dxf_fill:
                    self._write_fill(xf_format, True)
                if xf_format.has_dxf_border:
                    self._write_border(xf_format, True)
                self._xml_end_tag('dxf')

            self._xml_end_tag('dxfs')
        else:
            self._xml_empty_tag('dxfs', attributes)

    def _write_table_styles(self):
        # Write the <tableStyles> element.
        count = 0
        default_table_style = 'TableStyleMedium9'
        default_pivot_style = 'PivotStyleLight16'

        attributes = [
            ('count', count),
            ('defaultTableStyle', default_table_style),
            ('defaultPivotStyle', default_pivot_style),
        ]

        self._xml_empty_tag('tableStyles', attributes)

    def _write_colors(self):
        # Write the <colors> element.
        custom_colors = self.custom_colors

        if not custom_colors:
            return

        self._xml_start_tag('colors')
        self._write_mru_colors(custom_colors)
        self._xml_end_tag('colors')

    def _write_mru_colors(self, custom_colors):
        # Write the <mruColors> element for the most recently used colors.

        # Write the custom custom_colors in reverse order.
        custom_colors.reverse()

        # Limit the mruColors to the last 10.
        if len(custom_colors) > 10:
            custom_colors = custom_colors[0:10]

        self._xml_start_tag('mruColors')

        # Write the custom custom_colors in reverse order.
        for color in custom_colors:
            self._write_color('rgb', color)

        self._xml_end_tag('mruColors')

    def _write_condense(self):
        # Write the <condense> element.
        attributes = [('val', 0)]

        self._xml_empty_tag('condense', attributes)

    def _write_extend(self):
        # Write the <extend> element.
        attributes = [('val', 0)]

        self._xml_empty_tag('extend', attributes)
