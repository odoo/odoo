/** @odoo-module */

import { ConnectionLostError } from "@web/core/network/rpc_service";
import { debounce } from "@web/core/utils/timing";
import { registry } from "@web/core/registry";

import { TextInputPopup } from "@point_of_sale/js/Popups/TextInputPopup";
import { NumberPopup } from "@point_of_sale/js/Popups/NumberPopup";
import { ConfirmPopup } from "@point_of_sale/js/Popups/ConfirmPopup";

import { EditableTable } from "./editable_table";
import { EditBar } from "./edit_bar";
import { Table } from "./table";
import { usePos } from "@point_of_sale/app/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { Component, onPatched, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";

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
            selectedFloorId: floor.id,
            selectedTableId: null,
            isEditMode: false,
            floorBackground: floor.background_color,
            floorMapScrollTop: 0,
        });
        this.floorMapRef = useRef("floor-map-ref");
        this.map = useRef("map");
        onPatched(this.onPatched);
        onMounted(this.onMounted);
        onWillUnmount(this.onWillUnmount);
    }
    onPatched() {
        this.floorMapRef.el.style.background = this.state.floorBackground;
        this.state.floorMapScrollTop = this.floorMapRef.el.getBoundingClientRect().top;
    }
    onMounted() {
        this.pos.openCashControl();
        this.floorMapRef.el.style.background = this.state.floorBackground;
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
        this.state.selectedTableId = null;
    }
    async _createTableHelper(copyTable) {
        const existingTable = this.activeFloor.tables;
        let newTable;
        if (copyTable) {
            newTable = Object.assign({}, copyTable);
            newTable.position_h += 10;
            newTable.position_v += 10;
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
        newTable.name = this._getNewTableName(newTable.name);
        delete newTable.id;
        newTable.floor_id = [this.activeFloor.id, ""];
        newTable.floor = this.activeFloor;
        await this._save(newTable);
        this.activeTables.push(newTable);
        return newTable;
    }
    _getNewTableName(name) {
        if (name) {
            const num = Number((name.match(/\d+/g) || [])[0] || 0);
            const str = name.replace(/\d+/g, "");
            const n = { num: num, str: str };
            n.num += 1;
            this._lastName = n;
        } else if (this._lastName) {
            this._lastName.num += 1;
        } else {
            this._lastName = { num: 1, str: "" };
        }
        return "" + this._lastName.str + this._lastName.num;
    }
    async _save(table) {
        const tableCopy = { ...table };
        delete tableCopy.floor;
        const tableId = await this.orm.call("restaurant.table", "create_from_ui", [tableCopy]);
        table.id = tableId;
        this.env.pos.tables_by_id[tableId] = table;
    }
    async _tableLongpolling() {
        if (this.state.isEditMode) {
            return;
        }
        const result = await this.orm.call("pos.config", "get_tables_order_count", [
            this.env.pos.config.id,
        ]);
        result.forEach((table) => {
            const table_obj = this.env.pos.tables_by_id[table.id];
            const unsynced_orders = this.env.pos.getTableOrders(table_obj.id).filter(
                (o) =>
                    o.server_id === undefined &&
                    (o.orderlines.length !== 0 || o.paymentlines.length !== 0) &&
                    // do not count the orders that are already finalized
                    !o.finalized
            ).length;
            table_obj.order_count = table.orders + unsynced_orders;
        });
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
        this.state.isEditMode = false;
        this.state.selectedTableId = null;
    }
    toggleEditMode() {
        this.state.isEditMode = !this.state.isEditMode;
        this.state.selectedTableId = null;
    }
    async onSelectTable(table) {
        if (this.state.isEditMode) {
            this.state.selectedTableId = table.id;
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
    async createTable() {
        const newTable = await this._createTableHelper();
        if (newTable) {
            this.state.selectedTableId = newTable.id;
        }
    }
    async duplicateTable() {
        if (!this.selectedTable) {
            return;
        }
        const newTable = await this._createTableHelper(this.selectedTable);
        if (newTable) {
            this.state.selectedTableId = newTable.id;
        }
    }
    async renameTable() {
        const selectedTable = this.selectedTable;
        if (!selectedTable) {
            return;
        }
        const { confirmed, payload: newName } = await this.popup.add(TextInputPopup, {
            startingValue: selectedTable.name,
            title: this.env._t("Table Name ?"),
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
        const selectedTable = this.selectedTable;
        if (!selectedTable) {
            return;
        }
        const { confirmed, payload: inputNumber } = await this.popup.add(NumberPopup, {
            startingValue: selectedTable.seats,
            cheap: true,
            title: this.env._t("Number of Seats ?"),
            isInputSelected: true,
        });
        if (!confirmed) {
            return;
        }
        const newSeatsNum = parseInt(inputNumber, 10) || selectedTable.seats;
        if (newSeatsNum !== selectedTable.seats) {
            selectedTable.seats = newSeatsNum;
            await this._save(selectedTable);
        }
    }
    async changeShape() {
        if (!this.selectedTable) {
            return;
        }
        this.selectedTable.shape = this.selectedTable.shape === "square" ? "round" : "square";
        this.render();
        await this._save(this.selectedTable);
    }
    async setTableColor(color) {
        this.selectedTable.color = color;
        this.render();
        await this._save(this.selectedTable);
    }
    async setFloorColor(color) {
        this.state.floorBackground = color;
        this.activeFloor.background_color = color;
        await this.orm.write("restaurant.floor", [this.activeFloor.id], {
            background_color: color,
        });
    }
    async deleteTable() {
        if (!this.selectedTable) {
            return;
        }
        const { confirmed } = await this.popup.add(ConfirmPopup, {
            title: this.env._t("Are you sure ?"),
            body: this.env._t("Removing a table cannot be undone"),
        });
        if (!confirmed) {
            return;
        }
        const originalSelectedTableId = this.state.selectedTableId;
        this.env.pos.tables_by_id[originalSelectedTableId].active = false;
        await this.orm.call("restaurant.table", "create_from_ui", [
            { active: false, id: originalSelectedTableId },
        ]);
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
        delete this.env.pos.tables_by_id[originalSelectedTableId];
        this.env.pos.TICKET_SCREEN_STATE.syncedOrders.cache = {};
    }
}

registry.category("pos_screens").add("FloorScreen", FloorScreen);
