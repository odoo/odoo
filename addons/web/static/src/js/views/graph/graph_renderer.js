odoo.define('web.GraphRenderer', function (require) {
"use strict";

/**
 * The graph renderer turns the data from the graph model into a nice looking
 * svg chart.  This code uses the nvd3 library.
 *
 * Note that we use a custom build for the nvd3, with only the model we actually
 * use.
 */

var AbstractRenderer = require('web.AbstractRenderer');
var config = require('web.config');
var core = require('web.core');
var field_utils = require('web.field_utils');
var dataComparisonUtils = require('web.dataComparisonUtils');

var _t = core._t;
var qweb = core.qweb;
var DateClasses = dataComparisonUtils.DateClasses;

var CHART_TYPES = ['pie', 'bar', 'line'];

// hide top legend when too many items for device size
var MAX_LEGEND_LENGTH = 25 * (Math.max(1, config.device.size_class));
var SPLIT_THRESHOLD = config.device.isMobile ? Infinity : 20;

return AbstractRenderer.extend({
    className: "o_graph_renderer",
    /**
     * @override
     * @param {Widget} parent
     * @param {Object} state
     * @param {Object} params
     * @param {boolean} params.stacked
     */
    init: function (parent, state, params) {
        this._super.apply(this, arguments);
        this.datasets = [];
        this.isEmbedded = params.isEmbedded;
        this.stacked = this.state.compare ? false : params.stacked;
        this.title = params.title || '';
        this.fields = params.fields || {};
        this.formatOptions = {
            // allow to decide if utils.human_number should be used
            humanReadable: function (value) {
                return Math.abs(value) >= 1000;
            },
            // with the choices below, 1236 is represented by 1.24k
            minDigits: 1,
            decimals: 2,
            // avoid comma separators for thousands in numbers when human_number is used
            formatterCallback: function (str) {
                return str;
            }
        };
    },
    /**
     * @override
     */
    destroy: function () {
        nv.utils.offWindowResize(this.to_remove);
        this._super();
    },
    /**
     * The graph view uses the nv(d3) lib to render the graph. This lib requires
     * that the rendering is done directly into the DOM (so that it can correctly
     * compute positions). However, the views are always rendered in fragments,
     * and appended to the DOM once ready (to prevent them from flickering). We
     * here use the on_attach_callback hook, called when the widget is attached
     * to the DOM, to perform the rendering. This ensures that the rendering is
     * always done in the DOM.
     *
     * @override
     */
    on_attach_callback: function () {
        this._super.apply(this, arguments);
        this.isInDOM = true;
        this._render();
    },
    /**
     * @override
     */
    on_detach_callback: function () {
        this._super.apply(this, arguments);
        this.isInDOM = false;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @param {Object} state
     * @param {Object} params
     */
    updateState: function (state, params) {
        this.stacked = this.state.compare ? false : params.stacked;
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Used to format correctly the value in tooltips and y axis
     *
     * @private
     * @param {number} value
     * @returns {strin} The number formatted
     */
    _formatValue: function (value) {
        return field_utils.format.float(value, this.formatOption);
    },
    /**
     * Render the chart.
     *
     * Note that This method is synchronous, but the actual rendering is done
     * asynchronously.  The reason for that is that nvd3/d3 needs to be in the
     * DOM to correctly render itself.  So, we trick Odoo by returning
     * immediately, then we render the chart when the widget is in the DOM.
     *
     * @override
     * @private
     * @returns {Promise} The _super promise is actually resolved immediately
     */
    _render: function () {
        if (this.to_remove) {
            nv.utils.offWindowResize(this.to_remove);
        }
        if (!_.contains(CHART_TYPES, this.state.mode)) {
            this.$el.empty();
            this.trigger_up('warning', {
                title: _t('Invalid mode for chart'),
                message: _t('Cannot render chart with mode : ') + this.state.mode
            });
        } else if (!this.state.dataPoints.length && this.state.mode !== 'pie') {
            this.$el.empty();
            this.$el.append(qweb.render('GraphView.error', {
                title: _t("No data to display"),
                description: _t("Try to add some records, or make sure that " +
                    "there is no active filter in the search bar."),
            }));
        } else if (this.isInDOM) {
            // only render the graph if the widget is already in the DOM (this
            // happens typically after an update), otherwise, it will be
            // rendered when the widget will be attached to the DOM (see
            // 'on_attach_callback')
            this._renderGraph();
        }
        return this._super.apply(this, arguments);
    },

    _prepareDataSets: function (dataPoints) {
        var self = this;
        var measure = this.fields[this.state.measure].string;

        function getGroupLabel(dataPt) {
            // ([origin] + second to last groupBys) or measure
            var z = dataPt.labels.slice(1).join("/");
            if (self.state.compare) {
                z = self.state.origins[dataPt.originIndex] + (z ? ('/' + z) : '');
            }
            z = z || measure;
            return z;
        }

        function getXLabel(dataPt) {
            return dataPt.labels.slice(0, 1).join("/") || _t('Total');
        }

        var comparisonField = this.state.comparisonField;
        var groupBys = this.state.groupBy.map(function (gb) {
            return gb.split(":")[0];
        });

        // if dateIdentification is true, we will identify dates coming from
        // different origins if they have same rank in the corresponding date sets
        // (date sets are assumed pairwise disjoint, naturally ordered and not all empty)
        var dateIdentification = groupBys.indexOf(comparisonField) === 0;

        var dateSets;
        var dateClasses;
        if (dateIdentification) {
            dateSets = this.state.origins.map(function () {
                return [];
            });
            dataPoints.forEach(function (dataPt) {
                dateSets[dataPt.originIndex].push(dataPt.labels[0]);
            });
            dateSets = dateSets.map(function (dateSet) {
                return _.uniq(dateSet);
            });
            var interval = this.state.groupBy[0].split(":")[1] || 'month';
            dateClasses = new DateClasses(dateSets, interval);
        }

        // dataPoints --> points separated into different groups
        var groups = {};
        var groupInfo = {};
        var xRange = [];
        dataPoints.forEach(function (dataPt) {
            var groupLabel = getGroupLabel(dataPt);
            if (!(groupLabel in groups)) {
                groups[groupLabel] = {};
            }
            if (!(groupLabel in groupInfo)) {
                groupInfo[groupLabel] = {
                    // by construction, all data points in the same group
                    // have the same origin.
                    originIndex: dataPt.originIndex,
                    xLabels: {}
                };
            }
            var xLabel = getXLabel(dataPt);
            var xValue;
            if (dateIdentification) {
                xValue = dateClasses.representative(xLabel);
            } else {
                xValue = xLabel;
            }
            xRange.push(xValue);

            groups[groupLabel][xValue] = dataPt.value;
            groupInfo[groupLabel].xLabels[xValue] = xLabel;
        });

        xRange = _.uniq(xRange);

        // If not dateIdentification, each group is completed to have points over each x in xrange
        // If dateIdentification, we complete each group to have points over each x corresponding
        // to a date coming from a datapoint from the same origin.
        // Each group is transformed into a single datum for nvd3.
        var datasets = Object.keys(groups).map(function (groupLabel) {
            var range;
            var originIndex = groupInfo[groupLabel].originIndex;
            if (dateIdentification) {
                range = xRange.slice(0, dateSets[originIndex].length);
            } else {
                range = xRange;
            }
            var points = range.reduce(
                function (acc, xValue) {
                    var y = groups[groupLabel][xValue];
                    if (!y) {
                        if (dateIdentification) {
                            groupInfo[groupLabel].xLabels[xValue] = dateClasses.representative(xValue, originIndex);
                        } else {
                            groupInfo[groupLabel].xLabels[xValue] = xValue;
                        }
                    }
                    acc.push({
                        x: xValue,
                        y: y || 0,
                    });
                    return acc;
                },
                []
            );
            return {
                key: groupLabel,
                values: points
            };
        });

        return {
            datasets: datasets,
            ticksLabels: xRange,
            groupInfo: groupInfo,
        };
    },

    /**
     * Helper function to set up data properly for the multiBarChart model in
     * nvd3.
     *
     * @returns {nvd3 chart}
     */
    _renderBarChart: function () {
        var self = this;

        // prepare data for bar chart
        var dataPoints = this.state.dataPoints.filter(function (dataPt) {
            return dataPt.count > 0;
        });

        // put data in a format for nvd3
        var dataProcessed = this._prepareDataSets(dataPoints);
        var groupInfo = dataProcessed.groupInfo;
        this.datasets = dataProcessed.datasets;

        // style data
        if (this.state.groupBy.length === 1) {
            this.datasets.forEach(function (group) {
                if (groupInfo[group.key].originIndex === 1) {
                    group.color = '#ff7f0e';
                }
            });
        }

        // nvd3 specific
        var $svgContainer = $('<div/>', {class: 'o_graph_svg_container'});
        this.$el.append($svgContainer);
        var svg = d3.select($svgContainer[0]).append('svg');
        svg.datum(this.datasets);

        svg.transition().duration(0);

        var chart = nv.models.multiBarChart();
        chart.options({
          margin: {left: 80, bottom: 100, top: 80, right: 0},
          delay: 100,
          transition: 10,
          controlLabels: {
            'grouped': _t('Grouped'),
            'stacked': _t('Stacked'),
          },
          showLegend: _.size(this.datasets) <= MAX_LEGEND_LENGTH,
          showXAxis: true,
          showYAxis: true,
          rightAlignYAxis: false,
          stacked: this.stacked,
          reduceXTicks: false,
          rotateLabels: -20,
          showControls: (this.state.groupBy.length > 1)
        });

        chart.yAxis
            .tickFormat(function (d) {
                return self._formatValue(d);
            });


        chart.tooltip.contentGenerator(function (data) {
            var lines = data.series.map(function (serie) {
                var label = groupInfo[serie.key].xLabels[data.value];
                if (self.state.groupBy.length > 1 || self.state.compare) {
                    label = label + "/" + serie.key;
                }
                return {
                    color: serie.color,
                    label: label,
                    value: self._formatValue(serie.value),
                };
            });
            return qweb.render("web.Chart.Tooltip", {
                title: self.fields[self.state.measure].string,
                lines: lines.sort(function (line1, line2) {
                    return line2.value - line1.value;
                }),
            });
        });

        chart(svg);
        return chart;
    },
    /**
     * Helper function to set up data properly for the pieChart model in
     * nvd3.
     *
     * returns undefined in the case of an non-embedded pie chart with no data.
     * (all zero data included)
     *.
     * @returns {nvd3 chart|undefined}
     */
    _renderPieChart: function (originIndex) {
        var self = this;
        var all_negative = true;
        var some_negative = false;
        var all_zero = true;

        var dataPoints = this.state.dataPoints.filter(function (dataPt) {
            return dataPt.originIndex === originIndex && dataPt.count > 0;
        });
        dataPoints.forEach(function (datapt) {
            all_negative = all_negative && (datapt.value < 0);
            some_negative = some_negative || (datapt.value < 0);
            all_zero = all_zero && (datapt.value === 0);
        });
        if (some_negative && !all_negative) {
            this.$el.append(qweb.render('GraphView.error', {
                title: _t("Invalid data"),
                description: _t("Pie chart cannot mix positive and negative numbers. " +
                    "Try to change your domain to only display positive results"),
            }));
            return;
        }
        if (all_zero) {
            if (this.isEmbedded || this.state.compare) {
                // add fake data to display an empty pie chart
                this.datasets = [{
                    x : "No data" ,
                    y : 1
                }];
            } else {
                this.$el.append(qweb.render('GraphView.error', {
                    title: _t("Invalid data"),
                    description: _t("Pie chart cannot display all zero numbers.. " +
                        "Try to change your domain to display positive results"),
                }));
                return;
            }
        } else {
            this.datasets = dataPoints.map(function (datapt) {
                return {
                    x: datapt.labels.join("/") || _t('Total'),
                    y: datapt.value,
                };
            });
        }

        var $svgContainer = $('<div/>', {class: 'o_graph_svg_container'});
        this.$el.append($svgContainer);
        var svg = d3.select($svgContainer[0]).append('svg');
        svg.datum(this.datasets);

        svg.transition().duration(100);

        var color;
        var legend_right = config.device.size_class > config.device.SIZES.VSM;
        if (all_zero) {
            color = (['lightgrey']);
            svg.append("text")
                .attr("text-anchor", "middle")
                .attr("x", "50%")
                .attr("y", "50%")
                .text(_t("No data to display"));
        } else {
            color = d3.scale.category10().range();
        }

        var chart = nv.models.pieChart().labelType('percent');
        chart.options({
          delay: 250,
          showLegend: !all_zero && (legend_right || _.size(this.datasets) <= MAX_LEGEND_LENGTH),
          legendPosition: legend_right ? 'right' : 'top',
          transition: 100,
          color: color,
          showLabels: all_zero ? false: true,
        });

        chart.tooltip.contentGenerator(function (data) {
            return qweb.render("web.Chart.Tooltip", {
                title: self.fields[self.state.measure].string,
                lines : [{
                    color: data.color,
                    label: data.data.x,
                    value: self._formatValue(data.data.y),
                }],
            });
        });

        chart(svg);
        return chart;
    },
    /**
     * Helper function to set up data properly for the line model in
     * nvd3.
     *
     * @returns {nvd3 chart}
     */
    _renderLineChart: function () {
        var self = this;

        // remove some data points
        var dataPoints = this.state.dataPoints.filter(function (dataPt) {
            return dataPt.labels[0] !== _t("Undefined");
        });

        var dataProcessed = this._prepareDataSets(dataPoints);
        var ticksLabels = dataProcessed.ticksLabels;
        var groupInfo = dataProcessed.groupInfo;
        this.datasets = dataProcessed.datasets;

        // style data
        if (this.state.groupBy.length === 1) {
            this.datasets.forEach(function (group) {
                if (groupInfo[group.key].originIndex === 0) {
                    group.area = true;
                }
                if (groupInfo[group.key].originIndex === 1) {
                    group.color = '#ff7f0e';
                }
            });
        }
        this.datasets.forEach(function (group) {
            group.values = group.values.map(function (value) {
                return {
                    x: ticksLabels.indexOf(value.x),
                    y: value.y
                };
            });
        });

        var $svgContainer = $('<div/>', { class: 'o_graph_svg_container'});
        // Split the tooltip into columns for large data because some portion goes out off the screen.
        if (this.datasets.length >= SPLIT_THRESHOLD) {
            $svgContainer.addClass('o_tooltip_split_in_columns');
        }
        this.$el.append($svgContainer);
        var svg = d3.select($svgContainer[0]).append('svg');
        svg.datum(this.datasets);

        svg.transition().duration(0);

        var chart = nv.models.lineChart();
        chart.options({
          margin: {left: 0, bottom: 20, top: 0, right: 0},
          useInteractiveGuideline: true,
          showLegend: _.size(this.datasets) <= MAX_LEGEND_LENGTH,
          showXAxis: true,
          showYAxis: true,
          stacked: true,
        });
        chart.forceY([0]);
        chart.xAxis
            .tickFormat(function (d) {
                return ticksLabels[d];
            });
        chart.yAxis
            .showMaxMin(false)
            .tickFormat(function (d) {
                return self._formatValue(d);
            });
        chart.yAxis.tickPadding(5);
        chart.yAxis.orient("right");

        chart.interactiveLayer.tooltip.contentGenerator(function (data) {
            var lines = data.series.filter(function (serie) {
                return serie.data.x === data.value;
            }).map(function (serie) {
                var label = groupInfo[serie.key].xLabels[ticksLabels[data.value]];
                if (self.state.groupBy.length > 1 || self.state.compare) {
                    label = label + "/" + serie.key;
                }
                return {
                    color: serie.color,
                    label: label,
                    value: self._formatValue(serie.value),
                };
            });
            return qweb.render("web.Chart.Tooltip", {
                title: self.fields[self.state.measure].string,
                lines: lines.sort(function (line1, line2) {
                    return line2.value - line1.value;
                }),
            });
        });

        chart(svg);

        // Bigger line (stroke-width 1.5 is hardcoded in nv.d3)
        $svgContainer.find('.nvd3 .nv-groups g.nv-group').css('stroke-width', '2px');

        // Delete first and last label because there is no enough space because
        // of the tiny margins.
        if (ticksLabels.length > 3) {
            $svgContainer.find('svg .nv-x g.nv-axisMaxMin-x > text').hide();
        }

        return chart;
    },
    /**
     * Renders the graph according to its type. This function must be called
     * when the renderer is in the DOM (for nvd3 to render the graph correctly).
     *
     * @private
     */
    _renderGraph: function () {
        var self = this;

        this.$el.empty();

        function chartResize (chart){
            if (chart && chart.tooltip.chartContainer) {
                self.to_remove = chart.update;
                nv.utils.onWindowResize(chart.update);
                chart.tooltip.chartContainer(self.$('.o_graph_svg_container').last()[0]);
            }
        }
        var chart = this['_render' + _.str.capitalize(this.state.mode) + 'Chart'](0);

        if (chart) {
            chart.dispatch.on('renderEnd', function () {
                // FIXME: When 'orient' is right for Y axis, horizontal lines aren't displayed correctly
                $('.nv-y .tick > line').attr('x2', function (i, value) {
                    return Math.abs(value);
                });
            });
            chartResize(chart);
        }

        if (this.state.mode === 'pie' && this.state.compare) {
            // Render graph title
            var chartTitle = this.title + ' (' + this.state.timeRangeDescription + ')';
            this.$('.o_graph_svg_container').last().prepend($('<label/>', {
                text: chartTitle,
            }));

            // Instantiate comparison graph
            var comparisonChart = this['_render' + _.str.capitalize(this.state.mode) + 'Chart'](1);
            // Render comparison graph title
            var comparisonChartTitle = this.title + ' (' + this.state.comparisonTimeRangeDescription + ')';
            this.$('.o_graph_svg_container').last().prepend($('<label/>', {
                text: comparisonChartTitle,
            }));
            chartResize(comparisonChart);
            if (chart) {
                chart.update();
            }
        } else if (this.title) {
            this.$('.o_graph_svg_container').last().prepend($('<label/>', {
                text: this.title,
            }));
        }
    },
});

});
