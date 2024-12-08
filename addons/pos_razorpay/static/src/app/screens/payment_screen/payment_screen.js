import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";

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
    addNewPaymentLine(paymentMethod) {
        if (paymentMethod.use_payment_terminal === "razorpay" && this.isRefundOrder) {
            const refundedOrder = this.currentOrder.lines[0]?.refunded_orderline_id?.order_id;
            const razorpayPaymentlines = refundedOrder.payment_ids.filter(
                (pi) => pi.payment_method_id.use_payment_terminal === "razorpay"
            );
            const transactions_ids = this.currentOrder.payment_ids.map((pi) => pi.transaction_id);
            const res = super.addNewPaymentLine(paymentMethod);
            const newPaymentLine = this.paymentLines.at(-1);
            if (
                res &&
                (razorpayPaymentlines.length !== 1 ||
                    Math.abs(newPaymentLine.amount) < razorpayPaymentlines[0].amount ||
                    newPaymentLine.amount === 0 ||
                    transactions_ids.includes(newPaymentLine.transaction_id))
            ) {
                this.deletePaymentLine(newPaymentLine.uuid);
                return false;
            }
            if (res) {
                newPaymentLine.setAmount(-razorpayPaymentlines[0].amount);
                newPaymentLine.updateRefundPaymentLine(razorpayPaymentlines[0]);
            }
            return res;
        } else {
            return super.addNewPaymentLine(paymentMethod);
        }
    },
});
