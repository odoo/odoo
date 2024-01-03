/** @odoo-module */
import { registry } from "@web/core/registry";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component, useState } from "@odoo/owl";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";

export class SplitBillScreen extends Component {
    static template = "pos_restaurant.SplitBillScreen";
    static components = { Orderline, OrderWidget };
    static props = {
        disallow: { type: Boolean, optional: true },
    };

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

    createSplittedOrder() {
        const curOrderUuid = this.currentOrder.uuid;
        this.newOrder = this.pos.createNewOrder();
        this.newOrder.uiState.splittedOrderUuid = curOrderUuid;

        // Create lines for the new order
        for (const line of this.orderlines) {
            if (this.qtyTracker[line.uuid]) {
                this.pos.models["pos.order.line"].create(
                    {
                        ...line.serialize(),
                        qty: this.qtyTracker[line.uuid],
                        order_id: this.newOrder.id,
                    },
                    false,
                    true
                );

                if (line.get_quantity() === this.qtyTracker[line.uuid]) {
                    line.delete();
                } else {
                    line.update({ qty: line.get_quantity() - this.qtyTracker[line.uuid] });
                }
            }
        }

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

        this.newOrder.originalSplittedOrder = this.currentOrder;
        this.newOrder.set_screen_data({ name: "PaymentScreen" });
        this.currentOrder.setCustomerCount(this.currentOrder.getCustomerCount() - 1);
        this.currentOrder.set_screen_data({ name: "ProductScreen" });

        this.pos.selectedOrderUuid = this.newOrder.uuid;
        this.pos.showScreen("PaymentScreen");
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
