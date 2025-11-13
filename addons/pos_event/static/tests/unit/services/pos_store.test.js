import { expect, test } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("createDummyProductForEvents", async () => {
    const store = await setupPosEnv();
    const models = store.models;
    const eventProducts = models["product.template"].filter((product) => product._event_id);
    const event = models["event.event"].get(1);

    // Check if a dummy product for the event is created
    expect(eventProducts).toHaveLength(1);
    expect(eventProducts[0].event_id).toEqual(event);
});
