import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "../utils";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

test("_getProductByBarcode", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();
    const order = store.getOrder();
    const comp = await mountWithCleanup(ProductScreen, { props: { orderUuid: order.uuid } });
    await comp.addProductToOrder(store.models["product.template"].get(5));

    expect(order.displayPrice).toBe(3.45);
    expect(comp.total).toBe("$\u00a03.45");
    expect(comp.items).toBe("1");

    const productByBarcode = await comp._getProductByBarcode({ base_code: "test_test" });
    expect(productByBarcode.id).toEqual(5);
});

test("fastValidate", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();
    const order = store.getOrder();
    const fastPaymentMethod = order.config.fast_payment_method_ids[0];
    const productScreen = await mountWithCleanup(ProductScreen, {
        props: { orderUuid: order.uuid },
    });
    await productScreen.addProductToOrder(store.models["product.template"].get(5));

    expect(order.displayPrice).toBe(3.45);
    expect(productScreen.total).toBe("$\u00a03.45");
    expect(productScreen.items).toBe("1");

    await productScreen.fastValidate(fastPaymentMethod);

    expect(order.payment_ids[0].payment_method_id).toEqual(fastPaymentMethod);
    expect(order.state).toBe("paid");
    expect(order.amount_paid).toBe(3.45);
});

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
    let discountLine = order.getSelectedOrderline();
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
