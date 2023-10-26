/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useSelfOrder } from "@pos_self_order/app/self_order_service";
import { PopupTable } from "@pos_self_order/app/components/popup_table/popup_table";
import { _t } from "@web/core/l10n/translation";
import { OrderWidget } from "@pos_self_order/app/components/order_widget/order_widget";

export class CartPage extends Component {
    static template = "pos_self_order.CartPage";
    static components = { PopupTable, OrderWidget };

    setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");
        this.sendInProgress = false;
        this.state = useState({
            selectTable: false,
            cancelConfirmation: false,
        });
    }

    get lines() {
        const lines = this.selfOrder.currentOrder.lines;
        return lines ? lines : [];
    }

    get linesToDisplay() {
        const selfOrder = this.selfOrder;
        const order = selfOrder.currentOrder;

        if (selfOrder.config.self_ordering_pay_after === "meal" && !order.isSavedOnServer) {
            return order.hasNotAllLinesSent();
        } else {
            return this.lines;
        }
    }

    getLineChangeQty(line) {
        const currentQty = line.qty;
        const lastChange = this.selfOrder.currentOrder.lastChangesSent[line.uuid];
        return !lastChange ? currentQty : currentQty - lastChange.qty;
    }

    backToMenu() {
        this.router.navigate("product_list");
    }

    async pay() {
        const orderingMode = this.selfOrder.config.self_ordering_service_mode;
        const type = this.selfOrder.config.self_ordering_mode;
        const takeAway = this.selfOrder.currentOrder.take_away;

        if (this.sendInProgress || !this.selfOrder.verifyCart()) {
            return;
        }

        if (type === "mobile" && orderingMode === "table" && !takeAway && !this.selfOrder.table) {
            this.state.selectTable = true;
            return;
        }

        this.sendInProgress = true;
        await this.selfOrder.confirmOrder();
        this.sendInProgress = false;
    }

    selectTable(table) {
        if (table) {
            this.selfOrder.table = table;
            this.router.addTableIdentifier(table);
            this.pay();
        }

        this.state.selectTable = false;
    }

    getChildLines(line) {
        return this.lines.filter((l) => l.combo_parent_uuid === line.uuid);
    }

    getPrice(line) {
        const childLines = this.getChildLines(line);
        if (childLines.length == 0) {
            return line.price_subtotal_incl;
        } else {
            let price = 0;
            for (const child of childLines) {
                price += child.price_subtotal_incl;
            }
            return price;
        }
    }

    canChangeQuantity(line) {
        const order = this.selfOrder.currentOrder;
        const lastChange = order.lastChangesSent[line.uuid];

        if (!lastChange) {
            return true;
        }

        return lastChange.qty < line.qty;
    }

    canDeleteLine(line) {
        const lastChange = this.selfOrder.currentOrder.lastChangesSent[line.uuid];
        return !lastChange ? true : lastChange.qty !== line.qty;
    }

    async removeLine(line) {
        const lastChange = this.selfOrder.currentOrder.lastChangesSent[line.uuid];

        if (!this.canDeleteLine(line)) {
            return;
        }

        if (lastChange) {
            line.qty = lastChange.qty;
        } else {
            this.selfOrder.currentOrder.removeLine(line.uuid);
        }

        await this.selfOrder.getPricesFromServer();
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
            if (cline.combo_parent_uuid === line.uuid) {
                this._changeQuantity(cline, increase);
            }
        }
    }

    async changeQuantity(line, increase) {
        await this._changeQuantity(line, increase);
        await this.selfOrder.getPricesFromServer();
    }

    clickOnLine(line) {
        const order = this.selfOrder.currentOrder;
        this.selfOrder.editedLine = line;

        if (order.state === "draft" && !order.lastChangesSent[line.uuid]) {
            this.selfOrder.editedOrder = order;

            if (line.child_lines.length > 0) {
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
