/** @odoo-module */

import { useListener } from "@web/core/utils/hooks";
import { PosComponent } from "@point_of_sale/js/PosComponent";

export class ReprintReceiptButton extends PosComponent {
    static template = "ReprintReceiptButton";

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
