/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    get nextScreen() {
        const order = this.currentOrder;
        if (!this.pos.config.set_tip_after_payment || order.is_tipped) {
            return super.nextScreen;
        }
        // Take the first payment method as the main payment.
        const mainPayment = order.get_paymentlines()[0];
        if (mainPayment && mainPayment.canBeAdjusted()) {
            return "TipScreen";
        }
        return super.nextScreen;
    },
});
