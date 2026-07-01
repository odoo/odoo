import { test, expect } from "@odoo/hoot";
import { queryFirst, animationFrame } from "@odoo/hoot-dom";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { CartPage } from "@pos_self_order/app/pages/cart_page/cart_page";
import { setupSelfPosEnv, getFilledSelfOrder, addComboProduct } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";
import { ChooseComboPopup } from "@pos_self_order/app/components/choose_combo_popup/choose_combo_popup";

definePosSelfModels();

test("removeLine", async () => {
    const store = await setupSelfPosEnv();
    const order = await getFilledSelfOrder(store);
    const line = order.lines[0];
    const comp = await mountWithCleanup(CartPage, {});

    expect(order.lines).toHaveLength(2);
    comp.removeLine(line);
    expect(order.lines).toHaveLength(1);
});

test("changeQuantity", async () => {
    const store = await setupSelfPosEnv();
    const order = await getFilledSelfOrder(store);
    const line = order.lines[1];
    const comp = await mountWithCleanup(CartPage, {});

    expect(order.lines).toHaveLength(2);
    // decrease the qty of line by 1
    comp.changeQuantity(line, false);
    expect(line.qty).toBe(1);
    // decrease the qty of line again, should trigger removeLine
    comp.changeQuantity(line, false);
    expect(order.lines).toHaveLength(1);
});

test("pay", async () => {
    const store = await setupSelfPosEnv();
    const order = await getFilledSelfOrder(store);
    const comp = await mountWithCleanup(CartPage, {});

    await comp.pay();
    expect(order.id).toBeOfType("number");
    expect(order.lines).toHaveLength(2);
    expect(order.lines[0].id).toBeOfType("number");
});

test("canChangeQuantity", async () => {
    const store = await setupSelfPosEnv();
    const order = await getFilledSelfOrder(store);
    const line = order.lines[0];
    const comp = await mountWithCleanup(CartPage, {});

    expect(comp.canChangeQuantity(line)).toBe(true);
    await comp.pay();
    expect(comp.canChangeQuantity(line)).toBe(false);
});

test("totalPriceAndTax", async () => {
    const store = await setupSelfPosEnv("mobile", "table", "meal");
    await getFilledSelfOrder(store);
    const comp = await mountWithCleanup(CartPage, {});
    await animationFrame();

    expect(comp.totalPriceAndTax).toEqual({ priceWithTax: 595, tax: 95 });
    store.cancelOrder();
    await store.addToCart(store.models["product.template"].get(6), 2);
    expect(comp.totalPriceAndTax).toEqual({ priceWithTax: 250, tax: 50 });
});

test("getPrice", async () => {
    const store = await setupSelfPosEnv();
    const order = await getFilledSelfOrder(store);
    const [line1, line2] = order.lines;
    const comp = await mountWithCleanup(CartPage, {});

    expect(comp.getPrice(line1)).toBe(345);
    expect(comp.getPrice(line2)).toBe(250);

    // For combo parent line
    const parentLine = await addComboProduct(store);
    expect(comp.getPrice(parentLine)).toBe(500);
});

test("add note button is not shown in kiosk mode", async () => {
    const store = await setupSelfPosEnv("kiosk");
    await getFilledSelfOrder(store);
    await mountWithCleanup(CartPage, {});

    const orderNoteContainer = queryFirst(".order-note");
    expect(orderNoteContainer).toBe(null);
});

test("pay opens combo suggestion popup and applies a direct combo", async () => {
    const store = await setupSelfPosEnv();
    const combo1 = store.models["product.combo"].get(1);

    combo1.is_upsell = false;
    combo1.qty_free = combo1.qty_max = 1;

    await store.addToCart(store.models["product.template"].get(8), 1);
    await store.addToCart(store.models["product.template"].get(10), 1);
    const comboProduct = store.models["product.template"].get(7);

    const normalLines = store.currentOrder.lines.filter((line) => !line.combo_parent_id);
    expect(normalLines).toHaveLength(2);

    const comp = await mountWithCleanup(CartPage, {});
    patchWithCleanup(store, {
        async confirmOrder() {},
    });

    patchWithCleanup(comp.dialog, {
        add(component, props) {
            expect(component).toBe(ChooseComboPopup);
            props.getPayload(props.potentialCombos[0]);
        },
    });

    await comp.pay();

    const ComboProductLines = store.currentOrder.lines.filter((line) => !line.combo_parent_id);
    expect(ComboProductLines).toHaveLength(1);
    expect(ComboProductLines[0].product_id.product_tmpl_id.id).toBe(comboProduct.id);
    expect(ComboProductLines[0].combo_line_ids).toHaveLength(2);
    expect(store.pendingComboConversion).toBe(null);
});

