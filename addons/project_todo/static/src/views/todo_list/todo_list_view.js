/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { TodoListController } from "./todo_list_controller";

export const todoListView = {
    ...listView,
    Controller: TodoListController,
};

registry.category("views").add("todo_list", todoListView);
