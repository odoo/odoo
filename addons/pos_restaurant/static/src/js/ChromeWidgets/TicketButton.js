odoo.define('pos_restaurant.TicketButton', function (require) {
    'use strict';

    const TicketButton = require('point_of_sale.TicketButton');
    const Registries = require('point_of_sale.Registries');
    const { isConnectionError } = require('point_of_sale.utils');

    const PosResTicketButton = (TicketButton) =>
        class extends TicketButton {
            async onClick() {
                if (this.env.pos.config.iface_floorplan && !this.props.isTicketScreenShown && !this.env.pos.table) {
                    try {
                        this.env.pos.setLoadingOrderState(true);
                        await this.env.pos._syncAllOrdersFromServer();
                    } catch (error) {
                        if (isConnectionError(error)) {
                            await this.showPopup('OfflineErrorPopup', {
                                title: this.env._t('Offline'),
                                body: this.env._t('Due to a connection error, the orders are not synchronized.'),
                            });
                        } else {
                            this.showPopup('ErrorPopup', {
                                title: this.env._t('Unknown error'),
                                body: error.message,
                            });
                        }
                    } finally {
                        this.env.pos.setLoadingOrderState(false);
                        this.showScreen('TicketScreen');
                    }
                } else {
                    super.onClick();
                }
            }
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
