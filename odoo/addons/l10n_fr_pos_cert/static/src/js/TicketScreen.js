/** @odoo-module **/

import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
    shouldHideDeleteButton() {
        return this.pos.is_french_country() || super.shouldHideDeleteButton(...arguments);
    }
});
