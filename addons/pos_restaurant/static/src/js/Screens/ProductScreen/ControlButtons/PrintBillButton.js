/** @odoo-module */

import { usePos } from "@point_of_sale/app/pos_hook";
import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { Component } from "@odoo/owl";

export class PrintBillButton extends Component {
    static template = "PrintBillButton";

    setup() {
        super.setup();
        this.pos = usePos();
    }
    _isDisabled() {
        const order = this.env.pos.get_order();
        return order.get_orderlines().length === 0;
    }
    click() {
        this.pos.showTempScreen("BillScreen");
    }
}

ProductScreen.addControlButton({
    component: PrintBillButton,
    condition: function () {
        return this.env.pos.config.iface_printbill;
    },
});
