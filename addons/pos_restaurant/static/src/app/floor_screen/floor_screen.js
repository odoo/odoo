/** @odoo-module */

import { ConnectionLostError } from "@web/core/network/rpc_service";
import { debounce, useDebounced } from "@web/core/utils/timing";
import { registry } from "@web/core/registry";

import { TextInputPopup } from "@point_of_sale/js/Popups/TextInputPopup";
import { NumberPopup } from "@point_of_sale/js/Popups/NumberPopup";
import { ConfirmPopup } from "@point_of_sale/js/Popups/ConfirmPopup";
import { ErrorPopup } from "@point_of_sale/js/Popups/ErrorPopup";

import { EditableTable } from "./editable_table";
import { Table } from "./table";
import { usePos } from "@point_of_sale/app/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { Component, onPatched, onMounted, useRef, useState } from "@odoo/owl";
import { sprintf } from "@web/core/utils/strings";

export class FloorScreen extends Component {
    static components = { EditableTable, Table };
    static template = "pos_restaurant.FloorScreen";
    static props = { isShown: Boolean, floor: { type: true, optional: true } };
    static storeOnOrder = false;
    static colors = [
        { tableColor: "#FFFFFF", floorColor: "#FFFFFF", label: "White" },
        { tableColor: "#EB6D6D", floorColor: "#F49595", label: "Red" },
        { tableColor: "#35D374", floorColor: "#82E9AB", label: "Green" },
        { tableColor: "#6C6DEC", floorColor: "#8889F2", label: "Blue" },
        { tableColor: "#EBBF6D", floorColor: "#FFD688", label: "Orange" },
        { tableColor: "#EBEC6D", floorColor: "#FEFF9A", label: "Yellow" },
        { tableColor: "#AC6DAD", floorColor: "#D1ABD2", label: "Purple" },
        { tableColor: "#6C6D6D", floorColor: "#4B4B4B", label: "Grey" },
        { tableColor: "#ACADAD", floorColor: "#D2D2D2", label: "Light grey" },
        { tableColor: "#4ED2BE", floorColor: "#7FDDEC", label: "Turquoise" },
    ];

