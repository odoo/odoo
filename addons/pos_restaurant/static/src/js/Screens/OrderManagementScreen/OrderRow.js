odoo.define('pos_restaurant.OrderRow', function (require) {
    'use strict';

    const OrderRow = require('point_of_sale.OrderRow');
    const Registries = require('point_of_sale.Registries');

    const PosResOrderRow = (OrderRow) =>
        class extends OrderRow {
            get table() {
                return this.order.table ? this.order.table.name : '';
            }
        };

    Registries.Component.extend(OrderRow, PosResOrderRow);

    return OrderRow;
});
