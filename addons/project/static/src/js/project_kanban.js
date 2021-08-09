/** @odoo-module **/

import KanbanController from 'web.KanbanController';
import KanbanRenderer from 'web.KanbanRenderer';
import KanbanView from 'web.KanbanView';
import KanbanColumn from 'web.KanbanColumn';
import viewRegistry from 'web.view_registry';
import KanbanRecord from 'web.KanbanRecord';
import { ProjectControlPanel } from '@project/js/project_control_panel';

// PROJECTS

const ProjectProjectKanbanRecord = KanbanRecord.extend({
    /**
     * @override
     * @private
     */
    _openRecord: function () {
        const kanbanBoxesElement = this.el.querySelectorAll('.o_project_kanban_boxes a');
        if (this.selectionMode !== true && kanbanBoxesElement.length) {
            kanbanBoxesElement[0].click();
        } else {
            this._super.apply(this, arguments);
        }
    },
});

const ProjectProjectKanbanRenderer = KanbanRenderer.extend({
    config: _.extend({}, KanbanRenderer.prototype.config, {
        KanbanRecord: ProjectProjectKanbanRecord,
    }),
});

const ProjectProjectKanbanView = KanbanView.extend({
    config: Object.assign({}, KanbanView.prototype.config, {
        Renderer: ProjectProjectKanbanRenderer,
    })
});

viewRegistry.add('project_project_kanban', ProjectProjectKanbanView);

// TASKS

const ProjectTaskKanbanColumn = KanbanColumn.extend({
    /**
     * @override
     * @private
     */
    _onDeleteColumn: function (event) {
        event.preventDefault();
        this.trigger_up('kanban_column_delete_wizard');
    },
});

const ProjectTaskKanbanRenderer = KanbanRenderer.extend({
    config: Object.assign({}, KanbanRenderer.prototype.config, {
        KanbanColumn: ProjectTaskKanbanColumn,
    }),
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
    },
});

const ProjectKanbanView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Controller: ProjectKanbanController,
        Renderer: ProjectTaskKanbanRenderer,
        ControlPanel: ProjectControlPanel,
    }),
});

viewRegistry.add('project_task_kanban', ProjectKanbanView);
