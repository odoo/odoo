import { animationFrame } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { clickControlButton } from "./product_screen_util";

export async function clickSplitButton() {
    await clickControlButton("Split");
}

export async function clickSplitOrderline(productName) {
    await contains(`.splitbill-screen .orderline .product-name:contains("${productName}")`).click();
    await animationFrame();
}

export async function clickSplitAction(buttonName) {
    await contains(`.splitbill-screen .pay-button button:contains("${buttonName}")`).click();
    await animationFrame();
}
