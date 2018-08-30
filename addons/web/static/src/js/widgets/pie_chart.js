odoo.define('web.PieChart', function (require) {
"use strict";

/**
 * This widget render a Pie Chart. It is used in the dashboard view.
 */
var ajax = require('web.ajax');
var config = require('web.config');
var core = require('web.core');
var Domain = require('web.Domain');
var Widget = require('web.Widget');
var widgetRegistry = require('web.widget_registry');

var _t = core._t;

var GROUPABLE_TYPES = ['many2one', 'char', 'boolean', 'selection', 'date', 'datetime'];

var PieChart = Widget.extend({
    className: 'o_pie_chart',
    cssLibs: [
        '/web/static/lib/nvd3/nv.d3.css'
    ],
    jsLibs: [
        '/web/static/lib/nvd3/d3.v3.js',
        '/web/static/lib/nvd3/nv.d3.js',
        '/web/static/src/js/libs/nvd3.js'
    ],

    /**
     * override
     *
     * @param {Widget} parent
     * @param {Object} record
     * @param {Object} node
     */
    init: function (parent, record, node) {
        this._super(parent);
        this.record = record;
        this.model = record.model;
        this.domain = record.domain;
        if (node.attrs.modifiers) {
            this.domain = this.domain.concat(Domain.prototype.stringToArray(node.attrs.modifiers.domain || '[]'));
            this.measure = node.attrs.modifiers.measure || '';
            this.title = node.attrs.modifiers.title || this.measure || '';
            this.interval = node.attrs.modifiers.groupby.split(':')[1];
            this.groupBy = node.attrs.modifiers.groupby.split(':')[0] || '';
            if (!_.contains(Object.keys(this.record.fields), this.groupBy)) {
                return;
            }

            this.groupByField = this.record.fields[this.groupBy];
            this.groupByType = this.groupByField.type;
        }
    },
    /**
     * override
     */
    willStart: function () {
        var self = this;
        this.data = [];

        var query = {
            model: this.model,
            method: 'read_group',
            domain: this.domain,
            groupBy: [this.groupBy + (this.interval ? ':' + this.interval : '')],
            fields: [this.measure],
            lazy: false,
        };

        // Handle case where measure attribute is missing.
        query.fields =  this.measure ? [this.measure] : [];

        return $.when(self._rpc(query), ajax.loadLibs(self)).then(
            function (result) {
                if (result) {
                    if (_.contains(GROUPABLE_TYPES, self.groupByType)) {
                        for (var i = 0; i < result.length; i++) {
                            var value = result[i][self.measure];
                            var label = undefined;
                            var interval = self.interval ? ':' + self.interval : '';
                            var groupby = self.groupBy + interval;

                            switch (self.groupByType) {
                                case 'boolean':
                                    label = ['False', 'True'][i];
                                    break;
                                case 'many2one':
                                    label =  result[i][groupby][1];
                                    break;
                                default:
                                    label = result[i][groupby];
                            }

                            self.data.push({
                                label: label || _t('Undefined'),
                                value: value,
                            });
                        }
                    }
                }
            });
    },

    /**
     * override
     *
     */
    /*
    start: function () {
        this._renderGraph();
    },
    */
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------
    /**
     * This method ensure that Pie Chart is attached to DOM before being rendered.
     *
     * If we don't do that, Pie Chart can be rendered without being aware of the
     * size of its container, it is then rendered with a size of 0 0 and remains
     * invisible (even with a good lens).
     */
    on_attach_callback: function() {
        this._renderGraph();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    /**
     * @private
     */
    _render: function () {
        // Note: The rendering of this widget is aynchronous as NVD3 does a
        // setTimeout(0); before executing the callback given to addGraph.
        var self = this;
        if(!this.data || !_.isArray(this.data)) {
            return;
        }
        this.chart = null;
        this.$el.empty()
        var $label = this._renderLabel(this.title);
        $label.appendTo(this.$el);
        var $svgContainer = $('<svg >', {class: 'o_graph_svg_container'}); //.appendTo(this.$el);

        this.$el.append($svgContainer);
        var svg = d3.select($svgContainer[0]).append('svg');
        svg.datum(this.data);
        svg.transition().duration(1);
        var legend_right = config.device.size_class > config.device.SIZES.VSM;

        var chart = nv.models.pieChart().labelType('percent');
        chart.options({
            x: function(d) { return d.label },
            y: function(d) { return d.value },
            delay: 0,
            showLegend: true,
            legendPosition: legend_right ? 'right' : 'top',
            transition: 1,
            color: d3.scale.category10().range(),
        });
        chart.legend.rightAlign(false);
        chart.legend.align(true);
        chart.legend.expanded(true);
        chart(svg);

        return chart;
    },
    /**
     * @private
     * @param {any} value
     * @param {any} field
     * @returns {string}
     */
    _getNumberedValue: function (value, field) {
        var id = value[0];
        var name = value[1];
        this.numbering[field] = this.numbering[field] || {};
        this.numbering[field][name] = this.numbering[field][name] || {};
        var numbers = this.numbering[field][name];
        numbers[id] = numbers[id] || _.size(numbers) + 1;
        return name + (numbers[id] > 1 ? "  (" + numbers[id] + ")" : "");
    },
     /**
     * Renders a pie chart's label.
     *
     * @private
     * @param {String} title
     * @returns {jQueryElement}
     */
    _renderLabel: function (title) {
        var $result = $('<label>', {text: title});
        return $result;
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

        var chartResize = function (chart) {
            if (chart) {
                self.to_remove = chart.update;
                nv.utils.onWindowResize(chart.update);
            }
        }
        var chart = this._render();
        chartResize(chart);
    },
});

widgetRegistry.add('pie_chart', PieChart);

return PieChart;

});
