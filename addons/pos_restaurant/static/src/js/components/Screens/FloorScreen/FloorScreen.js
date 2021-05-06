odoo.define('pos_restaurant.FloorScreen', function (require) {
    'use strict';

    const { debounce } = owl.utils;
    const { useState, useRef } = owl.hooks;
    const { useListener } = require('web.custom_hooks');
    const PosComponent = require('point_of_sale.PosComponent');
    const EditableTable = require('pos_restaurant.EditableTable');
    const EditBar = require('pos_restaurant.EditBar');
    const TableWidget = require('pos_restaurant.TableWidget');

    class FloorScreen extends PosComponent {
        constructor() {
            super(...arguments);
            this._setTableColor = debounce(this._setTableColor, 70);
            this._setFloorColor = debounce(this._setFloorColor, 70);
            useListener('select-table', this._onSelectTable);
            useListener('save-table', (event) => this.env.model.saveTableToServer(event.detail));
            useListener('create-table', this._onCreateTable);
            useListener('duplicate-table', this._onDuplicateTable);
            useListener('rename-table', this._renameTable);
            useListener('change-seats-num', this._changeSeatsNum);
            useListener('change-shape', this._changeShape);
            useListener('set-table-color', this._setTableColor);
            useListener('set-floor-color', this._setFloorColor);
            useListener('delete-table', this._deleteTable);
            this.floorMapRef = useRef('floor-map-ref');
        }
        patched() {
            this.floorMapRef.el.style.background = this.props.activeFloor.background_color;
        }
        mounted() {
            this.floorMapRef.el.style.background = this.props.activeFloor.background_color;
            this._tableLongpolling();
            this.tableLongpolling = setInterval(this._tableLongpolling.bind(this), 5000);
        }
        willUnmount() {
            this.env.model.data.uiState.FloorScreen.isEditMode = false;
            this.env.model.data.uiState.FloorScreen.selectedTableId = false;
            clearInterval(this.tableLongpolling);
        }
        getActiveTables() {
            if (!this.props.activeFloor) return [];
            return this.props.activeFloor.table_ids.map((id) => this.env.model.getRecord('restaurant.table', id));
        }
        _onCreateTable() {
            this.env.model.actionHandler({ name: 'actionCreateTable', args: [this.props.activeFloor] });
        }
        _onDuplicateTable() {
            this.env.model.actionHandler({ name: 'actionDuplicateTable', args: [this.env.model.getSelectedTable()] });
        }
        async _changeSeatsNum() {
            const selectedTable = this.env.model.getSelectedTable();
            if (!selectedTable) return;
            const [confirmed, inputNumber] = await this.env.ui.askUser('NumberPopup', {
                startingValue: selectedTable.seats,
                cheap: true,
                title: this.env._t('Number of Seats ?'),
                isInputSelected: true,
            });
            if (!confirmed) return;
            const newSeatsNum = parseInt(inputNumber, 10) || selectedTable.seats;
            if (newSeatsNum !== selectedTable.seats) {
                await this.env.model.actionHandler({
                    name: 'actionUpdateTable',
                    args: [selectedTable, { seats: newSeatsNum }],
                });
            }
        }
        async _changeShape() {
            const selectedTable = this.env.model.getSelectedTable();
            if (!selectedTable) return;
            const newShape = selectedTable.shape === 'square' ? 'round' : 'square';
            await this.env.model.actionHandler({
                name: 'actionUpdateTable',
                args: [selectedTable, { shape: newShape }],
            });
        }
        async _renameTable() {
            const selectedTable = this.env.model.getSelectedTable();
            if (!selectedTable) return;
            const [confirmed, newName] = await this.env.ui.askUser('TextInputPopup', {
                startingValue: selectedTable.name,
                title: this.env._t('Table Name ?'),
            });
            if (!confirmed) return;
            if (newName !== selectedTable.name) {
                await this.env.model.actionHandler({
                    name: 'actionUpdateTable',
                    args: [selectedTable, { name: newName }],
                });
            }
        }
        async _setTableColor({ detail: color }) {
            const selectedTable = this.env.model.getSelectedTable();
            await this.env.model.actionHandler({ name: 'actionUpdateTable', args: [selectedTable, { color }] });
        }
        async _setFloorColor({ detail: color }) {
            await this.env.model.actionHandler({
                name: 'actionUpdateFloor',
                args: [this.props.activeFloor, { background_color: color }],
            });
        }
        async _deleteTable() {
            const selectedTable = this.env.model.getSelectedTable();
            if (!selectedTable) return;
            const confirmed = await this.env.ui.askUser('ConfirmPopup', {
                title: this.env._t('Are you sure ?'),
                body: this.env._t('Removing a table cannot be undone'),
            });
            if (!confirmed) return;
            await this.env.model.actionHandler({ name: 'actionDeleteTable', args: [selectedTable] });
        }
        async _onSelectTable(event) {
            if (this.env.model.data.uiState.FloorScreen.isEditMode) {
                await this.env.model.actionHandler({ name: 'actionSetFloorScreenSelectedTable', args: [event.detail] });
            } else {
                await this.env.model.actionHandler({ name: 'actionSetTable', args: [event.detail] });
            }
        }
        async _tableLongpolling() {
            if (this.env.model.data.uiState.FloorScreen.isEditMode || this.env.model.data.uiState.isIdle) {
                return;
            }
            await this.env.model.actionHandler({ name: 'actionUpdateTableOrderCounts' });
        }
    }
    FloorScreen.components = { EditableTable, EditBar, TableWidget };
    FloorScreen.template = 'pos_restaurant.FloorScreen';
    FloorScreen.hideOrderSelector = true;

    return FloorScreen;
});
