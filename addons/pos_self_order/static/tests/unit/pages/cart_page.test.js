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

test("isCheckout", async () => {
    const store = await setupSelfPosEnv();
    await getFilledSelfOrder(store);
    const comp = await mountWithCleanup(CartPage, {});

    expect(comp.isCheckout).toBe(true);

    history.pushState({ fromLanding: true }, "");
    expect(comp.isCheckout).toBe(false);

    history.pushState(null, "");
    expect(comp.isCheckout).toBe(true);
});

test("totalPriceAndTax", async () => {
    const store = await setupSelfPosEnv("mobile", "table", "meal");
    await getFilledSelfOrder(store);
    const comp = await mountWithCleanup(CartPage, {});
    await animationFrame();

    expect(comp.totalPriceAndTax).toEqual({ priceWithTax: 595, tax: 95 });

    await comp.pay();
    await store.addToCart(store.models["product.template"].get(6), 2);
    expect(comp.totalPriceAndTax).toEqual({ priceWithTax: 250, tax: 50 });

    history.pushState({ fromLanding: true }, "");
    expect(comp.totalPriceAndTax).toEqual({ priceWithTax: 595, tax: 95 });
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

test("onClickBack", async () => {
    const store = await setupSelfPosEnv();
    const order = await getFilledSelfOrder(store);
    const comp = await mountWithCleanup(CartPage, {});

    patchWithCleanup(comp.router, {
        navigate(route) {
            if (route === "product_list") {
                expect.step(`navigate:${route}`);
            }
        },
        back() {
            expect.step("back");
        },
    });
    expect(order.unsentLines.length).toBeGreaterThan(0);
    comp.onClickBack();
    expect.verifySteps(["navigate:product_list"]);

    await comp.pay();
    expect(order.unsentLines.length).toBe(0);
    comp.onClickBack();
    expect.verifySteps(["back"]);
});

test("presetButton", async () => {
    const store = await setupSelfPosEnv();
    const order = await getFilledSelfOrder(store);
    const comp = await mountWithCleanup(CartPage, {});

    const inPreset = store.models["pos.preset"].get(1);
    store.config.self_ordering_pay_after = "each";
    store.config.use_presets = true;
    order.preset_id = inPreset;

    const expected = { label: "In" };

    // Classic
    expect(comp.presetButton).toMatchObject(expected);

    // Do not use presets
    store.config.use_presets = false;
    expect(comp.presetButton).toBe(null);

    // No preset selected
    store.config.use_presets = true;
    order.preset_id = false;
    expect(comp.presetButton).toBe(null);

    // Pay after meal, not already ordered
    order.preset_id = inPreset;
    store.config.self_ordering_pay_after = "meal";
    expect(comp.presetButton).toMatchObject(expected);

    // Pay after meal, already ordered
    await comp.pay(); // --> Clear `order.uiState.lineChanges`
    expect(comp.presetButton).toBe(null);

    // Pay after each, no unsent lines
    store.config.self_ordering_pay_after = "each";
    expect(comp.presetButton).toBe(null);
});

test("payButton", async () => {
    const store = await setupSelfPosEnv();
    const order = await getFilledSelfOrder(store);
    const comp = await mountWithCleanup(CartPage, {});

    // Meal, checkout flow, with unsent changes -> Order
    store.hasPaymentMethod = () => true;
    store.config.self_ordering_pay_after = "meal";
    expect(comp.payButton).toMatchObject({ label: "Order", disabled: false });

    // Meal, reached via My Order, with unsent changes elsewhere and a
    // payment method configured -> Pay, but disabled: the customer must
    // go through the normal checkout flow to actually submit those changes.
    history.pushState({ fromLanding: true }, "");
    expect(comp.payButton).toMatchObject({ label: "Pay", disabled: true });

    // Meal, via My Order, unsent changes, no payment method -> no button.
    store.hasPaymentMethod = () => false;
    expect(comp.payButton).toBe(null);

    // Meal, once the pending changes are actually sent: "Pay" (enabled) if
    // a payment method is configured, otherwise no button.
    history.pushState(null, "");
    store.hasPaymentMethod = () => true;
    await comp.pay();
    expect(comp.payButton).toMatchObject({ label: "Pay", disabled: false });

    store.hasPaymentMethod = () => false;
    expect(comp.payButton).toBe(null);

    // Each - payment method available
    store.config.self_ordering_pay_after = "each";
    store.hasPaymentMethod = () => true;
    expect(comp.payButton).toMatchObject({ label: "Pay" });

    // Each - no payment method with unsent lines
    store.hasPaymentMethod = () => false;
    await store.addToCart(store.models["product.template"].get(5), 1);
    expect(comp.payButton).toMatchObject({ label: "Order" });

    // Each - no payment method without unsent lines
    const save = order.lines;
    order.lines = [];
    expect(comp.payButton).toBe(null);
    order.lines = save;
});

test("OrderWidget renders back and pay buttons in the DOM", async () => {
    const store = await setupSelfPosEnv();
    await getFilledSelfOrder(store);
    store.hasPaymentMethod = () => true;
    await mountWithCleanup(CartPage, {});

    expect(".btn-back").toHaveCount(1);
    expect(".cart").toHaveCount(1);
    expect(".cart").toHaveText("Pay");
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
