import { expect, test } from "@odoo/hoot";
import { EventConfiguratorPopup } from "@pos_event/app/components/popup/event_configurator_popup/event_configurator_popup";
import { mountPosDialog, setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("confirm payload and getTicketMaxQty and ticketIsAvailable", async () => {
    const store = await setupPosEnv();
    const tickets = [store.models["event.event.ticket"].get(1)];
    const avaibilityByTicket = { 1: tickets[0].seats_available || "unlimited" };
    let payload = [];

    const comp = await mountPosDialog(EventConfiguratorPopup, {
        availabilityPerTicket: avaibilityByTicket,
        slotResult: {},
        tickets: tickets,
        close: () => {},
        getPayload: (data) => {
            payload = data;
        },
    });

    expect(comp.getTicketMaxQty(tickets[0])).toBe(5);
    expect(comp.ticketIsAvailable(tickets[0])).toBe(true);

    comp.state[1] = { qty: 1 };
    comp.confirm();

    expect(payload).toHaveLength(1);
    expect(payload[0].qty).toBe(1);
    expect(payload[0].ticket_id).toEqual(tickets[0]);
    expect(payload[0].product_id).toEqual(tickets[0].product_id);
});
