import { test, expect } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { createOrderWithLoyalty } from "@pos_loyalty/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { ManageGiftCardPopup } from "@pos_loyalty/app/components/popups/manage_giftcard_popup/manage_giftcard_popup";

definePosModels();

test("addBalance", async () => {
    const store = await setupPosEnv();

    mockDate("2025-02-01 00:00:00");

    let payloadResult = null;

    const order = await createOrderWithLoyalty(store, [
        { product: store.models["product.product"].get(5), qty: 1, price: 10 },
    ]);

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

    await popup.addBalance();

    expect(payloadResult.code).toBe("101");
    expect(payloadResult.amount).toBe(100);
    expect(payloadResult.expDate).toBe("2026-02-01");
});
