/** @odoo-module */

import { ProductScreen } from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import { usePos } from "@point_of_sale/app/pos_hook";
import { Component } from "@odoo/owl";

export class SetSaleOrderButton extends Component {
    static template = "SetSaleOrderButton";
    setup() {
        this.pos = usePos();
    }
    async click() {
        this.pos.showScreen("SaleOrderManagementScreen");
    }
}

ProductScreen.addControlButton({ component: SetSaleOrderButton });
