import { test, expect } from "@odoo/hoot";
import { animationFrame, mockDate } from "@odoo/hoot-mock";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { getFilledOrder, setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { ManageGiftCardPopup } from "@pos_loyalty/app/components/popups/manage_giftcard_popup/manage_giftcard_popup";

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

test("checkGiftCard notifies the cashier when the connection is lost", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);

    await mountWithCleanup(MainComponentsContainer);
    const popup = await mountWithCleanup(ManageGiftCardPopup, {
        props: {
            line: order.lines[0],
            title: "Sell/Manage physical gift card",
            getPayload: () => {},
            close: () => {},
        },
    });

    store.data.network.offline = true;
    popup.state.inputValue = "1234";
    popup.state.loading = true;

    expect(await popup.checkGiftCard()).toBe(true);
    await animationFrame();

    expect(".o_notification").toHaveCount(1);
    expect(".o_notification_content").toHaveText("An error occurred while checking the gift card.");
    expect(popup.state.loading).toBe(false);
});
