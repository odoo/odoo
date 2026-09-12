import { animationFrame, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { sendBufferKeys } from "@point_of_sale/../tests/unit/ui_utils";
import { ONLINE_PAYMENT_METHOD_ID } from "@pos_online_payment/../tests/unit/data/pos_payment_method.data";

export const ONLINE_PAYMENT_POS_CONFIG = {
    module_pos_restaurant: false,
    set_tip_after_payment: false,
    available_preset_ids: [],
};

function getOnlinePaymentMethod(store, customerRequired) {
    if (!customerRequired) {
        return store.models["pos.payment.method"].get(ONLINE_PAYMENT_METHOD_ID);
    }
    return store.models["pos.payment.method"].create({
        name: "Online payment",
        type: "online",
        payment_method_type: "none",
        sequence: 3,
        _customer_required: true,
    });
}

export function addOnlinePaymentMethod(store, { customerRequired = false, only = false } = {}) {
    const method = getOnlinePaymentMethod(store, customerRequired);
    store.config.payment_method_ids = only
        ? [method]
        : [...store.config.payment_method_ids.filter((pm) => pm.type !== "online"), method];
}

export function setFlatProductPrice(store, price) {
    store.models["product.pricelist.item"].get(1).fixed_price = price;
    store.models["product.template"].get(5).taxes_id = [];
}

export async function selectCustomerOnPaymentScreen(name) {
    await contains(".payment-screen .partner-button").click();
    await waitFor(".partner-list");
    await contains(`.partner-info:contains("${name}")`).click();
    await animationFrame();
}

export function getOnlinePaymentLines(order) {
    return order.payment_ids.filter((line) => line.payment_method_id.type === "online");
}

function paymentlineSelector(name, amount) {
    return `.paymentlines .paymentline .payment-infos:has(.payment-name:contains("${name}")):has(.payment-amount:contains("${amount}"))`;
}

export async function clickPaymentline(name, amount) {
    await contains(paymentlineSelector(name, amount)).click();
    await animationFrame();
}

export async function deletePaymentline(name, amount) {
    await contains(`${paymentlineSelector(name, amount)} ~ .delete-button`).click();
    await animationFrame();
}

export async function enterPaymentlineAmount(amount) {
    await sendBufferKeys(...amount.toString().split(""));
}

export function isValidateHighlighted() {
    return Boolean(document.querySelector(".payment-screen .validation-button.next.highlight"));
}
