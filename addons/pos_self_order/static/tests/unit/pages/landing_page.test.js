import { test, expect } from "@odoo/hoot";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { LandingPage } from "@pos_self_order/app/pages/landing_page/landing_page";
import { setupSelfPosEnv, getFilledSelfOrder, mockNavigate } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";

definePosSelfModels();

test("clickMyOrder navigates to cart with fromLanding when a draft order exists", async () => {
    const store = await setupSelfPosEnv("mobile");
    await getFilledSelfOrder(store);
    const comp = await mountWithCleanup(LandingPage, {});

    expect(comp.draftOrder.length).toBeGreaterThan(0);

    patchWithCleanup(comp.router, {
        navigate(route, params, historyState) {
            expect.step(`${route}:${JSON.stringify(params)}:${JSON.stringify(historyState)}`);
        },
    });

    comp.clickMyOrder();
    expect.verifySteps(['cart:{}:{"fromLanding":true}']);
});

test("clickMyOrder navigates to orderHistory when there is no draft order", async () => {
    await setupSelfPosEnv();
    const comp = await mountWithCleanup(LandingPage, {});

    expect(comp.draftOrder.length).toBe(0);

    const navigate = mockNavigate(comp.router);

    comp.clickMyOrder();

    expect(navigate).toEqual(["orderHistory"]);
});

test("navigates to product list when presets are disabled", async () => {
    const store = await setupSelfPosEnv();
    store.config.use_presets = false;

    const comp = await mountWithCleanup(LandingPage, {});
    const navigate = mockNavigate(comp.router);

    comp.start();

    expect(navigate).toEqual(["product_list"]);
});

test("handles single and multiple available presets", async () => {
    const store = await setupSelfPosEnv("mobile", "counter", "each", {}, true);
    store.config.use_presets = true;

    // Single available preset.
    store.models["pos.preset"].getAll = () => store.models["pos.preset"].readMany([20, 21]);

    let comp = await mountWithCleanup(LandingPage, {});
    let navigate = mockNavigate(comp.router);

    comp.start();

    expect(store.currentOrder.preset_id.id).toBe(21);
    expect(navigate).toEqual(["product_list"]);

    // Multiple available presets.
    store.currentOrder.preset_id = null;
    store.models["pos.preset"].getAll = () => store.models["pos.preset"].readMany([21, 23]);

    comp = await mountWithCleanup(LandingPage, {});
    navigate = mockNavigate(comp.router);

    comp.start();

    expect(store.currentOrder.preset_id).toBeEmpty();
    expect(navigate).toEqual(["location"]);
});

test("includes table-service presets in QR/kiosk mode", async () => {
    const store = await setupSelfPosEnv("mobile", "counter", "each", {}, true);
    store.config.use_presets = true;

    // Table-service presets are available in QR mode.
    store.router.getTableIdentifier = () => "T1";
    store.models["pos.preset"].getAll = () => store.models["pos.preset"].readMany([20, 21]);

    expect(store.availablePresets.length).toBe(2);

    const comp = await mountWithCleanup(LandingPage, {});
    const navigate = mockNavigate(comp.router);

    comp.start();

    expect(store.currentOrder.preset_id).toBeEmpty();
    expect(navigate).toEqual(["location"]);
});
