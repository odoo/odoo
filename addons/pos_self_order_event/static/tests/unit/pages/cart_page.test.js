import { test, describe, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { CartPage } from "@pos_self_order/app/pages/cart_page/cart_page";
import { setupSelfPosEnv, getFilledSelfOrder } from "@pos_self_order/../tests/unit/utils";
import { definePosSelfModels } from "@pos_self_order/../tests/unit/data/generate_model_definitions";

definePosSelfModels();

describe("cart_page", () => {
    test("changeQuantity", async () => {
        const store = await setupSelfPosEnv();
        const order = await getFilledSelfOrder(store);
        const comp = await mountWithCleanup(CartPage, {});

        const line = order.lines[1];
        line.event_ticket_id = 1;
        expect(order.lines).toHaveLength(2);
        expect(line.qty).toBe(2);
        comp.changeQuantity(line, false);
        expect(line.qty).toBe(2);

        line.event_ticket_id = undefined;
        comp.changeQuantity(line, false);
        expect(line.qty).toBe(1);
        comp.changeQuantity(line, false);
        expect(order.lines).toHaveLength(1);
    });
});
