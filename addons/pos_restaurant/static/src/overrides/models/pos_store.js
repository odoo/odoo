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
        this.orderToTransferUuid = null; // table transfer feature
        this.floorPlanStyle = "default";
        this.isEditMode = false;
        this.isTableToMerge = false;
        this.tableSyncing = false;
        await super.setup(...arguments);
        if (this.config.module_pos_restaurant) {
            this.setActivityListeners();
            this.showScreen("FloorScreen", { floor: this.selectedTable?.floor || null });
            this.currentFloor = this.config.floor_ids?.length > 0 ? this.config.floor_ids[0] : null;
            // Sync the number of orders on each table with other PoS
            this.getTableOrderCount();
        }
    },
    async getTableOrderCount() {
        const result = await this.data.call(
            "pos.config",
            "get_tables_order_count_and_printing_changes",
            [this.config.id]
        );
        this.ws_syncTableCount(result);
        this.bus.subscribe("TABLE_ORDER_COUNT", this.ws_syncTableCount.bind(this));
    },
    // using the same floorplan.
    async ws_syncTableCount(data) {
        const missingTable = data.find(
            (table) => !(table.id in this.models["restaurant.table"].getAllBy("id"))
        );

        if (missingTable) {
            const response = await this.data.searchRead("restaurant.floor", [
                ["pos_config_ids", "in", this.config.id],
            ]);

            const table_ids = response.map((floor) => floor.raw.table_ids).flat();
            await this.data.read("restaurant.table", table_ids);
        }

        const tableByIds = this.models["restaurant.table"].getAllBy("id");
        for (const table of data) {
            tableByIds[table.id].uiState.changeCount = table.changes;
            tableByIds[table.id].uiState.orderCount = table.orders;
            tableByIds[table.id].uiState.skipCount = table.skip_changes;
        }
    },
    get categoryCount() {
        const orderChange = this.getOrderChanges().orderlines;

        const categories = Object.values(orderChange).reduce((acc, curr) => {
            const categories =
                this.models["product.product"].get(curr.product_id)?.pos_categ_ids || [];

            for (const category of categories) {
                if (category) {
                    if (!acc[category.id]) {
                        acc[category.id] = {
                            count: curr.quantity,
                            name: category.name,
                        };
                    } else {
                        acc[category.id].count += curr.quantity;
                    }
                }
            }

            return acc;
        }, {});
        return Object.values(categories);
    },
    createNewOrder() {
        const order = super.createNewOrder(...arguments);

        if (this.config.module_pos_restaurant && this.selectedTable && !order.table_id) {
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
    add_new_order() {
        const order = super.add_new_order(...arguments);
        this.addPendingOrder([order.id]);
        return order;
    },
    getSyncAllOrdersContext(orders) {
        const context = super.getSyncAllOrdersContext(...arguments);
        if (this.config.module_pos_restaurant && this.selectedTable) {
            context["table_ids"] = [this.selectedTable.id];
            context["force"] = true;
        }
        return context;
    },
    getPendingOrder() {
        const context = this.getSyncAllOrdersContext();
        const { orderToCreate, orderToUpdate, paidOrdersNotSent } = super.getPendingOrder();

        if (!this.config.module_pos_restaurant || !context.table_ids || !context.table_ids.length) {
            return { orderToCreate, orderToUpdate, paidOrdersNotSent };
        }

        return {
            paidOrdersNotSent,
            orderToCreate: orderToCreate.filter(
                (o) => context.table_ids.includes(o.table_id.id) && !this.tableSyncing
            ),
            orderToUpdate: orderToUpdate.filter(
                (o) => context.table_ids.includes(o.table_id.id) && !this.tableSyncing
            ),
        };
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
        this.selectedTable = table;
        try {
            this.loadingOrderState = true;
            await this.syncAllOrders();
        } finally {
            this.loadingOrderState = false;
            let currentOrder = this.getTableOrders(table.id).find((order) =>
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
    getTableOrders(tableId) {
        return this.get_order_list().filter((order) => order.table_id?.id === tableId);
    },
    async unsetTable() {
        try {
            await this.syncAllOrders();
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
        return this.models["pos.order"]
            .filter((o) => !o.finalized)
            .some((o) => o.table_id?.id === table?.id && o.lines.length);
    },
    shouldShowNavbarButtons() {
        return super.shouldShowNavbarButtons(...arguments) && !this.orderToTransferUuid;
    },
    async transferTable(table) {
        const order = this.models["pos.order"].getBy("uuid", this.orderToTransferUuid);
        const originalTable = order.table_id;
        if (table.id === originalTable.id) {
            return;
        }
        if (
            order.table_id.id !== table.id &&
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
        this.loadingOrderState = false;
        if (this.isTableToMerge && order.table_id.id !== table.id) {
            originalTable.update({ parent_id: table });
            this.updateTables(originalTable);
            this.isTableToMerge = false;
        }
        order.update({ table_id: table });
        this.set_order(order);
        this.orderToTransferUuid = null;
        this.showScreen("ProductScreen");
    },
    updateTables(...tables) {
        this.data.call("restaurant.table", "update_tables", [
            tables.map((t) => t.id),
            Object.fromEntries(
                tables.map((t) => [
                    t.id,
                    { ...t.serialize({ orm: true }), parent_id: t.parent_id?.id || false },
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
