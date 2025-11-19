import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("_onUpdateSelectedOrderline: refund skips discount line", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const discountProduct = store.models["product.template"].get(151);

    const line1 = await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(5),
        qty: 3,
    });
    await store.addLineToCurrentOrder({
        product_tmpl_id: discountProduct,
    });
    const line2 = await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(6),
    });
    order.state = "paid";

    const ticketScreen = await mountWithCleanup(TicketScreen);
    ticketScreen.onClickOrder(order);

    expect(ticketScreen.getSelectedOrderlineId()).toBe(line1.id);
    ticketScreen._onUpdateSelectedOrderline({
        key: "Enter",
        buffer: "3",
    });
    expect(ticketScreen.getSelectedOrderlineId()).toBe(line2.id);
});
