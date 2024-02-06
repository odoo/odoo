/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

export class BackButton extends Component {
    static template = "point_of_sale.BackButton";
    static props = {};

    setup() {
        this.pos = usePos();
        this.ui = useState(useService("ui"));
    }
    _mobile_back_button() {
        if (this.pos.showResultMobile && this.ui.isSmall) {
            this.pos.showResultMobile = false;
        } else if (this.pos.selectedCategory && this.ui.isSmall) {
            this.pos.setSelectedCategory(this.pos.selectedCategory.parent_id?.id);
        } else {
            return false;
        }
        return true;
    }
    async onClick() {
        if (this.pos.mainScreen.component === TicketScreen) {
            if (this.pos.ticket_screen_mobile_pane == "left") {
                this.pos.closeScreen();
            } else {
                this.pos.ticket_screen_mobile_pane = "left";
            }
        } else if (
            this.pos.mobile_pane == "left" ||
            this.pos.mainScreen.component === PaymentScreen
        ) {
            this.pos.mobile_pane = "right";
            this.pos.showScreen("ProductScreen");
        } else {
            this._mobile_back_button();
        }
    }
}
