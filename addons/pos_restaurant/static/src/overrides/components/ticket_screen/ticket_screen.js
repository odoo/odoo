/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { useAutofocus } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { parseFloat } from "@web/views/fields/parsers";
import { ConfirmPopup } from "@point_of_sale/app/utils/confirm_popup/confirm_popup";
import { Component, useState } from "@odoo/owl";

patch(TicketScreen.prototype, {
    _getScreenToStatusMap() {
        return Object.assign(super._getScreenToStatusMap(...arguments), {
            PaymentScreen: this.pos.config.set_tip_after_payment
                ? "OPEN"
                : super._getScreenToStatusMap(...arguments).PaymentScreen,
            TipScreen: "TIPPING",
        });
    },
    getTable(order) {
        const table = order.getTable();
        if (table) {
            let floorAndTable = "";

            if (this.pos.floors && this.pos.floors.length > 1) {
                floorAndTable = `${table.floor.name}/`;
            }

            floorAndTable += table.name;
            return floorAndTable;
        }
    },
    //@override
    _getSearchFields() {
        if (!this.pos.config.module_pos_restaurant) {
            return super._getSearchFields(...arguments);
        }
        return Object.assign({}, super._getSearchFields(...arguments), {
            TABLE: {
                repr: this.getTable.bind(this),
                displayName: _t("Table"),
                modelField: "table_id.name",
            },
        });
    },
    async _setOrder(order) {
        if (!this.pos.config.module_pos_restaurant || this.pos.table || !order.tableId) {
            return super._setOrder(...arguments);
        }
        // we came from the FloorScreen
        const orderTable = order.getTable();
        await this.pos.setTable(orderTable, order.uid);
        this.closeTicketScreen();
    },
    get allowNewOrders() {
        return this.pos.config.module_pos_restaurant
            ? Boolean(this.pos.table)
            : super.allowNewOrders;
    },
    async settleTips() {
        // set tip in each order
        for (const order of this.getFilteredOrderList()) {
            const tipAmount = parseFloat(order.uiState.TipScreen.inputTipAmount || "0");
            const serverId = this.pos.validated_orders_name_server_id_map[order.name];
            if (!serverId) {
                console.warn(
                    `${order.name} is not yet sync. Sync it to server before setting a tip.`
                );
            } else {
                const result = await this.setTip(order, serverId, tipAmount);
                if (!result) {
                    break;
                }
            }
        }
    },
    async setTip(order, serverId, amount) {
        try {
            const paymentline = order.get_paymentlines()[0];
            if (paymentline.payment_method.payment_terminal) {
                paymentline.amount += amount;
                this.pos.set_order(order, { silent: true });
                await paymentline.payment_method.payment_terminal.send_payment_adjust(
                    paymentline.cid
                );
            }

            if (!amount) {
                await this.setNoTip(serverId);
            } else {
                order.finalized = false;
                order.set_tip(amount);
                order.finalized = true;
                const tip_line = order.selected_orderline;
                await this.orm.call("pos.order", "set_tip", [serverId, tip_line.export_as_JSON()]);
            }
            if (order === this.pos.get_order()) {
                this._selectNextOrder(order);
            }
            this.pos.removeOrder(order);
            return true;
        } catch {
            const { confirmed } = await this.popup.add(ConfirmPopup, {
                title: "Failed to set tip",
                body: `Failed to set tip to ${order.name}. Do you want to proceed on setting the tips of the remaining?`,
            });
            return confirmed;
        }
    },
    async setNoTip(serverId) {
        await this.orm.call("pos.order", "set_no_tip", [serverId]);
    },
    _getOrderStates() {
        const result = super._getOrderStates(...arguments);
        if (this.pos.config.set_tip_after_payment) {
            result.delete("PAYMENT");
            result.set("OPEN", { text: _t("Open"), indented: true });
            result.set("TIPPING", { text: _t("Tipping"), indented: true });
        }
        return result;
    },
    async onDoRefund() {
        const order = this.getSelectedOrder();
        if (this.pos.config.module_pos_restaurant && order && !this.pos.table) {
            this.pos.setTable(order.table ? order.table : Object.values(this.pos.tables_by_id)[0]);
        }
        super.onDoRefund(...arguments);
    },
    isDefaultOrderEmpty(order) {
        if (this.pos.config.module_pos_restaurant) {
            return false;
        }
        return super.isDefaultOrderEmpty(...arguments);
    },
});

export class TipCell extends Component {
    static template = "pos_restaurant.TipCell";

    setup() {
        this.state = useState({ isEditing: false });
        this.orderUiState = this.props.order.uiState.TipScreen;
        useAutofocus();
    }
    get tipAmountStr() {
        return this.env.utils.formatCurrency(parseFloat(this.orderUiState.inputTipAmount || "0"));
    }
    onBlur() {
        this.state.isEditing = false;
    }
    onKeydown(event) {
        if (event.key === "Enter") {
            this.state.isEditing = false;
        }
    }
    editTip() {
        this.state.isEditing = true;
    }
}

patch(TicketScreen, {
    components: { ...TicketScreen.components, TipCell },
});
