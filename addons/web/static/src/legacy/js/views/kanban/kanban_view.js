odoo.define('web.KanbanView', function (require) {
"use strict";

var BasicView = require('web.BasicView');
var core = require('web.core');
var KanbanController = require('web.KanbanController');
var kanbanExamplesRegistry = require('web.kanban_examples_registry');
var KanbanModel = require('web.KanbanModel');
var KanbanRenderer = require('web.KanbanRenderer');
var utils = require('web.utils');

var _lt = core._lt;

var KanbanView = BasicView.extend({
    accesskey: "k",
    display_name: _lt("Kanban"),
    icon: 'oi oi-view-kanban',
    mobile_friendly: true,
    config: _.extend({}, BasicView.prototype.config, {
        Model: KanbanModel,
        Controller: KanbanController,
        Renderer: KanbanRenderer,
    }),
    jsLibs: [],
    viewType: 'kanban',

    /**
     * @constructor
     */
    init: function (viewInfo, params) {
        this._super.apply(this, arguments);

        this.loadParams.limit = this.loadParams.limit || 40;
        this.loadParams.openGroupByDefault = true;
        this.loadParams.type = 'list';
        this.noDefaultGroupby = params.noDefaultGroupby;
        var progressBar;
        utils.traverse(this.arch, function (n) {
            var isProgressBar = (n.tag === 'progressbar');
            if (isProgressBar) {
                progressBar = _.clone(n.attrs);
                progressBar.colors = JSON.parse(progressBar.colors);
                progressBar.sum_field = progressBar.sum_field || false;
            }
            return !isProgressBar;
        });
        if (progressBar) {
            this.loadParams.progressBar = progressBar;
        }

        var activeActions = this.controllerParams.activeActions;
        var archAttrs = this.arch.attrs;
        activeActions = _.extend(activeActions, {
            group_create: this.arch.attrs.group_create ? !!JSON.parse(archAttrs.group_create) : true,
            group_edit: archAttrs.group_edit ? !!JSON.parse(archAttrs.group_edit) : true,
            group_delete: archAttrs.group_delete ? !!JSON.parse(archAttrs.group_delete) : true,
        });

        this.rendererParams.column_options = {
            editable: activeActions.group_edit,
            deletable: activeActions.group_delete,
            archivable: archAttrs.archivable ? !!JSON.parse(archAttrs.archivable) : true,
            group_creatable: activeActions.group_create,
            quickCreateView: archAttrs.quick_create_view || null,
            recordsDraggable: archAttrs.records_draggable ? !!JSON.parse(archAttrs.records_draggable) : true,
            hasProgressBar: !!progressBar,
        };
        this.rendererParams.record_options = {
            editable: activeActions.edit,
            deletable: activeActions.delete,
            read_only_mode: params.readOnlyMode,
            selectionMode: params.selectionMode,
        };
        if (('action' in archAttrs) && ('type' in archAttrs)) {
            this.rendererParams.record_options.openAction = {
                action: archAttrs.action,
                type: archAttrs.type
            };
        }
        this.rendererParams.quickCreateEnabled = this._isQuickCreateEnabled();
        this.rendererParams.readOnlyMode = params.readOnlyMode;
        var examples = archAttrs.examples;
        if (examples) {
            this.rendererParams.examples = kanbanExamplesRegistry.get(examples);
        }

        this.controllerParams.on_create = archAttrs.on_create;
        this.controllerParams.hasButtons = !params.selectionMode ? true : false;
        this.controllerParams.quickCreateEnabled = this.rendererParams.quickCreateEnabled;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} viewInfo
     * @returns {boolean} true iff the quick create feature is not explicitely
     *   disabled (with create="False" or quick_create="False" in the arch)
     */
    _isQuickCreateEnabled: function () {
        if (!this.controllerParams.activeActions.create) {
            return false;
        }
        if (this.arch.attrs.quick_create !== undefined) {
            return !!JSON.parse(this.arch.attrs.quick_create);
        }
        return true;
    },
    /**
     * Handles the <field> attribute allow_group_range_value,
     * used to configure, for a date(time) field, whether we want to use the front-end
     * logic to get the group value. (i.e. with drag&drop and quickCreate features)
     * if false, those features will be disabled for the current field.
     * Only handles the following types: date / datetime
     * if undefined the default is false
     *
     * @override
     */
    _processField(viewType, field, attrs) {
        if (['date', 'datetime'].includes(field.type) && 'allow_group_range_value' in attrs) {
            attrs.allowGroupRangeValue = !!JSON.parse(attrs.allow_group_range_value);
            delete attrs.allow_group_range_value;
        }
        return this._super(...arguments);
    },
    /**
     * Detect <img t-att-src="kanban_image(...)"/> nodes to automatically add the
     * 'write_date' field in the fieldsInfo to ensure that the images is
     * properly reloaded when necessary.
     *
     * @override
     */
    _processNode(node, fv) {
        const isKanbanImage = node.tag === 'img' &&
                              node.attrs['t-att-src'] &&
                              node.attrs['t-att-src'].includes('kanban_image');
        if (isKanbanImage && !fv.fieldsInfo.kanban.write_date) {
            fv.fieldsInfo.kanban.write_date = { type: 'datetime' };
        }
        return this._super(...arguments);
    },
    /**
     * @override
     * @private
     */
    _updateMVCParams: function () {
        this._super.apply(this, arguments);
        if (this.searchMenuTypes.includes('groupBy') && !this.noDefaultGroupby && this.arch.attrs.default_group_by) {
            this.loadParams.groupBy = [this.arch.attrs.default_group_by];
        }
    },
});

return KanbanView;

});
