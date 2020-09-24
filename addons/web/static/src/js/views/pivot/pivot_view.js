odoo.define('web.PivotView', function (require) {
    "use strict";

    /**
     * The Pivot View is a view that represents data in a 'pivot grid' form. It
     * aggregates data on 2 dimensions and displays the result, allows the user to
     * 'zoom in' data.
     */

    const AbstractView = require('web.AbstractView');
    const config = require('web.config');
    const core = require('web.core');
    const PivotModel = require('web.PivotModel');
    const PivotController = require('web.PivotController');
    const PivotRenderer = require('web.PivotRenderer');
    const RendererWrapper = require('web.RendererWrapper');

    const _t = core._t;
    const _lt = core._lt;

    const searchUtils = require('web.searchUtils');
    const GROUPABLE_TYPES = searchUtils.GROUPABLE_TYPES;

    const PivotView = AbstractView.extend({
        display_name: _lt('Pivot'),
        icon: 'fa-table',
        config: Object.assign({}, AbstractView.prototype.config, {
            Model: PivotModel,
            Controller: PivotController,
            Renderer: PivotRenderer,
        }),
        viewType: 'pivot',
        searchMenuTypes: ['filter', 'groupBy', 'comparison', 'favorite'],

        /**
         * @override
         * @param {Object} params
         * @param {Array} params.additionalMeasures
         */
        init: function (viewInfo, params) {
            this._super.apply(this, arguments);

            const activeMeasures = []; // Store the defined active measures
            const colGroupBys = []; // Store the defined group_by used on cols
            const rowGroupBys = []; // Store the defined group_by used on rows
            const measures = {}; // All the available measures
            const groupableFields = {}; // The fields which can be used to group data
            const widgets = {}; // Wigdets defined in the arch
            const additionalMeasures = params.additionalMeasures || [];

            this.fields.__count = { string: _t("Count"), type: "integer" };

            //Compute the measures and the groupableFields
            Object.keys(this.fields).forEach(name => {
                const field = this.fields[name];
                if (name !== 'id' && field.store === true) {
                    if (['integer', 'float', 'monetary'].includes(field.type) || additionalMeasures.includes(name)) {
                        measures[name] = field;
                    }
                    if (GROUPABLE_TYPES.includes(field.type)) {
                        groupableFields[name] = field;
                    }
                }
            });
            measures.__count = { string: _t("Count"), type: "integer" };


            this.arch.children.forEach(field => {
                let name = field.attrs.name;
                // Remove invisible fields from the measures if not in additionalMeasures
                if (field.attrs.invisible && py.eval(field.attrs.invisible)) {
                    if (name in groupableFields) {
                        delete groupableFields[name];
                    }
                    if (!additionalMeasures.includes(name)) {
                        delete measures[name];
                        return;
                    }
                }
                if (field.attrs.interval) {
                    name += ':' + field.attrs.interval;
                }
                if (field.attrs.widget) {
                    widgets[name] = field.attrs.widget;
                }
                // add active measures to the measure list.  This is very rarely
                // necessary, but it can be useful if one is working with a
                // functional field non stored, but in a model with an overrided
                // read_group method.  In this case, the pivot view could work, and
                // the measure should be allowed.  However, be careful if you define
                // a measure in your pivot view: non stored functional fields will
                // probably not work (their aggregate will always be 0).
                if (field.attrs.type === 'measure' && !(name in measures)) {
                    measures[name] = this.fields[name];
                }
                if (field.attrs.string && name in measures) {
                    measures[name].string = field.attrs.string;
                }
                if (field.attrs.type === 'measure' || 'operator' in field.attrs) {
                    activeMeasures.push(name);
                    measures[name] = this.fields[name];
                }
                if (field.attrs.type === 'col') {
                    colGroupBys.push(name);
                }
                if (field.attrs.type === 'row') {
                    rowGroupBys.push(name);
                }
            });
            if ((!activeMeasures.length) || this.arch.attrs.display_quantity) {
                activeMeasures.splice(0, 0, '__count');
            }

            this.loadParams.measures = activeMeasures;
            this.loadParams.colGroupBys = config.device.isMobile ? [] : colGroupBys;
            this.loadParams.rowGroupBys = rowGroupBys;
            this.loadParams.fields = this.fields;
            this.loadParams.default_order = params.default_order || this.arch.attrs.default_order;
            this.loadParams.groupableFields = groupableFields;

            const disableLinking = !!(this.arch.attrs.disable_linking &&
                                        JSON.stringify(this.arch.attrs.disable_linking));

            this.rendererParams.widgets = widgets;
            this.rendererParams.disableLinking = disableLinking;

            this.controllerParams.disableLinking = disableLinking;
            this.controllerParams.title = params.title || this.arch.attrs.string || _t("Untitled");
            this.controllerParams.measures = measures;

            // retrieve form and list view ids from the action to open those views
            // when a data cell of the pivot view is clicked
            this.controllerParams.views = [
                _findView(params.actionViews, 'list'),
                _findView(params.actionViews, 'form'),
            ];

            function _findView(views, viewType) {
                const view = views.find(view => {
                    return view.type === viewType;
                });
                return [view ? view.viewID : false, viewType];
            }
        },

        /**
         *
         * @override
         */
        getRenderer(parent, state) {
            state = Object.assign(state || {}, this.rendererParams);
            return new RendererWrapper(parent, this.config.Renderer, state);
        },
    });

    return PivotView;

});
