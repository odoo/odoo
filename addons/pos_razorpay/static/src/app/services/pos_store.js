import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    async pay() {
        const currentOrder = this.getOrder();
        const refundedOrder = currentOrder?.lines[0]?.refunded_orderline_id?.order_id;
        const razorpayPaymentlines = refundedOrder?.payment_ids.filter(
            (pi) => pi.payment_method_id.use_payment_terminal === "razorpay"
        );
        const reazorpayPaymentMethod = currentOrder.config_id.payment_method_ids.find(
            (pm) => pm.use_payment_terminal === "razorpay"
        );
        await super.pay();
        if (reazorpayPaymentMethod && refundedOrder && razorpayPaymentlines?.length === 1) {
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
                const getTotalDue = currentOrder.getTotalDue();
                if (getTotalDue < 0 && Math.abs(getTotalDue) > razorpayPaymentlines[0].amount) {
                    const paymentLine = currentOrder.addPaymentline(
                        razorpayPaymentlines[0].payment_method_id
                    );
                    paymentLine.setAmount(-razorpayPaymentlines[0].amount);
                    paymentLine.updateRefundPaymentLine(razorpayPaymentlines[0]);
                }
                if (currentOrder.getDue() < 0) {
                    paymentIds.forEach((pi) => {
                        const current_due = currentOrder.getDue();
                        if (
                            current_due < 0 &&
                            pi.payment_method_id &&
                            !pi.payment_method_id.use_payment_terminal
                        ) {
                            currentOrder
                                .addPaymentline(pi.payment_method_id)
                                .setAmount(current_due);
                        }
                    });
                }
            }
        }
    },
});
