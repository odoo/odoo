import { animationFrame, advanceTime, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { clickControlButton, ensurePane } from "@point_of_sale/../tests/unit/ui_utils";

export async function clickSellPhysicalGiftCard() {
    ensurePane("left");
    await contains(".info-list a:contains(Sell physical gift card?)").click();
    await animationFrame();
}

export async function editManageGiftCardPopup(
    steps = {},
    clickButton = true,
    buttonLabel = "Add Balance"
) {
    if (steps.code !== undefined) {
        await contains(".modal input#code").edit(steps.code);
        await animationFrame();
        await advanceTime(500);
    }
    if (steps.amount !== undefined) {
        await contains(".modal input#amount").edit(steps.amount);
        await animationFrame();
    }
    if (clickButton) {
        await contains(`.modal button:contains(${buttonLabel})`).click();
        await animationFrame();
        await advanceTime(500);
    }
}

export async function enterCode(code) {
    await clickControlButton("Enter Code");
    await waitFor(".modal textarea");
    await contains(".modal textarea").edit(code);
    await contains('.modal .btn-primary:contains("Apply")').click();
    await animationFrame();
}

export async function checkErrorInPopup(errorMessage) {
    await waitFor(`div.alert:contains(${errorMessage})`);
}
