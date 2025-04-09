import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { ConnectionLostError } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { EditOrderNamePopup } from "@pos_restaurant/app/popup/edit_order_name_popup/edit_order_name_popup";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";
import { SelectionPopup } from "@point_of_sale/app/components/popups/selection_popup/selection_popup";
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
                    this.dialog.closeAll() &&
                    this.config.module_pos_restaurant &&
                    !["PaymentScreen", "TicketScreen", "ActionScreen"].includes(
                        this.mainScreen.component.name
                    ) &&
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
    async sendOrderInPreparationUpdateLastChange(order, cancelled = false) {
        const currentPreset = order.preset_id;
        if (
            this.config.use_presets &&
            currentPreset?.use_guest &&
            !order.uiState.guestSetted &&
            !cancelled
        ) {
            const response = await this.setCustomerCount(order);
            if (!response) {
                return;
            }
            order.uiState.guestSetted = true;
        }

        if (!cancelled) {
            order.cleanCourses();
            const firstCourse = order.getFirstCourse();
            if (firstCourse && !firstCourse.fired) {
                firstCourse.fired = true;
                this.getOrder().deselectCourse();
            }
        }

        return await super.sendOrderInPreparationUpdateLastChange(order, cancelled);
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
        const mergedCourses = this.mergeCourses(sourceOrder, destOrder);
        while (sourceOrder.lines.length) {
            const orphanLine = sourceOrder.lines[0];
            const destinationLine = destOrder?.lines?.find((l) => l.canBeMergedWith(orphanLine));
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
                const serializedLine = { ...orphanLine.raw };
                serializedLine.order_id = destOrder.id;
                delete serializedLine.uuid;
                delete serializedLine.id;
                const newLine = this.models["pos.order.line"].create(serializedLine, false, true);
                newLine.course_id = orphanLine.course_id?.id;
                uuid = newLine.uuid;
                if (orphanLine.course_id && mergedCourses) {
                    // Replace new line uuid in the merged courses
                    const course = mergedCourses[orphanLine.course_id.uuid];
                    if (course?.lines) {
                        course.lines = course.lines.map((lineUuid) =>
                            lineUuid === orphanLine.uuid ? uuid : lineUuid
                        );
                    }
                }
                this.handlePreparationHistory(
                    sourceOrder.last_order_preparation_change.lines,
                    destOrder.last_order_preparation_change.lines,
                    orphanLine,
                    newLine,
                    orphanLine.qty
                );
            }

            if (sourceOrder.table_id) {
                destOrder.uiState.unmerge[uuid] = {
                    table_id: sourceOrder.table_id.id,
                    quantity: orphanLine.qty,
                };
            }

            orphanLine.delete();
            whileGuard++;
            if (whileGuard > 1000) {
                break;
            }
        }
        if (mergedCourses) {
            destOrder.uiState.unmergeCourses = {
                ...destOrder.uiState.unmergeCourses,
                ...mergedCourses,
            };
        }
        if (destOrder.courses) {
            // Ensure unassigned lines in destOrder are linked to the last course
            const lastCourse = destOrder.courses?.at(-1);
            if (lastCourse) {
                destOrder.lines.forEach((line) => {
                    if (!line.course_id) {
                        line.course_id = lastCourse;
                    }
                });
            }
        }

        this.deleteOrders([sourceOrder], [], true);
        this.syncAllOrders({ orders: [destOrder] });
        return destOrder;
    },
    mergeCourses(sourceOrder, destOrder) {
        if (!sourceOrder.hasCourses() && !destOrder?.hasCourses()) {
            return;
        }
        const result = {}; // Contains the required info to restore merge courses in the original table
        const courseMap = new Map();
        sourceOrder.course_ids.forEach((course) => {
            courseMap.set(course.index, course);
            result[course.uuid] = {
                table_id: sourceOrder.table_id?.id,
                lines: course.line_ids.map((l) => l.uuid),
                index: course.index,
                fired: course.fired,
                fired_date: course.fired_date,
            };
        });

        // Add courses from the target, merging lines if course numbers match
        destOrder.course_ids?.forEach((targetCourse) => {
            if (courseMap.has(targetCourse.index)) {
                // If the course already exists, merge the lines
                const sourceCourse = courseMap.get(targetCourse.index);
                if (sourceCourse) {
                    const sourceCourseLines = [...sourceCourse.line_ids];
                    sourceCourseLines.forEach((source_line) => {
                        source_line.course_id = targetCourse;
                        source_line.combo_line_ids?.forEach((line) => {
                            line.course_id = targetCourse;
                        });
                    });
                    result[targetCourse.uuid] = result[sourceCourse.uuid];
                    delete result[sourceCourse.uuid];
                }
            }
            courseMap.set(targetCourse.index, targetCourse);
        });

        // Ensures all courses are assigned to the target order
        const mergedCourses = Array.from(courseMap.values()).sort((a, b) => a.index - b.index);
        mergedCourses.forEach((course) => (course.order_id = destOrder.id));
        destOrder.course_ids = mergedCourses;
        return result;
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
        let beforeMergeCourseDetails;
        if (order?.uiState?.unmergeCourses) {
            beforeMergeCourseDetails = Object.entries(order.uiState.unmergeCourses).reduce(
                (acc, [uuid, details]) => {
                    if (details.table_id === unmergeTable.id) {
                        acc.push({
                            ...details,
                            uuid: uuid,
                        });
                    }
                    return acc;
                },
                []
            );
        }

        if (beforeMergeDetails.length) {
            const newOrder = this.addNewOrder({ table_id: unmergeTable });

            const courseByLines = {};
            if (beforeMergeCourseDetails?.length) {
                // Restore courses
                for (const courseDetails of beforeMergeCourseDetails) {
                    const course = this.data.models["restaurant.order.course"].create({
                        order_id: newOrder,
                        index: courseDetails.index,
                        fired: courseDetails.fired,
                        fired_date: courseDetails.fired_date,
                    });
                    courseDetails.lines?.forEach((lineUuid) => {
                        courseByLines[lineUuid] = course;
                    });
                    delete order.uiState.unmergeCourses[courseDetails.uuid];
                }
            }

            for (const detail of beforeMergeDetails) {
                const line = order.lines.find((l) => l.uuid === detail.uuid);
                const serializedLine = { ...line.raw };
                delete serializedLine.uuid;
                delete serializedLine.id;
                const course = courseByLines[detail.uuid];
                Object.assign(serializedLine, {
                    order_id: newOrder.id,
                    qty: detail.quantity,
                });

                const newLine = this.models["pos.order.line"].create(serializedLine, false, true);
                if (course) {
                    newLine.course_id = course;
                }
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
                    const quantityChange = this.getOrderChanges(order);
                    acc.changed += quantityChange.count;
                    return acc;
                },
                { changed: 0 }
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

        const data = await super.afterProcessServerData(...arguments);
        this.restoreSampleDataState();
        return data;
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
        let currentCourse;
        if (this.config.module_pos_restaurant) {
            const order = this.getOrder();
            if (!order.uiState.booked) {
                order.setBooked(true);
            }
            if (order.hasCourses()) {
                let course = order.getSelectedCourse();
                if (!course) {
                    course = order.getLastCourse();
                }
                currentCourse = course;
                order.selectCourse(course);
                vals = { ...vals, course_id: course };
            }
        }
        const result = await super.addLineToCurrentOrder(vals, opts, configure);

        if (currentCourse && result?.combo_line_ids) {
            result.combo_line_ids.forEach((line) => {
                line.course_id = currentCourse;
            });
        }

        return result;
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
        this.deviceSync.readDataFromServer();
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
                this.syncAllOrders();
            } else if (order && this.previousScreen !== "ReceiptScreen") {
                await this.syncAllOrders({ orders: [order] });
            }
        }
    },
    getActiveOrdersOnTable(table) {
        return this.models["pos.order"].filter((o) => o.table_id?.id === table.id && !o.finalized);
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
        const onClickWhileTransfer = async (ev) => {
            if (ev.target.closest(".button-floor")) {
                return;
            }
            this.isOrderTransferMode = false;
            const tableElement = ev.target.closest(".table");
            if (!tableElement) {
                return;
            }
            const table = this.getTableFromElement(tableElement);
            await this.transferOrder(orderUuid, table);
            this.setTableFromUi(table);
            document.removeEventListener("click", onClickWhileTransfer);
        };
        document.addEventListener("click", onClickWhileTransfer);
    },
    prepareOrderTransfer(order, destinationTable) {
        const originalTable = order.table_id;
        this.alert.dismiss();

        if (destinationTable.rootTable.id === originalTable?.id) {
            this.setOrder(order);
            this.setTable(destinationTable);
            return false;
        }

        if (!this.tableHasOrders(destinationTable)) {
            order.table_id = destinationTable;
            this.setOrder(order);
            this.syncAllOrders({ orders: [order] });
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
        await this.mergeOrders(sourceOrder, destinationOrder, destinationTable);
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
                    { ...t.serializeForORM(), parent_id: t.parent_id?.id || false },
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
    shouldCreatePendingOrder(order) {
        return super.shouldCreatePendingOrder(order) || order.course_ids?.length > 0;
    },
    setOrder(order) {
        order?.ensureCourseSelection();
        super.setOrder(order);
    },
    addCourse() {
        const order = this.getOrder();

        const course = this.data.models["restaurant.order.course"].create({
            order_id: order,
            index: order.getNextCourseIndex(),
        });
        let selectedCourse = course;
        if (order.course_ids.length === 1 && order.lines.length > 0) {
            // Assign order lines to the first course
            order.lines.forEach((line) => (line.course_id = course));
            // Create a second empty course
            selectedCourse = this.data.models["restaurant.order.course"].create({
                order_id: order,
                index: order.getNextCourseIndex(),
            });
        }
        order.recomputeOrderData(); // To ensure that courses are stored locally
        order.selectCourse(selectedCourse);
        return course;
    },
    async fireCourse(course) {
        const order = course.order_id;
        course.fired = true;
        order.deselectCourse();
        await this.sendOrderInPreparation(order, { firedCourseId: course.id, byPassPrint: true });
        await this.printCourseTicket(course);
        return true;
    },
    async printCourseTicket(course) {
        try {
            const changes = {
                new: [],
                cancelled: [],
                noteUpdate: course.lines.map((line) => ({ product_id: line.getProduct().id })),
                noteUpdateTitle: _t("Course %s fired", "" + course.index),
                printNoteUpdateData: false,
            };
            this.getOrder().uiState.lastPrint = changes;
            await this.printChanges(this.getOrder(), changes, false);
        } catch (e) {
            console.error("Unable to print course", e);
        }
    },
    async transferLinesToCourse() {
        const order = this.getOrder();
        if (!order) {
            return;
        }
        const selectedLine = order.getSelectedOrderline();
        const selectedCourse = order.getSelectedCourse()
            ? order.getSelectedCourse()
            : selectedLine.course_id;
        const selectionList = this.getOrder().courses.map((course) => ({
            id: course.id,
            label: course.name,
            isSelected: course.id === selectedCourse?.id,
            item: course,
        }));
        const dialogTitle = selectedLine
            ? _t('Transfer "%s" to:', selectedLine.getFullProductName())
            : _t('Transfer all products of "%s" into:', selectedCourse.name);
        const destCourse = await makeAwaitable(this.dialog, SelectionPopup, {
            title: dialogTitle,
            list: selectionList,
        });
        if (!destCourse) {
            return;
        }
        if (selectedLine) {
            selectedLine.course_id = destCourse.id;
        } else {
            const lines = [...selectedCourse.lines];
            lines.forEach((line) => {
                line.course_id = destCourse.id;
            });
        }
        order.selectCourse(destCourse);
        order.recomputeOrderData();
    },
    async loadSampleData() {
        if (this.config.module_pos_restaurant) {
            const data = { screen: "ProductScreen" };
            const table_number = this.getOrder()?.table_id?.table_number;
            if (table_number) {
                data.tableNumber = table_number;
            }
            sessionStorage.setItem("posPreSampleDataLoadState", JSON.stringify(data));
        }
        return super.loadSampleData();
    },
    restoreSampleDataState() {
        if (this.config.module_pos_restaurant) {
            let parsedState = sessionStorage.getItem("posPreSampleDataLoadState");
            if (!parsedState) {
                return;
            }
            try {
                sessionStorage.removeItem("posPreSampleDataLoadState");
                parsedState = JSON.parse(parsedState);
                const { tableNumber, screen } = parsedState;
                if (tableNumber) {
                    this.searchOrder(tableNumber);
                } else if (screen) {
                    this.showScreen(screen);
                }
            } catch (err) {
                console.error(err);
            }
        }
    },
});
