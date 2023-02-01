/** @odoo-module */

import { useListener } from "@web/core/utils/hooks";
import { PosComponent } from "@point_of_sale/js/PosComponent";
import { usePos } from "@point_of_sale/app/pos_hook";

export class ReprintReceiptButton extends PosComponent {
    static template = "ReprintReceiptButton";

    setup() {
        super.setup();
        this.pos = usePos();
        useListener("click", this._onClick);
    }
    async _onClick() {
        if (!this.props.order) {
            return;
        }
        this.pos.showScreen("ReprintReceiptScreen", { order: this.props.order });
    }
}
