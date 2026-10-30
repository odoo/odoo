import { test, expect } from "@odoo/hoot";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

definePosModels();

function patchNotifications(store) {
    const notifications = [];
    patchWithCleanup(store.notification, {
        add: (_message, options) => notifications.push(options?.type),
    });
    return notifications;
}

test("Opening the payment screen reads the data from the server", async () => {
    const store = await setupPosEnv();
    const table = store.models["restaurant.table"].get(2);
    const order = await getFilledOrder(store, { table_id: table });
    let readCount = 0;
    patchWithCleanup(store.deviceSync, {
        readDataFromServer: async () => readCount++,
    });
    const notifications = patchNotifications(store);
    const comp = await mountWithCleanup(PaymentScreen, { props: { orderUuid: order.uuid } });
    expect(readCount).toBe(1);
    expect(comp.currentOrder.uuid).toBe(order.uuid);
    expect(notifications).toEqual([]);
});

test("The payment screen follows the order merged by the server", async () => {
    const store = await setupPosEnv();
    const table = store.models["restaurant.table"].get(2);
    const order = await getFilledOrder(store, { table_id: table });
    // Open order of the table created on another device
    const serverOrder = store.createNewOrder({ table_id: table });
    store.setOrder(order);
    patchWithCleanup(store.deviceSync, {
        // Same as the merge done by the device synchronisation: the lines are moved to the
        // open order of the table, which is selected, and the local order is deleted
        readDataFromServer: async () => {
            for (const line of order.lines.slice()) {
                line.update({ order_id: serverOrder });
            }
            store.setOrder(serverOrder);
            store.data.localDeleteCascade(order);
        },
    });
    const notifications = patchNotifications(store);
    const comp = await mountWithCleanup(PaymentScreen, { props: { orderUuid: order.uuid } });
    expect(comp.currentOrder.uuid).toBe(serverOrder.uuid);
    expect(notifications).toEqual(["warning"]);
});

test("The payment screen opens for an order without lines", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder({ table_id: store.models["restaurant.table"].get(2) });
    patchWithCleanup(store.deviceSync, {
        readDataFromServer: async () => {},
    });
    const notifications = patchNotifications(store);
    const comp = await mountWithCleanup(PaymentScreen, { props: { orderUuid: order.uuid } });
    expect(comp.currentOrder.uuid).toBe(order.uuid);
    expect(notifications).toEqual([]);
});

test("The payment screen opens when the server data cannot be read", async () => {
    const store = await setupPosEnv();
    const table = store.models["restaurant.table"].get(2);
    const order = await getFilledOrder(store, { table_id: table });
    patchWithCleanup(store.deviceSync, {
        readDataFromServer: async () => {
            throw new Error("Server error");
        },
    });
    const notifications = patchNotifications(store);
    const comp = await mountWithCleanup(PaymentScreen, { props: { orderUuid: order.uuid } });
    expect(comp.currentOrder.uuid).toBe(order.uuid);
    expect(notifications).toEqual(["danger"]);
});
