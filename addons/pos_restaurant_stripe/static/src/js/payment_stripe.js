odoo.define('pos_restaurant_stripe.payment', function (require) {
    "use strict";

    var PaymentStripe = require('pos_stripe.payment');

    PaymentStripe.include({
        captureAfterPayment: async function (processPayment, line) {
            // Don't capture if the customer can tip, in that case we
            // will capture later.
            if (! this.canBeAdjusted(line.cid)) {
                return this._super(...arguments);
            }
        },

        canBeAdjusted: function (cid) {
            var order = this.pos.get_order();
            var line = order.get_paymentline(cid);
            return this.pos.config.set_tip_after_payment && line.payment_method.use_payment_terminal === "stripe";
        }
    });
});
