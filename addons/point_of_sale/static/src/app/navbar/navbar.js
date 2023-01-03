/** @odoo-module */

import PosComponent from "@point_of_sale/js/PosComponent";
import { usePos } from "@point_of_sale/app/pos_store";

export class Navbar extends PosComponent {
    static template = "point_of_sale.Navbar";
    static props = {
        showCashMoveButton: Boolean,
    };
    setup() {
        this.pos = usePos();
    }
    get customerFacingDisplayButtonIsShown() {
        return this.env.pos.config.iface_customer_facing_display;
    }
}
