import { animationFrame, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";

export async function clickNewOrder() {
    await contains(".floor-screen .btn-new-order").click();
    await animationFrame();
}

export async function clickOrders() {
    await contains(".pos-leftheader .orders-button").click();
    await animationFrame();
}

export async function clickRegister() {
    await contains(".pos-leftheader .register-label").click();
    await animationFrame();
}

export async function createFloatingOrder() {
    await contains(".pos-leftheader .list-plus-btn").click();
    await waitFor(".product-screen");
    await animationFrame();
}

export async function clickFloatingOrder(name) {
    const button = `.floating-order-container button:contains("${name}")`;
    const toggle = document.querySelector(".pos-leftheader .list-container-items > button");
    if (toggle) {
        await contains(toggle).click();
        await waitFor(".modal .list-container-items");
        await contains(`.modal ${button}`).click();
    } else {
        await contains(`.pos-leftheader ${button}`).click();
    }
    await animationFrame();
}
