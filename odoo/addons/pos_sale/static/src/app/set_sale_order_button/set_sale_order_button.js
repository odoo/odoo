/** @odoo-module */

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component } from "@odoo/owl";

export class SetSaleOrderButton extends Component {
    static template = "pos_sale.SetSaleOrderButton";
    setup() {
        this.pos = usePos();
    }
    async click() {
        this.pos.showScreen("SaleOrderManagementScreen");
    }
}

ProductScreen.addControlButton({ component: SetSaleOrderButton });
