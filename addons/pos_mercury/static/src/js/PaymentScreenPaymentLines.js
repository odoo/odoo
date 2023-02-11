odoo.define('pos_mercury.PaymentScreenPaymentLines', function (require) {
    'use strict';

    const PaymentScreenPaymentLines = require('point_of_sale.PaymentScreenPaymentLines');
    const Registries = require('point_of_sale.Registries');

    const PosMercuryPaymentLines = (PaymentScreenPaymentLines) =>
        class extends PaymentScreenPaymentLines {
            /**
             * @override
             */
            selectedLineClass(line) {
                return Object.assign({}, super.selectedLineClass(line), {
                    o_pos_mercury_swipe_pending: line.mercury_swipe_pending,
                });
            }
            /**
             * @override
             */
            unselectedLineClass(line) {
                return Object.assign({}, super.unselectedLineClass(line), {
                    o_pos_mercury_swipe_pending: line.mercury_swipe_pending,
                });
            }
        };

    Registries.Component.extend(PaymentScreenPaymentLines, PosMercuryPaymentLines);

    return PaymentScreenPaymentLines;
});
