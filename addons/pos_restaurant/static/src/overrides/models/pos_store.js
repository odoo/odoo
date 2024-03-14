/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { FloorScreen } from "@pos_restaurant/app/floor_screen/floor_screen";
import { TipScreen } from "@pos_restaurant/app/tip_screen/tip_screen";
import { ConnectionLostError } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { ask } from "@point_of_sale/app/store/make_awaitable_dialog";

const NON_IDLE_EVENTS = [
    "mousemove",
    "mousedown",
    "touchstart",
    "touchend",
    "touchmove",
    "click",
    "scroll",
    "keypress",
];
let IDLE_TIMER_SETTER;

patch(PosStore.prototype, {
    /**
     * @override
     */
    async setup() {
        this.tableNotifications = {};
        this.orderToTransfer = null; // table transfer feature
        this.transferredOrdersSet = new Set(); // used to know which orders has been transferred but not sent to the back end yet
        this.floorPlanStyle = "default";
        this.isEditMode = false;
        this.isTableToMerge = false;
        await super.setup(...arguments);
        if (this.config.module_pos_restaurant) {
            this.setActivityListeners();
            this.showScreen("FloorScreen", { floor: this.selectedTable?.floor || null });
        }
        this.currentFloor = this.config.floor_ids?.length > 0 ? this.config.floor_ids[0] : null;
    },
    setActivityListeners() {
        IDLE_TIMER_SETTER = this.setIdleTimer.bind(this);
        for (const event of NON_IDLE_EVENTS) {
            window.addEventListener(event, IDLE_TIMER_SETTER);
        }
    },
    setIdleTimer() {
        clearTimeout(this.idleTimer);
        if (this.shouldResetIdleTimer()) {
            this.idleTimer = setTimeout(() => this.actionAfterIdle(), 60000);
        }
    },
    async actionAfterIdle() {
        if (!document.querySelector(".modal-open")) {
            const table = this.selectedTable;
            const order = this.get_order();
            if (order && order.get_screen_data().name === "ReceiptScreen") {
                // When the order is finalized, we can safely remove it from the memory
                // We check that it's in ReceiptScreen because we want to keep the order if it's in a tipping state
                this.removeOrder(order);
            }
            this.setSelectedCategory(
                (this.config.start_category && this.config.iface_start_categ_id?.[0]) || 0
            );
            this.showScreen("FloorScreen", { floor: table?.floor });
        }
    },
    getReceiptHeaderData(order) {
        const json = super.getReceiptHeaderData(...arguments);
        if (this.config.module_pos_restaurant && order) {
            if (order.getTable()) {
                json.table = order.getTable().name;
            }
            json.customer_count = order.getCustomerCount();
        }
        return json;
    },
    shouldResetIdleTimer() {
        const stayPaymentScreen =
            this.mainScreen.component === PaymentScreen && this.get_order().paymentlines.length > 0;
        return (
            this.config.module_pos_restaurant &&
            !stayPaymentScreen &&
            this.mainScreen.component !== FloorScreen
        );
    },
    showScreen(screenName) {
        super.showScreen(...arguments);
        this.setIdleTimer();
    },
    closeScreen() {
        if (this.config.module_pos_restaurant && !this.get_order()) {
            return this.showScreen("FloorScreen");
        }
        return super.closeScreen(...arguments);
    },
    addOrderIfEmpty() {
        if (!this.config.module_pos_restaurant) {
            return super.addOrderIfEmpty(...arguments);
        }
    },
    /**
     * @override
     * Before closing pos, we remove the event listeners set on window
     * for detecting activities outside FloorScreen.
     */
    async closePos() {
        if (IDLE_TIMER_SETTER) {
            for (const event of NON_IDLE_EVENTS) {
                window.removeEventListener(event, IDLE_TIMER_SETTER);
            }
        }
        return super.closePos(...arguments);
    },
    showBackButton() {
        return (
            super.showBackButton(...arguments) ||
            this.mainScreen.component === TipScreen ||
            (this.mainScreen.component === ProductScreen && this.config.module_pos_restaurant)
        );
    },
    //@override
    async afterProcessServerData() {
        const res = await super.afterProcessServerData(...arguments);
        if (this.config.module_pos_restaurant) {
            this.selectedTable = null;
        }
        return res;
    },
    //@override
    // if we have tables, we do not load a default order, as the default order will be
    // set when the user selects a table.
    set_start_order() {
        if (!this.config.module_pos_restaurant) {
            super.set_start_order(...arguments);
        }
    },
    //@override
    add_new_order() {
        const order = super.add_new_order(...arguments);
        this.ordersToUpdateSet.add(order);
        return order;
    },
    async _getTableOrdersFromServer(tableIds) {
        const orders = await this.data.call("pos.order", "export_for_ui_table_draft", [tableIds]);
        return orders;
    },
    /**
     * Sync orders that got updated to the back end
     * @param tableId ID of the table we want to sync
     */
    async _syncTableOrdersToServer() {
        await this.sendDraftToServer();
        await this._removeOrdersFromServer();
        // This need to be called here otherwise _onReactiveOrderUpdated() will be called after the set is being cleared
        this.ordersToUpdateSet.clear();
        this.transferredOrdersSet.clear();
    },
    /**
     * Replace all the orders of a table by orders fetched from the backend
     * @param tableId ID of the table
     * @throws error
     */
    async _syncTableOrdersFromServer(tableId) {
        await this._removeOrdersFromServer(); // in case we were offline and we deleted orders in the mean time
        const ordersJsons = await this._getTableOrdersFromServer([tableId]);
        await this._addPricelists(ordersJsons);
        await this._addFiscalPositions(ordersJsons);
        const tableOrders = this.getTableOrders(tableId);
        this._replaceOrders(tableOrders, ordersJsons);
    },
    async _getOrdersJson() {
        if (this.config.module_pos_restaurant) {
            const tableIds = [].concat(
                ...this.models["restaurant.floor"].map((floor) =>
                    floor.table_ids.map((table) => table.id)
                )
            );
            await this._syncTableOrdersToServer(); // to prevent losing the transferred orders
            const ordersJsons = await this._getTableOrdersFromServer(tableIds); // get all orders
            await this._loadMissingProducts(ordersJsons);
            return ordersJsons;
        } else {
            return await super._getOrdersJson();
        }
    },
    _shouldRemoveOrder(order) {
        return super._shouldRemoveOrder(...arguments) && !this.transferredOrdersSet.has(order);
    },
    _shouldCreateOrder(json) {
        return (
            (!this._transferredOrder(json) || this._isSameTable(json)) &&
            (!this.selectedOrder || super._shouldCreateOrder(...arguments))
        );
    },
    _shouldRemoveSelectedOrder(removeSelected) {
        return this.selectedOrder && super._shouldRemoveSelectedOrder(...arguments);
    },
    _isSelectedOrder(json) {
        return !this.selectedOrder || super._isSelectedOrder(...arguments);
    },
    _isSameTable(json) {
        const transferredOrder = this._transferredOrder(json);
        return transferredOrder && transferredOrder.tableId === json.tableId;
    },
    _transferredOrder(json) {
        return [...this.transferredOrdersSet].find((order) => order.uid === json.uid);
    },
    _createOrder(json) {
        const transferredOrder = this._transferredOrder(json);
        if (this._isSameTable(json)) {
            // this means we transferred back to the original table, we'll prioritize the server state
            this.removeOrder(transferredOrder, false);
        }
        return super._createOrder(...arguments);
    },
    getDefaultSearchDetails() {
        if (this.selectedTable && this.selectedTable.id) {
            return {
                fieldName: "TABLE",
                searchTerm: this.selectedTable.name,
            };
        }
        return super.getDefaultSearchDetails();
    },
    async setTable(table, orderUid = null) {
        this.selectedTable = table;
        try {
            this.loadingOrderState = true;
            await this._syncTableOrdersFromServer(table.id);
        } finally {
            this.loadingOrderState = false;
            const currentOrder = this.getTableOrders(table.id).find((order) =>
                orderUid ? order.uid === orderUid : !order.finalized
            );
            if (currentOrder) {
                this.set_order(currentOrder);
            } else {
                this.add_new_order();
            }
        }
    },
    getTableOrders(tableId) {
        return this.get_order_list().filter((order) => order.tableId === tableId);
    },
    async unsetTable() {
        try {
            await this._syncTableOrdersToServer();
        } catch (e) {
            if (!(e instanceof ConnectionLostError)) {
                throw e;
            }
            Promise.reject(e);
        }
        this.selectedTable = null;
        const order = this.get_order();
        if (order && !order.isBooked) {
            this.removeOrder(order);
        }
        this.set_order(null);
    },
    tableHasOrders(table) {
        return this.orders.some(
            (o) => o?.tableId === table.id && o.finalized === false && o.orderlines.length
        );
    },
    shouldShowNavbarButtons() {
        return super.shouldShowNavbarButtons(...arguments) && !this.orderToTransfer;
    },
    async transferTable(table) {
        const originalTable = this.models["restaurant.table"].getBy(
            "id",
            this.orderToTransfer.tableId
        );
        if (table.id === originalTable.id) {
            return;
        }
        if (
            this.orderToTransfer.tableId !== table.id &&
            this.tableHasOrders(table) &&
            this.tableHasOrders(originalTable)
        ) {
            const confirm = await ask(this.dialog, {
                title: _t("Multiple open orders"),
                body: _t(
                    "Both tables have an open order. If you proceed, both orders will live on the same table. You can access them anytime from the Orders menu."
                ),
            });
            if (!confirm) {
                return;
            }
        }
        this.selectedTable = table;
        try {
            this.loadingOrderState = true;
            await this._syncTableOrdersFromServer(table.id);
        } finally {
            this.loadingOrderState = false;
            if (this.isTableToMerge && this.orderToTransfer.tableId !== table.id) {
                originalTable.update({ parent_id: table });
                this.updateTables(originalTable);
                this.isTableToMerge = false;
            }
            this.orderToTransfer.tableId = table.id;
            this.set_order(this.orderToTransfer);
            this.transferredOrdersSet.add(this.orderToTransfer);
            this.orderToTransfer = null;
        }
    },
    updateTables(...tables) {
        this.data.call("restaurant.table", "update_tables", [
            tables.map((t) => t.id),
            Object.fromEntries(
                tables.map((t) => [
                    t.id,
                    { ...t.serialize(true), parent_id: t.parent_id?.id || false },
                ])
            ),
        ]);
    },
    getCustomerCount(tableId) {
        const tableOrders = this.getTableOrders(tableId).filter((order) => !order.finalized);
        return tableOrders.reduce((count, order) => count + order.getCustomerCount(), 0);
    },
    isOpenOrderShareable() {
        return super.isOpenOrderShareable(...arguments) || this.config.module_pos_restaurant;
    },
    toggleEditMode() {
        this.isEditMode = !this.isEditMode;
    },
    async addProductToCurrentOrder(product, options = {}) {
        if (this.config.module_pos_restaurant && !this.get_order().booked) {
            this.get_order().setBooked(true);
        }
        return super.addProductToCurrentOrder(...arguments);
    },
});
