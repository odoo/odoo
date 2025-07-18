import { describe, expect, test } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { EventConfiguratorPopup } from "@pos_event/app/components/popup/event_configurator_popup/event_configurator_popup";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

describe("event_configurator_popup.js", () => {
    test("event_configurator_popup payload", async () => {
        const store = await setupPosEnv();
        const tickets = [store.models["event.event.ticket"].get(1)];
        const avaibilityByTicket = { 1: tickets[0].seats_available || "unlimited" };
        let payload = [];
        const comp = await mountWithCleanup(EventConfiguratorPopup, {
            props: {
                availabilityPerTicket: avaibilityByTicket,
                slotResult: {},
                tickets: tickets,
                getPayload: (data) => {
                    payload = data;
                },
                close: () => {},
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
});
