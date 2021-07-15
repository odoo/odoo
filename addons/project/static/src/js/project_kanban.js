odoo.define('project.project_kanban', function (require) {
'use strict';

var KanbanController = require('web.KanbanController');
var KanbanView = require('web.KanbanView');
var KanbanColumn = require('web.KanbanColumn');
var view_registry = require('web.view_registry');
var KanbanRecord = require('web.KanbanRecord');

KanbanRecord.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
     // YTI TODO: Should be transformed into a extend and specific to project
    _openRecord: function () {
        if (this.selectionMode !== true && this.modelName === 'project.project' &&
            this.$(".o_project_kanban_boxes a").length) {
            this.$('.o_project_kanban_boxes a').first().click();
        } else {
            this._super.apply(this, arguments);
        }
    },
});

var ProjectKanbanController = KanbanController.extend({
    custom_events: _.extend({}, KanbanController.prototype.custom_events, {
        'kanban_column_delete_wizard': '_onDeleteColumnWizard',
    }),

    _onDeleteColumnWizard: function (ev) {
        ev.stopPropagation();
        const self = this;
        const column_id = ev.target.id;
        var state = this.model.get(this.handle, {raw: true});
        this._rpc({
            model: 'project.task.type',
            method: 'unlink_wizard',
            args: [column_id],
            context: state.getContext(),
        }).then(function (res) {
            self.do_action(res);
        });
    }
});

var ProjectKanbanView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Controller: ProjectKanbanController
    }),
});

KanbanColumn.include({
    _onDeleteColumn: function (event) {
        event.preventDefault();
        if (this.modelName === 'project.task') {
            this.trigger_up('kanban_column_delete_wizard');
            return;
        }
        this._super.apply(this, arguments);
    }
});

view_registry.add('project_kanban', ProjectKanbanView);

return ProjectKanbanController;
});
