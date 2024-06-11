/** @odoo-module */

import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
    setPartnerToRefundOrder(partner, destinationOrder) {
        if (!this.pos.isPeruvianCompany()) {
            return super.setPartnerToRefundOrder(...arguments);
        }
        if (
            partner &&
            (!destinationOrder.get_partner() ||
                destinationOrder.get_partner().id === this.pos.consumidorFinalAnonimoId)
        ) {
            return destinationOrder.set_partner(partner);
        }
    },
});