test("pay opens combo suggestion popup and applies repeated single-free combos", async () => {
    const store = await setupSelfPosEnv();
    const combo1 = store.models["product.combo"].get(1);

    combo1.is_upsell = false;
    combo1.qty_free = combo1.qty_max = 1;

    await store.addToCart(store.models["product.template"].get(8), 2);
    await store.addToCart(store.models["product.template"].get(10), 2);
    const comboProduct = store.models["product.template"].get(7);

    const comp = await mountWithCleanup(CartPage, {});
    patchWithCleanup(store, {
        async confirmOrder() {},
    });

    patchWithCleanup(comp.dialog, {
        add(component, props) {
            expect(component).toBe(ChooseComboPopup);
            props.getPayload(props.potentialCombos[1]);
        },
    });

    await comp.pay();
    await animationFrame();

    const comboProductLines = store.currentOrder.lines.filter((line) => !line.combo_parent_id);
    expect(comboProductLines).toHaveLength(2);
    expect(
        comboProductLines.every((line) => line.product_id.product_tmpl_id.id === comboProduct.id)
    ).toBe(true);
    expect(comboProductLines.map((line) => line.qty)).toEqual([1, 1]);
    expect(comboProductLines.map((line) => line.combo_line_ids.length)).toEqual([2, 2]);
    expect(store.pendingComboConversion).toBe(null);
});

test("pay opens combo suggestion popup and redirects upsell combos to combo selection", async () => {
    const store = await setupSelfPosEnv();
    await store.addToCart(store.models["product.template"].get(8), 1);
    await store.addToCart(store.models["product.template"].get(10), 1);
    const comboProduct = store.models["product.product"].get(7);

    const comp = await mountWithCleanup(CartPage, {});

    patchWithCleanup(comp.dialog, {
        add(component, props) {
            expect(component).toBe(ChooseComboPopup);
            props.getPayload(props.potentialCombos[0]);
        },
    });
    patchWithCleanup(comp.router, {
        navigate(route, params, options) {
            expect.step(`${route}:${params.id}:${options.redirectPage}`);
        },
    });

    expect(
        store.comboSuggestion
            .getPotentialCombos(store.currentOrder)
            .filter((combo) => combo.totalComboPrice <= combo.totalSplitedComboLinePrice)[0].product
            .id
    ).toBe(comboProduct.id);

    await comp.pay();
    await animationFrame();
    expect.verifySteps(["combo_selection:7:cart"]);
});

test("getBackButton", async () => {
    await setupSelfPosEnv();
    const comp = await mountWithCleanup(CartPage, {});

    const backButton = comp.getBackButton();
    const expected = {
        position: "left",
        label: "Back",
        icon: "oi oi-chevron-left",
        severity: "secondary",
        extraClasses: "btn-back",
    };

    expect(backButton).toMatchObject(expected);
});

test("getPresetButton", async () => {
    const store = await setupSelfPosEnv();
    const order = await getFilledSelfOrder(store);
    const comp = await mountWithCleanup(CartPage, {});

    const inPreset = store.models["pos.preset"].get(1);
    store.config.self_ordering_pay_after = "each";
    store.config.use_presets = true;
    order.preset_id = inPreset;

    const expected = {
        position: "right",
        label: "In",
        severity: "secondary",
        extraClasses: "preset-btn",
    };

    // Classic
    expect(comp.getPresetButton()).toMatchObject(expected);

    // Do not use presets
    store.config.use_presets = false;
    expect(comp.getPresetButton()).toBe(null);

    // No preset selected
    store.config.use_presets = true;
    order.preset_id = false;
    expect(comp.getPresetButton()).toBe(null);

    // Pay after meal, not already ordered
    order.preset_id = inPreset;
    store.config.self_ordering_pay_after = "meal";
    expect(comp.getPresetButton()).toMatchObject(expected);

    // Pay after meal, already ordered
    await comp.pay(); // --> Clear `order.uiState.lineChanges`
    expect(comp.getPresetButton()).toBe(null);

    // Pay after each, no unsent lines
    store.config.self_ordering_pay_after = "each";
    expect(comp.getPresetButton()).toBe(null);
});

