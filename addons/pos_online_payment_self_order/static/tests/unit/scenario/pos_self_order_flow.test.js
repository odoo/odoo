import { test } from "@odoo/hoot";
import { setupSelfPosEnv, mockRouterNavigate } from "@pos_self_order/../tests/unit/utils";
import { definePosSelfModels } from "@pos_self_order/../tests/unit/data/generate_model_definitions";
import * as Utils from "@pos_self_order/../tests/unit/ui_utils";

definePosSelfModels();

test("zero amount total order flow with payment method", async () => {
    mockRouterNavigate();
    await setupSelfPosEnv(
        "kiosk",
        "counter",
        "each",
        {
            use_presets: false,
            available_preset_ids: [],
        },
        true
    );
    // For zero amount total order will be redirected to confirmation page instead of payment page.
    await Utils.clickOrderNow();
    await Utils.clickCategory("Category 2");
    await Utils.clickProduct("Free Product - Wood chair");
    await Utils.clickBtn("Checkout");
    await Utils.checkIsNoBtn("Pay");
    await Utils.clickBtn("Order");
    await Utils.checkConfirmationPage();
    await Utils.clickBtn("Close");
    // For non-zero amount total order will be redirected to payment page.
    await Utils.clickOrderNow();
    await Utils.clickCategory("Food");
    await Utils.clickProduct("Bacon burger");
    await Utils.clickBtn("Checkout");
    await Utils.checkIsNoBtn("Order");
    await Utils.clickBtn("Pay");
    await Utils.checkPaymentPage();
});
