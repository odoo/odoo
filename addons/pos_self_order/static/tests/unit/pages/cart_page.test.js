import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { CartPage } from "@pos_self_order/app/pages/cart_page/cart_page";
import { setupSelfPosEnv, getFilledSelfOrder, addComboProduct } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";

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

test("getPrice", async () => {
    const store = await setupSelfPosEnv();
    const order = await getFilledSelfOrder(store);
    const [line1, line2] = order.lines;
    const comp = await mountWithCleanup(CartPage, {});

    expect(comp.getPrice(line1)).toBe(345);
    expect(comp.getPrice(line2)).toBe(250);

    // For combo parent line
    const parentLine = await addComboProduct(store);
    expect(comp.getPrice(parentLine)).toBe(2125);
});
