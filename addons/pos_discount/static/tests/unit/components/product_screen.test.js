import { expect, test } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

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
    await store.applyDiscount(10);
    const receivedButtonsDisableStatue = productScreen
        .getNumpadButtons()
        .filter((button) => ["quantity", "discount"].includes(button.value))
        .map((button) => button.disabled);
    let discountLine = order.getDiscountLine();
    expect(Math.abs(discountLine.priceIncl).toString()).toBe(
        (order.lines[0].priceIncl * 0.1).toPrecision(2)
    );
    expect(receivedButtonsDisableStatue).toEqual([true, true]);

    await productScreen.addProductToOrder(product1);
    discountLine = order.getDiscountLine();

    expect(Math.abs(discountLine.priceIncl).toString()).toBe(
        (order.lines[0].priceIncl * 0.1).toPrecision(2)
    );
});
