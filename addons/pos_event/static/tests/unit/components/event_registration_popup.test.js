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
