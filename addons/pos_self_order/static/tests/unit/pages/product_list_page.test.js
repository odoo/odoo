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

test("getBackButton", async () => {
    const store = await setupSelfPosEnv();
    const order = await getFilledSelfOrder(store);
    const comp = await mountWithCleanup(ProductListPage, {});

    expect(comp.getBackButton()).toBe(null);

    order.lines = [];
    expect(comp.getBackButton()).toMatchObject({
        position: "left",
        label: "Back",
        icon: "oi oi-chevron-left",
        severity: "secondary",
        extraClasses: "btn-back",
    });
});

test("getDiscardButton", async () => {
    await setupSelfPosEnv();
    const comp = await mountWithCleanup(ProductListPage, {});

    expect(comp.getDiscardButton()).toMatchObject({
        position: "left",
        label: "Discard",
        severity: "secondary",
        icon: "btn-close",
        extraClasses: "btn-cancel",
    });
});

test("getCheckoutButton", async () => {
    const store = await setupSelfPosEnv();
    const comp = await mountWithCleanup(ProductListPage, {});

    const expected = {
        position: "right",
        label: "Checkout",
        severity: "primary",
        extraClasses: "cart",
    };

    expect(comp.getCheckoutButton()).toMatchObject({ ...expected, disabled: true });
    await getFilledSelfOrder(store);
    expect(comp.getCheckoutButton()).toMatchObject({ ...expected, disabled: false });
});

test("getTotalProps", async () => {
    const store = await setupSelfPosEnv();
    await getFilledSelfOrder(store);
    const comp = await mountWithCleanup(ProductListPage, {});

    store.config.iface_tax_included = "total";
    expect(comp.getTotalProps()).toMatchObject({ count: 5, price: 595 });

    store.config.iface_tax_included = "subtotal";
    expect(comp.getTotalProps()).toMatchObject({ count: 5, price: 500 });
});

test("orderWidgetProps", async () => {
    await setupSelfPosEnv();
    const comp = await mountWithCleanup(ProductListPage, {});

    comp.getTotalProps = () => 100;
    comp.getBackButton = () => ({ label: "Back" });
    comp.getDiscardButton = () => ({ label: "Discard" });
    comp.getCheckoutButton = () => ({ label: "Checkout" });

    expect(comp.orderWidgetProps).toMatchObject({
        total: 100,
        buttons: [{ label: "Back" }, { label: "Checkout" }],
    });

    comp.getBackButton = () => null;
    comp.getCheckoutButton = () => null;
    expect(comp.orderWidgetProps).toMatchObject({
        total: 100,
        buttons: [{ label: "Discard" }],
    });
});
