/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { TodoItem } from "../TodoItem/todo_item.js";
import { useAutoFocus } from "../utils.js";

export class TodoList extends Component {
  static template = "awesome_owl.todo_list";
  static components = {
    TodoItem,
  };

  setup() {
    this.todos = useState([
      // { id: 1, description: "Buy milk", isCompleted: false },
      // { id: 2, description: "Write code", isCompleted: true },
      // { id: 3, description: "Read a book", isCompleted: false },
    ]);

    this.todoId = 1

    this.toggleState = this.toggleState.bind(this);
    this.removeItem = this.removeItem.bind(this);

    this.inputRef = useAutoFocus('input')
  }

  addTodo(e) {
    if (e.keyCode === 13) {
      const input = e.target;
      const description = input.value.trim();

      if (description) {
        this.todos.push({ id: this.todoId++, description, isCompleted: false });
        input.value = "";
      }
    }
  }

  toggleState(todoId) {
    const todo = this.todos.find(todo => todo.id === todoId)
    if (todo) {
      todo.isCompleted = !todo.isCompleted
    }
  }

  removeItem(id) {
    const index = this.todos.findIndex((todo) => todo.id === id);
    if (index !== -1) {
      this.todos.splice(index, 1);
    }
  }
}
