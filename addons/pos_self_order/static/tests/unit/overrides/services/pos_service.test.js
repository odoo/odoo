import { test, expect, describe } from "@odoo/hoot";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { setupPoSEnvForSelfOrder } from "../../utils";
import { patch } from "@web/core/utils/patch";

definePosModels();

describe("pos_store.js", () => {
    test("check self_ordering_table_id", async () => {
        const store = await setupPoSEnvForSelfOrder();
        const table = store.models["restaurant.table"].getFirst();

        expect(store.tableHasOrders(table)).toBe(false);
        expect(store.getActiveOrdersOnTable(table)).toHaveLength(0);
        expect(store.getTableOrders(table)).toHaveLength(0);

        const order1 = await getFilledOrder(store, { table_id: table });

        expect(store.tableHasOrders(table)).toBe(true);
        expect(store.getActiveOrdersOnTable(table)).toHaveLength(1);
        expect(store.getTableOrders(table.id)).toHaveLength(1);

        order1.state = "cancel";
        expect(store.tableHasOrders(table)).toBe(false);
        expect(store.getActiveOrdersOnTable(table)).toHaveLength(0);
        expect(store.getTableOrders(table)).toHaveLength(0);

        const order2 = await getFilledOrder(store, { self_ordering_table_id: table });
        expect(store.tableHasOrders(table)).toBe(true);
        expect(store.getActiveOrdersOnTable(table)).toHaveLength(1);
        expect(store.getTableOrders(table.id)).toHaveLength(1);

        // Avoid doublon
        order2.table_id = table;
        expect(store.tableHasOrders(table)).toBe(true);
        expect(store.getActiveOrdersOnTable(table)).toHaveLength(1);
        expect(store.getTableOrders(table.id)).toHaveLength(1);

        order2.state = "cancel";
        expect(store.tableHasOrders(table)).toBe(false);
        expect(store.getActiveOrdersOnTable(table)).toHaveLength(0);
        expect(store.getTableOrders(table)).toHaveLength(0);
    });

    test("notifies the cashier POS when a new self order arrives", async () => {
        const store = await setupPoSEnvForSelfOrder();
        const soundEvents = [];
        const notifications = [];
        patch(store.sound, {
            play(name) {
                soundEvents.push(`play:${name}`);
            },
            stop(name) {
                soundEvents.push(`stop:${name}`);
            },
        });
        patch(store.notification, {
            add(message, opts) {
                notifications.push({ message: message.toString(), opts });
                return () => opts.onClose?.();
            },
        });
        const order = store.addNewOrder({});
        store._handleSelfOrder(order.id);
        expect(notifications).toHaveLength(1);
        expect(soundEvents).toInclude("play:order-receive-tone");

        const selectedOrders = [];
        const navigatedOrders = [];
        patch(store, {
            setOrder(order) {
                selectedOrders.push(order);
            },
            navigateToOrderScreen(order) {
                navigatedOrders.push(order);
            },
        });
        notifications[0].opts.buttons[0].onClick();
        expect(selectedOrders).toEqual([order]);
        expect(navigatedOrders).toEqual([order]);
        expect(soundEvents).toInclude("stop:order-receive-tone");
    });
});
