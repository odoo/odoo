import { test, expect } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("showSubPads", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const ticketScreen = await mountWithCleanup(TicketScreen);

    const admin = store.models["hr.employee"].get(2);
    const restrictiveEmp = store.models["hr.employee"].get(4);

    order.state = "paid";
    ticketScreen.onClickOrder(order);
    store.accessRight.setCashier(admin);
    await animationFrame();
    expect(store.accessRight.canShowPads).toBe(true);
    store.accessRight.setCashier(restrictiveEmp);
    ticketScreen.onClickOrder(order);
    await animationFrame();
    expect(store.accessRight.canShowPads).toBe(false);
});
