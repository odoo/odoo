/** @odoo-module */

import { usePos } from "@point_of_sale/app/pos_hook";
import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { Component } from "@odoo/owl";

export class SplitBillButton extends Component {
    static template = "SplitBillButton";

    setup() {
        this.pos = usePos();
    }
    _isDisabled() {
        const order = this.pos.globalState.get_order();
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
        return this.pos.globalState.config.iface_splitbill;
    },
});
