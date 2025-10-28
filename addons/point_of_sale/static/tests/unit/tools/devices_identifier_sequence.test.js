import { test, expect } from "@odoo/hoot";
import { getFilledOrder, setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

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
