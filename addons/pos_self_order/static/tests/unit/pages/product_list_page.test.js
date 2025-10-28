import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ProductListPage } from "@pos_self_order/app/pages/product_list_page/product_list_page";
import { setupSelfPosEnv } from "../utils";
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

    // unavailable Product
    const unavailableProduct = models["product.template"].get(6);
    unavailableProduct.self_order_available = false;
    comp.selectProduct(unavailableProduct);
    expect(store.currentOrder.lines).toHaveLength(1);

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
