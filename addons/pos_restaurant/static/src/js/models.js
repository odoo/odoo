/** @odoo-module */

import { PosGlobalState, Order, Orderline, Payment } from "@point_of_sale/js/models";
import { ConnectionLostError } from "@web/core/network/rpc_service";
import { patch } from "@web/core/utils/patch";

patch(PosGlobalState.prototype, "pos_restaurant.PosGlobalState", {
    setup() {
        this._super(...arguments);
        this.orderToTransfer = null; // table transfer feature
        this.transferredOrdersSet = new Set(); // used to know which orders has been transferred but not sent to the back end yet
        this.floorPlanStyle = "default";
        this.isEditMode = false;
    },
    //@override
    async _processData(loadedData) {
        await this._super(...arguments);
        if (this.config.module_pos_restaurant) {
            this.floors = loadedData["restaurant.floor"];
            this.loadRestaurantFloor();
        }
    },
    //@override
    async after_load_server_data() {
        var res = await this._super(...arguments);
        if (this.config.module_pos_restaurant) {
            this.table = null;
        }
        return res;
    },
    //@override
    // if we have tables, we do not load a default order, as the default order will be
    // set when the user selects a table.
    set_start_order() {
        if (!this.config.module_pos_restaurant) {
            this._super(...arguments);
        }
    },
    //@override
    add_new_order() {
        const order = this._super(...arguments);
        this.ordersToUpdateSet.add(order);
        return order;
    },
    async _getTableOrdersFromServer(tableIds) {
        this.set_synch("connecting", 1);
        try {
            // FIXME POSREF timeout
            const orders = await this.env.services.orm.silent.call(
                "pos.order",
                "get_table_draft_orders",
                [tableIds]
            );
            this.set_synch("connected");
            return orders;
        } catch (error) {
            this.set_synch("error");
            throw error;
        }
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
                ...this.floors.map((floor) => floor.tables.map((table) => table.id))
            );
            await this._syncTableOrdersToServer(); // to prevent losing the transferred orders
            const ordersJsons = await this._getTableOrdersFromServer(tableIds); // get all orders
            return ordersJsons;
        } else {
            return await this._super();
        }
    },
    _shouldRemoveOrder(order) {
        return this._super(...arguments) && !this.transferredOrdersSet.has(order);
    },
    _shouldCreateOrder(json) {
        return (
            (!this._transferredOrder(json) || this._isSameTable(json)) &&
            (!this.selectedOrder || this._super(...arguments))
        );
    },
    _shouldRemoveSelectedOrder(removeSelected) {
        return this.selectedOrder && this._super(...arguments);
    },
    _isSelectedOrder(json) {
        return !this.selectedOrder || this._super(...arguments);
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
        return this._super(...arguments);
    },
    loadRestaurantFloor() {
        // we do this in the front end due to the circular/recursive reference needed
        // Ignore floorplan features if no floor specified.
        this.floors_by_id = {};
        this.tables_by_id = {};
        for (const floor of this.floors) {
            this.floors_by_id[floor.id] = floor;
            for (const table of floor.tables) {
                this.tables_by_id[table.id] = table;
                table.floor = floor;
            }
        }
    },
    async setTable(table, orderUid = null) {
        this.table = table;
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
        this.table = null;
        this.set_order(null);
    },
    setCurrentOrderToTransfer() {
        this.orderToTransfer = this.selectedOrder;
    },
    async transferTable(table) {
        this.table = table;
        try {
            this.loadingOrderState = true;
            await this._syncTableOrdersFromServer(table.id);
        } finally {
            this.loadingOrderState = false;
            this.orderToTransfer.tableId = table.id;
            this.set_order(this.orderToTransfer);
            this.transferredOrdersSet.add(this.orderToTransfer);
            this.orderToTransfer = null;
        }
    },
    getCustomerCount(tableId) {
        const tableOrders = this.getTableOrders(tableId).filter((order) => !order.finalized);
        return tableOrders.reduce((count, order) => count + order.getCustomerCount(), 0);
    },
    isOpenOrderShareable() {
        return this._super(...arguments) || this.config.module_pos_restaurant;
    },
    toggleEditMode() {
        this.isEditMode = !this.isEditMode;
    },
});

// New orders are now associated with the current table, if any.
patch(Order.prototype, "pos_restaurant.Order", {
    setup(options) {
        this._super(...arguments);
        if (this.pos.config.module_pos_restaurant) {
            if (!this.tableId && !options.json && this.pos.table) {
                this.tableId = this.pos.table.id;
            }
            this.customerCount = this.customerCount || 1;
        }
    },
    //@override
    export_as_JSON() {
        const json = this._super(...arguments);
        if (this.pos.config.module_pos_restaurant) {
            json.table_id = this.tableId;
            json.customer_count = this.customerCount;
        }

        return json;
    },
    //@override
    init_from_JSON(json) {
        this._super(...arguments);
        if (this.pos.config.module_pos_restaurant) {
            this.tableId = json.table_id;
            this.validation_date = moment.utc(json.creation_date).local().toDate();
            this.customerCount = json.customer_count;
        }
    },
    //@override
    export_for_printing() {
        const json = this._super(...arguments);
        if (this.pos.config.module_pos_restaurant) {
            if (this.getTable()) {
                json.table = this.getTable().name;
            }
            json.customer_count = this.getCustomerCount();
        }
        return json;
    },
    getCustomerCount() {
        return this.customerCount;
    },
    setCustomerCount(count) {
        this.customerCount = Math.max(count, 0);
    },
    getTable() {
        if (this.pos.config.module_pos_restaurant) {
            return this.pos.tables_by_id[this.tableId];
        }
        return null;
    },
});

patch(Orderline.prototype, "pos_restaurant.Orderline", {
    setup() {
        this._super(...arguments);
        this.note = this.note || "";
    },
    //@override
    clone() {
        const orderline = this._super(...arguments);
        orderline.note = this.note;
        return orderline;
    },
    //@override
    export_as_JSON() {
        const json = this._super(...arguments);
        json.note = this.note;
        if (this.pos.config.iface_printers) {
            json.uuid = this.uuid;
        }
        return json;
    },
    //@override
    init_from_JSON(json) {
        this._super(...arguments);
        this.note = json.note;
        if (this.pos.config.iface_printers) {
            this.uuid = json.uuid;
        }
    },
    get_line_diff_hash() {
        if (this.getNote()) {
            return this.id + "|" + this.getNote();
        } else {
            return "" + this.id;
        }
    },
});

patch(Payment.prototype, "pos_restaurant.Payment", {
    /**
     * Override this method to be able to show the 'Adjust Authorisation' button
     * on a validated payment_line and to show the tip screen which allow
     * tipping even after payment. By default, this returns true for all
     * non-cash payment.
     */
    canBeAdjusted() {
        if (this.payment_method.payment_terminal) {
            return this.payment_method.payment_terminal.canBeAdjusted(this.cid);
        }
        return !this.payment_method.is_cash_count;
    },
});
