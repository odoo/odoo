/** @odoo-module */

import { Component } from "@odoo/owl";

export class EditListInput extends Component {
    static template = "point_of_sale.EditListInput";
    static props = {
        item: Object,
        deletable: Boolean,
        createNewItem: Function,
        onInputChange: Function,
        removeItem: Function,
    };

    onKeyup(event) {
        if (event.key === "Enter" && event.target.value.trim() !== "") {
            this.props.createNewItem();
        }
    }
    onInput(event) {
        this.props.onInputChange(this.props.item._id, event.target.value);
    }
}
