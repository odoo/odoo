###############################################################################
#
# ChartLine - A class for writing the Excel XLSX Line charts.
#
# Copyright 2013-2018, John McNamara, jmcnamara@cpan.org
#

from . import chart


class ChartLine(chart.Chart):
    """
    A class for writing the Excel XLSX Line charts.


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
        super(ChartLine, self).__init__()

        if options is None:
            options = {}

        self.default_marker = {'type': 'none'}
        self.smooth_allowed = True

        # Set the available data label positions for this chart type.
        self.label_position_default = 'right'
        self.label_positions = {
            'center': 'ctr',
            'right': 'r',
            'left': 'l',
            'above': 't',
            'below': 'b',
            # For backward compatibility.
            'top': 't',
            'bottom': 'b'}

    ###########################################################################
    #
    # Private API.
    #
    ###########################################################################

    def _write_chart_type(self, args):
        # Override the virtual superclass method with a chart specific method.
        # Write the c:lineChart element.
        self._write_line_chart(args)

    ###########################################################################
    #
    # XML methods.
    #
    ###########################################################################

    def _write_line_chart(self, args):
        # Write the <c:lineChart> element.

        if args['primary_axes']:
            series = self._get_primary_axes_series()
        else:
            series = self._get_secondary_axes_series()

        if not len(series):
            return

        self._xml_start_tag('c:lineChart')

        # Write the c:grouping element.
        self._write_grouping('standard')

        # Write the series elements.
        for data in series:
            self._write_ser(data)

        # Write the c:dropLines element.
        self._write_drop_lines()

        # Write the c:hiLowLines element.
        self._write_hi_low_lines()

        # Write the c:upDownBars element.
        self._write_up_down_bars()

        # Write the c:marker element.
        self._write_marker_value()

        # Write the c:axId elements
        self._write_axis_ids(args)

        self._xml_end_tag('c:lineChart')

    def _write_d_pt_point(self, index, point):
        # Write an individual <c:dPt> element. Override the parent method to
        # add markers.

        self._xml_start_tag('c:dPt')

        # Write the c:idx element.
        self._write_idx(index)

        self._xml_start_tag('c:marker')

        # Write the c:spPr element.
        self._write_sp_pr(point)

        self._xml_end_tag('c:marker')

        self._xml_end_tag('c:dPt')

    def _write_marker_value(self):
        # Write the <c:marker> element without a sub-element.
        attributes = [('val', 1)]

        self._xml_empty_tag('c:marker', attributes)
