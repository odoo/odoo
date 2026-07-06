import { animationFrame, tick, waitFor, queryAll } from "@odoo/hoot-dom";
import { contains, getService, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { Chrome } from "@point_of_sale/app/pos_app";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

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

export async function ensureTicketPane(targetPane) {
    if (!isMobile()) {
        return;
    }
    const pos = getService("pos");
    if (pos.ticket_screen_mobile_pane !== targetPane) {
        pos.switchPaneTicketScreen();
        await animationFrame();
    }
}

export async function mountPosApp(store) {
    store.session.state = "opened";
    await mountWithCleanup(Chrome, { props: { disableLoader: () => {} } });
    await tick();
    await animationFrame();
}

export async function mountProductScreen(store) {
    return mountWithCleanup(ProductScreen, {
        props: { orderUuid: store.getOrder().uuid },
    });
}

export function queryEl(selector, text) {
    const els = document.querySelectorAll(selector);
    if (!text) {
        return els[0] || null;
    }
    for (const el of els) {
        if (el.textContent.includes(text)) {
            return el;
        }
    }
    return null;
}

export async function clickDisplayedProduct(name) {
    await ensurePane("right");
    await contains(`article.product .product-name:contains("${name}")`).click();
    await animationFrame();
}

export async function clickNumpad(key) {
    await ensurePane("left");
    const label = key === "backspace" ? "⌫" : key;
    await contains(`.numpad button:contains("${label}")`).click();
    await animationFrame();
}

export async function enterNumpadValue(value) {
    for (const char of value.toString().split("")) {
        await clickNumpad(char);
    }
}

export async function sendBufferKeys(...keys) {
    const numberBuffer = getService("number_buffer");
    for (const key of keys.flat()) {
        numberBuffer.sendKey(key);
    }
    numberBuffer.capture();
    await animationFrame();
}

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

export async function clickNewOrder() {
    await contains(".floor-screen .btn-new-order").click();
    await animationFrame();
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

export async function clickPaymentMethod(name) {
    await contains(`.paymentmethod:contains("${name}")`).click();
    await animationFrame();
}

export async function clickValidatePayment() {
    await contains(".payment-screen .validation-button.highlight").click();
    await tick();
    await animationFrame();
}

export async function clickNextOrder() {
    await contains(".feedback-screen .validation").click();
    await animationFrame();
}

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

export async function clickOrders() {
    await contains(".pos-leftheader .orders-button").click();
    await animationFrame();
}

export async function clickRegister() {
    await contains(".pos-leftheader .register-label").click();
    await animationFrame();
}

export async function selectTicketOrder(reference) {
    await ensureTicketPane("left");
    await contains(`.ticket-screen .order-row:contains("${reference}")`).click();
    await animationFrame();
}

export async function loadSelectedOrder() {
    if (isMobile()) {
        await ensureTicketPane("left");
        await contains(".ticket-screen .load-order-button").click();
    } else {
        await contains(".ticket-screen .pads .btn-primary").click();
    }
    await animationFrame();
}

export async function clickTicketReviewButton() {
    await ensureTicketPane("left");
    await contains(".ticket-screen .review-button").click();
    await animationFrame();
}

export async function clickTicketAction(buttonText) {
    await ensureTicketPane("right");
    await contains(`.ticket-screen .pads button:contains("${buttonText}")`).click();
    await animationFrame();
}

export async function clickTicketNumpad(key) {
    if (isMobile()) {
        await ensureTicketPane("right");
    }
    const label = key === "backspace" ? "⌫" : key;
    await contains(`.ticket-screen .numpad button:contains("${label}")`).click();
    await animationFrame();
}

export async function clickDeleteOrderOnTicket(orderRef) {
    await ensureTicketPane("left");
    if (orderRef) {
        await selectTicketOrder(orderRef);
    }
    if (isMobile()) {
        const row = document.querySelector(`.ticket-screen .order-row.highlight [name="delete"]`);
        if (row) {
            await contains(row).click();
        } else {
            await contains(`.ticket-screen .order-row.highlight .fa-trash`).click();
        }
    } else {
        if (orderRef) {
            await contains(
                `.ticket-screen .order-row:contains("${orderRef}") .delete-column button`
            ).click();
        } else {
            await contains(".ticket-screen .order-row .delete-column button").click();
        }
    }
    await animationFrame();
}

export async function confirmDialog(buttonText) {
    await waitFor(".modal");
    if (buttonText) {
        await contains(`.modal .btn:contains("${buttonText}")`).click();
    } else {
        await contains(".modal .btn-primary").click();
    }
    await animationFrame();
}

export async function cancelDialog() {
    await waitFor(".modal");
    await contains(".modal .btn-secondary").click();
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

export async function selectComboItem(productName) {
    await contains(
        `.modal label.combo-item article.product:has(.product-name:contains("${productName}"))`
    ).click();
    await animationFrame();
}

export async function confirmCombo() {
    await contains(".modal footer button.confirm").click();
    await animationFrame();
}

export async function clickOrderline(productName) {
    await ensurePane("left");
    await contains(`.orderline .product-name:contains("${productName}")`).click();
    await animationFrame();
}

export function getOrderTotal() {
    const el = document.querySelector(".order-summary .total");
    return el ? el.textContent.trim() : "";
}

export function getOrderlineNames() {
    return queryAll(".orderline .product-name").map((el) => el.textContent.trim());
}
