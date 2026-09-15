import { expect } from "@odoo/hoot";
import { animationFrame, queryAll, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";

export async function clickOrderNow() {
    await contains(".btn:contains('Order Now'), .btn:contains('Order now')").click();
    await animationFrame();
}

export async function clickProduct(name) {
    await contains(`.product_list .o_self_product_box span:contains('${name}')`).click();
    await animationFrame();
}

export async function clickCategory(name) {
    await contains(`.category_btn:contains('${name}')`).click();
    await animationFrame();
}

export async function clickBtn(buttonName) {
    await contains(`.btn:contains('${buttonName}')`).click();
    await animationFrame();
}

export async function checkConfirmationPage() {
    await waitFor(".confirmation-page");
}

export async function checkPaymentPage() {
    await waitFor(".payment-page");
}

export async function checkIsNoBtn(text) {
    expect(`.btn:contains('${text}')`).toHaveCount(0);
}

export async function checkSlotDisabled(slotValue) {
    await waitFor(".select_popup_preset_info");
    const slots = queryAll(".select_popup_preset_info .slot-select option");
    expect(slots.some((slot) => slot.textContent.trim() === slotValue && slot.disabled)).toBe(true);
}

export async function clickCartButton(buttonName) {
    await contains(`.cart.btn:contains('${buttonName}')`).click();
    await animationFrame();
}
