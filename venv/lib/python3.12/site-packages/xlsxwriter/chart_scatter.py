###############################################################################
#
# ChartScatter - A class for writing the Excel XLSX Scatter charts.
#
# SPDX-License-Identifier: BSD-2-Clause
# Copyright 2013-2023, John McNamara, jmcnamara@cpan.org
#

from . import chart
from warnings import warn


class ChartScatter(chart.Chart):
    """
    A class for writing the Excel XLSX Scatter charts.


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
        super(ChartScatter, self).__init__()

        if options is None:
            options = {}

        self.subtype = options.get("subtype")

        if not self.subtype:
            self.subtype = "marker_only"

        self.cross_between = "midCat"
        self.horiz_val_axis = 0
        self.val_axis_position = "b"
        self.smooth_allowed = True
        self.requires_category = True

        # Set the available data label positions for this chart type.
        self.label_position_default = "right"
        self.label_positions = {
            "center": "ctr",
            "right": "r",
            "left": "l",
            "above": "t",
            "below": "b",
            # For backward compatibility.
            "top": "t",
            "bottom": "b",
        }

    def combine(self, chart=None):
        """
        Create a combination chart with a secondary chart.

        Note: Override parent method to add a warning.

        Args:
            chart: The secondary chart to combine with the primary chart.

        Returns:
            Nothing.

        """
        if chart is None:
            return

        warn(
            "Combined chart not currently supported with scatter chart "
            "as the primary chart"
        )

    ###########################################################################
    #
    # Private API.
    #
    ###########################################################################

    def _write_chart_type(self, args):
        # Override the virtual superclass method with a chart specific method.
        # Write the c:scatterChart element.
        self._write_scatter_chart(args)

    ###########################################################################
    #
    # XML methods.
    #
    ###########################################################################

    def _write_scatter_chart(self, args):
        # Write the <c:scatterChart> element.

        if args["primary_axes"]:
            series = self._get_primary_axes_series()
        else:
            series = self._get_secondary_axes_series()

        if not len(series):
            return

        style = "lineMarker"
        subtype = self.subtype

        # Set the user defined chart subtype.
        if subtype == "marker_only":
            style = "lineMarker"

        if subtype == "straight_with_markers":
            style = "lineMarker"

        if subtype == "straight":
            style = "lineMarker"
            self.default_marker = {"type": "none"}

        if subtype == "smooth_with_markers":
            style = "smoothMarker"

        if subtype == "smooth":
            style = "smoothMarker"
            self.default_marker = {"type": "none"}

        # Add default formatting to the series data.
        self._modify_series_formatting()

        self._xml_start_tag("c:scatterChart")

        # Write the c:scatterStyle element.
        self._write_scatter_style(style)

        # Write the series elements.
        for data in series:
            self._write_ser(data)

        # Write the c:axId elements
        self._write_axis_ids(args)

        self._xml_end_tag("c:scatterChart")

    def _write_ser(self, series):
        # Over-ridden to write c:xVal/c:yVal instead of c:cat/c:val elements.
        # Write the <c:ser> element.

        index = self.series_index
        self.series_index += 1

        self._xml_start_tag("c:ser")

        # Write the c:idx element.
        self._write_idx(index)

        # Write the c:order element.
        self._write_order(index)

        # Write the series name.
        self._write_series_name(series)

        # Write the c:spPr element.
        self._write_sp_pr(series)

        # Write the c:marker element.
        self._write_marker(series.get("marker"))

        # Write the c:dPt element.
        self._write_d_pt(series.get("points"))

        # Write the c:dLbls element.
        self._write_d_lbls(series.get("labels"))

        # Write the c:trendline element.
        self._write_trendline(series.get("trendline"))

        # Write the c:errBars element.
        self._write_error_bars(series.get("error_bars"))

        # Write the c:xVal element.
        self._write_x_val(series)

        # Write the c:yVal element.
        self._write_y_val(series)

        # Write the c:smooth element.
        if "smooth" in self.subtype and series["smooth"] is None:
            # Default is on for smooth scatter charts.
            self._write_c_smooth(True)
        else:
            self._write_c_smooth(series["smooth"])

        self._xml_end_tag("c:ser")

    def _write_plot_area(self):
        # Over-ridden to have 2 valAx elements for scatter charts instead
        # of catAx/valAx.
        #
        # Write the <c:plotArea> element.
        self._xml_start_tag("c:plotArea")

        # Write the c:layout element.
        self._write_layout(self.plotarea.get("layout"), "plot")

        # Write the subclass chart elements for primary and secondary axes.
        self._write_chart_type({"primary_axes": 1})
        self._write_chart_type({"primary_axes": 0})

        # Write c:catAx and c:valAx elements for series using primary axes.
        self._write_cat_val_axis(
            {
                "x_axis": self.x_axis,
                "y_axis": self.y_axis,
                "axis_ids": self.axis_ids,
                "position": "b",
            }
        )

        tmp = self.horiz_val_axis
        self.horiz_val_axis = 1

        self._write_val_axis(
            {
                "x_axis": self.x_axis,
                "y_axis": self.y_axis,
                "axis_ids": self.axis_ids,
                "position": "l",
            }
        )

        self.horiz_val_axis = tmp

        # Write c:valAx and c:catAx elements for series using secondary axes
        self._write_cat_val_axis(
            {
                "x_axis": self.x2_axis,
                "y_axis": self.y2_axis,
                "axis_ids": self.axis2_ids,
                "position": "b",
            }
        )
        self.horiz_val_axis = 1
        self._write_val_axis(
            {
                "x_axis": self.x2_axis,
                "y_axis": self.y2_axis,
                "axis_ids": self.axis2_ids,
                "position": "l",
            }
        )

        # Write the c:spPr element for the plotarea formatting.
        self._write_sp_pr(self.plotarea)

        self._xml_end_tag("c:plotArea")

    def _write_x_val(self, series):
        # Write the <c:xVal> element.
        formula = series.get("categories")
        data_id = series.get("cat_data_id")
        data = self.formula_data[data_id]

        self._xml_start_tag("c:xVal")

        # Check the type of cached data.
        data_type = self._get_data_type(data)

        if data_type == "str":
            # Write the c:numRef element.
            self._write_str_ref(formula, data, data_type)
        else:
            # Write the c:numRef element.
            self._write_num_ref(formula, data, data_type)

        self._xml_end_tag("c:xVal")

    def _write_y_val(self, series):
        # Write the <c:yVal> element.
        formula = series.get("values")
        data_id = series.get("val_data_id")
        data = self.formula_data[data_id]

        self._xml_start_tag("c:yVal")

        # Unlike Cat axes data should only be numeric.
        # Write the c:numRef element.
        self._write_num_ref(formula, data, "num")

        self._xml_end_tag("c:yVal")

    def _write_scatter_style(self, val):
        # Write the <c:scatterStyle> element.
        attributes = [("val", val)]

        self._xml_empty_tag("c:scatterStyle", attributes)

    def _modify_series_formatting(self):
        # Add default formatting to the series data unless it has already been
        # specified by the user.
        subtype = self.subtype

        # The default scatter style "markers only" requires a line type.
        if subtype == "marker_only":
            # Go through each series and define default values.
            for series in self.series:
                # Set a line type unless there is already a user defined type.
                if not series["line"]["defined"]:
                    series["line"] = {
                        "width": 2.25,
                        "none": 1,
                        "defined": 1,
                    }

    def _write_d_pt_point(self, index, point):
        # Write an individual <c:dPt> element. Override the parent method to
        # add markers.

        self._xml_start_tag("c:dPt")

        # Write the c:idx element.
        self._write_idx(index)

        self._xml_start_tag("c:marker")

        # Write the c:spPr element.
        self._write_sp_pr(point)

        self._xml_end_tag("c:marker")

        self._xml_end_tag("c:dPt")
