/** @odoo-module */

import PosComponent from "@point_of_sale/js/PosComponent";
import Registries from "@point_of_sale/js/Registries";

/**
 * props {
 *     createNewItem: callback,
 *     removeItem: callback,
 *     item: object,
 * }
 */
class EditListInput extends PosComponent {
    onKeyup(event) {
        if (event.key === "Enter" && event.target.value.trim() !== "") {
            this.props.createNewItem();
        }
    }
    onInput(event) {
        this.props.onInputChange(this.props.item._id, event.target.value);
    }
}
EditListInput.template = "EditListInput";

Registries.Component.add(EditListInput);

export default EditListInput;
