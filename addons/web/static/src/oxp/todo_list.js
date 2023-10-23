/** @odoo-module **/

import { registry } from "@web/core/registry";

import { Component, useState } from "@odoo/owl";

export class TodoList extends Component {
    static template = "web.TodoList";

    setup() {
        this.nextId = 1;
        this.state = useState({
            todoItems: [
                {
                    id: 1,
                    message: "Send email to John",
                    isDone: false,
                },
            ],
            todoIdInEdition: null,
        });
    }

    onInputChange(ev) {
        this.state.todoItems.push({
            id: ++this.nextId,
            message: ev.target.value,
            isDone: false,
        });
        ev.target.value = "";
    }

    delete(id) {
        const index = this.state.todoItems.findIndex((todo) => todo.id === id);
        this.state.todoItems.splice(index, 1);
    }

    toggleDone(id) {
        const todoItem = this.state.todoItems.find((todo) => todo.id === id);
        todoItem.isDone = !todoItem.isDone;
    }

    switchInEdition(id) {
        this.state.todoIdInEdition = id;
    }

    editMessage(ev) {
        const todoItem = this.state.todoItems.find(
            (todo) => todo.id === this.state.todoIdInEdition
        );
        todoItem.message = ev.target.value;
        this.state.todoIdInEdition = null;
    }
}

registry.category("actions").add("todo_list", TodoList);
