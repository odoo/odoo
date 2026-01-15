import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ProductPage } from "@pos_self_order/app/pages/product_page/product_page";
import { setupSelfPosEnv } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";

definePosSelfModels();

test("changeQuantity and isProductAvailable", async () => {
    const store = await setupSelfPosEnv();
    const models = store.models;
    const product = models["product.template"].get(5);
    const comp = await mountWithCleanup(ProductPage, { props: { productTemplate: product } });

    expect(comp.state.qty).toBe(1);
    expect(comp.isProductAvailable()).toBe(true);

    comp.changeQuantity(true);
    expect(comp.state.qty).toBe(2);
    comp.changeQuantity(false);
    expect(comp.state.qty).toBe(1);
    // Quantity should not decrease below 1
    comp.changeQuantity(false);
    expect(comp.state.qty).toBe(1);
});

test("getProductPrice", async () => {
    const store = await setupSelfPosEnv();
    const models = store.models;
    const product = models["product.template"].get(5);
    const comp = await mountWithCleanup(ProductPage, { props: { productTemplate: product } });

    expect(comp.getProductPrice()).toBe(115);
    comp.state.qty = 4;
    expect(comp.getProductPrice()).toBe(460);

    store.config.iface_tax_included = "subtotal";
    comp.state.qty = 1;
    expect(comp.getProductPrice()).toBe(100);
    comp.state.qty = 4;
    expect(comp.getProductPrice()).toBe(400);
});

test("isAddToCartEnabled", async () => {
    const store = await setupSelfPosEnv();
    const models = store.models;
    const product = models["product.template"].get(5);
    const comp = await mountWithCleanup(ProductPage, { props: { productTemplate: product } });

    // Product unavailability
    product.self_order_available = false;
    expect(comp.isAddToCartEnabled()).toBe(false);
});
