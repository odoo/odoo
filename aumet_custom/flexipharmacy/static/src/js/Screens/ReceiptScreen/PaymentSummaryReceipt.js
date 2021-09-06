odoo.define('flexipharmacy.PaymentSummaryReceipt', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class PaymentSummaryReceipt extends PosComponent {}
    PaymentSummaryReceipt.template = 'PaymentSummaryReceipt';

    Registries.Component.add(PaymentSummaryReceipt);

    return PaymentSummaryReceipt;
});
