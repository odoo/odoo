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
                    this.config.module_pos_restaurant &&
                    this.mainScreen.component.name !== "PaymentScreen" &&
                    this.showScreen("FloorScreen"),
            },
        ];
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
    async closingSessionNotification(data) {
        await super.closingSessionNotification(...arguments);
        this.computeTableCount(data);
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
        this.addPendingOrder([order.id]);
        return order;
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
        this.selectedTable = table;

        const tableOrders = table.orders;

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
    tableHasOrders(table) {
        return Boolean(table.getOrder());
    },
    getTableFromElement(el) {
        return this.models["restaurant.table"].get(
            [...el.classList].find((c) => c.includes("tableId")).split("-")[1]
        );
    },
    async transferOrder(orderUuid, destinationTable) {
        const order = this.models["pos.order"].getBy("uuid", orderUuid);
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
            const destinationOrder = this.getActiveOrdersOnTable(destinationTable)[0];
            const linesToUpdate = [];
            for (const orphanLine of order.lines) {
                const adoptingLine = destinationOrder.lines.find((l) =>
                    l.can_be_merged_with(orphanLine)
                );
                if (adoptingLine) {
                    adoptingLine.merge(orphanLine);
                } else {
                    linesToUpdate.push(orphanLine);
                }
            }
            linesToUpdate.forEach((orderline) => {
                orderline.update({ order_id: destinationOrder });
            });
            this.set_order(destinationOrder);
            if (destinationOrder?.id) {
                this.addPendingOrder([destinationOrder.id]);
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
