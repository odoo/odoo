import { test, expect, describe } from "@odoo/hoot";
import { getFilledOrder, setupPosEnv } from "../utils";

describe.current.tags("pos");
describe("pos_store.js", () => {
    test("getProductPrice", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        const product = store.models["product.template"].get(5);
        const price = store.getProductPrice(product);
        expect(price).toBe(3.45);
        order.setPricelist(null);

        const newPrice = store.getProductPrice(product);
        expect(newPrice).toBe(115.0);

        const formattedPrice = store.getProductPrice(product, false, true);
        expect(formattedPrice).toBe("$\u00a0115.00");
    });

    test("setTip", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store); // Should have 2 lines
        expect(order.lines.length).toBe(2);

        await store.setTip(50);
        expect(order.is_tipped).toBe(true);
        expect(order.tip_amount).toBe(50);
        expect(order.lines.length).toBe(3); // 2 original lines + 1 tip line
    });
});
