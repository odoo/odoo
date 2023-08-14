odoo.define('pos_restaurant.FloorScreen', function (require) {
    'use strict';

    const { debounce } = owl.utils;
    const PosComponent = require('point_of_sale.PosComponent');
    const { useState, useRef } = owl.hooks;
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');

    class FloorScreen extends PosComponent {
        /**
         * @param {Object} props
         * @param {Object} props.floor
         */
        constructor() {
            super(...arguments);
            this._setTableColor = debounce(this._setTableColor, 70);
            this._setFloorColor = debounce(this._setFloorColor, 70);
            useListener('select-table', this._onSelectTable);
            useListener('deselect-table', this._onDeselectTable);
            useListener('save-table', this._onSaveTable);
            useListener('create-table', this._createTable);
            useListener('duplicate-table', this._duplicateTable);
            useListener('rename-table', this._renameTable);
            useListener('change-seats-num', this._changeSeatsNum);
            useListener('change-shape', this._changeShape);
            useListener('set-table-color', this._setTableColor);
            useListener('set-floor-color', this._setFloorColor);
            useListener('delete-table', this._deleteTable);
            const floor = this.props.floor ? this.props.floor : this.env.pos.floors[0];
            this.state = useState({
                selectedFloorId: floor.id,
                selectedTableId: null,
                isEditMode: false,
                floorBackground: floor.background_color,
                floorMapScrollTop: 0,
            });
            this.floorMapRef = useRef('floor-map-ref');
        }
        patched() {
            this.floorMapRef.el.style.background = this.state.floorBackground;
            this.state.floorMapScrollTop = this.floorMapRef.el.getBoundingClientRect().top;
        }
        mounted() {
            if (this.env.pos.table) {
                this.env.pos.set_table(null);
            }
            this.floorMapRef.el.style.background = this.state.floorBackground;
            this.state.floorMapScrollTop = this.floorMapRef.el.getBoundingClientRect().top;
            // call _tableLongpolling once then set interval of 5sec.
            this._tableLongpolling();
            this.tableLongpolling = setInterval(this._tableLongpolling.bind(this), 5000);
        }
        willUnmount() {
            clearInterval(this.tableLongpolling);
        }
        get activeFloor() {
            return this.env.pos.floors_by_id[this.state.selectedFloorId];
        }
        get activeTables() {
            return this.activeFloor.tables;
        }
        get isFloorEmpty() {
            return this.activeTables.length === 0;
        }
        get selectedTable() {
            return this.state.selectedTableId !== null
                ? this.env.pos.tables_by_id[this.state.selectedTableId]
                : false;
        }
        selectFloor(floor) {
            this.state.selectedFloorId = floor.id;
            this.state.floorBackground = this.activeFloor.background_color;
            this.state.isEditMode = false;
            this.state.selectedTableId = null;
        }
        toggleEditMode() {
            this.state.isEditMode = !this.state.isEditMode;
            this.state.selectedTableId = null;
        }
        async _createTable() {
            const newTable = await this._createTableHelper();
            if (newTable) {
                this.state.selectedTableId = newTable.id;
            }
        }
        async _duplicateTable() {
            if (!this.selectedTable) return;
            const newTable = await this._createTableHelper(this.selectedTable);
            if (newTable) {
                this.state.selectedTableId = newTable.id;
            }
        }
        async _changeSeatsNum() {
            const selectedTable = this.selectedTable
            if (!selectedTable) return;
            const { confirmed, payload: inputNumber } = await this.showPopup('NumberPopup', {
                startingValue: selectedTable.seats,
                cheap: true,
                title: this.env._t('Number of Seats ?'),
            });
            if (!confirmed) return;
            const newSeatsNum = parseInt(inputNumber, 10) || selectedTable.seats;
            if (newSeatsNum !== selectedTable.seats) {
                selectedTable.seats = newSeatsNum;
                await this._save(selectedTable);
            }
        }
        async _changeShape() {
            if (!this.selectedTable) return;
            this.selectedTable.shape = this.selectedTable.shape === 'square' ? 'round' : 'square';
            this.render();
            await this._save(this.selectedTable);
        }
        async _renameTable() {
            const selectedTable = this.selectedTable;
            if (!selectedTable) return;
            const { confirmed, payload: newName } = await this.showPopup('TextInputPopup', {
                startingValue: selectedTable.name,
                title: this.env._t('Table Name ?'),
            });
            if (!confirmed) return;
            if (newName !== selectedTable.name) {
                selectedTable.name = newName;
                await this._save(selectedTable);
            }
        }
        async _setTableColor({ detail: color }) {
            this.selectedTable.color = color;
            this.render();
            await this._save(this.selectedTable);
        }
        async _setFloorColor({ detail: color }) {
            this.state.floorBackground = color;
            this.activeFloor.background_color = color;
            try {
                await this.rpc({
                    model: 'restaurant.floor',
                    method: 'write',
                    args: [[this.activeFloor.id], { background_color: color }],
                });
            } catch (error) {
                if (error.message.code < 0) {
                    await this.showPopup('OfflineErrorPopup', {
                        title: this.env._t('Offline'),
                        body: this.env._t('Unable to change background color'),
                    });
                } else {
                    throw error;
                }
            }
        }
        async _deleteTable() {
            if (!this.selectedTable) return;
            const { confirmed } = await this.showPopup('ConfirmPopup', {
                title: this.env._t('Are you sure ?'),
                body: this.env._t('Removing a table cannot be undone'),
            });
            if (!confirmed) return;
            try {
                const originalSelectedTableId = this.state.selectedTableId;
                await this.rpc({
                    model: 'restaurant.table',
                    method: 'create_from_ui',
                    args: [{ active: false, id: originalSelectedTableId }],
                });
                this.activeFloor.tables = this.activeTables.filter(
                    (table) => table.id !== originalSelectedTableId
                );
                // Value of an object can change inside async function call.
                //   Which means that in this code block, the value of `state.selectedTableId`
                //   before the await call can be different after the finishing the await call.
                // Since we wanted to disable the selected table after deletion, we should be
                //   setting the selectedTableId to null. However, we only do this if nothing
                //   else is selected during the rpc call.
                if (this.state.selectedTableId === originalSelectedTableId) {
                    this.state.selectedTableId = null;
                }
            } catch (error) {
                if (error.message.code < 0) {
                    await this.showPopup('OfflineErrorPopup', {
                        title: this.env._t('Offline'),
                        body: this.env._t('Unable to delete table'),
                    });
                } else {
                    throw error;
                }
            }
        }
        _onSelectTable(event) {
            const table = event.detail;
            if (this.state.isEditMode) {
                this.state.selectedTableId = table.id;
            } else {
                this.env.pos.set_table(table);
            }
        }
        _onDeselectTable() {
            this.state.selectedTableId = null;
        }
        async _createTableHelper(copyTable) {
            let newTable;
            if (copyTable) {
                newTable = Object.assign({}, copyTable);
                newTable.position_h += 10;
                newTable.position_v += 10;
            } else {
                newTable = {
                    position_v: 100,
                    position_h: 100,
                    width: 75,
                    height: 75,
                    shape: 'square',
                    seats: 1,
                };
            }
            newTable.name = this._getNewTableName(newTable.name);
            delete newTable.id;
            newTable.floor_id = [this.activeFloor.id, ''];
            newTable.floor = this.activeFloor;
            try {
                await this._save(newTable);
                this.activeTables.push(newTable);
                return newTable;
            } catch (error) {
                if (error.message.code < 0) {
                    await this.showPopup('ErrorPopup', {
                        title: this.env._t('Offline'),
                        body: this.env._t('Unable to create table because you are offline.'),
                    });
                    return;
                } else {
                    throw error;
                }
            }
        }
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
        }
        async _save(table) {
            const fields = this.env.pos.models.find((model) => model.model === 'restaurant.table')
                .fields;
            const serializeTable = {};
            for (let field of fields) {
                if (typeof table[field] !== 'undefined') {
                    serializeTable[field] = table[field];
                }
            }
            serializeTable.id = table.id;
            const tableId = await this.rpc({
                model: 'restaurant.table',
                method: 'create_from_ui',
                args: [serializeTable],
            });
            table.id = tableId;
            this.env.pos.tables_by_id[tableId] = table;
        }
        async _onSaveTable(event) {
            const table = event.detail;
            await this._save(table);
        }
        async _tableLongpolling() {
            if (this.state.isEditMode) {
                return;
            }
            try {
                const result = await this.rpc({
                    model: 'pos.config',
                    method: 'get_tables_order_count',
                    args: [this.env.pos.config.id],
                });
                result.forEach((table) => {
                    const table_obj = this.env.pos.tables_by_id[table.id];
                    const unsynced_orders = this.env.pos
                        .get_table_orders(table_obj)
                        .filter(
                            (o) =>
                                o.server_id === undefined &&
                                (o.orderlines.length !== 0 || o.paymentlines.length !== 0) &&
                                // do not count the orders that are already finalized
                                !o.finalized
                        ).length;
                    table_obj.order_count = table.orders + unsynced_orders;
                });
                this.render();
            } catch (error) {
                if (error.message.code < 0) {
                    await this.showPopup('OfflineErrorPopup', {
                        title: 'Offline',
                        body: 'Unable to get orders count',
                    });
                } else {
                    throw error;
                }
            }
        }
    }
    FloorScreen.template = 'FloorScreen';
    FloorScreen.hideOrderSelector = true;

    Registries.Component.add(FloorScreen);

    return FloorScreen;
});
