import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosStockModels } from "@pos_stock/../tests/unit/data/generate_model_definitions";

definePosStockModels();

test("setShippingDate and getShippingDate with Luxon", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const testDate = "2019-03-11";
    order.shipping_date = testDate;

    expect(order.shipping_date.toISODate()).toBe(testDate);
    order.shipping_date = null;
    expect(order.shipping_date).toBeEmpty();
});
