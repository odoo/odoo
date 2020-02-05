odoo.define('point_of_sale.PaymentScreenElectronicPayment', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');

    class PaymentScreenElectronicPayment extends PosComponent {}

    return { PaymentScreenElectronicPayment };
});
