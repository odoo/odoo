odoo.define('web.PieChart', function (require) {
"use strict";

/**
 * This widget render a Pie Chart. It is used in the dashboard view.
 */
var ajax = require('web.ajax');
var config = require('web.config');
var Widget = require('web.Widget');
var widgetRegistry = require('web.widget_registry');

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

        if (node.attrs.modifiers) {
            this.measure = node.attrs.modifiers.measure || '';
            this.measureField = this.record.fields[this.measure];
            this.groupBy = node.attrs.modifiers.groupby.split(':')[0] || '';
            this.interval = node.attrs.modifiers.groupby.split(':')[1];

            if (!_.contains(Object.keys(this.record.fields), this.groupBy)) {
                return;
            }

            this.groupByField = this.record.fields[this.groupBy];
            this.groupByType = this.groupByField.type;
            this.title = node.attrs.modifiers.title || this.measure || '';
            this.trueLabel = node.attrs.modifiers.trueLabel || 'True';
            this.falseLabel = node.attrs.modifiers.falseLabel || 'False';
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
            domain: [],
            groupBy: [this.groupBy + (this.interval ? ':' + this.interval : '')],
            fields: [this.measure],
            lazy: false,
        };

        // Handle case where measure attribute is missing.
        query.fields =  this.measure ? [this.measure] : [];

        return $.when(this._rpc(query), ajax.loadLibs(this)).then(
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
                                'label': label,
                                'value': value,
                            });
                        }
                    }
                }
            });
    },

    /**
     * This method ensure that Pie Chart is attached to DOM before being rendered.
     *
     * If we don't do that, Pie Chart can be rendered without being aware of the
     * size of its container, it is then rendered with a size of 0 0 and remains
     * invisible (even with a good lens).
     */
    on_attach_callback: function() {
        this._render();
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
        // setTimeout(0) before executing the callback given to addGraph.
        var self = this;
        if(!this.data || !_.isArray(this.data)) {
            return;
        }

        var $label = this._renderLabel(this.title);
        this.$el.empty();
        $label.appendTo(this.$el);
        $('<svg width=auto height=auto>').appendTo(this.$el);

        var legend_right = config.device.size_class > config.device.SIZES.XS;
        var legendPosition = legend_right ? 'right' : 'top';
        var color = d3.scale.category10().range();

        nv.addGraph(function () {
            self.chart = nv.models.pieChart()
                                  .x(function(d) { return d.label })
                                  .y(function(d) { return d.value })
                                  .legendPosition(legendPosition)
                                  .labelType('percent')
                                  .showLabels(true)
                                  .showLegend(true)
                                  .color(color);

            self.chart.legend.rightAlign(false);
            self.chart.legend.align(true);
            self.chart.legend.expanded(true);

            d3.select(self.$('svg')[0])
                .datum(self.data)
                .transition().duration(0)
                .call(self.chart);
            self.chart.update();
        });
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
});

widgetRegistry.add('pie_chart', PieChart);

return PieChart;

});
