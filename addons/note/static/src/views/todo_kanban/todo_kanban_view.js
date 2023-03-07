/** @odoo-module */

import { registry } from "@web/core/registry";
import { kanbanView } from '@web/views/kanban/kanban_view';
import { TodoKanbanModel } from "./todo_kanban_model";
import { TodoKanbanRenderer } from './todo_kanban_renderer';

export const todoKanbanView = {
    ...kanbanView,
    Model: TodoKanbanModel,
    Renderer: TodoKanbanRenderer,
};

registry.category('views').add('project_task_to_do_kanban', todoKanbanView);
