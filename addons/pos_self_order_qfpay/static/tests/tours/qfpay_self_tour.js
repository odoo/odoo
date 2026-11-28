/* global posmodel */
import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";
import { patch } from "@web/core/utils/patch";
import { QFPay } from "@pos_qfpay/app/qfpay";
import { mockQFPayWebhook } from "@pos_qfpay/../tests/tours/utils/common";

// Mock the terminal: the payload is signed by the server, as for a real payment
patch(QFPay.prototype, {
    async sendRequest(endpoint, signedPayload) {
        if (endpoint !== "trade") {
            throw new Error("Only 'trade' endpoint is supported on self checkout");
        }
        if (typeof signedPayload !== "string" || !signedPayload) {
            throw new Error("The payload sent to the terminal is not signed");
        }
        return { respcd: "6000" };
    },
});

registry.category("web_tour.tours").add("kiosk_qfpay_order", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Letter Tray"),
        Utils.clickBtn("Checkout"),
        Utils.clickBtn("Pay"),
        Utils.checkIsNoBtn("Pay"),
        {
            content: "Waiting for Qfpay payment to be processed",
            trigger: "body:not(:has(.btn:text(Retry)))",
            run: async function () {
                const amount = posmodel.currentOrder.amount_total;
                const paymentMethodId = posmodel.models["pos.payment.method"].getAll()[0].id;
                mockQFPayWebhook(posmodel.currentOrder.uuid, paymentMethodId, amount, false);
            },
        },
        Utils.clickBtn("Close"),
    ],
});
