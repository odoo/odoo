odoo.define('pos_restaurant.OrderSelector', function(require) {
    'use strict';

    const { OrderSelector } = require('point_of_sale.OrderSelector');
    const Registry = require('point_of_sale.ComponentsRegistry');

    const PosResOrderSelector = OrderSelector =>
        class extends OrderSelector {
            get currentTable() {
                return this.env.pos.table;
            }
            get backToFloorButtonIsShown() {
                return this.env.pos.config.iface_floorplan && this.currentTable;
            }
        };

    Registry.extend(OrderSelector.name, PosResOrderSelector);
});
