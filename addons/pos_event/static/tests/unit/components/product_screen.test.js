import { test, expect } from "@odoo/hoot";
import { pointerDown, pointerUp, queryOne, waitFor } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";
import { mountProductScreen } from "@point_of_sale/../tests/unit/ui_utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { LONG_PRESS_DURATION, TOUCH_DELAY } from "@point_of_sale/utils";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";

definePosModels();

test("long press on an event product opens the EventInfoPopup", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();
    await mountProductScreen(store);
    const product = queryOne('.product-sortable[data-product-id="dummy_1"]');
    await pointerDown(product);
    await advanceTime(LONG_PRESS_DURATION + TOUCH_DELAY + 5);
    await pointerUp(product);
    const popup = await waitFor(".event-order-info-popup");
    expect(popup.textContent).toMatch("Odoo Community Days");
});
