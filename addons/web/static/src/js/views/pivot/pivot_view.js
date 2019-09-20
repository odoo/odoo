odoo.define('web.PivotView', function (require) {
"use strict";

/**
 * The Pivot View is a view that represents data in a 'pivot grid' form. It
 * aggregates data on 2 dimensions and displays the result, allows the user to
 * 'zoom in' data.
 */

var AbstractView = require('web.AbstractView');
var config = require('web.config');
var core = require('web.core');
var PivotModel = require('web.PivotModel');
var PivotController = require('web.PivotController');
var PivotRenderer = require('web.PivotRenderer');

var _t = core._t;
var _lt = core._lt;

var controlPanelViewParameters = require('web.controlPanelViewParameters');
var GROUPABLE_TYPES = controlPanelViewParameters.GROUPABLE_TYPES;

var PivotView = AbstractView.extend({
    display_name: _lt('Pivot'),
    icon: 'fa-table',
    config: _.extend({}, AbstractView.prototype.config,{
        Model: PivotModel,
        Controller: PivotController,
        Renderer: PivotRenderer,
    }),
    viewType: 'pivot',
    searchMenuTypes: ['filter', 'groupBy', 'timeRange', 'favorite'],

    /**
     * @override
     * @param {Object} params
     */
    init: function (viewInfo, params) {
        var self = this;
        this._super.apply(this, arguments);

        var activeMeasures = [];
        var colGroupBys = [];
        var rowGroupBys = [];

        var measures = {};
        var groupableFields = {};
        var widgets = {};

        this.fields.__count = {string: _t("Count"), type: "integer"};
        _.each(this.fields, function (field, name) {
            if ((name !== 'id') && (field.store === true)) {
                if (_.contains(['integer', 'float', 'monetary'], field.type) ||
                    _.contains(params.additionalMeasures, name)) {
                        measures[name] = field;
                }
                if (_.contains(GROUPABLE_TYPES, field.type)) {
                    groupableFields[name] = field;
                }
            }
        });
        measures.__count = {string: _t("Count"), type: "integer"};

        this.arch.children.forEach(function (field) {
            var name = field.attrs.name;
            if (field.attrs.interval) {
                name += ':' + field.attrs.interval;
            }
            if (field.attrs.widget) {
                widgets[name] = field.attrs.widget;
            }
            if (field.attrs.invisible && py.eval(field.attrs.invisible)) {
                delete measures[name];
                return;
            }
            // add active measures to the measure list.  This is very rarely
            // necessary, but it can be useful if one is working with a
            // functional field non stored, but in a model with an overrided
            // read_group method.  In this case, the pivot view could work, and
            // the measure should be allowed.  However, be careful if you define
            // a measure in your pivot view: non stored functional fields will
            // probably not work (their aggregate will always be 0).
            if (field.attrs.type === 'measure' && !(name in measures)) {
                measures[name] = self.fields[name];
            }
            if (field.attrs.string) {
              measures[name].string = field.attrs.string;
            }
            if (field.attrs.type === 'measure' || 'operator' in field.attrs) {
                activeMeasures.push(name);
                measures[name] = self.fields[name];
            }
            if (field.attrs.type === 'col') {
                colGroupBys.push(name);
            }
            if (field.attrs.type === 'row') {
                rowGroupBys.push(name);
            }
        });
        if ((!activeMeasures.length) || this.arch.attrs.display_quantity) {
            activeMeasures = ['__count'].concat(activeMeasures);
        }

        this.loadParams.measures = activeMeasures;
        this.loadParams.colGroupBys = colGroupBys;
        this.loadParams.rowGroupBys = rowGroupBys;
        this.loadParams.fields = this.fields;
        this.loadParams.default_order = params.default_order || this.arch.attrs.default_order;
        if (config.device.isMobile) {
            this.loadParams.colGroupBys = [];
        }


        this.rendererParams.widgets = widgets;
        this.rendererParams.enableLinking = !this.arch.attrs.disable_linking;

        this.controllerParams.title = params.title || this.arch.attrs.string || _t("Untitled");
        this.controllerParams.measures = measures;
        this.controllerParams.groupableFields = groupableFields;
        // retrieve form and list view ids from the action to open those views
        // when a data cell of the pivot view is clicked
        this.controllerParams.views = [
            _findView(params.actionViews, 'list'),
            _findView(params.actionViews, 'form'),
        ];
        function _findView(views, viewType) {
            var view = _.find(views, function (view) {
                return view.type === viewType;
            });
            return [view ? view.viewID : false, viewType];
        }
    },
});

return PivotView;

});
