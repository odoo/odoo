/** @odoo-module */

import { usePos } from "@point_of_sale/app/pos_hook";
import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { Component } from "@odoo/owl";

export class CustomerButton extends Component {
    static template = "point_of_sale.CustomerButton";

    setup() {
        this.pos = usePos();
    }

    get partner() {
        const order = this.pos.globalState.get_order();
        return order ? order.get_partner() : null;
    }
}

ProductScreen.addControlButton({
    component: CustomerButton,
    position: ["before", "SetFiscalPositionButton"],
    condition: function () {
        return (
            this.pos.globalState.config.module_pos_restaurant &&
            this.pos.globalState.orderPreparationCategories.size
        );
    },
});
