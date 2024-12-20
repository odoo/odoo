import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { FloorScreen } from "@pos_restaurant/app/screens/floor_screen/floor_screen";
import { ConnectionLostError } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { EditOrderNamePopup } from "@pos_restaurant/app/popup/edit_order_name_popup/edit_order_name_popup";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

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
        this.isEditMode = false;
        this.tableSyncing = false;
        this.tableSelectorState = false;
        await super.setup(...arguments);
    },
    get firstScreen() {
        const screen = super.firstScreen;

        if (!this.config.module_pos_restaurant) {
            return screen;
        }

        return screen === "LoginScreen" ? "LoginScreen" : this.defaultScreen;
    },
    get defaultScreen() {
        if (this.config.module_pos_restaurant) {
            const screens = {
                register: "ProductScreen",
                tables: "FloorScreen",
            };
            return screens[this.config.default_screen];
        }
        return super.defaultScreen;
    },
    async onDeleteOrder(order) {
        const orderIsDeleted = await super.onDeleteOrder(...arguments);
        if (
            orderIsDeleted &&
            this.config.module_pos_restaurant &&
            this.mainScreen.component.name !== "TicketScreen"
        ) {
            this.showScreen("FloorScreen");
        }
    },
    // using the same floorplan.
    async wsSyncTableCount(data) {
        if (data["login_number"] === odoo.login_number) {
            return;
        }

        const orderIds = this.models["pos.order"]
            .filter((order) => !order.finalized && typeof order.id === "number")
            .map((o) => o.id);
        const orderToLoad = new Set([...data["order_ids"], ...orderIds]);
        await this.data.read("pos.order", [...orderToLoad]);
    },
    get categoryCount() {
        const orderChanges = this.getOrderChanges();
        const linesChanges = orderChanges.orderlines;

        const categories = Object.values(linesChanges).reduce((acc, curr) => {
            const categories =
                this.models["product.product"].get(curr.product_id)?.product_tmpl_id
                    ?.pos_categ_ids || [];

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
        const noteCount = ["general_customer_note", "internal_note"].reduce(
            (count, note) => count + (note in orderChanges ? 1 : 0),
            0
        );

        const nbNoteChange = Object.keys(orderChanges.noteUpdated).length;
        if (nbNoteChange) {
            categories["noteUpdate"] = { count: nbNoteChange, name: _t("Note") };
        }
        // Only send modeUpdate if there's already an older mode in progress.
        const currentOrder = this.getOrder();
        if (
            orderChanges.modeUpdate &&
            Object.keys(currentOrder.last_order_preparation_change.lines).length
        ) {
            const displayName = _t(currentOrder.preset_id?.name);
            categories["modeUpdate"] = { count: 1, name: displayName };
        }

        return [
            ...Object.values(categories),
            ...(noteCount > 0 ? [{ count: noteCount, name: _t("Message") }] : []),
        ];
    },
    get selectedTable() {
        return this.getOrder()?.table_id;
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
            const order = this.getOrder();
            if (order && order.getScreenData().name === "ReceiptScreen") {
                // When the order is finalized, we can safely remove it from the memory
                // We check that it's in ReceiptScreen because we want to keep the order if it's in a tipping state
                this.removeOrder(order);
            }
            this.showScreen(this.defaultScreen);
        }
    },
    shouldResetIdleTimer() {
        const stayPaymentScreen =
            this.mainScreen.component === PaymentScreen && this.getOrder().payment_ids.length > 0;
        return (
            this.config.module_pos_restaurant &&
            !stayPaymentScreen &&
            this.mainScreen.component !== FloorScreen
        );
    },
    showScreen(screenName, props = {}, newOrder = false) {
        const order = this.getOrder();
        if (
            this.config.module_pos_restaurant &&
            this.mainScreen.component === ProductScreen &&
            order &&
            !order.isBooked
        ) {
            this.removeOrder(order);
        }
        super.showScreen(...arguments);
        if (this.screenName != this.defaultScreen) {
            this.setIdleTimer();
        }
    },
    closeScreen() {
        if (this.config.module_pos_restaurant && !this.getOrder()) {
            return this.showScreen("FloorScreen");
        }
        return super.closeScreen(...arguments);
    },
    showDefault() {
        this.showScreen(this.defaultScreen, {}, this.defaultScreen == "ProductScreen");
    },
    addOrderIfEmpty(forceEmpty) {
        if (!this.config.module_pos_restaurant || forceEmpty) {
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
    //@override
    async afterProcessServerData() {
        this.floorPlanStyle =
            localStorage.getItem("floorPlanStyle") || (this.ui.isSmall ? "kanban" : "default");
        if (this.config.module_pos_restaurant) {
            this.setActivityListeners();
            this.currentFloor = this.config.floor_ids?.length > 0 ? this.config.floor_ids[0] : null;
            this.bus.subscribe("SYNC_ORDERS", this.wsSyncTableCount.bind(this));
        }

        return await super.afterProcessServerData(...arguments);
    },
    //@override
    addNewOrder(data = {}) {
        const order = super.addNewOrder(...arguments);
        this.addPendingOrder([order.id]);
        return order;
    },
    createOrderIfNeeded(data) {
        if (this.config.module_pos_restaurant && !data["table_id"]) {
            let order = this.models["pos.order"].find((order) => order.isDirectSale);
            if (!order) {
                order = this.createNewOrder(data);
            }
            return order;
        }
        return super.createOrderIfNeeded(...arguments);
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
    async addLineToCurrentOrder(vals, opts = {}, configure = true) {
        if (this.config.module_pos_restaurant && !this.getOrder().uiState.booked) {
            this.getOrder().setBooked(true);
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
            await this.syncAllOrders({ table_ids: tableIds });
        }
        //Need product details from backand to UI for urbanpiper
        return await super.getServerOrders();
    },
    getDefaultSearchDetails() {
        if (this.selectedTable && this.selectedTable.id) {
            return {
                fieldName: "REFERENCE",
                searchTerm: this.selectedTable.getName(),
            };
        }
        return super.getDefaultSearchDetails();
    },
    async setTable(table, orderUuid = null) {
        this.loadingOrderState = true;

        let currentOrder = table
            .getOrders()
            .find((order) => (orderUuid ? order.uuid === orderUuid : !order.finalized));

        if (currentOrder) {
            this.setOrder(currentOrder);
        } else {
            const potentialsOrders = this.models["pos.order"].filter(
                (o) => !o.table_id && !o.finalized && o.lines.length === 0
            );

            if (potentialsOrders.length) {
                currentOrder = potentialsOrders[0];
                currentOrder.update({ table_id: table });
                this.selectedOrderUuid = currentOrder.uuid;
            } else {
                this.addNewOrder({ table_id: table });
            }
        }
        try {
            this.loadingOrderState = true;
            const orders = await this.syncAllOrders({ throw: true });
            const orderUuids = orders.map((order) => order.uuid);
            for (const order of table.getOrders()) {
                if (
                    !orderUuids.includes(order.uuid) &&
                    typeof order.id === "number" &&
                    order.uiState.screen_data?.value?.name !== "TipScreen"
                ) {
                    order.delete();
                }
            }
        } finally {
            this.loadingOrderState = false;
        }
    },
    editFloatingOrderName(order) {
        this.dialog.add(EditOrderNamePopup, {
            title: _t("Edit Order Name"),
            placeholder: _t("18:45 John 4P"),
            startingValue: order.floating_order_name || "",
            getPayload: async (newName) => {
                if (typeof order.id == "number") {
                    this.data.write("pos.order", [order.id], {
                        floating_order_name: newName,
                    });
                } else {
                    order.floating_order_name = newName;
                }
            },
        });
    },
    setFloatingOrder(floatingOrder) {
        if (this.getOrder()?.isFilledDirectSale) {
            this.transferOrder(this.getOrder().uuid, null, floatingOrder);
            return;
        }
        this.setOrder(floatingOrder);

        const props = {};
        const screenName = floatingOrder.getScreenData().name;
        if (screenName === "PaymentScreen") {
            props.orderUuid = floatingOrder.uuid;
        }

        this.showScreen(screenName || "ProductScreen", props);
    },
    findTable(tableNumber) {
        const find_table = (t) => t.table_number === parseInt(tableNumber);
        return (
            this.currentFloor?.table_ids.find(find_table) ||
            this.models["restaurant.table"].find(find_table)
        );
    },
    searchOrder(buffer) {
        const table = this.findTable(buffer);
        if (table) {
            this.setTableFromUi(table);
            return true;
        }
        return false;
    },
    async setTableFromUi(table, orderUuid = null) {
        try {
            if (!orderUuid && this.getOrder()?.isFilledDirectSale) {
                this.transferOrder(this.getOrder().uuid, table);
                return;
            }
            this.tableSyncing = true;
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
            this.tableSyncing = false;
            const orders = this.getTableOrders(table.id);
            if (orders.length > 0) {
                this.setOrder(orders[0]);
                const props = {};
                if (orders[0].getScreenData().name === "PaymentScreen") {
                    props.orderUuid = orders[0].uuid;
                }
                this.showScreen(orders[0].getScreenData().name, props);
            } else {
                this.addNewOrder({ table_id: table });
                this.showScreen("ProductScreen");
            }
        }
    },
    getTableOrders(tableId) {
        return this.getOpenOrders().filter((order) => order.table_id?.id === tableId);
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
        const order = this.getOrder();
        if (order && !order.isBooked) {
            this.removeOrder(order);
        }
    },
    getActiveOrdersOnTable(table) {
        return this.models["pos.order"].filter(
            (o) => o.table_id?.id === table.id && !o.finalized && o.lines.length
        );
    },
    tableHasOrders(table) {
        return Boolean(table.getOrder());
    },
    getTableFromElement(el) {
        return this.models["restaurant.table"].get(
            [...el.classList].find((c) => c.includes("tableId")).split("-")[1]
        );
    },
    prepareOrderTransfer(order, destinationTable) {
        const originalTable = order.table_id;
        this.loadingOrderState = false;
        this.alert.dismiss();

        if (destinationTable.id === originalTable?.id) {
            this.setOrder(order);
            this.setTable(destinationTable);
            return false;
        }

        if (!this.tableHasOrders(destinationTable)) {
            order.origin_table_id = originalTable?.id;
            order.table_id = destinationTable;
            this.setOrder(order);
            this.addPendingOrder([order.id]);
            return false;
        }
        return true;
    },
    async updateOrderLinesForTableChange(orderDetails, canBeMergedWithLine = false) {
        const { sourceOrder, destinationOrder } = orderDetails;
        const linesToUpdate = [];

        for (const orphanLine of sourceOrder.lines) {
            const adoptingLine = destinationOrder?.lines.find((l) => l.canBeMergedWith(orphanLine));
            if (adoptingLine && canBeMergedWithLine) {
                if (sourceOrder.last_order_preparation_change.lines[orphanLine.preparationKey]) {
                    if (
                        destinationOrder.last_order_preparation_change.lines[
                            adoptingLine.preparationKey
                        ]
                    ) {
                        destinationOrder.last_order_preparation_change.lines[
                            adoptingLine.preparationKey
                        ]["quantity"] +=
                            sourceOrder.last_order_preparation_change.lines[
                                orphanLine.preparationKey
                            ]["quantity"];
                        destinationOrder.last_order_preparation_change.lines[
                            adoptingLine.preparationKey
                        ]["transferredQty"] =
                            sourceOrder.last_order_preparation_change.lines[
                                orphanLine.preparationKey
                            ]["quantity"];
                    } else {
                        destinationOrder.last_order_preparation_change.lines[
                            adoptingLine.preparationKey
                        ] = {
                            ...sourceOrder.last_order_preparation_change.lines[
                                orphanLine.preparationKey
                            ],
                            uuid: adoptingLine.uuid,
                            transferredQty:
                                sourceOrder.last_order_preparation_change.lines[
                                    orphanLine.preparationKey
                                ]["quantity"],
                        };
                    }
                }
                adoptingLine.merge(orphanLine);
            } else {
                if (
                    sourceOrder.last_order_preparation_change.lines[orphanLine.preparationKey] &&
                    !destinationOrder.last_order_preparation_change.lines[orphanLine.preparationKey]
                ) {
                    destinationOrder.last_order_preparation_change.lines[
                        orphanLine.preparationKey
                    ] = sourceOrder.last_order_preparation_change.lines[orphanLine.preparationKey];
                    orphanLine.skip_change = true;
                }
                linesToUpdate.push(orphanLine);
            }
        }

        linesToUpdate.forEach((orderline) => {
            if (!orderline.origin_order_id) {
                orderline.origin_order_id = orderline.order_id.id;
            }
            orderline.order_id = destinationOrder;
        });

        this.setOrder(destinationOrder);
        if (destinationOrder?.id) {
            this.addPendingOrder([destinationOrder.id]);
        }
    },
    async transferOrder(orderUuid, destinationTable = null, destinationOrder = null) {
        if (!destinationTable && !destinationOrder) {
            return;
        }
        const sourceOrder = this.models["pos.order"].getBy("uuid", orderUuid);

        if (destinationTable) {
            if (!this.prepareOrderTransfer(sourceOrder, destinationTable)) {
                return;
            }
            destinationOrder = this.getActiveOrdersOnTable(destinationTable.rootTable)[0];
        }
        await this.updateOrderLinesForTableChange({ sourceOrder, destinationOrder }, true);

        sourceOrder.isTransferedOrder = true;
        await this.deleteOrders([sourceOrder]);
        if (destinationTable) {
            await this.setTable(destinationTable);
        }
    },
    async mergeTableOrders(orderUuid, destinationTable) {
        const sourceOrder = this.models["pos.order"].getBy("uuid", orderUuid);

        if (!this.prepareOrderTransfer(sourceOrder, destinationTable)) {
            return;
        }

        const destinationOrder = this.getActiveOrdersOnTable(destinationTable.rootTable)[0];
        await this.updateOrderLinesForTableChange({ sourceOrder, destinationOrder }, false);
        await this.setTable(destinationTable);
    },
    async restoreOrdersToOriginalTable(orderToExtract, mergedOrder) {
        const orderlines = mergedOrder.lines.filter((line) => line.origin_order_id);
        for (const orderline of orderlines) {
            if (
                orderline?.origin_order_id.id === orderToExtract.id ||
                orderToExtract.table_id.children.length
            ) {
                orderline.order_id = orderToExtract;
                if (orderline?.origin_order_id.id === orderToExtract.id) {
                    if (orderline.skip_change) {
                        orderline.toggleSkipChange();
                    }
                    orderline.origin_order_id = null;
                }
                if (
                    mergedOrder.last_order_preparation_change.lines[orderline.preparationKey] &&
                    !orderToExtract.last_order_preparation_change.lines[orderline.preparationKey]
                ) {
                    orderToExtract.last_order_preparation_change.lines[orderline.preparationKey] =
                        mergedOrder.last_order_preparation_change.lines[orderline.preparationKey];
                    orderline.setHasChange(true);
                    orderline.toggleSkipChange();
                    orderline.uiState.hideSkipChangeClass = true;
                }
                delete mergedOrder.last_order_preparation_change.lines[orderline.preparationKey];
            }
        }

        this.addPendingOrder([orderToExtract.id, mergedOrder.id]);
        await this.setTable(orderToExtract.table_id);
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
    toggleEditMode() {
        this.isEditMode = !this.isEditMode;
        if (this.isEditMode) {
            this.tableSelectorState = false;
        }
    },
    storeFloorScrollPosition(floorId, position) {
        if (!floorId) {
            return;
        }
        this.floorScrollPositions = this.floorScrollPositions || {};
        this.floorScrollPositions[floorId] = position;
    },
    getFloorScrollPositions(floorId) {
        if (!floorId || !this.floorScrollPositions) {
            return;
        }
        return this.floorScrollPositions[floorId];
    },
});
