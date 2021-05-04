odoo.define('pos_restaurant.AbstractOrderManagementScreen', function (require) {
    'use strict';

    const AbstractOrderManagementScreen = require('point_of_sale.AbstractOrderManagementScreen');
    const { patch } = require('web.utils');

    patch(AbstractOrderManagementScreen.prototype, 'pos_restaurant', {
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

    return AbstractOrderManagementScreen;
});
