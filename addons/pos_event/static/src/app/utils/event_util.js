export function updateSeats(models, data) {
    for (const ev of data) {
        const event = models["event.event"].get(ev.event_id);
        if (!event) {
            continue;
        }

        event.seats_available = ev.seats_available;

        for (const ticket of ev.event_ticket_ids) {
            const eventTicket = models["event.event.ticket"].get(ticket.ticket_id);
            if (eventTicket) {
                eventTicket.seats_available = ticket.seats_available;
            }
        }

        for (const slot of ev.event_slot_ids) {
            const eventSlot = models["event.slot"].get(slot.slot_id);
            if (eventSlot) {
                eventSlot.seats_available = slot.seats_available;
            }
        }
    }
}

export function createDummyProductForEvents(models) {
    const eventProducts = [];
    for (const event of models["event.event"].getAll()) {
        const eventTicketWithProduct = event.event_ticket_ids.filter((ticket) => ticket.product_id);
        if (!eventTicketWithProduct.length) {
            continue;
        }

        const categIds = eventTicketWithProduct.flatMap(
            (ticket) => ticket.product_id.pos_categ_ids
        );
        const taxeIds = eventTicketWithProduct.flatMap((ticket) => ticket.product_id.taxes_id);

        const product = models["product.template"].create({
            id: `dummy_${event.id}`,
            available_in_pos: true,
            display_name: event.name,
            name: event.name,
            pos_categ_ids: categIds.map((categ) => ["link", categ]),
            taxes_id: taxeIds.map((tax) => ["link", tax]),
            _event_id: event.id,
        });

        // Disable original ticket products
        for (const ticket of event.event_ticket_ids) {
            const productTmpl = ticket.product_id?.product_tmpl_id;
            if (productTmpl) {
                productTmpl.available_in_pos = false;
            }
        }
        eventProducts.push(product);
    }
    return eventProducts;
}
