odoo.define('web.PivotView', function (require) {
"use strict";

/**
 * The Pivot View is a view that represents data in a 'pivot grid' form. It
 * aggregates data on 2 dimensions and displays the result, allows the user to
 * 'zoom in' data.
 */

var AbstractView = require('web.AbstractView');
var core = require('web.core');
var PivotModel = require('web.PivotModel');
var PivotController = require('web.PivotController');
var PivotRenderer = require('web.PivotRenderer');

var _t = core._t;
var _lt = core._lt;

var GROUPABLE_TYPES =
    ['many2one', 'char', 'boolean', 'selection', 'date', 'datetime'];

var PivotView = AbstractView.extend({
    display_name: _lt('Pivot'),
    icon: 'fa-table',
    config: {
        Model: PivotModel,
        Controller: PivotController,
        Renderer: PivotRenderer,
    },
    /**
     * @override
     * @param {Object} params
     */
    init: function (viewInfo, params) {
        this._super.apply(this, arguments);

        var arch = viewInfo.arch;
        var fields = _.extend({
            __count: {string: _t("Count"), type: "integer"}
        }, viewInfo.fields);
        var activeMeasures = [];
        var colGroupBys = [];
        var rowGroupBys = [];

        var measures = {};
        var groupableFields = {};

        _.each(fields, function (field, name) {
            if ((name !== 'id') && (field.store === true)) {
                if (_.contains(['integer', 'float', 'monetary'], field.type)) {
                    measures[name] = field;
                }
                if (_.contains(GROUPABLE_TYPES, field.type)) {
                    groupableFields[name] = field;
                }
            }
        });
        measures.__count = {string: _t("Count"), type: "integer"};

        arch.children.forEach(function (field) {
            var name = field.attrs.name;
            if (field.attrs.interval) {
                name += ':' + field.attrs.interval;
            }

            // add active measures to the measure list.  This is very rarely
            // necessary, but it can be useful if one is working with a
            // functional field non stored, but in a model with an overrided
            // read_group method.  In this case, the pivot view could work, and
            // the measure should be allowed.  However, be careful if you define
            // a measure in your pivot view: non stored functional fields will
            // probably not work (their aggregate will always be 0).
            if (field.type === 'measure' && !(field.name in measures)) {
                measures[field.name] = field;
            }
            if (field.attrs.type === 'measure' || 'operator' in field.attrs) {
                activeMeasures.push(name);
            }
            if (field.attrs.type === 'col') {
                colGroupBys.push(name);
            }
            if (field.attrs.type === 'row') {
                rowGroupBys.push(name);
            }
        });
        if ((!activeMeasures.length) || arch.attrs.display_quantity) {
            activeMeasures.push('__count');
        }

        this.loadParams.measures = activeMeasures;
        this.loadParams.colGroupBys = colGroupBys;
        this.loadParams.rowGroupBys = rowGroupBys;
        this.loadParams.fields = fields;

        this.controllerParams.title = params.title || arch.attrs.string || _t("Untitled");
        this.controllerParams.enableLinking = !arch.attrs.disable_linking;
        this.controllerParams.measures = measures;
        this.controllerParams.groupableFields = groupableFields;
    },
});

return PivotView;

});


