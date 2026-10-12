import { animationFrame } from "@odoo/hoot-dom";
import { contains, getService } from "@web/../tests/web_test_helpers";

export function isMobile() {
    return getService("ui").isSmall;
}

export async function ensurePane(targetPane) {
    if (!isMobile()) {
        return;
    }
    const pos = getService("pos");
    if (pos.mobile_pane !== targetPane) {
        pos.switchPane();
        await animationFrame();
    }
}

export async function clickDisplayedProduct(name) {
    await ensurePane("right");
    await contains(`article.product .product-name:contains("${name}")`).click();
    await animationFrame();
}

export async function clickFastPaymentMethod(name) {
    await ensurePane("right");
    await contains(`.fast-pay-button:contains("${name}")`).click();
    await animationFrame();
}
