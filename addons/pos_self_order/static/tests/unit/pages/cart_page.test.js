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

test("setTip adds and removes tip correctly", async () => {
    const store = await setupSelfPosEnv();
    const order = await getFilledSelfOrder(store);
    const comp = await mountWithCleanup(CartPage, {});
    await animationFrame();

    const tipProductId = store.config.tip_product_id?.id;
    // Add tip
    await comp.setTip(5, "fixed", 5);
    expect(order.is_tipped).toBe(true);
    expect(order.tip_amount).toBe(5);
    const tipLine = order.lines.find((l) => l.product_id?.id === tipProductId);
    expect(tipLine).not.toBe(undefined);
    expect(tipLine.price_unit).toBe(5);
    // Remove tip
    await comp.setTip(false);
    expect(order.is_tipped).toBe(false);
    const tipLineAfter = order.lines.find((l) => l.product_id?.id === tipProductId);
    expect(tipLineAfter).toBe(undefined);
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
