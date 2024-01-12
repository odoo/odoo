/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";
import { ConnectionLostError } from "@web/core/network/rpc";
import { debounce } from "@web/core/utils/timing";
import { registry } from "@web/core/registry";

import { TextInputPopup } from "@point_of_sale/app/utils/input_popups/text_input_popup";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Table } from "@pos_restaurant/app/floor_screen/table";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted, useRef, useState, onWillStart } from "@odoo/owl";
import { ask } from "@point_of_sale/app/store/make_awaitable_dialog";
import { unique } from "@web/core/utils/arrays";

export class FloorScreen extends Component {
    static components = { Table };
    static template = "pos_restaurant.FloorScreen";
    static props = { floor: { type: true, optional: true } };
    static storeOnOrder = false;

    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
        const floor = this.pos.currentFloor;
        this.state = useState({
            selectedFloorId: floor ? floor.id : null,
            selectedTableIds: this.pos.orderToTransfer ? [this.pos.orderToTransfer.tableId] : [],
            isColorPicker: false,
        });
        this.floorMapRef = useRef("floor-map-ref");
        const ui = useState(useService("ui"));
        const mode = localStorage.getItem("floorPlanStyle");
        this.pos.floorPlanStyle = ui.isSmall || mode == "kanban" ? "kanban" : "default";
        this.map = useRef("map");
        onMounted(() => this.pos.openCashControl());
        onWillStart(this.onWillStart);
    }
    async onWillStart() {
        const table = this.pos.selectedTable;
        if (table) {
            const orders = this.pos.get_order_list();
            const tableOrders = orders.filter(
                (order) => order.tableId === table.id && !order.finalized
            );
            const qtyChange = tableOrders.reduce(
                (acc, order) => {
                    const quantityChange = order.getOrderChanges();
                    const quantitySkipped = order.getOrderChanges(true);
                    acc.changed += quantityChange.count;
                    acc.skipped += quantitySkipped.count;
                    return acc;
                },
                { changed: 0, skipped: 0 }
            );

            this.pos.tableNotifications[table.id] = {
                changes_count: qtyChange.changed,
                skip_changes: qtyChange.skipped,
            };
        }
        await this.pos.unsetTable();
    }
    onClickFloorMap() {
        this.state.selectedTableIds = [];
        this.state.isColorPicker = false;
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
    async _createTableHelper(copyTable, duplicateFloor = false) {
        const existingTable = this.activeFloor.table_ids;
        let newTableData;
        if (copyTable) {
            newTableData = copyTable.serialize(true);
            if (!duplicateFloor) {
                newTableData.position_h += 10;
                newTableData.position_v += 10;
            }
            delete newTableData.id;
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

            newTableData = {
                position_v: posV,
                position_h: posH,
                width: widthTable,
                height: heightTable,
                shape: "square",
                seats: 2,
                color: "rgb(53, 211, 116)",
                floor_id: this.activeFloor.id,
            };
        }
        if (!duplicateFloor) {
            newTableData.name = this._getNewTableName();
        }
        return (await this.pos.data.create("restaurant.table", [newTableData]))[0];
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
    get activeFloor() {
        return this.state.selectedFloorId
            ? this.pos.models["restaurant.floor"].get(this.state.selectedFloorId)
            : null;
    }
    get activeTables() {
        return this.activeFloor ? this.activeFloor.table_ids : null;
    }
    get selectedTables() {
        return this.state.selectedTableIds.map((id) => this.pos.models["restaurant.table"].get(id));
    }
    get nbrFloors() {
        return this.pos.models["restaurant.floor"].length;
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
        this.pos.currentFloor = floor;
        this.state.selectedFloorId = floor.id;
        this.state.selectedTableIds = [];
    }
    async onSelectTable(table, ev) {
        if (this.pos.isEditMode) {
            if (ev.ctrlKey || ev.metaKey) {
                this.state.selectedTableIds.push(table.id);
            } else {
                this.state.selectedTableIds = [];
                this.state.selectedTableIds.push(table.id);
            }
            return;
        }
        if (table.parent_id) {
            this.onSelectTable(table.parent_id, ev);
            return;
        }
        if (this.pos.orderToTransfer) {
            await this.pos.transferTable(table);
        } else {
            try {
                await this.pos.setTable(table);
            } catch (e) {
                if (!(e instanceof ConnectionLostError)) {
                    throw e;
                }
                // Reject error in a separate stack to display the offline popup, but continue the flow
                Promise.reject(e);
            }
        }
        const order = this.pos.get_order();
        if (order) {
            this.pos.showScreen(order.get_screen_data().name);
        }
    }
    closeEditMode() {
        this.pos.isEditMode = false;
        this.state.selectedTableIds = [];
    }
    async addFloor() {
        this.dialog.add(TextInputPopup, {
            title: _t("New Floor"),
            placeholder: _t("Floor name"),
            getPayload: async (newName) => {
                const floor = await this.pos.data.create(
                    "restaurant.floor",
                    [
                        {
                            name: newName,
                            background_color: "#ACADAD",
                            pos_config_ids: [this.pos.config.id],
                        },
                    ],
                    false
                );

                this.selectFloor(floor["restaurant.floor"][0]);
                this.pos.isEditMode = true;
            },
        });
    }
    async createTable() {
        const newTable = await this._createTableHelper();
        if (newTable) {
            this.state.selectedTableIds = [newTable.id];
        }
    }
    async duplicateTableOrFloor() {
        if (this.selectedTables.length == 0) {
            const floor = this.activeFloor;
            const tables = this.activeFloor.table_ids;
            const newFloorName = floor.name + " (copy)";
            const copyFloor = await this.pos.data.create("restaurant.floor", [
                {
                    name: newFloorName,
                    background_color: "#ACADAD",
                    pos_config_ids: [this.pos.config.id],
                },
            ]);

            this.selectFloor(copyFloor["restaurant.floor"][0]);
            this.pos.isEditMode = true;

            for (const table of tables) {
                await this._createTableHelper(table, true);
            }
            return;
        }
        const selectedTables = this.selectedTables;
        this.state.selectedTableIds = [];

        for (const table of selectedTables) {
            const newTable = await this._createTableHelper(table);
            if (newTable) {
                this.state.selectedTableIds.push(newTable.id);
            }
        }
    }
    async rename() {
        if (this.selectedTables.length > 1) {
            return;
        }
        this.dialog.add(
            TextInputPopup,
            this.selectedTables.length === 1
                ? {
                      startingValue: this.selectedTables[0].name,
                      title: _t("Table Name ?"),
                      getPayload: (newName) => {
                          if (newName !== this.selectedTables[0].name) {
                              this.selectedTables[0].name = newName;
                              this.pos.updateTables(this.selectedTables[0]);
                          }
                      },
                  }
                : {
                      startingValue: this.activeFloor.name,
                      title: _t("Floor Name ?"),
                      getPayload: (newName) => {
                          if (newName !== this.activeFloor.name) {
                              this.activeFloor.name = newName;
                              this.pos.data.write("restaurant.floor", [this.activeFloor.id], {
                                  name: newName,
                              });
                          }
                      },
                  }
        );
    }
    async changeSeatsNum() {
        const selectedTables = this.selectedTables;
        if (selectedTables.length == 0) {
            return;
        }
        this.dialog.add(NumberPopup, {
            startingValue: 0,
            cheap: true,
            title: _t("Number of Seats?"),
            isInputSelected: true,
            getPayload: (num) => {
                const newSeatsNum = parseInt(num, 10);
                selectedTables.forEach((selectedTable) => {
                    if (newSeatsNum !== selectedTable.seats) {
                        selectedTable.seats = newSeatsNum;
                        this.pos.updateTables(selectedTable);
                    }
                });
            },
        });
    }
    stopOrderTransfer() {
        this.pos.isTableToMerge = false;
        this.pos.orderToTransfer = null;
    }
    changeShape(form) {
        for (const table of this.selectedTables) {
            table.shape = form;
        }
        this.pos.updateTables(...this.selectedTables);
    }
    unlinkTables() {
        for (const table of this.selectedTables) {
            table.update({ parent_id: null });
        }
        this.pos.updateTables(...this.selectedTables);
    }
    linkTables() {
        const parentTable =
            this.selectedTables.filter((t) => t.parent_id)?.[0] || this.selectedTables[0];
        const childrenTables = this.selectedTables.filter((t) => t.id !== parentTable.id);
        for (const table of childrenTables) {
            table.update({ parent_id: parentTable });
        }
        this.pos.updateTables(...this.childrenTables);
    }
    isLinkingDisabled() {
        return (
            this.selectedTables.length < 2 ||
            // all the selected tables must have the same parent or no parent
            unique(this.selectedTables.filter((t) => t.parent_id).map((t) => t.parent_id)).length >
                1 ||
            // among the tables there can only be one that has children
            this.selectedTables.filter((t) => this.getChildren(t).length).length > 1
        );
    }
    setColor(color) {
        if (this.selectedTables.length > 0) {
            this.selectedTables.forEach((selectedTable) => {
                selectedTable.color = color;
            });
            this.pos.updateTables(...this.selectedTables);
        } else {
            this.activeFloor.background_color = color;
            this.pos.data.write("restaurant.floor", [this.activeFloor.id], {
                background_color: color,
            });
        }
        this.state.isColorPicker = false;
    }
    _getColors() {
        return {
            white: [255, 255, 255],
            red: [235, 109, 109],
            green: [53, 211, 116],
            blue: [108, 109, 236],
            orange: [235, 191, 109],
            yellow: [235, 236, 109],
            purple: [172, 109, 173],
            grey: [108, 109, 109],
            lightGrey: [172, 173, 173],
            turquoise: [78, 210, 190],
        };
    }
    formatColor(color) {
        return `rgb(${color})`;
    }
    getColors() {
        return Object.fromEntries(
            Object.entries(this._getColors()).map(([k, v]) => [k, this.formatColor(v)])
        );
    }
    getLighterShade(color) {
        return this.formatColor([...this._getColors()[color], 0.75]);
    }
    async deleteFloorOrTable() {
        if (this.selectedTables.length == 0) {
            const confirmed = await ask(this.dialog, {
                title: `Removing floor ${this.activeFloor.name}`,
                body: sprintf(
                    _t("Removing a floor cannot be undone. Do you still want to remove %s?"),
                    this.activeFloor.name
                ),
            });
            if (!confirmed) {
                return;
            }
            const activeFloor = this.activeFloor;
            try {
                await this.pos.data.call("restaurant.floor", "deactivate_floor", [
                    activeFloor.id,
                    this.pos.session.id,
                ]);
            } catch {
                this.dialog.add(AlertDialog, {
                    title: _t("Delete Error"),
                    body: _t(
                        "You cannot delete a floor with orders still in draft for this floor."
                    ),
                });
                return;
            }

            const orderList = [...this.pos.get_order_list()];
            for (const order of orderList) {
                if (activeFloor.table_ids.includes(order.tableId)) {
                    this.pos.removeOrder(order, false);
                }
            }

            for (const table_id of activeFloor.table_ids) {
                table_id.delete();
            }

            activeFloor.delete();

            this.pos.TICKET_SCREEN_STATE.syncedOrders.cache = {};
            if (this.pos.models["restaurant.floor"].length > 0) {
                this.selectFloor(this.pos.models["restaurant.floor"].getAll()[0]);
            } else {
                this.pos.isEditMode = false;
                this.pos.floorPlanStyle = "default";
            }
            return;
        }

        const confirmed = await ask(this.dialog, {
            title: _t("Are you sure?"),
            body: _t("Removing a table cannot be undone"),
        });
        if (!confirmed) {
            return;
        }
        const originalSelectedTableIds = [...this.state.selectedTableIds];

        try {
            const response = await this.pos.data.call(
                "restaurant.table",
                "are_orders_still_in_draft",
                [originalSelectedTableIds]
            );

            if (response) {
                for (const id of originalSelectedTableIds) {
                    //remove order not send to server
                    for (const order of this.pos.get_order_list()) {
                        if (order.tableId == id) {
                            this.pos.removeOrder(order, false);
                        }
                    }
                    const records = this.pos.data.write("restaurant.table", [id], {
                        active: false,
                    });
                    records[0].delete();
                }
            }
        } catch {
            this.dialog.add(AlertDialog, {
                title: _t("Delete Error"),
                body: _t("You cannot delete a table with orders still in draft for this table."),
            });
        }

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
        this.pos.TICKET_SCREEN_STATE.syncedOrders.cache = {};
    }
    getFloorChangeCount(floor) {
        let changeCount = 0;
        if (!floor) {
            return changeCount;
        }
        const table_ids = floor.table_ids;
        for (const table of table_ids) {
            const tNotif = this.pos.tableNotifications[table.id];
            if (tNotif) {
                changeCount += tNotif.changes_count;
            }
        }

        return changeCount;
    }
    getChildren(table) {
        return this.pos.models["restaurant.table"].filter((t) => t.parent_id?.id === table.id);
    }
}

registry.category("pos_screens").add("FloorScreen", FloorScreen);
