import { test, expect } from "@odoo/hoot";
import { setupSelfPosEnv, getFilledSelfOrder } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";

definePosSelfModels();

test("getDisplayPriceWithQty", async () => {
    const store = await setupSelfPosEnv();
    const order = await getFilledSelfOrder(store);
    const [line1, line2] = order.lines;

    store.config.iface_tax_included = "subtotal";
    expect(line1.getDisplayPriceWithQty(3)).toBe(300);
    expect(line2.getDisplayPriceWithQty(2)).toBe(200);

    store.config.iface_tax_included = "total";
    expect(line1.getDisplayPriceWithQty(3)).toBe(345);
    expect(line2.getDisplayPriceWithQty(2)).toBe(250);
});

test("getPendingQtyDelta", async () => {
    const store = await setupSelfPosEnv();
    const order = await getFilledSelfOrder(store);
    const line = order.lines[0];

    // Never synced: no baseline recorded yet, so there is no pending delta.
    expect(line.getPendingQtyDelta()).toBe(0);

    // Record a synced baseline, matching the current qty: no delta yet.
    order.uiState.lineChanges[line.uuid] = { qty: line.qty };
    expect(line.getPendingQtyDelta()).toBe(0);

    line.qty += 2;
    expect(line.getPendingQtyDelta()).toBe(2);

    line.qty -= 5;
    expect(line.getPendingQtyDelta()).toBe(-3);
});

test("changes getter uses getPendingQtyDelta for the qty diff", async () => {
    const store = await setupSelfPosEnv();
    const order = await getFilledSelfOrder(store);
    const line = order.lines[0];

    order.uiState.lineChanges[line.uuid] = {
        qty: line.qty,
        customer_note: line.customer_note,
        attribute_value_ids: JSON.stringify([]),
        custom_attribute_value_ids: JSON.stringify([]),
    };
    expect(line.changes.qty).toBe(false);

    line.qty += 1;
    expect(line.changes.qty).toBe(1);
});
