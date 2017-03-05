odoo.define('web.GraphView', function (require) {
"use strict";

/**
 * The Graph View is responsible to display a graphical (meaning: chart)
 * representation of the current dataset.  As of now, it is currently able to
 * display data in three types of chart: bar chart, line chart and pie chart.
 */

var AbstractView = require('web.AbstractView');
var core = require('web.core');
var GraphModel = require('web.GraphModel');
var Controller = require('web.GraphController');
var GraphRenderer = require('web.GraphRenderer');

var _t = core._t;
var _lt = core._lt;

var GraphView = AbstractView.extend({
    display_name: _lt('Graph'),
    icon: 'fa-bar-chart',
    config: {
        Model: GraphModel,
        Controller: Controller,
        Renderer: GraphRenderer,
    },
    /**
     * @override
     */
    init: function (arch, fields) {
        this._super.apply(this, arguments);

        var initialMeasure = '__count__';
        var initialGroupBys = [];
        fields.__count__ = {string: _t("Count"), type: "integer"};
        arch.children.forEach(function (field) {
            var name = field.attrs.name;
            if (field.attrs.interval) {
                name += ':' + field.attrs.interval;
            }
            if (field.attrs.type === 'measure') {
                initialMeasure = name;
            } else {
                initialGroupBys.push(name);
            }
        });

        var measures = {__count__: {string: _t("Count"), type: "integer"}};
        _.each(fields, function (field, name) {
            if (name !== 'id' && field.store === true) {
                if (field.type === 'integer' || field.type === 'float' || field.type === 'monetary') {
                    measures[name] = field;
                }
            }
        });

        this.controllerParams.measures = measures;
        this.rendererParams.stacked = arch.attrs.stacked !== "False";

        this.loadParams.initialMode = arch.attrs.type || 'bar';
        this.loadParams.initialMeasure = initialMeasure;
        this.loadParams.initialGroupBys = initialGroupBys;
        this.loadParams.fields = fields;
    },
});

return GraphView;

});
