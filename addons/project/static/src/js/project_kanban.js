odoo.define('project.project_kanban', function (require) {
'use strict';

var KanbanController = require('web.KanbanController');
var KanbanView = require('web.KanbanView');
var KanbanColumn = require('web.KanbanColumn');
var view_registry = require('web.view_registry');
var KanbanRecord = require('web.KanbanRecord');
const ProjectControlPanel = require("project.ProjectControlPanel");
const ProjectUpdateWidget = require("project.ProjectUpdateWidget");

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
        if (this.modelName === 'project.project' && this.$(".o_project_kanban_boxes a").length) {
            /* const activeId = this.state.data.id;
            if (activeId) {
                this.do_action({
                    type: "ir.actions.client",
                    tag: "action_project_updates",
                    res_model: "project.task",
                    params: {
                        active_id: activeId,
                    },
                }, { clear_breadcrumbs: false });
            } */
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

    /**
     * @override
     */
    start: function() {
        this._super.apply(this, arguments);
        var $project_update_jquery = document.querySelector('.o_project_updates_breadcrumb');
        new ProjectUpdateWidget(this).mount(project_update_jquery);
    },

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
        Controller: ProjectKanbanController,
        ControlPanel: ProjectControlPanel
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
