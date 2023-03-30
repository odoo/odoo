/** @odoo-module */

import { ListController } from "@web/views/list/list_controller";

export class TodoListController extends ListController {
    get actionMenuItems() {
        this.archiveEnabled = true;
        const actionToKeep = ["archive", "unarchive", "duplicate", "delete"];
        const menuItems = super.actionMenuItems;
        const filteredActions = menuItems.action?.filter(action => actionToKeep.includes(action.key)) || [];
        menuItems.action = filteredActions;
        menuItems.print = [];
        return menuItems;
    }
}
