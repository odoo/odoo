odoo.define('web.KanbanView', function (require) {
"use strict";

var BasicView = require('web.BasicView');
var core = require('web.core');
var config = require('web.config');
var KanbanModel = require('web.KanbanModel');
var KanbanRenderer = require('web.KanbanRenderer');
var KanbanController = require('web.KanbanController');
var kanbanExamplesRegistry = require('web.kanban_examples_registry');
var utils = require('web.utils');

var _lt = core._lt;

var KanbanView = BasicView.extend({
    accesskey: "k",
    display_name: _lt("Kanban"),
    icon: 'fa-th-large',
    mobile_friendly: true,
    config: {
        Model: KanbanModel,
        Controller: KanbanController,
        Renderer: KanbanRenderer,
    },
    jsLibs: [],
    viewType: 'kanban',

    /**
     * @constructor
     */
    init: function (viewInfo, params) {
        this._super.apply(this, arguments);

        this.loadParams.limit = this.loadParams.limit || 40;
        // in mobile, columns are lazy-loaded, so set 'openGroupByDefault' to
        // false so that they will won't be loaded by the initial load
        this.loadParams.openGroupByDefault = config.device.isMobile ? false : true;
        this.loadParams.type = 'list';
        this.loadParams.groupBy = this.arch.attrs.default_group_by ? [this.arch.attrs.default_group_by] : (params.groupBy || []);
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
        activeActions = _.extend(activeActions, {
            group_create: this.arch.attrs.group_create ? JSON.parse(this.arch.attrs.group_create) : true,
            group_edit: this.arch.attrs.group_edit ? JSON.parse(this.arch.attrs.group_edit) : true,
            group_delete: this.arch.attrs.group_delete ? JSON.parse(this.arch.attrs.group_delete) : true,
        });

        this.rendererParams.column_options = {
            editable: activeActions.group_edit,
            deletable: activeActions.group_delete,
            group_creatable: activeActions.group_create && !config.device.isMobile,
            quick_create: params.isQuickCreateEnabled || this._isQuickCreateEnabled(),
            quickCreateView: this.arch.attrs.quick_create_view || null,
            hasProgressBar: !!progressBar,
        };
        this.rendererParams.record_options = {
            editable: activeActions.edit,
            deletable: activeActions.delete,
            read_only_mode: params.readOnlyMode,
        };
        var examples = this.arch.attrs.examples;
        if (examples) {
            this.rendererParams.examples = kanbanExamplesRegistry.get(examples);
        }

        this.controllerParams.on_create = this.arch.attrs.on_create;
        this.controllerParams.readOnlyMode = false;
        this.controllerParams.hasButtons = true;

        if (config.device.isMobile) {
            this.jsLibs.push('/web/static/lib/jquery.touchSwipe/jquery.touchSwipe.js');
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} viewInfo
     */
    _isQuickCreateEnabled: function () {
        var groupBy = this.loadParams.groupBy[0];
        groupBy = groupBy !== undefined ? groupBy.split(':')[0] : undefined;
        if (groupBy !== undefined && !_.contains(['char', 'boolean', 'many2one'], this.fields[groupBy].type)) {
            return false;
        }
        if (!this.controllerParams.activeActions.create) {
            return false;
        }
        if (this.arch.attrs.quick_create !== undefined) {
            return JSON.parse(this.arch.attrs.quick_create);
        }
        return true;
    },
});

return KanbanView;

});
