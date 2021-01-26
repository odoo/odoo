odoo.define('pos_restaurant.TicketScreen', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const TicketScreen = require('point_of_sale.TicketScreen');
    const Registries = require('point_of_sale.Registries');
    const { useAutofocus } = require('web.custom_hooks');
    const { posbus } = require('point_of_sale.utils');
    const { parse } = require('web.field_utils');
    const { useState, useContext } = owl.hooks;

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
            get filterOptions() {
                const { Payment, Open, Tipping } = this.getOrderStates();
                var filterOptions = super.filterOptions;
                if (this.env.pos.config.set_tip_after_payment) {
                    var idx = filterOptions.indexOf(Payment);
                    filterOptions[idx] = Open;
                }
                return [...filterOptions, Tipping];
            }
            get _screenToStatusMap() {
                const { Open, Tipping } = this.getOrderStates();
                return Object.assign(super._screenToStatusMap, {
                    PaymentScreen: this.env.pos.config.set_tip_after_payment ? Open : super._screenToStatusMap.PaymentScreen,
                    TipScreen: Tipping,
                });
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
            async settleTips() {
                // set tip in each order
                for (const order of this.filteredOrderList) {
                    const tipAmount = parse.float(order.uiState.TipScreen.state.inputTipAmount || '0');
                    const serverId = this.env.pos.validated_orders_name_server_id_map[order.name];
                    if (!serverId) {
                        console.warn(`${order.name} is not yet sync. Sync it to server before setting a tip.`);
                    } else {
                        const result = await this.setTip(order, serverId, tipAmount);
                        if (!result) break;
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
                        await this.setNoTip();
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
                    order.finalize();
                    return true;
                } catch (error) {
                    const { confirmed } = await this.showPopup('ConfirmPopup', {
                        title: 'Failed to set tip',
                        body: `Failed to set tip to ${order.name}. Do you want to proceed on setting the tips of the remaining?`,
                    });
                    return confirmed;
                }
            }
            async setNoTip() {
                await this.rpc({
                    method: 'set_no_tip',
                    model: 'pos.order',
                    args: [serverId],
                });
            }
            getOrderStates() {
                return Object.assign(super.getOrderStates(), {
                    Tipping: this.env._t('Tipping'),
                    Open: this.env._t('Open'),
                });
            }
        };

    Registries.Component.extend(TicketScreen, PosResTicketScreen);

    class TipCell extends PosComponent {
        constructor() {
            super(...arguments);
            this.state = useState({ isEditing: false });
            this.orderUiState = useContext(this.props.order.uiState.TipScreen);
            useAutofocus({ selector: 'input' });
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
