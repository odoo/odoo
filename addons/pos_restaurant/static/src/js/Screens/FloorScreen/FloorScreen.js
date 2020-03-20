odoo.define('point_of_sale.FloorScreen', function(require) {
    'use strict';

    const { debounce } = owl.utils;
    const { PosComponent } = require('point_of_sale.PosComponent');
    const { Chrome } = require('point_of_sale.chrome');
    const { useState, useRef } = owl.hooks;
    const { useListener } = require('web.custom_hooks');
    const Registry = require('point_of_sale.ComponentsRegistry');

    class FloorScreen extends PosComponent {
        static template = 'FloorScreen';
        constructor() {
            super(...arguments);
            useListener('select-table', this._onSelectTable);
            useListener('deselect-table', this._onDeselectTable);
            useListener('save-table', this._onSaveTable);
            const firstFloor = this.env.pos.floors[0];
            this.state = useState({
                selectedFloorId: firstFloor.id,
                selectedTableId: null,
                isEditMode: false,
                isColorPicker: false,
                floorBackground: firstFloor.background_color,
            });
            this.floorMapRef = useRef('floor-map-ref');
            this.setTableColor = debounce(this.setTableColor, 70);
            this.setFloorColor = debounce(this.setFloorColor, 70);
        }
        patched() {
            this.floorMapRef.el.style.background = this.state.floorBackground;
        }
        mounted() {
            this.floorMapRef.el.style.background = this.state.floorBackground;
        }
        willUnmount() {}
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
        }
        toggleEditMode() {
            this.state.isEditMode = !this.state.isEditMode;
            this.state.selectedTableId = null;
        }
        toggleColorPicker() {
            this.state.isColorPicker = !this.state.isColorPicker;
        }
        async createTable() {
            const newTable = await this._createTable();
            if (newTable) {
                this.state.selectedTableId = newTable.id;
            }
        }
        async duplicateTable() {
            if (!this.selectedTable) return;
            const newTable = await this._createTable(this.selectedTable);
            if (newTable) {
                this.state.selectedTableId = newTable.id;
            }
        }
        async changeSeatsNum() {
            if (!this.selectedTable) return;
            const { confirmed, payload: inputNumber } = await this.showPopup('NumberPopup', {
                startingValue: this.selectedTable.seats,
                cheap: true,
                title: this.env._t('Number of Seats ?'),
            });
            if (!confirmed) return;
            const newSeatsNum = parseInt(inputNumber, 10) || this.selectedTable.seats;
            if (newSeatsNum !== this.selectedTable.seats) {
                this.selectedTable.seats = newSeatsNum;
                await this._save(this.selectedTable);
            }
        }
        async changeShape() {
            if (!this.selectedTable) return;
            this.selectedTable.shape = this.selectedTable.shape === 'square' ? 'round' : 'square';
            this.render();
            await this._save(this.selectedTable);
        }
        async renameTable() {
            if (!this.selectedTable) return;
            const { confirmed, payload: newName } = await this.showPopup('TextInputPopup', {
                startingValue: this.selectedTable.name,
                title: this.env._t('Table Name ?'),
            });
            if (!confirmed) return;
            if (newName !== this.selectedTable.name) {
                this.selectedTable.name = newName;
                await this._save(this.selectedTable);
            }
        }
        async setTableColor(color) {
            this.selectedTable.color = color;
            this.render();
            await this._save(this.selectedTable);
        }
        async setFloorColor(color) {
            this.state.floorBackground = color;
            this.activeFloor.background = color;
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
        async deleteTable() {
            if (!this.selectedTable) return;
            const { confirmed } = await this.showPopup('ConfirmPopup', {
                title: this.env._t('Are you sure ?'),
                body: this.env._t('Removing a table cannot be undone'),
            });
            if (!confirmed) return;
            try {
                await this.rpc({
                    model: 'restaurant.table',
                    method: 'create_from_ui',
                    args: [{ active: false, id: this.state.selectedTableId }],
                });
                this.activeFloor.tables = this.activeTables.filter(
                    table => table.id !== this.state.selectedTableId
                );
                this.state.selectedTableId = null;
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
                // this.showScreen('ProductScreen');
            }
        }
        _onDeselectTable() {
            this.state.selectedTableId = null;
        }
        async _createTable(copyTable) {
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
            const fields = this.env.pos.models.find(model => model.model === 'restaurant.table')
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
    }

    Registry.add('FloorScreen', FloorScreen);

    Chrome.setStartUpScreen(FloorScreen);

    return { FloorScreen };
});
