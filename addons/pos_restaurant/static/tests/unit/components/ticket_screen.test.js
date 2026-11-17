import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

definePosModels();

test("setOrder does not select a table order being synced", async () => {
    const store = await setupPosEnv();
    const screen = await mountWithCleanup(TicketScreen);
    const table = store.models["restaurant.table"].get(2);
    const order = store.addNewOrder({ table_id: table });
    store.setOrder(null);

    store.syncingOrders.add(order.uuid);
    await screen.setOrder(order);
    expect(store.getOrder()).toBe(undefined);

    store.syncingOrders.delete(order.uuid);
    await screen.setOrder(order);
    expect(store.getOrder()).toBe(order);
});
