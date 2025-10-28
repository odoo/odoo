import { expect, test } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { applyDiscount } from "../utils";

definePosModels();

test("getNumpadButtons", async () => {
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
    const productScreen = await mountWithCleanup(ProductScreen, {
        props: { orderUuid: order.uuid },
    });
    await applyDiscount(10);
    const receivedButtonsDisableStatue = productScreen
        .getNumpadButtons()
        .filter((button) => ["quantity", "discount"].includes(button.value))
        .map((button) => button.disabled);
    const orderline = order.getSelectedOrderline();
    expect(Math.abs(orderline.price_subtotal_incl).toString()).toBe(
        ((order.amount_total + order.amount_tax) * 0.1).toPrecision(2)
    );
    expect(receivedButtonsDisableStatue).toEqual([true, true]);
});
