/** @odoo-module */

import { useListener } from "@web/core/utils/hooks";
import PosComponent from "@point_of_sale/js/PosComponent";
import Registries from "@point_of_sale/js/Registries";

class ReprintReceiptButton extends PosComponent {
    setup() {
        super.setup();
        useListener("click", this._onClick);
    }
    async _onClick() {
        if (!this.props.order) {
            return;
        }
        this.showScreen("ReprintReceiptScreen", { order: this.props.order });
    }
}
ReprintReceiptButton.template = "ReprintReceiptButton";
Registries.Component.add(ReprintReceiptButton);

export default ReprintReceiptButton;
