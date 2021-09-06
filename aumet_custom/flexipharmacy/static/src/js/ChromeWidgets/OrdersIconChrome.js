odoo.define('flexipharmacy.OrdersIconChrome', function(require) {
    'use strict';

    const { useState } = owl;
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class OrdersIconChrome extends PosComponent {
        constructor() {
            super(...arguments);
        }
        async onClick() {
            this.trigger('show-orders-panel');
        }
        get count() {
            return this.props.orderCount;
        }
    }
    OrdersIconChrome.template = 'OrdersIconChrome';

    Registries.Component.add(OrdersIconChrome);

    return OrdersIconChrome;
});
