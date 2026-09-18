import { expect, test } from "@odoo/hoot";
import { getFilledOrder, setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { onRpc } from "@web/../tests/web_test_helpers";

definePosModels();

test("Related models must keep local records", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const product = store.models["product.template"].get(8);
    expect(order.isSynced).toBe(false);
    expect(order.lines.every((l) => l.isSynced === true)).toBe(false);
    await store.syncAllOrders();
    expect(order.isSynced).toBe(true);
    expect(order.lines.every((l) => l.isSynced === true)).toBe(true);
    await store.addLineToOrder(
        {
            product_tmpl_id: product,
            qty: 1,
        },
        order
    );
    expect(order.lines.every((l) => l.isSynced === true)).toBe(false);

    // Download the same order from server, the local unsynced line must be kept
    await store.data.loadServerOrders([["id", "=", order.id]]);
    expect(order.lines.every((l) => l.isSynced === true)).toBe(false);
});

test("Check behavior when deleting records", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    expect(order.isSynced).toBe(false);
    expect(order.lines.every((l) => l.isSynced === true)).toBe(false);
    await store.syncAllOrders();
    expect(order.isSynced).toBe(true);
    expect(order.lines.every((l) => l.isSynced === true)).toBe(true);
    order.removeOrderline(order.lines[0]);
    expect(order.lines).toHaveLength(1);

    // At this point if we download the same order from server,
    // we must not lose the local deletion
    await store.data.loadServerOrders([["id", "=", order.id]]);
    expect(order.lines).toHaveLength(2);

    // But if we sync before downloading, the deletion must be kept
    order.removeOrderline(order.lines[0]);
    expect(order.lines).toHaveLength(1);
    await store.syncAllOrders({ orders: [order] });
    await store.data.loadServerOrders([["id", "=", order.id]]);
    expect(order.lines).toHaveLength(1);
});

test("Local changes must survive a synchronisation triggered by another device", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    await store.syncAllOrders();
    expect(order.isSynced).toBe(true);

    // Add local change to order
    const product = store.models["product.template"].get(8);
    await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);
    store.addPendingOrder([order.id]);
    expect(order.isDirty()).toBe(true);

    // Another device edited the same order: we read the open orders from the server
    // Order must stay dirty (cause the local changes are not yet sent to the server)
    await store.deviceSync.readDataFromServer();
    expect(order.isDirty()).toBe(true);
    await store.syncAllOrders();
    expect(order.lines).toHaveLength(3);
    expect(order.lines.every((l) => l.isSynced === true)).toBe(true);
});

test("A stale draft read does not reopen a paid order", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    order.state = "paid";
    await store.syncAllOrders();
    expect(order.finalized).toBe(true);

    // The answer of a read started before the payment was committed
    const staleOrder = { ...order.raw, state: "draft" };
    onRpc("pos.order", "read_pos_orders", () => ({ "pos.order": [staleOrder] }));
    await store.data.loadServerOrders([["state", "=", "draft"]]);
    expect(order.state).toBe("paid");
});
