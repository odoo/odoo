/** @odoo-module **/

import TicketScreen from "point_of_sale.TicketScreen";
import {patch} from "@web/core/utils/patch";

patch(TicketScreen.prototype, "l10n_pe_pos.TicketScreen", {
    setPartnerToRefundOrder(partner, destinationOrder) {
        if (this.env.pos.isPeruvianCompany()) {
            if (
                partner &&
                (!destinationOrder.get_partner() ||
                    destinationOrder.get_partner().id === this.env.pos.consumidorFinalId)
            ) {
                destinationOrder.set_partner(partner);
            }
        } else {
            this._super(...arguments);
        }
    },
});
