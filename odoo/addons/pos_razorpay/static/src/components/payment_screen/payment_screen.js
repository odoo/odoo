/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
            onMounted(async() => {
                const pendingPaymentLine = this.currentOrder.paymentlines.find(
                    paymentLine => paymentLine.payment_method.use_payment_terminal === 'razorpay' && (!paymentLine.is_done() && paymentLine.get_payment_status() !== 'pending')
                );
                if (pendingPaymentLine) {
                    const payment_status = await pendingPaymentLine.payment_method.payment_terminal._waitForPaymentConfirmation();
                    if (payment_status?.status === "AUTHORIZED") {
                        pendingPaymentLine.set_payment_status("done");
                    } else {
                        pendingPaymentLine.set_payment_status("force_done");
                    }
                }
            });
        }
});
