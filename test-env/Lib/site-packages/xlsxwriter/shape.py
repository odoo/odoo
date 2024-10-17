###############################################################################
#
# Shape - A class for to represent Excel XLSX shape objects.
#
# Copyright 2013-2018, John McNamara, jmcnamara@cpan.org
#
import copy
from warnings import warn


class Shape(object):
    """
    A class for to represent Excel XLSX shape objects.


    """

    ###########################################################################
    #
    # Public API.
    #
    ###########################################################################

    def __init__(self, shape_type, name, options):
        """
        Constructor.

        """
        super(Shape, self).__init__()
        self.name = name
        self.shape_type = shape_type
        self.connect = 0
        self.drawing = 0
        self.edit_as = ''
        self.id = 0
        self.text = ''
        self.stencil = 1
        self.element = -1
        self.start = None
        self.start_index = None
        self.end = None
        self.end_index = None
        self.adjustments = []
        self.start_side = ''
        self.end_side = ''
        self.flip_h = 0
        self.flip_v = 0
        self.rotation = 0
        self.textbox = False

        self.align = None
        self.fill = None
        self.font = None
        self.format = None
        self.line = None

        self._set_options(options)

    ###########################################################################
    #
    # Private API.
    #
    ###########################################################################

    def _set_options(self, options):

        self.align = self._get_align_properties(options.get('align'))
        self.fill = self._get_fill_properties(options.get('fill'))
        self.font = self._get_font_properties(options.get('font'))
        self.gradient = self._get_gradient_properties(options.get('gradient'))
        self.line = self._get_line_properties(options.get('line'))

        if options.get('border'):
            self.line = self._get_line_properties(options['border'])

        # Gradient fill overrides solid fill.
        if self.gradient:
            self.fill = None

    ###########################################################################
    #
    # Static methods for processing chart/shape style properties.
    #
    ###########################################################################

    @staticmethod
    def _get_line_properties(line):
        # Convert user line properties to the structure required internally.

        if not line:
            return {'defined': False}

        # Copy the user defined properties since they will be modified.
        line = copy.deepcopy(line)

        dash_types = {
            'solid': 'solid',
            'round_dot': 'sysDot',
            'square_dot': 'sysDash',
            'dash': 'dash',
            'dash_dot': 'dashDot',
            'long_dash': 'lgDash',
            'long_dash_dot': 'lgDashDot',
            'long_dash_dot_dot': 'lgDashDotDot',
            'dot': 'dot',
            'system_dash_dot': 'sysDashDot',
            'system_dash_dot_dot': 'sysDashDotDot',
        }

        # Check the dash type.
        dash_type = line.get('dash_type')

        if dash_type is not None:
            if dash_type in dash_types:
                line['dash_type'] = dash_types[dash_type]
            else:
                warn("Unknown dash type '%s'" % dash_type)
                return

        line['defined'] = True

        return line

    @staticmethod
    def _get_fill_properties(fill):
        # Convert user fill properties to the structure required internally.

        if not fill:
            return {'defined': False}

        # Copy the user defined properties since they will be modified.
        fill = copy.deepcopy(fill)

        fill['defined'] = True

        return fill

    @staticmethod
    def _get_pattern_properties(pattern):
        # Convert user defined pattern to the structure required internally.

        if not pattern:
            return

        # Copy the user defined properties since they will be modified.
        pattern = copy.deepcopy(pattern)

        if not pattern.get('pattern'):
            warn("Pattern must include 'pattern'")
            return

        if not pattern.get('fg_color'):
            warn("Pattern must include 'fg_color'")
            return

        types = {
            'percent_5': 'pct5',
            'percent_10': 'pct10',
            'percent_20': 'pct20',
            'percent_25': 'pct25',
            'percent_30': 'pct30',
            'percent_40': 'pct40',
            'percent_50': 'pct50',
            'percent_60': 'pct60',
            'percent_70': 'pct70',
            'percent_75': 'pct75',
            'percent_80': 'pct80',
            'percent_90': 'pct90',
            'light_downward_diagonal': 'ltDnDiag',
            'light_upward_diagonal': 'ltUpDiag',
            'dark_downward_diagonal': 'dkDnDiag',
            'dark_upward_diagonal': 'dkUpDiag',
            'wide_downward_diagonal': 'wdDnDiag',
            'wide_upward_diagonal': 'wdUpDiag',
            'light_vertical': 'ltVert',
            'light_horizontal': 'ltHorz',
            'narrow_vertical': 'narVert',
            'narrow_horizontal': 'narHorz',
            'dark_vertical': 'dkVert',
            'dark_horizontal': 'dkHorz',
            'dashed_downward_diagonal': 'dashDnDiag',
            'dashed_upward_diagonal': 'dashUpDiag',
            'dashed_horizontal': 'dashHorz',
            'dashed_vertical': 'dashVert',
            'small_confetti': 'smConfetti',
            'large_confetti': 'lgConfetti',
            'zigzag': 'zigZag',
            'wave': 'wave',
            'diagonal_brick': 'diagBrick',
            'horizontal_brick': 'horzBrick',
            'weave': 'weave',
            'plaid': 'plaid',
            'divot': 'divot',
            'dotted_grid': 'dotGrid',
            'dotted_diamond': 'dotDmnd',
            'shingle': 'shingle',
            'trellis': 'trellis',
            'sphere': 'sphere',
            'small_grid': 'smGrid',
            'large_grid': 'lgGrid',
            'small_check': 'smCheck',
            'large_check': 'lgCheck',
            'outlined_diamond': 'openDmnd',
            'solid_diamond': 'solidDmnd',
        }

        # Check for valid types.
        if not pattern['pattern'] in types:
            warn("unknown pattern type '%s'" % pattern['pattern'])
            return
        else:
            pattern['pattern'] = types[pattern['pattern']]

        # Specify a default background color.
        pattern['bg_color'] = pattern.get('bg_color', '#FFFFFF')

        return pattern

    @staticmethod
    def _get_gradient_properties(gradient):
        # Convert user defined gradient to the structure required internally.

        if not gradient:
            return

        # Copy the user defined properties since they will be modified.
        gradient = copy.deepcopy(gradient)

        types = {
            'linear': 'linear',
            'radial': 'circle',
            'rectangular': 'rect',
            'path': 'shape'
        }

        # Check the colors array exists and is valid.
        if 'colors' not in gradient or type(gradient['colors']) != list:
            warn("Gradient must include colors list")
            return

        # Check the colors array has the required number of entries.
        if not 2 <= len(gradient['colors']) <= 10:
            warn("Gradient colors list must at least 2 values "
                 "and not more than 10")
            return

        if 'positions' in gradient:
            # Check the positions array has the right number of entries.
            if len(gradient['positions']) != len(gradient['colors']):
                warn("Gradient positions not equal to number of colors")
                return

            # Check the positions are in the correct range.
            for pos in gradient['positions']:
                if not 0 <= pos <= 100:
                    warn("Gradient position must be in the range "
                         "0 <= position <= 100")
                    return
        else:
            # Use the default gradient positions.
            if len(gradient['colors']) == 2:
                gradient['positions'] = [0, 100]

            elif len(gradient['colors']) == 3:
                gradient['positions'] = [0, 50, 100]

            elif len(gradient['colors']) == 4:
                gradient['positions'] = [0, 33, 66, 100]

            else:
                warn("Must specify gradient positions")
                return

        angle = gradient.get('angle')
        if angle:
            if not 0 <= angle < 360:
                warn("Gradient angle must be in the range "
                     "0 <= angle < 360")
                return
        else:
            gradient['angle'] = 90

        # Check for valid types.
        gradient_type = gradient.get('type')

        if gradient_type is not None:

            if gradient_type in types:
                gradient['type'] = types[gradient_type]
            else:
                warn("Unknown gradient type '%s" % gradient_type)
                return
        else:
            gradient['type'] = 'linear'

        return gradient

    @staticmethod
    def _get_font_properties(options):
        # Convert user defined font values into private dict values.
        if options is None:
            options = {}

        font = {
            'name': options.get('name'),
            'color': options.get('color'),
            'size': options.get('size', 11),
            'bold': options.get('bold'),
            'italic': options.get('italic'),
            'underline': options.get('underline'),
            'pitch_family': options.get('pitch_family'),
            'charset': options.get('charset'),
            'baseline': options.get('baseline', -1),
            'rotation': options.get('rotation'),
            'lang': options.get('lang', 'en-US'),
        }

        # Convert font size units.
        if font['size']:
            font['size'] = int(font['size'] * 100)

        # Convert rotation into 60,000ths of a degree.
        if font['rotation']:
            font['rotation'] = 60000 * int(font['rotation'])

        return font

    @staticmethod
    def _get_font_style_attributes(font):
        # _get_font_style_attributes.
        attributes = []

        if not font:
            return attributes

        if font.get('size'):
            attributes.append(('sz', font['size']))

        if font.get('bold') is not None:
            attributes.append(('b', 0 + font['bold']))

        if font.get('italic') is not None:
            attributes.append(('i', 0 + font['italic']))

        if font.get('underline') is not None:
            attributes.append(('u', 'sng'))

        if font.get('baseline') != -1:
            attributes.append(('baseline', font['baseline']))

        return attributes

    @staticmethod
    def _get_font_latin_attributes(font):
        # _get_font_latin_attributes.
        attributes = []

        if not font:
            return attributes

        if font['name'] is not None:
            attributes.append(('typeface', font['name']))

        if font['pitch_family'] is not None:
            attributes.append(('pitchFamily', font['pitch_family']))

        if font['charset'] is not None:
            attributes.append(('charset', font['charset']))

        return attributes

    @staticmethod
    def _get_align_properties(align):
        # Convert user defined align to the structure required internally.
        if not align:
            return {'defined': False}

        # Copy the user defined properties since they will be modified.
        align = copy.deepcopy(align)

        if 'vertical' in align:
            align_type = align['vertical']

            align_types = {
                'top': 'top',
                'middle': 'middle',
                'bottom': 'bottom',
            }

            if align_type in align_types:
                align['vertical'] = align_types[align_type]
            else:
                warn("Unknown alignment type '%s'" % align_type)
                return {'defined': False}

        if 'horizontal' in align:
            align_type = align['horizontal']

            align_types = {
                'left': 'left',
                'center': 'center',
                'right': 'right',
            }

            if align_type in align_types:
                align['horizontal'] = align_types[align_type]
            else:
                warn("Unknown alignment type '%s'" % align_type)
                return {'defined': False}

        align['defined'] = True

        return align
