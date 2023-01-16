/** @odoo-module */

import { usePos } from "@point_of_sale/app/pos_store";
import { PosComponent } from "@point_of_sale/js/PosComponent";

export class TicketButton extends PosComponent {
    static template = "TicketButton";

    setup() {
        this.pos = usePos();
    }
    onClick() {
        if (this.isTicketScreenShown) {
            this.env.posbus.trigger("ticket-button-clicked");
        } else {
            this.showScreen("TicketScreen");
        }
    }
    get isTicketScreenShown() {
        return this.pos.mainScreen.name === "TicketScreen";
    }
    get count() {
        if (this.env.pos) {
            return this.env.pos.get_order_list().length;
        } else {
            return 0;
        }
    }
}
