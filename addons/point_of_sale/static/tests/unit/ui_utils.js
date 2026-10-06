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

export async function clickOrderButton() {
    await ensurePane("left");
    await contains(".actionpad .submit-order").click();
    await animationFrame();
}
export async function clickBackButton() {
    await ensurePane("left");
    await contains(".actionpad .back-button").click();
}
