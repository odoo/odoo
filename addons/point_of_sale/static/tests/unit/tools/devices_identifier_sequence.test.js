import { test, expect } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { PosOrder } from "../data/pos_order.data";
import { getFilledOrder, setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

// The mock server replaces pos_reference on create, the real one keeps it
const keepSyncedReferences = () =>
    patchWithCleanup(PosOrder.prototype, {
        create(values) {
            const id = super.create(...arguments);
            if (values?.pos_reference) {
                this.write([id], { pos_reference: values.pos_reference });
            }
            return id;
        },
    });

test("Check GAP", async () => {
    const store = await setupPosEnv();
    const device = store.device;
    let orderStack = [];

    // Ensure there is no order at the beginning
    await store.deleteOrders(store.models["pos.order"].getAll());

    const createNewOrdersAndCheck = async (nbr) => {
        for (let i = 0; i < nbr; i++) {
            const order = await getFilledOrder(store);
            orderStack.push(order);
        }
    };

    const deleteOrdersAndCheck = async () => {
        const numbers = orderStack.map((order) => parseInt(order.pos_reference.split("-")[2]));
        await store.deleteOrders(orderStack);
        orderStack = [];
        expect(device.data.unsynced_number_stack).not.toBeEmpty();
        expect(device.data.unsynced_number_stack).toMatch(numbers);
    };

    // Create 15 orders, check that the next number is incremented correctly
    await createNewOrdersAndCheck(15);
    expect(device.data.next_number).toBe(16);
    expect(device.data.unsynced_number_stack).toBeEmpty();

    // Delete all of them, check that the unsynced number stack is filled
    await deleteOrdersAndCheck();

    // Create 15 more orders, the number should not be incremented, we reuse the unsynced numbers
    await createNewOrdersAndCheck(15);

    // Stack is empty numbers are used
    expect(device.data.unsynced_number_stack).toBeEmpty();
    expect(device.data.next_number).toBe(16);
    await deleteOrdersAndCheck();
    expect(device.data.next_number).toBe(16);

    // Create 15 more orders, the number should be incremented
    await createNewOrdersAndCheck(15);
    expect(device.data.next_number).toBe(16);

    // Sync orders and cancel them
    const orders = await store.syncAllOrders();
    await store.deleteOrders(orders);

    // Create 15 more orders, the number should be incremented again
    await createNewOrdersAndCheck(15);
    expect(device.data.next_number).toBe(31);
});

test("Device identifier is set", async () => {
    const store = await setupPosEnv();
    const device = store.device;
    expect(device.identifier).not.toBeEmpty();
});

test("A removed order frees its number right away", async () => {
    const store = await setupPosEnv();
    const device = store.device;
    await store.deleteOrders(store.models["pos.order"].getAll());

    const order = await getFilledOrder(store);
    const number = parseInt(order.pos_reference.split("-")[2]);

    store.removeOrder(order, false);
    expect(device.data.unsynced_number_stack).toEqual([number]);
});

test("A number still used by an order is not reused", async () => {
    const store = await setupPosEnv();
    const device = store.device;
    await store.deleteOrders(store.models["pos.order"].getAll());

    const order = await getFilledOrder(store);
    const number = parseInt(order.pos_reference.split("-")[2]);
    // The number is back on the stack while the order is still here: its
    // removal was lost by a reload, or another tab removed its own copy
    device.saveUnusedNumber([order]);
    expect(device.data.unsynced_number_stack).toEqual([number]);

    const next = await getFilledOrder(store);
    expect(next.pos_reference).not.toBe(order.pos_reference);
    expect(device.data.unsynced_number_stack).toBeEmpty();
});

test("A number held by a synced order is not reused", async () => {
    const store = await setupPosEnv();
    keepSyncedReferences();
    const device = store.device;
    await store.deleteOrders(store.models["pos.order"].getAll());

    const order = await getFilledOrder(store);
    const reference = order.pos_reference;
    const number = parseInt(reference.split("-")[2]);
    await store.syncAllOrders();
    expect(order.isSynced).toBe(true);
    // Another tab removed its unsynced copy of the order
    device.save({ unsynced_number_stack: [number] });

    const next = await getFilledOrder(store);
    expect(next.pos_reference).not.toBe(reference);
});

test("A synced number leaves the reuse stack", async () => {
    const store = await setupPosEnv();
    keepSyncedReferences();
    const device = store.device;
    await store.deleteOrders(store.models["pos.order"].getAll());

    const order = await getFilledOrder(store);
    const number = parseInt(order.pos_reference.split("-")[2]);
    device.saveUnusedNumber([order]);
    expect(device.data.unsynced_number_stack).toEqual([number]);

    await store.syncAllOrders();
    expect(order.isSynced).toBe(true);
    // The order can now leave this device (deleted, other session) while the
    // server keeps its number
    expect(device.data.unsynced_number_stack).toBeEmpty();
});

test("Numbers of another device or config stay on the reuse stack", async () => {
    const store = await setupPosEnv();
    const device = store.device;
    await store.deleteOrders(store.models["pos.order"].getAll());

    const order = await getFilledOrder(store);
    const [prefix, config, digits] = order.pos_reference.split("-");
    const number = parseInt(digits);
    device.saveUnusedNumber([order]);
    store.removeOrder(order, false);
    expect(device.data.unsynced_number_stack).toEqual([number]);

    const year = prefix.slice(0, 2);
    device.removeUsedNumbers([
        { pos_reference: `${year}${device.identifier}9-${config}-${digits}` },
        { pos_reference: `${year}${device.identifier}-${config}9-${digits}` },
    ]);
    expect(device.data.unsynced_number_stack).toEqual([number]);
});
