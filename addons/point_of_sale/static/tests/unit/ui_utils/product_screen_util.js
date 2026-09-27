import { animationFrame, waitFor } from "@odoo/hoot-dom";
import { contains, getService } from "@web/../tests/web_test_helpers";
import { ensurePane, isMobile } from "./common";
import { clickNumpadButtons } from "./numpad_util";

export async function clickDisplayedProduct(name) {
    await ensurePane("right");
    await contains(`article.product .product-name:contains("${name}")`).click();
    await animationFrame();
}

export async function addOrderlineFromProductScreen(productName, { quantity = 1, unitPrice } = {}) {
    await clickDisplayedProduct(productName);

    if (unitPrice !== undefined) {
        await clickNumpadButtons("Price", unitPrice, "Qty");
    }
    if (quantity.toString() !== "1") {
        await clickNumpadButtons(quantity);
    }
}

export async function clickControlButton(label) {
    await ensurePane("left");
    const btn = [
        ...document.querySelectorAll(".control-buttons button, .control-button, .actionpad button"),
    ].find((el) => el.textContent.includes(label));
    if (btn) {
        await contains(btn).click();
    } else {
        if (isMobile()) {
            await contains(".product-screen .mobile-more-button").click();
        } else {
            await contains(".product-screen .more-btn").click();
        }
        await animationFrame();
        await contains(`.control-buttons-modal .control-button:contains("${label}")`).click();
    }
    await animationFrame();
}

export async function selectPreset(presetName) {
    await ensurePane("left");
    await contains(`.selection-item:contains("${presetName}")`).click();
    await animationFrame();
}

export async function clickOrderButton() {
    await ensurePane("left");
    await contains(".actionpad .submit-order").click();
    await animationFrame();
}

export async function clickPayButton() {
    await ensurePane("left");
    await contains(".actionpad .pay-order-button").click();
    await animationFrame();
}

export async function selectFiscalPosition(name) {
    await clickControlButton("Tax");
    await waitFor(".selection-item");
    await contains(`.selection-item:contains("${name}")`).click();
    await animationFrame();
}

export async function addCustomerNote(text) {
    await clickControlButton("Customer Note");
    await waitFor(".modal textarea");
    await contains(".modal textarea").edit(text);
    await contains(".modal .btn-primary").click();
    await animationFrame();
}

export async function clickRefundButton() {
    await clickControlButton("Refund");
    await animationFrame();
}

export async function scanBarcode(barcode) {
    getService("barcode").bus.trigger("barcode_scanned", { barcode });
    await animationFrame();
    await animationFrame();
}

export function setFlatProductPrice(store, price) {
    store.models["product.pricelist.item"].get(1).fixed_price = price;
    store.models["product.template"].get(5).taxes_id = [];
}
