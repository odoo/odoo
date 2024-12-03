import { registry } from "@web/core/registry";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillDestroy, useState } from "@odoo/owl";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";
import { OrderDisplay } from "@point_of_sale/app/components/order_display/order_display";

export class SplitBillScreen extends Component {
    static template = "pos_restaurant.SplitBillScreen";
    static components = { Orderline, OrderDisplay };
    static props = {
        disallow: { type: Boolean, optional: true },
    };

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

    async paySplittedOrder() {
        if (this.getNumberOfProducts() > 0) {
            const originalOrder = this.currentOrder;
            await this.createSplittedOrder();
            originalOrder.setScreenData({ name: "SplitBillScreen" });
        }
        this.pos.pay();
    }
    async transferSplittedOrder(event) {
        // Prevents triggering the 'startTransferOrder' event listener
        event.stopPropagation();
        if (this.getNumberOfProducts() > 0) {
            await this.createSplittedOrder();
        }
        this.pos.startTransferOrder();
    }

    // Calculates the sent quantities for both orders and adjusts for last_order_preparation_change.
    _getSentQty(ogLine, newLine, orderedQty) {
        const unorderedQty = ogLine.qty - orderedQty;

        const delta = newLine.qty - unorderedQty;
        const newQty = delta > 0 ? delta : 0;

        return {
            [ogLine.preparationKey]: orderedQty - newQty,
            [newLine.preparationKey]: newQty,
        };
    }

    async createSplittedOrder() {
        const curOrderUuid = this.currentOrder.uuid;
        const originalOrder = this.pos.models["pos.order"].find((o) => o.uuid === curOrderUuid);
        const originalOrderName = this._getOrderName(originalOrder);
        const newOrderName = this._getSplitOrderName(originalOrderName);

        const newOrder = this.pos.createNewOrder();
        newOrder.floating_order_name = newOrderName;
        newOrder.uiState.splittedOrderUuid = curOrderUuid;
        newOrder.originalSplittedOrder = originalOrder;

        let sentQty = {};
        // Create lines for the new order
        const lineToDel = [];
        for (const line of originalOrder.lines) {
            if (this.qtyTracker[line.uuid]) {
                const data = line.serialize();
                delete data.uuid;
                const newLine = this.pos.models["pos.order.line"].create(
                    {
                        ...data,
                        qty: this.qtyTracker[line.uuid],
                        order_id: newOrder.id,
                    },
                    false,
                    true
                );

                const orderedQty =
                    originalOrder.last_order_preparation_change.lines[line.preparationKey]
                        ?.quantity || 0;
                sentQty = { ...sentQty, ...this._getSentQty(line, newLine, orderedQty) };
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

        Object.keys(originalOrder.last_order_preparation_change.lines).forEach(
            (linePreparationKey) => {
                originalOrder.last_order_preparation_change.lines[linePreparationKey]["quantity"] =
                    sentQty[linePreparationKey];
            }
        );
        newOrder.updateLastOrderChange();
        Object.keys(newOrder.last_order_preparation_change.lines).forEach((linePreparationKey) => {
            newOrder.last_order_preparation_change.lines[linePreparationKey]["quantity"] =
                sentQty[linePreparationKey];
        });
        this.pos.addPendingOrder([originalOrder.id, newOrder.id]);

        originalOrder.customer_count -= 1;
        originalOrder.setScreenData({ name: "ProductScreen" });
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
