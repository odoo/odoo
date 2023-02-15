/** @odoo-module */

import { LegacyComponent } from "@web/legacy/legacy_component";

/**
 * props {
 *     createNewItem: callback,
 *     removeItem: callback,
 *     item: object,
 * }
 */
export class EditListInput extends LegacyComponent {
    static template = "EditListInput";

    onKeyup(event) {
        if (event.key === "Enter" && event.target.value.trim() !== "") {
            this.props.createNewItem();
        }
    }
    onInput(event) {
        this.props.onInputChange(this.props.item._id, event.target.value);
    }
}
