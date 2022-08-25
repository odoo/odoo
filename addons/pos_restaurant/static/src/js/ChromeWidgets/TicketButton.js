odoo.define('pos_restaurant.TicketButton', function (require) {
    'use strict';

    const TicketButton = require('point_of_sale.TicketButton');
    const Registries = require('point_of_sale.Registries');

    const PosResTicketButton = (TicketButton) =>
        class extends TicketButton {
            async onClick() {
                if (this.env.pos.config.iface_floorplan && !this.props.isTicketScreenShown && !this.env.pos.table) {
                    await this._syncAllFromServer();
                    this.showScreen('TicketScreen');
                } else {
                    super.onClick();
                }
            }
            async _syncAllFromServer() {
                const pos = this.env.pos;
                try {
                    for (const floor of pos.floors) {
                        for (const table of floor.tables) {
                            await pos.replace_table_orders_from_server(table);
                        }
                    }
                } catch (e) {
                    await this.showPopup('ErrorPopup', {
                        title: this.env._t('Connection Error'),
                        body: this.env._t('Due to a connection error, the orders are not synchronized.'),
                    });
                }
            }
            /**
             * If no table is set to pos, which means the current main screen
             * is floor screen, then the order count should be based on all the orders.
             */
            get count() {
                if (!this.env.pos || !this.env.pos.config) return 0;
                if (this.env.pos.config.iface_floorplan && !this.env.pos.table) {
                    return this.env.pos.orders.length;
                } else {
                    return super.count;
                }
            }
        };

    Registries.Component.extend(TicketButton, PosResTicketButton);

    return TicketButton;
});
