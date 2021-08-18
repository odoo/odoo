odoo.define('flexipharmacy.PaymentDetail', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class PaymentDetail extends PosComponent {}
    PaymentDetail.template = 'PaymentDetail';

    Registries.Component.add(PaymentDetail);

    return PaymentDetail;
});
