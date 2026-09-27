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
    const selected = await store.selectCashier("1234", true);
    expect(selected.id).toBe(emp.id);
    expect(store.accessRight.hasLoggedIn()).toBe(true);
    expect(store.accessRight.loggedCashier.id).toBe(selected.id);

    // with wrong pin
    store.accessRight.resetCashier();
    const result = await store.selectCashier("wrongpin", true);
    expect(result).toBeEmpty();
});

test("canEditPrice", async () => {
    const store = await setupPosEnv();
    const manager = store.models["hr.employee"].get(2);
    const cashier = store.models["hr.employee"].get(3);
    const restrictive = store.models["hr.employee"].get(4);

    const checkCanEditPrice = (employee, result) => {
        store.setCashier(employee);
        expect(store.accessRight.canEditPrice).toBe(result);
    };

    // Without the restriction, both the manager and the cashier may set a price.
    store.config.restrict_price_control = false;
    checkCanEditPrice(manager, true);
    checkCanEditPrice(cashier, true);
    checkCanEditPrice(restrictive, false);

    // With the restriction, only the manager may.
    store.config.restrict_price_control = true;
    checkCanEditPrice(manager, true);
    checkCanEditPrice(cashier, false);
    checkCanEditPrice(restrictive, false);
});
