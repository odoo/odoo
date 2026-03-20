import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        onMounted(async () => {
            const waitingPaymentLine = this.currentOrder.payment_ids.find(
                (paymentLine) =>
                    paymentLine.payment_method_id.use_payment_terminal === "pine_labs" &&
                    !paymentLine.isDone() &&
                    paymentLine.setPaymentStatus() !== "pending"
            );
            if (waitingPaymentLine) {
                waitingPaymentLine.setPaymentStatus("waitingCard");
                const payment_status =
                    await waitingPaymentLine.payment_method_id.payment_terminal._waitForPaymentToConfirm();
                if (payment_status?.status === "TXN APPROVED") {
                    waitingPaymentLine.setPaymentStatus("done");
                    this.pos.paymentTerminalInProgress = false;
                } else if (payment_status?.status === "TXN UPLOADED") {
                    waitingPaymentLine.setPaymentStatus("waitingCard");
                } else {
                    waitingPaymentLine.setPaymentStatus("retry");
                    this.pos.paymentTerminalInProgress = false;
                }
            }
        });
    },
});
