/** @odoo-module */

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/pos_hook";

export class IndependentToOrderScreen extends Component {
    static storeOnOrder = false;
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
    }
    close() {
        this.pos.closeScreen();
    }
}
