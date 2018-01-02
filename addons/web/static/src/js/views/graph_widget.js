odoo.define('web.GraphWidget', function (require) {
"use strict";

var config = require('web.config');
var core = require('web.core');
var Model = require('web.DataModel');
var formats = require('web.formats');
var Widget = require('web.Widget');

var _t = core._t;
var QWeb = core.qweb;

// hide top legend when too many item for device size
var MAX_LEGEND_LENGTH = 25 * (1 + config.device.size_class);

return Widget.extend({
    init: function (parent, model, options) {
        this._super(parent);
        this.context = options.context;
        this.fields = options.fields;
        this.fields.__count__ = {string: _t("Count"), type: "integer"};
        this.model = new Model(model, {group_by_no_leaf: true});

        this.domain = options.domain || [];
        this.groupbys = options.groupbys || [];
        this.mode = options.mode || "bar";
        this.measure = options.measure || "__count__";
        this.stacked = options.stacked;
    },
    start: function () {
        return this.load_data().then(this.proxy('display_graph'));
    },
    update_data: function (domain, groupbys) {
        this.domain = domain;
        this.groupbys = groupbys;
        return this.load_data().then(this.proxy('display_graph'));
    },
    set_mode: function (mode) {
        this.mode = mode;
        this.display_graph();
    },
    set_measure: function (measure) {
        this.measure = measure;
        return this.load_data().then(this.proxy('display_graph'));        
    },
    load_data: function () {
        var fields = this.groupbys.slice(0);
        if (this.measure !== '__count__'.slice(0))
            fields = fields.concat(this.measure);
        return this.model
                    .query(fields)
                    .filter(this.domain)
                    .context(this.context)
                    .lazy(false)
                    .group_by(this.groupbys.slice(0,2))
                    .then(this.proxy('prepare_data'));
    },
    prepare_data: function () {
        var raw_data = arguments[0],
            is_count = this.measure === '__count__';
        var data_pt, j, values, value;

        this.data = [];
        for (var i = 0; i < raw_data.length; i++) {
            data_pt = raw_data[i].attributes;
            values = [];
            if (this.groupbys.length === 1) data_pt.value = [data_pt.value];
            for (j = 0; j < data_pt.value.length; j++) {
                var field = _.isArray(data_pt.grouped_on) ? data_pt.grouped_on[j] : data_pt.grouped_on;
                values[j] = this.sanitize_value(data_pt.value[j], field);
            }
            value = is_count ? data_pt.length : data_pt.aggregates[this.measure];
            this.data.push({
                labels: values,
                value: value
            });
        }
    },
    sanitize_value: function (value, field) {
        if (value === false) return _t("Undefined");
        if (value instanceof Array) return value[1];
        if (field && this.fields[field] && (this.fields[field].type === 'selection')) {
            var selected = _.where(this.fields[field].selection, {0: value})[0];
            return selected ? selected[1] : value;
        }
        return value;
    },
    display_graph: function () {
        if (this.to_remove) {
            nv.utils.offWindowResize(this.to_remove);
        }
        this.$el.empty();
        if (!this.data.length) {
            this.$el.append(QWeb.render('GraphView.error', {
                title: _t("No data to display"),
                description: _t("No data available for this chart. " +
                    "Try to add some records, or make sure that " +
                    "there is no active filter in the search bar."),
            }));
        } else {
            var chart = this['display_' + this.mode]();
            if (chart && chart.tooltip.chartContainer) {
                chart.tooltip.chartContainer(this.$el[0]);
            }
        }
    },
    display_bar: function () {
        // prepare data for bar chart
        var data, values,
            measure = this.fields[this.measure].string;

        // zero groupbys
        if (this.groupbys.length === 0) {
            data = [{
                values: [{
                    x: measure,
                    y: this.data[0].value}],
                key: measure
            }];
        } 
        // one groupby
        if (this.groupbys.length === 1) {
            values = this.data.map(function (datapt) {
                return {x: datapt.labels, y: datapt.value};
            });
            data = [
                {
                    values: values,
                    key: measure,
                }
            ];
        }
        if (this.groupbys.length > 1) {
            var xlabels = [],
                series = [],
                label, serie, value;
            values = {};
            for (var i = 0; i < this.data.length; i++) {
                label = this.data[i].labels[0];
                serie = this.data[i].labels[1];
                value = this.data[i].value;
                if ((!xlabels.length) || (xlabels[xlabels.length-1] !== label)) {
                    xlabels.push(label);
                }
                series.push(this.data[i].labels[1]);
                if (!(serie in values)) {values[serie] = {};}
                values[serie][label] = this.data[i].value;
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
        var maxVal = _.max(values, function(v) {return v.y})
        chart.options({
          margin: {left: 12 * String(maxVal && maxVal.y || 10000000).length, bottom: 60},
          delay: 250,
          transition: 10,
          showLegend: _.size(data) <= MAX_LEGEND_LENGTH,
          showXAxis: true,
          showYAxis: true,
          rightAlignYAxis: false,
          stacked: this.stacked,
          reduceXTicks: false,
          rotateLabels: -20,
          showControls: (this.groupbys.length > 1)
        });
        chart.yAxis.tickFormat(function(d) { return formats.format_value(d, { type : 'float' });});

        chart(svg);
        this.to_remove = chart.update;
        nv.utils.onWindowResize(chart.update);

        return chart;
    },
    display_pie: function () {
        var data = [],
            all_negative = true,
            some_negative = false,
            all_zero = true;
        
        this.data.forEach(function (datapt) {
            all_negative = all_negative && (datapt.value < 0);
            some_negative = some_negative || (datapt.value < 0);
            all_zero = all_zero && (datapt.value === 0);
        });
        if (some_negative && !all_negative) {
            return this.$el.append(QWeb.render('GraphView.error', {
                title: _t("Invalid data"),
                description: _t("Pie chart cannot mix positive and negative numbers. " +
                    "Try to change your domain to only display positive results"),
            }));
        }
        if (all_zero) {
            return this.$el.append(QWeb.render('GraphView.error', {
                title: _t("Invalid data"),
                description: _t("Pie chart cannot display all zero numbers.. " +
                    "Try to change your domain to display positive results"),
            }));
        }
        if (this.groupbys.length) {
            data = this.data.map(function (datapt) {
                return {x:datapt.labels.join("/"), y: datapt.value};
            });
        }
        var svg = d3.select(this.$el[0]).append('svg');
        svg.datum(data);

        svg.transition().duration(100);

        var legend_right = config.device.size_class > config.device.SIZES.XS;

        var chart = nv.models.pieChart();
        chart.options({
          delay: 250,
          showLegend: legend_right || _.size(data) <= MAX_LEGEND_LENGTH,
          legendPosition: legend_right ? 'right' : 'top',
          transition: 100,
          color: d3.scale.category10().range(),
        });

        chart(svg);
        this.to_remove = chart.update;
        nv.utils.onWindowResize(chart.update);

        return chart;
    },
    display_line: function () {
        if (this.data.length < 2) {
            this.$el.append(QWeb.render('GraphView.error', {
                title: _t("Not enough data points"),
                description: "You need at least two data points to display a line chart."
            }));
            return;
        }
        var self = this,
            data = [],
            tickValues,
            tickFormat,
            measure = this.fields[this.measure].string;
        if (this.groupbys.length === 1) {
            var values = this.data.map(function (datapt, index) {
                return {x: index, y: datapt.value};
            });
            data = [
                {
                    values: values,
                    key: measure,
                }
            ];
            tickValues = this.data.map(function (d, i) { return i;});
            tickFormat = function (d) {return self.data[d].labels;};
        }
        if (this.groupbys.length > 1) {
            data = [];
            var data_dict = {},
                tick = 0,
                tickLabels = [],
                serie, tickLabel,
                identity = function (p) {return p;};
            tickValues = [];
            for (var i = 0; i < this.data.length; i++) {
                if (this.data[i].labels[0] !== tickLabel) {
                    tickLabel = this.data[i].labels[0];
                    tickValues.push(tick);
                    tickLabels.push(tickLabel);
                    tick++;
                }
                serie = this.data[i].labels[1];
                if (!data_dict[serie]) {
                    data_dict[serie] = {
                        values: [],
                        key: serie,
                    };
                }
                data_dict[serie].values.push({
                    x: tick, y: this.data[i].value,
                });
                data = _.map(data_dict, identity);
            }
            tickFormat = function (d) {return tickLabels[d];};
        }

        var svg = d3.select(this.$el[0]).append('svg');
        svg.datum(data);

        svg.transition().duration(0);

        var chart = nv.models.lineChart();
        var maxVal = _.max(values, function(v) {return v.y})
        chart.options({
          margin: {left: 12 * String(maxVal && maxVal.y || 10000000).length, right: 50},
          useInteractiveGuideline: true,
          showLegend: _.size(data) <= MAX_LEGEND_LENGTH,
          showXAxis: true,
          showYAxis: true,
        });
        chart.xAxis.tickValues(tickValues)
            .tickFormat(tickFormat);
        chart.yAxis.tickFormat(function(d) { return openerp.web.format_value(d, { type : 'float' });});

        chart(svg);
        this.to_remove = chart.update;
        nv.utils.onWindowResize(chart.update);

        return chart;
    },
    destroy: function () {
        nv.utils.offWindowResize(this.to_remove);
        return this._super();
    }
});

});
