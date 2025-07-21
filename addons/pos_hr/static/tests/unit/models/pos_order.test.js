import { test, expect, describe } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

describe("pos_order.js", () => {
    test("getCashierName", async () => {
        const store = await setupPosEnv();
        const emp = store.models["hr.employee"].get(3);
        store.setCashier(emp);
        const posOrder = store.getOrder();
        expect(posOrder.getCashierName()).toBe("Employee1");
    });
});
