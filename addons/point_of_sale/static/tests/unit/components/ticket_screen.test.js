import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "../utils";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("_onUpdateSelectedOrderline: refund moves to next", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const comboLine = await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(7),
        payload: [
            [
                { combo_item_id: store.models["product.combo.item"].get(1), qty: 1 },
                { combo_item_id: store.models["product.combo.item"].get(3), qty: 1 },
            ],
            [],
        ],
        configure: false,
    });
    const line2Refund = await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(8),
        qty: 2,
    });

    const line1 = await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(5),
        qty: 3,
    });
    const line2 = await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(6),
    });
    order.state = "paid";

    // refund `line2Refund`
    const refundedOrder = store.createNewOrder();
    const refundingLine = await store.addLineToOrder(
        { product_tmpl_id: store.models["product.template"].get(8), qty: -2 },
        refundedOrder
    );
    line2Refund.refund_orderline_ids = [refundingLine.id];
    refundedOrder.state = "paid";

    const ticketScreen = await mountWithCleanup(TicketScreen);
    ticketScreen.onClickOrder(order);
    expect(ticketScreen.getSelectedOrderlineId()).toBe(comboLine.id);
    ticketScreen._onUpdateSelectedOrderline({ key: "Enter", buffer: "1" });
    expect(ticketScreen.getSelectedOrderlineId()).toBe(line1.id);
    ticketScreen._onUpdateSelectedOrderline({ key: "Enter", buffer: "2" });
    expect(ticketScreen.getSelectedOrderlineId()).toBe(line1.id);
    ticketScreen._onUpdateSelectedOrderline({ key: "Enter", buffer: "3" });
    expect(ticketScreen.getSelectedOrderlineId()).toBe(line2.id);
});
