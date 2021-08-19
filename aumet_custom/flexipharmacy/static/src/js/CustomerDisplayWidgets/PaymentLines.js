odoo.define('flexipharmacy.PaymentLines', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class PaymentLines extends PosComponent {}
    PaymentLines.template = 'PaymentLines';

    Registries.Component.add(PaymentLines);

    return PaymentLines;
});
