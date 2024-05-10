/** @odoo-module */

import { registry } from "@web/core/registry";
import { kanbanView } from '@web/views/kanban/kanban_view';
import { ProjectTaskKanbanModel } from "./project_task_kanban_model";
import { ProjectTaskKanbanRenderer } from './project_task_kanban_renderer';
import { ProjectTaskKanbanRecord } from './project_task_kanban_record';
import { ProjectControlPanel } from "../../components/project_control_panel/project_control_panel";

export const projectTaskKanbanView = {
    ...kanbanView,
    Model: ProjectTaskKanbanModel,
    Renderer: ProjectTaskKanbanRenderer,
    RecordLegacy: ProjectTaskKanbanRecord,
    ControlPanel: ProjectControlPanel,
};

registry.category('views').add('project_task_kanban', projectTaskKanbanView);
