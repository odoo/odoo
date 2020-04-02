odoo.define('point_of_sale.PaymentScreenElectronicPayment', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');
    const Registry = require('point_of_sale.ComponentsRegistry');

    class PaymentScreenElectronicPayment extends PosComponent {
        static template = 'PaymentScreenElectronicPayment';
    }

    Registry.add('PaymentScreenElectronicPayment', PaymentScreenElectronicPayment);

    return { PaymentScreenElectronicPayment };
});
