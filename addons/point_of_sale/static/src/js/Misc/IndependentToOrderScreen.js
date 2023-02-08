/** @odoo-module */

import { usePos } from "@point_of_sale/app/pos_hook";
import { LegacyComponent } from "@web/legacy/legacy_component";

export class IndependentToOrderScreen extends LegacyComponent {
    static storeOnOrder = false;
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
    }
    close() {
        this.pos.closeScreen();
    }
}
