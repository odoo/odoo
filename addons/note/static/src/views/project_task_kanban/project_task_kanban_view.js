/** @odoo-module */

import { registry } from "@web/core/registry";
import { kanbanView } from '@web/views/kanban/kanban_view';
import { ProjectTaskKanbanModel } from "./project_task_kanban_model";
import { ProjectTaskKanbanRenderer } from './project_task_kanban_renderer';
/**import { ProjectControlPanel } from "../../components/project_control_panel/project_control_panel";*//**TO CHECK*/

export const projectTaskToDoKanbanView = {
    ...kanbanView,
    Model: ProjectTaskKanbanModel,
    Renderer: ProjectTaskKanbanRenderer,
/**    ControlPanel: ProjectControlPanel,*/
};

registry.category('views').add('project_task_to_do_kanban', projectTaskToDoKanbanView);
