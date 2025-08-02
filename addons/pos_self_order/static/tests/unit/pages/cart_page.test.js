import { test, describe, expect, beforeEach } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { CartPage } from "@pos_self_order/app/pages/cart_page/cart_page";
import { setupSelfPosEnv, patchSession, getFilledSelfOrder } from "../utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();
beforeEach(patchSession);

describe("cart_page", () => {
    test("removeLine", async () => {
        const store = await setupSelfPosEnv();
        const order = await getFilledSelfOrder(store);
        const [line1, line2] = order.lines;

        const comp = await mountWithCleanup(CartPage, {});

        comp.removeLine(line1);
        expect(order.lines).toHaveLength(1);

        // decrease the qty of line2 by 1
        comp.changeQuantity(line2, false);
        expect(line2.qty).toBe(1);

        // again decrease the qty of line2, should trigger removeLine
        comp.changeQuantity(line2, false);
        expect(order.lines).toHaveLength(0);
    });

    test("pay", async () => {
        const store = await setupSelfPosEnv();
        const order = await getFilledSelfOrder(store);

        const comp = await mountWithCleanup(CartPage, {});

        await comp.pay();
        expect(order.id).toBeOfType("number");
        expect(order.lines).toHaveLength(2);
        expect(order.lines[0].id).toBeOfType("number");
        expect(order.lines[1].id).toBeOfType("number");
    });
});
