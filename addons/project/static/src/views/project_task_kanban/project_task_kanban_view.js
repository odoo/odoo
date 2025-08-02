import { registry } from "@web/core/registry";
import { kanbanView } from '@web/views/kanban/kanban_view';
import { ProjectTaskKanbanController } from "./project_task_kanban_controller";
import { ProjectTaskKanbanModel } from "./project_task_kanban_model";
import { ProjectTaskKanbanRenderer } from './project_task_kanban_renderer';
import { ProjectTaskControlPanel } from "../project_task_control_panel/project_task_control_panel";

export const projectTaskKanbanView = {
    ...kanbanView,
    ControlPanel: ProjectTaskControlPanel,
    Model: ProjectTaskKanbanModel,
    Renderer: ProjectTaskKanbanRenderer,
    Controller: ProjectTaskKanbanController,
    buttonTemplate: "project.ProjectTaskKanbanView.Buttons",
};

registry.category('views').add('project_task_kanban', projectTaskKanbanView);
