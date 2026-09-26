import { animationFrame, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { sendBufferKeys, setFlatProductPrice } from "@point_of_sale/../tests/unit/ui_utils";
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

// `setFlatProductPrice` writes the pricelist item owned by pricelist 2, which no
// order uses by default, so the flat price only applies once that pricelist is on
// the config (for the orders to come) and on the order already opened.
export function applyFlatProductPrice(store, price) {
    setFlatProductPrice(store, price);
    const pricelist = store.models["product.pricelist"].get(2);
    store.config.pricelist_id = pricelist;
    store.getOrder()?.setPricelist(pricelist);
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

export async function enterPaymentlineAmount(amount) {
    await sendBufferKeys(...amount.toString().split(""));
}

export function isValidateHighlighted() {
    return Boolean(document.querySelector(".payment-screen .validation-button.next.highlight"));
}
