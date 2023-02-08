/** @odoo-module */

import { useListener } from "@web/core/utils/hooks";
import { LegacyComponent } from "@web/legacy/legacy_component";
import { usePos } from "@point_of_sale/app/pos_hook";

export class ReprintReceiptButton extends LegacyComponent {
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
