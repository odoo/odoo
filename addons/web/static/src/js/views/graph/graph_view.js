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
    init: function (viewInfo) {
        this._super.apply(this, arguments);

        var measure;
        var groupBys = [];
        viewInfo.fields = _.defaults({__count__: {string: _t("Count"), type: "integer"}}, viewInfo.fields);
        viewInfo.arch.children.forEach(function (field) {
            var name = field.attrs.name;
            if (field.attrs.interval) {
                name += ':' + field.attrs.interval;
            }
            if (field.attrs.type === 'measure') {
                measure = name;
            } else {
                groupBys.push(name);
            }
        });

        var measures = {__count__: {string: _t("Count"), type: "integer"}};
        _.each(viewInfo.fields, function (field, name) {
            if (name !== 'id' && field.store === true) {
                if (field.type === 'integer' || field.type === 'float' || field.type === 'monetary') {
                    measures[name] = field;
                }
            }
        });

        this.controllerParams.measures = measures;
        this.rendererParams.stacked = viewInfo.arch.attrs.stacked !== "False";

        this.loadParams.mode = viewInfo.arch.attrs.type || 'bar';
        this.loadParams.measure = measure || '__count__';
        this.loadParams.groupBys = groupBys || [];
        this.loadParams.fields = viewInfo.fields;
    },
});

return GraphView;

});
