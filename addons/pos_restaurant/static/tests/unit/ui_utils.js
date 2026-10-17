import { animationFrame, waitFor, press } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import {
    clickControlButton,
    ensurePane,
    clickPaymentMethod,
    enterNumpadValue,
    isMobile,
    clickPaymentline,
} from "@point_of_sale/../tests/unit/ui_utils";

export async function clickTable(name) {
    await contains(`.o_fp_canvas .o_fp_table:has(.o_fp_table_number:contains("${name}"))`).click();
    await animationFrame();
}

export async function clickTableById(tableId) {
    await contains(`.o_fp_table[data-table_id='${tableId}']`).click();
    await animationFrame();
}

export async function clickFloor(name) {
    await contains(`.floor-selector .button-floor:contains("${name}")`).click();
    await animationFrame();
}

export async function clickPlanButton() {
    await contains(".table-button").click();
    await animationFrame();
}

export async function clickCourseButton() {
    await ensurePane("left");
    await clickControlButton("Course");
    await animationFrame();
}

export async function clickFireCourseButton() {
    await ensurePane("left");
    await contains(".actionpad .fire-btn").click();
    await animationFrame();
}

export async function clickTransferButton() {
    await clickControlButton("Transfer");
    await animationFrame();
}

export async function setGuestCount(count) {
    await clickControlButton("Guest");
    await waitFor(".modal .numpad");
    for (const d of count.toString().split("")) {
        await contains(`.modal .numpad button:contains("${d}")`).click();
        await animationFrame();
    }
    await press("Enter");
    await animationFrame();
}

export async function clickSplitAndPay() {
    await contains(".o_split_and_pay_button").click();
    await animationFrame();
}

export async function splitAndPay(paymentMethod, amount) {
    await clickPaymentMethod(paymentMethod);
    await animationFrame();
    if (isMobile()) {
        await clickPaymentline();
        await animationFrame();
    }
    await enterNumpadValue(amount);
    if (isMobile()) {
        await press("Enter");
    }
    await animationFrame();
    await clickSplitAndPay();
}

export function isSplitAndPayButtonShown() {
    return Boolean(document.querySelector(".o_split_and_pay_button"));
}
