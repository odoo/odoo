import { test, waitFor } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { setupAndMountPosApp } from "@point_of_sale/../tests/unit/utils";
import * as Utils from "@point_of_sale/../tests/unit/ui_utils";

definePosModels();

test("test fast payment for qr_code type payment method", async () => {
    await setupAndMountPosApp();
    Utils.clickDisplayedProduct("Bacon burger");
    Utils.clickFastPaymentMethod("QR Code");
    await waitFor(".modal");
    await contains(".modal .btn:contains(Cancel Payment)").click();
    Utils.clickFastPaymentMethod("QR Code");
    await waitFor(".modal");
    await contains(".modal .btn:contains(Confirm Payment)").click();
    await waitFor(".receipt-screen");
});
