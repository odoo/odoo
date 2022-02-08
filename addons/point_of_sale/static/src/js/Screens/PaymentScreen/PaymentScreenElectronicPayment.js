odoo.define('point_of_sale.PaymentScreenElectronicPayment', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class PaymentScreenElectronicPayment extends PosComponent {}
    PaymentScreenElectronicPayment.template = 'PaymentScreenElectronicPayment';

    Registries.Component.add(PaymentScreenElectronicPayment);

    return PaymentScreenElectronicPayment;
});
