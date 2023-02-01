/** @odoo-module */

import { usePos } from "@point_of_sale/app/pos_hook";
import { PosComponent } from "@point_of_sale/js/PosComponent";
import { TicketScreen } from "@point_of_sale/js/Screens/TicketScreen/TicketScreen";

export class TicketButton extends PosComponent {
    static template = "TicketButton";

    setup() {
        this.pos = usePos();
    }
    onClick() {
        if (this.isTicketScreenShown) {
            this.env.posbus.trigger("ticket-button-clicked");
        } else {
            this.pos.showScreen("TicketScreen");
        }
    }
    get isTicketScreenShown() {
        return this.pos.mainScreen.component === TicketScreen;
    }
    get count() {
        if (this.env.pos) {
            return this.env.pos.get_order_list().length;
        } else {
            return 0;
        }
    }
}
