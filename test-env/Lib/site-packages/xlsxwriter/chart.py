###############################################################################
#
# Chart - A class for writing the Excel XLSX Worksheet file.
#
# Copyright 2013-2018, John McNamara, jmcnamara@cpan.org
#
import re
import copy
from warnings import warn

from .shape import Shape
from . import xmlwriter
from .utility import get_rgb_color
from .utility import xl_rowcol_to_cell
from .utility import xl_range_formula
from .utility import supported_datetime
from .utility import datetime_to_excel_datetime
from .utility import quote_sheetname


class Chart(xmlwriter.XMLwriter):
    """
    A class for writing the Excel XLSX Chart file.


    """

    ###########################################################################
    #
    # Public API.
    #
    ###########################################################################

    def __init__(self, options=None):
        """
        Constructor.

        """

        super(Chart, self).__init__()

        self.subtype = None
        self.sheet_type = 0x0200
        self.orientation = 0x0
        self.series = []
        self.embedded = 0
        self.id = -1
        self.series_index = 0
        self.style_id = 2
        self.axis_ids = []
        self.axis2_ids = []
        self.cat_has_num_fmt = 0
        self.requires_category = False
        self.legend = {}
        self.cat_axis_position = 'b'
        self.val_axis_position = 'l'
        self.formula_ids = {}
        self.formula_data = []
        self.horiz_cat_axis = 0
        self.horiz_val_axis = 1
        self.protection = 0
        self.chartarea = {}
        self.plotarea = {}
        self.x_axis = {}
        self.y_axis = {}
        self.y2_axis = {}
        self.x2_axis = {}
        self.chart_name = ''
        self.show_blanks = 'gap'
        self.show_hidden = 0
        self.show_crosses = 1
        self.width = 480
        self.height = 288
        self.x_scale = 1
        self.y_scale = 1
        self.x_offset = 0
        self.y_offset = 0
        self.table = None
        self.cross_between = 'between'
        self.default_marker = None
        self.series_gap_1 = None
        self.series_gap_2 = None
        self.series_overlap_1 = None
        self.series_overlap_2 = None
        self.drop_lines = None
        self.hi_low_lines = None
        self.up_down_bars = None
        self.smooth_allowed = False
        self.title_font = None
        self.title_name = None
        self.title_formula = None
        self.title_data_id = None
        self.title_layout = None
        self.title_overlay = None
        self.title_none = False
        self.date_category = False
        self.date_1904 = False
        self.remove_timezone = False
        self.label_positions = {}
        self.label_position_default = ''
        self.already_inserted = False
        self.combined = None
        self.is_secondary = False
        self.warn_sheetname = True
        self._set_default_properties()

    def add_series(self, options=None):
        """
        Add a data series to a chart.

        Args:
            options:  A dictionary of chart series options.

        Returns:
            Nothing.

        """
        # Add a series and it's properties to a chart.
        if options is None:
            options = {}

        # Check that the required input has been specified.
        if 'values' not in options:
            warn("Must specify 'values' in add_series()")
            return

        if self.requires_category and 'categories' not in options:
            warn("Must specify 'categories' in add_series() "
                 "for this chart type")
            return

        if len(self.series) == 255:
            warn("The maximum number of series that can be added to an "
                 "Excel Chart is 255")
            return

        # Convert list into a formula string.
        values = self._list_to_formula(options.get('values'))
        categories = self._list_to_formula(options.get('categories'))

        # Switch name and name_formula parameters if required.
        name, name_formula = self._process_names(options.get('name'),
                                                 options.get('name_formula'))

        # Get an id for the data equivalent to the range formula.
        cat_id = self._get_data_id(categories, options.get('categories_data'))
        val_id = self._get_data_id(values, options.get('values_data'))
        name_id = self._get_data_id(name_formula, options.get('name_data'))

        # Set the line properties for the series.
        line = Shape._get_line_properties(options.get('line'))

        # Allow 'border' as a synonym for 'line' in bar/column style charts.
        if options.get('border'):
            line = Shape._get_line_properties(options['border'])

        # Set the fill properties for the series.
        fill = Shape._get_fill_properties(options.get('fill'))

        # Set the pattern fill properties for the series.
        pattern = Shape._get_pattern_properties(options.get('pattern'))

        # Set the gradient fill properties for the series.
        gradient = Shape._get_gradient_properties(options.get('gradient'))

        # Pattern fill overrides solid fill.
        if pattern:
            self.fill = None

        # Gradient fill overrides the solid and pattern fill.
        if gradient:
            pattern = None
            fill = None

        # Set the marker properties for the series.
        marker = self._get_marker_properties(options.get('marker'))

        # Set the trendline properties for the series.
        trendline = self._get_trendline_properties(options.get('trendline'))

        # Set the line smooth property for the series.
        smooth = options.get('smooth')

        # Set the error bars properties for the series.
        y_error_bars = self._get_error_bars_props(options.get('y_error_bars'))
        x_error_bars = self._get_error_bars_props(options.get('x_error_bars'))

        error_bars = {'x_error_bars': x_error_bars,
                      'y_error_bars': y_error_bars}

        # Set the point properties for the series.
        points = self._get_points_properties(options.get('points'))

        # Set the labels properties for the series.
        labels = self._get_labels_properties(options.get('data_labels'))

        # Set the "invert if negative" fill property.
        invert_if_neg = options.get('invert_if_negative', False)

        # Set the secondary axis properties.
        x2_axis = options.get('x2_axis')
        y2_axis = options.get('y2_axis')

        # Store secondary status for combined charts.
        if x2_axis or y2_axis:
            self.is_secondary = True

        # Set the gap for Bar/Column charts.
        if options.get('gap') is not None:
            if y2_axis:
                self.series_gap_2 = options['gap']
            else:
                self.series_gap_1 = options['gap']

        # Set the overlap for Bar/Column charts.
        if options.get('overlap'):
            if y2_axis:
                self.series_overlap_2 = options['overlap']
            else:
                self.series_overlap_1 = options['overlap']

        # Add the user supplied data to the internal structures.
        series = {
            'values': values,
            'categories': categories,
            'name': name,
            'name_formula': name_formula,
            'name_id': name_id,
            'val_data_id': val_id,
            'cat_data_id': cat_id,
            'line': line,
            'fill': fill,
            'pattern': pattern,
            'gradient': gradient,
            'marker': marker,
            'trendline': trendline,
            'labels': labels,
            'invert_if_neg': invert_if_neg,
            'x2_axis': x2_axis,
            'y2_axis': y2_axis,
            'points': points,
            'error_bars': error_bars,
            'smooth': smooth
        }

        self.series.append(series)

    def set_x_axis(self, options):
        """
        Set the chart X axis options.

        Args:
            options:  A dictionary of axis options.

        Returns:
            Nothing.

        """
        axis = self._convert_axis_args(self.x_axis, options)

        self.x_axis = axis

    def set_y_axis(self, options):
        """
        Set the chart Y axis options.

        Args:
            options: A dictionary of axis options.

        Returns:
            Nothing.

        """
        axis = self._convert_axis_args(self.y_axis, options)

        self.y_axis = axis

    def set_x2_axis(self, options):
        """
        Set the chart secondary X axis options.

        Args:
            options: A dictionary of axis options.

        Returns:
            Nothing.

        """
        axis = self._convert_axis_args(self.x2_axis, options)

        self.x2_axis = axis

    def set_y2_axis(self, options):
        """
        Set the chart secondary Y axis options.

        Args:
            options: A dictionary of axis options.

        Returns:
            Nothing.

        """
        axis = self._convert_axis_args(self.y2_axis, options)

        self.y2_axis = axis

    def set_title(self, options=None):
        """
        Set the chart title options.

        Args:
            options: A dictionary of chart title options.

        Returns:
            Nothing.

        """
        if options is None:
            options = {}

        name, name_formula = self._process_names(options.get('name'),
                                                 options.get('name_formula'))

        data_id = self._get_data_id(name_formula, options.get('data'))

        self.title_name = name
        self.title_formula = name_formula
        self.title_data_id = data_id

        # Set the font properties if present.
        self.title_font = self._convert_font_args(options.get('name_font'))

        # Set the axis name layout.
        self.title_layout = self._get_layout_properties(options.get('layout'),
                                                        True)
        # Set the title overlay option.
        self.title_overlay = options.get('overlay')

        # Set the automatic title option.
        self.title_none = options.get('none')

    def set_legend(self, options):
        """
        Set the chart legend options.

        Args:
            options: A dictionary of chart legend options.

        Returns:
            Nothing.
        """
        # Convert the user defined properties to internal properties.
        self.legend = self._get_legend_properties(options)

    def set_plotarea(self, options):
        """
        Set the chart plot area options.

        Args:
            options: A dictionary of chart plot area options.

        Returns:
            Nothing.
        """
        # Convert the user defined properties to internal properties.
        self.plotarea = self._get_area_properties(options)

    def set_chartarea(self, options):
        """
        Set the chart area options.

        Args:
            options: A dictionary of chart area options.

        Returns:
            Nothing.
        """
        # Convert the user defined properties to internal properties.
        self.chartarea = self._get_area_properties(options)

    def set_style(self, style_id):
        """
        Set the chart style type.

        Args:
            style_id: An int representing the chart style.

        Returns:
            Nothing.
        """
        # Set one of the 48 built-in Excel chart styles. The default is 2.
        if style_id is None:
            style_id = 2

        if style_id < 0 or style_id > 48:
            style_id = 2

        self.style_id = style_id

    def show_blanks_as(self, option):
        """
        Set the option for displaying blank data in a chart.

        Args:
            option: A string representing the display option.

        Returns:
            Nothing.
        """
        if not option:
            return

        valid_options = {
            'gap': 1,
            'zero': 1,
            'span': 1,
        }

        if option not in valid_options:
            warn("Unknown show_blanks_as() option '%s'" % option)
            return

        self.show_blanks = option

    def show_hidden_data(self):
        """
        Display data on charts from hidden rows or columns.

        Args:
            option: A string representing the display option.

        Returns:
            Nothing.
        """
        self.show_hidden = 1

    def set_size(self, options=None):
        """
        Set size or scale of the chart.

        Args:
            options: A dictionary of chart size options.

        Returns:
            Nothing.
        """
        if options is None:
            options = {}

        # Set dimensions or scale for the chart.
        self.width = options.get('width', self.width)
        self.height = options.get('height', self.height)
        self.x_scale = options.get('x_scale', 1)
        self.y_scale = options.get('y_scale', 1)
        self.x_offset = options.get('x_offset', 0)
        self.y_offset = options.get('y_offset', 0)

    def set_table(self, options=None):
        """
        Set properties for an axis data table.

        Args:
            options: A dictionary of axis table options.

        Returns:
            Nothing.

        """
        if options is None:
            options = {}

        table = {}

        table['horizontal'] = options.get('horizontal', 1)
        table['vertical'] = options.get('vertical', 1)
        table['outline'] = options.get('outline', 1)
        table['show_keys'] = options.get('show_keys', 0)
        table['font'] = self._convert_font_args(options.get('font'))

        self.table = table

    def set_up_down_bars(self, options=None):
        """
        Set properties for the chart up-down bars.

        Args:
            options: A dictionary of options.

        Returns:
            Nothing.

        """
        if options is None:
            options = {}

        # Defaults.
        up_line = None
        up_fill = None
        down_line = None
        down_fill = None

        # Set properties for 'up' bar.
        if options.get('up'):
            if 'border' in options['up']:
                # Map border to line.
                up_line = Shape._get_line_properties(options['up']['border'])

            if 'line' in options['up']:
                up_line = Shape._get_line_properties(options['up']['line'])

            if 'fill' in options['up']:
                up_fill = Shape._get_fill_properties(options['up']['fill'])

        # Set properties for 'down' bar.
        if options.get('down'):
            if 'border' in options['down']:
                # Map border to line.
                down_line = \
                    Shape._get_line_properties(options['down']['border'])

            if 'line' in options['down']:
                down_line = Shape._get_line_properties(options['down']['line'])

            if 'fill' in options['down']:
                down_fill = Shape._get_fill_properties(options['down']['fill'])

        self.up_down_bars = {'up': {'line': up_line,
                                    'fill': up_fill,
                                    },
                             'down': {'line': down_line,
                                      'fill': down_fill,
                                      },
                             }

    def set_drop_lines(self, options=None):
        """
        Set properties for the chart drop lines.

        Args:
            options: A dictionary of options.

        Returns:
            Nothing.

        """
        if options is None:
            options = {}

        line = Shape._get_line_properties(options.get('line'))
        fill = Shape._get_fill_properties(options.get('fill'))

        # Set the pattern fill properties for the series.
        pattern = Shape._get_pattern_properties(options.get('pattern'))

        # Set the gradient fill properties for the series.
        gradient = Shape._get_gradient_properties(options.get('gradient'))

        # Pattern fill overrides solid fill.
        if pattern:
            self.fill = None

        # Gradient fill overrides the solid and pattern fill.
        if gradient:
            pattern = None
            fill = None

        self.drop_lines = {'line': line,
                           'fill': fill,
                           'pattern': pattern,
                           'gradient': gradient}

    def set_high_low_lines(self, options=None):
        """
        Set properties for the chart high-low lines.

        Args:
            options: A dictionary of options.

        Returns:
            Nothing.

        """
        if options is None:
            options = {}

        line = Shape._get_line_properties(options.get('line'))
        fill = Shape._get_fill_properties(options.get('fill'))

        # Set the pattern fill properties for the series.
        pattern = Shape._get_pattern_properties(options.get('pattern'))

        # Set the gradient fill properties for the series.
        gradient = Shape._get_gradient_properties(options.get('gradient'))

        # Pattern fill overrides solid fill.
        if pattern:
            self.fill = None

        # Gradient fill overrides the solid and pattern fill.
        if gradient:
            pattern = None
            fill = None

        self.hi_low_lines = {'line': line,
                             'fill': fill,
                             'pattern': pattern,
                             'gradient': gradient}

    def combine(self, chart=None):
        """
        Create a combination chart with a secondary chart.

        Args:
            chart: The secondary chart to combine with the primary chart.

        Returns:
            Nothing.

        """
        if chart is None:
            return

        self.combined = chart

    ###########################################################################
    #
    # Private API.
    #
    ###########################################################################

    def _assemble_xml_file(self):
        # Assemble and write the XML file.

        # Write the XML declaration.
        self._xml_declaration()

        # Write the c:chartSpace element.
        self._write_chart_space()

        # Write the c:lang element.
        self._write_lang()

        # Write the c:style element.
        self._write_style()

        # Write the c:protection element.
        self._write_protection()

        # Write the c:chart element.
        self._write_chart()

        # Write the c:spPr element for the chartarea formatting.
        self._write_sp_pr(self.chartarea)

        # Write the c:printSettings element.
        if self.embedded:
            self._write_print_settings()

        # Close the worksheet tag.
        self._xml_end_tag('c:chartSpace')
        # Close the file.
        self._xml_close()

    def _convert_axis_args(self, axis, user_options):
        # Convert user defined axis values into private hash values.
        options = axis['defaults'].copy()
        options.update(user_options)

        name, name_formula = self._process_names(options.get('name'),
                                                 options.get('name_formula'))

        data_id = self._get_data_id(name_formula, options.get('data'))

        axis = {
            'defaults': axis['defaults'],
            'name': name,
            'formula': name_formula,
            'data_id': data_id,
            'reverse': options.get('reverse'),
            'min': options.get('min'),
            'max': options.get('max'),
            'minor_unit': options.get('minor_unit'),
            'major_unit': options.get('major_unit'),
            'minor_unit_type': options.get('minor_unit_type'),
            'major_unit_type': options.get('major_unit_type'),
            'display_units': options.get('display_units'),
            'log_base': options.get('log_base'),
            'crossing': options.get('crossing'),
            'position_axis': options.get('position_axis'),
            'position': options.get('position'),
            'label_position': options.get('label_position'),
            'label_align': options.get('label_align'),
            'num_format': options.get('num_format'),
            'num_format_linked': options.get('num_format_linked'),
            'interval_unit': options.get('interval_unit'),
            'interval_tick': options.get('interval_tick'),
            'text_axis': False,
        }

        if 'visible' in options:
            axis['visible'] = options.get('visible')
        else:
            axis['visible'] = 1

        # Convert the display units.
        axis['display_units'] = self._get_display_units(axis['display_units'])
        axis['display_units_visible'] = \
            options.get('display_units_visible', True)

        # Map major_gridlines properties.
        if (options.get('major_gridlines')
                and options['major_gridlines']['visible']):
            axis['major_gridlines'] = \
                self._get_gridline_properties(options['major_gridlines'])

        # Map minor_gridlines properties.
        if (options.get('minor_gridlines')
                and options['minor_gridlines']['visible']):
            axis['minor_gridlines'] = \
                self._get_gridline_properties(options['minor_gridlines'])

        # Only use the first letter of bottom, top, left or right.
        if axis.get('position'):
            axis['position'] = axis['position'].lower()[0]

        # Set the position for a category axis on or between the tick marks.
        if axis.get('position_axis'):
            if axis['position_axis'] == 'on_tick':
                axis['position_axis'] = 'midCat'
            elif axis['position_axis'] == 'between':
                # Doesn't need to be modified.
                pass
            else:
                # Otherwise use the default value.
                axis['position_axis'] = None

        # Set the category axis as a date axis.
        if options.get('date_axis'):
            self.date_category = True

        # Set the category axis as a text axis.
        if options.get('text_axis'):
            self.date_category = False
            axis['text_axis'] = True

        # Convert datetime args if required.
        if axis.get('min') and supported_datetime(axis['min']):
            axis['min'] = datetime_to_excel_datetime(axis['min'],
                                                     self.date_1904,
                                                     self.remove_timezone)
        if axis.get('max') and supported_datetime(axis['max']):
            axis['max'] = datetime_to_excel_datetime(axis['max'],
                                                     self.date_1904,
                                                     self.remove_timezone)
        if axis.get('crossing') and supported_datetime(axis['crossing']):
            axis['crossing'] = datetime_to_excel_datetime(axis['crossing'],
                                                          self.date_1904,
                                                          self.remove_timezone)

        # Set the font properties if present.
        axis['num_font'] = self._convert_font_args(options.get('num_font'))
        axis['name_font'] = self._convert_font_args(options.get('name_font'))

        # Set the axis name layout.
        axis['name_layout'] = \
            self._get_layout_properties(options.get('name_layout'), True)

        # Set the line properties for the axis.
        axis['line'] = Shape._get_line_properties(options.get('line'))

        # Set the fill properties for the axis.
        axis['fill'] = Shape._get_fill_properties(options.get('fill'))

        # Set the pattern fill properties for the series.
        axis['pattern'] = Shape._get_pattern_properties(options.get('pattern'))

        # Set the gradient fill properties for the series.
        axis['gradient'] = \
            Shape._get_gradient_properties(options.get('gradient'))

        # Pattern fill overrides solid fill.
        if axis.get('pattern'):
            axis['fill'] = None

        # Gradient fill overrides the solid and pattern fill.
        if axis.get('gradient'):
            axis['pattern'] = None
            axis['fill'] = None

        # Set the tick marker types.
        axis['minor_tick_mark'] = \
            self._get_tick_type(options.get('minor_tick_mark'))
        axis['major_tick_mark'] = \
            self._get_tick_type(options.get('major_tick_mark'))

        return axis

    def _convert_font_args(self, options):
        # Convert user defined font values into private dict values.
        if not options:
            return

        font = {
            'name': options.get('name'),
            'color': options.get('color'),
            'size': options.get('size'),
            'bold': options.get('bold'),
            'italic': options.get('italic'),
            'underline': options.get('underline'),
            'pitch_family': options.get('pitch_family'),
            'charset': options.get('charset'),
            'baseline': options.get('baseline', 0),
            'rotation': options.get('rotation'),
        }

        # Convert font size units.
        if font['size']:
            font['size'] = int(font['size'] * 100)

        # Convert rotation into 60,000ths of a degree.
        if font['rotation']:
            font['rotation'] = 60000 * int(font['rotation'])

        return font

    def _list_to_formula(self, data):
        # Convert and list of row col values to a range formula.

        # If it isn't an array ref it is probably a formula already.
        if type(data) is not list:
            # Check for unquoted sheetnames.
            if (data and ' ' in data and "'" not in data
                    and self.warn_sheetname):
                warn("Sheetname in '%s' contains spaces but isn't quoted. "
                     "This may cause errors in Excel." % data)
            return data

        formula = xl_range_formula(*data)

        return formula

    def _process_names(self, name, name_formula):
        # Switch name and name_formula parameters if required.

        if name is not None:
            if isinstance(name, list):
                # Convert an list of values into a name formula.
                cell = xl_rowcol_to_cell(name[1], name[2], True, True)
                name_formula = quote_sheetname(name[0]) + '!' + cell
                name = ''
            elif re.match(r'^=?[^!]+!\$?[A-Z]+\$?[0-9]+', name):
                # Name looks like a formula, use it to set name_formula.
                name_formula = name
                name = ''

        return name, name_formula

    def _get_data_type(self, data):
        # Find the overall type of the data associated with a series.

        # Check for no data in the series.
        if data is None or len(data) == 0:
            return 'none'

        if isinstance(data[0], list):
            return 'multi_str'

        # Determine if data is numeric or strings.
        for token in data:
            if token is None:
                continue

            try:
                float(token)
            except ValueError:
                # Not a number. Assume entire data series is string data.
                return 'str'

        # The series data was all numeric.
        return 'num'

    def _get_data_id(self, formula, data):
        # Assign an id to a each unique series formula or title/axis formula.
        # Repeated formulas such as for categories get the same id. If the
        # series or title has user specified data associated with it then
        # that is also stored. This data is used to populate cached Excel
        # data when creating a chart. If there is no user defined data then
        # it will be populated by the parent Workbook._add_chart_data().

        # Ignore series without a range formula.
        if not formula:
            return

        # Strip the leading '=' from the formula.
        if formula.startswith('='):
            formula = formula.lstrip('=')

        # Store the data id in a hash keyed by the formula and store the data
        # in a separate array with the same id.
        if formula not in self.formula_ids:
            # Haven't seen this formula before.
            formula_id = len(self.formula_data)

            self.formula_data.append(data)
            self.formula_ids[formula] = formula_id
        else:
            # Formula already seen. Return existing id.
            formula_id = self.formula_ids[formula]

            # Store user defined data if it isn't already there.
            if self.formula_data[formula_id] is None:
                self.formula_data[formula_id] = data

        return formula_id

    def _get_marker_properties(self, marker):
        # Convert user marker properties to the structure required internally.

        if not marker:
            return

        # Copy the user defined properties since they will be modified.
        marker = copy.deepcopy(marker)

        types = {
            'automatic': 'automatic',
            'none': 'none',
            'square': 'square',
            'diamond': 'diamond',
            'triangle': 'triangle',
            'x': 'x',
            'star': 'star',
            'dot': 'dot',
            'short_dash': 'dot',
            'dash': 'dash',
            'long_dash': 'dash',
            'circle': 'circle',
            'plus': 'plus',
            'picture': 'picture',
        }

        # Check for valid types.
        marker_type = marker.get('type')

        if marker_type is not None:

            if marker_type in types:
                marker['type'] = types[marker_type]
            else:
                warn("Unknown marker type '%s" % marker_type)
                return

        # Set the line properties for the marker.
        line = Shape._get_line_properties(marker.get('line'))

        # Allow 'border' as a synonym for 'line'.
        if 'border' in marker:
            line = Shape._get_line_properties(marker['border'])

        # Set the fill properties for the marker.
        fill = Shape._get_fill_properties(marker.get('fill'))

        # Set the pattern fill properties for the series.
        pattern = Shape._get_pattern_properties(marker.get('pattern'))

        # Set the gradient fill properties for the series.
        gradient = Shape._get_gradient_properties(marker.get('gradient'))

        # Pattern fill overrides solid fill.
        if pattern:
            self.fill = None

        # Gradient fill overrides the solid and pattern fill.
        if gradient:
            pattern = None
            fill = None

        marker['line'] = line
        marker['fill'] = fill
        marker['pattern'] = pattern
        marker['gradient'] = gradient

        return marker

    def _get_trendline_properties(self, trendline):
        # Convert user trendline properties to structure required internally.

        if not trendline:
            return

        # Copy the user defined properties since they will be modified.
        trendline = copy.deepcopy(trendline)

        types = {
            'exponential': 'exp',
            'linear': 'linear',
            'log': 'log',
            'moving_average': 'movingAvg',
            'polynomial': 'poly',
            'power': 'power',
        }

        # Check the trendline type.
        trend_type = trendline.get('type')

        if trend_type in types:
            trendline['type'] = types[trend_type]
        else:
            warn("Unknown trendline type '%s'" % trend_type)
            return

        # Set the line properties for the trendline.
        line = Shape._get_line_properties(trendline.get('line'))

        # Allow 'border' as a synonym for 'line'.
        if 'border' in trendline:
            line = Shape._get_line_properties(trendline['border'])

        # Set the fill properties for the trendline.
        fill = Shape._get_fill_properties(trendline.get('fill'))

        # Set the pattern fill properties for the series.
        pattern = Shape._get_pattern_properties(trendline.get('pattern'))

        # Set the gradient fill properties for the series.
        gradient = Shape._get_gradient_properties(trendline.get('gradient'))

        # Pattern fill overrides solid fill.
        if pattern:
            self.fill = None

        # Gradient fill overrides the solid and pattern fill.
        if gradient:
            pattern = None
            fill = None

        trendline['line'] = line
        trendline['fill'] = fill
        trendline['pattern'] = pattern
        trendline['gradient'] = gradient

        return trendline

    def _get_error_bars_props(self, options):
        # Convert user error bars properties to structure required internally.
        if not options:
            return

        # Default values.
        error_bars = {
            'type': 'fixedVal',
            'value': 1,
            'endcap': 1,
            'direction': 'both'
        }

        types = {
            'fixed': 'fixedVal',
            'percentage': 'percentage',
            'standard_deviation': 'stdDev',
            'standard_error': 'stdErr',
            'custom': 'cust',
        }

        # Check the error bars type.
        error_type = options['type']

        if error_type in types:
            error_bars['type'] = types[error_type]
        else:
            warn("Unknown error bars type '%s" % error_type)
            return

        # Set the value for error types that require it.
        if 'value' in options:
            error_bars['value'] = options['value']

        # Set the end-cap style.
        if 'end_style' in options:
            error_bars['endcap'] = options['end_style']

        # Set the error bar direction.
        if 'direction' in options:
            if options['direction'] == 'minus':
                error_bars['direction'] = 'minus'
            elif options['direction'] == 'plus':
                error_bars['direction'] = 'plus'
            else:
                # Default to 'both'.
                pass

        # Set any custom values.
        error_bars['plus_values'] = options.get('plus_values')
        error_bars['minus_values'] = options.get('minus_values')
        error_bars['plus_data'] = options.get('plus_data')
        error_bars['minus_data'] = options.get('minus_data')

        # Set the line properties for the error bars.
        error_bars['line'] = Shape._get_line_properties(options.get('line'))

        return error_bars

    def _get_gridline_properties(self, options):
        # Convert user gridline properties to structure required internally.

        # Set the visible property for the gridline.
        gridline = {'visible': options.get('visible')}

        # Set the line properties for the gridline.
        gridline['line'] = Shape._get_line_properties(options.get('line'))

        return gridline

    def _get_labels_properties(self, labels):
        # Convert user labels properties to the structure required internally.

        if not labels:
            return None

        # Copy the user defined properties since they will be modified.
        labels = copy.deepcopy(labels)

        # Map user defined label positions to Excel positions.
        position = labels.get('position')

        if position:
            if position in self.label_positions:
                if position == self.label_position_default:
                    labels['position'] = None
                else:
                    labels['position'] = self.label_positions[position]
            else:
                warn("Unsupported label position '%s' for this chart type"
                     % position)
                return

        # Map the user defined label separator to the Excel separator.
        separator = labels.get('separator')
        separators = {
            ',': ', ',
            ';': '; ',
            '.': '. ',
            "\n": "\n",
            ' ': ' ',
        }

        if separator:
            if separator in separators:
                labels['separator'] = separators[separator]
            else:
                warn("Unsupported label separator")
                return

        # Set the font properties if present.
        labels['font'] = self._convert_font_args(labels.get('font'))

        return labels

    def _get_area_properties(self, options):
        # Convert user area properties to the structure required internally.
        area = {}

        # Set the line properties for the chartarea.
        line = Shape._get_line_properties(options.get('line'))

        # Allow 'border' as a synonym for 'line'.
        if options.get('border'):
            line = Shape._get_line_properties(options['border'])

        # Set the fill properties for the chartarea.
        fill = Shape._get_fill_properties(options.get('fill'))

        # Set the pattern fill properties for the series.
        pattern = Shape._get_pattern_properties(options.get('pattern'))

        # Set the gradient fill properties for the series.
        gradient = Shape._get_gradient_properties(options.get('gradient'))

        # Pattern fill overrides solid fill.
        if pattern:
            self.fill = None

        # Gradient fill overrides the solid and pattern fill.
        if gradient:
            pattern = None
            fill = None

        # Set the plotarea layout.
        layout = self._get_layout_properties(options.get('layout'), False)

        area['line'] = line
        area['fill'] = fill
        area['pattern'] = pattern
        area['layout'] = layout
        area['gradient'] = gradient

        return area

    def _get_legend_properties(self, options=None):
        # Convert user legend properties to the structure required internally.
        legend = {}

        if options is None:
            options = {}

        legend['position'] = options.get('position', 'right')
        legend['delete_series'] = options.get('delete_series')
        legend['font'] = self._convert_font_args(options.get('font'))
        legend['layout'] = self._get_layout_properties(options.get('layout'),
                                                       False)

        # Turn off the legend.
        if options.get('none'):
            legend['position'] = 'none'

        # Set the line properties for the legend.
        line = Shape._get_line_properties(options.get('line'))

        # Allow 'border' as a synonym for 'line'.
        if options.get('border'):
            line = Shape._get_line_properties(options['border'])

        # Set the fill properties for the legend.
        fill = Shape._get_fill_properties(options.get('fill'))

        # Set the pattern fill properties for the series.
        pattern = Shape._get_pattern_properties(options.get('pattern'))

        # Set the gradient fill properties for the series.
        gradient = Shape._get_gradient_properties(options.get('gradient'))

        # Pattern fill overrides solid fill.
        if pattern:
            self.fill = None

        # Gradient fill overrides the solid and pattern fill.
        if gradient:
            pattern = None
            fill = None

        # Set the legend layout.
        layout = self._get_layout_properties(options.get('layout'), False)

        legend['line'] = line
        legend['fill'] = fill
        legend['pattern'] = pattern
        legend['layout'] = layout
        legend['gradient'] = gradient

        return legend

    def _get_layout_properties(self, args, is_text):
        # Convert user defined layout properties to format used internally.
        layout = {}

        if not args:
            return

        if is_text:
            properties = ('x', 'y')
        else:
            properties = ('x', 'y', 'width', 'height')

        # Check for valid properties.
        for key in args.keys():
            if key not in properties:
                warn("Property '%s' allowed not in layout options" % key)
                return

        # Set the layout properties.
        for prop in properties:
            if prop not in args.keys():
                warn("Property '%s' must be specified in layout options"
                     % prop)
                return

            value = args[prop]

            try:
                float(value)
            except ValueError:
                warn("Property '%s' value '%s' must be numeric in layout" %
                     (prop, value))
                return

            if value < 0 or value > 1:
                warn("Property '%s' value '%s' must be in range "
                     "0 < x <= 1 in layout options" % (prop, value))
                return

            # Convert to the format used by Excel for easier testing
            layout[prop] = "%.17g" % value

        return layout

    def _get_points_properties(self, user_points):
        # Convert user points properties to structure required internally.
        points = []

        if not user_points:
            return

        for user_point in user_points:
            point = {}

            if user_point is not None:

                # Set the line properties for the point.
                line = Shape._get_line_properties(user_point.get('line'))

                # Allow 'border' as a synonym for 'line'.
                if 'border' in user_point:
                    line = Shape._get_line_properties(user_point['border'])

                # Set the fill properties for the chartarea.
                fill = Shape._get_fill_properties(user_point.get('fill'))

                # Set the pattern fill properties for the series.
                pattern = \
                    Shape._get_pattern_properties(user_point.get('pattern'))

                # Set the gradient fill properties for the series.
                gradient = \
                    Shape._get_gradient_properties(user_point.get('gradient'))

                # Pattern fill overrides solid fill.
                if pattern:
                    self.fill = None

                # Gradient fill overrides the solid and pattern fill.
                if gradient:
                    pattern = None
                    fill = None

                point['line'] = line
                point['fill'] = fill
                point['pattern'] = pattern
                point['gradient'] = gradient

            points.append(point)

        return points

    def _get_display_units(self, display_units):
        # Convert user defined display units to internal units.
        if not display_units:
            return

        types = {
            'hundreds': 'hundreds',
            'thousands': 'thousands',
            'ten_thousands': 'tenThousands',
            'hundred_thousands': 'hundredThousands',
            'millions': 'millions',
            'ten_millions': 'tenMillions',
            'hundred_millions': 'hundredMillions',
            'billions': 'billions',
            'trillions': 'trillions',
        }

        if display_units in types:
            display_units = types[display_units]
        else:
            warn("Unknown display_units type '%s'" % display_units)
            return

        return display_units

    def _get_tick_type(self, tick_type):
        # Convert user defined display units to internal units.
        if not tick_type:
            return

        types = {
            'outside': 'out',
            'inside': 'in',
            'none': 'none',
            'cross': 'cross',
        }

        if tick_type in types:
            tick_type = types[tick_type]
        else:
            warn("Unknown tick_type  '%s'" % tick_type)
            return

        return tick_type

    def _get_primary_axes_series(self):
        # Returns series which use the primary axes.
        primary_axes_series = []

        for series in self.series:
            if not series['y2_axis']:
                primary_axes_series.append(series)

        return primary_axes_series

    def _get_secondary_axes_series(self):
        # Returns series which use the secondary axes.
        secondary_axes_series = []

        for series in self.series:
            if series['y2_axis']:
                secondary_axes_series.append(series)

        return secondary_axes_series

    def _add_axis_ids(self, args):
        # Add unique ids for primary or secondary axes
        chart_id = 5001 + int(self.id)
        axis_count = 1 + len(self.axis2_ids) + len(self.axis_ids)

        id1 = '%04d%04d' % (chart_id, axis_count)
        id2 = '%04d%04d' % (chart_id, axis_count + 1)

        if args['primary_axes']:
            self.axis_ids.append(id1)
            self.axis_ids.append(id2)

        if not args['primary_axes']:
            self.axis2_ids.append(id1)
            self.axis2_ids.append(id2)

    def _set_default_properties(self):
        # Setup the default properties for a chart.

        self.x_axis['defaults'] = {
            'num_format': 'General',
            'major_gridlines': {'visible': 0}
        }

        self.y_axis['defaults'] = {
            'num_format': 'General',
            'major_gridlines': {'visible': 1}
        }

        self.x2_axis['defaults'] = {
            'num_format': 'General',
            'label_position': 'none',
            'crossing': 'max',
            'visible': 0
        }

        self.y2_axis['defaults'] = {
            'num_format': 'General',
            'major_gridlines': {'visible': 0},
            'position': 'right',
            'visible': 1
        }

        self.set_x_axis({})
        self.set_y_axis({})

        self.set_x2_axis({})
        self.set_y2_axis({})

    ###########################################################################
    #
    # XML methods.
    #
    ###########################################################################

    def _write_chart_space(self):
        # Write the <c:chartSpace> element.
        schema = 'http://schemas.openxmlformats.org/'
        xmlns_c = schema + 'drawingml/2006/chart'
        xmlns_a = schema + 'drawingml/2006/main'
        xmlns_r = schema + 'officeDocument/2006/relationships'

        attributes = [
            ('xmlns:c', xmlns_c),
            ('xmlns:a', xmlns_a),
            ('xmlns:r', xmlns_r),
        ]

        self._xml_start_tag('c:chartSpace', attributes)

    def _write_lang(self):
        # Write the <c:lang> element.
        val = 'en-US'

        attributes = [('val', val)]

        self._xml_empty_tag('c:lang', attributes)

    def _write_style(self):
        # Write the <c:style> element.
        style_id = self.style_id

        # Don't write an element for the default style, 2.
        if style_id == 2:
            return

        attributes = [('val', style_id)]

        self._xml_empty_tag('c:style', attributes)

    def _write_chart(self):
        # Write the <c:chart> element.
        self._xml_start_tag('c:chart')

        if self.title_none:
            # Turn off the title.
            self._write_c_auto_title_deleted()
        else:
            # Write the chart title elements.
            if self.title_formula is not None:
                self._write_title_formula(self.title_formula,
                                          self.title_data_id,
                                          None,
                                          self.title_font,
                                          self.title_layout,
                                          self.title_overlay)
            elif self.title_name is not None:
                self._write_title_rich(self.title_name,
                                       None,
                                       self.title_font,
                                       self.title_layout,
                                       self.title_overlay)

        # Write the c:plotArea element.
        self._write_plot_area()

        # Write the c:legend element.
        self._write_legend()

        # Write the c:plotVisOnly element.
        self._write_plot_vis_only()

        # Write the c:dispBlanksAs element.
        self._write_disp_blanks_as()

        self._xml_end_tag('c:chart')

    def _write_disp_blanks_as(self):
        # Write the <c:dispBlanksAs> element.
        val = self.show_blanks

        # Ignore the default value.
        if val == 'gap':
            return

        attributes = [('val', val)]

        self._xml_empty_tag('c:dispBlanksAs', attributes)

    def _write_plot_area(self):
        # Write the <c:plotArea> element.
        self._xml_start_tag('c:plotArea')

        # Write the c:layout element.
        self._write_layout(self.plotarea.get('layout'), 'plot')

        # Write  subclass chart type elements for primary and secondary axes.
        self._write_chart_type({'primary_axes': True})
        self._write_chart_type({'primary_axes': False})

        # Configure a combined chart if present.
        second_chart = self.combined
        if second_chart:
            # Secondary axis has unique id otherwise use same as primary.
            if second_chart.is_secondary:
                second_chart.id = 1000 + self.id
            else:
                second_chart.id = self.id

            # Share the same filehandle for writing.
            second_chart.fh = self.fh

            # Share series index with primary chart.
            second_chart.series_index = self.series_index

            # Write the subclass chart type elements for combined chart.
            second_chart._write_chart_type({'primary_axes': True})
            second_chart._write_chart_type({'primary_axes': False})

        # Write the category and value elements for the primary axes.
        args = {'x_axis': self.x_axis,
                'y_axis': self.y_axis,
                'axis_ids': self.axis_ids}

        if self.date_category:
            self._write_date_axis(args)
        else:
            self._write_cat_axis(args)

        self._write_val_axis(args)

        # Write the category and value elements for the secondary axes.
        args = {'x_axis': self.x2_axis,
                'y_axis': self.y2_axis,
                'axis_ids': self.axis2_ids}

        self._write_val_axis(args)

        # Write the secondary axis for the secondary chart.
        if second_chart and second_chart.is_secondary:
            args = {'x_axis': second_chart.x2_axis,
                    'y_axis': second_chart.y2_axis,
                    'axis_ids': second_chart.axis2_ids}

            second_chart._write_val_axis(args)

        if self.date_category:
            self._write_date_axis(args)
        else:
            self._write_cat_axis(args)

        # Write the c:dTable element.
        self._write_d_table()

        # Write the c:spPr element for the plotarea formatting.
        self._write_sp_pr(self.plotarea)

        self._xml_end_tag('c:plotArea')

    def _write_layout(self, layout, layout_type):
        # Write the <c:layout> element.

        if not layout:
            # Automatic layout.
            self._xml_empty_tag('c:layout')
        else:
            # User defined manual layout.
            self._xml_start_tag('c:layout')
            self._write_manual_layout(layout, layout_type)
            self._xml_end_tag('c:layout')

    def _write_manual_layout(self, layout, layout_type):
        # Write the <c:manualLayout> element.
        self._xml_start_tag('c:manualLayout')

        # Plotarea has a layoutTarget element.
        if layout_type == 'plot':
            self._xml_empty_tag('c:layoutTarget', [('val', 'inner')])

        # Set the x, y positions.
        self._xml_empty_tag('c:xMode', [('val', 'edge')])
        self._xml_empty_tag('c:yMode', [('val', 'edge')])
        self._xml_empty_tag('c:x', [('val', layout['x'])])
        self._xml_empty_tag('c:y', [('val', layout['y'])])

        # For plotarea and legend set the width and height.
        if layout_type != 'text':
            self._xml_empty_tag('c:w', [('val', layout['width'])])
            self._xml_empty_tag('c:h', [('val', layout['height'])])

        self._xml_end_tag('c:manualLayout')

    def _write_chart_type(self, options):
        # Write the chart type element. This method should be overridden
        # by the subclasses.
        return

    def _write_grouping(self, val):
        # Write the <c:grouping> element.
        attributes = [('val', val)]

        self._xml_empty_tag('c:grouping', attributes)

    def _write_series(self, series):
        # Write the series elements.
        self._write_ser(series)

    def _write_ser(self, series):
        # Write the <c:ser> element.
        index = self.series_index
        self.series_index += 1

        self._xml_start_tag('c:ser')

        # Write the c:idx element.
        self._write_idx(index)

        # Write the c:order element.
        self._write_order(index)

        # Write the series name.
        self._write_series_name(series)

        # Write the c:spPr element.
        self._write_sp_pr(series)

        # Write the c:marker element.
        self._write_marker(series['marker'])

        # Write the c:invertIfNegative element.
        self._write_c_invert_if_negative(series['invert_if_neg'])

        # Write the c:dPt element.
        self._write_d_pt(series['points'])

        # Write the c:dLbls element.
        self._write_d_lbls(series['labels'])

        # Write the c:trendline element.
        self._write_trendline(series['trendline'])

        # Write the c:errBars element.
        self._write_error_bars(series['error_bars'])

        # Write the c:cat element.
        self._write_cat(series)

        # Write the c:val element.
        self._write_val(series)

        # Write the c:smooth element.
        if self.smooth_allowed:
            self._write_c_smooth(series['smooth'])

        self._xml_end_tag('c:ser')

    def _write_idx(self, val):
        # Write the <c:idx> element.

        attributes = [('val', val)]

        self._xml_empty_tag('c:idx', attributes)

    def _write_order(self, val):
        # Write the <c:order> element.

        attributes = [('val', val)]

        self._xml_empty_tag('c:order', attributes)

    def _write_series_name(self, series):
        # Write the series name.

        if series['name_formula'] is not None:
            self._write_tx_formula(series['name_formula'], series['name_id'])
        elif series['name'] is not None:
            self._write_tx_value(series['name'])

    def _write_c_smooth(self, smooth):
        # Write the <c:smooth> element.

        if smooth:
            self._xml_empty_tag('c:smooth', [('val', '1')])

    def _write_cat(self, series):
        # Write the <c:cat> element.
        formula = series['categories']
        data_id = series['cat_data_id']
        data = None

        if data_id is not None:
            data = self.formula_data[data_id]

        # Ignore <c:cat> elements for charts without category values.
        if not formula:
            return

        self._xml_start_tag('c:cat')

        # Check the type of cached data.
        cat_type = self._get_data_type(data)

        if cat_type == 'str':
            self.cat_has_num_fmt = 0
            # Write the c:numRef element.
            self._write_str_ref(formula, data, cat_type)

        elif cat_type == 'multi_str':
            self.cat_has_num_fmt = 0
            # Write the c:numRef element.
            self._write_multi_lvl_str_ref(formula, data)

        else:
            self.cat_has_num_fmt = 1
            # Write the c:numRef element.
            self._write_num_ref(formula, data, cat_type)

        self._xml_end_tag('c:cat')

    def _write_val(self, series):
        # Write the <c:val> element.
        formula = series['values']
        data_id = series['val_data_id']
        data = self.formula_data[data_id]

        self._xml_start_tag('c:val')

        # Unlike Cat axes data should only be numeric.
        # Write the c:numRef element.
        self._write_num_ref(formula, data, 'num')

        self._xml_end_tag('c:val')

    def _write_num_ref(self, formula, data, ref_type):
        # Write the <c:numRef> element.
        self._xml_start_tag('c:numRef')

        # Write the c:f element.
        self._write_series_formula(formula)

        if ref_type == 'num':
            # Write the c:numCache element.
            self._write_num_cache(data)
        elif ref_type == 'str':
            # Write the c:strCache element.
            self._write_str_cache(data)

        self._xml_end_tag('c:numRef')

    def _write_str_ref(self, formula, data, ref_type):
        # Write the <c:strRef> element.

        self._xml_start_tag('c:strRef')

        # Write the c:f element.
        self._write_series_formula(formula)

        if ref_type == 'num':
            # Write the c:numCache element.
            self._write_num_cache(data)
        elif ref_type == 'str':
            # Write the c:strCache element.
            self._write_str_cache(data)

        self._xml_end_tag('c:strRef')

    def _write_multi_lvl_str_ref(self, formula, data):
        # Write the <c:multiLvlStrRef> element.

        if not data:
            return

        self._xml_start_tag('c:multiLvlStrRef')

        # Write the c:f element.
        self._write_series_formula(formula)

        self._xml_start_tag('c:multiLvlStrCache')

        # Write the c:ptCount element.
        count = len(data[-1])
        self._write_pt_count(count)

        for cat_data in reversed(data):

            self._xml_start_tag('c:lvl')

            for i, point in enumerate(cat_data):
                # Write the c:pt element.
                self._write_pt(i, cat_data[i])

            self._xml_end_tag('c:lvl')

        self._xml_end_tag('c:multiLvlStrCache')
        self._xml_end_tag('c:multiLvlStrRef')

    def _write_series_formula(self, formula):
        # Write the <c:f> element.

        # Strip the leading '=' from the formula.
        if formula.startswith('='):
            formula = formula.lstrip('=')

        self._xml_data_element('c:f', formula)

    def _write_axis_ids(self, args):
        # Write the <c:axId> elements for the primary or secondary axes.

        # Generate the axis ids.
        self._add_axis_ids(args)

        if args['primary_axes']:
            # Write the axis ids for the primary axes.
            self._write_axis_id(self.axis_ids[0])
            self._write_axis_id(self.axis_ids[1])
        else:
            # Write the axis ids for the secondary axes.
            self._write_axis_id(self.axis2_ids[0])
            self._write_axis_id(self.axis2_ids[1])

    def _write_axis_id(self, val):
        # Write the <c:axId> element.

        attributes = [('val', val)]

        self._xml_empty_tag('c:axId', attributes)

    def _write_cat_axis(self, args):
        # Write the <c:catAx> element. Usually the X axis.
        x_axis = args['x_axis']
        y_axis = args['y_axis']
        axis_ids = args['axis_ids']

        # If there are no axis_ids then we don't need to write this element.
        if axis_ids is None or not len(axis_ids):
            return

        position = self.cat_axis_position
        horiz = self.horiz_cat_axis

        # Overwrite the default axis position with a user supplied value.
        if x_axis.get('position'):
            position = x_axis['position']

        self._xml_start_tag('c:catAx')

        self._write_axis_id(axis_ids[0])

        # Write the c:scaling element.
        self._write_scaling(x_axis.get('reverse'),
                            None,
                            None,
                            None)

        if not x_axis.get('visible'):
            self._write_delete(1)

        # Write the c:axPos element.
        self._write_axis_pos(position, y_axis.get('reverse'))

        # Write the c:majorGridlines element.
        self._write_major_gridlines(x_axis.get('major_gridlines'))

        # Write the c:minorGridlines element.
        self._write_minor_gridlines(x_axis.get('minor_gridlines'))

        # Write the axis title elements.
        if x_axis['formula'] is not None:
            self._write_title_formula(x_axis['formula'],
                                      x_axis['data_id'],
                                      horiz,
                                      x_axis['name_font'],
                                      x_axis['name_layout'])
        elif x_axis['name'] is not None:
            self._write_title_rich(x_axis['name'],
                                   horiz,
                                   x_axis['name_font'],
                                   x_axis['name_layout'])

        # Write the c:numFmt element.
        self._write_cat_number_format(x_axis)

        # Write the c:majorTickMark element.
        self._write_major_tick_mark(x_axis.get('major_tick_mark'))

        # Write the c:minorTickMark element.
        self._write_minor_tick_mark(x_axis.get('minor_tick_mark'))

        # Write the c:tickLblPos element.
        self._write_tick_label_pos(x_axis.get('label_position'))

        # Write the c:spPr element for the axis line.
        self._write_sp_pr(x_axis)

        # Write the axis font elements.
        self._write_axis_font(x_axis.get('num_font'))

        # Write the c:crossAx element.
        self._write_cross_axis(axis_ids[1])

        if self.show_crosses or x_axis.get('visible'):

            # Note, the category crossing comes from the value axis.
            if (y_axis.get('crossing') is None
                    or y_axis.get('crossing') == 'max'):

                # Write the c:crosses element.
                self._write_crosses(y_axis.get('crossing'))
            else:

                # Write the c:crossesAt element.
                self._write_c_crosses_at(y_axis.get('crossing'))

        # Write the c:auto element.
        if not x_axis.get('text_axis'):
            self._write_auto(1)

        # Write the c:labelAlign element.
        self._write_label_align(x_axis.get('label_align'))

        # Write the c:labelOffset element.
        self._write_label_offset(100)

        # Write the c:tickLblSkip element.
        self._write_c_tick_lbl_skip(x_axis.get('interval_unit'))

        # Write the c:tickMarkSkip element.
        self._write_c_tick_mark_skip(x_axis.get('interval_tick'))

        self._xml_end_tag('c:catAx')

    def _write_val_axis(self, args):
        # Write the <c:valAx> element. Usually the Y axis.
        x_axis = args['x_axis']
        y_axis = args['y_axis']
        axis_ids = args['axis_ids']
        position = args.get('position', self.val_axis_position)
        horiz = self.horiz_val_axis

        # If there are no axis_ids then we don't need to write this element.
        if axis_ids is None or not len(axis_ids):
            return

        # Overwrite the default axis position with a user supplied value.
        position = y_axis.get('position') or position

        self._xml_start_tag('c:valAx')

        self._write_axis_id(axis_ids[1])

        # Write the c:scaling element.
        self._write_scaling(y_axis.get('reverse'),
                            y_axis.get('min'),
                            y_axis.get('max'),
                            y_axis.get('log_base'))

        if not y_axis.get('visible'):
            self._write_delete(1)

        # Write the c:axPos element.
        self._write_axis_pos(position, x_axis.get('reverse'))

        # Write the c:majorGridlines element.
        self._write_major_gridlines(y_axis.get('major_gridlines'))

        # Write the c:minorGridlines element.
        self._write_minor_gridlines(y_axis.get('minor_gridlines'))

        # Write the axis title elements.
        if y_axis['formula'] is not None:
            self._write_title_formula(y_axis['formula'],
                                      y_axis['data_id'],
                                      horiz,
                                      y_axis['name_font'],
                                      y_axis['name_layout'])
        elif y_axis['name'] is not None:
            self._write_title_rich(y_axis['name'],
                                   horiz,
                                   y_axis.get('name_font'),
                                   y_axis.get('name_layout'))

        # Write the c:numberFormat element.
        self._write_number_format(y_axis)

        # Write the c:majorTickMark element.
        self._write_major_tick_mark(y_axis.get('major_tick_mark'))

        # Write the c:minorTickMark element.
        self._write_minor_tick_mark(y_axis.get('minor_tick_mark'))

        # Write the c:tickLblPos element.
        self._write_tick_label_pos(y_axis.get('label_position'))

        # Write the c:spPr element for the axis line.
        self._write_sp_pr(y_axis)

        # Write the axis font elements.
        self._write_axis_font(y_axis.get('num_font'))

        # Write the c:crossAx element.
        self._write_cross_axis(axis_ids[0])

        # Note, the category crossing comes from the value axis.
        if x_axis.get('crossing') is None or x_axis['crossing'] == 'max':

            # Write the c:crosses element.
            self._write_crosses(x_axis.get('crossing'))
        else:

            # Write the c:crossesAt element.
            self._write_c_crosses_at(x_axis.get('crossing'))

        # Write the c:crossBetween element.
        self._write_cross_between(x_axis.get('position_axis'))

        # Write the c:majorUnit element.
        self._write_c_major_unit(y_axis.get('major_unit'))

        # Write the c:minorUnit element.
        self._write_c_minor_unit(y_axis.get('minor_unit'))

        # Write the c:dispUnits element.
        self._write_disp_units(y_axis.get('display_units'),
                               y_axis.get('display_units_visible'))

        self._xml_end_tag('c:valAx')

    def _write_cat_val_axis(self, args):
        # Write the <c:valAx> element. This is for the second valAx
        # in scatter plots. Usually the X axis.
        x_axis = args['x_axis']
        y_axis = args['y_axis']
        axis_ids = args['axis_ids']
        position = args['position'] or self.val_axis_position
        horiz = self.horiz_val_axis

        # If there are no axis_ids then we don't need to write this element.
        if axis_ids is None or not len(axis_ids):
            return

        # Overwrite the default axis position with a user supplied value.
        position = x_axis.get('position') or position

        self._xml_start_tag('c:valAx')

        self._write_axis_id(axis_ids[0])

        # Write the c:scaling element.
        self._write_scaling(x_axis.get('reverse'),
                            x_axis.get('min'),
                            x_axis.get('max'),
                            x_axis.get('log_base'))

        if not x_axis.get('visible'):
            self._write_delete(1)

        # Write the c:axPos element.
        self._write_axis_pos(position, y_axis.get('reverse'))

        # Write the c:majorGridlines element.
        self._write_major_gridlines(x_axis.get('major_gridlines'))

        # Write the c:minorGridlines element.
        self._write_minor_gridlines(x_axis.get('minor_gridlines'))

        # Write the axis title elements.
        if x_axis['formula'] is not None:
            self._write_title_formula(x_axis['formula'],
                                      x_axis['data_id'],
                                      horiz,
                                      x_axis['name_font'],
                                      x_axis['name_layout'])
        elif x_axis['name'] is not None:
            self._write_title_rich(x_axis['name'],
                                   horiz,
                                   x_axis['name_font'],
                                   x_axis['name_layout'])

        # Write the c:numberFormat element.
        self._write_number_format(x_axis)

        # Write the c:majorTickMark element.
        self._write_major_tick_mark(x_axis.get('major_tick_mark'))

        # Write the c:minorTickMark element.
        self._write_minor_tick_mark(x_axis.get('minor_tick_mark'))

        # Write the c:tickLblPos element.
        self._write_tick_label_pos(x_axis.get('label_position'))

        # Write the c:spPr element for the axis line.
        self._write_sp_pr(x_axis)

        # Write the axis font elements.
        self._write_axis_font(x_axis.get('num_font'))

        # Write the c:crossAx element.
        self._write_cross_axis(axis_ids[1])

        # Note, the category crossing comes from the value axis.
        if y_axis.get('crossing') is None or y_axis['crossing'] == 'max':

            # Write the c:crosses element.
            self._write_crosses(y_axis.get('crossing'))
        else:

            # Write the c:crossesAt element.
            self._write_c_crosses_at(y_axis.get('crossing'))

        # Write the c:crossBetween element.
        self._write_cross_between(y_axis.get('position_axis'))

        # Write the c:majorUnit element.
        self._write_c_major_unit(x_axis.get('major_unit'))

        # Write the c:minorUnit element.
        self._write_c_minor_unit(x_axis.get('minor_unit'))

        # Write the c:dispUnits element.
        self._write_disp_units(x_axis.get('display_units'),
                               x_axis.get('display_units_visible'))

        self._xml_end_tag('c:valAx')

    def _write_date_axis(self, args):
        # Write the <c:dateAx> element. Usually the X axis.
        x_axis = args['x_axis']
        y_axis = args['y_axis']
        axis_ids = args['axis_ids']

        # If there are no axis_ids then we don't need to write this element.
        if axis_ids is None or not len(axis_ids):
            return

        position = self.cat_axis_position

        # Overwrite the default axis position with a user supplied value.
        position = x_axis.get('position') or position

        self._xml_start_tag('c:dateAx')

        self._write_axis_id(axis_ids[0])

        # Write the c:scaling element.
        self._write_scaling(x_axis.get('reverse'),
                            x_axis.get('min'),
                            x_axis.get('max'),
                            x_axis.get('log_base'))

        if not x_axis.get('visible'):
            self._write_delete(1)

        # Write the c:axPos element.
        self._write_axis_pos(position, y_axis.get('reverse'))

        # Write the c:majorGridlines element.
        self._write_major_gridlines(x_axis.get('major_gridlines'))

        # Write the c:minorGridlines element.
        self._write_minor_gridlines(x_axis.get('minor_gridlines'))

        # Write the axis title elements.
        if x_axis['formula'] is not None:
            self._write_title_formula(x_axis['formula'],
                                      x_axis['data_id'],
                                      None,
                                      x_axis['name_font'],
                                      x_axis['name_layout'])
        elif x_axis['name'] is not None:
            self._write_title_rich(x_axis['name'],
                                   None,
                                   x_axis['name_font'],
                                   x_axis['name_layout'])

        # Write the c:numFmt element.
        self._write_number_format(x_axis)

        # Write the c:majorTickMark element.
        self._write_major_tick_mark(x_axis.get('major_tick_mark'))

        # Write the c:minorTickMark element.
        self._write_minor_tick_mark(x_axis.get('minor_tick_mark'))

        # Write the c:tickLblPos element.
        self._write_tick_label_pos(x_axis.get('label_position'))

        # Write the c:spPr element for the axis line.
        self._write_sp_pr(x_axis)

        # Write the axis font elements.
        self._write_axis_font(x_axis.get('num_font'))

        # Write the c:crossAx element.
        self._write_cross_axis(axis_ids[1])

        if self.show_crosses or x_axis.get('visible'):

            # Note, the category crossing comes from the value axis.
            if (y_axis.get('crossing') is None
                    or y_axis.get('crossing') == 'max'):

                # Write the c:crosses element.
                self._write_crosses(y_axis.get('crossing'))
            else:

                # Write the c:crossesAt element.
                self._write_c_crosses_at(y_axis.get('crossing'))

        # Write the c:auto element.
        self._write_auto(1)

        # Write the c:labelOffset element.
        self._write_label_offset(100)

        # Write the c:tickLblSkip element.
        self._write_c_tick_lbl_skip(x_axis.get('interval_unit'))

        # Write the c:tickMarkSkip element.
        self._write_c_tick_mark_skip(x_axis.get('interval_tick'))

        # Write the c:majorUnit element.
        self._write_c_major_unit(x_axis.get('major_unit'))

        # Write the c:majorTimeUnit element.
        if x_axis.get('major_unit'):
            self._write_c_major_time_unit(x_axis['major_unit_type'])

        # Write the c:minorUnit element.
        self._write_c_minor_unit(x_axis.get('minor_unit'))

        # Write the c:minorTimeUnit element.
        if x_axis.get('minor_unit'):
            self._write_c_minor_time_unit(x_axis['minor_unit_type'])

        self._xml_end_tag('c:dateAx')

    def _write_scaling(self, reverse, min_val, max_val, log_base):
        # Write the <c:scaling> element.

        self._xml_start_tag('c:scaling')

        # Write the c:logBase element.
        self._write_c_log_base(log_base)

        # Write the c:orientation element.
        self._write_orientation(reverse)

        # Write the c:max element.
        self._write_c_max(max_val)

        # Write the c:min element.
        self._write_c_min(min_val)

        self._xml_end_tag('c:scaling')

    def _write_c_log_base(self, val):
        # Write the <c:logBase> element.

        if not val:
            return

        attributes = [('val', val)]

        self._xml_empty_tag('c:logBase', attributes)

    def _write_orientation(self, reverse):
        # Write the <c:orientation> element.
        val = 'minMax'

        if reverse:
            val = 'maxMin'

        attributes = [('val', val)]

        self._xml_empty_tag('c:orientation', attributes)

    def _write_c_max(self, max_val):
        # Write the <c:max> element.

        if max_val is None:
            return

        attributes = [('val', max_val)]

        self._xml_empty_tag('c:max', attributes)

    def _write_c_min(self, min_val):
        # Write the <c:min> element.

        if min_val is None:
            return

        attributes = [('val', min_val)]

        self._xml_empty_tag('c:min', attributes)

    def _write_axis_pos(self, val, reverse):
        # Write the <c:axPos> element.

        if reverse:
            if val == 'l':
                val = 'r'
            if val == 'b':
                val = 't'

        attributes = [('val', val)]

        self._xml_empty_tag('c:axPos', attributes)

    def _write_number_format(self, axis):
        # Write the <c:numberFormat> element. Note: It is assumed that if
        # a user defined number format is supplied (i.e., non-default) then
        # the sourceLinked attribute is 0.
        # The user can override this if required.
        format_code = axis.get('num_format')
        source_linked = 1

        # Check if a user defined number format has been set.
        if (format_code is not None
                and format_code != axis['defaults']['num_format']):
            source_linked = 0

        # User override of sourceLinked.
        if axis.get('num_format_linked'):
            source_linked = 1

        attributes = [
            ('formatCode', format_code),
            ('sourceLinked', source_linked),
        ]

        self._xml_empty_tag('c:numFmt', attributes)

    def _write_cat_number_format(self, axis):
        # Write the <c:numFmt> element. Special case handler for category
        # axes which don't always have a number format.
        format_code = axis.get('num_format')
        source_linked = 1
        default_format = 1

        # Check if a user defined number format has been set.
        if (format_code is not None
                and format_code != axis['defaults']['num_format']):
            source_linked = 0
            default_format = 0

        # User override of sourceLinked.
        if axis.get('num_format_linked'):
            source_linked = 1

        # Skip if cat doesn't have a num format (unless it is non-default).
        if not self.cat_has_num_fmt and default_format:
            return

        attributes = [
            ('formatCode', format_code),
            ('sourceLinked', source_linked),
        ]

        self._xml_empty_tag('c:numFmt', attributes)

    def _write_data_label_number_format(self, format_code):
        # Write the <c:numberFormat> element for data labels.
        source_linked = 0

        attributes = [
            ('formatCode', format_code),
            ('sourceLinked', source_linked),
        ]

        self._xml_empty_tag('c:numFmt', attributes)

    def _write_major_tick_mark(self, val):
        # Write the <c:majorTickMark> element.

        if not val:
            return

        attributes = [('val', val)]

        self._xml_empty_tag('c:majorTickMark', attributes)

    def _write_minor_tick_mark(self, val):
        # Write the <c:minorTickMark> element.

        if not val:
            return

        attributes = [('val', val)]

        self._xml_empty_tag('c:minorTickMark', attributes)

    def _write_tick_label_pos(self, val=None):
        # Write the <c:tickLblPos> element.
        if val is None or val == 'next_to':
            val = 'nextTo'

        attributes = [('val', val)]

        self._xml_empty_tag('c:tickLblPos', attributes)

    def _write_cross_axis(self, val):
        # Write the <c:crossAx> element.

        attributes = [('val', val)]

        self._xml_empty_tag('c:crossAx', attributes)

    def _write_crosses(self, val=None):
        # Write the <c:crosses> element.
        if val is None:
            val = 'autoZero'

        attributes = [('val', val)]

        self._xml_empty_tag('c:crosses', attributes)

    def _write_c_crosses_at(self, val):
        # Write the <c:crossesAt> element.

        attributes = [('val', val)]

        self._xml_empty_tag('c:crossesAt', attributes)

    def _write_auto(self, val):
        # Write the <c:auto> element.

        attributes = [('val', val)]

        self._xml_empty_tag('c:auto', attributes)

    def _write_label_align(self, val=None):
        # Write the <c:labelAlign> element.

        if val is None:
            val = 'ctr'

        if val is 'right':
            val = 'r'

        if val is 'left':
            val = 'l'

        attributes = [('val', val)]

        self._xml_empty_tag('c:lblAlgn', attributes)

    def _write_label_offset(self, val):
        # Write the <c:labelOffset> element.

        attributes = [('val', val)]

        self._xml_empty_tag('c:lblOffset', attributes)

    def _write_c_tick_lbl_skip(self, val):
        # Write the <c:tickLblSkip> element.
        if val is None:
            return

        attributes = [('val', val)]

        self._xml_empty_tag('c:tickLblSkip', attributes)

    def _write_c_tick_mark_skip(self, val):
        # Write the <c:tickMarkSkip> element.
        if val is None:
            return

        attributes = [('val', val)]

        self._xml_empty_tag('c:tickMarkSkip', attributes)

    def _write_major_gridlines(self, gridlines):
        # Write the <c:majorGridlines> element.

        if not gridlines:
            return

        if not gridlines['visible']:
            return

        if gridlines['line']['defined']:
            self._xml_start_tag('c:majorGridlines')

            # Write the c:spPr element.
            self._write_sp_pr(gridlines)

            self._xml_end_tag('c:majorGridlines')
        else:
            self._xml_empty_tag('c:majorGridlines')

    def _write_minor_gridlines(self, gridlines):
        # Write the <c:minorGridlines> element.

        if not gridlines:
            return

        if not gridlines['visible']:
            return

        if gridlines['line']['defined']:
            self._xml_start_tag('c:minorGridlines')

            # Write the c:spPr element.
            self._write_sp_pr(gridlines)

            self._xml_end_tag('c:minorGridlines')
        else:
            self._xml_empty_tag('c:minorGridlines')

    def _write_cross_between(self, val):
        # Write the <c:crossBetween> element.
        if val is None:
            val = self.cross_between

        attributes = [('val', val)]

        self._xml_empty_tag('c:crossBetween', attributes)

    def _write_c_major_unit(self, val):
        # Write the <c:majorUnit> element.

        if not val:
            return

        attributes = [('val', val)]

        self._xml_empty_tag('c:majorUnit', attributes)

    def _write_c_minor_unit(self, val):
        # Write the <c:minorUnit> element.

        if not val:
            return

        attributes = [('val', val)]

        self._xml_empty_tag('c:minorUnit', attributes)

    def _write_c_major_time_unit(self, val=None):
        # Write the <c:majorTimeUnit> element.
        if val is None:
            val = 'days'

        attributes = [('val', val)]

        self._xml_empty_tag('c:majorTimeUnit', attributes)

    def _write_c_minor_time_unit(self, val=None):
        # Write the <c:minorTimeUnit> element.
        if val is None:
            val = 'days'

        attributes = [('val', val)]

        self._xml_empty_tag('c:minorTimeUnit', attributes)

    def _write_legend(self):
        # Write the <c:legend> element.
        legend = self.legend
        position = legend.get('position', 'right')
        font = legend.get('font')
        delete_series = []
        overlay = 0

        if (legend.get('delete_series')
                and type(legend['delete_series']) is list):
            delete_series = legend['delete_series']

        if position.startswith('overlay_'):
            position = position.replace('overlay_', '')
            overlay = 1

        allowed = {
            'right': 'r',
            'left': 'l',
            'top': 't',
            'bottom': 'b',
            'top_right': 'tr',
        }

        if position == 'none':
            return

        if position not in allowed:
            return

        position = allowed[position]

        self._xml_start_tag('c:legend')

        # Write the c:legendPos element.
        self._write_legend_pos(position)

        # Remove series labels from the legend.
        for index in delete_series:
            # Write the c:legendEntry element.
            self._write_legend_entry(index)

        # Write the c:layout element.
        self._write_layout(legend.get('layout'), 'legend')

        # Write the c:overlay element.
        if overlay:
            self._write_overlay()

        if font:
            self._write_tx_pr(None, font)

        # Write the c:spPr element.
        self._write_sp_pr(legend)

        self._xml_end_tag('c:legend')

    def _write_legend_pos(self, val):
        # Write the <c:legendPos> element.

        attributes = [('val', val)]

        self._xml_empty_tag('c:legendPos', attributes)

    def _write_legend_entry(self, index):
        # Write the <c:legendEntry> element.

        self._xml_start_tag('c:legendEntry')

        # Write the c:idx element.
        self._write_idx(index)

        # Write the c:delete element.
        self._write_delete(1)

        self._xml_end_tag('c:legendEntry')

    def _write_overlay(self):
        # Write the <c:overlay> element.
        val = 1

        attributes = [('val', val)]

        self._xml_empty_tag('c:overlay', attributes)

    def _write_plot_vis_only(self):
        # Write the <c:plotVisOnly> element.
        val = 1

        # Ignore this element if we are plotting hidden data.
        if self.show_hidden:
            return

        attributes = [('val', val)]

        self._xml_empty_tag('c:plotVisOnly', attributes)

    def _write_print_settings(self):
        # Write the <c:printSettings> element.
        self._xml_start_tag('c:printSettings')

        # Write the c:headerFooter element.
        self._write_header_footer()

        # Write the c:pageMargins element.
        self._write_page_margins()

        # Write the c:pageSetup element.
        self._write_page_setup()

        self._xml_end_tag('c:printSettings')

    def _write_header_footer(self):
        # Write the <c:headerFooter> element.
        self._xml_empty_tag('c:headerFooter')

    def _write_page_margins(self):
        # Write the <c:pageMargins> element.
        bottom = 0.75
        left = 0.7
        right = 0.7
        top = 0.75
        header = 0.3
        footer = 0.3

        attributes = [
            ('b', bottom),
            ('l', left),
            ('r', right),
            ('t', top),
            ('header', header),
            ('footer', footer),
        ]

        self._xml_empty_tag('c:pageMargins', attributes)

    def _write_page_setup(self):
        # Write the <c:pageSetup> element.
        self._xml_empty_tag('c:pageSetup')

    def _write_c_auto_title_deleted(self):
        # Write the <c:autoTitleDeleted> element.
        self._xml_empty_tag('c:autoTitleDeleted', [('val', 1)])

    def _write_title_rich(self, title, horiz, font, layout, overlay=False):
        # Write the <c:title> element for a rich string.

        self._xml_start_tag('c:title')

        # Write the c:tx element.
        self._write_tx_rich(title, horiz, font)

        # Write the c:layout element.
        self._write_layout(layout, 'text')

        # Write the c:overlay element.
        if overlay:
            self._write_overlay()

        self._xml_end_tag('c:title')

    def _write_title_formula(self, title, data_id, horiz, font, layout,
                             overlay=False):
        # Write the <c:title> element for a rich string.

        self._xml_start_tag('c:title')

        # Write the c:tx element.
        self._write_tx_formula(title, data_id)

        # Write the c:layout element.
        self._write_layout(layout, 'text')

        # Write the c:overlay element.
        if overlay:
            self._write_overlay()

        # Write the c:txPr element.
        self._write_tx_pr(horiz, font)

        self._xml_end_tag('c:title')

    def _write_tx_rich(self, title, horiz, font):
        # Write the <c:tx> element.

        self._xml_start_tag('c:tx')

        # Write the c:rich element.
        self._write_rich(title, horiz, font)

        self._xml_end_tag('c:tx')

    def _write_tx_value(self, title):
        # Write the <c:tx> element with a value such as for series names.

        self._xml_start_tag('c:tx')

        # Write the c:v element.
        self._write_v(title)

        self._xml_end_tag('c:tx')

    def _write_tx_formula(self, title, data_id):
        # Write the <c:tx> element.
        data = None

        if data_id is not None:
            data = self.formula_data[data_id]

        self._xml_start_tag('c:tx')

        # Write the c:strRef element.
        self._write_str_ref(title, data, 'str')

        self._xml_end_tag('c:tx')

    def _write_rich(self, title, horiz, font):
        # Write the <c:rich> element.

        if font and font.get('rotation'):
            rotation = font['rotation']
        else:
            rotation = None

        self._xml_start_tag('c:rich')

        # Write the a:bodyPr element.
        self._write_a_body_pr(rotation, horiz)

        # Write the a:lstStyle element.
        self._write_a_lst_style()

        # Write the a:p element.
        self._write_a_p_rich(title, font)

        self._xml_end_tag('c:rich')

    def _write_a_body_pr(self, rotation, horiz):
        # Write the <a:bodyPr> element.
        attributes = []

        if rotation is None and horiz:
            rotation = -5400000

        if rotation is not None:
            attributes.append(('rot', rotation))

        if horiz:
            attributes.append(('vert', 'horz'))

        self._xml_empty_tag('a:bodyPr', attributes)

    def _write_a_lst_style(self):
        # Write the <a:lstStyle> element.
        self._xml_empty_tag('a:lstStyle')

    def _write_a_p_rich(self, title, font):
        # Write the <a:p> element for rich string titles.

        self._xml_start_tag('a:p')

        # Write the a:pPr element.
        self._write_a_p_pr_rich(font)

        # Write the a:r element.
        self._write_a_r(title, font)

        self._xml_end_tag('a:p')

    def _write_a_p_formula(self, font):
        # Write the <a:p> element for formula titles.

        self._xml_start_tag('a:p')

        # Write the a:pPr element.
        self._write_a_p_pr_formula(font)

        # Write the a:endParaRPr element.
        self._write_a_end_para_rpr()

        self._xml_end_tag('a:p')

    def _write_a_p_pr_rich(self, font):
        # Write the <a:pPr> element for rich string titles.

        self._xml_start_tag('a:pPr')

        # Write the a:defRPr element.
        self._write_a_def_rpr(font)

        self._xml_end_tag('a:pPr')

    def _write_a_p_pr_formula(self, font):
        # Write the <a:pPr> element for formula titles.

        self._xml_start_tag('a:pPr')

        # Write the a:defRPr element.
        self._write_a_def_rpr(font)

        self._xml_end_tag('a:pPr')

    def _write_a_def_rpr(self, font):
        # Write the <a:defRPr> element.
        has_color = 0

        style_attributes = Shape._get_font_style_attributes(font)
        latin_attributes = Shape._get_font_latin_attributes(font)

        if font and font.get('color') is not None:
            has_color = 1

        if latin_attributes or has_color:
            self._xml_start_tag('a:defRPr', style_attributes)

            if has_color:
                self._write_a_solid_fill({'color': font['color']})

            if latin_attributes:
                self._write_a_latin(latin_attributes)

            self._xml_end_tag('a:defRPr')
        else:
            self._xml_empty_tag('a:defRPr', style_attributes)

    def _write_a_end_para_rpr(self):
        # Write the <a:endParaRPr> element.
        lang = 'en-US'

        attributes = [('lang', lang)]

        self._xml_empty_tag('a:endParaRPr', attributes)

    def _write_a_r(self, title, font):
        # Write the <a:r> element.

        self._xml_start_tag('a:r')

        # Write the a:rPr element.
        self._write_a_r_pr(font)

        # Write the a:t element.
        self._write_a_t(title)

        self._xml_end_tag('a:r')

    def _write_a_r_pr(self, font):
        # Write the <a:rPr> element.
        has_color = 0
        lang = 'en-US'

        style_attributes = Shape._get_font_style_attributes(font)
        latin_attributes = Shape._get_font_latin_attributes(font)

        if font and font['color'] is not None:
            has_color = 1

        # Add the lang type to the attributes.
        style_attributes.insert(0, ('lang', lang))

        if latin_attributes or has_color:
            self._xml_start_tag('a:rPr', style_attributes)

            if has_color:
                self._write_a_solid_fill({'color': font['color']})

            if latin_attributes:
                self._write_a_latin(latin_attributes)

            self._xml_end_tag('a:rPr')
        else:
            self._xml_empty_tag('a:rPr', style_attributes)

    def _write_a_t(self, title):
        # Write the <a:t> element.

        self._xml_data_element('a:t', title)

    def _write_tx_pr(self, horiz, font):
        # Write the <c:txPr> element.

        if font and font.get('rotation'):
            rotation = font['rotation']
        else:
            rotation = None

        self._xml_start_tag('c:txPr')

        # Write the a:bodyPr element.
        self._write_a_body_pr(rotation, horiz)

        # Write the a:lstStyle element.
        self._write_a_lst_style()

        # Write the a:p element.
        self._write_a_p_formula(font)

        self._xml_end_tag('c:txPr')

    def _write_marker(self, marker):
        # Write the <c:marker> element.
        if marker is None:
            marker = self.default_marker

        if not marker:
            return

        if marker['type'] == 'automatic':
            return

        self._xml_start_tag('c:marker')

        # Write the c:symbol element.
        self._write_symbol(marker['type'])

        # Write the c:size element.
        if marker.get('size'):
            self._write_marker_size(marker['size'])

        # Write the c:spPr element.
        self._write_sp_pr(marker)

        self._xml_end_tag('c:marker')

    def _write_marker_size(self, val):
        # Write the <c:size> element.

        attributes = [('val', val)]

        self._xml_empty_tag('c:size', attributes)

    def _write_symbol(self, val):
        # Write the <c:symbol> element.

        attributes = [('val', val)]

        self._xml_empty_tag('c:symbol', attributes)

    def _write_sp_pr(self, series):
        # Write the <c:spPr> element.

        has_fill = False
        has_line = False
        has_pattern = series.get('pattern')
        has_gradient = series.get('gradient')

        if series.get('fill') and series['fill']['defined']:
            has_fill = True

        if series.get('line') and series['line']['defined']:
            has_line = True

        if (not has_fill and not has_line and not has_pattern
                and not has_gradient):
            return

        self._xml_start_tag('c:spPr')

        # Write the fill elements for solid charts such as pie and bar.
        if series.get('fill') and series['fill']['defined']:
            if 'none' in series['fill']:
                # Write the a:noFill element.
                self._write_a_no_fill()
            else:
                # Write the a:solidFill element.
                self._write_a_solid_fill(series['fill'])

        if series.get('pattern'):
            # Write the a:gradFill element.
            self._write_a_patt_fill(series['pattern'])

        if series.get('gradient'):
            # Write the a:gradFill element.
            self._write_a_grad_fill(series['gradient'])

        # Write the a:ln element.
        if series.get('line') and series['line']['defined']:
            self._write_a_ln(series['line'])

        self._xml_end_tag('c:spPr')

    def _write_a_ln(self, line):
        # Write the <a:ln> element.
        attributes = []

        # Add the line width as an attribute.
        width = line.get('width')

        if width:
            # Round width to nearest 0.25, like Excel.
            width = int((width + 0.125) * 4) / 4.0

            # Convert to internal units.
            width = int(0.5 + (12700 * width))

            attributes = [('w', width)]

        self._xml_start_tag('a:ln', attributes)

        # Write the line fill.
        if 'none' in line:
            # Write the a:noFill element.
            self._write_a_no_fill()
        elif 'color' in line:
            # Write the a:solidFill element.
            self._write_a_solid_fill(line)

        # Write the line/dash type.
        line_type = line.get('dash_type')
        if line_type:
            # Write the a:prstDash element.
            self._write_a_prst_dash(line_type)

        self._xml_end_tag('a:ln')

    def _write_a_no_fill(self):
        # Write the <a:noFill> element.
        self._xml_empty_tag('a:noFill')

    def _write_a_solid_fill(self, fill):
        # Write the <a:solidFill> element.

        self._xml_start_tag('a:solidFill')

        if 'color' in fill:
            color = get_rgb_color(fill['color'])
            transparency = fill.get('transparency')
            # Write the a:srgbClr element.
            self._write_a_srgb_clr(color, transparency)

        self._xml_end_tag('a:solidFill')

    def _write_a_srgb_clr(self, val, transparency=None):
        # Write the <a:srgbClr> element.
        attributes = [('val', val)]

        if transparency:
            self._xml_start_tag('a:srgbClr', attributes)

            # Write the a:alpha element.
            self._write_a_alpha(transparency)

            self._xml_end_tag('a:srgbClr')
        else:
            self._xml_empty_tag('a:srgbClr', attributes)

    def _write_a_alpha(self, val):
        # Write the <a:alpha> element.

        val = int((100 - int(val)) * 1000)

        attributes = [('val', val)]

        self._xml_empty_tag('a:alpha', attributes)

    def _write_a_prst_dash(self, val):
        # Write the <a:prstDash> element.

        attributes = [('val', val)]

        self._xml_empty_tag('a:prstDash', attributes)

    def _write_trendline(self, trendline):
        # Write the <c:trendline> element.

        if not trendline:
            return

        self._xml_start_tag('c:trendline')

        # Write the c:name element.
        self._write_name(trendline.get('name'))

        # Write the c:spPr element.
        self._write_sp_pr(trendline)

        # Write the c:trendlineType element.
        self._write_trendline_type(trendline['type'])

        # Write the c:order element for polynomial trendlines.
        if trendline['type'] == 'poly':
            self._write_trendline_order(trendline.get('order'))

        # Write the c:period element for moving average trendlines.
        if trendline['type'] == 'movingAvg':
            self._write_period(trendline.get('period'))

        # Write the c:forward element.
        self._write_forward(trendline.get('forward'))

        # Write the c:backward element.
        self._write_backward(trendline.get('backward'))

        if 'intercept' in trendline:
            # Write the c:intercept element.
            self._write_c_intercept(trendline['intercept'])

        if trendline.get('display_r_squared'):
            # Write the c:dispRSqr element.
            self._write_c_disp_rsqr()

        if trendline.get('display_equation'):
            # Write the c:dispEq element.
            self._write_c_disp_eq()

            # Write the c:trendlineLbl element.
            self._write_c_trendline_lbl()

        self._xml_end_tag('c:trendline')

    def _write_trendline_type(self, val):
        # Write the <c:trendlineType> element.

        attributes = [('val', val)]

        self._xml_empty_tag('c:trendlineType', attributes)

    def _write_name(self, data):
        # Write the <c:name> element.

        if data is None:
            return

        self._xml_data_element('c:name', data)

    def _write_trendline_order(self, val):
        # Write the <c:order> element.
        if val < 2:
            val = 2

        attributes = [('val', val)]

        self._xml_empty_tag('c:order', attributes)

    def _write_period(self, val):
        # Write the <c:period> element.
        if val < 2:
            val = 2

        attributes = [('val', val)]

        self._xml_empty_tag('c:period', attributes)

    def _write_forward(self, val):
        # Write the <c:forward> element.

        if not val:
            return

        attributes = [('val', val)]

        self._xml_empty_tag('c:forward', attributes)

    def _write_backward(self, val):
        # Write the <c:backward> element.

        if not val:
            return

        attributes = [('val', val)]

        self._xml_empty_tag('c:backward', attributes)

    def _write_c_intercept(self, val):
        # Write the <c:intercept> element.
        attributes = [('val', val)]

        self._xml_empty_tag('c:intercept', attributes)

    def _write_c_disp_eq(self):
        # Write the <c:dispEq> element.
        attributes = [('val', 1)]

        self._xml_empty_tag('c:dispEq', attributes)

    def _write_c_disp_rsqr(self):
        # Write the <c:dispRSqr> element.
        attributes = [('val', 1)]

        self._xml_empty_tag('c:dispRSqr', attributes)

    def _write_c_trendline_lbl(self):
        # Write the <c:trendlineLbl> element.
        self._xml_start_tag('c:trendlineLbl')

        # Write the c:layout element.
        self._write_layout(None, None)

        # Write the c:numFmt element.
        self._write_trendline_num_fmt()

        self._xml_end_tag('c:trendlineLbl')

    def _write_trendline_num_fmt(self):
        # Write the <c:numFmt> element.
        attributes = [
            ('formatCode', 'General'),
            ('sourceLinked', 0),
        ]

        self._xml_empty_tag('c:numFmt', attributes)

    def _write_hi_low_lines(self):
        # Write the <c:hiLowLines> element.
        hi_low_lines = self.hi_low_lines

        if hi_low_lines is None:
            return

        if 'line' in hi_low_lines and hi_low_lines['line']['defined']:

            self._xml_start_tag('c:hiLowLines')

            # Write the c:spPr element.
            self._write_sp_pr(hi_low_lines)

            self._xml_end_tag('c:hiLowLines')
        else:
            self._xml_empty_tag('c:hiLowLines')

    def _write_drop_lines(self):
        # Write the <c:dropLines> element.
        drop_lines = self.drop_lines

        if drop_lines is None:
            return

        if drop_lines['line']['defined']:

            self._xml_start_tag('c:dropLines')

            # Write the c:spPr element.
            self._write_sp_pr(drop_lines)

            self._xml_end_tag('c:dropLines')
        else:
            self._xml_empty_tag('c:dropLines')

    def _write_overlap(self, val):
        # Write the <c:overlap> element.

        if val is None:
            return

        attributes = [('val', val)]

        self._xml_empty_tag('c:overlap', attributes)

    def _write_num_cache(self, data):
        # Write the <c:numCache> element.
        if data:
            count = len(data)
        else:
            count = 0

        self._xml_start_tag('c:numCache')

        # Write the c:formatCode element.
        self._write_format_code('General')

        # Write the c:ptCount element.
        self._write_pt_count(count)

        for i in range(count):
            token = data[i]

            if token is None:
                continue

            try:
                float(token)
            except ValueError:
                # Write non-numeric data as 0.
                token = 0

            # Write the c:pt element.
            self._write_pt(i, token)

        self._xml_end_tag('c:numCache')

    def _write_str_cache(self, data):
        # Write the <c:strCache> element.
        count = len(data)

        self._xml_start_tag('c:strCache')

        # Write the c:ptCount element.
        self._write_pt_count(count)

        for i in range(count):
            # Write the c:pt element.
            self._write_pt(i, data[i])

        self._xml_end_tag('c:strCache')

    def _write_format_code(self, data):
        # Write the <c:formatCode> element.

        self._xml_data_element('c:formatCode', data)

    def _write_pt_count(self, val):
        # Write the <c:ptCount> element.

        attributes = [('val', val)]

        self._xml_empty_tag('c:ptCount', attributes)

    def _write_pt(self, idx, value):
        # Write the <c:pt> element.

        if value is None:
            return

        attributes = [('idx', idx)]

        self._xml_start_tag('c:pt', attributes)

        # Write the c:v element.
        self._write_v(value)

        self._xml_end_tag('c:pt')

    def _write_v(self, data):
        # Write the <c:v> element.

        self._xml_data_element('c:v', data)

    def _write_protection(self):
        # Write the <c:protection> element.
        if not self.protection:
            return

        self._xml_empty_tag('c:protection')

    def _write_d_pt(self, points):
        # Write the <c:dPt> elements.
        index = -1

        if not points:
            return

        for point in points:
            index += 1
            if not point:
                continue

            self._write_d_pt_point(index, point)

    def _write_d_pt_point(self, index, point):
        # Write an individual <c:dPt> element.

            self._xml_start_tag('c:dPt')

            # Write the c:idx element.
            self._write_idx(index)

            # Write the c:spPr element.
            self._write_sp_pr(point)

            self._xml_end_tag('c:dPt')

    def _write_d_lbls(self, labels):
        # Write the <c:dLbls> element.

        if not labels:
            return

        self._xml_start_tag('c:dLbls')

        # Write the c:numFmt element.
        if labels.get('num_format'):
            self._write_data_label_number_format(labels['num_format'])

        # Write the data label font elements.
        if labels.get('font'):
            self._write_axis_font(labels['font'])

        # Write the c:dLblPos element.
        if labels.get('position'):
            self._write_d_lbl_pos(labels['position'])

        # Write the c:showLegendKey element.
        if labels.get('legend_key'):
            self._write_show_legend_key()

        # Write the c:showVal element.
        if labels.get('value'):
            self._write_show_val()

        # Write the c:showCatName element.
        if labels.get('category'):
            self._write_show_cat_name()

        # Write the c:showSerName element.
        if labels.get('series_name'):
            self._write_show_ser_name()

        # Write the c:showPercent element.
        if labels.get('percentage'):
            self._write_show_percent()

        # Write the c:separator element.
        if labels.get('separator'):
            self._write_separator(labels['separator'])

        # Write the c:showLeaderLines element.
        if labels.get('leader_lines'):
            self._write_show_leader_lines()

        self._xml_end_tag('c:dLbls')

    def _write_show_legend_key(self):
        # Write the <c:showLegendKey> element.
        val = '1'

        attributes = [('val', val)]

        self._xml_empty_tag('c:showLegendKey', attributes)

    def _write_show_val(self):
        # Write the <c:showVal> element.
        val = 1

        attributes = [('val', val)]

        self._xml_empty_tag('c:showVal', attributes)

    def _write_show_cat_name(self):
        # Write the <c:showCatName> element.
        val = 1

        attributes = [('val', val)]

        self._xml_empty_tag('c:showCatName', attributes)

    def _write_show_ser_name(self):
        # Write the <c:showSerName> element.
        val = 1

        attributes = [('val', val)]

        self._xml_empty_tag('c:showSerName', attributes)

    def _write_show_percent(self):
        # Write the <c:showPercent> element.
        val = 1

        attributes = [('val', val)]

        self._xml_empty_tag('c:showPercent', attributes)

    def _write_separator(self, data):
        # Write the <c:separator> element.
        self._xml_data_element('c:separator', data)

    def _write_show_leader_lines(self):
        # Write the <c:showLeaderLines> element.
        val = 1

        attributes = [('val', val)]

        self._xml_empty_tag('c:showLeaderLines', attributes)

    def _write_d_lbl_pos(self, val):
        # Write the <c:dLblPos> element.

        attributes = [('val', val)]

        self._xml_empty_tag('c:dLblPos', attributes)

    def _write_delete(self, val):
        # Write the <c:delete> element.

        attributes = [('val', val)]

        self._xml_empty_tag('c:delete', attributes)

    def _write_c_invert_if_negative(self, invert):
        # Write the <c:invertIfNegative> element.
        val = 1

        if not invert:
            return

        attributes = [('val', val)]

        self._xml_empty_tag('c:invertIfNegative', attributes)

    def _write_axis_font(self, font):
        # Write the axis font elements.

        if not font:
            return

        self._xml_start_tag('c:txPr')
        self._write_a_body_pr(font.get('rotation'), None)
        self._write_a_lst_style()
        self._xml_start_tag('a:p')

        self._write_a_p_pr_rich(font)

        self._write_a_end_para_rpr()
        self._xml_end_tag('a:p')
        self._xml_end_tag('c:txPr')

    def _write_a_latin(self, attributes):
        # Write the <a:latin> element.
        self._xml_empty_tag('a:latin', attributes)

    def _write_d_table(self):
        # Write the <c:dTable> element.
        table = self.table

        if not table:
            return

        self._xml_start_tag('c:dTable')

        if table['horizontal']:
            # Write the c:showHorzBorder element.
            self._write_show_horz_border()

        if table['vertical']:
            # Write the c:showVertBorder element.
            self._write_show_vert_border()

        if table['outline']:
            # Write the c:showOutline element.
            self._write_show_outline()

        if table['show_keys']:
            # Write the c:showKeys element.
            self._write_show_keys()

        if table['font']:
            # Write the table font.
            self._write_tx_pr(None, table['font'])

        self._xml_end_tag('c:dTable')

    def _write_show_horz_border(self):
        # Write the <c:showHorzBorder> element.
        attributes = [('val', 1)]

        self._xml_empty_tag('c:showHorzBorder', attributes)

    def _write_show_vert_border(self):
        # Write the <c:showVertBorder> element.
        attributes = [('val', 1)]

        self._xml_empty_tag('c:showVertBorder', attributes)

    def _write_show_outline(self):
        # Write the <c:showOutline> element.
        attributes = [('val', 1)]

        self._xml_empty_tag('c:showOutline', attributes)

    def _write_show_keys(self):
        # Write the <c:showKeys> element.
        attributes = [('val', 1)]

        self._xml_empty_tag('c:showKeys', attributes)

    def _write_error_bars(self, error_bars):
        # Write the X and Y error bars.

        if not error_bars:
            return

        if error_bars['x_error_bars']:
            self._write_err_bars('x', error_bars['x_error_bars'])

        if error_bars['y_error_bars']:
            self._write_err_bars('y', error_bars['y_error_bars'])

    def _write_err_bars(self, direction, error_bars):
        # Write the <c:errBars> element.

        if not error_bars:
            return

        self._xml_start_tag('c:errBars')

        # Write the c:errDir element.
        self._write_err_dir(direction)

        # Write the c:errBarType element.
        self._write_err_bar_type(error_bars['direction'])

        # Write the c:errValType element.
        self._write_err_val_type(error_bars['type'])

        if not error_bars['endcap']:
            # Write the c:noEndCap element.
            self._write_no_end_cap()

        if error_bars['type'] == 'stdErr':
            # Don't need to write a c:errValType tag.
            pass
        elif error_bars['type'] == 'cust':
            # Write the custom error tags.
            self._write_custom_error(error_bars)
        else:
            # Write the c:val element.
            self._write_error_val(error_bars['value'])

        # Write the c:spPr element.
        self._write_sp_pr(error_bars)

        self._xml_end_tag('c:errBars')

    def _write_err_dir(self, val):
        # Write the <c:errDir> element.

        attributes = [('val', val)]

        self._xml_empty_tag('c:errDir', attributes)

    def _write_err_bar_type(self, val):
        # Write the <c:errBarType> element.

        attributes = [('val', val)]

        self._xml_empty_tag('c:errBarType', attributes)

    def _write_err_val_type(self, val):
        # Write the <c:errValType> element.

        attributes = [('val', val)]

        self._xml_empty_tag('c:errValType', attributes)

    def _write_no_end_cap(self):
        # Write the <c:noEndCap> element.
        attributes = [('val', 1)]

        self._xml_empty_tag('c:noEndCap', attributes)

    def _write_error_val(self, val):
        # Write the <c:val> element for error bars.

        attributes = [('val', val)]

        self._xml_empty_tag('c:val', attributes)

    def _write_custom_error(self, error_bars):
        # Write the custom error bars tags.

        if error_bars['plus_values']:
            # Write the c:plus element.
            self._xml_start_tag('c:plus')

            if isinstance(error_bars['plus_values'], list):
                self._write_num_lit(error_bars['plus_values'])
            else:
                self._write_num_ref(error_bars['plus_values'],
                                    error_bars['plus_data'],
                                    'num')
            self._xml_end_tag('c:plus')

        if error_bars['minus_values']:
            # Write the c:minus element.
            self._xml_start_tag('c:minus')

            if isinstance(error_bars['minus_values'], list):
                self._write_num_lit(error_bars['minus_values'])
            else:
                self._write_num_ref(error_bars['minus_values'],
                                    error_bars['minus_data'],
                                    'num')
            self._xml_end_tag('c:minus')

    def _write_num_lit(self, data):
        # Write the <c:numLit> element for literal number list elements.
        count = len(data)

        # Write the c:numLit element.
        self._xml_start_tag('c:numLit')

        # Write the c:formatCode element.
        self._write_format_code('General')

        # Write the c:ptCount element.
        self._write_pt_count(count)

        for i in range(count):
            token = data[i]

            if token is None:
                continue

            try:
                float(token)
            except ValueError:
                # Write non-numeric data as 0.
                token = 0

            # Write the c:pt element.
            self._write_pt(i, token)

        self._xml_end_tag('c:numLit')

    def _write_up_down_bars(self):
        # Write the <c:upDownBars> element.
        up_down_bars = self.up_down_bars

        if up_down_bars is None:
            return

        self._xml_start_tag('c:upDownBars')

        # Write the c:gapWidth element.
        self._write_gap_width(150)

        # Write the c:upBars element.
        self._write_up_bars(up_down_bars.get('up'))

        # Write the c:downBars element.
        self._write_down_bars(up_down_bars.get('down'))

        self._xml_end_tag('c:upDownBars')

    def _write_gap_width(self, val):
        # Write the <c:gapWidth> element.

        if val is None:
            return

        attributes = [('val', val)]

        self._xml_empty_tag('c:gapWidth', attributes)

    def _write_up_bars(self, bar_format):
        # Write the <c:upBars> element.

        if bar_format['line'] and bar_format['line']['defined']:
            self._xml_start_tag('c:upBars')

            # Write the c:spPr element.
            self._write_sp_pr(bar_format)

            self._xml_end_tag('c:upBars')
        else:
            self._xml_empty_tag('c:upBars')

    def _write_down_bars(self, bar_format):
        # Write the <c:downBars> element.

        if bar_format['line'] and bar_format['line']['defined']:
            self._xml_start_tag('c:downBars')

            # Write the c:spPr element.
            self._write_sp_pr(bar_format)

            self._xml_end_tag('c:downBars')
        else:
            self._xml_empty_tag('c:downBars')

    def _write_disp_units(self, units, display):
        # Write the <c:dispUnits> element.

        if not units:
            return

        attributes = [('val', units)]

        self._xml_start_tag('c:dispUnits')
        self._xml_empty_tag('c:builtInUnit', attributes)

        if display:
            self._xml_start_tag('c:dispUnitsLbl')
            self._xml_empty_tag('c:layout')
            self._xml_end_tag('c:dispUnitsLbl')

        self._xml_end_tag('c:dispUnits')

    def _write_a_grad_fill(self, gradient):
        # Write the <a:gradFill> element.

        attributes = [('flip', 'none'), ('rotWithShape', '1')]

        if gradient['type'] == 'linear':
            attributes = []

        self._xml_start_tag('a:gradFill', attributes)

        # Write the a:gsLst element.
        self._write_a_gs_lst(gradient)

        if gradient['type'] == 'linear':
            # Write the a:lin element.
            self._write_a_lin(gradient['angle'])
        else:
            # Write the a:path element.
            self._write_a_path(gradient['type'])

            # Write the a:tileRect element.
            self._write_a_tile_rect(gradient['type'])

        self._xml_end_tag('a:gradFill')

    def _write_a_gs_lst(self, gradient):
        # Write the <a:gsLst> element.
        positions = gradient['positions']
        colors = gradient['colors']

        self._xml_start_tag('a:gsLst')

        for i in range(len(colors)):
            pos = int(positions[i] * 1000)
            attributes = [('pos', pos)]
            self._xml_start_tag('a:gs', attributes)

            # Write the a:srgbClr element.
            # TODO: Wait for a feature request to support transparency.
            color = get_rgb_color(colors[i])
            self._write_a_srgb_clr(color)

            self._xml_end_tag('a:gs')

        self._xml_end_tag('a:gsLst')

    def _write_a_lin(self, angle):
        # Write the <a:lin> element.

        angle = int(60000 * angle)

        attributes = [
            ('ang', angle),
            ('scaled', '0'),
        ]

        self._xml_empty_tag('a:lin', attributes)

    def _write_a_path(self, gradient_type):
        # Write the <a:path> element.

        attributes = [('path', gradient_type)]

        self._xml_start_tag('a:path', attributes)

        # Write the a:fillToRect element.
        self._write_a_fill_to_rect(gradient_type)

        self._xml_end_tag('a:path')

    def _write_a_fill_to_rect(self, gradient_type):
        # Write the <a:fillToRect> element.

        if gradient_type == 'shape':
            attributes = [
                ('l', '50000'),
                ('t', '50000'),
                ('r', '50000'),
                ('b', '50000'),
            ]
        else:
            attributes = [
                ('l', '100000'),
                ('t', '100000'),
            ]

        self._xml_empty_tag('a:fillToRect', attributes)

    def _write_a_tile_rect(self, gradient_type):
        # Write the <a:tileRect> element.

        if gradient_type == 'shape':
            attributes = []
        else:
            attributes = [
                ('r', '-100000'),
                ('b', '-100000'),
            ]

        self._xml_empty_tag('a:tileRect', attributes)

    def _write_a_patt_fill(self, pattern):
        # Write the <a:pattFill> element.

        attributes = [('prst', pattern['pattern'])]

        self._xml_start_tag('a:pattFill', attributes)

        # Write the a:fgClr element.
        self._write_a_fg_clr(pattern['fg_color'])

        # Write the a:bgClr element.
        self._write_a_bg_clr(pattern['bg_color'])

        self._xml_end_tag('a:pattFill')

    def _write_a_fg_clr(self, color):
        # Write the <a:fgClr> element.

        color = get_rgb_color(color)

        self._xml_start_tag('a:fgClr')

        # Write the a:srgbClr element.
        self._write_a_srgb_clr(color)

        self._xml_end_tag('a:fgClr')

    def _write_a_bg_clr(self, color):
        # Write the <a:bgClr> element.

        color = get_rgb_color(color)

        self._xml_start_tag('a:bgClr')

        # Write the a:srgbClr element.
        self._write_a_srgb_clr(color)

        self._xml_end_tag('a:bgClr')
