import { test, expect } from "@odoo/hoot";
import { MockServer, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { definePosStockModels } from "../data/generate_model_definitions";

const { DateTime } = luxon;

definePosStockModels();

test("Paid orders to pick up today are listed first, even when not on the first page", async () => {
    const store = await setupPosEnv();
    store.config.ship_later = true;
    // Only on the server: the mock search_order_ids returns an empty first page.
    const duePickupId = MockServer.env["pos.order"].create({
        config_id: store.config.id,
        session_id: store.session.id,
        state: "paid",
        date_order: DateTime.now().minus({ days: 3 }).toSQL({ includeOffset: false }),
        pickup_later: true,
        shipping_date: DateTime.now().toISODate(),
    });
    const pastPickup = store.addNewOrder();
    Object.assign(pastPickup, {
        state: "paid",
        pickup_later: true,
        shipping_date: DateTime.now().minus({ days: 1 }),
    });

    const ticketScreen = await mountWithCleanup(TicketScreen);
    await ticketScreen.onFilterSelected("SYNCED");
    expect(ticketScreen.getFilteredOrderList().map((o) => o.id)).toEqual([
        duePickupId,
        pastPickup.id,
    ]);
});
