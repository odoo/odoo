import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        onMounted(async () => {
            const waitingPaymentLine = this.currentOrder.payment_ids.find(
                (paymentLine) =>
                    paymentLine.payment_method_id.payment_provider === "dpopay" &&
                    !paymentLine.isDone() &&
                    paymentLine.getPaymentStatus() !== "pending"
            );
            if (waitingPaymentLine) {
                waitingPaymentLine.setPaymentStatus("waitingCard");
                const payment_status =
                    await waitingPaymentLine.payment_method_id.payment_interface._waitForPaymentToConfirm();
                if (payment_status?.resultCode === "00") {
                    waitingPaymentLine.setPaymentStatus("done");
                } else if (payment_status?.inProgress) {
                    waitingPaymentLine.setPaymentStatus("waitingCard");
                } else {
                    waitingPaymentLine.setPaymentStatus("retry");
                }
            }
        });
    },
});
