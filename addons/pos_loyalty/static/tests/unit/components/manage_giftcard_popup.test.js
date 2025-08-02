import { describe, test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { ManageGiftCardPopup } from "@pos_loyalty/app/components/popups/manage_giftcard_popup/manage_giftcard_popup";

definePosModels();

describe("manage_giftcard_popup.js", () => {
    test("should validate inputs and call getPayload with correct values", async () => {
        await setupPosEnv();

        let payloadResult = null;

        const popup = await mountWithCleanup(ManageGiftCardPopup, {
            props: {
                title: "Add Balance",
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

        popup.state.inputValue = "GC-001";
        popup.state.amountValue = "100";
        popup.state.error = false;
        popup.state.amountError = false;

        await popup.addBalance();

        expect(payloadResult.code).toBe("GC-001");
        expect(payloadResult.amount).toBe(100);
        expect(typeof payloadResult.expDate).toBe("string");
        expect(payloadResult.expDate).toMatch(/^\d{4}-\d{2}-\d{2}/);
    });
});
