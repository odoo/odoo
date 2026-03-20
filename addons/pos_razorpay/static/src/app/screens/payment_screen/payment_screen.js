import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        onMounted(async () => {
            const pendingPaymentLine = this.currentOrder.payment_ids.find(
                (paymentLine) =>
                    paymentLine.payment_method_id.use_payment_terminal === "razorpay" &&
                    !paymentLine.isDone() &&
                    paymentLine.getPaymentStatus() !== "pending"
            );
            if (pendingPaymentLine) {
                const payment_status =
                    await pendingPaymentLine.payment_method_id.payment_terminal._waitForPaymentConfirmation();
                if (payment_status?.status === "AUTHORIZED") {
                    pendingPaymentLine.setPaymentStatus("done");
                } else {
                    pendingPaymentLine.setPaymentStatus("force_done");
                }
            }
        });
    },
    async addNewPaymentLine(paymentMethod) {
        if (paymentMethod.use_payment_terminal === "razorpay" && this.isRefundOrder) {
            const refundedOrder = this.currentOrder.lines[0]?.refunded_orderline_id?.order_id;
            if (!refundedOrder) {
                return false;
            }
            const transactionsIds = this.currentOrder.payment_ids.map(
                (pi) => pi.uiState.transaction_id
            );
            const razorpayPaymentline = refundedOrder.payment_ids.find(
                (pi) =>
                    pi.payment_method_id.use_payment_terminal === "razorpay" &&
                    !transactionsIds.find((x) => x === pi.transaction_id)
            );
            const currentDue = this.currentOrder.remainingDue;
            if (!razorpayPaymentline || currentDue === 0) {
                this.pos.notification.add(
                    _t(
                        "Adding a new Razorpay payment line is not allowed under the current conditions."
                    ),
                    { type: "warning", sticky: false }
                );
                return false;
            }
            const res = await super.addNewPaymentLine(paymentMethod);
            const newPaymentLine = this.paymentLines.at(-1);
            const amountToSet = Math.min(
                Math.abs(newPaymentLine.amount),
                razorpayPaymentline.amount
            );
            if (res) {
                newPaymentLine.setAmount(-amountToSet);
                newPaymentLine.updateRefundPaymentLine(razorpayPaymentline);
            }
            return res;
        } else {
            return await super.addNewPaymentLine(paymentMethod);
        }
    },
});
