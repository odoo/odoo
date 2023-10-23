/** @odoo-module **/

import { reactive, useComponent, useState, useSubEnv } from "@odoo/owl";

let nextId = 1;

class TodoItemModel {
    constructor(todoList, { message, isDone }) {
        this.id = nextId++;
        this.todoList = todoList;
        this.message = message || "";
        this.isDone = isDone || false;
    }

    toggleDone() {
        this.isDone = !this.isDone;
    }

    editMessage(message) {
        this.message = message;
    }

    delete() {
        this.todoList.delete(this.id);
    }
}

export class TodoListModel {
    constructor(todoItems) {
        this.todoItems = todoItems.map((todoItem) => new TodoItemModel(this, todoItem));
    }

    add(todoItem) {
        this.todoItems.push(new TodoItemModel(this, todoItem));
    }

    delete(id) {
        const index = this.todoItems.findIndex((todo) => todo.id === id);
        this.todoItems.splice(index, 1);
    }
}

export function useTodoListModel() {
    const component = useComponent();
    if (!component.env.todoListModel) {
        useSubEnv({
            todoListModel: reactive(
                new TodoListModel([
                    {
                        message: "Send email to John",
                    },
                ])
            ),
        });
    }
    return useState(component.env.todoListModel);
}
