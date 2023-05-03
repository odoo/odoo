/** @odoo-module */

import { Order } from "@point_of_sale/js/models";

import { SplitOrderline } from "./SplitOrderline";
import { registry } from "@web/core/registry";
import { usePos } from "@point_of_sale/app/pos_hook";
import { Component, useState, onMounted } from "@odoo/owl";

export class SplitBillScreen extends Component {
    static template = "SplitBillScreen";
    static components = { SplitOrderline };

    setup() {
        super.setup();
        this.pos = usePos();
        this.splitlines = useState(this._initSplitLines(this.env.pos.get_order()));
        this.newOrderLines = {};
        this.newOrder = undefined;
        this._isFinal = false;
        onMounted(() => {
            // Should create the new order outside of the constructor because
            // sequence_number of pos_session is modified. which will trigger
            // rerendering which will rerender this screen and will be infinite loop.
            this.newOrder = new Order(
                {},
                {
                    pos: this.env.pos,
                    temporary: true,
                }
            );
            this.render();
        });
    }
    get currentOrder() {
        return this.env.pos.get_order();
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
            if (this.env.pos.orderPreparationCategories.size) {
                this.currentOrder.updateLastOrderChange();
                this.newOrder.updateLastOrderChange();
            }

            this.newOrder.setCustomerCount(1);
            const newCustomerCount = this.currentOrder.getCustomerCount() - 1;
            this.currentOrder.setCustomerCount(newCustomerCount || 1);
            this.currentOrder.set_screen_data({ name: "ProductScreen" });

            const reactiveNewOrder = this.env.pos.makeOrderReactive(this.newOrder);
            this.env.pos.orders.add(reactiveNewOrder);
            this.env.pos.selectedOrder = reactiveNewOrder;
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

        this.env.pos
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
        const order = this.env.pos.get_order();
        let full = true;
        const splitlines = this.splitlines;
        const groupedLines = _.groupBy(order.get_orderlines(), (line) => line.get_product().id);

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
        const order = this.env.pos.get_order();
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
