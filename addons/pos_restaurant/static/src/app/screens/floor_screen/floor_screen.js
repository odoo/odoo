import { Component, useEffect, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { FloorEditorToolBar } from "@pos_restaurant/app/screens/floor_screen/floor_plan_editor/toolbar/toolbar";
import { NumpadDropdown } from "@pos_restaurant/app/components/numpad_dropdown/numpad_dropdown";
import { FloorPlan } from "@pos_restaurant/app/screens/floor_screen/floor_plan/floor_plan";
import { useFloorPlanStore } from "@pos_restaurant/app/hooks/floor_plan_hook";
import { FloorPlanEditor } from "@pos_restaurant/app/screens/floor_screen/floor_plan_editor/floor_plan_editor";

export class FloorScreen extends Component {
    static template = "pos_restaurant.FloorScreen";
    static components = { NumpadDropdown, FloorEditorToolBar, FloorPlan, FloorPlanEditor };
    static props = {};
    static storeOnOrder = false;

    setup() {
        this.pos = usePos();
        this.floorPlanStore = useFloorPlanStore();
        this.ui = useService("ui");

        useEffect(
            (isEditMode) => {
                if (isEditMode) {
                    document.body.classList.add("o_fp_edit_mode");
                } else {
                    document.body.classList.remove("o_fp_edit_mode");
                }
            },
            () => [this.floorPlanStore.editMode]
        );

        onMounted(() => {
            this.pos.openOpeningControl();
            if (!this.pos.isOrderTransferMode) {
                this.resetTable();
            }
        });
    }

    async resetTable() {
        this.pos.searchProductWord = "";
        const table = this.pos.selectedTable;
        if (table) {
            await this.pos.unsetTable();
        }
        // Set order to null when reaching the floor screen.
        if (!(this.pos.getOrder()?.isFilledDirectSale && !this.pos.getOrder().finalized)) {
            this.pos.setOrder(null);
        }
    }

<<<<<<< 384dce8575ca7530351deaf5b08c004da36c062f
    startFloorPlanEditing() {
        this.floorPlanStore.startEditMode();
||||||| d58f4ed332af35f6de26a93f07adf05368731e20
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
                active: true,
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
            newTableData.table_number = this._getNewTableNumber();
        }
        const table = await this.createTableFromRaw(newTableData);
        return table;
    }
    async createTableFromRaw(newTableData) {
        newTableData.active = true;
        const table = await this.pos.data.create("restaurant.table", [newTableData]);
        return table[0];
    }
    async unMergeTable(table) {
        const mainOrder = this.pos.getActiveOrdersOnTable(table.rootTable)?.[0];
        this.pos.restoreOrdersToOriginalTable(mainOrder, table);
    }
    _getNewTableNumber() {
        if (!this.activeTables?.length) {
            return 1;
        }
        return Math.max(...this.activeTables.map((t) => t.table_number)) + 1;
    }
    get activeFloor() {
        return this.state.selectedFloorId
            ? this.pos.models["restaurant.floor"].get(this.state.selectedFloorId)
            : null;
    }
    get activeTables() {
        return this.activeFloor?.table_ids?.filter((table) => table.active) || [];
    }
    get selectedTables() {
        return this.state.selectedTableIds.map((id) => this.pos.models["restaurant.table"].get(id));
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
        this.saveCurrentFloorScrollPosition();
        this.pos.currentFloor = floor;
        this.state.selectedFloorId = floor.id;
        this.unselectTables();
        this.restoreFloorScrollPosition();
    }
    async onClickTable(table, ev) {
        if (this.pos.isEditMode) {
            if (this.state.selectedTableIds.includes(table.id)) {
                this.state.selectedTableIds = this.state.selectedTableIds.filter(
                    (id) => id !== table.id
                );
                return;
            }
            if (!ev.ctrlKey && !ev.metaKey) {
                this.unselectTables();
            }
            this.state.selectedTableIds.push(table.id);
            return;
        }
        if (table.parent_id) {
            this.onClickTable(table.parent_id, ev);
            return;
        }
        if (!this.pos.isOrderTransferMode) {
            await this.pos.setTableFromUi(table);
        }
    }
    unselectTables() {
        if (this.selectedTables.length) {
            for (const table of this.selectedTables) {
                this.pos.data.write("restaurant.table", [table.id], table.serializeForORM());
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
                            background_color: "white",
                            pos_config_ids: [this.pos.config.id],
                        },
                    ],
                    false
                );

                this.selectFloor(floor[0]);
                this.pos.isEditMode = true;
            },
        });
