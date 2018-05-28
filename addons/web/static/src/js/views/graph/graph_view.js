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
    cssLibs: [
        '/web/static/lib/nvd3/nv.d3.css'
    ],
    jsLibs: [
        '/web/static/lib/nvd3/d3.v3.js',
        '/web/static/lib/nvd3/nv.d3.js',
        '/web/static/src/js/libs/nvd3.js'
    ],
    config: {
        Model: GraphModel,
        Controller: Controller,
        Renderer: GraphRenderer,
    },
    viewType: 'graph',
    /**
     * @override
     */
    init: function (viewInfo, params) {
        this._super.apply(this, arguments);

        var self = this;
        var measure;
        var groupBys = [];
        var measures = {__count__: {string: _t("Count"), type: "integer"}};
        this.fields.__count__ = {string: _t("Count"), type: "integer"};

        this.arch.children.forEach(function (field) {
            var name = field.attrs.name;
            if (field.attrs.interval) {
                name += ':' + field.attrs.interval;
            }
            if (field.attrs.type === 'measure') {
                measure = name;
                measures[name] = self.fields[name];
            } else {
                groupBys.push(name);
            }
        });

        _.each(this.fields, function (field, name) {
            if (name !== 'id' && field.store === true) {
                if (_.contains(['integer', 'float', 'monetary'], field.type) ||
                    _.contains(params.additionalMeasures, name)) {
                        measures[name] = field;
                }
            }
        });

        this.controllerParams.measures = measures;
        this.rendererParams.stacked = this.arch.attrs.stacked !== "False";

        this.loadParams.mode = this.arch.attrs.type || 'bar';
        this.loadParams.measure = measure || '__count__';
        this.loadParams.groupBys = groupBys || [];
        this.loadParams.fields = this.fields;
    },
});

return GraphView;

});
