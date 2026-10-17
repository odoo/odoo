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
<<<<<<< 59e583a17c7a2cbca7219e71c4275d7753128de9

export async function selectTicketFilter(filterName) {
    await contains(".ticket-screen .filter").click();
    await animationFrame();
    await contains(`.dropdown-item:contains("${filterName}")`).click();
    await animationFrame();
}
||||||| bf6e680e0f385e5ae1a0ae4005a98708828b0d3c
=======

export async function clickFastPaymentMethod(name) {
    await ensurePane("right");
    await contains(`.fast-pay-button:contains("${name}")`).click();
    await animationFrame();
}
>>>>>>> b70d0c58ceed59be62d8329a33a6cedf870988db
