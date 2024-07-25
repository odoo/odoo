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
            const razorpayPaymentlines = refundedOrder.payment_ids.filter(
                (pi) => pi.payment_method_id.use_payment_terminal === "razorpay"
            );
            const current_due = this.currentOrder.getDue();
            if (
                razorpayPaymentlines.length !== 1 ||
                Math.abs(current_due) < razorpayPaymentlines[0].amount ||
                current_due === 0
            ) {
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
            if (res) {
                newPaymentLine.setAmount(-razorpayPaymentlines[0].amount);
                newPaymentLine.updateRefundPaymentLine(razorpayPaymentlines[0]);
            }
            return res;
        } else {
            return await super.addNewPaymentLine(paymentMethod);
        }
    },
});
