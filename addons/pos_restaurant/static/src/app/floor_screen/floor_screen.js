/** @odoo-module */

import { ConnectionLostError } from "@web/core/network/rpc_service";
import { debounce } from "@web/core/utils/timing";
import { registry } from "@web/core/registry";

import { TextInputPopup } from "@point_of_sale/js/Popups/TextInputPopup";
import { NumberPopup } from "@point_of_sale/js/Popups/NumberPopup";
import { ConfirmPopup } from "@point_of_sale/js/Popups/ConfirmPopup";
import { ErrorPopup } from "@point_of_sale/js/Popups/ErrorPopup";

import { EditableTable } from "./editable_table";
import { EditBar } from "./edit_bar";
import { Table } from "./table";
import { usePos } from "@point_of_sale/app/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { Component, onPatched, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";
import { sprintf } from "@web/core/utils/strings";

export class FloorScreen extends Component {
    static components = { EditableTable, EditBar, Table };
    static template = "pos_restaurant.FloorScreen";
    static props = { isShown: Boolean, floor: { type: true, optional: true } };
    static storeOnOrder = false;

    setup() {
        super.setup();
        this.pos = usePos();
        this.popup = useService("popup");
        this.orm = useService("orm");
        const floor = this.props.floor ? this.props.floor : this.env.pos.floors[0];
        this.state = useState({
            selectedFloorId: floor ? floor.id : null,
            selectedTableIds: [],
            floorBackground: floor ? floor.background_color : null,
            floorMapScrollTop: 0,
            isColorPicker: false,
        });
        if (!this.env.pos.floorPlanStyle) {
            if (this.env.isMobile) {
                this.env.pos.floorPlanStyle = "kanban";
            } else {
                this.env.pos.floorPlanStyle = "default";
            }
        }
        this.floorMapRef = useRef("floor-map-ref");
        this.addFloorRef = useRef("add-floor-ref");
        this.map = useRef("map");
        onPatched(this.onPatched);
        onMounted(this.onMounted);
        onWillUnmount(this.onWillUnmount);
    }
    onPatched() {
        this.floorMapRef.el.style.background = this.state.floorBackground;
        this.addFloorRef.el.style.background = this.state.floorBackground;
        if (!this.env.pos.isEditMode && this.env.pos.floors.length > 0) {
            this.addFloorRef.el.style.display = "none";
        } else {
            this.addFloorRef.el.style.display = "initial";
        }
        this.state.floorMapScrollTop = this.floorMapRef.el.getBoundingClientRect().top;
    }
    onMounted() {
        this.pos.openCashControl();
        this.floorMapRef.el.style.background = this.state.floorBackground;
        this.addFloorRef.el.style.background = this.state.floorBackground;
        if (!this.env.pos.isEditMode && this.env.pos.floors.length > 0) {
            this.addFloorRef.el.style.display = "none";
        } else {
            this.addFloorRef.el.style.display = "initial";
        }
        this.state.floorMapScrollTop = this.floorMapRef.el.getBoundingClientRect().top;
        // call _tableLongpolling once then set interval of 5sec.
        this._tableLongpolling();
        this.tableLongpolling = setInterval(this._tableLongpolling.bind(this), 5000);
    }
    onWillUnmount() {
        clearInterval(this.tableLongpolling);
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
        newTable.floor_id = [this.activeFloor.id, ""];
        newTable.floor = this.activeFloor;
        await this._save(newTable);
        this.activeTables.push(newTable);
        this.activeFloor.table_ids.push(newTable.id);
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
    async _save(table) {
        const tableCopy = { ...table };
        delete tableCopy.floor;
        const tableId = await this.orm.call("restaurant.table", "create_from_ui", [tableCopy]);
        table.id = tableId;
        this.env.pos.tables_by_id[tableId] = table;
    }
    async _renameFloor(floorId, newName) {
        await this.orm.call("restaurant.floor", "rename_floor", [floorId, newName]);
    }
    async _tableLongpolling() {
        if (this.env.pos.isEditMode) {
            return;
        }
        const result = await this.orm.call("pos.config", "get_tables_order_count", [
            this.env.pos.config.id,
        ]);
        for (const table of result) {
            if (!(table.id in this.env.pos.tables_by_id)) {
                //We enter this condition if, after loading our PoS, a table is deleted on a PoS and not on another.
                //This will lead in receiving information on orders from a table that we do not have.
                //If we do not have a table in the PoS but still receive information about it, we reload the tables
                //from the server.
                const result = await this.orm.call("pos.session", "get_pos_ui_restaurant_floor", [
                    [odoo.pos_session_id],
                ]);
                if (this.env.pos.config.is_table_management) {
                    this.env.pos.floors = result;
                    this.env.pos.loadRestaurantFloor();
                }
            }
            const table_obj = this.env.pos.tables_by_id[table.id];
            const unsynced_orders = this.env.pos.getTableOrders(table_obj.id).filter(
                (o) =>
                    o.server_id === undefined &&
                    (o.orderlines.length !== 0 || o.paymentlines.length !== 0) &&
                    // do not count the orders that are already finalized
                    !o.finalized
            ).length;
            table_obj.order_count = table.orders + unsynced_orders;
        }
    }
    get activeFloor() {
        return this.state.selectedFloorId
            ? this.env.pos.floors_by_id[this.state.selectedFloorId]
            : null;
    }
    get activeTables() {
        return this.activeFloor ? this.activeFloor.tables : null;
    }
    get isFloorEmpty() {
        return this.activeTables ? this.activeTables.length === 0 : true;
    }
    get selectedTables() {
        const tables = [];
        this.state.selectedTableIds.forEach((id) => {
            tables.push(this.env.pos.tables_by_id[id]);
        });
        return tables;
    }
    get nbrFloors() {
        return this.env.pos.floors.length;
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
    toggleEditMode() {
        this.env.pos.toggleEditMode();
        if (!this.env.pos.isEditMode && this.env.pos.floors.length > 0) {
            this.addFloorRef.el.style.display = "none";
        } else {
            this.addFloorRef.el.style.display = "initial";
        }
        this.state.selectedTableIds = [];
    }
    async onSelectTable(table, ev) {
        if (this.env.pos.isEditMode) {
            if (ev.ctrlKey || ev.metaKey) {
                this.state.selectedTableIds.push(table.id);
            } else {
                this.state.selectedTableIds = [];
                this.state.selectedTableIds.push(table.id);
            }
        } else {
            if (this.env.pos.orderToTransfer) {
                await this.env.pos.transferTable(table);
            } else {
                try {
                    await this.env.pos.setTable(table);
                } catch (e) {
                    if (!(e.message instanceof ConnectionLostError)) {
                        throw e;
                    }
                    // Reject error in a separate stack to display the offline popup, but continue the flow
                    Promise.reject(e);
                }
            }
            const order = this.env.pos.get_order();
            this.pos.showScreen(order.get_screen_data().name);
        }
    }
    async onSaveTable(table) {
        await this._save(table);
    }
    async addFloor() {
        const { confirmed, payload: newName } = await this.popup.add(TextInputPopup, {
            title: this.env._t("Floor Name"),
        });
        if (!confirmed) {
            return;
        }
        const floor = await this.orm.call("restaurant.floor", "create_from_ui", [
            newName,
            "#ACADAD",
            this.env.pos.config.id,
        ]);
        this.env.pos.floors_by_id[floor.id] = floor;
        this.env.pos.floors.push(floor);
        this.selectFloor(floor);
        this.env.pos.isEditMode = true;
    }
    async createTable() {
        const newTable = await this._createTableHelper();
        if (newTable) {
            this.state.selectedTableIds = [];
            this.state.selectedTableIds.push(newTable.id);
        }
    }
    async duplicateTableOrFloor() {
        if (this.selectedTables.length == 0) {
            const floor = this.activeFloor;
            const tables = this.activeFloor.tables;
            const newFloorName = floor.name + " (copy)";
            const newFloor = await this.orm.call("restaurant.floor", "create_from_ui", [
                newFloorName,
                floor.background_color,
                this.env.pos.config.id,
            ]);
            this.env.pos.floors_by_id[newFloor.id] = newFloor;
            this.env.pos.floors.push(newFloor);
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
    async renameTable() {
        const selectedTables = this.selectedTables;
        const selectedFloor = this.activeFloor;
        if (selectedTables.length > 1) {
            return;
        }
        if (selectedTables.length == 0) {
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
        const selectedTable = selectedTables[0];
        const { confirmed, payload: newName } = await this.popup.add(TextInputPopup, {
            startingValue: selectedTable.name,
            title: this.env._t("Table Name?"),
        });
        if (!confirmed) {
            return;
        }
        if (newName !== selectedTable.name) {
            selectedTable.name = newName;
            await this._save(selectedTable);
        }
    }
    async changeSeatsNum() {
        const selectedTables = this.selectedTables;
        if (selectedTables.length == 0) {
            return;
        }
        const { confirmed, payload: inputNumber } = await this.popup.add(NumberPopup, {
            startingValue: 0,
            cheap: true,
            title: this.env._t("Number of Seats?"),
            isInputSelected: true,
        });
        if (!confirmed) {
            return;
        }
        const newSeatsNum = parseInt(inputNumber, 10);
        selectedTables.forEach(async (selectedTable) => {
            if (newSeatsNum !== selectedTable.seats) {
                selectedTable.seats = newSeatsNum;
                await this._save(selectedTable);
            }
        });
    }
    async changeToCircle() {
        await this.changeShape("round");
    }
    async changeToSquare() {
        await this.changeShape("square");
    }
    async changeShape(form) {
        if (this.selectedTables.length == 0) {
            return;
        }
        this.selectedTables.forEach(async (selectedTable) => {
            selectedTable.shape = form;
            await this._save(selectedTable);
        });
        this.render();
    }
    async setTableColor(color) {
        const selectedTables = this.selectedTables;
        selectedTables.forEach(async (selectedTable) => {
            selectedTable.color = color;
            await this._save(selectedTable);
        });
        this.render();
        this.state.isColorPicker = false;
    }
    async setFloorColor(color) {
        this.state.floorBackground = color;
        this.activeFloor.background_color = color;
        await this.orm.write("restaurant.floor", [this.activeFloor.id], {
            background_color: color,
        });
        this.state.isColorPicker = false;
    }
    toggleColorPicker() {
        this.state.isColorPicker = !this.state.isColorPicker;
    }
    async deleteFloorOrTable() {
        if (this.selectedTables.length == 0) {
            const { confirmed } = await this.popup.add(ConfirmPopup, {
                title: `Removing floor ${this.activeFloor.name}`,
                body: sprintf(
                    this.env._t("Removing a floor cannot be undone. Do you still wanna remove %s?"),
                    this.activeFloor.name
                ),
            });
            if (!confirmed) {
                return;
            }
            const originalSelectedFloorId = this.activeFloor.id;
            await this.orm.call("restaurant.floor", "deactivate_floor", [
                originalSelectedFloorId,
                this.env.pos.pos_session.id,
            ]);
            const floor = this.env.pos.floors_by_id[originalSelectedFloorId];
            const orderList = [...this.env.pos.get_order_list()];
            for (const order of orderList) {
                if (floor.table_ids.includes(order.tableId)) {
                    this.env.pos.removeOrder(order, false);
                }
            }
            floor.table_ids.forEach((tableId) => {
                delete this.env.pos.tables_by_id[tableId];
            });
            delete this.env.pos.floors_by_id[originalSelectedFloorId];
            this.env.pos.floors = this.env.pos.floors.filter(
                (floor) => floor.id != originalSelectedFloorId
            );
            this.env.pos.TICKET_SCREEN_STATE.syncedOrders.cache = {};
            if (this.env.pos.floors.length > 0) {
                this.selectFloor(this.env.pos.floors[0]);
            } else {
                this.env.pos.isEditMode = false;
                this.env.pos.floorPlanStyle = "default";
                this.state.floorBackground = null;
            }
            return;
        }
        const { confirmed } = await this.popup.add(ConfirmPopup, {
            title: this.env._t("Are you sure?"),
            body: this.env._t("Removing a table cannot be undone"),
        });
        if (!confirmed) {
            return;
        }
        const originalSelectedTableIds = [...this.state.selectedTableIds];
        originalSelectedTableIds.forEach(async (id) => {
            const response = await this.orm.call("restaurant.table", "are_orders_still_in_draft", [
                id,
            ]);
            if (!response) {
                //remove order not send to server
                for (const order of this.env.pos.get_order_list()) {
                    if (order.tableId == id) {
                        this.env.pos.removeOrder(order, false);
                    }
                }
                this.env.pos.tables_by_id[id].active = false;
                await this.orm.call("restaurant.table", "create_from_ui", [
                    { active: false, id: id },
                ]);
                this.activeFloor.tables = this.activeTables.filter((table) => table.id !== id);
                delete this.env.pos.tables_by_id[id];
            } else {
                await this.popup.add(ErrorPopup, {
                    title: this.env._t("Delete Error"),
                    body: this.env._t(
                        "You cannot delete a table with orders still in draft for this table."
                    ),
                });
            }
        });
        // Value of an object can change inside async function call.
        //   Which means that in this code block, the value of `state.selectedTableId`
        //   before the await call can be different after the finishing the await call.
        // Since we wanted to disable the selected table after deletion, we should be
        //   setting the selectedTableId to null. However, we only do this if nothing
        //   else is selected during the rpc call.
        const equalsCheck = (a, b) => {
            return JSON.stringify(a) === JSON.stringify(b);
        };
        if (equalsCheck(this.state.selectedTableIds, originalSelectedTableIds)) {
            this.state.selectedTableIds = [];
        }
        this.env.pos.TICKET_SCREEN_STATE.syncedOrders.cache = {};
    }
}

registry.category("pos_screens").add("FloorScreen", FloorScreen);
