/** @odoo-module */

import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { Component } from "@odoo/owl";

export class SplitBillButton extends Component {
    static template = "pos_restaurant.SplitBillButton";

    setup() {
        this.pos = usePos();
    }
    _isDisabled() {
        const order = this.pos.get_order();
        return (
            order
                .get_orderlines()
                .reduce((totalProduct, orderline) => totalProduct + orderline.quantity, 0) < 2
        );
    }
    async click() {
        this.pos.showScreen("SplitBillScreen");
    }
}

ProductScreen.addControlButton({
    component: SplitBillButton,
    condition: function () {
        return this.pos.config.iface_splitbill;
    },
});
