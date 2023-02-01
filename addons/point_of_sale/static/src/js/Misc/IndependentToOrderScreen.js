/** @odoo-module */

import { usePos } from "@point_of_sale/app/pos_hook";
import { PosComponent } from "@point_of_sale/js/PosComponent";

export class IndependentToOrderScreen extends PosComponent {
    static storeOnOrder = false;
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
    }
    close() {
        const order = this.env.pos.get_order();
        const { name: screenName } = order.get_screen_data();
        this.pos.showScreen(screenName);
    }
}
