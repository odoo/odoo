import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { ConnectionLostError } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    /**
     * @override
     */
    async setup() {
        this.isEditMode = false;
        this.tableSyncing = false;
        await super.setup(...arguments);
    },
    get idleTimeout() {
        return [
            ...super.idleTimeout,
            {
                timeout: 180000, // 3 minutes
                action: () =>
                    this.dialog.closeAll() &&
                    this.config.module_pos_restaurant &&
                    !["LoginScreen", "PaymentScreen"].includes(this.mainScreen.component.name) &&
                    this.showScreen("FloorScreen"),
            },
        ];
    },
    get firstScreen() {
        const screen = super.firstScreen;

        if (!this.config.module_pos_restaurant) {
            return screen;
        }

        return screen === "LoginScreen" ? "LoginScreen" : "FloorScreen";
    },
    async onDeleteOrder(order) {
        const orderIsDeleted = await super.onDeleteOrder(...arguments);
        if (
            this.config.module_pos_restaurant &&
            orderIsDeleted &&
            this.mainScreen.component.name !== "TicketScreen"
        ) {
            this.showScreen("FloorScreen");
        }
        return orderIsDeleted;
    },
    async closingSessionNotification() {
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
                    const quantitySkipped = this.getOrderChanges(true, order);
                    const quantityChange = this.getOrderChanges(false, order);
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
        const orderChanges = this.getOrderChanges();
        const linesChanges = orderChanges.orderlines;

        const categories = Object.values(linesChanges).reduce((acc, curr) => {
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

        const nbNoteChange = Object.keys(orderChanges.noteUpdated).length;
        if (nbNoteChange) {
            categories["noteUpdate"] = { count: nbNoteChange, name: _t("Note") };
        }
        // Only send modeUpdate if there's already an older mode in progress.
        const currentOrder = this.get_order();
        if (
            orderChanges.modeUpdate &&
            Object.keys(currentOrder.last_order_preparation_change.lines).length
        ) {
            const displayName = currentOrder.takeaway ? _t("Take out") : _t("Dine in");
            categories["modeUpdate"] = { count: 1, name: displayName };
        }

        return [
            ...Object.values(categories),
            ...("generalNote" in orderChanges ? [{ count: 1, name: _t("Message") }] : []),
        ];
    },
    createNewOrder() {
        const order = super.createNewOrder(...arguments);

        if (this.config.module_pos_restaurant && this.selectedTable && !order.table_id) {
            order.update({ table_id: this.selectedTable });
        }

        return order;
    },
    getReceiptHeaderData(order) {
        const json = super.getReceiptHeaderData(...arguments);
        if (this.config.module_pos_restaurant && order) {
            if (order.getTable()) {
                json.table = order.getTable().table_number;
            }
            json.customer_count = order.getCustomerCount();
        }
        return json;
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
    //@override
    async afterProcessServerData() {
        this.floorPlanStyle =
            localStorage.getItem("floorPlanStyle") || (this.ui.isSmall ? "kanban" : "default");
        if (this.config.module_pos_restaurant) {
            this.currentFloor = this.config.floor_ids?.length > 0 ? this.config.floor_ids[0] : null;
        }

        const res = await super.afterProcessServerData(...arguments);
        if (this.config.module_pos_restaurant) {
            this.selectedTable = null;
        }
        return res;
    },
    //@override
    add_new_order() {
        const order = super.add_new_order(...arguments);
        if (this.config.module_pos_restaurant) {
            this.addPendingOrder([order.id]);
        }
        return order;
    },
    async addLineToCurrentOrder(vals, opts = {}, configure = true) {
        if (this.config.module_pos_restaurant) {
            const order = this.get_order();
            this.addPendingOrder([order.id]);
            if (!this.get_order().uiState.booked) {
                this.get_order().setBooked(true);
            }
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
                fieldName: "TABLE",
                searchTerm: this.selectedTable.getName(),
            };
        }
        return super.getDefaultSearchDetails();
    },
    async setTable(table, orderUuid = null) {
        this.deviceSync.readDataFromServer();
        this.selectedTable = table;
        let currentOrder = table
            ? table.orders.find((o) => o.uuid === orderUuid || !o.finalized)
            : null;

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
    },
    async setTableFromUi(table, orderUuid = null) {
        try {
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
                this.set_order(orders[0]);
                const props = {};
                if (orders[0].get_screen_data().name === "PaymentScreen") {
                    props.orderUuid = orders[0].uuid;
                }
                this.showScreen(orders[0].get_screen_data().name, props);
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
        } else if (order && this.previousScreen !== "ReceiptScreen") {
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
    tableHasOrders(table) {
        return Boolean(table.getOrder());
    },
    getTableFromElement(el) {
        return this.models["restaurant.table"].get(
            [...el.classList].find((c) => c.includes("tableId")).split("-")[1]
        );
    },
    mergePreparationLines(preparationLine, destPreparationLine, destinationOrder, destOrderLine) {
        if (preparationLine && destPreparationLine) {
            destPreparationLine.quantity += preparationLine.quantity;
            preparationLine.quantity = 0;
        } else if (preparationLine) {
            const preparationLineCopy = { ...preparationLine };
            preparationLineCopy.order_id = destinationOrder.id;
            preparationLineCopy.uuid = destOrderLine.uuid;
            destinationOrder.last_order_preparation_change.lines[destOrderLine.preparationKey] =
                preparationLineCopy;
            preparationLine.quantity = 0;
        }
    },
    async transferOrder(orderUuid, destinationTable) {
        const order = this.models["pos.order"].getBy("uuid", orderUuid);
        const destinationOrder = this.getActiveOrdersOnTable(destinationTable)[0];
        await this.syncAllOrders({ orders: [destinationOrder || order] });
        const originalTable = order.table_id;
        this.loadingOrderState = false;
        this.alert.dismiss();
        if (destinationTable.id === originalTable?.id) {
            this.set_order(order);
            await this.setTable(destinationTable);
            return;
        }
        if (!this.tableHasOrders(destinationTable)) {
            order.update({ table_id: destinationTable });
            this.set_order(order);
            this.addPendingOrder([order.id]);
        } else {
            for (const orphanLine of order.lines) {
                const adoptingLine = destinationOrder.lines.find((l) =>
                    l.can_be_merged_with(orphanLine)
                );
                if (adoptingLine) {
                    adoptingLine.merge(orphanLine);
                    this.mergePreparationLines(
                        order.last_order_preparation_change.lines[orphanLine.preparationKey],
                        destinationOrder.last_order_preparation_change.lines[
                            adoptingLine.preparationKey
                        ],
                        destinationOrder,
                        adoptingLine
                    );
                } else {
                    const serialized = orphanLine.serialize();
                    serialized.order_id = destinationOrder.id;
                    delete serialized.uuid;
                    delete serialized.id;
                    const newOrderLine = this.models["pos.order.line"].create(
                        serialized,
                        false,
                        true
                    );

                    const preparationLine =
                        order.last_order_preparation_change.lines[orphanLine.preparationKey];
                    if (preparationLine) {
                        const preparationLineCopy = { ...preparationLine };
                        preparationLineCopy.order_id = destinationOrder.id;
                        destinationOrder.last_order_preparation_change.lines[
                            newOrderLine.preparationKey
                        ] = preparationLineCopy;
                        preparationLine.quantity = 0;
                    }
                }
            }

            this.set_order(destinationOrder);
            await this.deleteOrders([order]);
        }

        await this.syncAllOrders({ orders: [destinationOrder || order] });
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
    get showSaveOrderButton() {
        return super.showSaveOrderButton && !this.config.module_pos_restaurant;
    },
});
