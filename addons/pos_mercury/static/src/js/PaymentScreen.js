odoo.define('pos_mercury.PaymentScreen', function (require) {
    'use strict';

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const { useBarcodeReader } = require('point_of_sale.custom_hooks');
    const { patch } = require('web.utils');

    patch(PaymentScreen.prototype, 'pos_mercury', {
        setup() {
            this._super(...arguments);
            if (this.env.model.getMercuryPaymentMethods().length !== 0) {
                useBarcodeReader(this.env.model.barcodeReader, {
                    credit: this._onCardSwipe,
                });
            }
        },
        /**
         * Handles card swipe.
         * Automatically creates a mercury payment if there is no active payment.
         */
        async _onCardSwipe(parsed_result) {
            let activePayment = this.env.model.getActivePayment(this.props.activeOrder);
            if (!activePayment) {
                const mercuryPaymentMethod = this.env.model.getMercuryPaymentMethods()[0];
                activePayment = await this.env.model.actionHandler({
                    name: 'actionAddPayment',
                    args: [this.props.activeOrder, mercuryPaymentMethod],
                });
            }
            if (this.env.model.isMercuryPayment(activePayment)) {
                this.trigger('send-payment-request', [activePayment, parsed_result]);
            }
        },
    });

    return PaymentScreen;
});