=======
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
                active: true,
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
            newTableData.table_number = this._getNewTableNumber();
        }
        const table = await this.createTableFromRaw(newTableData);
        return table;
    }
    async createTableFromRaw(newTableData) {
        newTableData.active = true;
        const table = await this.pos.data.create("restaurant.table", [newTableData]);
        return table[0];
    }
    async unMergeTable(table) {
        const mainOrder = this.pos.getActiveOrdersOnTable(table.rootTable)?.[0];
        this.pos.restoreOrdersToOriginalTable(mainOrder, table);
    }
    _getNewTableNumber() {
        if (!this.activeTables?.length) {
            return 1;
        }
        return Math.max(...this.activeTables.map((t) => t.table_number)) + 1;
    }
    get activeFloor() {
        return this.state.selectedFloorId
            ? this.pos.models["restaurant.floor"].get(this.state.selectedFloorId)
            : null;
    }
    get activeTables() {
        return this.activeFloor?.table_ids?.filter((table) => table.active) || [];
    }
    get selectedTables() {
        return this.state.selectedTableIds.map((id) => this.pos.models["restaurant.table"].get(id));
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
        this.saveCurrentFloorScrollPosition();
        this.pos.currentFloor = floor;
        this.state.selectedFloorId = floor.id;
        this.unselectTables();
        this.restoreFloorScrollPosition();
    }
    async onClickTable(table, ev) {
        if (this.pos.isEditMode) {
            if (this.state.selectedTableIds.includes(table.id)) {
                this.state.selectedTableIds = this.state.selectedTableIds.filter(
                    (id) => id !== table.id
                );
                return;
            }
            if (!ev.ctrlKey && !ev.metaKey) {
                this.unselectTables();
            }
            this.state.selectedTableIds.push(table.id);
            return;
        }
        if (table.parent_id) {
            this.onClickTable(table.parent_id, ev);
            return;
        }
        if (!this.pos.isOrderTransferMode) {
            await this.pos.setTableFromUi(table);
        }
    }
    unselectTables() {
        if (this.selectedTables.length) {
            for (const table of this.selectedTables) {
                this.pos.data.write("restaurant.table", [table.id], table.serializeForORM());
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
                            background_color: "white",
                            active: true,
                            pos_config_ids: [this.pos.config.id],
                        },
                    ],
                    false
                );

                this.selectFloor(floor[0]);
                this.pos.isEditMode = true;
            },
        });
>>>>>>> d03fbf084643cb68b2edfd04d31b292e72eb68f0
    }

    selectFloor(floorUuid) {
        this.floorPlanStore.selectFloorByUuid(floorUuid);
    }

