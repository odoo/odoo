import { animationFrame, tick, waitFor, queryAll } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { normalizeText } from "./common";
import { confirmDialog } from "./dialog_util";

export async function clickPaymentMethod(name, changeDefault = false) {
    if (changeDefault) {
        await selectDefaultPaymentMethod(name);
    }
    await contains(`.paymentmethod:contains("${name}")`).click();
    await animationFrame();
}

export async function selectDefaultPaymentMethod(name) {
    await contains(
        ".pos-leftheader button:has([data-icon='menu']), .pos-topheader button:has([data-icon='menu'])"
    ).click();
    await animationFrame();
    await contains(".o_pos_burger_menu_buttons button:contains('Payment Methods')").click();
    await selectDefaultPaymentMethodInPopup(name);
}

export async function selectDefaultPaymentMethodInPopup(name) {
    await contains(`.modal-body button:contains("${name}")`).click();
    await confirmDialog("Confirm");
}

export async function clickCurrencyWisePaymentMethod(name, currencyCode, amount) {
    await contains(
        `.paymentmethod:contains("${name}") + div .currency-wise-method:contains("${currencyCode}"):contains("${amount}")`
    ).click();
    await animationFrame();
}

export async function clickValidatePayment() {
    await contains(".payment-screen .validation-button.highlight").click();
    await tick();
    await animationFrame();
}

export async function selectedPaymentLineHasAmount(amount) {
    const selectedLine = document.querySelector(".paymentline.selected");
    const amountEl = selectedLine.querySelector(".payment-amount");
    const displayedAmount = amountEl.textContent.trim();
    return displayedAmount === amount;
}

function paymentlineSelector({ name, amount, nth, selected } = {}) {
    const selectedSelector = selected ? ".selected" : "";
    const nameSelector = name ? `:has(.payment-name:contains("${name}"))` : "";
    const amountSelector = amount ? `:has(.payment-amount:contains("${amount}"))` : "";
    const nthSelector = nth ? `:nth-of-type(${nth})` : "";

    return `.paymentlines .paymentline${nthSelector}${selectedSelector}${nameSelector}${amountSelector}`;
}

export async function clickPaymentline(opts) {
    await contains(`${paymentlineSelector(opts)} .payment-infos`).click();
    await animationFrame();
}

export async function deletePaymentline(opts) {
    await contains(`${paymentlineSelector(opts)} .delete-button`).click();
    await animationFrame();
}

export async function paymentScreenAmountTotal(amount) {
    await waitFor(`.paymentlines-container .total:contains('${amount}')`);
}

export async function paymentScreenRemainingTotal(amount) {
    await waitFor(`.payment-status-amount:contains(Remaining):contains('${amount}')`);
}

export function countPaymentlines() {
    return document.querySelectorAll(".paymentlines .paymentline").length;
}

export function selectedPaymentline() {
    const line = document.querySelector(".paymentlines .paymentline.selected");
    if (!line) {
        return null;
    }
    return {
        name: normalizeText(line.querySelector(".payment-name").textContent),
        amount: normalizeText(line.querySelector(".payment-amount").textContent),
    };
}

export function actionState() {
    const title = document.querySelector(".paymentline_status .paymentline_status_title");
    const state =
        title && [...title.classList].find((cls) => cls.startsWith("paymentline_status_title_"));
    return state ? state.slice("paymentline_status_title_".length) : null;
}

async function clickActionButton(id) {
    await contains(`.paymentline_status_actions .paymentline_status_actions_button_${id}`, {
        visible: false,
    }).click();
    await animationFrame();
    await animationFrame();
}

export async function clickSendButton() {
    await clickActionButton("send");
}

export async function clickRetryButton() {
    await clickActionButton("retry");
}

export async function clickCancelButton() {
    await clickActionButton("cancel");
}

export async function clickForceDoneButton() {
    await clickActionButton("force_done");
}

export function isQrPopupShown() {
    return Boolean(document.querySelector(".modal .o_qr_popup"));
}

export async function qrPopupAmount() {
    await waitFor(".modal .o_qr_popup .qr-code-amount");
    return normalizeText(document.querySelector(".modal .o_qr_popup .qr-code-amount").textContent);
}

export async function closeQrPopup() {
    await contains(".o_qr_popup .qr-code-popup-footer .cancel-button").click();
    await animationFrame();
}

export async function showQrPopup(opts) {
    await contains(`${paymentlineSelector(opts)} .paymentline_show_qr_code`).click();
    await animationFrame();
}

export function isShowQrPopupDisabled(opts) {
    return (
        queryAll(`${paymentlineSelector(opts)} .paymentline_show_qr_code[disabled]`).length === 1
    );
}
