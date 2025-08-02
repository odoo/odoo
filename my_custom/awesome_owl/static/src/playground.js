/** @odoo-module **/

import { Component, useState, xml, markup } from "@odoo/owl";
import { Counter } from "./counter/counter.js";
import { Card } from "./card/card.js";
import { TodoList } from "./TodoList/todo_list.js";

export class Playground extends Component {
  // Đăng kí component con
  static components = { Counter, Card, TodoList };

  // Dùng template được định nghĩa sẵn trong XML
  static template = "awesome_owl.playground";

  // static template = xml`
  //   <Counter/>
  //   <div>
  //     <Card title="'card 1'" content="value1"/>
  //     <Card title="'card 2'" content="value2"/>
  //   </div>
  // `;

  content1 = "content of card 1";
  content2 = markup("<div>new content of card 2</div>");

  setup() {
    this.state = useState({ sum: 0 });
  }

  incrementSum(newValue) {
    this.state.sum++;
  }
}
