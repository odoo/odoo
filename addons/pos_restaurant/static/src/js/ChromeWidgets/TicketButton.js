odoo.define('pos_restaurant.TicketButton', function (require) {
    'use strict';

    const TicketButton = require('point_of_sale.TicketButton');
    const Registries = require('point_of_sale.Registries');

    const PosResTicketButton = (TicketButton) =>
        class extends TicketButton {
            /**
             * If no table is set to pos, which means the current main screen
             * is floor screen, then the order count should be based on all the orders.
             */
            get count() {
                if (!this.env.pos || !this.env.pos.config) return 0;
                if (this.env.pos.config.iface_floorplan && this.env.pos.table) {
                    return this.env.pos.getTableOrders(this.env.pos.table.id).length;
                } else {
                    return super.count;
                }
            }
        };

    Registries.Component.extend(TicketButton, PosResTicketButton);

    return TicketButton;
});
