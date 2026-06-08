import { expect, test } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("test_selling_multiple_ticket_saved: event ticket lines only merge for the same ticket", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const product = store.models["product.template"].get(108);
    const ticket = store.models["event.event.ticket"].get(1);
    const otherTicket = store.models["event.event.ticket"].get(5);

    const line = await store.addLineToOrder(
        { product_tmpl_id: product, event_ticket_id: ticket },
        order,
        {},
        false
    );
    const sameTicketLine = await store.addLineToOrder(
        { product_tmpl_id: product, event_ticket_id: ticket },
        order,
        {},
        false
    );
    const otherTicketLine = await store.addLineToOrder(
        { product_tmpl_id: product, event_ticket_id: otherTicket },
        order,
        {},
        false
    );

    expect(line.canBeMergedWith(sameTicketLine)).toBe(true);
    expect(line.canBeMergedWith(otherTicketLine)).toBe(false);
});

test("test_selling_multiple_ticket_saved: event ticket quantities cannot be changed and removing clears registrations", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const product = store.models["product.template"].get(108);
    const ticket = store.models["event.event.ticket"].get(1);
    const line = await store.addLineToOrder(
        { product_tmpl_id: product, event_ticket_id: ticket },
        order,
        {},
        false
    );

    const registration = store.models["event.registration"].create({
        event_id: ticket.event_id,
        event_ticket_id: ticket,
        pos_order_line_id: line,
    });

    expect(line.setQuantity(2)).toEqual({
        title: "Ticket error",
        body: "You cannot change quantity for a line linked with an event registration",
    });

    line.setQuantity("");

    expect(line.event_registration_ids).toHaveLength(0);
    expect(store.models["event.registration"].get(registration.id)).toBeEmpty();
});
