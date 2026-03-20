import { test, expect } from "@odoo/hoot";
import { setupSelfPosEnv, getFilledSelfOrder } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";

definePosSelfModels();

test("isTakeaway", async () => {
    const store = await setupSelfPosEnv();
    const order = await getFilledSelfOrder(store);

    expect(order.lines).toHaveLength(2);
    expect(order.isTakeaway).toBe(true);
});
test("Self Order changes and unsentLines and lineChanges and recomputeChanges", async () => {
    const store = await setupSelfPosEnv();
    const order = await getFilledSelfOrder(store);
    const [line1, line2] = order.lines;

    expect(order.unsentLines).toHaveLength(2);
    expect(order.changes[line1.uuid]).toMatchObject(line1.changes);
    expect(order.changes[line2.uuid]).toMatchObject(line2.changes);
    expect(order.uiState.lineChanges).toHaveLength(0);

    // Simulating Order sent for preparation
    await store.sendDraftOrderToServer();
    order.recomputeChanges();

    expect(order.unsentLines).toHaveLength(0);
    expect(order.uiState.lineChanges).toHaveLength(2);

    // delete line
    line2.delete();
    expect(order.uiState.lineChanges).toHaveLength(2);
    order.recomputeChanges();
    expect(order.uiState.lineChanges).toHaveLength(1);

    // Add new Line to order
    const product = store.models["product.template"].get(6);

    await store.addToCart(product, 1);
    const line3 = order.lines[1];
    expect(order.unsentLines).toHaveLength(1);
    expect(order.changes[line3.uuid]).toMatchObject(line3.changes);
});
