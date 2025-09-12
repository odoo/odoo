import { _t } from "@web/core/l10n/translation";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { useAutofocus } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { Component, useState } from "@odoo/owl";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";

patch(TicketScreen.prototype, {
    _getScreenToStatusMap() {
        return Object.assign(super._getScreenToStatusMap(...arguments), {
            PaymentScreen: this.pos.config.set_tip_after_payment
                ? "OPEN"
                : super._getScreenToStatusMap(...arguments).PaymentScreen,
            TipScreen: "TIPPING",
        });
    },
    getTableTag(order) {
        return order.table_id?.table_number;
    },
    getTable(order) {
        const table = order.getTable();
        if (table) {
            let floorAndTable = "";

            if (this.pos.models["restaurant.floor"].length > 0) {
                floorAndTable = `${table.floor_id.name}/`;
            }

            floorAndTable += table.getName();
            return floorAndTable;
        }
    },
    //@override
    _getSearchFields() {
        const res = super._getSearchFields(...arguments);
        if (this.pos.config.module_pos_restaurant) {
            res.REFERENCE.modelFields.push("table_id.table_number");
        }
        return res;
    },
    async setOrder(order) {
        const shouldBeOverridden = this.pos.config.module_pos_restaurant && order.table_id;
        if (shouldBeOverridden) {
            const orderTable = order.getTable();
            await this.pos.setTable(orderTable, order.uuid);
        }
        return await super.setOrder(order);
    },
    async settleTips() {
        const promises = [];
        for (const order of this.getFilteredOrderList()) {
            const amount = this.env.utils.parseValidFloat(order.uiState.TipScreen.inputTipAmount);

            if (!order.isSynced) {
                logPosMessage(
                    "TicketScreen",
                    "settleTips",
                    `${order.name} is not yet sync. Sync it to server before setting a tip.`
                );
                continue;
            }

            order.state = "draft";
            this.pos.selectedOrderUuid = order.uuid;
            await this.pos.setTip(amount);
            order.state = "paid";
            order.uiState.screen_data.value = { name: "", props: {} };

            const serializedTipLine = order.getSelectedOrderline().serializeForORM();
            order.getSelectedOrderline().delete();

            promises.push(
                new Promise((resolve) => {
                    const fn = async () => {
                        const tipLine = await this.pos.data.create("pos.order.line", [
                            serializedTipLine,
                        ]);
                        const state = await this.pos.data.ormWrite("pos.order", [order.id], {
                            is_tipped: true,
                            tip_amount: tipLine[0].price_unit,
                        });

                        if (state) {
                            order.update({
                                is_tipped: true,
                                tip_amount: tipLine[0].price_unit,
                            });
                        }
                        resolve();
                    };
                    fn();
                })
            );
        }

        await Promise.all(promises);
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
    isDefaultOrderEmpty(order) {
        if (this.pos.config.module_pos_restaurant) {
            return false;
        }
        return super.isDefaultOrderEmpty(...arguments);
    },
});

export class TipCell extends Component {
    static template = "pos_restaurant.TipCell";
    static props = {
        order: Object,
    };

    setup() {
        this.state = useState({ isEditing: false });
        this.orderUiState = this.props.order.uiState.TipScreen;
        useAutofocus();
    }
    get tipAmountStr() {
        return this.env.utils.formatCurrency(
            this.env.utils.parseValidFloat(this.orderUiState.inputTipAmount)
        );
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
