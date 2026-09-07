/** @odoo-module **/

import { registry } from "@web/core/registry";

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class TodoCounter extends Component {
    static template = "TodoCounter";

    setup() {
        this.actionService = useService("action");
        this.todoListModel = useState(useService("todo").todoListModel);
    }

    get total() {
        return this.todoListModel.todoItems.length;
    }

    get nbDone() {
        return this.todoListModel.todoItems.filter((todo) => todo.isDone).length;
    }

    onClick() {
        this.actionService.doAction({
            type: "ir.actions.client",
            tag: "todo_list",
        });
    }
}

export const systrayItem = {
    Component: TodoCounter,
};

registry.category("systray").add("oxp.todoCounter", systrayItem, { sequence: 10 });
