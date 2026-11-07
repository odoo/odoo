/** @odoo-module */

import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { Component } from "@odoo/owl";

export class TransferOrderButton extends Component {
    static template = "pos_restaurant.TransferOrderButton";

    setup() {
        this.pos = usePos();
    }
    async click() {
        this.pos.setCurrentOrderToTransfer();
        this.pos.showScreen("FloorScreen");
    }
}

ProductScreen.addControlButton({
    component: TransferOrderButton,
    condition: function () {
        return this.pos.config.module_pos_restaurant;
    },
});
