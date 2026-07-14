// Part of Odoo. See LICENSE file for full copyright and licensing details.
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.data.connectWebSocket("UPDATE_AVAILABLE_SEATS", (data) => {
            for (const ev of data) {
                const event = this.models["event.event"].get(ev.event_id);
                if (event) {
                    event.seats_available = ev.seats_available;
                } else {
                    continue;
                }

                for (const ticket of ev.event_ticket_ids) {
                    const eventTicket = this.models["event.event.ticket"].get(ticket.ticket_id);
                    if (eventTicket) {
                        eventTicket.seats_available = ticket.seats_available;
                    }
                }
            }
        });

        this.createDummyProductForEvents();
    },

    createDummyProductForEvents() {
        for (const event of this.models["event.event"].getAll()) {
            const eventTicketWithProduct = event.event_ticket_ids.filter(
                (ticket) => ticket.product_id
            );

            if (!eventTicketWithProduct.length) {
                continue;
            }

            const lowestPrice = eventTicketWithProduct.sort((a, b) => a.price - b.price)[0];
            const categIds = eventTicketWithProduct.flatMap(
                (ticket) => ticket.product_id.pos_categ_ids
            );
            const taxeIds = eventTicketWithProduct.flatMap((ticket) => ticket.product_id.taxes_id);
            this.models["product.product"].create({
                id: `dummy_${event.id}`,
                available_in_pos: true,
                lst_price: lowestPrice.price,
                display_name: event.name,
                pos_categ_ids: categIds.map((categ) => ["link", categ]),
                taxes_id: taxeIds.map((tax) => ["link", tax]),
                _event_id: event.id,
            });
        }
    },
});
