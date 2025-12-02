import { expect, test } from "@odoo/hoot";
import { EventRegistrationPopup } from "@pos_event/app/components/popup/event_registration_popup/event_registration_popup";
import { mountPosDialog, setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("confirm payload", async () => {
    const store = await setupPosEnv();
    const event = store.models["event.event"].get(1);
    const tickets = [store.models["event.event.ticket"].get(1)];
    let payload = [];
    const data = [
        {
            qty: 1,
            ticket_id: tickets[0],
            product_id: tickets[0].product_id,
        },
    ];
    const comp = await mountPosDialog(EventRegistrationPopup, {
        event: event,
        data: data,
        getPayload: (data) => {
            payload = data;
        },
        close: () => {},
    });

    comp.state.byRegistration[0].questions = {
        1: "Test User",
        2: "test@test.com",
        3: "+911234567890",
        4: "1",
    };
    comp.confirm();

    const receivedValues = Object.values(payload.byRegistration[1][0]);
    expect(payload.byRegistration).toHaveLength(1);
    expect(parseInt(Object.keys(payload.byRegistration)[0])).toBe(tickets[0].id);
    expect(receivedValues).toEqual([
        "Test User",
        "test@test.com",
        "+911234567890",
        "1", // Received value is the ID of the answer `Male`, not the name.
    ]);
});

test("autofill first ticket with customer data", async () => {
    const store = await setupPosEnv();
    const partner = store.models["res.partner"].get(18);
    partner.email = "john@example.com";
    partner.phone = "+1234567890";
    partner.parent_name = "Don";

    const order = store.addNewOrder();
    order.partner_id = partner;

    const event = store.models["event.event"].get(1);
    const ticket = store.models["event.event.ticket"].get(1);
    const data = [{ qty: 2, ticket_id: ticket, product_id: ticket.product_id }];

    const comp = await mountPosDialog(EventRegistrationPopup, {
        event,
        data,
        getPayload: () => {},
        close: () => {},
    });

    const [first, second] = comp.state.byRegistration.map((r) => r.questions);

    expect(Object.values(first)).toEqual([
        "Public user",
        "john@example.com",
        "+1234567890",
        "",
        "Don",
    ]);
    expect(Object.values(second)).toEqual(["", "", "", "", ""]);
});
