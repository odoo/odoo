odoo.define('pos_restaurant.TicketScreen', function (require) {
    'use strict';

    const TicketScreen = require('point_of_sale.TicketScreen');
    const Registries = require('point_of_sale.Registries');
    const { posbus } = require('point_of_sale.utils');

    const PosResTicketScreen = (TicketScreen) =>
        class extends TicketScreen {
            close() {
                super.close();
                if (!this.env.pos.config.iface_floorplan) {
                    // Make sure the 'table-set' event is triggered
                    // to properly rerender the components that listens to it.
                    posbus.trigger('table-set');
                }
            }
            getTable(order) {
                return `${order.table.floor.name} (${order.table.name})`;
            }
            get _searchFields() {
                if (!this.env.pos.config.iface_floorplan) {
                    return super._searchFields;
                }
                return Object.assign({}, super._searchFields, {
                    Table: (order) => `${order.table.floor.name} (${order.table.name})`,
                });
            }
            _setOrder(order) {
                if (!this.env.pos.config.iface_floorplan) {
                    super._setOrder(order);
                } else if (order !== this.env.pos.get_order()) {
                    // Only call set_table if the order is not the same as the current order.
                    // This is to prevent syncing to the server because syncing is only intended
                    // when going back to the floorscreen or opening a table.
                    this.env.pos.set_table(order.table, order);
                }
            }
            get showNewTicketButton() {
                return this.env.pos.config.iface_floorplan ? Boolean(this.env.pos.table) : super.showNewTicketButton;
            }
            get orderList() {
                if (this.env.pos.table) {
                    return super.orderList;
                } else {
                    return this.env.pos.get('orders').models;
                }
            }
        };

    Registries.Component.extend(TicketScreen, PosResTicketScreen);

    return TicketScreen;
});
