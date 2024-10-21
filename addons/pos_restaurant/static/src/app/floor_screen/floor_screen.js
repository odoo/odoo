import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";
import { debounce } from "@web/core/utils/timing";
import { registry } from "@web/core/registry";

import { TextInputPopup } from "@point_of_sale/app/utils/input_popups/text_input_popup";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import {
    Component,
    onMounted,
    useRef,
    useState,
    onWillStart,
    useEffect,
    useExternalListener,
} from "@odoo/owl";
import { ask } from "@point_of_sale/app/store/make_awaitable_dialog";
import { loadImage } from "@point_of_sale/utils";
import { getDataURLFromFile } from "@web/core/utils/urls";
import { hasTouch } from "@web/core/browser/feature_detection";
import {
    getButtons,
    DECIMAL,
    ZERO,
    BACKSPACE,
} from "@point_of_sale/app/generic_components/numpad/numpad";
import { makeDraggableHook } from "@web/core/utils/draggable_hook_builder_owl";
import { pick } from "@web/core/utils/objects";
import { getOrderChanges } from "@point_of_sale/app/models/utils/order_change";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useTrackedAsync } from "@point_of_sale/app/utils/hooks";

function constrain(num, min, max) {
    return Math.min(Math.max(num, min), max);
}
/**
 * Gives the minimum and maximum x and y value for an element to prevent it from
 * overflowing outside of another element.
 *
 * @param {HTMLElement} el the element for which we want to get the position
 *  limits
 * @param {HTMLElement} limitEl the element outside of which the main element
 *  shouldn't overflow
 * @returns {{ minX: number, maxX: number, minY: number, maxY: number }} limits
 */
function getLimits(el, limitEl) {
    const limitRect = limitEl.getBoundingClientRect();
    const offsetParentRect = el.offsetParent.getBoundingClientRect();
    return {
        minX: limitRect.left - offsetParentRect.left,
        maxX: limitRect.left - offsetParentRect.left + limitRect.width,
        minY: limitRect.top - offsetParentRect.top,
        maxY: limitRect.top - offsetParentRect.top + limitRect.height,
    };
}
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
const useDraggable = makeDraggableHook({
    name: "useDraggable",
    onComputeParams({ ctx }) {
        ctx.followCursor = false;
    },
    onWillStartDrag: ({ ctx }) => pick(ctx.current, "element"),
    onDragStart: ({ ctx }) => pick(ctx.current, "element"),
    onDrag: ({ ctx }) => pick(ctx.current, "element"),
    onDrop: ({ ctx }) => pick(ctx.current, "element"),
});

const GRID_SIZE = 10;

export class FloorScreen extends Component {
    static components = { Dropdown, DropdownItem };
    static template = "pos_restaurant.FloorScreen";
    static props = { floor: { type: true, optional: true } };
    static storeOnOrder = false;

    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.ui = useService("ui");
        const floor = this.pos.currentFloor;
        this.state = useState({
            selectedFloorId: floor ? floor.id : null,
            floorHeight: "100%",
            floorWidth: "100%",
            selectedTableIds: [],
            potentialLink: null,
        });

        this.doCreateTable = useTrackedAsync(async () => {
            await this.createTable();
        });
        this.floorMapRef = useRef("floor-map-ref");
        this.floorScrollBox = useRef("floor-map-scroll");
        this.map = useRef("map");
        this.alert = useService("alert");
        const getTableElem = (table) => {
            return this.map.el.querySelector(`.tableId-${table.id}`);
        };
        const findIntersectingTableElem = (tableElem) => {
            const table = this.getPosTable(tableElem);
            return [...tableElem.parentElement.getElementsByClassName("table")].find(
                (t) =>
                    t !== tableElem &&
                    areElementsIntersecting(t, tableElem) &&
                    !table.isParent(this.getPosTable(t))
            );
        };
        const TABLE_LINKING_DELAY = 400;
        let offsetX, offsetY;
        const suggestLinkingPositions = () =>
            this.state.potentialLink?.parent &&
            this.state.potentialLink.time + TABLE_LINKING_DELAY < Date.now();

