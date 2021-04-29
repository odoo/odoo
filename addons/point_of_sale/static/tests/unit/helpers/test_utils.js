odoo.define('point_of_sale.unit.utils', function (require) {
    'use strict';
    function createCheckPayment(assert, model, order) {
        return function (caseName, payment, { amount, orderIsPaid, remaining, change, paymentIsValid }) {
            assert.ok(
                model.floatCompare(payment.amount, amount) === 0,
                `${caseName}: payment amount ${payment.amount} should be ${amount}`
            );
            assert.ok(
                model.getIsOrderPaid(order) === orderIsPaid,
                `${caseName}: order should be ${orderIsPaid ? 'paid' : 'unpaid'}`
            );
            const computedRemaining = model.getOrderDue(order);
            assert.ok(
                model.floatCompare(computedRemaining, remaining) === 0,
                `${caseName}: remaining ${computedRemaining} should be ${remaining}`
            );
            const computedChange = model.getOrderChange(order);
            assert.ok(
                model.floatCompare(computedChange, change) === 0,
                `${caseName}: change ${computedChange} should be ${change}`
            );
            assert.ok(
                model.isPaymentValidOnRounding(payment) === paymentIsValid,
                `${caseName}: payment with amount ${payment.amount} should be ${paymentIsValid ? 'valid' : 'invalid'}`
            );
        };
    }
    return { createCheckPayment };
});
