odoo.define('pos_restaurant.TicketButton', function (require) {
    'use strict';

    const TicketButton = require('point_of_sale.TicketButton');
    const { patch } = require('web.utils');

    patch(TicketButton.prototype, 'pos_restaurant', {
        getNumberOfOrders() {
            if (this.env.model.ifaceFloorplan) {
                const table = this.env.model.getActiveTable();
                return this.env.model.getTableOrders(table).length;
            } else {
                return this._super();
            }
        },
    });

    return TicketButton;
});
