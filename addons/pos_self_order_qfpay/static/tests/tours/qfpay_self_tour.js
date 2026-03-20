/* global posmodel */
import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";
import { patch } from "@web/core/utils/patch";
import { QFPay } from "@pos_qfpay/app/qfpay";
import { mockQFPayWebhook } from "@pos_qfpay/../tests/tours/utils/common";

// Patch QFPay to validate the request that would be sent to the terminal
patch(QFPay.prototype, {
    makeQFPayRequest: async function (endpoint, payload) {
        if (endpoint !== "trade") {
            throw new Error("Only 'trade' endpoint is supported on self checkout");
        }
        const paymentMethod = posmodel.models["pos.payment.method"].getAll()[0];
        const order = posmodel.currentOrder;
        const sessionId = posmodel.config.current_session_id.id;
        const expectedPayload = {
            func_type: 1001,
            amt: order.amount_total,
            channel: paymentMethod.qfpay_payment_type,
            out_trade_no: `${order.uuid}--${sessionId}--${paymentMethod.id}`,
            wait_card_timeout: 30,
            camera_id: 1,
        };
        if (!payload || JSON.stringify(payload) !== JSON.stringify(expectedPayload)) {
            throw new Error("Payload does not match expected payload");
        }
        return true;
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
