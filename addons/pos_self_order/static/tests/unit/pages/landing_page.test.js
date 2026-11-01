import { test, expect } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { LandingPage } from "@pos_self_order/app/pages/landing_page/landing_page";
import { mockNavigate, setupSelfPosEnv } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";

definePosSelfModels();

test("navigates to product list when presets are disabled", async () => {
    const store = await setupSelfPosEnv();
    store.config.use_presets = false;

    const comp = await mountWithCleanup(LandingPage, {});
    const navigate = mockNavigate(comp.router);

    comp.start();

    expect(navigate).toEqual(["product_list"]);
});

test("handles single and multiple available presets", async () => {
    const store = await setupSelfPosEnv("mobile");
    store.config.use_presets = true;

    // Single available preset.
    store.models["pos.preset"].getAll = () => store.models["pos.preset"].readMany([1, 10]);

    let comp = await mountWithCleanup(LandingPage, {});
    let navigate = mockNavigate(comp.router);

    comp.start();

    expect(store.currentOrder.preset_id.id).toBe(1);
    expect(navigate).toEqual(["product_list"]);

    // Multiple available presets.
    store.currentOrder.preset_id = null;
    store.models["pos.preset"].getAll = () => store.models["pos.preset"].readMany([1, 2]);

    comp = await mountWithCleanup(LandingPage, {});
    navigate = mockNavigate(comp.router);

    comp.start();

    expect(store.currentOrder.preset_id).toBeEmpty();
    expect(navigate).toEqual(["location"]);
});

test("resyncs category availability for the next customer", async () => {
    const store = await setupSelfPosEnv();
    const categ1 = store.models["pos.category"].get(1);

    categ1.update({ hour_after: 10, hour_until: 12 });
    mockDate("2025-11-29 18:00:00");
    store.computeAvailableCategories();
    expect(store.isCategoryAvailable(categ1.id)).toBeEmpty();
    expect(store.currentCategory.id).not.toBe(categ1.id);

    mockDate("2025-11-29 11:00:00");
    await mountWithCleanup(LandingPage, {});

    expect(!!store.isCategoryAvailable(categ1.id)).toBe(true);
    expect(store.currentCategory.id).toBe(categ1.id);
});

test("includes table-service presets in QR/kiosk mode", async () => {
    const store = await setupSelfPosEnv("mobile");
    store.config.use_presets = true;

    // Table-service presets are available in QR mode.
    store.router.getTableIdentifier = () => "T1";
    store.models["pos.preset"].getAll = () => store.models["pos.preset"].readMany([1, 10]);

    expect(store.availablePresets.length).toBe(2);

    const comp = await mountWithCleanup(LandingPage, {});
    const navigate = mockNavigate(comp.router);

    comp.start();

    expect(store.currentOrder.preset_id).toBeEmpty();
    expect(navigate).toEqual(["location"]);
});
