import { test, expect } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { waitFor } from "@odoo/hoot-dom";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import {
    getFilledOrder,
    setupPosEnv,
    setupAndMountPosApp,
} from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { ManageGiftCardPopup } from "@pos_loyalty/app/components/popups/manage_giftcard_popup/manage_giftcard_popup";
import { deactivateAllProgramsExcept } from "@pos_loyalty/../tests/unit/utils";
import * as PosUiUtils from "@point_of_sale/../tests/unit/ui_utils";
import * as LoyaltyUiUtils from "@pos_loyalty/../tests/unit/ui_utils";
const Utils = { ...PosUiUtils, ...LoyaltyUiUtils };

definePosModels();

test("addBalance", async () => {
    const store = await setupPosEnv();

    // Freeze current date so luxon.DateTime.now() is fixed
    mockDate("2025-01-01");

    let payloadResult = null;

    const order = await getFilledOrder(store);
    const popup = await mountWithCleanup(ManageGiftCardPopup, {
        props: {
            line: order.lines[0],
            title: "Sell/Manage physical gift card",
            getPayload: (code, amount, expDate) => {
                payloadResult = { code, amount, expDate };
            },
            close: () => {},
        },
    });

    popup.state.inputValue = "";
    popup.state.amountValue = "";
    const valid = popup.validateCode();

    expect(valid).toBe(false);
    expect(popup.state.error).toBe(true);

    popup.state.inputValue = "101";
    popup.state.amountValue = "100";
    popup.state.error = false;
    popup.state.amountError = false;

    await popup.addBalance();

    expect(payloadResult.code).toBe("101");
    expect(payloadResult.amount).toBe(100);
    // expiration is +1 year
    expect(payloadResult.expDate).toBe("2026-01-01");
});

test("test errors are displayed inside the popup itself", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });
    deactivateAllProgramsExcept(store, [3]);
    store.models["loyalty.program"].get(3).trigger_product_ids = [201];
    await Utils.clickDisplayedProduct("Gift Card");
    await Utils.clickSellPhysicalGiftCard();
    await Utils.editManageGiftCardPopup({ code: 1234567890 }, true);
    await Utils.clickDisplayedProduct("Gift Card");
    await Utils.clickSellPhysicalGiftCard();
    await Utils.editManageGiftCardPopup({ code: "CARD004" }, false);
    await Utils.checkErrorInPopup("No gift card matches this code. Check the code and try again.");
    // The rejected code stays in the input so it can be corrected, and it cannot be submitted
    expect(".modal input#code").toHaveValue("CARD004");
    await waitFor(".modal button:disabled:contains(Add Balance)");
    await Utils.editManageGiftCardPopup({ code: "EXISTING_CARD" }, true, "Add existing Gift Card");
    await Utils.clickDisplayedProduct("Gift Card");
    await Utils.clickSellPhysicalGiftCard();
    await Utils.editManageGiftCardPopup({ code: "EXISTING_CARD" }, false);
    await Utils.checkErrorInPopup(
        "This code is already used by another gift card in this order. Enter a different code."
    );
    // Add Balance button should be disabled when there is an error
    await waitFor(".modal button:disabled:contains(Add Balance)");
});
