/** @odoo-module */

import { usePos } from "@point_of_sale/app/pos_hook";
import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { Component } from "@odoo/owl";

export class TransferOrderButton extends Component {
    static template = "TransferOrderButton";

    setup() {
        super.setup();
        this.pos = usePos();
    }
    async click() {
        this.env.pos.setCurrentOrderToTransfer();
        this.pos.showScreen("FloorScreen");
    }
}

ProductScreen.addControlButton({
    component: TransferOrderButton,
    condition: function () {
        return this.env.pos.config.module_pos_restaurant;
    },
});
