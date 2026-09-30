import { test, expect, describe } from "@odoo/hoot";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { setupPoSEnvForSelfOrder } from "../../utils";

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
});
