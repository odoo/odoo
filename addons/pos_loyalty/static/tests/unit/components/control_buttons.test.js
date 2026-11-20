import { test, expect } from "@odoo/hoot";
import { setupAndMountPosApp } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { deactivateAllProgramsExcept } from "@pos_loyalty/../tests/unit/utils";
import * as PosUiUtils from "@point_of_sale/../tests/unit/ui_utils";
import * as LoyaltyUiUtils from "@pos_loyalty/../tests/unit/ui_utils";
const Utils = { ...PosUiUtils, ...LoyaltyUiUtils };

definePosModels();

test("test errors are displayed inside the enter code popup itself", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });
    deactivateAllProgramsExcept(store, [3]);
    await Utils.clickDisplayedProduct("TEST");
    expect(Utils.getOrderTotal()).toInclude("115.00");
    await Utils.enterCode("INVALID_CODE");
    await Utils.checkErrorInPopup(
        'No coupon or gift card matches the code "INVALID_CODE". Check the code and try again.'
    );
    await Utils.cancelDialog("Discard", "Enter Code");
    await Utils.enterCode("EXISTING_CARD");
    await Utils.cancelDialog("Discard", "Unpaid gift card");
    await Utils.checkErrorInPopup(
        "This gift card was not applied because it is not linked to any order."
    );
    await Utils.cancelDialog("Discard", "Enter Code");
    expect(Utils.getOrderTotal()).toInclude("115.00");
});
