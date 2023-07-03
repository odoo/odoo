/** @odoo-module */

import { Order } from "@point_of_sale/app/store/models";

import { SplitOrderline } from "@pos_restaurant/js/Screens/SplitBillScreen/SplitOrderline";
import { registry } from "@web/core/registry";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component, useState } from "@odoo/owl";
import { groupBy } from "@web/core/utils/arrays";

export class SplitBillScreen extends Component {
    static template = "pos_restaurant.SplitBillScreen";
    static components = { SplitOrderline };

    setup() {
        this.pos = usePos();
        this.splitlines = useState(this._initSplitLines(this.pos.get_order()));
        this.newOrderLines = {};
        this.newOrder = undefined;
        this._isFinal = false;
        this.newOrder = new Order(
            { env: this.env },
            {
                pos: this.pos,
                temporary: true,
            }
        );
    }
    get currentOrder() {
        return this.pos.get_order();
    }
    get orderlines() {
        return this.currentOrder.get_orderlines();
    }
    onClickLine(line) {
        this._splitQuantity(line);
        this._updateNewOrder(line);
    }
    back() {
        this.pos.showScreen("ProductScreen");
    }
    proceed() {
        if (Object.keys(this.splitlines || {})?.length === 0) {
            // Splitlines is empty
            return;
        }

        this._isFinal = true;
        delete this.newOrder.temporary;

        if (!this._isFullPayOrder()) {
            this._setQuantityOnCurrentOrder();

            this.newOrder.set_screen_data({ name: "PaymentScreen" });

            // for the kitchen printer we assume that everything
            // has already been sent to the kitchen before splitting
            // the bill. So we save all changes both for the old
            // order and for the new one. This is not entirely correct
            // but avoids flooding the kitchen with unnecessary orders.
            // Not sure what to do in this case.
            if (this.pos.orderPreparationCategories.size) {
                this.currentOrder.updateLastOrderChange();
                this.newOrder.updateLastOrderChange();
            }

            this.newOrder.setCustomerCount(1);
            this.newOrder.originalSplittedOrder = this.currentOrder;
            const newCustomerCount = this.currentOrder.getCustomerCount() - 1;
            this.currentOrder.setCustomerCount(newCustomerCount || 1);
            this.currentOrder.set_screen_data({ name: "ProductScreen" });

            const reactiveNewOrder = this.pos.makeOrderReactive(this.newOrder);
            this.pos.orders.add(reactiveNewOrder);
            this.pos.selectedOrder = reactiveNewOrder;
        }
        this.pos.showScreen("PaymentScreen");
    }
    /**
     * @param {models.Order} order
     * @returns {Object<{ quantity: number }>} splitlines
     */
    _initSplitLines(order) {
        const splitlines = {};
        for (const line of order.get_orderlines()) {
            splitlines[line.id] = { product: line.get_product().id, quantity: 0 };
        }
        return splitlines;
    }
    _splitQuantity(line) {
        const split = this.splitlines[line.id];

        let totalQuantity = 0;

        this.pos
            .get_order()
            .get_orderlines()
            .forEach(function (orderLine) {
                if (orderLine.get_product().id === split.product) {
                    totalQuantity += orderLine.get_quantity();
                }
            });

        if (line.get_quantity() > 0) {
            if (!line.get_unit().is_pos_groupable) {
                if (split.quantity !== line.get_quantity()) {
                    split.quantity = line.get_quantity();
                } else {
                    split.quantity = 0;
                }
            } else {
                if (split.quantity < totalQuantity) {
                    split.quantity += line.get_unit().is_pos_groupable
                        ? 1
                        : line.get_unit().rounding;
                    if (split.quantity > line.get_quantity()) {
                        split.quantity = line.get_quantity();
                    }
                } else {
                    split.quantity = 0;
                }
            }
        }
    }
    _updateNewOrder(line) {
        const split = this.splitlines[line.id];
        let orderline = this.newOrderLines[line.id];
        if (split.quantity) {
            if (!orderline) {
                orderline = line.clone();
                this.newOrder.add_orderline(orderline);
                this.newOrderLines[line.id] = orderline;
            }
            orderline.set_quantity(split.quantity, "do not recompute unit price");
        } else if (orderline) {
            this.newOrder.remove_orderline(orderline);
            this.newOrderLines[line.id] = null;
        }
    }
    _isFullPayOrder() {
        const order = this.pos.get_order();
        let full = true;
        const splitlines = this.splitlines;
        const groupedLines = groupBy(order.get_orderlines(), (line) => line.get_product().id);

        Object.keys(groupedLines).forEach(function (lineId) {
            var maxQuantity = groupedLines[lineId].reduce(
                (quantity, line) => quantity + line.get_quantity(),
                0
            );
            Object.keys(splitlines).forEach((id) => {
                const split = splitlines[id];
                if (split.product === groupedLines[lineId][0].get_product().id) {
                    maxQuantity -= split.quantity;
                }
            });
            if (maxQuantity !== 0) {
                full = false;
            }
        });

        return full;
    }
    _setQuantityOnCurrentOrder() {
        const order = this.pos.get_order();
        for (var id in this.splitlines) {
            var split = this.splitlines[id];
            var line = this.currentOrder.get_orderline(parseInt(id));

            if (!this.props.disallow) {
                line.set_quantity(
                    line.get_quantity() - split.quantity,
                    "do not recompute unit price"
                );
                if (Math.abs(line.get_quantity()) < 0.00001) {
                    this.currentOrder.remove_orderline(line);
                }
            } else {
                if (split.quantity) {
                    const decreaseLine = line.clone();
                    decreaseLine.order = order;
                    decreaseLine.noDecrease = true;
                    decreaseLine.set_quantity(-split.quantity);
                    order.add_orderline(decreaseLine);
                }
            }
        }
    }
}

registry.category("pos_screens").add("SplitBillScreen", SplitBillScreen);
