import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

definePosModels();

test("disablePriceButton", async () => {
    const store = await setupPosEnv();
    let loggedCashierId = 3; // User1
    patchWithCleanup(store.accessRight, {
        get loggedCashier() {
            return this.data.models["res.users"].get(loggedCashierId);
        },
    });

    // Without price restriction, everyone can modify prices
    store.config.restrict_price_control = false;
    expect(store.accessRight.disablePriceButton).toBe(false);
    loggedCashierId = 2; // Administrator
    expect(store.accessRight.disablePriceButton).toBe(false);

    // With price restriction, only managers can modify prices
    store.config.restrict_price_control = true;
    loggedCashierId = 3;
    expect(store.accessRight.disablePriceButton).toBe(true);
    loggedCashierId = 2;
    expect(store.accessRight.disablePriceButton).toBe(false);
});

test("disableLinediscount", async () => {
    const store = await setupPosEnv();

    store.config.manual_discount = true;
    expect(store.accessRight.disableLinediscount).toBe(false);
    store.config.manual_discount = false;
    expect(store.accessRight.disableLinediscount).toBe(true);
});

test("disableBackSpaceButton", async () => {
    const store = await setupPosEnv();
    expect(store.accessRight.disableBackSpaceButton).toBe(false);
});

test("canSwitchSign", async () => {
    const store = await setupPosEnv();
    expect(store.accessRight.canSwitchSign).toBe(true);
});

test("disablePartner", async () => {
    const store = await setupPosEnv();
    expect(store.accessRight.disablePartner).toBe(false);
});

test("disableClickPayment", async () => {
    const store = await setupPosEnv();
    expect(store.accessRight.disableClickPayment).toBe(false);
});

test("disableValidateOrder", async () => {
    const store = await setupPosEnv();
    expect(store.accessRight.disableValidateOrder).toBe(false);
});

test("disableToggleFavorite", async () => {
    const store = await setupPosEnv();
    expect(store.accessRight.disableToggleFavorite).toBe(false);
});

test("disableToggleOrder", async () => {
    const store = await setupPosEnv();
    expect(store.accessRight.disableToggleOrder).toBe(false);
});
