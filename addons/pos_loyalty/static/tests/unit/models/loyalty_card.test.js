import { test, describe, expect } from "@odoo/hoot";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";

definePosModels();

describe("loyalty.card", () => {
    test("isExpired", async () => {
        const store = await setupPosEnv();
        const models = store.models;

        const expiredCard = models["loyalty.card"].get(1);
        const activeCard = models["loyalty.card"].get(2);
        const noExpireCard = models["loyalty.card"].get(3);

        expect(expiredCard.isExpired()).toBe(false);
        expect(activeCard.isExpired()).toBe(true);
        expect(noExpireCard.isExpired()).toBe(false);
    });
});
