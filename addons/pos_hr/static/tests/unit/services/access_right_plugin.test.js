import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("checkPin", async () => {
    const store = await setupPosEnv();
    store.accessRight.resetCashier();
    const emp = store.models["hr.employee"].get(2);
    const result = await store.accessRight.checkPin(emp, "1234");
    expect(result).toBe(true);
});

test("selectCashier", async () => {
    const store = await setupPosEnv();
    store.accessRight.resetCashier();
    const emp = store.models["hr.employee"].get(2);
    // with correct pin
    const selected = await store.accessRight.selectCashier("1234", true);
    expect(selected.id).toBe(emp.id);
    expect(store.accessRight.hasLoggedIn()).toBe(true);
    expect(store.accessRight.loggedCashier.id).toBe(selected.id);

    // with wrong pin
    store.accessRight.resetCashier();
    const result = await store.accessRight.selectCashier("wrongpin", true);
    expect(result).toBeEmpty();
});
