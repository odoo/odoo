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
                    !paymentLine.isSettled &&
                    paymentLine.payment_status !== "pending"
            );
            if (waitingPaymentLine) {
                waitingPaymentLine.payment_status = "waiting_card";
                const payment_status =
                    await waitingPaymentLine.payment_method_id.payment_interface._waitForPaymentToConfirm();
                if (payment_status?.resultCode === "00") {
                    waitingPaymentLine.payment_status = "done";
                } else if (payment_status?.inProgress) {
                    waitingPaymentLine.payment_status = "waiting_card";
                } else {
                    waitingPaymentLine.payment_status = "retry";
                }
            }
        });
    },
});
