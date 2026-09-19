import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("canEditPrice", async () => {
    const store = await setupPosEnv();
    const manager = store.models["res.users"].get(2);
    const cashier = store.models["res.users"].get(3);

    const checkCanEditPrice = (user, result) => {
        store.setCashier(user);
        expect(store.accessRight.canEditPrice).toBe(result);
    };

    // Without the restriction, both the manager and the cashier may set a price.
    store.config.restrict_price_control = false;
    checkCanEditPrice(manager, true);
    checkCanEditPrice(cashier, true);

    // With the restriction, only the manager may.
    store.config.restrict_price_control = true;
    checkCanEditPrice(manager, true);
    checkCanEditPrice(cashier, false);
});
