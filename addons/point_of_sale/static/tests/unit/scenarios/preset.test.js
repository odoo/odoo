import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

test("test_preset_timing_retail: preset timing requires slot then accepts selected time", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const timedPreset = store.models["pos.preset"].get(5);

    order.setPreset(timedPreset);
    expect(order.preset_id.id).toBe(timedPreset.id);
    expect(order.presetRequirementsFilled).toBe(false);

    order.preset_time = "2026-04-14 15:00:00";
    expect(order.presetRequirementsFilled).toBe(true);
});

test("test_preset_timing_retail: preset customer selection sets customer requirement", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const addressPreset = store.models["pos.preset"].get(4);
    const partner = store.models["res.partner"].get(3);

    order.setPreset(addressPreset);
    expect(order.isCustomerRequired).toBe(true);

    order.setPartner(partner);
    expect(order.partner_id.id).toBe(partner.id);
    expect(order.isCustomerRequired).toBe(false);
});
