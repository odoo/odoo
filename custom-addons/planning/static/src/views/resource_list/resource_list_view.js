/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from '@web/views/list/list_view';
import { ResourceListController } from "@planning/views/resource_list/resource_list_controller";

export const resourceListView = {
    ...listView,
    Controller: ResourceListController,
};

registry.category("views").add("resource_list_view", resourceListView);
