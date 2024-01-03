/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        onMounted(() => {
            const pendingPaymentLine = this.currentOrder.payment_ids.find(
                (paymentLine) =>
                    paymentLine.payment_method_id.use_payment_terminal === "paytm" &&
                    !paymentLine.is_done() &&
                    paymentLine.get_payment_status() !== "pending"
            );
            if (pendingPaymentLine) {
                pendingPaymentLine.set_payment_status("force_done");
            }
        });
    },
});