<<<<<<< 384dce8575ca7530351deaf5b08c004da36c062f
||||||| d58f4ed332af35f6de26a93f07adf05368731e20
    _isTableVisible(table, margin = 0) {
        const container = this.floorScrollBox.el;
        const containerTop = container.scrollTop;
        const containerBottom = containerTop + container.clientHeight;
        const containerLeft = container.scrollLeft;
        const containerRight = containerLeft + container.clientWidth;

        const tableTop = table.position_v + margin;
        const tableLeft = table.position_h + margin;
        const tableBottom = tableTop + table.height;
        const tableRight = tableLeft + table.width;

        return (
            tableBottom <= containerBottom &&
            tableTop >= containerTop &&
            tableRight <= containerRight &&
            tableLeft >= containerLeft
        );
    }

    async duplicateFloor() {
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

        this.pos.isEditMode = true;
        for (const table of tables) {
            const tableSerialized = table.serializeForORM();
            tableSerialized.floor_id = copyFloor[0].id;
            await this.createTableFromRaw(tableSerialized);
        }

        this.selectFloor(copyFloor[0]);
    }
    async duplicateTable() {
        const selectedTables = this.selectedTables;
        this.state.selectedTableIds = [];

        for (const table of selectedTables) {
            const newTable = await this._createTableHelper(table);
            if (newTable) {
                this.state.selectedTableIds.push(newTable.id);
            }
        }
    }
    async renameFloor() {
        this.dialog.add(TextInputPopup, {
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
        });
    }
    async renameTable() {
        if (this.selectedTables.length > 1) {
            return;
        }
        if (this.selectedTables.length === 1) {
            this.dialog.add(NumberPopup, {
                startingValue: parseInt(this.selectedTables[0].table_number) || false,
                title: _t("Change table number?"),
                placeholder: _t("Enter a table number"),
                buttons: getButtons([{ ...DECIMAL, disabled: true }, ZERO, BACKSPACE]),
                isValid: (x) => x,
                getPayload: (newNumber) => {
                    if (parseInt(newNumber) !== this.selectedTables[0].table_number) {
                        this.pos.data.write("restaurant.table", [this.selectedTables[0].id], {
                            table_number: parseInt(newNumber),
                        });
                    }
                },
            });
        } else {
            this.dialog.add(TextInputPopup, {
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
            });
        }
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
    changeShape(form) {
        for (const table of this.selectedTables) {
            this.pos.data.write("restaurant.table", [table.id], { shape: form });
        }
    }

    setFloorColor(color, key) {
        this.activeFloor.background_color = color;
        this.pos.data.write("restaurant.floor", [this.activeFloor.id], {
            background_color: key,
            floor_background_image: false,
        });
    }

    setTableColor(color) {
        if (this.selectedTables.length > 0) {
            for (const table of this.selectedTables) {
                this.pos.data.write("restaurant.table", [table.id], { color: color });
            }
        }
    }
    _getColors() {
        const lightModeColors = {
            white: [249, 250, 251],
            red: [220, 80, 90],
            green: [60, 160, 90],
            blue: [30, 130, 210],
            orange: [250, 170, 60],
            yellow: [245, 205, 80],
            purple: [150, 100, 220],
            grey: [120, 130, 140],
            lightGrey: [200, 205, 210],
            turquoise: [40, 180, 200],
        };

        const darkModeColors = {
            white: [60, 62, 75],
            red: [200, 60, 75],
            green: [50, 130, 80],
            blue: [40, 90, 180],
            orange: [190, 120, 50],
            yellow: [190, 160, 40],
            purple: [130, 80, 160],
            grey: [40, 45, 50],
            lightGrey: [140, 145, 150],
            turquoise: [30, 140, 150],
        };

        return cookie.get("pos_color_scheme") === "dark" ? darkModeColors : lightModeColors;
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
    async deleteFloor() {
        const confirmed = await ask(this.dialog, {
            title: `Removing floor ${this.activeFloor.name}`,
            body: _t(
                "Removing a floor cannot be undone. Do you still want to remove %s?",
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
                body: _t("You cannot delete a floor with orders still in draft for this floor."),
            });
            return;
        }

        const orderList = [...this.pos.getOpenOrders()];
        for (const order of orderList) {
            if (activeFloor.table_ids.includes(order.tableId)) {
                this.pos.removeOrder(order, false);
            }
        }

        this.pos.models["restaurant.table"].deleteMany(activeFloor.table_ids);
        activeFloor.delete();

        if (this.pos.models["restaurant.floor"].length > 0) {
            this.selectFloor(this.pos.models["restaurant.floor"].getAll()[0]);
        } else {
            this.pos.isEditMode = false;
            this.pos.floorPlanStyle = "default";
        }
        return;
    }
    async deleteTable() {
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
                    for (const order of this.pos.getOpenOrders()) {
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
        const equalsCheck = (a, b) => JSON.stringify(a) === JSON.stringify(b);
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
            changeCount += this.getChangeCount(table) || 0;
        }

        return changeCount;
    }
    async uploadImage(event) {
        const file = event.target.files[0];
        if (!file) {
            // Don't proceed if there are no selected files.
            return;
        }
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
        }
    }
    getChangeCount(table) {
        // This information in uiState came by websocket
        // If the table is not synced, we need to count the unsynced orders
        let changeCount = 0;
        const tableOrders = this.pos.models["pos.order"].filter(
            (o) => o.table_id?.id === table.id && !o.finalized
        );

        for (const order of tableOrders) {
            const changes = getOrderChanges(order, this.pos.config.preparationCategories);
            changeCount += changes.nbrOfChanges;
        }

        return { changes: changeCount };
    }
    setColor(hasSelectedTable, color, key) {
        if (hasSelectedTable) {
            return this.setTableColor(color);
        } else {
            return this.setFloorColor(color, key);
        }
    }
    rename(hasSelectedTable) {
        if (hasSelectedTable) {
            return this.renameTable();
        } else {
            return this.renameFloor();
        }
    }
    duplicate(hasSelectedTable) {
        if (hasSelectedTable) {
            return this.duplicateTable();
        } else {
            return this.duplicateFloor();
        }
    }
    delete(hasSelectedTable) {
        if (hasSelectedTable) {
            return this.deleteTable();
        } else {
            return this.deleteFloor();
        }
    }
=======
    _isTableVisible(table, margin = 0) {
        const container = this.floorScrollBox.el;
        const containerTop = container.scrollTop;
        const containerBottom = containerTop + container.clientHeight;
        const containerLeft = container.scrollLeft;
        const containerRight = containerLeft + container.clientWidth;

        const tableTop = table.position_v + margin;
        const tableLeft = table.position_h + margin;
        const tableBottom = tableTop + table.height;
        const tableRight = tableLeft + table.width;

        return (
            tableBottom <= containerBottom &&
            tableTop >= containerTop &&
            tableRight <= containerRight &&
            tableLeft >= containerLeft
        );
    }

    async duplicateFloor() {
        const floor = this.activeFloor;
        const tables = this.activeFloor.table_ids;
        const newFloorName = floor.name + " (copy)";
        const copyFloor = await this.pos.data.create("restaurant.floor", [
            {
                name: newFloorName,
                active: true,
                background_color: "#ACADAD",
                pos_config_ids: [this.pos.config.id],
            },
        ]);

        this.pos.isEditMode = true;
        for (const table of tables) {
            const tableSerialized = table.serializeForORM();
            tableSerialized.floor_id = copyFloor[0].id;
            await this.createTableFromRaw(tableSerialized);
        }

        this.selectFloor(copyFloor[0]);
    }
    async duplicateTable() {
        const selectedTables = this.selectedTables;
        this.state.selectedTableIds = [];

        for (const table of selectedTables) {
            const newTable = await this._createTableHelper(table);
            if (newTable) {
                this.state.selectedTableIds.push(newTable.id);
            }
        }
    }
    async renameFloor() {
        this.dialog.add(TextInputPopup, {
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
        });
    }
    async renameTable() {
        if (this.selectedTables.length > 1) {
            return;
        }
        if (this.selectedTables.length === 1) {
            this.dialog.add(NumberPopup, {
                startingValue: parseInt(this.selectedTables[0].table_number) || false,
                title: _t("Change table number?"),
                placeholder: _t("Enter a table number"),
                buttons: getButtons([{ ...DECIMAL, disabled: true }, ZERO, BACKSPACE]),
                isValid: (x) => x,
                getPayload: (newNumber) => {
                    if (parseInt(newNumber) !== this.selectedTables[0].table_number) {
                        this.pos.data.write("restaurant.table", [this.selectedTables[0].id], {
                            table_number: parseInt(newNumber),
                        });
                    }
                },
            });
        } else {
            this.dialog.add(TextInputPopup, {
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
            });
        }
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
    changeShape(form) {
        for (const table of this.selectedTables) {
            this.pos.data.write("restaurant.table", [table.id], { shape: form });
        }
    }

    setFloorColor(color, key) {
        this.activeFloor.background_color = color;
        this.pos.data.write("restaurant.floor", [this.activeFloor.id], {
            background_color: key,
            floor_background_image: false,
        });
    }

    setTableColor(color) {
        if (this.selectedTables.length > 0) {
            for (const table of this.selectedTables) {
                this.pos.data.write("restaurant.table", [table.id], { color: color });
            }
        }
    }
    _getColors() {
        const lightModeColors = {
            white: [249, 250, 251],
            red: [220, 80, 90],
            green: [60, 160, 90],
            blue: [30, 130, 210],
            orange: [250, 170, 60],
            yellow: [245, 205, 80],
            purple: [150, 100, 220],
            grey: [120, 130, 140],
            lightGrey: [200, 205, 210],
            turquoise: [40, 180, 200],
        };

        const darkModeColors = {
            white: [60, 62, 75],
            red: [200, 60, 75],
            green: [50, 130, 80],
            blue: [40, 90, 180],
            orange: [190, 120, 50],
            yellow: [190, 160, 40],
            purple: [130, 80, 160],
            grey: [40, 45, 50],
            lightGrey: [140, 145, 150],
            turquoise: [30, 140, 150],
        };

        return cookie.get("pos_color_scheme") === "dark" ? darkModeColors : lightModeColors;
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
    async deleteFloor() {
        const confirmed = await ask(this.dialog, {
            title: `Removing floor ${this.activeFloor.name}`,
            body: _t(
                "Removing a floor cannot be undone. Do you still want to remove %s?",
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
                body: _t("You cannot delete a floor with orders still in draft for this floor."),
            });
            return;
        }

        const orderList = [...this.pos.getOpenOrders()];
        for (const order of orderList) {
            if (activeFloor.table_ids.includes(order.tableId)) {
                this.pos.removeOrder(order, false);
            }
        }

        this.pos.models["restaurant.table"].deleteMany(activeFloor.table_ids);
        activeFloor.delete();

        const remainingFloors = this.pos.config.floor_ids.filter((f) => f.active);
        if (remainingFloors.length > 0) {
            this.selectFloor(remainingFloors[0]);
        } else {
            this.pos.isEditMode = false;
            this.pos.floorPlanStyle = "default";
        }
        return;
    }
    async deleteTable() {
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
                    for (const order of this.pos.getOpenOrders()) {
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
        const equalsCheck = (a, b) => JSON.stringify(a) === JSON.stringify(b);
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
            changeCount += this.getChangeCount(table) || 0;
        }

        return changeCount;
    }
    async uploadImage(event) {
        const file = event.target.files[0];
        if (!file) {
            // Don't proceed if there are no selected files.
            return;
        }
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
        }
    }
    getChangeCount(table) {
        // This information in uiState came by websocket
        // If the table is not synced, we need to count the unsynced orders
        let changeCount = 0;
        const tableOrders = this.pos.models["pos.order"].filter(
            (o) => o.table_id?.id === table.id && !o.finalized
        );

        for (const order of tableOrders) {
            const changes = getOrderChanges(order, this.pos.config.preparationCategories);
            changeCount += changes.nbrOfChanges;
        }

        return { changes: changeCount };
    }
    setColor(hasSelectedTable, color, key) {
        if (hasSelectedTable) {
            return this.setTableColor(color);
        } else {
            return this.setFloorColor(color, key);
        }
    }
    rename(hasSelectedTable) {
        if (hasSelectedTable) {
            return this.renameTable();
        } else {
            return this.renameFloor();
        }
    }
    duplicate(hasSelectedTable) {
        if (hasSelectedTable) {
            return this.duplicateTable();
        } else {
            return this.duplicateFloor();
        }
    }
    delete(hasSelectedTable) {
        if (hasSelectedTable) {
            return this.deleteTable();
        } else {
            return this.deleteFloor();
        }
    }
>>>>>>> d03fbf084643cb68b2edfd04d31b292e72eb68f0
    clickNewOrder() {
        this.pos.addNewOrder();
        this.pos.navigate("ProductScreen", {
            orderUuid: this.pos.selectedOrderUuid,
        });
    }

    toggleTableSelector() {
        this.pos.tableSelectorState = !this.pos.tableSelectorState;
    }

    isEditMode() {
        return this.floorPlanStore.editMode;
    }

    onToolbarTransitionEnd(e) {
        if (e.propertyName !== "opacity") {
            return;
        }
        if (!this.floorPlanStore.editMode) {
            this.floorPlanStore.showEditToolbar = false;
        }
    }

    initFloorPlanEditorActionHandler(actionHandler) {
        this.fpeActionHandler = actionHandler;
    }

    getFloorPlanEditorActionHandler() {
        return this.fpeActionHandler;
    }
}

registry.category("pos_pages").add("FloorScreen", {
    name: "FloorScreen",
    component: FloorScreen,
    route: `/pos/ui/${odoo.pos_config_id}/floor`,
    params: {},
});
