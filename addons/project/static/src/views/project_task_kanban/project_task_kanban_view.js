import { registry } from "@web/core/registry";
import { kanbanView } from '@web/views/kanban/kanban_view';
import { ProjectTaskKanbanController } from "./project_task_kanban_controller";
import { ProjectTaskKanbanModel } from "./project_task_kanban_model";
import { ProjectTaskKanbanRenderer } from './project_task_kanban_renderer';

export const projectTaskKanbanView = {
    ...kanbanView,
    Model: ProjectTaskKanbanModel,
    Renderer: ProjectTaskKanbanRenderer,
    Controller: ProjectTaskKanbanController,
};

registry.category('views').add('project_task_kanban', projectTaskKanbanView);
