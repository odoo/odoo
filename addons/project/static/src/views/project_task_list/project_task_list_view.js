/** @odoo-module */

import { registry } from "@web/core/registry";
import { listView } from '@web/views/list/list_view';
import { ProjectTaskListController } from "./project_task_list_controller";
import { ProjectTaskListRenderer } from "./project_task_list_renderer";

export const projectTaskListView = {
    ...listView,
    Controller: ProjectTaskListController,
    Renderer: ProjectTaskListRenderer,
};

registry.category("views").add("project_task_list", projectTaskListView);
