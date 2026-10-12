import { expect } from "@odoo/hoot";
import { animationFrame, waitFor } from "@odoo/hoot-dom";
import { contains, getService } from "@web/../tests/web_test_helpers";

export function isMobile() {
    return getService("ui").isSmall;
}

export async function mountSelfOrderApp(store) {
    await animationFrame();
}

export async function clickBtn(buttonName) {
    await contains(`.btn:contains('${buttonName}')`).click();
    await animationFrame();
}

export async function hasBtn(buttonName) {
    waitFor(`.btn:contains(${buttonName})`);
}

export async function checkBtn(text) {
    await waitFor(`.btn:contains('${text}')`);
}

export async function checkIsNoBtn(text) {
    expect(`.btn:contains('${text}')`).toHaveCount(0);
}

export async function checkIsDisabledBtn(text) {
    await waitFor(`button.disabled:contains("${text}")`);
}

export function negateStep(text) {
    expect(`.btn:contains('${text}')`).toHaveCount(0);
}

export async function fillInput(placeholder, value) {
    await contains(`input[placeholder="${placeholder}"]`).edit(value);
    await animationFrame();
}

export async function clickBack() {
    await contains(".btn.btn-back").click();
    await animationFrame();
}

export const page = {
    isLanding: () => waitFor(".o_pos_landing_footer"),
    isEatingLocation: () => waitFor(".o_self_eating_location_box"),
    isProductList: () => waitFor(".o_self_product_list_page"),
    isProduct: () => waitFor(".o_self_product_page"),
    isCombo: () => waitFor(".o_self_combo_page"),
    isOptionalProduct: () => waitFor(".o_self_optional_product_page"),
    isConfirmation: () => waitFor(".confirmation-page"),
};
