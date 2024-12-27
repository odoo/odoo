import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { FloorScreen } from "@pos_restaurant/app/floor_screen/floor_screen";
import { ConnectionLostError } from "@web/core/network/rpc";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

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
        this.orderToTransferUuid = null; // table transfer feature
        this.isEditMode = false;
        await super.setup(...arguments);
        this.floorPlanStyle =
            localStorage.getItem("floorPlanStyle") || (this.ui.isSmall ? "kanban" : "default");
        if (this.config.module_pos_restaurant) {
            this.setActivityListeners();
            this.currentFloor = this.config.floor_ids?.length > 0 ? this.config.floor_ids[0] : null;
        }
    },
    async recordSynchronisation(data) {
        await super.recordSynchronisation(...arguments);
        if (data.records["pos.order"]?.length > 0) {
            // Verify if there is only 1 order by table.
            const orderByTableId = this.models["pos.order"].reduce((acc, order) => {
                // Floating order doesn't need to be verified.
                if (!order.finalized && order.table_id?.id) {
                    acc[order.table_id.id] = acc[order.table_id.id] || [];
                    acc[order.table_id.id].push(order);
                }
                return acc;
            }, {});

            for (const orders of Object.values(orderByTableId)) {
                if (orders.length > 1) {
                    // The only way to get here is if there is several waiters on the same table.
                    // In this case we take orderline of the local order and we add it to the synced order.
                    const syncedOrder = orders.find((order) => typeof order.id === "number");
                    const localOrders = orders.find((order) => typeof order.id !== "number");

                    let watcher = 0;
                    while (localOrders.lines.length > 0) {
                        if (watcher > 1000) {
                            break;
                        }

                        const line = localOrders.lines.pop();
                        line.update({ order_id: syncedOrder });
                        line.setDirty();
                        watcher++;
                    }

                    // Remove local orders from the local database.
                    if (this.get_order()?.id === localOrders.id) {
                        this.set_order(syncedOrder);
                        this.addPendingOrder([syncedOrder.id]);
                    }

                    localOrders.delete();
                }
            }
            this.computeTableCount();
        }
    },
    get firstScreen() {
        return this.config.module_pos_restaurant ? "FloorScreen" : super.firstScreen;
    },
    async closingSessionNotification(data) {
        await super.closingSessionNotification(...arguments);
        this.computeTableCount();
    },
    computeTableCount() {
        const tables = this.models["restaurant.table"].getAll();
        const orders = this.get_open_orders();
        for (const table of tables) {
            const tableOrders = orders.filter(
                (order) => order.table_id?.id === table.id && !order.finalized
            );
            const qtyChange = tableOrders.reduce(
                (acc, order) => {
                    const quantityChange = this.getOrderChanges(false, order);
                    const quantitySkipped = this.getOrderChanges(true, order);
                    acc.changed += quantityChange.count;
                    acc.skipped += quantitySkipped.count;
                    return acc;
                },
                { changed: 0, skipped: 0 }
            );

            table.uiState.orderCount = tableOrders.length;
            table.uiState.changeCount = qtyChange.changed;
        }
    },
    get categoryCount() {
        const orderChange = this.getOrderChanges().orderlines;

        const categories = Object.values(orderChange).reduce((acc, curr) => {
            const categories =
                this.models["product.product"].get(curr.product_id)?.pos_categ_ids || [];

            for (const category of categories.slice(0, 1)) {
                if (!acc[category.id]) {
                    acc[category.id] = {
                        count: curr.quantity,
                        name: category.name,
                    };
                } else {
                    acc[category.id].count += curr.quantity;
                }
            }

            return acc;
        }, {});
        return Object.values(categories);
    },
    createNewOrder(data = {}) {
        const order = super.createNewOrder(...arguments);

        if (
            this.config.module_pos_restaurant &&
            this.selectedTable &&
            !order.table_id &&
            !("table_id" in data)
        ) {
            order.update({ table_id: this.selectedTable });
        }

        return order;
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
            this.idleTimer = setTimeout(() => this.actionAfterIdle(), 180000);
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
            this.mainScreen.component === PaymentScreen && this.get_order().payment_ids.length > 0;
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
        if (this.orderToTransferUuid) {
            return true;
        }
        if (this.config.module_pos_restaurant) {
            const screenWoBackBtn = [ReceiptScreen, FloorScreen, TicketScreen];
            return (
                !screenWoBackBtn.includes(this.mainScreen.component) ||
                (this.ui.isSmall && this.mainScreen.component === TicketScreen)
            );
        } else {
            return super.showBackButton(...arguments);
        }
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
    add_new_order() {
        const order = super.add_new_order(...arguments);
        this.addPendingOrder([order.id]);
        return order;
    },
    getPendingOrder() {
        const context = this.getSyncAllOrdersContext();
        const { orderToCreate, orderToUpdate, paidOrdersNotSent } = super.getPendingOrder();

        if (!this.config.module_pos_restaurant || !context.table_ids || !context.table_ids.length) {
            return { orderToCreate, orderToUpdate, paidOrdersNotSent };
        }

        return {
            paidOrdersNotSent,
            orderToCreate: orderToCreate.filter((o) => context.table_ids.includes(o.table_id?.id)),
            orderToUpdate: orderToUpdate.filter((o) => context.table_ids.includes(o.table_id?.id)),
        };
    },
    async addLineToCurrentOrder(vals, opts = {}, configure = true) {
        if (this.config.module_pos_restaurant && !this.get_order().uiState.booked) {
            this.get_order().setBooked(true);
        }
        return super.addLineToCurrentOrder(vals, opts, configure);
    },
    async getServerOrders() {
        if (this.config.module_pos_restaurant) {
            const tableIds = [].concat(
                ...this.models["restaurant.floor"].map((floor) =>
                    floor.table_ids.map((table) => table.id)
                )
            );
            return await this.syncAllOrders({ table_ids: tableIds });
        } else {
            return await super.getServerOrders();
        }
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
    async setTable(table, orderUuid = null) {
        const order = this.models["pos.order"].find(
            (o) => o.table_id?.id === table.id && !o.finalized
        );

        if (order) {
            this.addPendingOrder([order.id]);
        }

        this.selectedTable = table;
        try {
            this.loadingOrderState = true;
        } finally {
            this.loadingOrderState = false;

            const tableOrders = this.models["pos.order"].filter(
                (o) =>
                    o.table_id?.id === table.id &&
                    // Include the orders that are in tipping state.
                    (!o.finalized || o.uiState.screen_data?.value?.name === "TipScreen")
            );

            let currentOrder = tableOrders.find((order) =>
                orderUuid ? order.uuid === orderUuid : !order.finalized
            );

            if (currentOrder) {
                this.set_order(currentOrder);
            } else {
                const potentialsOrders = this.models["pos.order"].filter(
                    (o) => !o.table_id && !o.finalized && o.lines.length === 0
                );

                if (potentialsOrders.length) {
                    currentOrder = potentialsOrders[0];
                    currentOrder.update({ table_id: table });
                    this.selectedOrderUuid = currentOrder.uuid;
                } else {
                    this.add_new_order();
                }
            }
        }
    },
    async setTableFromUi(table, orderUuid = null) {
        try {
            if (table.parent_id) {
                table = table.getParent();
            }
            await this.setTable(table, orderUuid);
        } catch (e) {
            if (!(e instanceof ConnectionLostError)) {
                throw e;
            }
            // Reject error in a separate stack to display the offline popup, but continue the flow
            Promise.reject(e);
        } finally {
            const orders = this.getTableOrders(table.id);
            if (orders.length > 0) {
                this.set_order(orders[0]);
                this.orderToTransferUuid = null;
                this.showScreen(orders[0].get_screen_data().name);
            } else {
                this.add_new_order();
                this.showScreen("ProductScreen");
            }
        }
    },
    getTableOrders(tableId) {
        return this.get_open_orders().filter((order) => order.table_id?.id === tableId);
    },
    async unsetTable() {
        this.selectedTable = null;
        const order = this.get_order();
        if (order && !order.isBooked) {
            this.removeOrder(order);
        } else if (order) {
            if (!this.orderToTransferUuid) {
                this.syncAllOrders({ orders: [order] });
            } else {
                await this.syncAllOrders({ orders: [order] });
            }
        }

        this.set_order(null);
    },
    getActiveOrdersOnTable(table) {
        return this.models["pos.order"].filter(
            (o) => o.table_id?.id === table.id && !o.finalized && o.lines.length
        );
    },
    shouldShowNavbarButtons() {
        return super.shouldShowNavbarButtons(...arguments) && !this.orderToTransferUuid;
    },
    async transferOrder(destinationTable) {
        const order = this.models["pos.order"].getBy("uuid", this.orderToTransferUuid);
        const destinationOrder = this.getActiveOrdersOnTable(destinationTable)[0];
        const originalTable = order.table_id;

        this.orderToTransferUuid = null;
        this.loadingOrderState = false;

        // Only one order by table so we do nothing
        this.set_order(destinationOrder || order);
        if (!destinationOrder) {
            order.update({ table_id: destinationTable });
            return;
        } else if (destinationTable.id !== originalTable?.id || destinationOrder.id !== order.id) {
            for (const orphanLine of [...order.lines]) {
                const adoptingLine = destinationOrder.lines.find((l) =>
                    l.can_be_merged_with(orphanLine)
                );
                if (adoptingLine) {
                    adoptingLine.merge(orphanLine);
                    orphanLine.delete();
                } else {
                    // We cannot just change the order_id of the line because it will be deleted by the
                    // server when cancelling the order. We need to create a new line with the same values.
                    const serialized = orphanLine.serialize();
                    serialized.order_id = destinationOrder.id;
                    this.models["pos.order.line"].create(serialized, false, true);
                }
            }

            await this.deleteOrders([order]);
        }

        await this.setTable(destinationTable);
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
    _shouldLoadOrders() {
        return super._shouldLoadOrders() || this.config.module_pos_restaurant;
    },
});
