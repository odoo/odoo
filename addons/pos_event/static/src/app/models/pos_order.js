// Part of Odoo. See LICENSE file for full copyright and licensing details.
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    get eventRegistrations() {
        return this.lines.flatMap((line) => line.event_registration_ids);
    },
    setPricelist(pricelist) {
        super.setPricelist(pricelist);
        // Restore original ticket price for event tickets orderlines, overriding pricelist-based changes
        for (const line of this.lines) {
            const ticket = line.event_ticket_id;
            if (ticket) {
                line.setUnitPrice(ticket.price ?? line.price_unit);
            }
        }
    },
});
