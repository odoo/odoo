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

var _t = core._t;
var qweb = core.qweb;

var CHART_TYPES = ['pie', 'bar', 'line'];

// hide top legend when too many items for device size
var MAX_LEGEND_LENGTH = 25 * (1 + config.device.size_class);

return AbstractRenderer.extend({
    className: "o_graph_svg_container",
    /**
     * @override
     * @param {Widget} parent
     * @param {Object} state
     * @param {Object} params
     * @param {boolean} params.stacked
     */
    init: function (parent, state, params) {
        this._super.apply(this, arguments);
        this.stacked = params.stacked;
        this.$el.css({minWidth: '100px', minHeight: '100px'});
    },
    /**
     * @override
     */
    destroy: function () {
        nv.utils.offWindowResize(this.to_remove);
        this._super();
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Render the chart.
     *
     * Note that This method is synchronous, but the actual rendering is done
     * asynchronously (in a setTimeout).  The reason for that is that nvd3/d3
     * needs to be in the DOM to correctly render itself.  So, we trick Odoo by
     * returning immediately, then wait a tiny interval before actually
     * displaying the data.
     *
     * @returns {Deferred} The _super deferred is actually resolved immediately
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
        } else if (!this.state.data.length) {
            this.$el.empty();
            this.$el.append(qweb.render('GraphView.error', {
                title: _t("No data to display"),
                description: _t("No data available for this chart. " +
                    "Try to add some records, or make sure that " +
                    "there is no active filter in the search bar."),
            }));
        } else {
            var self = this;
            setTimeout(function () {
                self.$el.empty();
                var chart = self['_render' + _.str.capitalize(self.state.mode) + 'Chart']();
                if (chart && chart.tooltip.chartContainer) {
                    self.to_remove = chart.update;
                    nv.utils.onWindowResize(chart.update);
                    chart.tooltip.chartContainer(self.el);
                }
            }, 0);
        }
        return this._super.apply(this, arguments);
    },

    /**
     * Helper function to set up data properly for the multiBarChart model in
     * nvd3.
     *
     * @returns {nvd3 chart}
     */
    _renderBarChart: function () {
        // prepare data for bar chart
        var self = this;
        var data, values;
        var measure = this.state.fields[this.state.measure].string;

        // zero groupbys
        if (this.state.groupedBy.length === 0) {
            data = [{
                values: [{
                    x: measure,
                    y: this.state.data[0].value}],
                key: measure
            }];
        }
        // one groupby
        if (this.state.groupedBy.length === 1) {
            values = this.state.data.map(function (datapt) {
                return {x: datapt.labels, y: datapt.value};
            });
            data = [
                {
                    values: values,
                    key: measure,
                }
            ];
        }
        if (this.state.groupedBy.length > 1) {
            var xlabels = [],
                series = [],
                label, serie, value;
            values = {};
            for (var i = 0; i < this.state.data.length; i++) {
                label = this.state.data[i].labels[0];
                serie = this.state.data[i].labels[1];
                value = this.state.data[i].value;
                if ((!xlabels.length) || (xlabels[xlabels.length-1] !== label)) {
                    xlabels.push(label);
                }
                series.push(this.state.data[i].labels[1]);
                if (!(serie in values)) {values[serie] = {};}
                values[serie][label] = this.state.data[i].value;
            }
            series = _.uniq(series);
            data = [];
            var current_serie, j;
            for (i = 0; i < series.length; i++) {
                current_serie = {values: [], key: series[i]};
                for (j = 0; j < xlabels.length; j++) {
                    current_serie.values.push({
                        x: xlabels[j],
                        y: values[series[i]][xlabels[j]] || 0,
                    });
                }
                data.push(current_serie);
            }
        }
        var svg = d3.select(this.$el[0]).append('svg');
        svg.datum(data);

        svg.transition().duration(0);

        var chart = nv.models.multiBarChart();
        chart.options({
          margin: {left: 80, bottom: 100, top: 80, right: 0},
          delay: 100,
          transition: 10,
          showLegend: _.size(data) <= MAX_LEGEND_LENGTH,
          showXAxis: true,
          showYAxis: true,
          rightAlignYAxis: false,
          stacked: this.stacked,
          reduceXTicks: false,
          rotateLabels: -20,
          showControls: (this.state.groupedBy.length > 1)
        });
        chart.yAxis.tickFormat(function (d) {
            var measure_field = self.state.fields[self.measure];
            return field_utils.format.float(d, {
                digits: measure_field && measure_field.digits || [69, 2],
            });
        });

        chart(svg);
        return chart;
    },
    /**
     * Helper function to set up data properly for the pieChart model in
     * nvd3.
     *
     * @returns {nvd3 chart}
     */
    _renderPieChart: function () {
        var data = [];
        var all_negative = true;
        var some_negative = false;
        var all_zero = true;

        this.state.data.forEach(function (datapt) {
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
            this.$el.append(qweb.render('GraphView.error', {
                title: _t("Invalid data"),
                description: _t("Pie chart cannot display all zero numbers.. " +
                    "Try to change your domain to display positive results"),
            }));
            return;
        }
        if (this.state.groupedBy.length) {
            data = this.state.data.map(function (datapt) {
                return {x:datapt.labels.join("/"), y: datapt.value};
            });
        }
        var svg = d3.select(this.$el[0]).append('svg');
        svg.datum(data);

        svg.transition().duration(100);

        var legend_right = config.device.size_class > config.device.SIZES.XS;

        var chart = nv.models.pieChart().labelType('percent');
        chart.options({
          delay: 250,
          showLegend: legend_right || _.size(data) <= MAX_LEGEND_LENGTH,
          legendPosition: legend_right ? 'right' : 'top',
          transition: 100,
          color: d3.scale.category10().range(),
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
        if (this.state.data.length < 2) {
            this.$el.append(qweb.render('GraphView.error', {
                title: _t("Not enough data points"),
                description: "You need at least two data points to display a line chart."
            }));
            return;
        }
        var self = this;
        var data = [];
        var tickValues;
        var tickFormat;
        var measure = this.state.fields[this.state.measure].string;

        if (this.state.groupedBy.length === 1) {
            var values = this.state.data.map(function (datapt, index) {
                return {x: index, y: datapt.value};
            });
            data = [
                {
                    values: values,
                    key: measure,
                }
            ];
            tickValues = this.state.data.map(function (d, i) { return i;});
            tickFormat = function (d) {return self.state.data[d].labels;};
        }
        if (this.state.groupedBy.length > 1) {
            data = [];
            var data_dict = {};
            var tick = 0;
            var tickLabels = [];
            var serie, tickLabel;
            var identity = function (p) {return p;};
            tickValues = [];
            for (var i = 0; i < this.state.data.length; i++) {
                if (this.state.data[i].labels[0] !== tickLabel) {
                    tickLabel = this.state.data[i].labels[0];
                    tickValues.push(tick);
                    tickLabels.push(tickLabel);
                    tick++;
                }
                serie = this.state.data[i].labels[1];
                if (!data_dict[serie]) {
                    data_dict[serie] = {
                        values: [],
                        key: serie,
                    };
                }
                data_dict[serie].values.push({
                    x: tick, y: this.state.data[i].value,
                });
                data = _.map(data_dict, identity);
            }
            tickFormat = function (d) {return tickLabels[d];};
        }

        var svg = d3.select(this.$el[0]).append('svg');
        svg.datum(data);

        svg.transition().duration(0);

        var chart = nv.models.lineChart();
        chart.options({
          margin: {left: 80, bottom: 100, top: 80, right: 0},
          useInteractiveGuideline: true,
          showLegend: _.size(data) <= MAX_LEGEND_LENGTH,
          showXAxis: true,
          showYAxis: true,
        });
        chart.xAxis.tickValues(tickValues)
            .tickFormat(tickFormat);
        chart.yAxis.tickFormat(function (d) {
            return field_utils.format.float(d, {
                digits : self.state.fields[self.state.measure] && self.state.fields[self.state.measure].digits || [69, 2],
            });
        });

        chart(svg);
        return chart;
    },
});

});
