import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ProductListPage } from "@pos_self_order/app/pages/product_list_page/product_list_page";
import { setupSelfPosEnv, getFilledSelfOrder } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";

definePosSelfModels();

test("selectProduct", async () => {
    const store = await setupSelfPosEnv();
    const models = store.models;
    const product = models["product.template"].get(5);
    const comp = await mountWithCleanup(ProductListPage, {});
    comp.flyToCart = () => {};

    comp.selectProduct(product);
    expect(store.currentOrder.lines).toHaveLength(1);
    expect(store.currentOrder.lines[0].product_id.id).toBe(5);

    // Combo Product
    const comboProduct = models["product.template"].get(7);
    comboProduct.combo_ids = [2];
    comp.selectProduct(comboProduct);
    // Should not add combo product to cart; should navigate to combo selection page
    expect(store.currentOrder.lines).toHaveLength(1);

    // Combo Product with one choice
    models["product.combo.item"].get(3).delete();
    comp.selectProduct(comboProduct);
    expect(store.currentOrder.lines).toHaveLength(3);
});

test("getSubCategories and selectCategory", async () => {
    const store = await setupSelfPosEnv();
    const models = store.models;
    expect(store.currentCategory).toBeEmpty();
    const comp = await mountWithCleanup(ProductListPage, {});

    expect(store.currentCategory.id).toBe(1);
    expect(comp.state.selectedCategory.id).toBe(1);
    expect(comp.getSubCategories()).toHaveLength(0);

    // If parent is category selected
    const foodCatg = models["pos.category"].get(3);
    comp.selectCategory(foodCatg);
    expect(comp.state.selectedCategory.id).toBe(3);
    expect(comp.getSubCategories()).toHaveLength(2);
    expect(comp.getSubCategories().map((c) => c.id)).toEqual([4, 5]);

    // If child-catg is category selected
    const pizzaCatg = models["pos.category"].get(5);
    comp.selectCategory(pizzaCatg);
    expect(comp.state.selectedCategory.id).toBe(5);
    expect(comp.getSubCategories()).toHaveLength(2);
    expect(comp.getSubCategories().map((c) => c.id)).toEqual([4, 5]);

    // for mobile mode
    store.config.self_ordering_mode = "mobile";
    expect(comp.getSubCategories()).toHaveLength(0);
});

test("showBackButton", async () => {
    const store = await setupSelfPosEnv();
    const order = await getFilledSelfOrder(store);
    const comp = await mountWithCleanup(ProductListPage, {});

    expect(comp.showBackButton).toBe(false);

    order.lines = [];
    expect(comp.showBackButton).toBe(true);
});

test("backTargetPage", async () => {
    const store = await setupSelfPosEnv();
    const order = await getFilledSelfOrder(store);
    const comp = await mountWithCleanup(ProductListPage, {});

    // No presets configured -> always default
    store.config.use_presets = false;
    expect(comp.backTargetPage).toBe("default");

    // Presets configured, none selected yet -> let the customer pick one
    store.config.use_presets = true;
    const inPreset = store.models["pos.preset"].get(1);
    order.preset_id = false;
    expect(comp.backTargetPage).toBe("location");

    // Pay after each, preset already selected, unsent items -> still let
    // them re-pick (presetButton stays available too in this mode)
    store.config.self_ordering_pay_after = "each";
    order.preset_id = inPreset;
    expect(comp.backTargetPage).toBe("location");

    // Pay after meal, preset selected, no round sent yet -> still let them
    // re-pick
    store.config.self_ordering_pay_after = "meal";
    expect(comp.backTargetPage).toBe("location");

    // Pay after meal, a round has already been sent -> lock the preset,
    // go to landing instead of back to location
    await store.sendDraftOrderToServer();
    expect(comp.backTargetPage).toBe("default");
});

test("checkoutDisabled", async () => {
    const store = await setupSelfPosEnv();
    const comp = await mountWithCleanup(ProductListPage, {});

    expect(comp.checkoutDisabled).toBe(true);
    await getFilledSelfOrder(store);
    expect(comp.checkoutDisabled).toBe(false);
});

test("total", async () => {
    const store = await setupSelfPosEnv();
    await getFilledSelfOrder(store);
    const comp = await mountWithCleanup(ProductListPage, {});

    store.config.iface_tax_included = "total";
    expect(comp.total).toMatchObject({ count: 5, price: 595 });

    store.config.iface_tax_included = "subtotal";
    expect(comp.total).toMatchObject({ count: 5, price: 500 });
});

test("OrderWidget renders the Discard button when there are pending changes", async () => {
    const store = await setupSelfPosEnv();
    await getFilledSelfOrder(store);
    await mountWithCleanup(ProductListPage, {});

    // With pending changes, the left slot shows Discard, not Back
    expect(".btn-cancel").toHaveCount(1);
    expect(".btn-back").toHaveCount(0);
    expect(".cart").toHaveText("Checkout");
});

test("OrderWidget renders the Back button when there are no pending changes", async () => {
    const store = await setupSelfPosEnv();
    const order = await getFilledSelfOrder(store);
    order.lines = [];
    await mountWithCleanup(ProductListPage, {});

    expect(".btn-back").toHaveCount(1);
    expect(".btn-cancel").toHaveCount(0);
});
