###############################################################################
#
# ChartRadar - A class for writing the Excel XLSX Radar charts.
#
# SPDX-License-Identifier: BSD-2-Clause
# Copyright 2013-2021, John McNamara, jmcnamara@cpan.org
#

from . import chart


class ChartRadar(chart.Chart):
    """
    A class for writing the Excel XLSX Radar charts.


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
        super(ChartRadar, self).__init__()

        if options is None:
            options = {}

        self.subtype = options.get('subtype')

        if not self.subtype:
            self.subtype = 'marker'
            self.default_marker = {'type': 'none'}

        # Override and reset the default axis values.
        self.x_axis['defaults']['major_gridlines'] = {'visible': 1}
        self.set_x_axis({})

        # Set the available data label positions for this chart type.
        self.label_position_default = 'center'
        self.label_positions = {'center': 'ctr'}

        # Hardcode major_tick_mark for now until there is an accessor.
        self.y_axis['major_tick_mark'] = 'cross'

    ###########################################################################
    #
    # Private API.
    #
    ###########################################################################

    def _write_chart_type(self, args):
        # Write the c:radarChart element.
        self._write_radar_chart(args)

    ###########################################################################
    #
    # XML methods.
    #
    ###########################################################################

    def _write_radar_chart(self, args):
        # Write the <c:radarChart> element.

        if args['primary_axes']:
            series = self._get_primary_axes_series()
        else:
            series = self._get_secondary_axes_series()

        if not len(series):
            return

        self._xml_start_tag('c:radarChart')

        # Write the c:radarStyle element.
        self._write_radar_style()

        # Write the series elements.
        for data in series:
            self._write_ser(data)

        # Write the c:axId elements
        self._write_axis_ids(args)

        self._xml_end_tag('c:radarChart')

    def _write_radar_style(self):
        # Write the <c:radarStyle> element.
        val = 'marker'

        if self.subtype == 'filled':
            val = 'filled'

        attributes = [('val', val)]

        self._xml_empty_tag('c:radarStyle', attributes)
