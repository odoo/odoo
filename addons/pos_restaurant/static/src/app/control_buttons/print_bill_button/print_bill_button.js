/** @odoo-module */

import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { Component } from "@odoo/owl";

export class PrintBillButton extends Component {
    static template = "pos_restaurant.PrintBillButton";

    setup() {
        this.pos = usePos();
    }
    _isDisabled() {
        const order = this.pos.get_order();
        if (!order) {
            return false;
        }
        return order.get_orderlines().length === 0;
    }
    click() {
        this.pos.showTempScreen("BillScreen");
    }
}

ProductScreen.addControlButton({
    component: PrintBillButton,
    condition: function () {
        return this.pos.config.iface_printbill;
    },
});
