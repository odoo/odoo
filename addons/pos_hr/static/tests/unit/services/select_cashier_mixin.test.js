import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { CashierSelector } from "@pos_hr/app/utils/select_cashier_mixin";

definePosModels();

test("checkPin", async () => {
    const store = await setupPosEnv();
    store.resetCashier();
    const selector = new CashierSelector(store, false, () => {});
    const emp = store.models["hr.employee"].get(2);
    const result = await selector.checkPin(emp, "1234");
    expect(result).toBe(true);
});

test("selectCashier", async () => {
    const store = await setupPosEnv();
    store.resetCashier();
    const selector = new CashierSelector(store, false, () => {});
    const emp = store.models["hr.employee"].get(2);
    // with correct pin
    const selected = await selector.selectCashier("1234", true);
    expect(selected.id).toBe(emp.id);
    expect(store.hasLoggedIn).toBe(true);
    expect(store.getCashier().id).toBe(selected.id);

    // with wrong pin
    store.resetCashier();
    const result = await selector.selectCashier("wrongpin", true);
    expect(result).toBeEmpty();
});