    setup() {
        super.setup();
        this.pos = usePos();
        this.popup = useService("popup");
        this.orm = useService("orm");
        const floor = this.props.floor || this.pos.globalState.floors[0];
        this.state = useState({
            selectedFloorId: floor ? floor.id : null,
            selectedTableIds: [],
            floorBackground: floor ? floor.background_color : null,
            floorMapScrollTop: 0,
            isColorPicker: false,
        });
        const ui = useState(useService("ui"));
        this.pos.globalState.floorPlanStyle ||= ui.isSmall ? "kanban" : "default";
        this.floorMapRef = useRef("floor-map-ref");
        this.map = useRef("map");
        onPatched(this.onPatched);
        onMounted(this.onMounted);
        this.debouncedUpdateTables = useDebounced((tableIds, tableValues) => {
            this.orm.call("restaurant.table", "multi_write", [tableIds, tableValues], {});
        }, 200);
    }
    onPatched() {
        this.state.floorMapScrollTop = this.floorMapRef.el.getBoundingClientRect().top;
        const floorIds = Object.keys(this.pos.globalState.floors_by_id);
        if (floorIds.length && !floorIds.includes(this.state.selectedFloorId.toString())) {
            this.selectFloor(this.pos.globalState.floors[0]);
        }
    }
    onMounted() {
        this.pos.openCashControl();
        this.state.floorMapScrollTop = this.floorMapRef.el.getBoundingClientRect().top;
    }
    _computePinchHypo(ev, callbackFunction) {
        const touches = ev.touches;
        // If two pointers are down, check for pinch gestures
        if (touches.length === 2) {
            const deltaX = touches[0].pageX - touches[1].pageX;
            const deltaY = touches[0].pageY - touches[1].pageY;
            callbackFunction(Math.hypot(deltaX, deltaY));
        }
    }
    _onPinchStart(ev) {
        ev.currentTarget.style.setProperty("touch-action", "none");
        this._computePinchHypo(ev, this.startPinch.bind(this));
    }
    _onPinchEnd(ev) {
        ev.currentTarget.style.removeProperty("touch-action");
    }
    _onPinchMove(ev) {
        debounce(this._computePinchHypo, 10, true)(ev, this.movePinch.bind(this));
    }
    _onDeselectTable() {
        this.state.selectedTableIds = [];
    }
    async _createTableHelper(copyTable, duplicateFloor = false) {
        const existingTable = this.activeFloor.tables;
        let newTable;
        if (copyTable) {
            newTable = Object.assign({}, copyTable);
            if (!duplicateFloor) {
                newTable.position_h += 10;
                newTable.position_v += 10;
            }
            delete newTable.id;
            newTable.order_count = 0;
        } else {
            let posV = 0;
            let posH = 10;
            const referenceScreenWidth = 1180;
            const spaceBetweenTable = 15 * (screen.width / referenceScreenWidth);
            const h_min = spaceBetweenTable;
            const h_max = screen.width;
            const v_max = screen.height;
            let potentialWidth = 100 * (h_max / referenceScreenWidth);
            if (potentialWidth > 130) {
                potentialWidth = 130;
            } else if (potentialWidth < 75) {
                potentialWidth = 75;
            }
            const heightTable = potentialWidth;
            const widthTable = potentialWidth;
            const positionTable = [];

            existingTable.forEach((table) => {
                positionTable.push([
                    table.position_v,
                    table.position_v + table.height,
                    table.position_h,
                    table.position_h + table.width,
                ]);
            });

            positionTable.sort((tableA, tableB) => {
                if (tableA[0] < tableB[0]) {
                    return -1;
                } else if (tableA[0] > tableB[0]) {
                    return 1;
                } else if (tableA[2] < tableB[2]) {
                    return -1;
                } else {
                    return 1;
                }
            });

            let actualHeight = 100;
            let impossible = true;

            while (actualHeight <= v_max - heightTable - spaceBetweenTable && impossible) {
                const tableIntervals = [
                    [h_min, h_min, v_max],
                    [h_max, h_max, v_max],
                ];
                for (let i = 0; i < positionTable.length; i++) {
                    if (positionTable[i][0] >= actualHeight + heightTable + spaceBetweenTable) {
                        continue;
                    } else if (positionTable[i][1] + spaceBetweenTable <= actualHeight) {
                        continue;
                    } else {
                        tableIntervals.push([
                            positionTable[i][2],
                            positionTable[i][3],
                            positionTable[i][1],
                        ]);
                    }
                }

                tableIntervals.sort((a, b) => {
                    if (a[0] < b[0]) {
                        return -1;
                    } else if (a[0] > b[0]) {
                        return 1;
                    } else if (a[1] < b[1]) {
                        return -1;
                    } else {
                        return 1;
                    }
                });

                let nextHeight = v_max;
                for (let i = 0; i < tableIntervals.length - 1; i++) {
                    if (tableIntervals[i][2] < nextHeight) {
                        nextHeight = tableIntervals[i][2];
                    }

                    if (
                        tableIntervals[i + 1][0] - tableIntervals[i][1] >
                        widthTable + spaceBetweenTable
                    ) {
                        impossible = false;
                        posV = actualHeight;
                        posH = tableIntervals[i][1] + spaceBetweenTable;
                        break;
                    }
                }
                actualHeight = nextHeight + spaceBetweenTable;
            }

            if (impossible) {
                posV = positionTable[0][0] + 10;
                posH = positionTable[0][2] + 10;
            }

            newTable = {
                position_v: posV,
                position_h: posH,
                width: widthTable,
                height: heightTable,
                shape: "square",
                seats: 1,
                color: "rgb(53, 211, 116)",
            };
        }
        if (!duplicateFloor) {
            newTable.name = this._getNewTableName();
        }
        newTable.floor_id = this.activeFloor.id;
        newTable.floor = this.activeFloor;
        const tableId = await this.orm.create("restaurant.table", [
            this.formatTableObjectForServer(newTable),
        ]);
        if (tableId.length) {
            newTable.id = tableId[0];
            newTable.active = true;
            this.pos.globalState.floors_by_id[this.state.selectedFloorId].tables.push(newTable);
            this.pos.globalState.floors_by_id[this.state.selectedFloorId].table_ids.push(
                tableId[0]
            );
        }

        return newTable;
    }
    _getNewTableName() {
        let firstNum = 1;
        const tablesNameNumber = this.activeTables
            .map((table) => +table.name)
            .sort(function (a, b) {
                return a - b;
            });

        for (let i = 0; i < tablesNameNumber.length; i++) {
            if (tablesNameNumber[i] == firstNum) {
                firstNum += 1;
            } else {
                break;
            }
        }
        return firstNum.toString();
    }
    formatTableObjectForServer(table) {
        const tableServerKeys = [
            "position_v",
            "position_h",
            "width",
            "height",
            "shape",
            "seats",
            "name",
            "floor_id",
            "color",
            "active",
        ];

        const tableFormatted = {};
        for (const key in table) {
            if (tableServerKeys.includes(key)) {
                tableFormatted[key] = table[key];
            }
        }
        return tableFormatted;
    }
    async updateTables(tables) {
        const tableIds = [];
        const tableValues = tables.reduce((acc, table) => {
            tableIds.push(table.id);
            acc[table.id] = this.formatTableObjectForServer(table);
            return acc;
        }, {});

        for (const idx in tableValues) {
            const selectedTable = this.selectedTables.find((table) => table.id == idx);
            for (const key of Object.keys(tableValues[idx])) {
                if (tableValues[idx][key] !== selectedTable[key]) {
                    selectedTable[key] = tableValues[idx][key];
                }
            }
        }

        if (tableIds.length) {
            this.debouncedUpdateTables(tableIds, tableValues);
        }
    }
    async _renameFloor(floorId, newName) {
        await this.orm.call("restaurant.floor", "rename_floor", [floorId, newName]);
    }
    get activeFloor() {
        return this.state.selectedFloorId
            ? this.pos.globalState.floors_by_id[this.state.selectedFloorId]
            : null;
    }
    get activeTables() {
        return this.activeFloor ? this.activeFloor.tables.filter((t) => t.active) : null;
    }
    get isFloorEmpty() {
        return this.activeTables ? this.activeTables.length === 0 : true;
    }
    get selectedTables() {
        return this.state.selectedTableIds.map((id) => this.pos.globalState.getTableById(id));
    }
    get nbrFloors() {
        return this.pos.globalState.floors.length;
    }
    movePinch(hypot) {
        const delta = hypot / this.scalehypot;
        const value = this.initalScale * delta;
        this.setScale(value);
    }
    startPinch(hypot) {
        this.scalehypot = hypot;
        this.initalScale = this.getScale();
    }
    getScale() {
        const scale = this.map.el.style.getPropertyValue("--scale");
        const parsedScaleValue = parseFloat(scale);
        return isNaN(parsedScaleValue) ? 1 : parsedScaleValue;
    }
    setScale(value) {
        // a scale can't be a negative number
        if (value > 0) {
            this.map.el.style.setProperty("--scale", value);
        }
    }
    selectFloor(floor) {
        this.state.selectedFloorId = floor.id;
        this.state.floorBackground = this.activeFloor.background_color;
        this.state.selectedTableIds = [];
    }
    async onSelectTable(table, ev) {
        const { globalState } = this.pos;
        if (globalState.isEditMode) {
            if (ev.ctrlKey || ev.metaKey) {
                this.state.selectedTableIds.push(table.id);
            } else {
                this.state.selectedTableIds = [table.id];
            }
        } else {
            if (globalState.orderToTransfer) {
                await globalState.transferTable(table);
            } else {
                try {
                    await globalState.setTable(table);
                } catch (e) {
                    if (!(e instanceof ConnectionLostError)) {
                        throw e;
                    }
                    // Reject error in a separate stack to display the offline popup, but continue the flow
                    Promise.reject(e);
                }
            }
            const order = globalState.get_order();
            this.pos.showScreen(order.get_screen_data().name);
        }
    }
    async addFloor() {
        const { confirmed, payload: newName } = await this.popup.add(TextInputPopup, {
            title: this.env._t("Floor Name"),
        });
        if (!confirmed) {
            return;
        }
        const { globalState } = this.pos;
        const floor = await this.orm.call("restaurant.floor", "create_from_ui", [
            newName,
            "#ACADAD",
            globalState.config.id,
        ]);
        globalState.floors_by_id[floor.id] = floor;
        globalState.floors.push(floor);
        this.selectFloor(floor);
        globalState.isEditMode = true;
    }
    async createTable() {
        const newTable = await this._createTableHelper();
        if (newTable) {
            this.state.selectedTableIds = [newTable.id];
        }
    }
    async duplicateTableOrFloor() {
        if (this.selectedTables.length == 0) {
            const { globalState } = this.pos;
            const floor = this.activeFloor;
            const tables = this.activeFloor.tables;
            const newFloorName = floor.name + " (copy)";
            const newFloor = await this.orm.call("restaurant.floor", "create_from_ui", [
                newFloorName,
                floor.background_color,
                globalState.config.id,
            ]);
            globalState.floors_by_id[newFloor.id] = newFloor;
            globalState.floors.push(newFloor);
            this.selectFloor(newFloor);
            for (const table of tables) {
                await this._createTableHelper(table, true);
            }
            return;
        }
        const selectedTables = this.selectedTables;
        this._onDeselectTable();

        for (const table of selectedTables) {
            const newTable = await this._createTableHelper(table);
            if (newTable) {
                this.state.selectedTableIds.push(newTable.id);
            }
        }
    }
    async renameFloor() {
        const selectedFloor = this.activeFloor;
        const { confirmed, payload: newName } = await this.popup.add(TextInputPopup, {
            startingValue: selectedFloor.name,
            title: this.env._t("Floor Name ?"),
        });
        if (!confirmed) {
            return;
        }
        if (newName !== selectedFloor.name) {
            selectedFloor.name = newName;
            await this._renameFloor(selectedFloor.id, newName);
        }
        return;
    }
    async renameTable() {
        const selectedTables = this.selectedTables;
        const selectedTable = selectedTables[0];

        if (selectedTables.length !== 1) {
            return;
        }

        const { confirmed, payload: newName } = await this.popup.add(TextInputPopup, {
            startingValue: selectedTable.name,
            title: this.env._t("Table Name?"),
        });

        if (confirmed) {
            this.updateTables([
                {
                    id: selectedTable.id,
                    name: newName,
                },
            ]);
        }
    }
    async changeSeatsNum() {
        if (this.selectedTables.length == 0) {
            return;
        }

        const { confirmed, payload: inputNumber } = await this.popup.add(NumberPopup, {
            startingValue: 0,
            cheap: true,
            title: this.env._t("Number of Seats?"),
            isInputSelected: true,
        });

        const updatedTables = this.selectedTables.map((table) => {
            return {
                id: table.id,
                seats: parseInt(inputNumber),
            };
        });

        if (confirmed) {
            this.updateTables(updatedTables);
        }
    }
    async changeShape() {
        const shape = this.selectedTables.find((table) => table.shape === "square")
            ? "round"
            : "square";

        const updatedTables = this.selectedTables.map((table) => {
            return {
                id: table.id,
                shape: shape,
            };
        });

        this.updateTables(updatedTables);
    }
    async setTableColor(color) {
        const updatedTables = this.selectedTables.map((table) => {
            return {
                id: table.id,
                color: color,
            };
        });

        this.updateTables(updatedTables);
    }
    async setFloorColor(color) {
        this.state.floorBackground = color;
        this.activeFloor.background_color = color;
        await this.orm.write("restaurant.floor", [this.activeFloor.id], {
            background_color: color,
        });
        this.state.isColorPicker = false;
    }
    async deleteTable() {
        const updatedTables = [];
        const { confirmed } = await this.popup.add(ConfirmPopup, {
            title: this.env._t("Are you sure?"),
            body: this.env._t("Removing a table cannot be undone"),
        });

        const response = await this.orm.call("restaurant.table", "are_orders_still_in_draft", [
            this.selectedTableIds,
        ]);

        if (response) {
            await this.popup.add(ErrorPopup, {
                title: this.env._t("Delete Error"),
                body: this.env._t(
                    "You cannot delete a table with orders still in draft for this table."
                ),
            });
            return;
        }

        for (const table of this.selectedTables) {
            for (const order of this.pos.globalState.get_order_list()) {
                if (order.tableId == table.id) {
                    this.pos.globalState.removeOrder(order, false);
                }
            }

            updatedTables.push({
                id: table.id,
                active: false,
            });
        }

        if (confirmed) {
            this.updateTables(updatedTables);
        }
    }
    async deleteFloor() {
        const { globalState } = this.pos;
        const { confirmed } = await this.popup.add(ConfirmPopup, {
            title: `Removing floor ${this.activeFloor.name}`,
            body: sprintf(
                this.env._t("Removing a floor cannot be undone. Do you still wanna remove %s?"),
                this.activeFloor.name
            ),
        });

        if (confirmed) {
            await this.orm.call("restaurant.floor", "deactivate_floor", [
                this.activeFloor.id,
                globalState.pos_session.id,
            ]);
        }

        return;
    }
}

registry.category("pos_screens").add("FloorScreen", FloorScreen);
