odoo.define('web.KanbanView', function (require) {
"use strict";

var BasicView = require('web.BasicView');
var core = require('web.core');
var KanbanModel = require('web.KanbanModel');
var KanbanRenderer = require('web.KanbanRenderer');
var KanbanController = require('web.KanbanController');

var _lt = core._lt;

var KanbanView = BasicView.extend({
    accesskey: "k",
    className: "o_kanban",
    display_name: _lt("Kanban"),
    icon: 'fa-th-large',
    mobile_friendly: true,
    config: {
        Model: KanbanModel,
        Controller: KanbanController,
        Renderer: KanbanRenderer,
    },
    init: function (arch, fields, params) {
        this._super.apply(this, arguments);

        var activeActions = this.controllerParams.activeActions;
        activeActions = _.extend(activeActions, {
            group_edit: arch.attrs.group_edit ? JSON.parse(arch.attrs.group_edit) : true,
            group_delete: arch.attrs.group_delete ? JSON.parse(arch.attrs.group_delete) : true,
        });

        this.rendererParams.column_options = {
            editable: activeActions.group_edit,
            deletable: activeActions.group_delete,
            group_creatable: true,
            quick_create: params.isQuickCreateEnabled || this._isQuickCreateEnabled(arch),
        };
        this.rendererParams.record_options = {
            editable: activeActions.edit,
            deletable: activeActions.delete,
            read_only_mode: params.readOnlyMode,
        };

        this.controllerParams.on_create = arch.attrs.on_create;

        this.controllerParams.readOnlyMode = false;
        this.controllerParams.hasButtons = true;

        this.loadParams.limit = this.loadParams.limit || 40;
        this.loadParams.openGroupByDefault = true;
        this.loadParams.type = 'list';

        this.loadParams.groupBy = arch.attrs.default_group_by ? [arch.attrs.default_group_by] : (params.groupBy || []);
    },
    _isQuickCreateEnabled: function (arch) {
        if (!this.controllerParams.activeActions.create) {
            return false;
        }
        if (arch.attrs.quick_create !== undefined) {
            return JSON.parse(arch.attrs.quick_create);
        }
        return true;
    }


});

return KanbanView;

});

    // config: _.extend({}, AbstractView.prototype.config, {
    //     openGroupByDefault: true,
    // }),
    // FIXME: adapt those options
    // defaults: _.extend(BasicController.prototype.defaults, {
    //     quick_creatable: true,
    //     creatable: true,
    //     read_only_mode: false,
    //     confirm_on_delete: true,
    // }),
