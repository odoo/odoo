/** @odoo-module */

import { registry } from "@web/core/registry";
import { listView } from '@web/views/list/list_view';
import { FolderListController } from "./folder_list_controller";

export const FolderListView = {
    ...listView,
    Controller: FolderListController,
};

registry.category("views").add("folder_list", FolderListView);
