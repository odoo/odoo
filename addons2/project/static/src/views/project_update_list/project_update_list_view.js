/** @odoo-module */

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ProjectUpdateListController } from './project_update_list_controller';

export const projectUpdateListView = {
    ...listView,
    Controller: ProjectUpdateListController,
};

registry.category('views').add('project_update_list', projectUpdateListView);
