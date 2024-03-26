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
import { Component, onMounted, useRef, useState, onWillStart, useEffect } from "@odoo/owl";
import { ask } from "@point_of_sale/app/store/make_awaitable_dialog";
import { unique } from "@web/core/utils/arrays";
import { loadImage } from "@point_of_sale/utils";
import { getDataURLFromFile } from "@web/core/utils/urls";
import { hasTouch } from "@web/core/browser/feature_detection";

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
            floorHeight: "100%",
            floorWidth: "100%",
            selectedTableIds: this.getTablesSelectedByDefault(),
            isColorPicker: false,
        });
        this.floorMapRef = useRef("floor-map-ref");
        this.floorScrollBox = useRef("floor-map-scroll");
        const ui = useState(useService("ui"));
        const mode = localStorage.getItem("floorPlanStyle");
        this.pos.floorPlanStyle = ui.isSmall || mode == "kanban" ? "kanban" : "default";
        this.map = useRef("map");
        onMounted(() => {
            this.pos.openCashControl();
        });
        onWillStart(this.onWillStart);
        useEffect(
            () => {
                this.computeFloorSize();
            },
            () => [this.activeFloor, this.pos.floorPlanStyle]
        );
        useEffect(
            (tableL) => {
                if (hasTouch()) {
                    if (tableL) {
                        this.floorScrollBox.el.classList.remove("overflow-scroll");
                        this.floorScrollBox.el.classList.add("overflow-hidden");
                    } else {
                        this.floorScrollBox.el.classList.remove("overflow-hidden");
                        this.floorScrollBox.el.classList.add("overflow-scroll");
                    }
                }
            },
            () => [this.state.selectedTableIds.length]
        );
    }
    computeFloorSize() {
        if (this.pos.floorPlanStyle === "kanban") {
            this.state.floorHeight = "100%";
            this.state.floorWidth = window.innerWidth + "px";
            return;
        }

        if (!this.activeFloor) {
            return;
        }

        const tables = this.activeFloor.table_ids;
        const floorV = this.floorMapRef.el.clientHeight;
        const floorH = this.floorMapRef.el.offsetWidth;
        const positionH = Math.max(
            ...tables.map((table) => table.position_h + table.width),
            floorH
        );
        const positionV = Math.max(
            ...tables.map((table) => table.position_v + table.height),
            floorV
        );

        if (this.activeFloor.floor_background_image) {
            const img = new Image();
            img.onload = () => {
                const height = Math.max(img.height, positionV);
                const width = Math.max(img.width, positionH);
                this.state.floorHeight = `${height}px`;
                this.state.floorWidth = `${width}px`;
            };
            img.src = "data:image/png;base64," + this.activeFloor.floor_background_image;
        } else {
            this.state.floorHeight = `${positionV}px`;
            this.state.floorWidth = `${positionH}px`;
        }
    }
    getTablesSelectedByDefault() {
        const oToTrans = this.pos.models["pos.order"].getBy("uuid", this.pos.orderToTransferUuid);
        return oToTrans ? [oToTrans.table_id.id] : [];
    }
    async onWillStart() {
        const table = this.pos.selectedTable;
        const tableByIds = this.pos.models["restaurant.table"].getAllBy("id");
        if (table) {
            const orders = this.pos.get_order_list();
            const tableOrders = orders.filter(
                (order) => order.table_id?.id === table.id && !order.finalized
            );
            const qtyChange = tableOrders.reduce(
                (acc, order) => {
                    const quantityChange = this.pos.getOrderChanges(false, order);
                    const quantitySkipped = this.pos.getOrderChanges(true, order);
                    acc.changed += quantityChange.count;
                    acc.skipped += quantitySkipped.count;
                    return acc;
                },
                { changed: 0, skipped: 0 }
            );

            tableByIds[table.id].uiState.orderCount = tableOrders.length;
            tableByIds[table.id].uiState.changeCount = qtyChange.changed;
        }
        await this.pos.unsetTable();
    }
    get floorBackround() {
        return this.activeFloor.floor_background_image
            ? "data:image/png;base64," + this.activeFloor.floor_background_image
            : "none";
    }
    onClickFloorMap() {
        for (const tableId of this.state.selectedTableIds) {
            const table = this.pos.models["restaurant.table"].get(tableId);
            this.pos.data.write("restaurant.table", [tableId], {
                ...table.serialize({ orm: true }),
            });
        }
        this.state.selectedTableIds = this.getTablesSelectedByDefault();
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
            newTableData = copyTable.serialize({ orm: true });
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
        const table = await this.createTableFromRaw(newTableData);
        return table;
    }
    async createTableFromRaw(newTableData) {
        newTableData.active = true;
        const table = await this.pos.data.create("restaurant.table", [newTableData]);
        return table[0];
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
        this.unselectTables();
    }
    async onClickTable(table, ev) {
        if (this.pos.isEditMode) {
            if (ev.ctrlKey || ev.metaKey) {
                this.state.selectedTableIds.push(table.id);
            } else {
                this.unselectTables();
                this.state.selectedTableIds.push(table.id);
            }
            return;
        }
        if (table.parent_id) {
            this.onClickTable(table.parent_id, ev);
            return;
        }
        const oToTrans = this.pos.models["pos.order"].getBy("uuid", this.pos.orderToTransferUuid);
        if (oToTrans) {
            await this.pos.transferTable(table);
        } else {
            try {
                this.pos.tableSyncing = true;
                await this.pos.setTable(table);
            } catch (e) {
                if (!(e instanceof ConnectionLostError)) {
                    throw e;
                }
                // Reject error in a separate stack to display the offline popup, but continue the flow
                Promise.reject(e);
            } finally {
                this.pos.tableSyncing = false;
            }
        }
        const orders = this.pos.getTableOrders(table.id);
        if (orders.length > 0) {
            this.pos.showScreen(orders[0].get_screen_data().name);
        } else {
            this.pos.add_new_order();
            this.pos.showScreen("ProductScreen");
        }
    }
    unselectTables() {
        if (this.selectedTables.length) {
            for (const table of this.selectedTables) {
                this.pos.data.write("restaurant.table", [table.id], table.serialize({ orm: true }));
            }
        }
        this.state.selectedTableIds = [];
    }
    closeEditMode() {
        this.pos.isEditMode = false;
        this.unselectTables();
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

                this.selectFloor(floor[0]);
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

            this.selectFloor(copyFloor[0]);
            this.pos.isEditMode = true;

            for (const table of tables) {
                const tableSerialized = table.serialize({ orm: true });
                tableSerialized.floor_id = copyFloor[0].id;
                await this.createTableFromRaw(tableSerialized);
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
                              this.pos.data.write("restaurant.table", [this.selectedTables[0].id], {
                                  name: newName,
                              });
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
            title: _t("Number of Seats?"),
            getPayload: (num) => {
                const newSeatsNum = parseInt(num, 10);
                selectedTables.forEach((selectedTable) => {
                    if (newSeatsNum !== selectedTable.seats) {
                        this.pos.data.write("restaurant.table", [selectedTable.id], {
                            seats: newSeatsNum,
                        });
                    }
                });
            },
        });
    }
    stopOrderTransfer() {
        const order = this.pos.models["pos.order"].getBy("uuid", this.pos.orderToTransferUuid);
        this.pos.set_order(order);
        this.pos.showScreen("ProductScreen");
        this.pos.isTableToMerge = false;
        this.pos.orderToTransferUuid = null;
    }
    changeShape(form) {
        for (const table of this.selectedTables) {
            this.pos.data.write("restaurant.table", [table.id], { shape: form });
        }
    }
    unlinkTables() {
        for (const table of this.selectedTables) {
            this.pos.data.write("restaurant.table", [table.id], { parent_id: false });
        }
    }
    linkTables() {
        const parentTable =
            this.selectedTables.filter((t) => t.parent_id)?.[0] || this.selectedTables[0];
        const childrenTables = this.selectedTables.filter((t) => t.id !== parentTable.id);
        for (const table of childrenTables) {
            table.update({ parent_id: parentTable });
        }
        this.pos.updateTables(...childrenTables);
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
            for (const table of this.selectedTables) {
                this.pos.data.write("restaurant.table", [table.id], { color: color });
            }
        } else {
            this.activeFloor.background_color = color;
            this.pos.data.write("restaurant.floor", [this.activeFloor.id], {
                background_color: color,
                floor_background_image: false,
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
                        if (order.table_id == id) {
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
    }
    getFloorChangeCount(floor) {
        let changeCount = 0;
        if (!floor) {
            return changeCount;
        }
        const table_ids = floor.table_ids;
        for (const table of table_ids) {
            changeCount += table.uiState.changeCount || 0;
        }

        return changeCount;
    }
    getChildren(table) {
        return this.pos.models["restaurant.table"].filter((t) => t.parent_id?.id === table.id);
    }
    async uploadImage(event) {
        const file = event.target.files[0];
        if (!file.type.match(/image.*/)) {
            this.dialog.add(AlertDialog, {
                title: _t("Unsupported File Format"),
                body: _t("Only web-compatible Image formats such as .png or .jpeg are supported."),
            });
        } else {
            const imageUrl = await getDataURLFromFile(file);
            const loadedImage = await loadImage(imageUrl);
            if (loadedImage) {
                this.env.services.ui.block();
                await this.pos.data.ormWrite("restaurant.floor", [this.activeFloor.id], {
                    floor_background_image: imageUrl.split(",")[1],
                });
                // A read is added to be sure that we have the same image as the one in backend
                await this.pos.data.read("restaurant.floor", [this.activeFloor.id]);
                this.env.services.ui.unblock();
            } else {
                this.dialog.add(AlertDialog, {
                    title: _t("Loading Image Error"),
                    body: _t("Encountered error when loading image. Please try again."),
                });
            }
            this.state.isColorPicker = false;
        }
    }
}

registry.category("pos_screens").add("FloorScreen", FloorScreen);
