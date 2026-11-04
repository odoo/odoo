import { test, expect } from "@odoo/hoot";
import { makeOrder } from "@point_of_sale/../tests/unit/utils";
import { mountTicketScreen } from "@point_of_sale/../tests/unit/ticket_screen_utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

const { DateTime } = luxon;

definePosModels();

test("Active: oldest expected time first", async () => {
    const { store, screen } = await mountTicketScreen();
    const now = DateTime.now();

    const later = makeOrder(store, {
        pos_reference: "001",
        date_order: now.minus({ hours: 2 }),
        preset_time: now.plus({ hours: 1 }),
    });
    const late = makeOrder(store, { pos_reference: "002", date_order: now.minus({ hours: 1 }) });
    const sameTime2 = makeOrder(store, { pos_reference: "004", date_order: now });
    const sameTime1 = makeOrder(store, { pos_reference: "003", date_order: now });

    expect(screen.list.localOrders()).toEqual([late, sameTime1, sameTime2, later], {
        message: "preset time if any, else order date; then reference",
    });
});
