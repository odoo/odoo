/** @odoo-module */

import { PaymentStripe } from "@pos_stripe/js/payment_stripe";
import { patch } from "@web/core/utils/patch";
// This patch needs to be applied after the patch from pos_restaurant
import "@pos_restaurant/js/payment";

patch(PaymentStripe.prototype, "pos_restaurant_stripe.PaymentStripe", {
    captureAfterPayment: async function (processPayment, line) {
        // Don't capture if the customer can tip, in that case we
        // will capture later.
        if (!this.canBeAdjusted(line.cid)) {
            return this._super(...arguments);
        }
    },

    canBeAdjusted: function (cid) {
        var order = this.pos.get_order();
        var line = order.get_paymentline(cid);
        return (
            this.pos.config.set_tip_after_payment &&
            line.payment_method.use_payment_terminal === "stripe"
        );
    },
});
