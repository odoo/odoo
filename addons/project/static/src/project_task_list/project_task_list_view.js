/** @odoo-module */

import { registry } from "@web/core/registry";
import { listView } from '@web/views/list/list_view';
import { ProjectTaskListController } from './project_task_list_controller';

export const projectTaskListView = {
    ...listView,
    Controller: ProjectTaskListController,
};

registry.category("views").add("project_task_list", projectTaskListView);
