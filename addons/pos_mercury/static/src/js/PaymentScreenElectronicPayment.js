odoo.define('pos_mercury.PaymentScreenElectronicPayment', function (require) {
    'use strict';

    const PaymentScreenElectronicPayment = require('point_of_sale.PaymentScreenElectronicPayment');
    const { patch } = require('web.utils');

    patch(PaymentScreenElectronicPayment.prototype, 'pos_mercury', {
        getPendingMessage(payment) {
            if (this.env.model.isMercuryPayment(payment)) {
                return this.env._t('Waiting for swipe...');
            } else {
                return this._super(...arguments);
            }
        },
        getCancelledMessage(payment) {
            if (this.env.model.isMercuryPayment(payment)) {
                return this.env._t('Try again. Waiting for swipe...');
            } else {
                return this._super(...arguments);
            }
        },
        get showSendButton() {
            if (this.env.model.isMercuryPayment(this.props.line)) {
                return false;
            } else {
                return true;
            }
        },
    });

    return PaymentScreenElectronicPayment;
});
