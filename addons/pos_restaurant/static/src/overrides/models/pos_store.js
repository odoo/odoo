import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { FloorScreen } from "@pos_restaurant/app/floor_screen/floor_screen";
import { ConnectionLostError } from "@web/core/network/rpc";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { uuidv4 } from "@point_of_sale/utils";
import { TipScreen } from "@pos_restaurant/app/tip_screen/tip_screen";

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

const { DateTime } = luxon;

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
            // Sync the number of orders on each table with other PoS
            this.getTableOrderCount();
        }
    },

    get firstScreen() {
        return this.config.module_pos_restaurant ? "FloorScreen" : super.firstScreen;
    },

    async getTableOrderCount() {
        this.lastWsTs = DateTime.now().ts;
        this.bus.subscribe("TABLE_ORDER_COUNT", this.ws_syncTableCount.bind(this));
    },
    // using the same floorplan.
    async ws_syncTableCount(data) {
        if (data.login_number === this.session.login_number) {
            this.computeTableCount(data);
            return;
        }

        const missingTable = data["table_ids"].find(
            (tableId) => !(tableId in this.models["restaurant.table"].getAllBy("id"))
        );
        if (missingTable) {
            const response = await this.data.searchRead("restaurant.floor", [
                ["pos_config_ids", "in", this.config.id],
            ]);

            const table_ids = response.map((floor) => floor.raw.table_ids).flat();
            await this.data.read("restaurant.table", table_ids);
        }
        const tableLocalOrders = this.models["pos.order"].filter(
            (o) => data["table_ids"].includes(o.table_id?.id) && !o.finalized
        );
        const localOrderlines = tableLocalOrders
            .filter((o) => typeof o.id === "number")
            .flatMap((o) => o.lines)
            .filter((l) => typeof l.id !== "number");
        const lineIdByOrderId = localOrderlines.reduce((acc, curr) => {
            if (!acc[curr.order_id.id]) {
                acc[curr.order_id.id] = [];
            }
            acc[curr.order_id.id].push(curr.id);
            return acc;
        }, {});

        const orders = await this.data.searchRead("pos.order", [
            ["session_id", "=", this.session.id],
            ["table_id", "in", data["table_ids"]],
        ]);
        await this.data.read(
            "pos.order.line",
            orders.flatMap((o) => o.lines).map((l) => l.id),
            ["qty"]
        );
        for (const [orderId, lineIds] of Object.entries(lineIdByOrderId)) {
            const lines = this.models["pos.order.line"].readMany(lineIds);
            for (const line of lines) {
                line.update({ order_id: orderId });
            }
        }

        let isDraftOrder = false;
        for (const order of orders) {
            if (order.state !== "draft") {
                this.removePendingOrder(order);
                continue;
            } else {
                this.addPendingOrder([order.id]);
            }

            const tableId = order.table_id?.id;
            if (!tableId) {
                continue;
            }

            const draftOrder = this.models["pos.order"].find(
                (o) => o.table_id?.id === tableId && o.id !== order.id && o.state === "draft"
            );

            if (!draftOrder) {
                continue;
            }

            for (const orphanLine of draftOrder.lines) {
                const adoptingLine = order.lines.find((l) => l.can_be_merged_with(orphanLine));
                if (adoptingLine && adoptingLine.id !== orphanLine.id) {
                    adoptingLine.merge(orphanLine);
                } else if (!adoptingLine) {
                    orphanLine.update({ order_id: order });
                }
            }

            if (this.selectedOrderUuid === draftOrder.uuid) {
                this.selectedOrderUuid = order.uuid;
            }

            await this.removeOrder(draftOrder, true);
            isDraftOrder = true;
        }

        if (
            this.get_order()?.finalized &&
            ![ReceiptScreen, TipScreen].includes(this.mainScreen.component)
        ) {
            this.add_new_order();
        }

        if (isDraftOrder) {
            await this.syncAllOrders();
        }

        this.computeTableCount(data);
    },
    cancelOrderNotification(data) {
        super.cancelOrderNotification(...arguments);
        this.computeTableCount(data);
    },
    async closingSessionNotification(data) {
        await super.closingSessionNotification(...arguments);
        this.computeTableCount(data);
    },
    computeTableCount(data) {
        const tableIds = data?.table_ids;
        const tables = tableIds
            ? this.models["restaurant.table"].readMany(tableIds)
            : this.models["restaurant.table"].getAll();
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
    getSyncAllOrdersContext(orders, options = {}) {
        const context = super.getSyncAllOrdersContext(...arguments);
        context["cancel_table_notification"] = options["cancel_table_notification"] || false;
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
            await this.syncAllOrders();
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
                    orphanLine.uuid = uuidv4();
                    orphanLine.update({ order_id: destinationOrder });
                }
            }

            await this.deleteOrders([order]);
        }

        await this.setTable(destinationTable);
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
    _shouldLoadOrders() {
        return super._shouldLoadOrders() || this.config.module_pos_restaurant;
    },
});
