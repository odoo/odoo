import { test, expect, describe } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

describe("pos_store.js", () => {
    test("createNewOrder", async () => {
        const store = await setupPosEnv();
        store.addNewOrder();
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
    test("shouldShowOpeningControl", async () => {
        const store = await setupPosEnv();
        const emp = store.models["hr.employee"].get(2);
        store.setCashier(emp);
        store.hasLoggedIn = true;
        expect(store.shouldShowOpeningControl()).toBe(true);
    });
    test("allowProductCreation", async () => {
        const store = await setupPosEnv();
        const admin = store.models["hr.employee"].get(2);
        store.setCashier(admin);
        expect(await store.allowProductCreation()).toBe(true);
        const emp = store.models["hr.employee"].get(3);
        store.setCashier(emp);
        expect(await store.allowProductCreation()).toBe(false);
    });
    test("addLineToCurrentOrder", async () => {
        const store = await setupPosEnv();
        store.addNewOrder();
        const admin = store.models["hr.employee"].get(2);
        store.setCashier(admin);
        const product_id = store.models["product.product"].get(5);
        const result = await store.addLineToCurrentOrder({
            product_id: product_id,
            product_tmpl_id: product_id.product_tmpl_id,
        });
        expect(result.order_id.employee_id.id).toBe(2);
    });
});
