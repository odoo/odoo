/** @odoo-module */

import { usePos } from "@point_of_sale/app/pos_hook";
import { LegacyComponent } from "@web/legacy/legacy_component";
import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { useListener } from "@web/core/utils/hooks";

export class PrintBillButton extends LegacyComponent {
    static template = "PrintBillButton";

    setup() {
        super.setup();
        this.pos = usePos();
        useListener("click", this.onClick);
    }
    _isDisabled() {
        const order = this.env.pos.get_order();
        return order.get_orderlines().length === 0;
    }
    onClick() {
        this.pos.showTempScreen("BillScreen");
    }
}

ProductScreen.addControlButton({
    component: PrintBillButton,
    condition: function () {
        return this.env.pos.config.iface_printbill;
    },
});
