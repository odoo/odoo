odoo.define('pos_restaurant.OrderManagementScreen', function (require) {
    'use strict';

    const OrderManagementScreen = require('point_of_sale.OrderManagementScreen');
    const { patch } = require('web.utils');

    patch(OrderManagementScreen.prototype, 'pos_restaurant', {
        async _onClickOrder(event) {
            const order = event.detail;
            if (
                this.env.model.ifaceFloorplan &&
                order.table_id &&
                !this.env.model.data.uiState.OrderManagementScreen.managementOrderIds.has(order.id)
            ) {
                const table = this.env.model.getRecord('restaurant.table', order.table_id);
                await this.env.model.actionHandler({ name: 'actionSetTableWithOrder', args: [table, order.id] });
            } else {
                await this._super(...arguments);
            }
        },
    });

    return OrderManagementScreen;
});
