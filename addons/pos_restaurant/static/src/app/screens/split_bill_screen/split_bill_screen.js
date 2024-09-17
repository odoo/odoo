import { registry } from "@web/core/registry";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillDestroy, useState } from "@odoo/owl";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";
import { OrderDisplay } from "@point_of_sale/app/components/order_display/order_display";

export class SplitBillScreen extends Component {
    static template = "pos_restaurant.SplitBillScreen";
<<<<<<< saas-18.1:addons/pos_restaurant/static/src/app/screens/split_bill_screen/split_bill_screen.js
    static components = { Orderline, OrderDisplay };
    static props = {
        disallow: { type: Boolean, optional: true },
    };
||||||| 69b404c7109ff689381f56520aad758424ec01aa:addons/pos_restaurant/static/src/app/split_bill_screen/split_bill_screen.js
    static components = { Orderline, OrderWidget };
    static props = {
        disallow: { type: Boolean, optional: true },
    };
=======
    static components = { Orderline, OrderWidget };
    static props = {};
>>>>>>> f3f07012b8df310db66b3e6cf06ef5598346aadd:addons/pos_restaurant/static/src/app/split_bill_screen/split_bill_screen.js

    setup() {
        this.pos = usePos();
        this.ui = useState(useService("ui"));
        this.qtyTracker = useState({});
        this.priceTracker = useState({});

        onWillDestroy(() => {
            // Removing on all lines because the current order change during the split
            this.pos.models["pos.order.line"].map((l) => (l.uiState.splitQty = false));
        });
    }

    get currentOrder() {
        return this.pos.getOrder();
    }

    get orderlines() {
        return this.currentOrder.getOrderlines();
    }

    get newOrderPrice() {
        return Object.values(this.priceTracker).reduce((a, b) => a + b, 0);
    }

    getNumberOfProducts() {
        return Object.values(this.qtyTracker).reduce((a, b) => a + b, 0);
    }

    onClickLine(line) {
        const lines = line.getAllLinesInCombo();

        for (const line of lines) {
            if (!line.isPosGroupable()) {
                if (this.qtyTracker[line.uuid] === line.getQuantity()) {
                    this.qtyTracker[line.uuid] = 0;
                } else {
                    this.qtyTracker[line.uuid] = line.getQuantity();
                }
            } else if (!this.qtyTracker[line.uuid]) {
                this.qtyTracker[line.uuid] = 1;
            } else if (this.qtyTracker[line.uuid] === line.getQuantity()) {
                this.qtyTracker[line.uuid] = 0;
            } else {
                this.qtyTracker[line.uuid] += 1;
            }

            this.priceTracker[line.uuid] =
                (line.getPriceWithTax() / line.qty) * this.qtyTracker[line.uuid];
            this.setLineQtyStr(line);
        }
    }

    _getOrderName(order) {
        return order.table_id?.table_number.toString() || order.floatingOrderName || "";
    }

    _getLatestOrderNameStartingWith(name) {
        return (
            this.pos
                .getOpenOrders()
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

<<<<<<< saas-18.1:addons/pos_restaurant/static/src/app/screens/split_bill_screen/split_bill_screen.js
||||||| 69b404c7109ff689381f56520aad758424ec01aa:addons/pos_restaurant/static/src/app/split_bill_screen/split_bill_screen.js
    createSplittedOrder() {
=======
    // Meant to be overridden
    async preSplitOrder(originalOrder, newOrder) {}
    async postSplitOrder(originalOrder, newOrder) {}

>>>>>>> f3f07012b8df310db66b3e6cf06ef5598346aadd:addons/pos_restaurant/static/src/app/split_bill_screen/split_bill_screen.js
    async createSplittedOrder() {
        const curOrderUuid = this.currentOrder.uuid;
        const originalOrder = this.pos.models["pos.order"].find((o) => o.uuid === curOrderUuid);
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

                if (line.getQuantity() === this.qtyTracker[line.uuid]) {
                    lineToDel.push(line);
                } else {
                    line.qty = line.getQuantity() - this.qtyTracker[line.uuid];
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
        if (this.pos.config.preparationCategories.size) {
            originalOrder.updateLastOrderChange();
            newOrder.updateLastOrderChange();
        }

        originalOrder.customer_count -= 1;
<<<<<<< saas-18.1:addons/pos_restaurant/static/src/app/screens/split_bill_screen/split_bill_screen.js
        originalOrder.setScreenData({ name: "ProductScreen" });
||||||| 69b404c7109ff689381f56520aad758424ec01aa:addons/pos_restaurant/static/src/app/split_bill_screen/split_bill_screen.js
        originalOrder.set_screen_data({ name: "ProductScreen" });
=======
        await this.postSplitOrder(originalOrder, newOrder);
        originalOrder.set_screen_data({ name: "ProductScreen" });
>>>>>>> f3f07012b8df310db66b3e6cf06ef5598346aadd:addons/pos_restaurant/static/src/app/split_bill_screen/split_bill_screen.js
        this.pos.selectedOrderUuid = null;
        this.pos.setOrder(newOrder);
        this.back();
    }

    setLineQtyStr(line) {
        const splitQty = this.qtyTracker[line.uuid];
        line.uiState.splitQty = `${splitQty} / ${line.getQuantityStr()}`;
    }

    back() {
        this.pos.showScreen("ProductScreen");
    }
}

registry.category("pos_screens").add("SplitBillScreen", SplitBillScreen);
