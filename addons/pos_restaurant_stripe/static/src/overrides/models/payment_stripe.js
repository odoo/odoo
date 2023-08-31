/** @odoo-module */

import { PaymentStripe } from "@pos_stripe/app/payment_stripe";
import { patch } from "@web/core/utils/patch";

patch(PaymentStripe.prototype, {
    async captureAfterPayment(processPayment, line) {
        // Don't capture if the customer can tip, in that case we
        // will capture later.
        if (!this.canBeAdjusted(line.cid)) {
            return super.captureAfterPayment(...arguments);
        }
    },

    canBeAdjusted(cid) {
        var order = this.pos.get_order();
        var line = order.get_paymentline(cid);
        return (
            this.pos.config.set_tip_after_payment &&
            line.payment_method.use_payment_terminal === "stripe" &&
            line.card_type !== "interac"
        );
    },
});
