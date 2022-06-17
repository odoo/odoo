/** @odoo-module */

import { registry } from "@web/core/registry";
import { kanbanView } from '@web/views/kanban/kanban_view';
import { ProjectTaskKanbanRenderer } from './project_task_kanban_renderer';

export const projectTaskKanbanView = {
    ...kanbanView,
    Renderer: ProjectTaskKanbanRenderer,
};

registry.category('views').add('project_task_kanban', projectTaskKanbanView);
