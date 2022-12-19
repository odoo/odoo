/** @odoo-module */

import { PosGlobalState, Order, Orderline, Payment } from "@point_of_sale/js/models";
import { uuidv4, batched } from "@point_of_sale/js/utils";
import core from "web.core";
import { Printer } from "@point_of_sale/js/printers";
import { patch } from "@web/core/utils/patch";
const QWeb = core.qweb;

patch(PosGlobalState.prototype, "pos_restaurant.PosGlobalState", {
    setup() {
        this._super(...arguments);
        this.orderToTransfer = null; // table transfer feature
        this.transferredOrdersSet = new Set(); // used to know which orders has been transferred but not sent to the back end yet
        this.printers_category_ids_set = new Set();
    },
    //@override
    async _processData(loadedData) {
        await this._super(...arguments);
        if (this.config.is_table_management) {
            this.floors = loadedData["restaurant.floor"];
            this.loadRestaurantFloor();
        }
        if (this.config.module_pos_restaurant) {
            this._loadRestaurantPrinter(loadedData["restaurant.printer"]);
        }
    },
    //@override
    async after_load_server_data() {
        var res = await this._super(...arguments);
        if (this.config.iface_floorplan) {
            this.table = null;
        }
        return res;
    },
    //@override
    // if we have tables, we do not load a default order, as the default order will be
    // set when the user selects a table.
    set_start_order() {
        if (!this.config.iface_floorplan) {
            this._super(...arguments);
        }
    },
    isInterfacePrinter() {
        return this.env.pos.config.iface_printers;
    },
    addSubmitOrderButton() {
        return this.config.module_pos_restaurant && this.unwatched.printers.length;
    },
    //@override
    createReactiveOrder(json) {
        let reactiveOrder = this._super(...arguments);
        if (this.isInterfacePrinter()) {
            const updateOrderChanges = () => {
                if (reactiveOrder.get_screen_data().name === "ProductScreen") {
                    reactiveOrder.updateChangesToPrint();
                }
            };
            reactiveOrder = owl.reactive(reactiveOrder, batched(updateOrderChanges));
            reactiveOrder.updateChangesToPrint();
        }
        return reactiveOrder;
    },
    _loadRestaurantPrinter(printers) {
        this.unwatched.printers = [];
        // list of product categories that belong to one or more order printer
        for (const printerConfig of printers) {
            const printer = this.create_printer(printerConfig);
            printer.config = printerConfig;
            this.unwatched.printers.push(printer);
            for (const id of printer.config.product_categories_ids) {
                this.printers_category_ids_set.add(id);
            }
        }
        this.config.iface_printers = !!this.unwatched.printers.length;
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
        await this._pushOrdersToServer();
        await this._removeOrdersFromServer();
        // This need to be called here otherwise _onReactiveOrderUpdated() will be called after the set is being cleared
        this.ordersToUpdateSet.clear();
        this.transferredOrdersSet.clear();
    },
    /**
     * Send the orders to be saved to the back end
     * @throw error
     */
    async _pushOrdersToServer() {
        const ordersUidsToSync = [...this.ordersToUpdateSet].map((order) => order.uid);
        const ordersToSync = this.db.get_unpaid_orders_to_sync(ordersUidsToSync);
        const ordersResponse = await this._save_to_server(ordersToSync, { draft: true });
        const tableOrders = [...this.ordersToUpdateSet].map((order) => order);
        ordersResponse.forEach((orderResponseData) =>
            this._updateOrder(orderResponseData, tableOrders)
        );
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
        if (this.config.iface_floorplan) {
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
        return (!this._transferredOrder(json) || this._isSameTable(json)) && (!this.selectedOrder || this._super(...arguments));
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
        return [...this.transferredOrdersSet].find(
            (order) => order.uid === json.uid
        );
    },
    _createOrder(json) {
        const transferredOrder = this._transferredOrder(json)
        if (this._isSameTable(json)) {
            // this means we transferred back to the original table, we'll prioritize the server state
            this.removeOrder(transferredOrder, false);
        }
        return this._super(...arguments);
    },
    loadRestaurantFloor() {
        // we do this in the front end due to the circular/recursive reference needed
        // Ignore floorplan features if no floor specified.
        this.config.iface_floorplan = !!(this.floors && this.floors.length > 0);
        if (this.config.iface_floorplan) {
            this.floors_by_id = {};
            this.tables_by_id = {};
            for (const floor of this.floors) {
                this.floors_by_id[floor.id] = floor;
                for (const table of floor.tables) {
                    this.tables_by_id[table.id] = table;
                    table.floor = floor;
                }
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
    unsetTable() {
        this._syncTableOrdersToServer();
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
    create_printer(config) {
        var url = config.proxy_ip || "";
        if (url.indexOf("//") < 0) {
            url = window.location.protocol + "//" + url;
        }
        if (url.indexOf(":", url.indexOf("//") + 2) < 0 && window.location.protocol !== "https:") {
            url = url + ":8069";
        }
        return new Printer(url, this);
    },
    isOpenOrderShareable() {
        return this._super(...arguments) || this.config.iface_floorplan;
    },
});

// New orders are now associated with the current table, if any.
patch(Order.prototype, "pos_restaurant.Order", {
    setup(options) {
        this._super(...arguments);
        if (this.pos.config.module_pos_restaurant) {
            if (this.pos.config.iface_floorplan && !this.tableId && !options.json && this.pos.table) {
                this.tableId = this.pos.table.id;
            }
            this.customerCount = this.customerCount || 1;
        }
        if (this.pos.isInterfacePrinter()) {
            // printedResume will store the previous state of the orderlines (when there were no skip), it will
            // store all the orderlines even if the product are not printable. This way, when we add a new category in
            // the printers, the already added products of the newly added category are not printed.
            this.printedResume = owl.markRaw(this.printedResume || {}); // we don't wanna track it and re-render
            // no need to store this in the backend, we can just compute it once the order is fetched from clicking a table
            if (!this.printingChanges) {
                this._resetPrintingChanges();
            }
        }
    },
    //@override
    export_as_JSON() {
        const json = this._super(...arguments);
        if (this.pos.config.module_pos_restaurant) {
            if (this.pos.config.iface_floorplan) {
                json.table_id = this.tableId;
            }
            json.customer_count = this.customerCount;
        }
        if (this.pos.isInterfacePrinter()) {
            json.multiprint_resume = JSON.stringify(this.printedResume);
            // so that it can be stored in local storage and be used when loading the pos in the floorscreen
            json.printing_changes = JSON.stringify(this.printingChanges);
        }
        return json;
    },
    //@override
    init_from_JSON(json) {
        this._super(...arguments);
        if (this.pos.config.module_pos_restaurant) {
            if (this.pos.config.iface_floorplan) {
                this.tableId = json.table_id;
                this.validation_date = moment.utc(json.creation_date).local().toDate();
            }
            this.customerCount = json.customer_count;
        }
        if (this.pos.isInterfacePrinter()) {
            this.printedResume = json.multiprint_resume && JSON.parse(json.multiprint_resume);
            this.printingChanges = json.printing_changes && JSON.parse(json.printing_changes);
        }
    },
    //@override
    export_for_printing() {
        const json = this._super(...arguments);
        if (this.pos.config.module_pos_restaurant) {
            if (this.pos.config.iface_floorplan && this.getTable()) {
                json.table = this.getTable().name;
            }
            json.customer_count = this.getCustomerCount();
        }
        return json;
    },
    _resetPrintingChanges() {
        this.printingChanges = { new: [], cancelled: [] };
    },
    /**
     * @returns {{ [productKey: string]: { product_id: number, name: string, note: string, quantity: number } }}
     */
    _computePrintChanges() {
        const changes = {};

        // If there's a new orderline, we add it otherwise we add the change if there's one
        this.orderlines.forEach((line) => {
            if (!line.mp_skip) {
                const productId = line.get_product().id;
                const note = line.get_note();
                const productKey = `${productId} - ${line.get_full_product_name()} - ${note}`;
                const lineKey = `${line.uuid} - ${note}`;
                const quantityDiff =
                    line.get_quantity() -
                    (this.printedResume[lineKey] ? this.printedResume[lineKey]["quantity"] : 0);
                if (quantityDiff) {
                    if (!changes[productKey]) {
                        changes[productKey] = {
                            product_id: productId,
                            name: line.get_full_product_name(),
                            note: note,
                            quantity: quantityDiff,
                        };
                    } else {
                        changes[productKey]["quantity"] += quantityDiff;
                    }
                    line.set_dirty(true);
                } else {
                    line.set_dirty(false);
                }
            }
        });

        // If there's an orderline that's not present anymore, we consider it as removed (even if note changed)
        for (const [lineKey, lineResume] of Object.entries(this.printedResume)) {
            if (!this._getPrintedLine(lineKey)) {
                const productKey = `${lineResume["product_id"]} - ${lineResume["name"]} - ${lineResume["note"]}`;
                if (!changes[productKey]) {
                    changes[productKey] = {
                        product_id: lineResume["product_id"],
                        name: lineResume["name"],
                        note: lineResume["note"],
                        quantity: -lineResume["quantity"],
                    };
                } else {
                    changes[productKey]["quantity"] -= lineResume["quantity"];
                }
            }
        }

        return changes;
    },
    _getPrintingCategoriesChanges(categories) {
        return {
            new: this.printingChanges["new"].filter((change) =>
                this.pos.db.is_product_in_category(categories, change["product_id"])
            ),
            cancelled: this.printingChanges["cancelled"].filter((change) =>
                this.pos.db.is_product_in_category(categories, change["product_id"])
            ),
        };
    },
    _getPrintedLine(lineKey) {
        return this.orderlines.find(
            (line) =>
                line.uuid === this.printedResume[lineKey]["line_uuid"] &&
                line.note === this.printedResume[lineKey]["note"]
        );
    },
    getCustomerCount() {
        return this.customerCount;
    },
    setCustomerCount(count) {
        this.customerCount = Math.max(count, 0);
    },
    getTable() {
        if (this.pos.config.iface_floorplan) {
            return this.pos.tables_by_id[this.tableId];
        }
        return null;
    },
    updatePrintedResume() {
        // we first remove the removed orderlines
        for (const lineKey in this.printedResume) {
            if (!this._getPrintedLine(lineKey)) {
                delete this.printedResume[lineKey];
            }
        }
        // we then update the added orderline or product quantity change
        this.orderlines.forEach((line) => {
            if (!line.mp_skip) {
                const note = line.get_note();
                const lineKey = `${line.uuid} - ${note}`;
                if (this.printedResume[lineKey]) {
                    this.printedResume[lineKey]["quantity"] = line.get_quantity();
                } else {
                    this.printedResume[lineKey] = {
                        line_uuid: line.uuid,
                        product_id: line.get_product().id,
                        name: line.get_full_product_name(),
                        note: note,
                        quantity: line.get_quantity(),
                    };
                }
                line.set_dirty(false);
            }
        });
        this._resetPrintingChanges();
    },
    updateChangesToPrint() {
        const changes = this._computePrintChanges(); // it's possible to have a change's quantity of 0
        // we thoroughly parse the changes we just computed to properly separate them into two
        const toAdd = [];
        const toRemove = [];

        for (const lineChange of Object.values(changes)) {
            if (lineChange["quantity"] > 0) {
                toAdd.push(lineChange);
            } else if (lineChange["quantity"] < 0) {
                lineChange["quantity"] *= -1; // we change the sign because that's how it is
                toRemove.push(lineChange);
            }
        }

        this.printingChanges = { new: toAdd, cancelled: toRemove };
    },
    hasChangesToPrint() {
        for (const printer of this.pos.unwatched.printers) {
            const changes = this._getPrintingCategoriesChanges(
                printer.config.product_categories_ids
            );
            if (changes["new"].length > 0 || changes["cancelled"].length > 0) {
                return true;
            }
        }
        return false;
    },
    hasSkippedChanges() {
        var orderlines = this.get_orderlines();
        for (var i = 0; i < orderlines.length; i++) {
            if (orderlines[i].mp_skip) {
                return true;
            }
        }
        return false;
    },
    async printChanges() {
        let isPrintSuccessful = true;
        const d = new Date();
        let hours = "" + d.getHours();
        hours = hours.length < 2 ? "0" + hours : hours;
        let minutes = "" + d.getMinutes();
        minutes = minutes.length < 2 ? "0" + minutes : minutes;

        for (const printer of this.pos.unwatched.printers) {
            const changes = this._getPrintingCategoriesChanges(
                printer.config.product_categories_ids
            );
            if (changes["new"].length > 0 || changes["cancelled"].length > 0) {
                const printingChanges = {
                    new: changes["new"],
                    cancelled: changes["cancelled"],
                    table_name: this.pos.config.iface_floorplan ? this.getTable().name : false,
                    floor_name: this.pos.config.iface_floorplan
                        ? this.getTable().floor.name
                        : false,
                    name: this.name || "unknown order",
                    time: {
                        hours,
                        minutes,
                    },
                };
                const receipt = QWeb.render("OrderChangeReceipt", { changes: printingChanges });
                const result = await printer.print_receipt(receipt);
                if (!result.successful) {
                    isPrintSuccessful = false;
                }
            }
        }
        return isPrintSuccessful;
    },
});

patch(Orderline.prototype, "pos_restaurant.Orderline", {
    setup() {
        this._super(...arguments);
        this.note = this.note || "";
        if (this.pos.isInterfacePrinter()) {
            this.uuid = this.uuid || uuidv4();
            // mp dirty is true if this orderline has changed since the last kitchen print
            this.mp_dirty = false;
            if (!this.mp_skip) {
                // mp_skip is true if the cashier want this orderline
                // not to be sent to the kitchen
                this.mp_skip = false;
            }
        }
    },
    //@override
    can_be_merged_with(orderline) {
        if (orderline.get_note() !== this.get_note()) {
            return false;
        } else {
            return !this.mp_skip && !orderline.mp_skip && this._super(...arguments);
        }
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
        if (this.pos.isInterfacePrinter()) {
            json.uuid = this.uuid;
            json.mp_skip = this.mp_skip;
        }
        return json;
    },
    //@override
    init_from_JSON(json) {
        this._super(...arguments);
        this.note = json.note;
        if (this.pos.isInterfacePrinter()) {
            this.uuid = json.uuid;
            this.mp_skip = json.mp_skip;
        }
    },
    set_note(note) {
        this.note = note;
    },
    get_note() {
        return this.note;
    },
    set_skip(skip) {
        if (this.mp_dirty && skip && !this.mp_skip) {
            this.mp_skip = true;
        }
        if (this.mp_skip && !skip) {
            this.mp_skip = false;
        }
    },
    set_dirty(dirty) {
        if (this.printable()) {
            this.mp_dirty = dirty;
        }
    },
    get_line_diff_hash() {
        if (this.get_note()) {
            return this.id + "|" + this.get_note();
        } else {
            return "" + this.id;
        }
    },
    // can this orderline be potentially printed ?
    printable() {
        return this.pos.db.is_product_in_category(
            this.pos.printers_category_ids_set,
            this.get_product().id
        );
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