        useExternalListener(window, "keydown", (ev) => {
            const overlayElements = document.querySelectorAll(".o-overlay-item");
            if (
                overlayElements.length == 0 &&
                ev.key === "Escape" &&
                this.pos.isEditMode &&
                this.state.selectedTableIds.length == 0 &&
                !this.state.potentialLink
            ) {
                this.pos.isEditMode = false;
            }
        });
        useDraggable({
            ref: this.map,
            elements: ".table",
            ignore: "span.table-handle",
            enabled: !this.pos.isEditMode,
            onDragStart: (ctx) => {
                ctx.addClass(ctx.element, "shadow");
                if (this.pos.isEditMode) {
                    return;
                }
                const table = this.getPosTable(ctx.element);
                this.state.potentialLink = { child: table };
                table.uiState.initialPosition = pick(table, "position_h", "position_v");
                // This helps when unlinking tables ( to keep the position )
                table.position_h = table.getX();
                table.position_v = table.getY();
                if (table.parent_id) {
                    this.pos.data.write("restaurant.table", [table.id], {
                        parent_id: null,
                    });
                }
            },
            onWillStartDrag: ({ element, x, y }) => {
                offsetX = x - element.getBoundingClientRect().left;
                offsetY = y - element.getBoundingClientRect().top;
            },
            onDrag: ({ element, x, y }) => {
                const table = this.getPosTable(element);
                if (!suggestLinkingPositions()) {
                    table.position_h =
                        x - offsetX + this.map.el.parentElement.parentElement.scrollLeft;
                    table.position_v = y - offsetY - this.map.el.getBoundingClientRect().top;
                    if (this.pos.isEditMode && !this.activeFloor.floor_background_image) {
                        table.position_h -= table.position_h % GRID_SIZE;
                        table.position_v -= table.position_v % GRID_SIZE;
                    }
                    if (this.pos.isEditMode || this.state.potentialLink?.parent) {
                        return;
                    }
                    const potentialParentElem = findIntersectingTableElem(element);
                    if (!potentialParentElem) {
                        this.alert.add("Link Table");
                        return;
                    }
                    this.state.potentialLink = {
                        child: table,
                        parent: this.getPosTable(potentialParentElem),
                        time: Date.now(),
                    };
                    this.alert.add(
                        `Link Table ${table.table_number} with ${this.state.potentialLink.parent.table_number}`
                    );
                    return;
                }
                const { child, parent } = this.state.potentialLink;
                const { left, top, width, height } = getTableElem(parent).getBoundingClientRect();
                const dx = x - left - width / 2;
                const dy = y - top - height / 2;
                if (
                    Math.abs(dx) > parent.width / 2 + child.width / 2 ||
                    Math.abs(dy) > parent.height / 2 + child.height / 2
                ) {
                    this.state.potentialLink = { child: table };
                    return;
                }
                table.setPositionAsIfLinked(
                    this.state.potentialLink.parent,
                    Math.abs(dx) > Math.abs(dy)
                        ? dx > 0
                            ? "left"
                            : "right"
                        : dy < 0
                        ? "top"
                        : "bottom"
                );
            },
            onDrop: ({ element }) => {
                this.alert.dismiss();
                const table = this.getPosTable(element);
                if (this.pos.isEditMode) {
                    this.pos.data.write("restaurant.table", [table.id], {
                        position_h: table.position_h,
                        position_v: table.position_v,
                    });
                    return;
                }
                table.position_h = table.uiState.initialPosition.position_h;
                table.position_v = table.uiState.initialPosition.position_v;
                if (!suggestLinkingPositions()) {
                    this.state.potentialLink = null;
                    return;
                }
                const oToTrans = this.pos.getActiveOrdersOnTable(table)[0];
                if (oToTrans) {
                    this.pos.transferOrder(oToTrans.uuid, this.state.potentialLink.parent);
                }
                this.pos.data.write("restaurant.table", [table.id], {
                    parent_id: this.state.potentialLink.parent.id,
                });
                this.state.potentialLink = null;
            },
        });
        this.useResizeHook();
        onMounted(() => {
            this.pos.openOpeningControl();
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
                        this.floorScrollBox.el.classList.remove("overflow-auto");
                        this.floorScrollBox.el.classList.add("overflow-hidden");
                    } else {
                        this.floorScrollBox.el.classList.remove("overflow-hidden");
                        this.floorScrollBox.el.classList.add("overflow-auto");
                    }
                }
            },
            () => [this.state.selectedTableIds.length]
        );
    }
    getPosTable(el) {
        return this.pos.getTableFromElement(el);
    }
    useResizeHook() {
        let startX, startY;
        let startPosH, startPosV, startWidth, startHeight;
        let table;
        useDraggable({
            ref: this.map,
            elements: "span.table-handle",
            onDragStart: (ctx) => {
                table = this.getPosTable(ctx.element.parentElement);
                startX = ctx.x;
                startY = ctx.y;
                startPosH = table.position_h;
                startPosV = table.position_v;
                startWidth = table.width;
                startHeight = table.height;
            },
            onDrag: (ctx) => {
                const newPosition = {
                    minX: startPosH,
                    minY: startPosV,
                    maxX: startPosH + startWidth,
                    maxY: startPosV + startHeight,
                };
                const dx = ctx.x - startX;
                const dy = ctx.y - startY;
                const limits = getLimits(ctx.element.parentElement, this.map.el);
                const MIN_TABLE_SIZE = 30;
                const bounds = {
                    maxX: [startPosH + MIN_TABLE_SIZE, limits.maxX + startWidth],
                    minX: [limits.minX, newPosition.maxX - MIN_TABLE_SIZE],
                    maxY: [startPosV + MIN_TABLE_SIZE, limits.maxY + startHeight],
                    minY: [limits.minY, newPosition.maxY - MIN_TABLE_SIZE],
                };
                const moveX = ctx.element.classList.contains("left") ? "minX" : "maxX";
                const moveY = ctx.element.classList.contains("top") ? "minY" : "maxY";
                newPosition[moveX] = constrain(newPosition[moveX] + dx, ...bounds[moveX]);
                newPosition[moveY] = constrain(newPosition[moveY] + dy, ...bounds[moveY]);
                if (!this.activeFloor.floor_background_image) {
                    newPosition[moveX] -= newPosition[moveX] % GRID_SIZE;
                    newPosition[moveY] -= newPosition[moveY] % GRID_SIZE;
                }
                table.position_h = newPosition.minX;
                table.position_v = newPosition.minY;
                table.width = newPosition.maxX - newPosition.minX;
                table.height = newPosition.maxY - newPosition.minY;
            },
            onDrop: (ctx) => {
                const table = this.getPosTable(ctx.element.parentElement);
                this.pos.data.write(
                    "restaurant.table",
                    [table.id],
                    pick(table, "position_h", "position_v", "width", "height")
                );
            },
        });
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
    async onWillStart() {
        this.pos.searchProductWord = "";
        await this.pos.unsetTable();
    }
    get floorBackround() {
        return this.activeFloor.floor_background_image
            ? "data:image/png;base64," + this.activeFloor.floor_background_image
            : "none";
    }
    getTableHandleOffset(table) {
        // min(width/2, height/2) is the real border radius
        // 0.2929 is (1 - cos(45°)) to get in the middle of the border's arc
        return table.shape === "round"
            ? -12 + Math.min(table.width / 2, table.height / 2) * 0.2929
            : -12;
    }
    onClickFloorMap(ev) {
        if (ev.target.closest(".table")) {
            return;
        }
        for (const tableId of this.state.selectedTableIds) {
            const table = this.pos.models["restaurant.table"].get(tableId);
            this.pos.data.write("restaurant.table", [tableId], {
                ...table.serialize({ orm: true }),
            });
        }
        this.state.selectedTableIds = [];
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
    _getNewTableNumber() {
        let firstNum = 1;
        const tablesNumber = this.activeTables
            .map((table) => table.table_number)
            .sort(function (a, b) {
                return a - b;
            });

        for (let i = 0; i < tablesNumber.length; i++) {
            if (tablesNumber[i] == firstNum) {
                firstNum += 1;
            } else {
                break;
            }
        }
        return firstNum;
    }
    get activeFloor() {
        return this.state.selectedFloorId
            ? this.pos.models["restaurant.floor"].get(this.state.selectedFloorId)
            : null;
    }
    get activeTables() {
        return this.activeFloor?.table_ids;
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
                            background_color: "#FFFFFF",
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

        this.selectFloor(copyFloor[0]);
        this.pos.isEditMode = true;

        for (const table of tables) {
            const tableSerialized = table.serialize({ orm: true });
            tableSerialized.floor_id = copyFloor[0].id;
            await this.createTableFromRaw(tableSerialized);
        }
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

    setFloorColor(color) {
        this.activeFloor.background_color = color;
        this.pos.data.write("restaurant.floor", [this.activeFloor.id], {
            background_color: color,
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
    async deleteFloor() {
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
                body: _t("You cannot delete a floor with orders still in draft for this floor."),
            });
            return;
        }

        const orderList = [...this.pos.get_open_orders()];
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
                    for (const order of this.pos.get_open_orders()) {
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
            changeCount += this.getChangeCount(table) || 0;
        }

        return changeCount;
    }
    getChildren(table) {
        return this.pos.models["restaurant.table"].filter((t) => t.parent_id?.id === table.id);
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
        let skipCount = 0;
        const tableOrders = this.pos.models["pos.order"].filter(
            (o) => o.table_id?.id === table.id && !o.finalized
        );

        for (const order of tableOrders) {
            const changes = getOrderChanges(order, false, this.pos.orderPreparationCategories);
            changeCount += changes.nbrOfChanges;
            skipCount += changes.nbrOfSkipped;
        }

        return { changes: changeCount, skip: skipCount };
    }
    setColor(hasSelectedTable, color) {
        if (hasSelectedTable) {
            return this.setTableColor(color);
        } else {
            return this.setFloorColor(color);
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
}

registry.category("pos_screens").add("FloorScreen", FloorScreen);
