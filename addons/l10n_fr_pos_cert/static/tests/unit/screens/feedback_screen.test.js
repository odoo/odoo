import { test, expect } from "@odoo/hoot";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("canEditPayment", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    order.state = "paid";
    // In FR localisation, edit payment should not be visble even when order.nb_print === 0
    expect(store.canEditPayment(order)).toBe(false);
});
