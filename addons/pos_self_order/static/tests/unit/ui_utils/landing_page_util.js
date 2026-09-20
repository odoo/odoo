import { expect } from "@odoo/hoot";
import { animationFrame, waitFor, queryFirst, delay } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { clickBtn } from "./common";

export async function clickOrderNow() {
    await contains(".btn:contains('Order Now'), .btn:contains('Order now')").click();
    await animationFrame();
}

export async function clickMyOrder() {
    await contains(".btn:contains('My Order'), .btn:contains('My Orders')").click();
    await animationFrame();
}

export async function clickMyOrders() {
    await clickBtn("My Orders");
}

export async function checkIsClosed() {
    await waitFor(".o-self-closed");
}

export async function checkIsOpened() {
    expect(".o-self-closed").toHaveCount(0);
}

export async function checkCarouselAutoPlaying() {
    await waitFor(".carousel-item.active");
    const firstSlideHtml = queryFirst(".carousel-item.active")?.outerHTML;
    await delay(250);
    const currentSlideHtml = queryFirst(".carousel-item.active")?.outerHTML;
    if (firstSlideHtml === currentSlideHtml) {
        throw new Error("Slideshow is not working. Slide should change in all self ordering mode.");
    }
}
