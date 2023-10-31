odoo.define('pos_restaurant.PaymentInterface', function (require) {
    "use strict";

    var PaymentInterface = require('point_of_sale.PaymentInterface');

    PaymentInterface.include({
        /**
         * Return true if the amount that was authorized can be modified,
         * false otherwise
         * @param {string} cid - The id of the paymentline
         */
        canBeAdjusted(cid) {
            return false;
        },

        /**
         * Called when the amount authorized by a payment request should
         * be adjusted to account for a new order line, it can only be called if
         * canBeAdjusted returns True
         * @param {string} cid - The id of the paymentline
         */
        send_payment_adjust: function (cid) {},
    });
});
