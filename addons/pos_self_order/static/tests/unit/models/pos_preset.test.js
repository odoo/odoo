import { test, describe, expect, beforeEach } from "@odoo/hoot";
import { setupSelfPosEnv, patchSession } from "../utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();
beforeEach(patchSession);

describe("self_order - pos.preset", () => {
    test("needsEmail", async () => {
        const store = await setupSelfPosEnv();
        const models = store.models;

        const preset = models["pos.preset"].get(10);

        expect(preset.needsEmail).toBe(true);
    });
});
