/** @odoo-module */

import { usePos } from "@point_of_sale/app/pos_hook";
import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { Component } from "@odoo/owl";

export class TransferOrderButton extends Component {
    static template = "TransferOrderButton";

    setup() {
        this.pos = usePos();
    }
    async click() {
        this.pos.globalState.setCurrentOrderToTransfer();
        this.pos.showScreen("FloorScreen");
    }
}

ProductScreen.addControlButton({
    component: TransferOrderButton,
    condition: function () {
        return this.pos.globalState.config.module_pos_restaurant;
    },
});
