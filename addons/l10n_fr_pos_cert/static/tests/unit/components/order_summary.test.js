import { test, expect } from "@odoo/hoot";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";

definePosModels();

test("don't show old unit price for discount orderline", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);

    const orderSummary = await mountWithCleanup(OrderSummary);
    const manualLine = order.lines[1];
    store.numpadMode = "price";
    orderSummary._setValue(4);

    const discountProduct = store.models["product.template"].get(14);
    store.config.discount_product_id = discountProduct;

    const discountLine = await store.addLineToOrder({ product_tmpl_id: discountProduct }, order);

    expect(orderSummary.showOldUnitPrice(manualLine)).toBe(true);
    expect(orderSummary.showOldUnitPrice(discountLine)).toBe(false);
});
