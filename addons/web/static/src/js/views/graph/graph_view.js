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

var controlPanelViewParameters = require('web.controlPanelViewParameters');
var GROUPABLE_TYPES = controlPanelViewParameters.GROUPABLE_TYPES;

var GraphView = AbstractView.extend({
    display_name: _lt('Graph'),
    icon: 'fa-bar-chart',
    jsLibs: [
        '/web/static/lib/Chart/Chart.js',
    ],
    config: _.extend({}, AbstractView.prototype.config, {
        Model: GraphModel,
        Controller: Controller,
        Renderer: GraphRenderer,
    }),
    viewType: 'graph',
    searchMenuTypes: ['filter', 'groupBy', 'timeRange', 'favorite'],

    /**
     * @override
     */
    init: function (viewInfo, params) {
        this._super.apply(this, arguments);

        var self = this;
        var measure;
        var groupBys = [];
        var measures = {__count__: {string: _t("Count"), type: "integer"}};
        var groupableFields = {};
        this.fields.__count__ = {string: _t("Count"), type: "integer"};

        this.arch.children.forEach(function (field) {
            var fieldName = field.attrs.name;
            if (fieldName === "id") {
                return;
            }
            var interval = field.attrs.interval;
            if (interval) {
                fieldName = fieldName + ':' + interval;
            }
            if (field.attrs.type === 'measure') {
                measure = fieldName;
                measures[fieldName] = self.fields[fieldName];
            } else {
                groupBys.push(fieldName);
            }
        });

        _.each(this.fields, function (field, name) {
            if (name !== 'id' && field.store === true) {
                if (_.contains(['integer', 'float', 'monetary'], field.type) ||
                    _.contains(params.additionalMeasures, name)) {
                        measures[name] = field;
                }
                if (_.contains(GROUPABLE_TYPES, field.type)) {
                    groupableFields[name] = field;
                }
            }
        });

        this.controllerParams.measures = measures;
        this.controllerParams.groupableFields = groupableFields;
        this.rendererParams.fields = this.fields;
        this.rendererParams.title = this.arch.attrs.title; // TODO: use attrs.string instead

        this.loadParams.mode = this.arch.attrs.type || 'bar';
        this.loadParams.measure = measure || '__count__';
        this.loadParams.groupBys = groupBys;
        this.loadParams.fields = this.fields;
        this.loadParams.comparisonDomain = params.comparisonDomain;
        this.loadParams.stacked = this.arch.attrs.stacked !== "False";
    },
});

return GraphView;

});
