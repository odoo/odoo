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
            if (Math.abs(currentOrder.totalDue) === refundedOrder.amount_total) {
                paymentIds.forEach((pi) => {
                    if (pi.payment_method_id) {
                        const result = currentOrder.addPaymentline(pi.payment_method_id);
                        if (!result.status) {
                            return;
                        }

                        result.data.setAmount(-pi.amount);
                        result.data.updateRefundPaymentLine(pi);
                    }
                });
            } else {
                // Add available payment lines of refunded order based on conditions.
                // Settle current order terminal based payment lines with refunded order terminal based payment lines
                const razorpayPaymentlines = paymentIds.filter(
                    (pi) => pi.payment_method_id.use_payment_terminal === "razorpay"
                );
                razorpayPaymentlines.forEach((pi) => {
                    const currentDue = currentOrder.remainingDue;
                    if (currentDue < 0) {
                        const result = currentOrder.addPaymentline(pi.payment_method_id);
                        if (!result.status) {
                            return false;
                        }

                        result.data.setAmount(-Math.min(Math.abs(currentDue), pi.amount));
                        result.data.updateRefundPaymentLine(pi);
                    }
                });
                if (currentOrder.remainingDue < 0) {
                    paymentIds.forEach((pi) => {
                        const currentDue = currentOrder.remainingDue;
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
