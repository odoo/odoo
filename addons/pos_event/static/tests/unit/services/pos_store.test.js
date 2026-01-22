import { expect, test } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("createDummyProductForEvents", async () => {
    const store = await setupPosEnv();
    const models = store.models;
    const eventProducts = models["product.template"].filter((product) => product._event_id);
    const events = models["event.event"].getAll();

    // Check if a dummy product for the event is created
    expect(eventProducts).toHaveLength(events.length);
    for (const product of eventProducts) {
        expect(product.event_id).toEqual(events.find((event) => event.id === product._event_id));
    }
});
