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
        expect(store.tableHasOrders(table)).toBe(false);
        expect(store.getActiveOrdersOnTable(table)).toHaveLength(0);
        expect(store.getTableOrders(table.id)).toHaveLength(0);

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

    test("notifies the POS cashier when a new self order arrives", async () => {
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
        const navigations = [];
        patch(store, {
            setOrder(order) {
                selectedOrders.push(order);
            },
            navigate(screen, params) {
                navigations.push({ screen, params });
            },
        });
        notifications[0].opts.buttons[0].onClick();

        expect(selectedOrders).toEqual([order]);
        expect(navigations).toHaveLength(1);
        const { stateOverride } = navigations[0].params;
        expect(navigations[0].screen).toBe("TicketScreen");
        expect(stateOverride.filter).toBe("ACTIVE_ORDERS");
        expect(stateOverride.search).toEqual({
            fieldName: "REFERENCE",
            searchTerm: order.getName(),
        });
        expect(soundEvents).toInclude("stop:order-receive-tone");
    });
});
