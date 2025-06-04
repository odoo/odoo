import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useSelfOrder } from "@pos_self_order/app/self_order_service";
import { PopupTable } from "@pos_self_order/app/components/popup_table/popup_table";
import { _t } from "@web/core/l10n/translation";
import { OrderWidget } from "@pos_self_order/app/components/order_widget/order_widget";
import { CancelPopup } from "@pos_self_order/app/components/cancel_popup/cancel_popup";
import { rpc } from "@web/core/network/rpc";

export class CartPage extends Component {
    static template = "pos_self_order.CartPage";
    static components = { PopupTable, OrderWidget };
    static props = {};

    setup() {
        this.selfOrder = useSelfOrder();
        this.dialog = useService("dialog");
        this.router = useService("router");
        this.state = useState({
            selectTable: false,
            cancelConfirmation: false,
        });
    }

    get showCancelButton() {
        return (
            this.selfOrder.config.self_ordering_mode === "mobile" &&
            this.selfOrder.config.self_ordering_pay_after === "each" &&
            typeof this.selfOrder.currentOrder.id === "number"
        );
    }

    get lines() {
        const lines = this.selfOrder.currentOrder.lines;
        return lines ? lines : [];
    }

    get linesToDisplay() {
        const selfOrder = this.selfOrder;
        const order = selfOrder.currentOrder;

        if (
            selfOrder.config.self_ordering_pay_after === "meal" &&
            Object.keys(order.changes).length > 0
        ) {
            return order.unsentLines;
        } else {
            return this.lines;
        }
    }

    async cancelOrder() {
        this.dialog.add(CancelPopup, {
            title: _t("Cancel order"),
            confirm: async () => {
                try {
                    await rpc("/pos-self-order/remove-order", {
                        access_token: this.selfOrder.access_token,
                        order_id: this.selfOrder.currentOrder.id,
                        order_access_token: this.selfOrder.currentOrder.access_token,
                    });
                    this.selfOrder.currentOrder.state = "cancel";
                    this.router.navigate("default");
                } catch (error) {
                    this.selfOrder.handleErrorNotification(error);
                }
            },
        });
    }

    getLineChangeQty(line) {
        const currentQty = line.qty;
        const lastChange = this.selfOrder.currentOrder.uiState.lineChanges[line.uuid];
        return !lastChange ? currentQty : currentQty - lastChange.qty;
    }

    async pay() {
        const orderingMode = this.selfOrder.config.self_ordering_service_mode;
        const type = this.selfOrder.config.self_ordering_mode;
        const takeAway = this.selfOrder.currentOrder.takeaway;

        if (
            this.selfOrder.rpcLoading ||
            !this.selfOrder.verifyCart() ||
            !this.selfOrder.verifyPriceLoading()
        ) {
            return;
        }

        if (
            type === "mobile" &&
            orderingMode === "table" &&
            !takeAway &&
            !this.selfOrder.currentTable
        ) {
            this.state.selectTable = true;
            return;
        } else {
            this.selfOrder.currentOrder.update({
                table_id: this.selfOrder.currentTable,
            });
        }

        this.selfOrder.rpcLoading = true;
        await this.selfOrder.confirmOrder();
        this.selfOrder.rpcLoading = false;
    }

    selectTable(table) {
        if (table) {
            this.selfOrder.currentOrder.update({
                table_id: table,
            });
            this.selfOrder.currentTable = table;
            this.router.addTableIdentifier(table);
            this.pay();
        }

        this.state.selectTable = false;
    }

    getPrice(line) {
        const childLines = line.combo_line_ids;
        if (childLines.length == 0) {
            return line.get_display_price();
        } else {
            let price = 0;
            for (const child of childLines) {
                price += child.get_display_price();
            }
            return price;
        }
    }

    canChangeQuantity(line) {
        const order = this.selfOrder.currentOrder;
        const lastChange = order.uiState.lineChanges[line.uuid];

        if (!lastChange) {
            return true;
        }

        return lastChange.qty < line.qty;
    }

    canDeleteLine(line) {
        const lastChange = this.selfOrder.currentOrder.uiState.lineChanges[line.uuid];
        return !lastChange ? true : lastChange.qty !== line.qty;
    }

    async removeLine(line) {
        const lastChange = this.selfOrder.currentOrder.uiState.lineChanges[line.uuid];

        if (!this.canDeleteLine(line)) {
            return;
        }

        if (lastChange) {
            line.qty = lastChange.qty;
            line.setDirty();
        } else {
            this.selfOrder.removeLine(line);
        }
    }

    async _changeQuantity(line, increase) {
        if (!increase && !this.canChangeQuantity(line)) {
            return;
        }

        if (!increase && line.qty === 1) {
            this.removeLine(line.uuid);
            return;
        }
        increase ? line.qty++ : line.qty--;
        for (const cline of this.selfOrder.currentOrder.lines) {
            if (cline.combo_parent_id?.uuid === line.uuid) {
                this._changeQuantity(cline, increase);
                cline.setDirty();
            }
        }

        line.setDirty();
    }

    async changeQuantity(line, increase) {
        await this._changeQuantity(line, increase);
    }

    clickOnLine(line) {
        const order = this.selfOrder.currentOrder;
        this.selfOrder.editedLine = line;

        if (order.state === "draft" && !order.lastChangesSent[line.uuid]) {
            this.selfOrder.selectedOrderUuid = order.uuid;

            if (line.combo_line_ids.length > 0) {
                this.router.navigate("combo_selection", { id: line.product_id });
            } else {
                this.router.navigate("product", { id: line.product_id });
            }
        } else {
            this.selfOrder.notification.add(_t("You cannot edit a posted orderline !"), {
                type: "danger",
            });
        }
    }
}
