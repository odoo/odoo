odoo.define('pos_mercury.OrderReceipt', function(require) {
    'use strict';

    const OrderReceipt = require('point_of_sale.OrderReceipt');
    const Registries = require('point_of_sale.Registries');

    const PosMercuryOrderReceipt = OrderReceipt =>
        class extends OrderReceipt {
            /**
             * The receipt has signature if one of the paymentlines
             * is paid with mercury.
             */
            get hasPosMercurySignature() {
                for (let line of this.paymentlines) {
                    if (line.mercury_data) return true;
                }
                return false;
            }
        };

    Registries.Component.extend(OrderReceipt, PosMercuryOrderReceipt);

    return OrderReceipt;
});
