import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { expectRoleAccess, setupRolesEnv } from "@pos_hr/../tests/unit/utils";

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

test("disablePriceButton", async () => {
    const env = await setupRolesEnv();
    env.store.config.restrict_price_control = false;
    expectRoleAccess(env, "disablePriceButton", "cashier", false);
    env.store.config.restrict_price_control = true;
    expectRoleAccess(env, "disablePriceButton", "manager", false);
});

test("disableLinediscount", async () => {
    const env = await setupRolesEnv();
    env.store.config.manual_discount = true;
    expectRoleAccess(env, "disableLinediscount", "cashier", false);
    env.store.config.manual_discount = false;
    expectRoleAccess(env, "disableLinediscount", "supervised", true);
});

test("disableBackSpaceButton", async () => {
    const env = await setupRolesEnv();
    expectRoleAccess(env, "disableBackSpaceButton", "restrictive", false);
});

test("canSwitchSign", async () => {
    const env = await setupRolesEnv();
    expectRoleAccess(env, "canSwitchSign", "cashier", true);
});

test("disablePartner", async () => {
    const env = await setupRolesEnv();
    expectRoleAccess(env, "disablePartner", "restrictive", false);
});

test("disableClickPayment", async () => {
    const env = await setupRolesEnv();
    expectRoleAccess(env, "disableClickPayment", "restrictive", false);
});

test("disableValidateOrder", async () => {
    const env = await setupRolesEnv();
    expectRoleAccess(env, "disableValidateOrder", "restrictive", false);
});

test("disableToggleFavorite", async () => {
    const env = await setupRolesEnv();
    expectRoleAccess(env, "disableToggleFavorite", "cashier", false);
});

test("disableToggleOrder", async () => {
    const env = await setupRolesEnv();
    expectRoleAccess(env, "disableToggleOrder", "restrictive", false);
});
