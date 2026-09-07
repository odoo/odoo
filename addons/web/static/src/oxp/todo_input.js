/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useTodoListModel } from "./todo_model";

export class TodoInput extends Component {
    static template = "web.TodoInput";

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
