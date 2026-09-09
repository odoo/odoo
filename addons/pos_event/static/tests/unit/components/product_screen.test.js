import { test, expect } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { mountProductScreen } from "@point_of_sale/../tests/unit/ui_utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import * as Utils from "@point_of_sale/../tests/unit/ui_utils";

definePosModels();

test("long press on an event product opens the EventInfoPopup", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();
    await mountProductScreen(store);
    await Utils.longPress('[data-product-id="dummy_1"]');
    const popup = await waitFor(".event-order-info-popup");
    expect(popup.textContent).toMatch("Odoo Community Days");
});
