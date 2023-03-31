/** @odoo-module */

import { registry } from "@web/core/registry";
import { listView } from '@web/views/list/list_view';
import { ProjectControlPanel } from "../../components/project_control_panel/project_control_panel";
import { ProjectTaskListController } from "./project_task_list_controller";
import { ProjectTaskListRenderer } from "./project_task_list_renderer";

export const projectTaskListView = {
    ...listView,
    ControlPanel: ProjectControlPanel,
    Controller: ProjectTaskListController,
    Renderer: ProjectTaskListRenderer,
};

registry.category("views").add("project_task_list", projectTaskListView);
