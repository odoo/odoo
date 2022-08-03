/** @odoo-module */

import { registry } from "@web/core/registry";
import { listView } from '@web/views/list/list_view';
import { ProjectControlPanel } from "../../components/project_control_panel/project_control_panel";

export const projectTaskListView = {
    ...listView,
    ControlPanel: ProjectControlPanel,
};

registry.category("views").add("project_task_list", projectTaskListView);
