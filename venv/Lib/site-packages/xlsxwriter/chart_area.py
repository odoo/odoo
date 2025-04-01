###############################################################################
#
# ChartArea - A class for writing the Excel XLSX Area charts.
#
# Copyright 2013-2018, John McNamara, jmcnamara@cpan.org
#

from . import chart


class ChartArea(chart.Chart):
    """
    A class for writing the Excel XLSX Area charts.


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
        super(ChartArea, self).__init__()

        if options is None:
            options = {}

        self.subtype = options.get('subtype')

        if not self.subtype:
            self.subtype = 'standard'

        self.cross_between = 'midCat'
        self.show_crosses = 0

        # Override and reset the default axis values.
        if self.subtype == 'percent_stacked':
            self.y_axis['defaults']['num_format'] = '0%'

        # Set the available data label positions for this chart type.
        self.label_position_default = 'center'
        self.label_positions = {'center': 'ctr'}

        self.set_y_axis({})

    ###########################################################################
    #
    # Private API.
    #
    ###########################################################################

    def _write_chart_type(self, args):
        # Override the virtual superclass method with a chart specific method.
        # Write the c:areaChart element.
        self._write_area_chart(args)

    ###########################################################################
    #
    # XML methods.
    #
    ###########################################################################
    #
    def _write_area_chart(self, args):
        # Write the <c:areaChart> element.

        if args['primary_axes']:
            series = self._get_primary_axes_series()
        else:
            series = self._get_secondary_axes_series()

        if not len(series):
            return

        subtype = self.subtype

        if subtype == 'percent_stacked':
            subtype = 'percentStacked'

        self._xml_start_tag('c:areaChart')

        # Write the c:grouping element.
        self._write_grouping(subtype)

        # Write the series elements.
        for data in series:
            self._write_ser(data)

        # Write the c:dropLines element.
        self._write_drop_lines()

        # Write the c:axId elements
        self._write_axis_ids(args)

        self._xml_end_tag('c:areaChart')