test("getPayButton", async () => {
    const store = await setupSelfPosEnv();
    const order = await getFilledSelfOrder(store);
    const comp = await mountWithCleanup(CartPage, {});

    const expected = {
        position: "right",
        severity: "primary",
        extraClasses: "cart",
    };

    // Meal - checkout with changes
    store.hasPaymentMethod = () => true;
    store.config.self_ordering_pay_after = "meal";
    expect(comp.getPayButton()).toMatchObject({ ...expected, label: "Order", disabled: false });

    // Meal - from landing
    history.pushState({ fromLanding: true }, "");
    expect(comp.getPayButton()).toMatchObject({ ...expected, label: "Pay" });

    // Meal - no payment method
    store.hasPaymentMethod = () => false;
    expect(comp.getPayButton()).toBe(null);

    // Each - payment method available
    store.config.self_ordering_pay_after = "each";
    store.hasPaymentMethod = () => true;
    expect(comp.getPayButton()).toMatchObject({ ...expected, label: "Pay" });

    // Each - no payment method with unsent lines
    store.hasPaymentMethod = () => false;
    expect(comp.getPayButton()).toMatchObject({ ...expected, label: "Order" });

    // Each - no payment method without unsent lines
    const save = order.lines;
    order.lines = [];
    expect(comp.getPayButton()).toBe(null);
    order.lines = save;

    // Meal - checkout without changes
    store.config.self_ordering_pay_after = "meal";
    history.pushState({ fromLanding: true }, "");
    store.hasPaymentMethod = () => true;
    expect(comp.getPayButton()).toMatchObject({ ...expected, label: "Pay" });
});

test("orderWidgetProps", async () => {
    await setupSelfPosEnv();
    const comp = await mountWithCleanup(CartPage, {});

    comp.getBackButton = () => ({ label: "Back" });
    comp.getPresetButton = () => ({ label: "Preset" });
    comp.getPayButton = () => ({ label: "Pay" });

    expect(comp.orderWidgetProps).toMatchObject({
        removeTopClasses: true,
        buttons: [{ label: "Back" }, { label: "Preset" }, { label: "Pay" }],
    });

    comp.getPresetButton = () => null;
    expect(comp.orderWidgetProps).toMatchObject({
        removeTopClasses: true,
        buttons: [{ label: "Back" }, { label: "Pay" }],
    });
});

test("getLineDisplayQty", async () => {
    const store = await setupSelfPosEnv();
    const order = await getFilledSelfOrder(store);
    const line = order.lines[0];
    const comp = await mountWithCleanup(CartPage, {});

    comp.getLineChangeQty = () => 10;
    expect(comp.getLineDisplayQty(line)).toBe(10);

    comp.getLineChangeQty = () => false;
    expect(comp.getLineDisplayQty(line)).toBe(line.qty);

    history.pushState({ fromLanding: true }, "");
    order.uiState.lineChanges[line.uuid] = { qty: 10 };
    expect(comp.getLineDisplayQty(line)).toBe(10);

    delete order.uiState.lineChanges[line.uuid];
    expect(comp.getLineDisplayQty(line)).toBe(line.qty);
});

test("lines", async () => {
    const store = await setupSelfPosEnv();
    const order = await getFilledSelfOrder(store);
    const comp = await mountWithCleanup(CartPage, {});
    const product12 = store.models["product.template"].get(12);

    store.config.self_ordering_pay_after = "meal";
    await comp.pay();
    await store.addToCart(product12, 4);

    const unsentLines = order.lines.filter((line) => line.product_id.id === 12);
    expect(comp.lines).toEqual(unsentLines);

    history.pushState({ fromLanding: true }, "");
    const sentLines = order.lines.filter((line) => line.product_id.id !== 12);
    expect(comp.lines).toEqual(sentLines);
});
