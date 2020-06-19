odoo.define('pos_restaurant.OrderSelector', function(require) {
    'use strict';

    const OrderSelector = require('point_of_sale.OrderSelector');
    const Registries = require('point_of_sale.Registries');

    const PosResOrderSelector = OrderSelector =>
        class extends OrderSelector {
            get currentTable() {
                return this.env.pos.table;
            }
            get backToFloorButtonIsShown() {
                return this.env.pos.config.iface_floorplan && this.currentTable;
            }
        };

    Registries.Component.extend(OrderSelector, PosResOrderSelector);

    return OrderSelector;
});
