import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { ConnectionLostError } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { EditOrderNamePopup } from "@pos_restaurant/app/popup/edit_order_name_popup/edit_order_name_popup";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";

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
    createNewOrder(data) {
        const order = super.createNewOrder(data);

        if (order.table_id) {
            order.setCustomerCount(order.table_id.seats);
        }

        return order;
    },
    async setCustomerCount(o = false) {
        const currentOrder = o || this.getOrder();
        const count = await makeAwaitable(this.dialog, NumberPopup, {
            feedback: (buffer) => {
                const value = this.env.utils.formatCurrency(
                    currentOrder?.amountPerGuest(parseInt(buffer, 10) || 0) || 0
                );
                return value ? `${value} / ${_t("Guest")}` : "";
            },
        });
        const guestCount = parseInt(count, 10) || 0;
        if (guestCount == 0 && currentOrder.lines.length === 0) {
            this.removeOrder(currentOrder);
            this.showScreen("FloorScreen");
            return false;
        }
        currentOrder.setCustomerCount(guestCount);
        this.addPendingOrder([currentOrder.id]);
        return true;
    },
    async sendOrderInPreparationUpdateLastChange(o, cancelled = false) {
        const currentPreset = o.preset_id;
        if (
            this.config.use_presets &&
            currentPreset?.use_guest &&
            !o.uiState.guestSetted &&
            !cancelled
        ) {
            const response = await this.setCustomerCount(o);

            if (!response) {
                return;
            }

            o.uiState.guestSetted = true;
        }

        return await super.sendOrderInPreparationUpdateLastChange(o, cancelled);
    },
    handlePreparationHistory(srcPrep, destPrep, srcLine, destLine, qty) {
        const srcKey = srcLine.preparationKey;
        const destKey = destLine.preparationKey;
        const srcQty = srcPrep[srcKey]?.quantity;

        if (srcQty) {
            if (srcQty <= qty) {
                const newPrep = { ...srcPrep[srcKey], uuid: destLine.uuid };
                destPrep[destKey] = newPrep;
                delete srcPrep[srcKey];
            } else {
                srcPrep[srcKey].quantity = srcQty - qty;
                destPrep[destKey] = { ...srcPrep[srcKey], uuid: destLine.uuid, quantity: qty };
            }
        }
    },
    async mergeOrders(sourceOrder, destOrder) {
        let whileGuard = 0;
        while (sourceOrder.lines.length) {
            const orphanLine = sourceOrder.lines[0];
            const destinationLine = destOrder?.lines.find((l) => l.canBeMergedWith(orphanLine));
            let uuid = "";

            if (destinationLine) {
                destinationLine.merge(orphanLine);
                uuid = destinationLine.uuid;

                this.handlePreparationHistory(
                    sourceOrder.last_order_preparation_change.lines,
                    destOrder.last_order_preparation_change.lines,
                    orphanLine,
                    destinationLine,
                    orphanLine.qty
                );
            } else {
                const serializedLine = orphanLine.serialize({ orm: true });
                serializedLine.order_id = destOrder.id;
                delete serializedLine.uuid;
                delete serializedLine.id;
                const newLine = this.models["pos.order.line"].create(serializedLine, false, true);
                uuid = newLine.uuid;

                this.handlePreparationHistory(
                    sourceOrder.last_order_preparation_change.lines,
                    destOrder.last_order_preparation_change.lines,
                    orphanLine,
                    newLine,
                    orphanLine.qty
                );
            }

            destOrder.uiState.unmerge[uuid] = {
                table_id: sourceOrder.table_id.id,
                quantity: orphanLine.qty,
            };

            orphanLine.delete();
            whileGuard++;
            if (whileGuard > 1000) {
                break;
            }
        }

        await this.deleteOrders([sourceOrder], [], true);
        await this.syncAllOrders({ orders: [destOrder] });
        return destOrder;
    },
    async restoreOrdersToOriginalTable(order, unmergeTable) {
        if (!order?.uiState?.unmerge) {
            return false;
        }

        const beforeMergeDetails = Object.entries(order.uiState.unmerge).reduce(
            (acc, [uuid, details]) => {
                if (details.table_id === unmergeTable.id) {
                    acc.push({
                        quantity: details.quantity,
                        uuid: uuid,
                    });
                }
                return acc;
            },
            []
        );

        if (beforeMergeDetails.length) {
            const newOrder = this.addNewOrder({ table_id: unmergeTable });
            for (const detail of beforeMergeDetails) {
                const line = order.lines.find((l) => l.uuid === detail.uuid);
                const serializedLine = line.serialize({ orm: true });

                delete serializedLine.uuid;
                delete serializedLine.id;

                Object.assign(serializedLine, {
                    order_id: newOrder.id,
                    qty: detail.quantity,
                });

                const newLine = this.models["pos.order.line"].create(serializedLine, false, true);
                if (parseFloat(line.qty - detail.quantity) === 0) {
                    line.delete();
                } else {
                    line.setQuantity(line.qty - newLine.qty);
                }

                this.handlePreparationHistory(
                    order.last_order_preparation_change.lines,
                    newOrder.last_order_preparation_change.lines,
                    line,
                    newLine,
                    detail.quantity
                );

                delete order.uiState.unmerge[line.uuid];
            }

            await this.syncAllOrders({ orders: [order, newOrder] });
            return newOrder;
        }

        return false;
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
                    if (this.getOrder()?.id === localOrders.id) {
                        this.setOrder(syncedOrder);
                        this.addPendingOrder([syncedOrder.id]);
                    }

                    localOrders.delete();
                }
            }
            this.computeTableCount();
        }
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
        const orders = this.getOpenOrders();
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

        const nbNoteChange = Object.keys(orderChanges.noteUpdate).length;
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
    //@override
    async afterProcessServerData() {
        this.floorPlanStyle =
            localStorage.getItem("floorPlanStyle") || (this.ui.isSmall ? "kanban" : "default");
        if (this.config.module_pos_restaurant) {
            this.currentFloor = this.config.floor_ids?.length > 0 ? this.config.floor_ids[0] : null;
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
        if (this.config.module_pos_restaurant) {
            return {
                fieldName: "REFERENCE",
                searchTerm: "",
            };
        }
        return super.getDefaultSearchDetails();
    },
    async setTable(table, orderUuid = null) {
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
        const order = this.getOrder();
        if (order && !order.isBooked) {
            this.removeOrder(order);
        } else if (order) {
            if (!this.isOrderTransferMode) {
                this.syncAllOrders({ orders: [order] });
            } else {
                await this.syncAllOrders({ orders: [order] });
            }
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
    startTransferOrder() {
        this.isOrderTransferMode = true;
        const orderUuid = this.getOrder().uuid;
        this.getOrder().setBooked(true);
        this.showScreen("FloorScreen");
        document.addEventListener(
            "click",
            async (ev) => {
                this.isOrderTransferMode = false;
                const tableElement = ev.target.closest(".table");
                if (!tableElement) {
                    return;
                }
                const table = this.getTableFromElement(tableElement);
                await this.transferOrder(orderUuid, table);
                this.setTableFromUi(table);
            },
            { once: true }
        );
    },
    prepareOrderTransfer(order, destinationTable) {
        const originalTable = order.table_id;
        this.alert.dismiss();

        if (destinationTable.id === originalTable?.id) {
            this.setOrder(order);
            this.setTable(destinationTable);
            return false;
        }

        if (!this.tableHasOrders(destinationTable)) {
            order.table_id = destinationTable;
            this.setOrder(order);
            this.addPendingOrder([order.id]);
            return false;
        }
        return true;
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
        await this.mergeOrders(sourceOrder, destinationOrder);
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
        await this.mergeOrders(sourceOrder, destinationOrder);
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
