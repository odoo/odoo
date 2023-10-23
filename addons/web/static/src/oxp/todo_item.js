/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

export class TodoItem extends Component {
    static template = "web.TodoItem";
    static props = {
        todoItem: Object,
        toggleDone: Function,
        delete: Function,
        editMessage: Function,
    };

    setup() {
        this.state = useState({
            isInEdition: false,
        });
    }

    editMessage(ev) {
        this.props.editMessage(ev.target.value);
        this.state.isInEdition = false;
    }

    switchInEdition() {
        this.state.isInEdition = true;
    }
}
