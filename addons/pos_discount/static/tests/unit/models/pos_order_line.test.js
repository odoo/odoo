import { expect, test } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { applyDiscount } from "../utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("isDiscountLine", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const product1 = store.models["product.template"].get(5);
    await store.addLineToOrder(
        {
            product_tmpl_id: product1,
            qty: 1,
        },
        order
    );
    await applyDiscount(10);
    const orderline = order.getSelectedOrderline();
    expect(Math.abs(orderline.price_subtotal_incl).toString()).toBe(
        ((order.amount_total + order.amount_tax) * 0.1).toPrecision(2)
    );
    expect(orderline.isDiscountLine).toBe(true);
});
