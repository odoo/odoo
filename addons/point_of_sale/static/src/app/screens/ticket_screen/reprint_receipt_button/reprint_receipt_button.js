/** @odoo-module */

import { usePos } from "@point_of_sale/app/pos_hook";
import { Component } from "@odoo/owl";

export class ReprintReceiptButton extends Component {
    static template = "ReprintReceiptButton";

    setup() {
        super.setup();
        this.pos = usePos();
    }
    async click() {
        if (!this.props.order) {
            return;
        }
        this.pos.showScreen("ReprintReceiptScreen", { order: this.props.order });
    }
}
