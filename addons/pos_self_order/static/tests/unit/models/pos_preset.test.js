import { test, expect } from "@odoo/hoot";
import { setupSelfPosEnv } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";

definePosSelfModels();

test("needsEmail", async () => {
    const store = await setupSelfPosEnv();
    const models = store.models;
    const preset = models["pos.preset"].get(10);

    expect(preset.needsEmail).toBeEmpty();
    preset.mail_template_id = 21;
    expect(preset.needsEmail).toBe(true);
    preset.mail_template_id = false;
    expect(preset.needsEmail).toBeEmpty();
});
