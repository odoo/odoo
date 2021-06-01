/** @odoo-module **/

import KanbanController from 'web.KanbanController';
import KanbanView from 'web.KanbanView';
import KanbanColumn from 'web.KanbanColumn';
import viewRegistry from 'web.view_registry';
import KanbanRecord from 'web.KanbanRecord';
import { ProjectControlPanel } from '@project/js/project_control_panel';

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

export const ProjectKanbanController = KanbanController.extend({
    custom_events: Object.assign({}, KanbanController.prototype.custom_events, {
        'kanban_column_delete_wizard': '_onDeleteColumnWizard',
    }),

    _onDeleteColumnWizard: function (ev) {
        ev.stopPropagation();
        const self = this;
        const columnId = ev.target.id;
        const state = this.model.get(this.handle, {raw: true});
        this._rpc({
            model: 'project.task.type',
            method: 'unlink_wizard',
            args: [columnId],
            context: state.getContext(),
        }).then(function (res) {
            self.do_action(res);
        });
    }
});

const ProjectKanbanView = KanbanView.extend({
    config: Object.assign({}, KanbanView.prototype.config, {
        Controller: ProjectKanbanController,
        ControlPanel: ProjectControlPanel,
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

viewRegistry.add('project_kanban', ProjectKanbanView);
