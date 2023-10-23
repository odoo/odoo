/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

export class TodoItem extends Component {
    static template = "web.TodoItem";
    static props = {
        todoItem: Object,
    };

    setup() {
        this.state = useState({
            isInEdition: false,
        });
    }

    editMessage(ev) {
        this.props.todoItem.editMessage(ev.target.value);
        this.state.isInEdition = false;
    }

    switchInEdition() {
        this.state.isInEdition = true;
    }
}
