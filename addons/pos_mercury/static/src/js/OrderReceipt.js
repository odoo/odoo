odoo.define('pos_mercury.OrderReceipt', function (require) {
    'use strict';

    const OrderReceipt = require('point_of_sale.OrderReceipt');
    const { patch } = require('web.utils');

    patch(OrderReceipt.prototype, 'pos_mercury', {
        /**
         * The receipt has signature if one of the payments
         * is paid with mercury.
         */
        hasPosMercurySignature(receipt) {
            for (const payment of receipt.paymentlines) {
                if (payment.mercury_data) return true;
            }
            return false;
        },
    });

    return OrderReceipt;
});
