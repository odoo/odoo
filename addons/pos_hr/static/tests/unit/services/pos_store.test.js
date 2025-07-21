import { test, expect, describe } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

describe("pos_hr pos_store.js", () => {
    test("createNewOrder", async () => {
        const store = await setupPosEnv();
        const order = store.getOrder();
        expect(order.employee_id.id).toBe(2);
    });
    test("employeeIsAdmin", async () => {
        const store = await setupPosEnv();
        const emp = store.models["hr.employee"].get(2);
        store.setCashier(emp);
        expect(store.employeeIsAdmin).toBe(true);
    });
    test("_getConnectedCashier", async () => {
        const store = await setupPosEnv();
        expect(store._getConnectedCashier().id).toBe(2);
    });
});
