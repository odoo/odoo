odoo.define('pos_restaurant.PaymentScreenElectronicPayment', function (require) {
    'use strict';

    const PaymentScreenElectronicPayment = require('point_of_sale.PaymentScreenElectronicPayment');
    const { patch } = require('web.utils');

    patch(PaymentScreenElectronicPayment.prototype, 'pos_restaurant', {
        allowAdjustment(payment) {
            const order = this.env.model.getRecord('pos.order', payment.pos_order_id);
            const { withTaxWithDiscount } = this.env.model.getOrderTotals(order);
            const totalPaid = this.env.model.getPaymentsTotalAmount(order);
            return (
                this.env.model.canBeAdjusted(payment) && this.env.model.floatCompare(totalPaid, withTaxWithDiscount) < 0
            );
        },
    });

    return PaymentScreenElectronicPayment;
});
