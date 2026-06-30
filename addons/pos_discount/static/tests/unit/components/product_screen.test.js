import { animationFrame, expect, test } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv, expectFormattedPrice } from "@point_of_sale/../tests/unit/utils";
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
    await animationFrame();
    const receivedButtonsDisableStatue = productScreen
        .getNumpadButtons()
        .filter((button) => ["quantity", "discount"].includes(button.value))
        .map((button) => button.disabled);
    expect(Math.abs(order.discountLines[0].priceIncl).toString()).toBe(
        (order.lines[0].priceIncl * 0.1).toPrecision(2)
    );

    expect(receivedButtonsDisableStatue).toEqual([true, true]);

    await productScreen.addProductToOrder(product1);
    // Animation frame doesn't work here since the debounced function used to recompute
    // discount is using eventListener, so we use setTimeout instead.
    setTimeout(() => {
        expect(Math.abs(order.discountLines[0].priceIncl).toString()).toBe(
            (order.lines[0].priceIncl * 0.1).toPrecision(2)
        );
    }, 100);
});

test("addProductToOrder reapplies the global discount", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const product = store.models["product.template"].get(5);
    const productScreen = await mountWithCleanup(ProductScreen, {
        props: { orderUuid: order.uuid },
    });

    await productScreen.addProductToOrder(product);
    expectFormattedPrice(productScreen.total, "$ 3.45");
    expect(order.priceIncl).toBe(3.45);
    expect(order.priceExcl).toBe(3);
    expect(order.amountTaxes).toBe(0.45);

    await store.applyDiscount(10);
    expectFormattedPrice(productScreen.total, "$ 3.10");
    expect(order.priceIncl).toBe(3.1);
    expect(order.priceExcl).toBe(2.7);
    expect(order.amountTaxes).toBe(0.4);

    await productScreen.addProductToOrder(product);
    await animationFrame();
    expectFormattedPrice(productScreen.total, "$ 6.21");
    expect(order.priceIncl).toBeCloseTo(6.21, { margin: 1e-12 });
    expect(order.priceExcl).toBe(5.4);
    expect(order.amountTaxes).toBe(0.81);
});
