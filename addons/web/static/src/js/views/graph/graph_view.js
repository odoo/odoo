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

var searchUtils = require('web.searchUtils');
var GROUPABLE_TYPES = searchUtils.GROUPABLE_TYPES;

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
    searchMenuTypes: ['filter', 'groupBy', 'comparison', 'favorite'],

    /**
     * @override
     */
    init: function (viewInfo, params) {
        this._super.apply(this, arguments);

        const additionalMeasures = params.additionalMeasures || [];
        let measure;
        const measures = {};
        const measureStrings = {};
        let groupBys = [];
        const groupableFields = {};
        this.fields.__count__ = { string: _t("Count"), type: 'integer' };

        this.arch.children.forEach(field => {
            let fieldName = field.attrs.name;
            if (fieldName === "id") {
                return;
            }
            const interval = field.attrs.interval;
            if (interval) {
                fieldName = fieldName + ':' + interval;
            }
            if (field.attrs.type === 'measure') {
                const { string } = this.fields[fieldName];
                measure = fieldName;
                measures[fieldName] = {
                    description: string,
                    fieldName,
                    groupNumber: 0,
                    isActive: false,
                    itemType: 'measure',
                };
            } else {
                groupBys.push(fieldName);
            }
            if (field.attrs.string) {
                measureStrings[fieldName] = field.attrs.string;
            }
        });

        for (const name in this.fields) {
            const field = this.fields[name];
            if (name !== 'id' && field.store === true) {
                if (
                    ['integer', 'float', 'monetary'].includes(field.type) ||
                    additionalMeasures.includes(name)
                ) {
                    measures[name] = {
                        description: field.string,
                        fieldName: name,
                        groupNumber: 0,
                        isActive: false,
                        itemType: 'measure',
                    };
                }
                if (GROUPABLE_TYPES.includes(field.type)) {
                    groupableFields[name] = field;
                }
            }
        }
        for (const name in measureStrings) {
            if (measures[name]) {
                measures[name].description = measureStrings[name];
            }
        }

        // Remove invisible fields from the measures
        this.arch.children.forEach(field => {
            let fieldName = field.attrs.name;
            if (field.attrs.invisible && py.eval(field.attrs.invisible)) {
                groupBys = groupBys.filter(groupBy => groupBy !== fieldName);
                if (fieldName in groupableFields) {
                    delete groupableFields[fieldName];
                }
                if (!additionalMeasures.includes(fieldName)) {
                    delete measures[fieldName];
                }
            }
        });

        const sortedMeasures = Object.values(measures).sort((a, b) => {
                const descA = a.description.toLowerCase();
                const descB = b.description.toLowerCase();
                return descA > descB ? 1 : descA < descB ? -1 : 0;
            });
        const countMeasure = {
            description: _t("Count"),
            fieldName: '__count__',
            groupNumber: 1,
            isActive: false,
            itemType: 'measure',
        };
        this.controllerParams.withButtons = params.withButtons !== false;
        this.controllerParams.measures = [...sortedMeasures, countMeasure];
        this.controllerParams.groupableFields = groupableFields;
        this.controllerParams.title = params.title || this.arch.attrs.string || _t("Untitled");
        // retrieve form and list view ids from the action to open those views
        // when the graph is clicked
        function _findView(views, viewType) {
            const view = views.find(view => {
                return view.type === viewType;
            });
            return [view ? view.viewID : false, viewType];
        }
        this.controllerParams.views = [
            _findView(params.actionViews, 'list'),
            _findView(params.actionViews, 'form'),
        ];

        this.rendererParams.fields = this.fields;
        this.rendererParams.title = this.arch.attrs.title; // TODO: use attrs.string instead
        this.rendererParams.disableLinking = !!JSON.parse(this.arch.attrs.disable_linking || '0');

        this.loadParams.mode = this.arch.attrs.type || 'bar';
        this.loadParams.orderBy = this.arch.attrs.order;
        this.loadParams.measure = measure || '__count__';
        this.loadParams.groupBys = groupBys;
        this.loadParams.fields = this.fields;
        this.loadParams.comparisonDomain = params.comparisonDomain;
        this.loadParams.stacked = this.arch.attrs.stacked !== "False";
    },
});

return GraphView;

});
