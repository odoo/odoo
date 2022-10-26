odoo.define('pos_restaurant.TicketScreen', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const TicketScreen = require('point_of_sale.TicketScreen');
    const Registries = require('point_of_sale.Registries');
    const { useAutofocus } = require("@web/core/utils/hooks");
    const { parse } = require('web.field_utils');

    const { useState } = owl;

    const PosResTicketScreen = (TicketScreen) =>
        class extends TicketScreen {
            close() {
                if (!this.env.pos.config.iface_floorplan) {
                    super.close();
                } else {
                    const order = this.env.pos.get_order();
                    if (order) {
                        const { name: screenName } = order.get_screen_data();
                        this.showScreen(screenName);
                    } else {
                        this.showScreen('FloorScreen');
                    }
                }
            }
            _getScreenToStatusMap() {
                return Object.assign(super._getScreenToStatusMap(), {
                    PaymentScreen: this.env.pos.config.set_tip_after_payment ? 'OPEN' : super._getScreenToStatusMap().PaymentScreen,
                    TipScreen: 'TIPPING',
                });
            }
            getTable(order) {
                return `${order.getTable().floor.name} (${order.getTable().name})`;
            }
            //@override
            _getSearchFields() {
                if (!this.env.pos.config.iface_floorplan) {
                    return super._getSearchFields();
                }
                return Object.assign({}, super._getSearchFields(), {
                    TABLE: {
                        repr: this.getTable.bind(this),
                        displayName: this.env._t('Table'),
                        modelField: 'table_id.name',
                    }
                });
            }
            async _setOrder(order) {
                if (!this.env.pos.config.iface_floorplan || this.env.pos.table) {
                    super._setOrder(order);
                } else {
                    // we came from the FloorScreen
                    const orderTable = order.getTable();
                    await this.env.pos.setTable(orderTable, order.uid);
                    this.close();
                }
            }
            shouldShowNewOrderButton() {
                return this.env.pos.config.iface_floorplan ? Boolean(this.env.pos.table) : super.shouldShowNewOrderButton();
            }
            _getOrderList() {
                if (this.env.pos.table) {
                    return this.env.pos.getTableOrders(this.env.pos.table.id);
                }
                return super._getOrderList();
            }
            async settleTips() {
                // set tip in each order
                for (const order of this.getFilteredOrderList()) {
                    const tipAmount = parse.float(order.uiState.TipScreen.inputTipAmount || '0');
                    const serverId = this.env.pos.validated_orders_name_server_id_map[order.name];
                    if (!serverId) {
                        console.warn(`${order.name} is not yet sync. Sync it to server before setting a tip.`);
                    } else {
                        const result = await this.setTip(order, serverId, tipAmount);
                        if (!result) break;
                    }
                }
            }
            //@override
            _selectNextOrder(currentOrder) {
                if (this.env.pos.config.iface_floorplan && this.env.pos.table) {
                    return super._selectNextOrder(...arguments);
                }
            }
            //@override
            async _onDeleteOrder() {
                await super._onDeleteOrder(...arguments);
                if (this.env.pos.config.iface_floorplan) {
                    if (!this.env.pos.table) {
                        this.env.pos._removeOrdersFromServer();
                    }
                    const orderList = this.env.pos.table ? this.env.pos.getTableOrders(this.env.pos.table.id) : this.env.pos.orders;
                    if (orderList.length == 0) {
                        this.showScreen('FloorScreen');
                    }
                }
            }
            async setTip(order, serverId, amount) {
                try {
                    const paymentline = order.get_paymentlines()[0];
                    if (paymentline.payment_method.payment_terminal) {
                        paymentline.amount += amount;
                        this.env.pos.set_order(order, {silent: true});
                        await paymentline.payment_method.payment_terminal.send_payment_adjust(paymentline.cid);
                    }

                    if (!amount) {
                        await this.setNoTip(serverId);
                    } else {
                        order.finalized = false;
                        order.set_tip(amount);
                        order.finalized = true;
                        const tip_line = order.selected_orderline;
                        await this.rpc({
                            method: 'set_tip',
                            model: 'pos.order',
                            args: [serverId, tip_line.export_as_JSON()],
                        });
                    }
                    if (order === this.env.pos.get_order()) {
                        this._selectNextOrder(order);
                    }
                    this.env.pos.removeOrder(order);
                    return true;
                } catch (_error) {
                    const { confirmed } = await this.showPopup('ConfirmPopup', {
                        title: 'Failed to set tip',
                        body: `Failed to set tip to ${order.name}. Do you want to proceed on setting the tips of the remaining?`,
                    });
                    return confirmed;
                }
            }
            async setNoTip(serverId) {
                await this.rpc({
                    method: 'set_no_tip',
                    model: 'pos.order',
                    args: [serverId],
                });
            }
            _getOrderStates() {
                const result = super._getOrderStates();
                if (this.env.pos.config.set_tip_after_payment) {
                    result.delete('PAYMENT');
                    result.set('OPEN', { text: this.env._t('Open'), indented: true });
                    result.set('TIPPING', { text: this.env._t('Tipping'), indented: true });
                }
                return result;
            }
            async _onDoRefund() {
                if(this.env.pos.config.iface_floorplan) {
                    this.env.pos.setTable(this.getSelectedSyncedOrder().table ? this.getSelectedSyncedOrder().table : Object.values(this.env.pos.tables_by_id)[0]);
                }
                super._onDoRefund();
            }
            isDefaultOrderEmpty(order) {
                if (this.env.pos.config.iface_floorplan) {
                    return false;
                }
                return super.isDefaultOrderEmpty(...arguments);
            }
        };

    Registries.Component.extend(TicketScreen, PosResTicketScreen);

    class TipCell extends PosComponent {
        setup() {
            super.setup();
            this.state = useState({ isEditing: false });
            this.orderUiState = this.props.order.uiState.TipScreen;
            useAutofocus();
        }
        get tipAmountStr() {
            return this.env.pos.format_currency(parse.float(this.orderUiState.inputTipAmount || '0'));
        }
        onBlur() {
            this.state.isEditing = false;
        }
        onKeydown(event) {
            if (event.key === 'Enter') {
                this.state.isEditing = false;
            }
        }
        editTip() {
            this.state.isEditing = true;
        }
    }
    TipCell.template = 'TipCell';

    Registries.Component.add(TipCell);

    return { TicketScreen, TipCell };
});
