import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ProductListPage } from "@pos_self_order/app/pages/product_list_page/product_list_page";
import { setupSelfPosEnv } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";

definePosSelfModels();

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
