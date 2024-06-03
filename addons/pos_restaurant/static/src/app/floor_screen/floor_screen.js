import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";
import { ConnectionLostError } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

import { TextInputPopup } from "@point_of_sale/app/utils/input_popups/text_input_popup";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { getOrderChanges } from "@point_of_sale/app/models/utils/order_change";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted, useRef, useState, onWillStart, useEffect } from "@odoo/owl";
import { ask } from "@point_of_sale/app/store/make_awaitable_dialog";
import { loadImage } from "@point_of_sale/utils";
import { getDataURLFromFile } from "@web/core/utils/urls";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { useDropzone } from "@mail/core/common/dropzone_hook";
import { makeDraggableHook } from "@web/core/utils/draggable_hook_builder_owl";
import { pick } from "@web/core/utils/objects";
import { constrain, getLimits } from "@point_of_sale/app/utils/movable_hook";
import { withComputedProperties } from "@web/core/utils/reactive";

/**
 * This hook exists only because safari on iOS does not support the `oncontextmenu` event
 */
export function useLongPress(querySelector, callback, ms = 350) {
    let timer = null;
    const start = (event) => {
        const el = event.target.closest(querySelector);
        if (el) {
            timer = setTimeout(() => {
                callback(el);
                event.preventDefault();
            }, ms);
        }
    };

    const stop = (event) => {
        if (timer) {
            clearTimeout(timer);
        }
        return true;
    };
    useEffect(
        () => {
            document.addEventListener("touchstart", start);
            document.addEventListener("touchend", stop);
            document.addEventListener("touchcancel", stop);

            return () => {
                document.removeEventListener("touchstart", start);
                document.removeEventListener("touchend", stop);
                document.removeEventListener("touchcancel", stop);
            };
        },
        () => []
    );
}

const getPositions = (ctx) => {
    const element = ctx.current.element;
    const scrollingContainer = element.parentElement.parentElement.parentElement;
    const x = ctx.pointer.x;
    // we want y to be relative to the floormap, not the whole screen, which includes the navbar and the floor selector
    const y = ctx.pointer.y - scrollingContainer.getBoundingClientRect().top;
    return {
        position_h: x + scrollingContainer.scrollLeft - element.getBoundingClientRect().width / 2,
        position_v: y + scrollingContainer.scrollTop - element.getBoundingClientRect().height / 2,
    };
};
const useDraggable = makeDraggableHook({
    name: "useDraggable",
    onComputeParams({ ctx }) {
        ctx.followCursor = false;
    },
    onWillStartDrag: ({ ctx }) => pick(ctx.current, "element"),
    onDragStart: ({ ctx }) => pick(ctx.current, "element"),
    onDrag: ({ ctx }) => ({
        ...pick(ctx.current, "element"),
        ...getPositions(ctx),
    }),
    onDragEnd: ({ ctx }) => pick(ctx.current, "element"),
    onDrop: ({ ctx }) => ({
        ...pick(ctx.current, "element"),
        ...getPositions(ctx),
    }),
});
export class FloorScreen extends Component {
    static components = { Dropdown, DropdownItem };
    static template = "pos_restaurant.FloorScreen";
    static props = { floor: { type: true, optional: true } };
    static storeOnOrder = false;
    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.state = useState({
            floor: this.props.floor || this.pos.config.floor_ids[0],
            resizingTable: null,
            isMovingTable: false,
            tableDropdownId: null,
            floorDropdownId: null,
        });
        const getPosTable = (el) => {
            return this.pos.models["restaurant.table"].get(
                [...el.classList].find((c) => c.includes("tableId")).split("-")[1]
            );
        };
        // TODO: only call this if we are on ios
        useLongPress(".table", (el) => {
            // this.onTableRightClick(getPosTable(el));
            console.log("sadf");
        });
        useLongPress(".button-floor", (el) => {
            // this.onFloorRightClick(
            //     this.pos.models["restaurant.floor"].get(
            //         [...el.classList].find((c) => c.includes("floorId")).split("-")[1]
            //     )
            // );
            console.log("sadf2");
        });

        this.ui = useState(useService("ui"));
        const mode = localStorage.getItem("floorPlanStyle");
        this.pos.floorPlanStyle = this.ui.isSmall || mode == "kanban" ? "kanban" : "default";
        this.map = useRef("map");
        onMounted(() => {
            this.pos.openCashControl();
        });
        onWillStart(this.onWillStart);
        useEffect(
            () => {
                const stopResize = () => (this.state.resizingTable = null);
                window.addEventListener("click", stopResize);
                return () => window.removeEventListener("click", stopResize);
            },
            () => []
        );
        const areElementsIntersecting = (el1, el2) => {
            const rect1 = el1.getBoundingClientRect();
            const rect2 = el2.getBoundingClientRect();
            return !(
                rect1.right < rect2.left ||
                rect1.left > rect2.right ||
                rect1.bottom < rect2.top ||
                rect1.top > rect2.bottom
            );
        };
        const findIntersectingTable = (tableElem) => {
            const table = getPosTable(tableElem);
            return [...tableElem.parentElement.getElementsByClassName("table")].find(
                (t) =>
                    t !== tableElem &&
                    areElementsIntersecting(t, tableElem) &&
                    !table.isParent(getPosTable(t))
            );
        };
        useDropzone(this.map, (ev) => this.uploadImage(ev.dataTransfer.files[0]));

