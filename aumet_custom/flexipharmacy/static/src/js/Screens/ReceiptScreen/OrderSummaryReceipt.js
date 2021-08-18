odoo.define('flexipharmacy.OrderSummaryReceipt', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class OrderSummaryReceipt extends PosComponent {}
    OrderSummaryReceipt.template = 'OrderSummaryReceipt';

    Registries.Component.add(OrderSummaryReceipt);

    return OrderSummaryReceipt;
});
