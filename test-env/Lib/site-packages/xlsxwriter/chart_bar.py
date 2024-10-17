###############################################################################
#
# ChartBar - A class for writing the Excel XLSX Bar charts.
#
# Copyright 2013-2018, John McNamara, jmcnamara@cpan.org
#

from . import chart
from warnings import warn


class ChartBar(chart.Chart):
    """
    A class for writing the Excel XLSX Bar charts.


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
        super(ChartBar, self).__init__()

        if options is None:
            options = {}

        self.subtype = options.get('subtype')

        if not self.subtype:
            self.subtype = 'clustered'

        self.cat_axis_position = 'l'
        self.val_axis_position = 'b'
        self.horiz_val_axis = 0
        self.horiz_cat_axis = 1
        self.show_crosses = 0

        # Override and reset the default axis values.
        self.x_axis['defaults']['major_gridlines'] = {'visible': 1}
        self.y_axis['defaults']['major_gridlines'] = {'visible': 0}

        if self.subtype == 'percent_stacked':
            self.x_axis['defaults']['num_format'] = '0%'

        # Set the available data label positions for this chart type.
        self.label_position_default = 'outside_end'
        self.label_positions = {
            'center': 'ctr',
            'inside_base': 'inBase',
            'inside_end': 'inEnd',
            'outside_end': 'outEnd'}

        self.set_x_axis({})
        self.set_y_axis({})

    def combine(self, chart=None):
        """
        Create a combination chart with a secondary chart.

        Note: Override parent method to add an extra check that is required
        for Bar charts to ensure that their combined chart is on a secondary
        axis.

        Args:
            chart: The secondary chart to combine with the primary chart.

        Returns:
            Nothing.

        """
        if chart is None:
            return

        if not chart.is_secondary:
            warn('Charts combined with Bar charts must be on a secondary axis')

        self.combined = chart

    ###########################################################################
    #
    # Private API.
    #
    ###########################################################################

    def _write_chart_type(self, args):
        # Override the virtual superclass method with a chart specific method.
        if args['primary_axes']:
            # Reverse X and Y axes for Bar charts.
            tmp = self.y_axis
            self.y_axis = self.x_axis
            self.x_axis = tmp

            if self.y2_axis['position'] == 'r':
                self.y2_axis['position'] = 't'

        # Write the c:barChart element.
        self._write_bar_chart(args)

    def _write_bar_chart(self, args):
        # Write the <c:barChart> element.

        if args['primary_axes']:
            series = self._get_primary_axes_series()
        else:
            series = self._get_secondary_axes_series()

        if not len(series):
            return

        subtype = self.subtype
        if subtype == 'percent_stacked':
            subtype = 'percentStacked'

        # Set a default overlap for stacked charts.
        if 'stacked' in self.subtype:
            if self.series_overlap_1 is None:
                self.series_overlap_1 = 100

        self._xml_start_tag('c:barChart')

        # Write the c:barDir element.
        self._write_bar_dir()

        # Write the c:grouping element.
        self._write_grouping(subtype)

        # Write the c:ser elements.
        for data in series:
            self._write_ser(data)

        # Write the c:gapWidth element.
        if args['primary_axes']:
            self._write_gap_width(self.series_gap_1)
        else:
            self._write_gap_width(self.series_gap_2)

        # Write the c:overlap element.
        if args['primary_axes']:
            self._write_overlap(self.series_overlap_1)
        else:
            self._write_overlap(self.series_overlap_2)

        # Write the c:axId elements
        self._write_axis_ids(args)

        self._xml_end_tag('c:barChart')

    ###########################################################################
    #
    # XML methods.
    #
    ###########################################################################

    def _write_bar_dir(self):
        # Write the <c:barDir> element.
        val = 'bar'

        attributes = [('val', val)]

        self._xml_empty_tag('c:barDir', attributes)

    def _write_err_dir(self, val):
        # Overridden from Chart class since it is not used in Bar charts.
        pass
