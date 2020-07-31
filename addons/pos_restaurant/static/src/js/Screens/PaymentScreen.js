odoo.define('pos_restaurant.PosResPaymentScreen', function (require) {
    'use strict';

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');

    const PosResPaymentScreen = (PaymentScreen) =>
        class extends PaymentScreen {
            get nextScreen() {
                return this.env.pos.config.set_tip_after_payment && !this.currentOrder.is_tipped ? 'TipScreen' : super.nextScreen;
            }
        };

    Registries.Component.extend(PaymentScreen, PosResPaymentScreen);

    return PosResPaymentScreen;
});
