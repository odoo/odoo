odoo.define('pos_restaurant.PosResPaymentScreen', function (require) {
    'use strict';

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');

    const PosResPaymentScreen = (PaymentScreen) =>
        class extends PaymentScreen {
            get nextScreen() {
                const order = this.currentOrder;
                if (!this.env.pos.config.set_tip_after_payment || order.is_tipped) {
                    return super.nextScreen;
                }
                // Take the first payment method as the main payment.
                const mainPayment = order.get_paymentlines()[0];
                if (mainPayment.canBeTipped()) {
                    return 'TipScreen';
                }
                return super.nextScreen;
            }
        };

    Registries.Component.extend(PaymentScreen, PosResPaymentScreen);

    return PosResPaymentScreen;
});
