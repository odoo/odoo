odoo.define('point_of_sale.OrderSummary', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class OrderSummary extends PosComponent {}
    OrderSummary.template = 'OrderSummary';

    Registries.Component.add(OrderSummary);

    return OrderSummary;
});
