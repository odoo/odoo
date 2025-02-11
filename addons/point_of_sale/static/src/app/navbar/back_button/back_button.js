/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

export class BackButton extends Component {
    static template = "point_of_sale.BackButton";

    setup() {
        this.pos = usePos();
        this.ui = useState(useService("ui"));
    }
    async onClick() {
        if (this.pos.mainScreen.component === TicketScreen) {
            if (this.pos.ticket_screen_mobile_pane == "left") {
                this.pos.closeScreen();
            } else {
                this.pos.ticket_screen_mobile_pane = "left";
            }
        } else {
            this.pos.mobile_pane = "right";
            this.pos.showScreen("ProductScreen");
        }
    }
}
