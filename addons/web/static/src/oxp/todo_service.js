/** @odoo-module **/

import { registry } from "@web/core/registry";
import { TodoListModel } from "./todo_model";
import { reactive } from "@odoo/owl";

export const todoService = {
    start() {
        const todoListModel = reactive(
            new TodoListModel([
                {
                    message: "Send email to John",
                },
            ])
        );

        return {
            todoListModel,
        };
    },
};

registry.category("services").add("todo", todoService);
