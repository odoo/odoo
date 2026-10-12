import { test, describe, expect } from "@odoo/hoot";

import { setupSelfPosEnv } from "@pos_self_order/../tests/unit/utils";
import { definePosSelfModels } from "@pos_self_order/../tests/unit/data/generate_model_definitions";

definePosSelfModels();

describe("self_order_service", () => {
    test("eventImageUrl", async () => {
        const store = await setupSelfPosEnv();
        const models = store.models;
        const event = models["event.event"].get(1);
        expect(store.eventImageUrl(event)).toBe(
            "/pos_self_order_event/static/src/img/placeholder_thumbnail.png"
        );
        event.image_1024 = "testimageformat";
        expect(store.eventImageUrl(event)).toBe("/web/image/event.event/1/image_1024");
    });
});
