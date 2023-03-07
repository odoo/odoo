/** @odoo-module */

import { registry } from "@web/core/registry";
import { TodoKanbanModel } from "@note/views/todo_kanban/todo_kanban_model";
import { todoKanbanView } from "@note/views/todo_kanban/todo_kanban_view";
import { ProjectTaskKanbanRenderer } from './project_task_kanban_renderer';
import { ProjectControlPanel } from "../../components/project_control_panel/project_control_panel";

export const projectTaskKanbanView = {
    ...todoKanbanView,
    Model: TodoKanbanModel,
    Renderer: ProjectTaskKanbanRenderer,
    ControlPanel: ProjectControlPanel,
};

registry.category('views').add('project_task_kanban', projectTaskKanbanView);
