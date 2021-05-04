odoo.define('pos_restaurant.PointOfSaleModel', function (require) {
    'use strict';

    const PointOfSaleModel = require('point_of_sale.PointOfSaleModel');
    const { sum, generateWrappedName } = require('point_of_sale.utils');
    const { Printer } = require('point_of_sale.Printer');
    const { patch } = require('web.utils');
    const { qweb, _t } = require('web.core');
    const { parse } = require('web.field_utils');

    patch(PointOfSaleModel.prototype, 'pos_restaurant', {
        setup() {
            this._super(...arguments);
            this.ifaceFloorplan = false;
        },
        _initDataDerived() {
            const result = this._super();
            result.sortedFloors = [];
            return result;
        },
        _initDataUiState() {
            const result = this._super();
            result.activeTableId = false;
            result.activeFloorId = false;
            result.orderIdToTransfer = false;
            result.orderIdsToRemove = new Set([]);
            result.FloorScreen = {
                selectedTableId: false,
                isEditMode: false,
                tableBackendOrdersCount: {},
            };
            return result;
        },
        async _assignTopLevelFields() {
            await this._super();
            this.ifaceFloorplan =
                this.config.module_pos_restaurant && Boolean(this.getRecords('restaurant.floor').length);
            this.ifacePrinters = this.config.is_order_printer && Boolean(this.getRecords('restaurant.printer').length);
        },
        async _assignDataDerived() {
            await this._super();
            this.data.derived.sortedFloors = this.getRecords('restaurant.floor').sort(
                (a, b) => a.sequence - b.sequence
            );
            this._setKitchenPrinters();
        },
        _getDefaultTableId() {
            const firstFloor = this.data.derived.sortedFloors[0];
            const firstTableId = firstFloor.table_ids[0];
            if (!firstTableId) {
                return this.getRecords('restaurant.table')[0].id;
            } else {
                return firstTableId;
            }
        },
        _getStartScreens(activeOrder) {
            const result = this._super(...arguments);
            if (this.ifaceFloorplan) {
                result.push(['FloorScreen', 50]);
            }
            return result;
        },
        _getDefaultScreen() {
            if (this.ifaceFloorplan) {
                return 'FloorScreen';
            } else {
                return this._super(...arguments);
            }
        },
        async actionDoneLoading() {
            if (this.ifaceFloorplan) {
                const floor = this.data.derived.sortedFloors[0];
                this.data.uiState.activeTableId = false;
                this.data.uiState.activeFloorId = floor.id;
                this.data.uiState.FloorScreen.isEditMode = false;
            }
            await this._super();
        },
        async actionOrderDone(order, nextScreen) {
            await this._super(...arguments);
            if (nextScreen === 'FloorScreen') {
                await this.actionExitTable(this.getActiveTable());
            }
        },
        _shouldSetScreenToOrder(screen) {
            if (screen === 'TipScreen') return true;
            return this._super(...arguments);
        },
        _createDefaultOrder() {
            const result = this._super(...arguments);
            if (this.ifaceFloorplan) {
                result.table_id = this.data.uiState.activeTableId || this._getDefaultTableId();
            }
            result.customer_count = 1;
            return result;
        },
        _manageOrderWhenOrderDone() {
            if (!this.ifaceFloorplan) {
                this._super();
            }
        },
        getOrderJSON(order) {
            const result = this._super(...arguments);
            result.table_id = order.table_id;
            result.customer_count = order.customer_count;
            result.multiprint_resume =
                typeof order.multiprint_resume === 'string'
                    ? order.multiprint_resume
                    : JSON.stringify(order.multiprint_resume);
            return result;
        },
        getOrderlineJSON(orderline) {
            const result = this._super(...arguments);
            result.mp_dirty = orderline.mp_dirty;
            result.mp_skip = orderline.mp_skip;
            result.note = orderline.note;
            result.mp_hash = orderline.mp_hash;
            return result;
        },
        async actionSelectOrder(order) {
            await this._super(...arguments);
            if (this.ifaceFloorplan) {
                if (!this.data.uiState.OrderManagementScreen.managementOrderIds.has(order.id) && order.table_id) {
                    const table = this.getRecord('restaurant.table', order.table_id);
                    this.data.uiState.activeTableId = order.table_id;
                    this.data.uiState.activeFloorId = table.floor_id;
                }
                if (order.lines.length && !this.getActiveOrderline(order)) {
                    this.actionSelectOrderline(order, order.lines[order.lines.length - 1]);
                }
            }
        },
        async actionUpdateOrderline(orderline, vals) {
            if ('qty' in vals) {
                if (
                    this.ifacePrinters &&
                    !this.floatEQ(orderline.qty, vals.qty) &&
                    this._isProductInCategory(this.data.derived.printersCategoryIds, orderline.product_id)
                ) {
                    vals.mp_dirty = true;
                }
            } else if ('note' in vals) {
                vals.mp_dirty = true;
            } else if ('mp_skip' in vals) {
                if (orderline.mp_dirty && vals.mp_skip && !orderline.mp_skip) {
                    vals.mp_skip = true;
                }
                if (orderline.mp_skip && !vals.mp_skip) {
                    vals.mp_dirty = true;
                    vals.mp_skip = false;
                }
            }
            await this._super(...arguments);
        },
        _canBeMergedWith(existingLine, line2merge) {
            return (
                existingLine.note === line2merge.note &&
                !existingLine.mp_skip &&
                !line2merge.mp_skip &&
                this._super(...arguments)
            );
        },
        _createOrderline(vals) {
            if (this.ifacePrinters) {
                vals.mp_dirty = this._isProductInCategory(this.data.derived.printersCategoryIds, vals.product_id);
            }
            if (!('note' in vals)) {
                vals.note = '';
            }
            if (!('mp_hash' in vals)) {
                vals.mp_hash = this._getNextId();
            }
            return this._super(...arguments);
        },
        getActiveScreenProps() {
            const result = this._super(...arguments);
            result.activeFloor = this.getActiveFloor();
            return result;
        },
        getOrderInfo(order) {
            const receipt = this._super(...arguments);
            if (this.ifaceFloorplan) {
                const table = this.getRecord('restaurant.table', order.table_id);
                const floor = this.getRecord('restaurant.floor', table.floor_id);
                receipt.table = table ? table.name : '';
                receipt.floor = floor ? floor.name : '';
            }
            receipt.customer_count = order.customer_count;
            return receipt;
        },
        async _chooseActiveOrder(draftOrders) {
            if (!this.ifaceFloorplan) {
                await this._super(...arguments);
            }
        },

        _setKitchenPrinters() {
            const restaurantPrinters = this.getRecords('restaurant.printer');
            const printers = restaurantPrinters.map((config) => {
                const printer = this._createPrinter(config);
                printer.config = config;
                return printer;
            });
            // list of product categories that belong to one or more order printer
            const printersCategoryIds = [
                ...new Set(
                    restaurantPrinters.reduce(
                        (categoryIds, printer) => [...categoryIds, ...printer.product_categories_ids],
                        []
                    )
                ),
            ];
            this.data.derived.printers = printers;
            this.data.derived.printersCategoryIds = printersCategoryIds;
        },
        _createPrinter: function (config) {
            var url = config.proxy_ip || '';
            if (url.indexOf('//') < 0) {
                url = window.location.protocol + '//' + url;
            }
            if (url.indexOf(':', url.indexOf('//') + 2) < 0 && window.location.protocol !== 'https:') {
                url = url + ':8069';
            }
            return new Printer(url, this);
        },
        /**
         * from a product id, and a list of category ids, returns
         * true if the product belongs to one of the provided category
         * or one of its child categories.
         */
        _isProductInCategory: function (categoryIds, productId) {
            if (!(categoryIds instanceof Array)) {
                categoryIds = [categoryIds];
            }
            let cat = this.getRecord('product.product', productId).pos_categ_id;
            while (cat) {
                for (const categoryId of categoryIds) {
                    // The == is important, ids may be strings
                    if (cat == categoryId) {
                        return true;
                    }
                }
                cat = this.data.derived.categoryParent[cat];
            }
            return false;
        },
        _getLineDiffHash(orderline) {
            return `${orderline.mp_hash}` + (orderline.note ? `|${orderline.note}` : '');
        },
        _buildOrderResume(order) {
            const resume = {};
            for (const line of this.getOrderlines(order)) {
                if (line.mp_skip) continue;
                const lineHash = this._getLineDiffHash(line);
                if (typeof resume[lineHash] === 'undefined') {
                    resume[lineHash] = {
                        qty: line.qty,
                        note: line.note,
                        product_id: line.product_id,
                        product_name_wrapped: generateWrappedName(this.getFullProductName(line)),
                    };
                } else {
                    resume[lineHash].qty += line.qty;
                }
            }
            return resume;
        },
        _saveResumeChanges(order) {
            order.multiprint_resume = this._buildOrderResume(order);
            for (const orderline of this.getOrderlines(order)) {
                orderline.mp_dirty = false;
            }
        },
        _computeResumeChanges(order, categories) {
            const current_res = this._buildOrderResume(order);
            const old_res = order.multiprint_resume
                ? typeof order.multiprint_resume === 'string'
                    ? JSON.parse(order.multiprint_resume)
                    : order.multiprint_resume
                : {};
            let add = [];
            let rem = [];

            for (const line_hash in current_res) {
                const curr = current_res[line_hash];
                const old = old_res[line_hash];
                if (!old) {
                    add.push({
                        id: curr.product_id,
                        name: this.getRecord('product.product', curr.product_id).display_name,
                        name_wrapped: curr.product_name_wrapped,
                        note: curr.note,
                        qty: curr.qty,
                    });
                } else if (old.qty < curr.qty) {
                    add.push({
                        id: curr.product_id,
                        name: this.getRecord('product.product', curr.product_id).display_name,
                        name_wrapped: curr.product_name_wrapped,
                        note: curr.note,
                        qty: curr.qty - old.qty,
                    });
                } else if (old.qty > curr.qty) {
                    rem.push({
                        id: curr.product_id,
                        name: this.getRecord('product.product', curr.product_id).display_name,
                        name_wrapped: curr.product_name_wrapped,
                        note: curr.note,
                        qty: old.qty - curr.qty,
                    });
                }
            }

            for (const line_hash in old_res) {
                if (!current_res[line_hash]) {
                    const old = old_res[line_hash];
                    rem.push({
                        id: old.product_id,
                        name: this.getRecord('product.product', old.product_id).display_name,
                        name_wrapped: old.product_name_wrapped,
                        note: old.note,
                        qty: old.qty,
                    });
                }
            }

            if (categories && categories.length > 0) {
                // filter the added and removed orders to only contains
                // products that belong to one of the categories supplied as a parameter

                const _add = [];
                const _rem = [];

                for (const item of add) {
                    if (this._isProductInCategory(categories, item.id)) {
                        _add.push(item);
                    }
                }
                add = _add;

                for (const item of rem) {
                    if (this._isProductInCategory(categories, item.id)) {
                        _rem.push(item);
                    }
                }
                rem = _rem;
            }

            const d = new Date();
            let hours = '' + d.getHours();
            hours = hours.length < 2 ? '0' + hours : hours;
            let minutes = '' + d.getMinutes();
            minutes = minutes.length < 2 ? '0' + minutes : minutes;

            const table = this.getRecord('restaurant.table', order.table_id);
            const floor = this.getRecord('restaurant.floor', table.floor_id);

            return {
                new: add,
                cancelled: rem,
                table: table ? table.name : false,
                floor: floor ? floor.name : false,
                name: this.getOrderName(order),
                time: {
                    hours: hours,
                    minutes: minutes,
                },
            };
        },
        hasResumeChangesToPrint(order) {
            for (const printer of this.data.derived.printers) {
                var changes = this._computeResumeChanges(order, printer.config.product_categories_ids);
                if (changes['new'].length > 0 || changes['cancelled'].length > 0) {
                    return true;
                }
            }
            return false;
        },
        hasSkippedResumeChanges(order) {
            const orderlines = this.getOrderlines(order);
            for (const line of orderlines) {
                if (line.mp_skip) return true;
            }
            return false;
        },
        /**
         * @param {'pos.order'} order
         */
        _isFullPayOrder(originalOrder, splitlines) {
            const groupedLines = _.groupBy(this.getOrderlines(originalOrder), (line) => line.product_id);
            let full = true;
            for (const lineId in groupedLines) {
                let maxQuantity = groupedLines[lineId].reduce((quantity, line) => quantity + line.qty, 0);
                for (const id in splitlines) {
                    const split = splitlines[id];
                    if (split.product === groupedLines[lineId][0].product_id) {
                        maxQuantity -= split.quantity;
                    }
                }
                if (maxQuantity !== 0) {
                    full = false;
                }
            }
            return full;
        },
        async actionSetFloor(floor) {
            this.data.uiState.activeTableId = false;
            this.data.uiState.activeFloorId = floor.id;
            this.data.uiState.FloorScreen.isEditMode = false;
            await this.actionShowScreen('FloorScreen');
        },
        /**
         * Sets the active table and selects the order of the given order id.
         * @param {'restaurant.table'} table
         * @param {string | number} orderToSelectId
         */
        async actionSetTableWithOrder(table, orderToSelectId) {
            if (!this.exists('pos.order', orderToSelectId)) {
                return await this.actionSetTable(table);
            }
            const orderToSelect = this.getRecord('pos.order', orderToSelectId);
            if (orderToSelect.table_id !== table.id) {
                throw new Error("Can't select order that doesn't belong to the table.");
            }
            const currentlyActiveTable = this.getActiveTable();
            if (!currentlyActiveTable) {
                await this._fetchTableOrdersFromServer(table);
            } else if (table !== currentlyActiveTable) {
                await this._saveTableOrdersToServer(currentlyActiveTable);
                await this._fetchTableOrdersFromServer(table);
            }
            this.data.uiState.activeTableId = table.id;
            await this.actionSelectOrder(this.getRecord('pos.order', orderToSelectId));
        },
        /**
         * Sets the active table.
         * If no orders in the table, create new order.
         * Otherwise, activate one from the table orders.
         * @param {'restaurant.table'} table
         */
        async actionSetTable(table) {
            this.data.uiState.activeTableId = table.id;
            await this._fetchTableOrdersFromServer(table);
            if (this.data.uiState.orderIdToTransfer) {
                const orderToTransfer = this.getRecord('pos.order', this.data.uiState.orderIdToTransfer);
                this.updateRecord('pos.order', orderToTransfer.id, { table_id: table.id });
                this.data.uiState.orderIdToTransfer = false;
                await this.actionSelectOrder(orderToTransfer);
            } else {
                const tableOrders = this.getTableOrders(table);
                if (tableOrders.length) {
                    // IMPROVEMENT: It maybe better to prioritize selection of the orders in ProductScreen.
                    await this.actionSelectOrder(tableOrders[0]);
                } else {
                    await this.actionCreateNewOrder();
                }
            }
        },
        actionDeselectTable() {
            this.data.uiState.FloorScreen.selectedTableId = false;
        },
        async actionTransferOrder(order) {
            const table = this.getRecord('restaurant.table', order.table_id);
            this.updateRecord('pos.order', order.id, { table_id: false });
            await this.actionExitTable(table);
            this.data.uiState.orderIdToTransfer = order.id;
        },
        actionSetCustomerCount(order, count) {
            this.updateRecord('pos.order', order.id, { customer_count: count });
        },
        async actionSplitOrder(originalOrder, splitlines) {
            if (!this._isFullPayOrder(originalOrder, splitlines)) {
                let newOrder = await this._createDefaultOrder();
                for (let splitID in splitlines) {
                    const split = splitlines[splitID];

                    // don't take into account the split that has zero quantity
                    if (this.floatEQ(split.quantity, 0)) continue;

                    // create orderline for the new order
                    let originalOrderLine = this.getRecord('pos.order.line', splitID);
                    const line = this.cloneRecord('pos.order.line', originalOrderLine, {
                        id: this._getNextId(),
                        qty: split.quantity,
                    });
                    await this.addOrderline(newOrder, line);

                    let newQuantity = originalOrderLine.qty - line.qty;
                    // update the order being split
                    if (!this.checkDisallowDecreaseQuantity(originalOrderLine, newQuantity)) {
                        // update the orderline if quantity change is allowed
                        if (this.floatEQ(newQuantity, 0)) {
                            await this.actionDeleteOrderline(originalOrder, originalOrderLine);
                        } else {
                            await this.actionUpdateOrderline(originalOrderLine, { qty: newQuantity });
                        }
                    } else {
                        // create line with negative quantity if quantity change is not allowed
                        const removedLine = this.cloneRecord('pos.order.line', originalOrderLine, {
                            id: this._getNextId(),
                            qty: -split.quantity,
                        });
                        await this.addOrderline(originalOrder, removedLine);
                    }
                }
                this._setActiveOrderId(newOrder.id);
            }
            await this.actionShowScreen('PaymentScreen');
        },
        async actionPrintResumeChanges(order) {
            if (this.hasResumeChangesToPrint(order)) {
                let isPrintSuccessful = true;
                let errorMessage;
                for (const printer of this.data.derived.printers) {
                    const changes = this._computeResumeChanges(order, printer.config.product_categories_ids);
                    if (changes['new'].length > 0 || changes['cancelled'].length > 0) {
                        const receipt = qweb.render('OrderChangeReceipt', { changes: changes, widget: this });
                        const result = await printer.print_receipt(receipt);
                        if (!result.successful) {
                            isPrintSuccessful = false;
                            errorMessage = result.message;
                        }
                    }
                }
                if (isPrintSuccessful) {
                    this._saveResumeChanges(order);
                } else {
                    await this.ui.askUser('ErrorPopup', errorMessage);
                }
            }
        },
        getTableOrders(table) {
            if (!table) {
                return this.getDraftOrders();
            }
            return this.getDraftOrders().filter((order) => order.table_id === table.id);
        },
        getOrdersSelection() {
            const activeTable = this.getActiveTable();
            if (activeTable) {
                return this.getTableOrders(activeTable);
            } else {
                return this._super();
            }
        },
        getOrderCount(table) {
            return this.getTableOrders(table).length;
        },
        getTable(order) {
            if (order.table_id) {
                const table = this.getRecord('restaurant.table', order.table_id);
                const floor = this.getRecord('restaurant.floor', table.floor_id);
                return `${floor.name} (${table.name})`;
            } else {
                return '';
            }
        },
        getActiveTable() {
            return this.getRecord('restaurant.table', this.data.uiState.activeTableId);
        },
        getActiveFloor() {
            return this.getRecord('restaurant.floor', this.data.uiState.activeFloorId);
        },
        /**
         * Returns total number of customers in a table.
         * @param {'restaurant.table'} table
         */
        getTotalNumberCustomers(table) {
            return sum(this.getTableOrders(table), (order) => order.customer_count || 0);
        },
        getOrderFloor(order) {
            const table = this.getRecord('restaurant.table', order.table_id);
            return this.getRecord('restaurant.floor', table.floor_id);
        },

        //#region FloorScreen

        getSelectedTable() {
            return this.getRecord('restaurant.table', this.data.uiState.FloorScreen.selectedTableId);
        },
        _getNewTableName(name) {
            if (name) {
                const num = Number((name.match(/\d+/g) || [])[0] || 0);
                const str = name.replace(/\d+/g, '');
                const n = { num: num, str: str };
                n.num += 1;
                this._lastName = n;
            } else if (this._lastName) {
                this._lastName.num += 1;
            } else {
                this._lastName = { num: 1, str: 'T' };
            }
            return '' + this._lastName.str + this._lastName.num;
        },
        async saveTableToServer(table) {
            if (!table) return;
            try {
                const tableId = await this._rpc({
                    model: 'restaurant.table',
                    method: 'create_from_ui',
                    args: [table],
                });
                table.id = tableId;
                if (table.active) {
                    this.setRecord('restaurant.table', table.id, table);
                } else {
                    this.deleteRecord('restaurant.table', table.id);
                }
            } catch (error) {
                if (error instanceof Error) throw error;
                if (error && error.message && error.message.code < 0) {
                    await this.ui.askUser('ErrorPopup', {
                        title: _t('Offline'),
                        body: _t('Unable to create/edit/delete table because you are offline.'),
                    });
                }
            }
        },
        actionToggleEditMode() {
            this.data.uiState.FloorScreen.isEditMode = !this.data.uiState.FloorScreen.isEditMode;
            this.data.uiState.FloorScreen.selectedTableId = false;
        },
        actionSetFloorScreenSelectedTable(table) {
            this.data.uiState.FloorScreen.selectedTableId = table.id;
        },
        async actionCreateTable(floor) {
            const newTable = {
                position_v: 100,
                position_h: 100,
                width: 75,
                height: 75,
                shape: 'square',
                seats: 1,
                name: this._getNewTableName(),
                floor_id: floor.id,
                active: true,
            };
            await this.saveTableToServer(newTable);
            this.updateRecord('restaurant.floor', floor.id, { table_ids: [...floor.table_ids, newTable.id] });
            this.data.uiState.FloorScreen.selectedTableId = newTable.id;
        },
        async actionDuplicateTable(table) {
            const newTable = Object.assign({}, table);
            newTable.position_h += 10;
            newTable.position_v += 10;
            newTable.name = this._getNewTableName(newTable.name);
            delete newTable.id;
            await this.saveTableToServer(newTable);
            const floor = this.getRecord('restaurant.floor', table.floor_id);
            this.updateRecord('restaurant.floor', floor.id, { table_ids: [...floor.table_ids, newTable.id] });
            this.data.uiState.FloorScreen.selectedTableId = newTable.id;
        },
        async actionUpdateTable(table, vals) {
            this.updateRecord('restaurant.table', table.id, vals);
            if ('active' in vals && !vals.active) {
                this.data.uiState.FloorScreen.selectedTableId = false;
            }
            await this.saveTableToServer(table);
        },
        async actionDeleteTable(table) {
            const ordersInTable = this.getDraftOrders().filter((order) => order.table_id === table.id);
            if (ordersInTable.length) {
                this.ui.askUser('ErrorPopup', {
                    title: _t('Unable to delete table.'),
                    body: _t('There are orders linked to this table. Clear the table from orders before deleting.'),
                });
                return;
            }
            await this.saveTableToServer({ id: table.id, active: false });
            const floor = this.getRecord('restaurant.floor', table.floor_id);
            this.updateRecord('restaurant.floor', floor.id, {
                table_ids: floor.table_ids.filter((id) => id !== table.id),
            });
            this.deleteRecord('restaurant.table', table.id);
        },
        async actionUpdateFloor(floor, vals) {
            this.updateRecord('restaurant.floor', floor.id, vals);
            try {
                await this._rpc({
                    model: 'restaurant.floor',
                    method: 'write',
                    args: [[floor.id], vals],
                });
            } catch (error) {
                if (error instanceof Error) throw error;
                if (error.message.code < 0) {
                    await this.ui.askUser('OfflineErrorPopup', {
                        title: _t('Offline'),
                        body: _t('Unable to save changes to the server.'),
                    });
                }
            }
        },
        async actionUpdateTableOrderCounts() {
            try {
                const result = await this._rpc({
                    model: 'pos.config',
                    method: 'get_tables_order_count',
                    args: [this.config.id],
                });
                const tableBackendOrdersCount = this.data.uiState.FloorScreen.tableBackendOrdersCount;
                for (const { id, orders } of result) {
                    tableBackendOrdersCount[id] = orders;
                }
            } catch (error) {
                if (error.message.code < 0) {
                    await this.ui.askUser('OfflineErrorPopup', {
                        title: _t('Offline'),
                        body: _t('Unable to get orders count'),
                    });
                } else {
                    throw error;
                }
            }
        },

        //#endregion FloorScreen

        //#region ORDER SYNCING

        actionDeleteOrder(order) {
            this._super(...arguments);
            this._setOrderIdsToRemove([order]);
        },
        async actionExitTable(table) {
            if (table) {
                const floor = this.getRecord('restaurant.floor', table.floor_id);
                await this._saveTableOrdersToServer(table);
                await this.actionSetFloor(floor);
            } else {
                await this.actionShowScreen('FloorScreen');
            }
        },
        _setOrderIdsToRemove(orders) {
            for (const order of orders) {
                if (!order._extras.server_id) continue;
                this.data.uiState.orderIdsToRemove.add(order._extras.server_id);
            }
        },
        _deleteOrderIdsToRemove(orderIds) {
            for (const orderId of orderIds) {
                this.data.uiState.orderIdsToRemove.delete(orderId);
            }
        },
        _getOrderIdsToRemove() {
            return [...this.data.uiState.orderIdsToRemove];
        },
        /**
         * Save to server given draft orders.
         * @param {'pos.order'[]} orders
         */
        async _saveDraftOrders(orders) {
            try {
                if (orders.length) {
                    await this._pushOrders(orders, true);
                }
            } catch (error) {
                if (error instanceof Error) throw error;
                if (error.message && error.message && error.message.code < 0) {
                    console.error(error);
                }
            }
        },
        /**
         * Removes from server the deleted orders.
         */
        async removeDeletedOrders() {
            const orderIds = this._getOrderIdsToRemove();
            if (!orderIds.length) return;
            const deletedOrderIds = await this._rpc({
                model: 'pos.order',
                method: 'remove_from_ui',
                args: [orderIds],
            });
            this._deleteOrderIdsToRemove(deletedOrderIds);
        },
        /**
         * Saves the orders of the given table to the backend.
         * @related _fetchTableOrdersFromServer
         * @param {'restaurant.table'} table
         */
        async _saveTableOrdersToServer(table) {
            // Select the orders in the given table that have has orderlines
            // or already has server_id (which means that it is already synced).
            const ordersToSave = this.getDraftOrders().filter(
                (order) => order.table_id === table.id && (order.lines.length || order._extras.server_id)
            );
            await this._saveDraftOrders(ordersToSave);
            await this.removeDeletedOrders();
        },
        /**
         * Get from the backend the updated orders of the given table.
         * @related _saveTableOrdersToServer
         * @param {'restaurant.table'} table
         */
        async _fetchTableOrdersFromServer(table) {
            const data = await this._rpc({
                model: 'pos.order',
                method: 'get_table_draft_orders',
                args: [table.id],
            });
            // Delete the orders that are unvalidated and not-empty.
            const ordersToDelete = this.getTableOrders(table).filter(
                (order) => !order._extras.validationDate && order.lines.length
            );
            for (const order of ordersToDelete) {
                this.deleteOrder(order.id);
            }
            this._loadOrders(data);
        },
        _loadOrders(data) {
            let extras = {};
            for (const model in data) {
                for (const record of data[model]) {
                    if (model === 'pos.order') {
                        extras = this._defaultOrderExtras(record.id);
                        extras.server_id = record.server_id;
                    }
                    this.setRecord(model, record.id, record, extras);
                    extras = {};
                }
            }
        },

        //#endregion ORDER SYNCING

        //#region TIPPING

        canBeAdjusted(payment) {
            const paymentTerminal = this.getPaymentTerminal(payment.payment_method_id);
            if (paymentTerminal) {
                return paymentTerminal.canBeAdjusted(payment.id);
            }
            const paymentMethod = this.getRecord('pos.payment.method', payment.payment_method_id);
            return !paymentMethod.is_cash_count;
        },
        async actionSendPaymentAdjust(order, payment, ...otherArgs) {
            const paymentMethod = this.getRecord('pos.payment.method', payment.payment_method_id);
            const previousAmount = payment.amount;
            const { withTaxWithDiscount } = this.getOrderTotals(order);
            const amountPaid = this.getPaymentsTotalAmount(order);
            const amountDiff = withTaxWithDiscount - amountPaid;
            // if amountDiff is zero, do nothing.
            if (this.monetaryEQ(amountDiff, 0)) return;
            this.actionUpdatePayment(payment, { amount: previousAmount + amountDiff });
            await this.noMutexActionHandler({ name: 'actionSetPaymentStatus', args: [payment, 'waiting'] });
            const paymentTerminal = this.getPaymentTerminal(paymentMethod.id);
            const isAdjustSuccessful = await paymentTerminal.send_payment_adjust(payment.id, ...otherArgs);
            if (!isAdjustSuccessful) {
                this.actionUpdatePayment(payment, { amount: previousAmount });
            }
            await this.noMutexActionHandler({ name: 'actionSetPaymentStatus', args: [payment, 'done'] });
        },
        _defaultOrderExtras(uid) {
            const result = this._super(...arguments);
            result.TipScreen = {
                inputTipAmount: '',
            };
            return result;
        },
        async actionValidateTip(order, amount, nextScreen) {
            const serverId = order._extras.server_id;
            if (this.monetaryEQ(amount, 0)) {
                await this._rpc({
                    method: 'set_no_tip',
                    model: 'pos.order',
                    args: [serverId],
                });
                return this.actionOrderDone(order, nextScreen);
            }

            const { withTaxWithDiscount } = this.getOrderTotals(order);
            if (this.monetaryGT(amount, 0.25 * withTaxWithDiscount)) {
                const msg = _t("%s is more than 25% of the order's total amount. Are you sure of this tip amount?");
                const confirmed = await this.ui.askUser('ConfirmPopup', {
                    title: _t('Are you sure?'),
                    body: _.str.sprintf(msg, this.formatCurrency(amount)),
                });
                if (!confirmed) return;
            }

            const tipLine = await this._setTip(order, amount);

            const payments = this.getPayments(order);
            const mainPayment = payments[0];
            const paymentTerminal = this.getPaymentTerminal(mainPayment.payment_method_id);
            if (paymentTerminal) {
                this.actionUpdatePayment(mainPayment, { amount: mainPayment.amount + amount });
                await paymentTerminal.send_payment_adjust(mainPayment.id);
            }

            if (tipLine) {
                await this._rpc({
                    method: 'set_tip',
                    model: 'pos.order',
                    args: [serverId, this.getOrderlineJSON(tipLine)],
                });
            }
            await this.actionOrderDone(order, nextScreen);
        },
        async actionSettleTips(ordersToTip) {
            const activeOrder = this.getActiveOrder();
            // set tip in each order
            for (const order of ordersToTip) {
                const tipAmount = parse.float(order._extras.TipScreen.inputTipAmount);
                if (!order._extras.server_id) {
                    console.warn(
                        `${this.getOrderName(order)} is not yet sync. Sync it to server before setting a tip.`
                    );
                } else {
                    const result = await this._settleTip(order, tipAmount);
                    if (!result) break;
                }
            }
            if (this.exists(activeOrder.id)) {
                this.data.uiState.activeOrderId = activeOrder.id;
            } else {
                const orders = this.getDraftOrders();
                if (orders.length) {
                    this.data.uiState.activeOrderId = orders[0].id;
                }
            }
        },
        async _settleTip(order, amount) {
            try {
                const payment = this.getPayments(order)[0];
                const paymentTerminal = this.getPaymentTerminal(payment.payment_method_id);
                if (paymentTerminal) {
                    payment.amount += amount;
                    // temporarily set the activeOrder
                    this.data.uiState.activeOrderId = order.id;
                    await paymentTerminal.send_payment_adjust(payment.id);
                }

                if (this.monetaryEQ(amount, 0)) {
                    await this._rpc({
                        method: 'set_no_tip',
                        model: 'pos.order',
                        args: [order._extras.server_id],
                    });
                } else {
                    const tipLine = await this._setTip(order, amount);
                    await this._rpc({
                        method: 'set_tip',
                        model: 'pos.order',
                        args: [order._extras.server_id, this.getOrderlineJSON(tipLine)],
                    });
                }
                this._tryDeleteOrder(order);
                return true;
            } catch (error) {
                const msgTemplate = _t(
                    'Failed to set tip to %s. Do you want to proceed on setting the tips of the remaining?'
                );
                const confirmed = await this.ui.askUser('ConfirmPopup', {
                    title: _t('Failed to set tip'),
                    body: _.str.sprintf(msgTemplate, this.getOrderName(order)),
                });
                return confirmed;
            }
        },

        //#endregion TIPPING

        //#region AUTO_BACK_TO_FLOORSCREEN

        async _onAfterIdleCallback() {
            await this._super(...arguments);
            await this.actionHandler({ name: 'actionExitTable', args: [this.getActiveTable()] });
        },
        _shouldTriggerAfterIdleCallback() {
            return this._super(...arguments) && this.ifaceFloorplan && this.getActiveScreen() !== 'FloorScreen';
        },
        _shouldActivateActivityListeners() {
            return this.ifaceFloorplan ? true : this._super(...arguments);
        },

        //#endregion AUTO_BACK_TO_FLOORSCREEN
    });

    return PointOfSaleModel;
});
