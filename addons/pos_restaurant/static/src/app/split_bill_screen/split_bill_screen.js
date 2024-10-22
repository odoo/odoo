import { registry } from "@web/core/registry";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component, useState } from "@odoo/owl";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";

export class SplitBillScreen extends Component {
    static template = "pos_restaurant.SplitBillScreen";
    static components = { Orderline, OrderWidget };
    static props = {};

    setup() {
        this.pos = usePos();
        this.qtyTracker = useState({});
        this.priceTracker = useState({});
    }

    get currentOrder() {
        return this.pos.get_order();
    }

    get orderlines() {
        return this.currentOrder.get_orderlines();
    }

    get newOrderPrice() {
        return Object.values(this.priceTracker).reduce((a, b) => a + b, 0);
    }

    onClickLine(line) {
        const lines = line.getAllLinesInCombo();

        for (const line of lines) {
            if (!line.is_pos_groupable()) {
                if (this.qtyTracker[line.uuid] === line.get_quantity()) {
                    this.qtyTracker[line.uuid] = 0;
                } else {
                    this.qtyTracker[line.uuid] = line.get_quantity();
                }
            } else if (!this.qtyTracker[line.uuid]) {
                this.qtyTracker[line.uuid] = 1;
            } else if (this.qtyTracker[line.uuid] === line.get_quantity()) {
                this.qtyTracker[line.uuid] = 0;
            } else {
                this.qtyTracker[line.uuid] += 1;
            }

            this.priceTracker[line.uuid] =
                (line.get_price_with_tax() / line.qty) * this.qtyTracker[line.uuid];
        }
    }

    _getOrderName(order) {
        return order.table_id?.table_number.toString() || order.getFloatingOrderName() || "";
    }

    _getLatestOrderNameStartingWith(name) {
        return (
            this.pos
                .get_open_orders()
                .map((order) => this._getOrderName(order))
                .filter((orderName) => orderName.slice(0, -1) === name)
                .sort((a, b) => a.slice(-1).localeCompare(b.slice(-1)))
                .at(-1) || name
        );
    }

    _getSplitOrderName(originalOrderName) {
        const latestOrderName = this._getLatestOrderNameStartingWith(originalOrderName);
        if (latestOrderName === originalOrderName) {
            return `${originalOrderName}B`;
        }
        const lastChar = latestOrderName[latestOrderName.length - 1];
        if (lastChar === "Z") {
            throw new Error("You cannot split the order into more than 26 parts!");
        }
        const nextChar = String.fromCharCode(lastChar.charCodeAt(0) + 1);
        return `${latestOrderName.slice(0, -1)}${nextChar}`;
    }

    // Meant to be overridden
    async preSplitOrder(originalOrder, newOrder) {}
    async postSplitOrder(originalOrder, newOrder) {}

    async createSplittedOrder() {
        const curOrderUuid = this.currentOrder.uuid;
        const originalOrder = this.pos.models["pos.order"].find((o) => o.uuid === curOrderUuid);
        this.pos.selectedTable = null;
        const originalOrderName = this._getOrderName(originalOrder);
        const newOrderName = this._getSplitOrderName(originalOrderName);

        const newOrder = this.pos.createNewOrder();
        newOrder.floating_order_name = newOrderName;
        newOrder.uiState.splittedOrderUuid = curOrderUuid;
        await this.preSplitOrder(originalOrder, newOrder);
        // Create lines for the new order
        const lineToDel = [];
        for (const line of originalOrder.lines) {
            if (this.qtyTracker[line.uuid]) {
                const data = line.serialize();
                delete data.uuid;
                this.pos.models["pos.order.line"].create(
                    {
                        ...data,
                        qty: this.qtyTracker[line.uuid],
                        order_id: newOrder.id,
                        skip_change: true,
                    },
                    false,
                    true
                );

                if (line.get_quantity() === this.qtyTracker[line.uuid]) {
                    lineToDel.push(line);
                } else {
                    line.update({ qty: line.get_quantity() - this.qtyTracker[line.uuid] });
                }
            }
        }

        for (const line of lineToDel) {
            line.delete();
        }

        // for the kitchen printer we assume that everything
        // has already been sent to the kitchen before splitting
        // the bill. So we save all changes both for the old
        // order and for the new one. This is not entirely correct
        // but avoids flooding the kitchen with unnecessary orders.
        // Not sure what to do in this case.
        if (this.pos.orderPreparationCategories.size) {
            originalOrder.updateLastOrderChange();
            newOrder.updateLastOrderChange();
        }

        originalOrder.customer_count -= 1;
        await this.postSplitOrder(originalOrder, newOrder);
        originalOrder.set_screen_data({ name: "ProductScreen" });
        this.pos.selectedOrderUuid = null;
        this.pos.set_order(newOrder);
        this.back();
    }

    getLineData(line) {
        const splitQty = this.qtyTracker[line.uuid];

        if (!splitQty) {
            return line.getDisplayData();
        }

        return { ...line.getDisplayData(), qty: `${splitQty} / ${line.get_quantity_str()}` };
    }

    back() {
        this.pos.showScreen("ProductScreen");
    }
}

registry.category("pos_screens").add("SplitBillScreen", SplitBillScreen);
