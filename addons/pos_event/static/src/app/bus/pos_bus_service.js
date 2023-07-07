/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosBus } from "@point_of_sale/app/bus/pos_bus_service";

patch(PosBus.prototype, {
    // Override
    dispatch(message) {
        super.dispatch(...arguments);

        if (!this.pos.config.module_pos_restaurant && message.type === "EVENT_REGISTRATION") {
            for (const ticketUpdate of message.payload) {
                this.pos.event_tickets.find(ticket => ticket.id === ticketUpdate.id).seats_available = ticketUpdate.seats_available
            }
        }
    },
});
