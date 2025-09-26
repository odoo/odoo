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
        this.ui = useService("ui");
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
            if (!line.isPosGroupable() && !line.isPartOfCombo()) {
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
            // We need this split for decimal quantities (e.g. 0.5 kg)
            if (this.qtyTracker[line.uuid] > line.getQuantity()) {
                this.qtyTracker[line.uuid] = line.getQuantity();
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
        const totalQty = this.currentOrder.lines.reduce((sum, line) => sum + line.qty, 0);
        const selectedQty = this.getNumberOfProducts();

        if (selectedQty > 0 && selectedQty < totalQty) {
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

    waitForNewOrder(data) {
        return new Promise((resolve) => {
            this.pos.createNewOrder(data, (order) => {
                resolve(order);
            });
        });
    }

    async createSplittedOrder() {
        const curOrderUuid = this.currentOrder.uuid;
        const originalOrder = this.pos.models["pos.order"].find((o) => o.uuid === curOrderUuid);
        const originalOrderName = this._getOrderName(originalOrder);
        const newOrderName = this._getSplitOrderName(originalOrderName);

        const newOrder = await this.waitForNewOrder({});
        newOrder.floating_order_name = newOrderName;
        newOrder.uiState.splittedOrderUuid = curOrderUuid;
        originalOrder.uiState.splittedOrderUuid = newOrder.uuid;

        // Create lines for the new order
        const comboMap = new Map();
        const lineToDel = [];
        const newCourses = new Map();
        for (const line of originalOrder.lines) {
            if (this.qtyTracker[line.uuid]) {
                let newCourse;
                if (line.course_id) {
                    // Create courses in the new order
                    const { course_id: oldCourse } = line;
                    const courseIndex = oldCourse.index;
                    newCourse = newCourses.get(courseIndex);
                    if (!newCourse) {
                        newCourse = this.pos.models["restaurant.order.course"].create({
                            order_id: newOrder,
                            index: courseIndex,
                        });
                        newCourses.set(courseIndex, newCourse);
                    }
                }
                const data = { ...line.raw };

                // Combo lines will be relinked by the children
                delete data.combo_line_ids;
                delete data.uuid;
                delete data.id;
                const newLine = this.pos.models["pos.order.line"].create(
                    {
                        ...data,
                        qty: this.qtyTracker[line.uuid],
                        order_id: newOrder.id,
                        course_id: newCourse?.id,
                    },
                    false,
                    true
                );

                newLine.setHasChange(false);

                if (line.combo_line_ids.length > 0) {
                    for (const comboLine of line.combo_line_ids) {
                        comboMap.set(comboLine.uuid, newLine);
                    }
                }

                if (line.combo_parent_id) {
                    newLine.combo_parent_id = comboMap.get(line.uuid);
                }

                if (line.getQuantity() === this.qtyTracker[line.uuid]) {
                    lineToDel.push(line);
                } else {
                    const newQty = line.getQuantity() - this.qtyTracker[line.uuid];
                    line.update({ qty: newQty });
                }

                this.pos.handlePreparationHistory(
                    originalOrder.last_order_preparation_change.lines,
                    newOrder.last_order_preparation_change.lines,
                    line,
                    newLine,
                    this.qtyTracker[line.uuid]
                );
            }
        }

        for (const line of lineToDel) {
            line.delete();
        }

        await this.pos.syncAllOrders({ orders: [originalOrder, newOrder] });
        originalOrder.customer_count -= 1;
        originalOrder.setScreenData({ name: "ProductScreen" });
        this.pos.selectedOrderUuid = null;
        this.pos.setOrder(newOrder);
        this.back();
    }

    setLineQtyStr(line) {
        const splitQty = this.qtyTracker[line.uuid];
        line.uiState.splitQty = `${splitQty} / ${line.getQuantityStr().unitPart}`;
    }

    back() {
        this.pos.showScreen("ProductScreen");
    }
}

registry.category("pos_screens").add("SplitBillScreen", SplitBillScreen);
