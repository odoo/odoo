import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("showSubPads", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const ticketScreen = await mountWithCleanup(TicketScreen);
    ticketScreen.onClickOrder(order);

    const admin = store.models["hr.employee"].get(2);
    store.setCashier(admin);
    expect(ticketScreen.showSubPads).toBe(false);
    const minimalEmp = store.models["hr.employee"].get(4);
    store.setCashier(minimalEmp);
    expect(ticketScreen.showSubPads).toBe(false);

    order.state = "paid";
    store.setCashier(admin);
    expect(ticketScreen.showSubPads).toBe(true);
    store.setCashier(minimalEmp);
    expect(ticketScreen.showSubPads).toBe(false);
});
