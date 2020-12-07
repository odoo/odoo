odoo.define('pos_restaurant.TicketScreen', function (require) {
    'use strict';

    const TicketScreen = require('point_of_sale.TicketScreen');
    const TipCell = require('pos_restaurant.TipCell');
    const { patch } = require('web.utils');

    patch(TicketScreen.prototype, 'pos_restaurant', {
        async onClickOrder(order) {
            if (this.env.model.ifaceFloorplan && order.table_id) {
                const table = this.env.model.getRecord('restaurant.table', order.table_id);
                await this.env.model.actionHandler({ name: 'actionSetTableWithOrder', args: [table, order.id] });
            } else {
                await this._super(...arguments);
            }
        },
        async onClickDiscard() {
            await this._super(...arguments);
            if (!this.env.model.getActiveTable()) {
                await this.env.model.removeDeletedOrders();
            }
        },
        get filteredOrderList() {
            const orders = this._super();
            const activeTable = this.env.model.getActiveTable();
            if (activeTable) {
                return orders.filter((order) => order.table_id === activeTable.id);
            } else {
                return orders;
            }
        },
        get filterOptions() {
            const { Payment, Open, Tipping } = this.getOrderStates();
            const filterOptions = this._super();
            if (this.env.model.config.set_tip_after_payment) {
                const idx = filterOptions.indexOf(Payment);
                filterOptions[idx] = Open;
            }
            return [...filterOptions, Tipping];
        },
        getTable(order) {
            return `${order.table.floor.name} (${order.table.name})`;
        },
        get showNewTicketButton() {
            return this.env.model.ifaceFloorplan ? Boolean(this.env.model.getActiveTable()) : this._super();
        },
        get searchFieldAccessors() {
            const { Table } = this.getSearchFieldNames();
            if (!this.env.model.ifaceFloorplan) {
                return this._super();
            }
            return Object.assign({}, this._super(), {
                [Table]: (order) => `${order.table.floor.name} (${order.table.name})`,
            });
        },
        getSearchFieldNames() {
            return Object.assign(this._super(), {
                Table: this.env._t('Table'),
            });
        },
        getOrderStates() {
            return Object.assign(this._super(), {
                Tipping: this.env._t('Tipping'),
                Open: this.env._t('Open'),
            });
        },
        get screenToStatus() {
            const result = this._super();
            const { Tipping, Open } = this.getOrderStates();
            return Object.assign(result, {
                PaymentScreen: this.env.model.config.set_tip_after_payment ? Open : result.PaymentScreen,
                TipScreen: Tipping,
            });
        },
        isTippingFilter() {
            const { Tipping } = this.getOrderStates();
            return this.env.model.data.uiState.TicketScreen.filter === Tipping;
        },
    });

    patch(TicketScreen, 'pos_restaurant', {
        components: { ...TicketScreen.components, TipCell },
    });

    return TicketScreen;
});
