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
});
