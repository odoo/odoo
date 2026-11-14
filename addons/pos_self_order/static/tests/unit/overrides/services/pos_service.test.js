import { test, expect, describe } from "@odoo/hoot";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { setupPoSEnvForSelfOrder } from "../../utils";
import { onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";

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
        onRpc("pos.order", "snooze_notification", () => true);
        const store = await setupPoSEnvForSelfOrder();
        const order = await getFilledOrder(store, { source: "mobile" }, true);
        const added = [];
        let closed = 0;
        patchWithCleanup(store.models, {
            connectNewData: () => ({ "pos.order": [order] }),
        });
        patchWithCleanup(store.deviceSync, {
            sound: { play() {}, stop() {} },
            notification: {
                add(message, options) {
                    added.push({ message, options });
                    return () => closed++;
                },
            },
        });

        await store.deviceSync.processDynamicRecords({});
        expect(added).toHaveLength(1);
        expect(added[0].options.sticky).toBe(true);

        added[0].options.onClose();
        expect(closed).toBe(1);
    });
});