        useDraggable({
            ref: this.map,
            elements: ".table",
            enable: () => !this.state.resizingTable && this.pos.floorPlanStyle !== "kanban",
            onDragStart: (ctx) => {
                ctx.addClass(ctx.element, "shadow");
                const table = getPosTable(ctx.element);
                if (table.parent_id) {
                    this.pos.data.write("restaurant.table", [table.id], {
                        parent_id: null,
                    });
                }
                table.uiState.initialPosition = pick(table, "position_h", "position_v");
                this.state.isMovingTable = true;
                this.state.tableDropdownId = null;
            },
            onDrag: (ctx) => {
                const table = getPosTable(ctx.element);
                table.position_h = ctx.position_h;
                table.position_v = ctx.position_v;

                // apply moving animation
                const dx = ctx.x - this.lastX;
                const time = Date.now();
                const dt = time - this.lastTime;
                const speed = dx / dt;
                const THRESHOLD = 0.4;
                if (speed > THRESHOLD) {
                    ctx.addClass(ctx.element, "rotate_right");
                    ctx.removeClass(ctx.element, "rotate_left");
                } else if (speed < -THRESHOLD) {
                    ctx.addClass(ctx.element, "rotate_left");
                    ctx.removeClass(ctx.element, "rotate_right");
                } else {
                    ctx.removeClass(ctx.element, "rotate_left");
                    ctx.removeClass(ctx.element, "rotate_right");
                }
                this.lastX = ctx.x;
                this.lastTime = time;

                // apply border to intersecting tables
                table.isIntersecting = Boolean(findIntersectingTable(ctx.element));
            },
            onDrop: ({ element, position_h, position_v }) => {
                const table = getPosTable(element);
                setTimeout(() => {
                    table.isIntersecting = false;
                    const interesectingTableElem = findIntersectingTable(element);
                    if (interesectingTableElem) {
                        const oToTrans = this.pos.getActiveOrdersOnTable(table)[0];
                        if (oToTrans) {
                            this.pos.orderToTransferUuid = oToTrans.uuid;
                            oToTrans.setBooked(true);
                            this.pos.transferTable(table);
                        }
                        this.pos.data.write("restaurant.table", [table.id], {
                            parent_id: getPosTable(interesectingTableElem).id,
                            ...table.uiState.initialPosition,
                        });
                    } else {
                        this.pos.data.write("restaurant.table", [table.id], {
                            position_h,
                            position_v,
                        });
                    }
                }, 1.1 * parseFloat(element.style.transitionDuration));
                this.state.isMovingTable = false;
            },
        });
        useDraggable({
            ref: this.map,
            elements: "span.table-handle",
            onDrag: (ctx) => {
                // FIXME: this function runs too often so we need to debounce it, find a better way to do it
                const time = Date.now();
                if (time - this.lastTime < 25) {
                    return;
                }
                this.lastTime = time;
                const table = getPosTable(ctx.element.parentElement);
                const newPosition = {
                    minX: table.position_h,
                    minY: table.position_v,
                    maxX: table.position_h + table.width,
                    maxY: table.position_v + table.height,
                };
                const dx =
                    ctx.x - ctx.getRect(ctx.element).left - ctx.getRect(ctx.element).width / 2;
                const dy =
                    ctx.y - ctx.getRect(ctx.element).top - ctx.getRect(ctx.element).height / 2;

                const limits = getLimits(ctx.element.parentElement, this.map.el);
                const MIN_TABLE_SIZE = 30;
                const bounds = {
                    maxX: [table.position_h + MIN_TABLE_SIZE, limits.maxX + table.width],
                    minX: [limits.minX, newPosition.maxX - MIN_TABLE_SIZE],
                    maxY: [table.position_v + MIN_TABLE_SIZE, limits.maxY + table.height],
                    minY: [limits.minY, newPosition.maxY - MIN_TABLE_SIZE],
                };
                const moveX = ctx.element.classList.contains("left") ? "minX" : "maxX";
                const moveY = ctx.element.classList.contains("top") ? "minY" : "maxY";
                newPosition[moveX] = constrain(newPosition[moveX] + dx, ...bounds[moveX]);
                newPosition[moveY] = constrain(newPosition[moveY] + dy, ...bounds[moveY]);

                table.position_h = newPosition.minX;
                table.position_v = newPosition.minY;
                table.width = newPosition.maxX - newPosition.minX;
                table.height = newPosition.maxY - newPosition.minY;
            },
            onDrop: (ctx) => {
                const table = getPosTable(ctx.element.parentElement);
                this.pos.data.write(
                    "restaurant.table",
                    [table.id],
                    pick(table, "position_h", "position_v", "width", "height")
                );
            },
        });
    }
    getTableDropdownState(table) {
        return withComputedProperties(
            {
                open: () => (this.state.tableDropdownId = table.id),
                close: () => (this.state.tableDropdownId = null),
            },
            [this.state],
            {
                isOpen(state) {
                    return state.tableDropdownId === table.id;
                },
            }
        );
    }
    getFloorDropdownState(floor) {
        return withComputedProperties(
            {
                open: () => (this.state.floorDropdownId = floor.id),
                close: () => (this.state.floorDropdownId = null),
            },
            [this.state],
            {
                isOpen(state) {
                    return state.floorDropdownId === floor.id;
                },
            }
        );
    }
    getTableHandleOffset(table) {
        // min(width/2, height/2) is the real border radius
        // 0.2929 is (1 - cos(45°)) to get in the middle of the border's arc
        return table.shape === "round"
            ? -12 + Math.min(table.width / 2, table.height / 2) * 0.2929
            : -12;
    }
    unlinkTables(table) {
        this.pos.data.write("restaurant.table", [table.id], {
            parent_id: null,
        });
        for (const t of table.getChildren()) {
            this.unlinkTables(t);
        }
    }
    async onWillStart() {
        this.pos.searchProductWord = "";
        const table = this.pos.selectedTable;
        const tableByIds = this.pos.models["restaurant.table"].getAllBy("id");
        if (table) {
            const orders = this.pos.get_open_orders();
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
        return this.state.floor.floor_background_image
            ? "data:image/png;base64," + this.state.floor.floor_background_image
            : "none";
    }
    async createTable(copyTable, duplicateFloor = false) {
        const existingTable = this.state.floor.table_ids;
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
                active: true,
                position_v: posV,
                position_h: posH,
                width: widthTable,
                height: heightTable,
                shape: "square",
                seats: 2,
                color: "rgb(53, 211, 116)",
                floor_id: this.state.floor.id,
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
    get activeTables() {
        return this.state.floor?.table_ids;
    }
    async onClickTable(table, ev) {
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
                const orders = this.pos.getTableOrders(table.id);
                if (orders.length > 0) {
                    this.pos.set_order(orders[0]);
                    this.pos.orderToTransferUuid = null;
                    this.pos.showScreen(orders[0].get_screen_data().name);
                } else {
                    this.pos.add_new_order();
                    this.pos.showScreen("ProductScreen");
                }
            }
        }
    }
    onFloorRightClick(floor, ev) {
        ev?.preventDefault?.();
        this.state.floorDropdownId = floor.id;
    }
    onTableRightClick(table, ev) {
        ev?.preventDefault?.();
        this.state.tableDropdownId = table.id;
    }
    async addTableOrFloor() {
        this.dialog.add(SelectionPopup, {
            list: [
                {
                    id: 1,
                    label: _t("New Table"),
                    item: "table",
                },
                {
                    id: 2,
                    label: _t("New Floor"),
                    item: "floor",
                },
            ],
            getPayload: async (selected) => {
                if (selected === "table") {
                    this.createTable();
                    return;
                }
                this.dialog.add(TextInputPopup, {
                    title: _t("New Floor"),
                    placeholder: _t("Floor name"),
                    getPayload: async (newName) => {
                        const floor = await this.pos.data.create(
                            "restaurant.floor",
                            [
                                {
                                    name: newName,
                                    background_color: "#FFFFFF",
                                    pos_config_ids: [this.pos.config.id],
                                },
                            ],
                            false
                        );

                        this.state.floor = floor[0];
                    },
                });
            },
        });
    }
    async duplicateFloor(floor) {
        const tables = this.state.floor.table_ids;
        const newFloorName = floor.name + " (copy)";
        const copyFloor = await this.pos.data.create("restaurant.floor", [
            {
                name: newFloorName,
                background_color: "#ACADAD",
                pos_config_ids: [this.pos.config.id],
            },
        ]);

        this.state.floor = copyFloor[0];

        for (const table of tables) {
            const tableSerialized = table.serialize({ orm: true });
            tableSerialized.floor_id = copyFloor[0].id;
            await this.createTableFromRaw(tableSerialized);
        }
        return;
    }
    async rename(item) {
        this.dialog.add(TextInputPopup, {
            startingValue: item.name,
            title: _t("New Name ?"),
            getPayload: (name) => {
                if (name !== item.name) {
                    this.pos.data.write(item.model.modelName, [item.id], { name });
                }
            },
        });
    }
    async changeSeatsNum(table) {
        this.dialog.add(NumberPopup, {
            title: _t("Number of Seats?"),
            getPayload: (num) => {
                this.pos.data.write("restaurant.table", [table.id], {
                    seats: parseInt(num, 10),
                });
            },
        });
    }
    stopOrderTransfer() {
        const order = this.pos.models["pos.order"].getBy("uuid", this.pos.orderToTransferUuid);
        this.pos.set_order(order);
        this.pos.showScreen("ProductScreen");
        this.pos.orderToTransferUuid = null;
    }
    toggleShape(table) {
        this.pos.data.write("restaurant.table", [table.id], {
            shape: table.shape === "round" ? "square" : "round",
        });
    }
    setTableColor(table, color) {
        this.state.tableDropdownId = null;
        this.pos.data.write("restaurant.table", [table.id], { color: color });
    }
    setFloorColor(floor, background_color) {
        this.state.floorDropdownId = null;
        this.pos.data.write("restaurant.floor", [floor.id], {
            background_color,
            floor_background_image: false,
        });
        this.state.floor = floor;
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
    async deleteFloor(floor) {
        const confirmed = await ask(this.dialog, {
            title: `Removing floor ${floor.name}`,
            body: sprintf(
                _t("Removing a floor cannot be undone. Do you still want to remove %s?"),
                floor.name
            ),
        });
        if (!confirmed) {
            return;
        }
        try {
            await this.pos.data.call("restaurant.floor", "deactivate_floor", [
                floor.id,
                this.pos.session.id,
            ]);
        } catch {
            this.dialog.add(AlertDialog, {
                title: _t("Delete Error"),
                body: _t("You cannot delete a floor with orders still in draft for this floor."),
            });
            return;
        }

        const orderList = [...this.pos.get_order_list()];
        for (const order of orderList) {
            if (floor.table_ids.includes(order.tableId)) {
                this.pos.removeOrder(order, false);
            }
        }

        for (const table_id of floor.table_ids) {
            table_id.delete();
        }

        floor.delete();

        if (this.pos.models["restaurant.floor"].length > 0) {
            this.state.floor = this.pos.models["restaurant.floor"].getAll()[0];
        } else {
            this.pos.floorPlanStyle = "default";
        }
    }
    async deleteTable(table) {
        const confirmed = await ask(this.dialog, {
            title: _t("Are you sure?"),
            body: _t("Removing a table cannot be undone"),
        });
        if (!confirmed) {
            return;
        }
        const records = await this.pos.data.write("restaurant.table", [table.id], {
            active: false,
        });
        if (records) {
            records[0].delete();
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

    changeImage(ev) {
        const file = ev.target.files[0];
        this.state.floorDropdownId = null;
        return this.uploadImage(file);
    }
    async uploadImage(file) {
        if (!file.type.match(/image.*/)) {
            this.dialog.add(AlertDialog, {
                title: _t("Unsupported File Format"),
                body: _t("Only web-compatible Image formats such as .png or .jpeg are supported."),
            });
            return;
        }
        const imageUrl = await getDataURLFromFile(file);
        const loadedImage = await loadImage(imageUrl);
        if (loadedImage) {
            this.env.services.ui.block();
            await this.pos.data.write("restaurant.floor", [this.state.floor.id], {
                floor_background_image: imageUrl.split(",")[1],
            });
            this.env.services.ui.unblock();
        } else {
            this.dialog.add(AlertDialog, {
                title: _t("Loading Image Error"),
                body: _t("Encountered error when loading image. Please try again."),
            });
        }
    }
    getOrderCount(table) {
        // This information in uiState came by websocket
        if (table.uiState.changeCount > 0) {
            return table.uiState.changeCount;
        }
        if (table.uiState.skipCount > 0) {
            return table.uiState.skipCount;
        }

        // If the table is not synced, we need to count the unsynced orders
        const orderCount = new Set();
        const tableOrders = this.pos.models["pos.order"].filter(
            (o) => o.table_id?.id === table.id && !o.finalized
        );

        table.uiState.orderCount = tableOrders.length;
        for (const order of tableOrders) {
            const changes = getOrderChanges(order, false, this.pos.orderPreparationCategories);
            table.uiState.changeCount += changes.nbrOfChanges;
        }

        return table.uiState.orderCount + orderCount.size || 0;
    }
}

registry.category("pos_screens").add("FloorScreen", FloorScreen);
