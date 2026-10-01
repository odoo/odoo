import { animationFrame, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { ensurePane, isMobile, queryEl } from "./common";

export async function clickPartnerButton() {
    await ensurePane("left");
    await contains(".product-screen .set-partner").click();
    await animationFrame();
    await waitFor(".partner-list");
}

export async function selectCustomer(name) {
    await clickPartnerButton();
    await contains(`.partner-info:contains("${name}")`).click();
    await animationFrame();
}

export async function checkSelectedCustomer(name) {
    if (!isMobile()) {
        await waitFor(`.set-partner:contains("${name}")`);
        await animationFrame();
    } else {
        await contains(".set-partner.btn-outline-secondary").click();
        await animationFrame();
        await queryEl(".partner-info .selected", name);
        await animationFrame();
        await contains(".modal-footer .btn-secondary").click();
        await animationFrame();
    }
}
