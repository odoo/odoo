import { test, describe, expect } from "@odoo/hoot";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { setupPoSEnvForSelfOrder } from "../../utils";

definePosModels();

describe("pos.config", () => {
    test("shouldLoadOrder", async () => {
        const store = await setupPoSEnvForSelfOrder();
        const config = store.config;
        config.module_pos_restaurant = false;

        expect(Boolean(config.shouldLoadOrder)).toBe(false);
        store.session._self_ordering = true;
        expect(Boolean(config.shouldLoadOrder)).toBe(true);
    });
});
