import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("disablePriceButton", async () => {
    const store = await setupPosEnv();
    const cashier = store.accessRight.loggedCashier;

    // Without price restriction, everyone can modify prices
    store.config.restrict_price_control = false;
    cashier._role = "cashier";
    expect(store.accessRight.disablePriceButton).toBe(false);
    cashier._role = "manager";
    expect(store.accessRight.disablePriceButton).toBe(false);

    // With price restriction, only managers can modify prices
    store.config.restrict_price_control = true;
    cashier._role = "cashier";
    expect(store.accessRight.disablePriceButton).toBe(true);
    cashier._role = "manager";
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
