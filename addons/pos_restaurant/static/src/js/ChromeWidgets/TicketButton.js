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
                const pos_config_id = pos.config.id
                try {
                    const server_orders = await this.rpc({
                        model: 'pos.order',
                        method: 'get_all_table_draft_orders',
                        args: [pos_config_id],
                        kwargs: {context: this.env.session.user_context},
                    }, {
                        timeout: 7500,
                        shadow: false,
                    });
                    const orders = Object.keys(pos.tables_by_id).reduce(function (acm, table_id){
                        const orders = pos.get_table_orders(pos.tables_by_id[table_id]);
                        return acm.concat(orders);
                    },[])
                    pos._replace_orders(orders, server_orders);
                } catch (_error) {
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
