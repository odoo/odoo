import { test, expect } from "@odoo/hoot";
import { queryFirst, animationFrame } from "@odoo/hoot-dom";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ProductListPage } from "@pos_self_order/app/pages/product_list_page/product_list_page";
import { setupSelfPosEnv } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";
import { serializeDateTime } from "@web/core/l10n/dates";

const { DateTime } = luxon;
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

test("test_self_order_product_availability: selectProduct - snoozed product is not added", async () => {
    const store = await setupSelfPosEnv();
    const models = store.models;
    const product = models["product.template"].get(5);
    const now = DateTime.now();
    const snooze = models["pos.product.template.snooze"].create({
        product_template_id: product,
        pos_config_id: store.config,
        start_time: serializeDateTime(now),
        end_time: serializeDateTime(now.plus({ hours: 1 })),
    });
    store.snoozedProductTracker.setSnoozes([snooze]);
    const comp = await mountWithCleanup(ProductListPage, {});
    comp.flyToCart = () => {};
    await animationFrame();
    comp.selectProduct(product);
    expect(store.currentOrder.lines).toHaveLength(0);
    // Verify "Out of stock" badge is displayed in the DOM
    const snoozedArticle = queryFirst(".o_self_product_box .opacity-25");
    expect(snoozedArticle).not.toBe(null);
    expect(snoozedArticle.querySelector(".text-bg-danger").textContent).toInclude("Out of stock");
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
