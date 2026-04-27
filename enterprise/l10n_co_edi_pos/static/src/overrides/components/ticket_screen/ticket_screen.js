/** @odoo-module */

import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
    // Override
    setPartnerToRefundOrder(partner, destinationOrder) {
        if (this.pos.company.l10n_co_edi_pos_dian_enabled) {
            const destinationPartner = destinationOrder.get_partner();
            if (
                partner &&
                (!destinationPartner ||
                    destinationPartner.id === this.pos.session._l10n_co_final_consumer_id)
            ) {
                destinationOrder.set_partner(partner);
            }
        } else {
            super.setPartnerToRefundOrder(partner, destinationOrder);
        }
    },
});
