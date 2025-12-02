import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { OrderWidget } from "@pos_self_order/app/components/order_widget/order_widget";
import { setupSelfPosEnv, getFilledSelfOrder } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";

definePosSelfModels();

test("buttonToShow", async () => {
    const store = await setupSelfPosEnv();
    const models = store.models;
    const comp = await mountWithCleanup(OrderWidget, { props: { action: () => {} } });

    store.router.activeSlot = "product_list";
    expect(comp.buttonToShow).toMatchObject({ label: "Checkout", disabled: true });

    await getFilledSelfOrder(store);
    expect(comp.buttonToShow).toMatchObject({ label: "Checkout", disabled: false });

    store.router.activeSlot = "cart";
    expect(comp.buttonToShow).toMatchObject({ label: "Order", disabled: false });
    // With valid payment method
    models["pos.payment.method"].getFirst().use_payment_terminal = "stripe";
    expect(comp.buttonToShow).toMatchObject({ label: "Pay", disabled: false });
});

test("lineNotSend", async () => {
    const store = await setupSelfPosEnv();
    const comp = await mountWithCleanup(OrderWidget, { props: { action: () => {} } });

    expect(comp.lineNotSend).toMatchObject({ price: 0, count: 0 });
    await getFilledSelfOrder(store);
    expect(comp.lineNotSend).toMatchObject({ price: 595, count: 5 });

    const product1 = store.models["product.template"].get(5);
    await store.addToCart(product1, 1);
    expect(comp.lineNotSend).toMatchObject({ price: 710, count: 6 });
});

test("shouldGoBack", async () => {
    const store = await setupSelfPosEnv();
    const comp = await mountWithCleanup(OrderWidget, { props: { action: () => {} } });

    // No orderlines
    expect(comp.shouldGoBack()).toBe(true);
    await getFilledSelfOrder(store);
    expect(comp.shouldGoBack()).toBe(false);

    await store.sendDraftOrderToServer();
    expect(comp.shouldGoBack()).toBe(true);

    const product5 = store.models["product.template"].get(5);
    store.addToCart(product5, 2, "");
    expect(comp.shouldGoBack()).toBe(false);

    store.router.activeSlot = "cart";
    expect(comp.shouldGoBack()).toBe(true);
});
