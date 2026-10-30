import { describe, expect, test } from "@odoo/hoot";
import { getFilledOrder, setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { onRpc } from "@web/../tests/web_test_helpers";
import { Deferred, tick } from "@odoo/hoot-mock";

definePosModels();

describe("server_synchronization.test.js", () => {
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

test("An order synced as draft then paid offline is kept until its payments are synced", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    await store.syncAllOrders();
    expect(order.isSynced).toBe(true);

    const cashPm = store.models["pos.payment.method"].find((pm) => pm.is_cash_count);
    order.addPaymentline(cashPm);
    order.state = "paid";
    expect(order.isUnsyncedPaid).toBe(true);
    expect(order.canBeRemovedFromIndexedDB).toBe(false);

    await store.syncAllOrders({ orders: [order] });
    expect(order.isUnsyncedPaid).toBe(false);
    expect(order.canBeRemovedFromIndexedDB).toBe(true);
});

test("The server draft does not reopen an order paid offline", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    await store.syncAllOrders();

    // Paid offline, the server still has the order as draft
    const cashPm = store.models["pos.payment.method"].find((pm) => pm.is_cash_count);
    order.addPaymentline(cashPm);
    order.state = "paid";
    await store.deviceSync.readDataFromServer();
    expect(order.state).toBe("paid");
    expect(order.isUnsyncedPaid).toBe(true);
});

test("The server draft wins once the server received the payments", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    await store.syncAllOrders();

    const cashPm = store.models["pos.payment.method"].find((pm) => pm.is_cash_count);
    order.addPaymentline(cashPm);
    const payment = order.payment_ids[0];
    order.state = "paid";

    // The server received the payments but kept the order draft (lines changed on another
    // device), and the answer of the sync was lost
    onRpc("pos.config", "read_config_open_orders", () => ({
        deleted_record_ids: {},
        dynamic_records: {
            "pos.order": [{ ...order.raw, state: "draft", payment_ids: [9999] }],
            "pos.payment": [
                {
                    id: 9999,
                    uuid: payment.uuid,
                    pos_order_id: order.id,
                    amount: payment.amount,
                    payment_method_id: cashPm.id,
                },
            ],
        },
    }));
    await store.deviceSync.readDataFromServer();
    expect(order.state).toBe("draft");
});

test("A read requested while another one is running is done again once it ends", async () => {
    const store = await setupPosEnv();
    const firstRead = new Deferred();
    let calls = 0;
    onRpc("pos.config", "read_config_open_orders", async () => {
        if (++calls === 1) {
            await firstRead;
        }
        return { deleted_record_ids: {}, dynamic_records: {} };
    });

    const first = store.deviceSync.readDataFromServer();
    let secondDone = false;
    const second = store.deviceSync.readDataFromServer().then(() => (secondDone = true));
    const third = store.deviceSync.readDataFromServer();
    await tick();
    // The callers wait for the running read instead of returning with stale data
    expect(calls).toBe(1);
    expect(secondDone).toBe(false);

    firstRead.resolve();
    await Promise.all([first, second, third]);
    // Only one more read for all the callers that came during the first one
    expect(calls).toBe(2);
    expect(secondDone).toBe(true);
});

test("Closing the session from another device sends an order synced as draft then paid offline", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    await store.syncAllOrders();

    const cashPm = store.models["pos.payment.method"].find((pm) => pm.is_cash_count);
    order.addPaymentline(cashPm);
    order.state = "paid";
    expect(order.isUnsyncedPaid).toBe(true);

    const syncedStates = [];
    onRpc("pos.order", "sync_from_ui", ({ args }) => {
        syncedStates.push(...args[0].map((o) => o.state));
    });
    await store.closingSessionNotification({
        device_identifier: `${store.device.identifier}-other`,
        session_id: store.session.id,
    });
    expect(syncedStates).toEqual(["paid"]);
    expect(order.isUnsyncedPaid).toBe(false);
});
