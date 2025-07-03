import { describe, test, expect } from "@odoo/hoot";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";

definePosModels();

describe("pos_store.js", () => {
    test("computeTableCount", async () => {
        const store = await setupPosEnv();
        const order1 = store.addNewOrder();
        const table = store.models["restaurant.table"].get(2);
        expect(table.uiState.orderCount).toBe(0);
        order1.table_id = table;
        store.computeTableCount();
        expect(table.uiState.orderCount).toBe(1);
    });
});
