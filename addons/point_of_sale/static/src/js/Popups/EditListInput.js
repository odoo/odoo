/** @odoo-module */

import { Component } from "@odoo/owl";

/**
 * props {
 *     createNewItem: callback,
 *     removeItem: callback,
 *     item: object,
 * }
 */
export class EditListInput extends Component {
    static template = "EditListInput";
    static props = {
        deletable: Boolean,
        removeItem: Function,
        item: Object,
        createNewItem: Function,
        onInputChange: Function,
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
