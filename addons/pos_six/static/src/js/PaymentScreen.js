odoo.define('pos_six.PaymentScreen', function (require) {
    'use strict';

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');

    const PosSixPaymentScreen = (PaymentScreen) =>
        class extends PaymentScreen {

            /**
             * @override
             */
            deletePaymentLine(event) {
                const line = this.paymentLines.find((line) => line.cid === event.detail.cid);
                if (line.payment_method && line.payment_method.use_payment_terminal === 'six') {
                    this.payment_interface.terminal.logoutAsync()
                }
                super.deletePaymentLine(event);
            }
        };

    Registries.Component.extend(PaymentScreen, PosSixPaymentScreen);

    return PaymentScreen;
});
