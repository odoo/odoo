/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { TodoItem } from "./todo_item";
import { useTodoListModel } from "./todo_model";
import { ComponentA } from "./component_a";

export class TodoList extends Component {
    static template = "web.TodoList";
    static components = { TodoItem, ComponentA };

    setup() {
        this.todoListModel = useTodoListModel();
    }

    onInputChange(ev) {
        this.todoListModel.add({
            message: ev.target.value,
        });
        ev.target.value = "";
    }
}

registry.category("actions").add("todo_list", TodoList);
