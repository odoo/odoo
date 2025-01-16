import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    async pay() {
        const currentOrder = this.getOrder();
        const refundedOrder = currentOrder?.lines[0]?.refunded_orderline_id?.order_id;
        const razorpayPaymentMethod = currentOrder.config_id.payment_method_ids.find(
            (pm) => pm.use_payment_terminal === "razorpay"
        );
        await super.pay();
        if (razorpayPaymentMethod && refundedOrder) {
            const paymentIds = refundedOrder.payment_ids || [];
            // Add all the available payment lines in the refunded order if the current order amount is the same as the refunded order
            if (Math.abs(currentOrder.getTotalDue()) === refundedOrder.amount_total) {
                paymentIds.forEach((pi) => {
                    if (pi.payment_method_id) {
                        const paymentLine = currentOrder.addPaymentline(pi.payment_method_id);
                        paymentLine.setAmount(-pi.amount);
                        paymentLine.updateRefundPaymentLine(pi);
                    }
                });
            } else {
                // Add available payment lines of refunded order based on conditions.
                // Settle current order terminal based payment lines with refunded order terminal based payment lines
                const razorpayPaymentlines = paymentIds.filter(
                    (pi) => pi.payment_method_id.use_payment_terminal === "razorpay"
                );
                razorpayPaymentlines.forEach((pi) => {
                    const currentDue = currentOrder.getDue();
                    if (currentDue < 0) {
                        const paymentLine = currentOrder.addPaymentline(pi.payment_method_id);
                        paymentLine.setAmount(-Math.min(Math.abs(currentDue), pi.amount));
                        paymentLine.updateRefundPaymentLine(pi);
                    }
                });
                if (currentOrder.getDue() < 0) {
                    paymentIds.forEach((pi) => {
                        const currentDue = currentOrder.getDue();
                        if (
                            currentDue < 0 &&
                            pi.payment_method_id &&
                            pi.payment_method_id.use_payment_terminal !== "razorpay"
                        ) {
                            currentOrder
                                .addPaymentline(pi.payment_method_id)
                                .setAmount(-Math.min(Math.abs(currentDue), pi.amount));
                        }
                    });
                }
            }
        }
    },
});
