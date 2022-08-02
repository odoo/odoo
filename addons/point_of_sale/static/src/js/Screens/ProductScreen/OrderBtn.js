odoo.define('point_of_sale.OrderBtn', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class OrderBtn extends PosComponent {

    }
    OrderBtn.template = 'OrderBtn';

    Registries.Component.add(OrderBtn);

    return OrderBtn;
});
