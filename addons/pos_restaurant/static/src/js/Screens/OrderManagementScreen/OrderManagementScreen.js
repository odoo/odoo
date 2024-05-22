odoo.define('pos_restaurant.OrderManagementScreen', function (require) {
    'use strict';

    const OrderManagementScreen = require('point_of_sale.OrderManagementScreen');
    const Registries = require('point_of_sale.Registries');

    const PosResOrderManagementScreen = (OrderManagementScreen) =>
        class extends OrderManagementScreen {
            /**
             * @override
             */
            _setOrder(order) {
                if (this.env.pos.config.module_pos_restaurant) {
                    const currentOrder = this.env.pos.get_order();
                    this.env.pos.set_table(order.table, order);
                    if (currentOrder && currentOrder.uid === order.uid) {
                        this.close();
                    }
                } else {
                    super._setOrder(order);
                }
            }
        };

    Registries.Component.extend(OrderManagementScreen, PosResOrderManagementScreen);

    return OrderManagementScreen;
});
