###############################################################################
#
# ChartDoughnut - A class for writing the Excel XLSX Doughnut charts.
#
# SPDX-License-Identifier: BSD-2-Clause
# Copyright 2013-2021, John McNamara, jmcnamara@cpan.org
#

from warnings import warn
from . import chart_pie


class ChartDoughnut(chart_pie.ChartPie):
    """
    A class for writing the Excel XLSX Doughnut charts.


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
        super(ChartDoughnut, self).__init__()

        self.vary_data_color = 1
        self.rotation = 0
        self.hole_size = 50

    def set_hole_size(self, size):
        """
        Set the Doughnut chart hole size.

        Args:
            size: 10 <= size <= 90.

        Returns:
            Nothing.

        """
        if size is None:
            return

        # Ensure the size is in Excel's range.
        if size < 10 or size > 90:
            warn("Chart hole size %d outside Excel range: 10 <= size <= 90"
                 % size)
            return

        self.hole_size = int(size)

    ###########################################################################
    #
    # Private API.
    #
    ###########################################################################

    def _write_chart_type(self, args):
        # Override the virtual superclass method with a chart specific method.
        # Write the c:doughnutChart element.
        self._write_doughnut_chart(args)

    ###########################################################################
    #
    # XML methods.
    #
    ###########################################################################

    def _write_doughnut_chart(self, args):
        # Write the <c:doughnutChart> element.  Over-ridden method to remove
        # axis_id code since Doughnut charts don't require val and cat axes.
        self._xml_start_tag('c:doughnutChart')

        # Write the c:varyColors element.
        self._write_vary_colors()

        # Write the series elements.
        for data in self.series:
            self._write_ser(data)

        # Write the c:firstSliceAng element.
        self._write_first_slice_ang()

        # Write the c:holeSize element.
        self._write_c_hole_size()

        self._xml_end_tag('c:doughnutChart')

    def _write_c_hole_size(self):
        # Write the <c:holeSize> element.
        attributes = [('val', self.hole_size)]

        self._xml_empty_tag('c:holeSize', attributes)
