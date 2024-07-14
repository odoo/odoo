/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import {
    Component,
    onWillRender,
    onWillUpdateProps,
    reactive,
    toRaw,
    useExternalListener,
    useRef,
    useState,
} from "@odoo/owl";
import { hasTouch, isMobileOS } from "@web/core/browser/feature_detection";
import { Domain } from "@web/core/domain";
import { is24HourFormat, formatDateTime, serializeDate, serializeDateTime } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { usePopover } from "@web/core/popover/popover_hook";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { useService } from "@web/core/utils/hooks";
import { omit } from "@web/core/utils/objects";
import { debounce, throttleForAnimation } from "@web/core/utils/timing";
import { url } from "@web/core/utils/urls";
import { useVirtual } from "@web/core/virtual_hook";
import { formatFloatTime } from "@web/views/fields/formatters";
import { useViewCompiler } from "@web/views/view_compiler";
import { ViewScaleSelector } from "@web/views/view_components/view_scale_selector";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { GanttCompiler } from "./gantt_compiler";
import { GanttConnector } from "./gantt_connector";
import {
    dateAddFixedOffset,
    getCellColor,
    getColorIndex,
    useGanttConnectorDraggable,
    useGanttDraggable,
    useGanttResizable,
    useGanttUndraggable,
    useMultiHover,
} from "./gantt_helpers";
import { GanttPopover } from "./gantt_popover";
import { GanttResizeBadge } from "./gantt_resize_badge";
import { GanttRowProgressBar } from "./gantt_row_progress_bar";
import { computeRange } from "./gantt_model";
import { browser } from "@web/core/browser/browser";

const { DateTime } = luxon;

/**
 * @typedef {`__column__${number}`} ColumnId
 * @typedef {`__connector__${number | "new"}`} ConnectorId
 * @typedef {import("./gantt_connector").ConnectorProps} ConnectorProps
 * @typedef {luxon.DateTime} DateTime
 * @typedef {"copy" | "reschedule"} DragActionMode
 * @typedef {"drag" | "locked" | "resize"} InteractionMode
 * @typedef {`__pill__${number}`} PillId
 * @typedef {import("./gantt_model").RowId} RowId
 *
 * @typedef Column
 * @property {ColumnId} id
 * @property {GridPosition} grid
 * @property {boolean} [isToday]
 * @property {DateTime} start
 * @property {DateTime} stop
 *
 * @typedef GridPosition
 * @property {number | number[]} [row]
 * @property {number | number[]} [column]
 *
 * @typedef Group
 * @property {boolean} break
 * @property {number} col
 * @property {Pill[]} pills
 * @property {number} aggregateValue
 * @property {GridPosition} grid
 *
 * @typedef GanttRendererProps
 * @property {import("./gantt_model").GanttModel} model
 * @property {Document} arch
 * @property {string} class
 * @property {(context: Record<string, any>)} create
 * @property {{ content?: Point }} [scrollPosition]
 * @property {{ el: HTMLDivElement | null }} [contentRef]
 *
 * @typedef HoveredInfo
 * @property {Element | null} connector
 * @property {HTMLElement | null} hoverable
 * @property {HTMLElement | null} pill
 *
 * @typedef Interaction
 * @property {InteractionMode | null} mode
 * @property {DragActionMode} dragAction
 *
 * @typedef Pill
 * @property {PillId} id
 * @property {boolean} disableStartResize
 * @property {boolean} disableStopResize
 * @property {boolean} highlighted
 * @property {number} leftMargin
 * @property {number} level
 * @property {string} name
 * @property {DateTime} startDate
 * @property {DateTime} stopDate
 * @property {GridPosition} grid
 * @property {RelationalRecord} record
 * @property {number} _color
 * @property {number} _progress
 *
 * @typedef Point
 * @property {number} [x]
 * @property {number} [y]
 *
 * @typedef {Record<string, any>} RelationalRecord
 * @property {number | false} id
 *
 * @typedef ResizeBadge
 * @property {Point & { right?: number }} position
 * @property {number} diff
 * @property {string} scale
 *
 * @typedef {import("./gantt_model").Row & {
 *  grid: GridPosition,
 *  pills: Pill[],
 *  cellColors?: Record<string, string>,
 *  thumbnailUrl?: string
 * }} Row
 *
 * @typedef SubColumn
 * @property {ColumnId} columnId
 * @property {boolean} [isToday]
 * @property {DateTime} start
 * @property {DateTime} stop
 */

/** @type {[Omit<InteractionMode, "drag"> | DragActionMode, string][]} */
const INTERACTION_CLASSNAMES = [
    ["connect", "o_connect"],
    ["copy", "o_copying"],
    ["locked", "o_grabbing_locked"],
    ["reschedule", "o_grabbing"],
    ["resize", "o_resizing"],
];
const NEW_CONNECTOR_ID = "__connector__new";

/**
 * Gantt Renderer
 *
 * @extends {Component<GanttRendererProps, any>}
 */
export class GanttRenderer extends Component {
    static components = {
        GanttConnector,
        GanttResizeBadge,
        GanttRowProgressBar,
        Popover: GanttPopover,
        ViewScaleSelector,
    };
    static props = [
        "model",
        "arch",
        "class",
        "create",
        "openDialog",
        "scrollPosition?",
        "contentRef?",
    ];

    static template = "web_gantt.GanttRenderer";
    static connectorCreatorTemplate = "web_gantt.GanttRenderer.ConnectorCreator";
    static headerTemplate = "web_gantt.GanttRenderer.Header";
    static pillTemplate = "web_gantt.GanttRenderer.Pill";
    static rowContentTemplate = "web_gantt.GanttRenderer.RowContent";
    static rowHeaderTemplate = "web_gantt.GanttRenderer.RowHeader";
    static totalRowTemplate = "web_gantt.GanttRenderer.TotalRow";

    static GRID_ROW_HEIGHT = 4; // Pixels
    static GROUP_ROW_SPAN = 6; // --> 24 pixels
    static ROW_SPAN = 9; // --> 36 pixels

    static getRowHeaderWidth = (width) => 100 / (width > 768 ? 6 : 3);

    setup() {
        this.model = this.props.model;

        this.cellContainerRef = useRef("cellContainer");
        this.rootRef = useRef("root");

        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.userService = useService("user");

        this.is24HourFormat = is24HourFormat();

        /** @type {HoveredInfo} */
        this.hovered = {
            connector: null,
            hoverable: null,
            pill: null,
        };

        this.selection = {
            active: false,
        };

        this.state = useState({ rowHeaderWidth: 0 });

        /** @type {Interaction} */
        this.interaction = reactive(
            {
                mode: null,
                dragAction: "reschedule",
            },
            () => this.onInteractionChange()
        );
        this.onInteractionChange(); // Used to hook into "interaction"
        /** @type {Record<ConnectorId, ConnectorProps>} */
        this.connectors = reactive({});
        this.progressBarsReactive = reactive({ el: null });
        /** @type {ResizeBadge} */
        this.resizeBadgeReactive = reactive({});

        /** @type {Column[]} */
        this.columns = [];
        /** @type {DateTime[]} */
        this.dateGridColumns = [];
        /** @type {Pill[]} */
        this.extraPills = [];
        /** @type {Row[]} */
        this.extraRows = [];
        /** @type {Record<PillId, Pill>} */
        this.pills = {}; // mapping to retrieve pills from pill ids
        /** @type {RowId[]} */
        this.rowIds = [];
        /** @type {Row[]} */
        this.rows = [];
        /** @type {SubColumn[]} */
        this.subColumns = [];

        const position = localization.direction === "rtl" ? "bottom" : "right";
        this.popover = usePopover(this.constructor.components.Popover, { position });

        const { popoverTemplate } = this.model.metaData;
        if (popoverTemplate) {
            this.popoverTemplate = useViewCompiler(GanttCompiler, {
                popoverTemplate,
            }).popoverTemplate;
        }

        this.throttledOnPointerMove = throttleForAnimation((ev) => this.onPointerMove(ev));

        useExternalListener(window, "keydown", (ev) => this.onWindowKeyDown(ev));
        useExternalListener(window, "keyup", (ev) => this.onWindowKeyUp(ev));
        useExternalListener(window, "pointerup", (ev) => this.onSelectStop(ev));

        const computeColumnWidth = debounce(() => this.computeColumnWidth(), 100);
        useExternalListener(window, "resize", computeColumnWidth);

        useMultiHover({
            ref: this.rootRef,
            selector: ".o_gantt_group",
            related: ["data-row-id"],
            className: "o_gantt_group_hovered",
        });

        // Draggable pills
        this.cellForDrag = { el: null, part: 0 };
        const dragState = useGanttDraggable({
            enable: () => this.cellForDrag.el,
            // Refs and selectors
            ref: this.rootRef,
            hoveredCell: this.cellForDrag,
            elements: ".o_draggable",
            ignore: ".o_resize_handle,.o_connector_creator_bullet",
            cells: ".o_gantt_cell",
            // Style classes
            cellDragClassName: "o_gantt_cell o_drag_hover",
            ghostClassName: "o_dragged_pill_ghost",
            // Handlers
            onDragStart: () => {
                this.popover.close();
                this.setStickyRowFromCell(this.cellForDrag.el);
                this.interaction.mode = "drag";
            },
            onDragEnd: () => {
                this.setStickyRowFromCell(null);
                this.interaction.mode = null;
            },
            onDrop: (params) => this.dragPillDrop(params),
        });

        // Un-draggable pills
        const unDragState = useGanttUndraggable({
            // Refs and selectors
            ref: this.rootRef,
            elements: ".o_undraggable",
            ignore: ".o_resize_handle,.o_connector_creator_bullet",
            edgeScrolling: { enabled: false },
            // Handlers
            onDragStart: () => {
                this.interaction.mode = "locked";
            },
            onDragEnd: () => {
                this.interaction.mode = null;
            },
        });

        // Resizable pills
        const resizeState = useGanttResizable({
            // Refs and selectors
            ref: this.cellContainerRef,
            elements: ".o_resizable",
            innerPills: ".o_gantt_pill",
            cells: ".o_gantt_cell",
            // Other params
            handles: "o_resize_handle",
            showHandles: (pillEl) => {
                const pill = this.pills[pillEl.dataset.pillId];
                const hideHandles = this.connectorDragState.dragging;
                return {
                    start: !pill.disableStartResize && !hideHandles,
                    end: !pill.disableStopResize && !hideHandles,
                };
            },
            rtl: () => localization.direction === "rtl",
            precision: () => this.model.metaData.scale.cellPart,
            // Handlers
            onDragStart: ({ pill, addClass }) => {
                this.popover.close();
                addClass(pill, "o_resized");
                this.interaction.mode = "resize";
            },
            onDrag: ({ pill, grabbedHandle, diff }) => {
                const rect = pill.getBoundingClientRect();
                const position = { top: rect.y + rect.height };
                if (grabbedHandle === "left") {
                    position.left = rect.x;
                } else {
                    position.right = document.body.offsetWidth - rect.x - rect.width;
                }
                const { cellTime, unitDescription } = this.model.metaData.scale;
                Object.assign(this.resizeBadgeReactive, {
                    position,
                    diff: diff * cellTime,
                    scale: unitDescription,
                });
            },
            onDragEnd: ({ pill, removeClass }) => {
                delete this.resizeBadgeReactive.position;
                delete this.resizeBadgeReactive.diff;
                delete this.resizeBadgeReactive.scale;
                removeClass(pill, "o_resized");
                this.interaction.mode = null;
            },
            onDrop: (params) => this.resizePillDrop(params),
        });

        // Draggable connector
        let initialPillId;
        this.connectorDragState = useGanttConnectorDraggable({
            ref: this.rootRef,
            elements: ".o_connector_creator_bullet",
            parentWrapper: ".o_gantt_cells .o_gantt_pill_wrapper",
            onDragStart: ({ initialPosition, sourcePill, x, y, addClass }) => {
                this.popover.close();
                initialPillId = sourcePill.dataset.pillId;
                addClass(sourcePill, "o_connector_creator_lock");
                this.setConnector({
                    id: NEW_CONNECTOR_ID,
                    highlighted: true,
                    sourcePoint: { left: initialPosition.x, top: initialPosition.y },
                    targetPoint: { left: x, top: y },
                });
                this.interaction.mode = "connect";
            },
            onDrag: ({ x, y }) => {
                this.setConnector({ id: NEW_CONNECTOR_ID, targetPoint: { left: x, top: y } });
            },
            onDragEnd: () => {
                this.setConnector({ id: NEW_CONNECTOR_ID, sourcePoint: null, targetPoint: null });
                this.interaction.mode = null;
            },
            onDrop: ({ target }) => {
                if (initialPillId === target.dataset.pillId) {
                    return;
                }
                const { id: masterId } = this.pills[initialPillId].record;
                const { id: slaveId } = this.pills[target.dataset.pillId].record;
                this.model.createDependency(masterId, slaveId);
            },
        });

        this.dragStates = [dragState, unDragState, resizeState];

        onWillUpdateProps(this.computeDerivedParams);
        onWillRender(this.onWillRender);

        /** @type {Row[]} */
        this.virtualRows = useVirtual({
            getItems: () => this.rows,
            getItemHeight: (row) => this.getRowHeight(row),
            initialScroll: this.props.scrollPosition,
            scrollableRef: this.props.contentRef,
        });

        this.computeDerivedParams();
    }

    //-------------------------------------------------------------------------
    // Getters
    //-------------------------------------------------------------------------

    get isDragging() {
        return this.dragStates.some((s) => s.dragging);
    }

    /**
     * @returns {boolean}
     */
    get isTouchDevice() {
        return isMobileOS() || hasTouch();
    }

    /**
     * @returns {number}
     */
    get pillHeight() {
        return this.constructor.GRID_ROW_HEIGHT * this.constructor.ROW_SPAN;
    }

    /**
     * @returns {number}
     */
    get rowHeight() {
        return this.constructor.GRID_ROW_HEIGHT;
    }

    //-------------------------------------------------------------------------
    // Methods
    //-------------------------------------------------------------------------

    /**
     * @param {Pill} pill
     * @param {Group} group
     */
    addTo(pill, group) {
        group.pills.push(pill);
        group.aggregateValue++; // pill count
        return true;
    }

    /**
     * Aggregates overlapping pills in group rows.
     *
     * @param {Pill[]} pills
     */
    aggregatePills(pills) {
        /** @type {Record<number, Group>} */
        const groups = {};
        for (let col = 1; col <= this.subColumns.length; col++) {
            groups[col] = {
                break: false,
                col,
                pills: [],
                aggregateValue: 0,
                grid: { column: [col, 1] },
            };
            // group.break = true means that the group cannot be merged with the previous one
            // We will merge groups that can be merged together (if this.shouldMergeGroups returns true)
        }

        for (const pill of pills) {
            let addedInPreviousCol = false;
            let col;
            for (col = this.getFirstcol(pill); col <= this.getLastCol(pill); col++) {
                const group = groups[col];
                const added = this.addTo(pill, group);
                if (addedInPreviousCol !== added) {
                    group.break = true;
                }
                addedInPreviousCol = added;
            }
            // here col = this.getLastCol(pill) + 1
            if (addedInPreviousCol && col <= this.subColumns.length) {
                groups[col].break = true;
            }
        }

        const filteredGroups = Object.values(groups).filter((g) => g.pills.length);

        if (this.shouldMergeGroups()) {
            return this.mergeGroups(filteredGroups);
        }

        return filteredGroups;
    }

    /**
     * Compute minimal levels required to display all pills without overlapping.
     * Side effect: level key is modified in pills.
     *
     * @param {Pill[]} pills
     */
    calculatePillsLevel(pills) {
        const firstPill = pills[0];
        firstPill.level = 0;
        const levels = [
            {
                pills: [firstPill],
                maxCol: this.getLastCol(firstPill),
            },
        ];
        for (const currentPill of pills.slice(1)) {
            const lastCol = this.getLastCol(currentPill);
            for (let l = 0; l < levels.length; l++) {
                const level = levels[l];
                if (this.getFirstcol(currentPill) > level.maxCol) {
                    currentPill.level = l;
                    level.pills.push(currentPill);
                    level.maxCol = lastCol;
                    break;
                }
            }
            if (isNaN(currentPill.level)) {
                currentPill.level = levels.length;
                levels.push({
                    pills: [currentPill],
                    maxCol: lastCol,
                });
            }
        }
        return levels.length;
    }

    /**
     * Returns the column indexes which fits both given dates inside
     * @param {DateTime} start
     * @param {DateTime} end
     * @param {DateTime[]} dates
     * @returns {[number, number]}
     */
    computeColumnIndexes(start, end, dates) {
        let startIndex, endIndex;
        for (let index = 0; index < dates.length; index++) {
            if (dates[index].ts <= start) {
                startIndex = index;
            }
            if (dates[index].ts >= end) {
                endIndex = index;
                break;
            }
        }
        return [startIndex, endIndex];
    }

    computeColumns() {
        this.columns = [];
        this.subColumns = [];
        this.dateGridColumns = [];

        const { scale, startDate, stopDate } = this.model.metaData;
        const { cellPart, cellTime, interval, time } = scale;
        const now = DateTime.local();
        let cellIndex = 1;
        let colOffset = 1;
        let date;
        for (date = startDate; date <= stopDate; date = date.plus({ [interval]: 1 })) {
            const start = date;
            const stop = date.endOf(interval);
            const index = cellIndex++;
            const columnId = `__column__${index}`;
            const column = {
                id: columnId,
                grid: { column: [colOffset, cellPart] },
                start,
                stop,
            };
            const isToday =
                (["week", "month"].includes(scale.id) && date.hasSame(now, "day")) ||
                (scale.id === "year" && date.hasSame(now, "month")) ||
                (scale.id === "day" && date.hasSame(now, "hour"));

            if (isToday) {
                column.isToday = true;
            }

            this.columns.push(column);

            for (let i = 0; i < cellPart; i++) {
                const subCellStart = dateAddFixedOffset(start, { [time]: i * cellTime });
                const subCellStop = dateAddFixedOffset(start, {
                    [time]: (i + 1) * cellTime,
                    seconds: -1,
                });
                this.subColumns.push({ start: subCellStart, stop: subCellStop, isToday, columnId });
                this.dateGridColumns.push(subCellStart);
            }

            colOffset += cellPart;
        }

        this.dateGridColumns.push(date);
    }

    computeColumnWidth() {
        const { cellPart } = this.model.metaData.scale;
        const subColumnCount = this.columns.length * cellPart;
        const totalWidth = browser.innerWidth;
        const rowHeaderWidthPercentage = this.constructor.getRowHeaderWidth(totalWidth);
        const cellContainerWidthPercentage = 100 - rowHeaderWidthPercentage;
        let cellContainerWidth = totalWidth * (cellContainerWidthPercentage / 100);
        cellContainerWidth = Math.round(cellContainerWidth / subColumnCount) * subColumnCount;
        this.state.rowHeaderWidth = totalWidth - cellContainerWidth;
        this.state.pillsWidth = cellContainerWidth / subColumnCount;
    }

    computeDerivedParams() {
        const { rows: modelRows } = this.model.data;

        if (this.shouldRenderConnectors()) {
            /** @type {Record<number, { masterIds: number[], pills: Record<RowId, Pill> }>} */
            this.mappingRecordToPillsByRow = {};
            /** @type {Record<RowId, Record<number, Pill>>} */
            this.mappingRowToPillsByRecord = {};
            /** @type {Record<ConnectorId, { sourcePillId: PillId, targetPillId: PillId }>} */
            this.mappingConnectorToPills = {};
            /** @type {Record<PillId, ConnectorId>} */
            this.mappingPillToConnectors = {};
        }

        this.topOffset = 0;
        this.nextPillId = 1;

        this.pills = {}; // mapping to retrieve pills from pill ids
        this.rows = [];
        this.rowIds = [];

        this.computeColumns();
        this.computeColumnWidth();

        const prePills = this.getPills();

        let pillsToProcess = [...prePills];
        for (const row of modelRows) {
            const result = this.processRow(row, pillsToProcess);
            this.rows.push(...result.rows);
            pillsToProcess = result.pillsToProcess;
        }

        this.gridTemplate = this.computeGrid(this.rows, this.columns);

        const { displayTotalRow } = this.model.metaData;
        if (displayTotalRow) {
            this.totalRow = this.getTotalRow(prePills);
        }

        if (this.shouldRenderConnectors()) {
            this.initializeConnectors();
            this.generateConnectors();
        }
    }

    /**
     * @param {PointerEvent} ev
     */
    computeDerivedParamsFromHover(ev) {
        const { scale } = this.model.metaData;

        const { connector, hoverable, pill } = this.hovered;

        // Update cell in drag
        const isCellHovered = hoverable?.matches(".o_gantt_cell");
        this.cellForDrag.el = isCellHovered ? hoverable : null;
        this.cellForDrag.part = 0;
        if (isCellHovered && scale.cellPart > 1) {
            const rect = hoverable.getBoundingClientRect();
            const x = Math.floor(rect.x);
            const width = Math.floor(rect.width);
            this.cellForDrag.part = Math.floor((ev.clientX - x) / (width / scale.cellPart));
        }

        if (this.isDragging) {
            this.progressBarsReactive.el = null;
            return;
        }

        if (!this.connectorDragState.dragging) {
            // Highlight connector
            const hoveredConnectorId = connector?.dataset.connectorId;
            for (const connectorId in this.connectors) {
                if (connectorId !== hoveredConnectorId) {
                    this.toggleConnectorHighlighting(connectorId, false);
                }
            }
            if (hoveredConnectorId) {
                this.progressBarsReactive.el = null;
                return this.toggleConnectorHighlighting(hoveredConnectorId, true);
            }
        }

        // Highlight pill
        const hoveredPillId = pill?.dataset.pillId;
        for (const pillId in this.pills) {
            if (pillId !== hoveredPillId) {
                this.togglePillHighlighting(pillId, false);
            }
        }
        this.togglePillHighlighting(hoveredPillId, true);

        // Update cell buttons
        if (
            this.selection.active &&
            isCellHovered &&
            Number(hoverable.dataset.columnIndex) !== this.selection.lastSelectId
        ) {
            const isUngroupedCellHovered = hoverable?.matches(".o_gantt_cell:not(.o_gantt_group)");
            if (isUngroupedCellHovered && !ev?.target.closest(".o_connector_creator")) {
                const columnIndex = Number(hoverable.dataset.columnIndex);
                const columnStart = Math.min(this.selection.initialIndex, columnIndex);
                const columnStop = Math.max(this.selection.initialIndex, columnIndex);
                this.selection.lastSelectId = columnIndex;
                for (const cell of this.getCellsOnRow(this.selection.rowId)) {
                    if (
                        cell.dataset.columnIndex < columnStart ||
                        cell.dataset.columnIndex > columnStop
                    ) {
                        cell.classList.remove("o_drag_hover");
                    } else {
                        cell.classList.add("o_drag_hover");
                    }
                }
            }
        }

        // Update progress bars
        this.progressBarsReactive.el = hoverable;
    }

    /**
     * @param {Row[]} rows
     * @param {Column[]} columns
     * @returns {{ rows: number, columns: number }}
     */
    computeGrid(rows, columns) {
        const { cellPart } = this.model.metaData.scale;
        return {
            rows: rows.reduce((acc, row) => acc + row.grid.row[1], 0),
            columns: columns.length * cellPart,
        };
    }

    /**
     * @param {ConnectorId} connectorId
     */
    deleteConnector(connectorId) {
        delete this.connectors[connectorId];
        delete this.mappingConnectorToPills[connectorId];
    }

    /**
     * @param {Object} params
     * @param {Element} params.pill
     * @param {Element} params.cell
     * @param {number} params.diff
     */
    async dragPillDrop({ pill, cell, diff }) {
        const { rowId } = cell.dataset;
        const { dateStartField, dateStopField, scale } = this.model.metaData;
        const { cellTime, time } = scale;
        const { record } = this.pills[pill.dataset.pillId];

        const start =
            diff && dateAddFixedOffset(record[dateStartField], { [time]: cellTime * diff });
        const stop = diff && dateAddFixedOffset(record[dateStopField], { [time]: cellTime * diff });
        const schedule = this.model.getSchedule({ rowId, start, stop });

        if (this.interaction.dragAction === "copy") {
            await this.model.copy(record.id, schedule, this.openPlanDialogCallback);
        } else {
            await this.model.reschedule(record.id, schedule, this.openPlanDialogCallback);
        }

        // If the pill lands on a closed group -> open it
        if (cell.classList.contains("o_gantt_group") && this.model.isClosed(rowId)) {
            this.model.toggleRow(rowId);
        }
    }

    /**
     * @param {Partial<Pill>} pill
     * @returns {Pill}
     */
    enrichPill(pill) {
        const { colorField, fields, pillDecorations, progressField } = this.model.metaData;

        pill.displayName = this.getDisplayName(pill);

        const classes = [];

        if (pillDecorations) {
            const pillContext = Object.assign({}, this.userService.context);
            for (const [fieldName, value] of Object.entries(pill.record)) {
                const field = fields[fieldName];
                switch (field.type) {
                    case "date": {
                        pillContext[fieldName] = value ? serializeDate(value) : false;
                        break;
                    }
                    case "datetime": {
                        pillContext[fieldName] = value ? serializeDateTime(value) : false;
                        break;
                    }
                    default: {
                        pillContext[fieldName] = value;
                    }
                }
            }

            for (const decoration in pillDecorations) {
                const expr = pillDecorations[decoration];
                if (evaluateBooleanExpr(expr, pillContext)) {
                    classes.push(decoration);
                }
            }
        }

        if (colorField) {
            pill._color = getColorIndex(pill.record[colorField]);
            classes.push(`o_gantt_color_${pill._color}`);
        }

        if (progressField) {
            pill._progress = pill.record[progressField] || 0;
        }

        pill.className = classes.join(" ");

        return pill;
    }

    generateConnectors() {
        this.nextConnectorId = 1;
        this.setConnector({
            id: NEW_CONNECTOR_ID,
            highlighted: true,
            sourcePoint: null,
            targetPoint: null,
        });
        for (const slaveId in this.mappingRecordToPillsByRow) {
            const { masterIds, pills: slavePills } = this.mappingRecordToPillsByRow[slaveId];
            for (const masterId of masterIds) {
                if (!(masterId in this.mappingRecordToPillsByRow)) {
                    continue;
                }
                const { pills: masterPills } = this.mappingRecordToPillsByRow[masterId];
                for (const [slaveRowId, targetPill] of Object.entries(slavePills)) {
                    for (const [masterRowId, sourcePill] of Object.entries(masterPills)) {
                        if (
                            masterRowId === slaveRowId ||
                            !(
                                slaveId in this.mappingRowToPillsByRecord[masterRowId] ||
                                masterId in this.mappingRowToPillsByRecord[slaveRowId]
                            ) ||
                            Object.keys(this.mappingRecordToPillsByRow[slaveId].pills).every(
                                (rowId) =>
                                    rowId !== masterRowId &&
                                    masterId in this.mappingRowToPillsByRecord[rowId]
                            ) ||
                            Object.keys(this.mappingRecordToPillsByRow[masterId].pills).every(
                                (rowId) =>
                                    rowId !== slaveRowId &&
                                    slaveId in this.mappingRowToPillsByRecord[rowId]
                            )
                        ) {
                            const masterRecord = sourcePill.record;
                            const slaveRecord = targetPill.record;
                            this.setConnector(
                                { alert: this.getConnectorAlert(masterRecord, slaveRecord) },
                                sourcePill.id,
                                targetPill.id
                            );
                        }
                    }
                }
            }
        }
    }

    /**
     * @param {Group} group
     * @param {Group} previousGroup
     */
    getAggregateValue(group, previousGroup) {
        // both groups have the same pills by construction
        // here the aggregateValue is the pill count
        return group.aggregateValue;
    }

    /**
     * @param {number} columnStart
     * @param {number} columnStop
     */
    getColumnStartStop(columnStartIndex, columnStopIndex = columnStartIndex) {
        const { start } = this.columns[columnStartIndex];
        const { stop } = this.columns[columnStopIndex];
        return { start, stop };
    }

    /**
     *
     * @param {number} masterRecord
     * @param {number} slaveRecord
     * @returns {import("./gantt_connector").ConnectorAlert | null}
     */
    getConnectorAlert(masterRecord, slaveRecord) {
        const { dateStartField, dateStopField } = this.model.metaData;
        if (slaveRecord[dateStartField] < masterRecord[dateStopField]) {
            if (slaveRecord[dateStartField] < masterRecord[dateStartField]) {
                return "error";
            } else {
                return "warning";
            }
        }
        return null;
    }

    /**
     * @param {string} rowId
     * @returns {NodeList[]}
     */
    getCellsOnRow(rowId) {
        return this.cellContainerRef.el.querySelectorAll(
            `.o_gantt_cell[data-row-id='${CSS.escape(rowId)}']`
        );
    }

    /**
     * @param {"top"|"bottom"} vertical the vertical alignment of the connector creator
     * @returns {{ vertical: "top"|"bottom", horizontal: "left"|"right" }}
     */
    getConnectorCreatorAlignment(vertical) {
        const alignment = { vertical };
        if (localization.direction === "rtl") {
            alignment.horizontal = vertical === "top" ? "right" : "left";
        } else {
            alignment.horizontal = vertical === "top" ? "left" : "right";
        }
        return alignment;
    }

    /**
     * This function will add a 'label' property to each
     * non-consolidated pill included in the pills list.
     * This new property is a string meant to replace
     * the text displayed on a pill.
     *
     * @param {Pill} pill
     */
    getDisplayName(pill) {
        const { computePillDisplayName, dateStartField, dateStopField, scale } =
            this.model.metaData;
        const { id: scaleId } = scale;
        const { record } = pill;

        if (!computePillDisplayName) {
            return record.display_name;
        }

        const startDate = record[dateStartField];
        const stopDate = record[dateStopField];
        const yearlessDateFormat = omit(DateTime.DATE_SHORT, "year");

        const spanAccrossDays =
            stopDate.startOf("day") > startDate.startOf("day") &&
            startDate.endOf("day").diff(startDate, "hours").toObject().hours >= 3 &&
            stopDate.diff(stopDate.startOf("day"), "hours").toObject().hours >= 3;
        const spanAccrossWeeks =
            computeRange("week", stopDate).start > computeRange("week", startDate).start;
        const spanAccrossMonths = stopDate.startOf("month") > startDate.startOf("month");

        /** @type {string[]} */
        const labelElements = [];

        // Start & End Dates
        if (scaleId === "year" && !spanAccrossDays) {
            labelElements.push(startDate.toLocaleString(yearlessDateFormat));
        } else if (
            (scaleId === "day" && spanAccrossDays) ||
            (scaleId === "week" && spanAccrossWeeks) ||
            (scaleId === "month" && spanAccrossMonths) ||
            (scaleId === "year" && spanAccrossDays)
        ) {
            labelElements.push(startDate.toLocaleString(yearlessDateFormat));
            labelElements.push(stopDate.toLocaleString(yearlessDateFormat));
        }

        // Start & End Times
        if (record.allocated_hours && !spanAccrossDays && ["week", "month"].includes(scaleId)) {
            const durationStr = formatFloatTime(record.allocated_hours, {
                noLeadingZeroHour: true,
            }).replace(/(:00|:)/g, "h");
            labelElements.push(
                startDate.toFormat("t"),
                `${stopDate.toFormat("t")} (${durationStr})`
            );
        }

        // Original Display Name
        if (scaleId !== "month" || !record.allocated_hours || spanAccrossDays) {
            labelElements.push(record.display_name);
        }

        return labelElements.filter((el) => !!el).join(" - ");
    }

    /**
     * @param {Pill} pill
     * @returns {number}
     */
    getFirstcol(pill) {
        return pill.grid.column[0];
    }

    /**
     * @returns {string}
     */
    getFormattedFocusDate() {
        const { focusDate, scale } = this.model.metaData;
        const { format, id: scaleId } = scale;
        switch (scaleId) {
            case "day":
            case "month":
            case "year":
                return formatDateTime(focusDate, { format });
            case "week": {
                const { startDate, stopDate } = this.model.metaData;
                const start = formatDateTime(startDate, { format });
                const stop = formatDateTime(stopDate, { format });
                return `${start} - ${stop}`;
            }
            default:
                throw new Error(`Unknown scale id "${scaleId}".`);
        }
    }

    /**
     * @param {Pill} pill
     */
    getGroupPillDisplayName(pill) {
        return pill.aggregateValue;
    }

    /**
     * @param {{ column?: number | number[], row?: number | number[] }} position
     */
    getGridPosition(position) {
        const style = [];
        for (const prop of ["column", "row"]) {
            const [index, span] = Array.isArray(position[prop]) ? position[prop] : [position[prop]];
            if (span && span !== 1) {
                if (span === -1) {
                    style.push(`grid-${prop}:${index} / -1`);
                } else {
                    style.push(`grid-${prop}:${index} / span ${span}`);
                }
            } else if (index) {
                style.push(`grid-${prop}:${index}`);
            }
        }
        return style.join(";");
    }

    /**
     * @param {Pill} pill
     */
    getLastCol(pill) {
        const [col, colspan] = pill.grid.column;
        return col + colspan - 1;
    }

    /**
     * @param {RelationalRecord} record
     * @returns {Partial<Pill>}
     */
    getPill(record) {
        const { canEdit, dateStartField, dateStopField, disableDrag, startDate, stopDate } =
            this.model.metaData;

        const startOutside = record[dateStartField] < startDate;
        const stopOutside = record[dateStopField] > stopDate;

        /** @type {DateTime} */
        const pillStartDate = startOutside ? startDate : record[dateStartField];
        /** @type {DateTime} */
        const pillStopDate = stopOutside ? stopDate : record[dateStopField];

        const disableStartResize = !canEdit || startOutside;
        const disableStopResize = !canEdit || stopOutside;

        const [startIndex, stopIndex] = this.computeColumnIndexes(
            pillStartDate,
            pillStopDate,
            this.dateGridColumns
        );

        const firstCol = startIndex + 1;
        const span = stopIndex - startIndex;

        /** @type {Partial<Pill>} */
        const pill = {
            disableDrag: disableDrag || disableStartResize || disableStopResize,
            disableStartResize,
            disableStopResize,
            grid: { column: [firstCol, span] },
            record,
            startDate: this.dateGridColumns[startIndex],
            stopDate: this.dateGridColumns[stopIndex],
        };

        return pill;
    }

    /**
     * @param {PillId} pillId
     */
    getPillEl(pillId) {
        return this.getPillWrapperEl(pillId).querySelector(".o_gantt_pill");
    }

    /**
     * @param {Object} group
     * @param {number} maxAggregateValue
     * @param {boolean} consolidate
     */
    getPillFromGroup(group, maxAggregateValue, consolidate) {
        const { excludeField, field, maxValue } = this.model.metaData.consolidationParams;

        const minColor = 215;
        const maxColor = 100;

        const newPill = {
            id: `__pill__${this.nextPillId++}`,
            level: 0,
            aggregateValue: group.aggregateValue,
            grid: group.grid,
        };

        // Enrich the aggregates with consolidation data
        if (consolidate && field) {
            newPill.consolidationValue = 0;
            for (const pill of group.pills) {
                if (!pill.record[excludeField]) {
                    newPill.consolidationValue += pill.record[field];
                }
            }
            newPill.consolidationMaxValue = maxValue;
            newPill.consolidationExceeded =
                newPill.consolidationValue > newPill.consolidationMaxValue;
        }

        if (consolidate && maxValue) {
            const status = newPill.consolidationExceeded ? "danger" : "success";
            newPill.className = `bg-${status} border-${status}`;
            newPill.displayName = newPill.consolidationValue;
        } else {
            const color =
                minColor -
                Math.round((newPill.aggregateValue - 1) / maxAggregateValue) *
                    (minColor - maxColor);
            newPill.style = `background-color:rgba(${color},${color},${color},0.6)`;
            newPill.displayName = this.getGroupPillDisplayName(newPill);
        }

        return newPill;
    }

    /**
     * There are two forms of pills: pills comming from fetched records
     * and pills that are some kind of aggregation of the previous.
     *
     * Here we create the pills of the firs type.
     *
     * The basic properties (independent of rows,...) of the pills of
     * the first type should be computed here.
     *
     * @returns {Partial<Pill>[]}
     */
    getPills() {
        const { records } = this.model.data;
        const { dateStartField } = this.model.metaData;
        const pills = [];
        for (const record of records) {
            const pill = this.getPill(record);
            pills.push(this.enrichPill(pill));
        }
        // sorting cannot be done when fetching data --> the snapping of pills breaks order
        return pills.sort(
            (p1, p2) =>
                p1.grid.column[0] - p2.grid.column[0] ||
                p1.record[dateStartField] - p2.record[dateStartField]
        );
    }

    /**
     * @param {PillId} pillId
     */
    getPillWrapperEl(pillId) {
        const pillSelector = `:scope > [data-pill-id="${pillId}"]`;
        return this.cellContainerRef.el?.querySelector(pillSelector);
    }

    /**
     * Get domain of records for plan dialog in the gantt view.
     *
     * @param {Object} state
     * @returns {any[][]}
     */
    getPlanDialogDomain() {
        const { dateStartField, dateStopField } = this.model.metaData;
        const newDomain = Domain.removeDomainLeaves(this.env.searchModel.globalDomain, [
            dateStartField,
            dateStopField,
        ]);
        return Domain.and([
            newDomain,
            ["|", [dateStartField, "=", false], [dateStopField, "=", false]],
        ]).toList({});
    }

    /**
     * @param {PillId} pillId
     * @param {boolean} onRight
     */
    getPoint(pillId, onRight) {
        if (localization.direction === "rtl") {
            onRight = !onRight;
        }
        const pillEl = this.getPillEl(pillId);
        const pillRect = pillEl.getBoundingClientRect();
        return {
            left: pillRect.left + (onRight ? pillRect.width : 0),
            top: pillRect.top + pillRect.height / 2,
        };
    }

    /**
     * @param {Pill} pill
     */
    getPopoverProps(pill) {
        const { record } = pill;
        const displayName = record.display_name;
        const { canEdit, dateStartField, dateStopField } = this.model.metaData;
        const context = this.popoverTemplate
            ? { ...record }
            : /* Default context */ {
                  name: displayName,
                  start: record[dateStartField].toFormat("f"),
                  stop: record[dateStopField].toFormat("f"),
              };

        return {
            title: displayName,
            context,
            template: this.popoverTemplate,
            button: {
                text: canEdit ? _t("Edit") : _t("View"),
                // Sync with the mutex to wait for potential changes on the view
                onClick: () =>
                    this.model.mutex.exec(
                        () => this.props.openDialog({ resId: record.id }) // (canEdit is also considered in openDialog)
                    ),
            },
        };
    }

    /**
     * @param {Row} row
     */
    getProgressBarProps(row) {
        return {
            progressBar: row.progressBar,
            reactive: this.progressBarsReactive,
            rowId: row.id,
        };
    }

    /**
     * @param {Unavailability[]} unavailabilities
     */
    getRowCellColors(unavailabilities) {
        const { cellPart } = this.model.metaData.scale;
        // We assume that the unavailabilities have been normalized
        // (i.e. are naturally ordered and are pairwise disjoint).
        // A subCell is considered unavailable (and greyed) when totally covered by
        // an unavailability.
        let index = 0;
        let j = 0;
        /** @type {Record<string, string>} */
        const cellColors = {};
        const subSlotUnavailabilities = [];
        for (const subColumn of this.subColumns) {
            const { isToday, start, stop, columnId } = subColumn;
            if (unavailabilities.slice(index).length) {
                let subSlotUnavailable = 0;
                for (let i = index; i < unavailabilities.length; i++) {
                    const u = unavailabilities[i];
                    if (stop > u.stop) {
                        index++;
                    } else if (u.start <= start) {
                        subSlotUnavailable = 1;
                        break;
                    }
                }
                subSlotUnavailabilities.push(subSlotUnavailable);
                if ((j + 1) % cellPart === 0) {
                    const style = getCellColor(cellPart, subSlotUnavailabilities, isToday);
                    subSlotUnavailabilities.splice(0, cellPart);
                    if (style) {
                        cellColors[columnId] = style;
                    }
                }
                j++;
            }
        }
        return cellColors;
    }

    /**
     * @param {Row} row
     */
    getRowHeight(row) {
        return row.grid.row[1] * this.constructor.GRID_ROW_HEIGHT;
    }

    getRowTitleStyle(row) {
        return this.getGridPosition({ column: row.grid.column });
    }

    openPlanDialogCallback() {}

    getSelectCreateDialogProps(params) {
        const domain = this.getPlanDialogDomain();
        const schedule = this.model.getDialogContext(params);
        return {
            title: _t("Plan"),
            resModel: this.model.metaData.resModel,
            context: schedule,
            domain,
            noCreate: !this.model.metaData.canCellCreate,
            onSelected: (resIds) => {
                if (resIds.length) {
                    this.model.reschedule(resIds, schedule, this.openPlanDialogCallback.bind(this));
                }
            },
        };
    }

    /**
     * @param {Pill[]} pills
     */
    getTotalRow(pills) {
        const preRow = {
            groupLevel: 0,
            id: "[]",
            isGroup: true,
            rows: [],
            name: _t("Total"),
            recordIds: pills.map(({ record }) => record.id),
        };

        this.topOffset = 0;
        const result = this.processRow(preRow, pills);
        const [totalRow] = result.rows;
        const maxAggregateValue = Math.max(...totalRow.pills.map((p) => p.aggregateValue));

        totalRow.factor = maxAggregateValue ? 90 / maxAggregateValue : 0;

        return totalRow;
    }

    getTodayDay() {
        return DateTime.local().day;
    }

    highlightPill(pillId, highlighted) {
        const pill = this.pills[pillId];
        if (!pill) {
            return;
        }
        pill.highlighted = highlighted;
        const pillWrapper = this.getPillWrapperEl(pillId);
        pillWrapper?.classList.toggle("highlight", highlighted);
        pillWrapper?.classList.toggle(
            "o_connector_creator_highlight",
            highlighted && this.connectorDragState.dragging
        );
    }

    initializeConnectors() {
        for (const connectorId in this.connectors) {
            this.deleteConnector(connectorId);
        }
    }

    isPillSmall(pill) {
        return this.state.pillsWidth * pill.grid.column[1] < pill.displayName.length * 10;
    }

    /**
     * @param {Row} row
     */
    isDisabled(row) {
        return this.model.useSampleModel;
    }

    /**
     * @param {Row} row
     */
    isHoverable(row) {
        return !this.model.useSampleModel;
    }

    /**
     * @param {Group[]} groups
     * @returns {Group[]}
     */
    mergeGroups(groups) {
        if (groups.length <= 1) {
            return groups;
        }
        const index = Math.floor(groups.length / 2);
        const left = this.mergeGroups(groups.slice(0, index));
        const right = this.mergeGroups(groups.slice(index));
        const group = right[0];
        if (!group.break) {
            const previousGroup = left.pop();
            group.break = previousGroup.break;
            group.grid.column[0] = previousGroup.grid.column[0];
            group.grid.column[1] += previousGroup.grid.column[1];
            group.aggregateValue = this.getAggregateValue(group, previousGroup);
        }
        return [...left, ...right];
    }

    onWillRender() {
        if (this.noDisplayedConnectors && this.shouldRenderConnectors()) {
            delete this.noDisplayedConnectors;
            this.computeDerivedParams();
        }

        this.visibleRows = [...new Set([...toRaw(this.virtualRows), ...this.extraRows])];

        if (!this.shouldRenderConnectors()) {
            this.noDisplayedConnectors = true;
            return;
        }

        const displayedPills = new Set();
        const visibleConnectorIds = new Set([NEW_CONNECTOR_ID]);
        for (const row of this.visibleRows) {
            if (row.isGroup) {
                continue;
            }
            for (const pill of row.pills) {
                displayedPills.add(pill.id);
                for (const connectorId of this.mappingPillToConnectors[pill.id] || []) {
                    visibleConnectorIds.add(connectorId);
                }
            }
        }

        this.visibleConnectors = [];
        const extraPillIds = new Set();
        for (const connectorId in this.connectors) {
            if (!visibleConnectorIds.has(connectorId)) {
                continue;
            }
            this.visibleConnectors.push(this.connectors[connectorId]);
            const { sourcePillId, targetPillId } = this.mappingConnectorToPills[connectorId];
            if (sourcePillId && !displayedPills.has(sourcePillId)) {
                extraPillIds.add(sourcePillId);
            }
            if (targetPillId && !displayedPills.has(targetPillId)) {
                extraPillIds.add(targetPillId);
            }
        }

        this.extraPills = [];
        for (const id of extraPillIds) {
            this.extraPills.push(this.pills[id]);
        }
    }

    /**
     * @param {Row} row
     * @param {Pill[]} pills
     */
    processRow(row, pills) {
        const { GROUP_ROW_SPAN, ROW_SPAN } = this.constructor;
        const { dependencyField, fields } = this.model.metaData;
        const {
            consolidate,
            fromServer,
            groupedByField,
            groupLevel,
            id,
            isGroup,
            name,
            progressBar,
            resId,
            rows,
            unavailabilities,
            recordIds,
        } = row;

        // compute the subset pills at row level
        const remainingPills = [];
        let rowPills = [];
        const groupPills = [];
        const isMany2many = groupedByField && fields[groupedByField].type === "many2many";
        for (const pill of pills) {
            const { record } = pill;
            const pushPill = recordIds.includes(record.id);
            let keepPill = false;
            if (pushPill && isMany2many) {
                const value = record[groupedByField];
                if (Array.isArray(value) && value.length > 1) {
                    keepPill = true;
                }
            }
            if (pushPill) {
                const rowPill = { ...pill };
                rowPills.push(rowPill);
                groupPills.push(pill);
            }
            if (!pushPill || keepPill) {
                remainingPills.push(pill);
            }
        }

        const baseSpan = isGroup ? GROUP_ROW_SPAN : ROW_SPAN;
        let span = baseSpan;
        if (rowPills.length) {
            if (isGroup) {
                if (this.shouldComputeAggregateValues(row)) {
                    const groups = this.aggregatePills(rowPills);
                    const maxAggregateValue = Math.max(
                        ...groups.map((group) => group.aggregateValue)
                    );
                    rowPills = groups.map((group) =>
                        this.getPillFromGroup(group, maxAggregateValue, consolidate)
                    );
                } else {
                    rowPills = [];
                }
            } else {
                const level = this.calculatePillsLevel(rowPills);
                span = level * baseSpan;
                if (!this.isTouchDevice) {
                    span += 4;
                }
            }
        }
        if (progressBar && this.isTouchDevice && (!rowPills.length || span === baseSpan)) {
            // In mobile: rows span over 2 rows to alllow progressbars to properly display
            span += ROW_SPAN;
        }

        for (const rowPill of rowPills) {
            rowPill.id = `__pill__${this.nextPillId++}`;
            rowPill.grid = {
                ...rowPill.grid,
                row: [this.topOffset + rowPill.level * baseSpan + 1, baseSpan],
            };

            if (!isGroup) {
                const { record } = rowPill;
                if (this.shouldRenderRecordConnectors(record)) {
                    if (!this.mappingRecordToPillsByRow[record.id]) {
                        this.mappingRecordToPillsByRow[record.id] = {
                            masterIds: record[dependencyField],
                            pills: {},
                        };
                    }
                    this.mappingRecordToPillsByRow[record.id].pills[id] = rowPill;
                    if (!this.mappingRowToPillsByRecord[id]) {
                        this.mappingRowToPillsByRecord[id] = {};
                    }
                    this.mappingRowToPillsByRecord[id][record.id] = rowPill;
                }
            }

            this.pills[rowPill.id] = rowPill;
        }

        /** @type {Row} */
        const processedRow = {
            fromServer,
            groupedByField,
            groupLevel,
            id,
            isGroup,
            name,
            pills: rowPills,
            progressBar,
            resId,
            grid: {
                row: [this.topOffset + 1, span],
                column: [groupLevel + 2, -1],
            },
        };

        this.topOffset += span;

        const field = this.model.metaData.thumbnails[groupedByField];
        if (field) {
            const model = this.model.metaData.fields[groupedByField].relation;
            processedRow.thumbnailUrl = url("/web/image", {
                model,
                id: resId,
                field,
            });
        }

        if (!isGroup && unavailabilities) {
            // attribute a color to each cell part according to row unavailabilities
            processedRow.cellColors = this.getRowCellColors(unavailabilities);
        } else {
            processedRow.cellColors = {};
        }

        const result = { rows: [processedRow], pillsToProcess: remainingPills };

        let pillsToProcess = groupPills;
        if (isGroup && !this.model.isClosed(id)) {
            for (const subRow of rows) {
                const res = this.processRow(subRow, pillsToProcess);
                result.rows.push(...res.rows);
                pillsToProcess = res.pillsToProcess;
            }
        }

        return result;
    }

    /**
     * @param {Object} params
     * @param {Element} params.pill
     * @param {number} params.diff
     * @param {"start" | "end"} params.direction
     */
    async resizePillDrop({ pill, diff, direction }) {
        const { dateStartField, dateStopField, scale } = this.model.metaData;
        const { cellTime, time } = scale;
        const { record } = this.pills[pill.dataset.pillId];
        const params = {};

        if (direction === "start") {
            params.start = dateAddFixedOffset(record[dateStartField], { [time]: cellTime * diff });
        } else {
            params.stop = dateAddFixedOffset(record[dateStopField], { [time]: cellTime * diff });
        }
        const schedule = this.model.getSchedule(params);

        await this.model.reschedule(record.id, schedule, this.openPlanDialogCallback);
    }

    /**
     * @param {Partial<ConnectorProps>} params
     * @param {PillId | null} [sourceId=null]
     * @param {PillId | null} [targetId=null]
     */
    setConnector(params, sourceId = null, targetId = null) {
        const connectorParams = { ...params };
        const connectorId = params.id || `__connector__${this.nextConnectorId++}`;

        if (sourceId) {
            connectorParams.sourcePoint = () => this.getPoint(sourceId, true);
        }

        if (targetId) {
            connectorParams.targetPoint = () => this.getPoint(targetId, false);
        }

        if (this.connectors[connectorId]) {
            Object.assign(this.connectors[connectorId], connectorParams);
        } else {
            this.connectors[connectorId] = {
                id: connectorId,
                highlighted: false,
                displayButtons: false,
                ...connectorParams,
            };
            this.mappingConnectorToPills[connectorId] = {
                sourcePillId: sourceId,
                targetPillId: targetId,
            };
        }

        if (sourceId) {
            if (!this.mappingPillToConnectors[sourceId]) {
                this.mappingPillToConnectors[sourceId] = [];
            }
            this.mappingPillToConnectors[sourceId].push(connectorId);
        }

        if (targetId) {
            if (!this.mappingPillToConnectors[targetId]) {
                this.mappingPillToConnectors[targetId] = [];
            }
            this.mappingPillToConnectors[targetId].push(connectorId);
        }
    }

    /**
     * @param {HTMLElement | null} [cellEl]
     */
    setStickyRowFromCell(cellEl) {
        this.extraRows = [];
        if (cellEl) {
            const { rowId } = cellEl.dataset;
            const row = this.rows.find((row) => row.id === rowId);
            if (row) {
                this.extraRows.push(row);
            }
        }
    }

    /**
     * @param {Row} row
     */
    shouldComputeAggregateValues(row) {
        return true;
    }

    shouldMergeGroups() {
        return true;
    }

    /**
     * Returns whether connectors should be rendered or not.
     * The connectors won't be rendered on sampleData as we can't be sure that data are coherent.
     * The connectors won't be rendered on mobile as the usability is not guarantied.
     * The connectors won't be rendered on multiple groupBy as we would need to manage groups folding which seems
     *     overkill at this stage.
     *
     * @return {boolean}
     */
    shouldRenderConnectors() {
        return (
            this.model.metaData.dependencyField &&
            !this.model.useSampleModel &&
            !this.env.isSmall &&
            this.model.metaData.groupedBy.length <= 1
        );
    }

    /**
     * Returns whether connectors should be rendered on particular records or not.
     * This method is intended to be overridden in particular modules in order to set particular record's condition.
     *
     * @param {RelationalRecord} record
     * @return {boolean}
     */
    shouldRenderRecordConnectors(record) {
        return this.shouldRenderConnectors();
    }

    /**
     * @param {ConnectorId | null} connectorId
     * @param {boolean} highlighted
     */
    toggleConnectorHighlighting(connectorId, highlighted) {
        const connector = this.connectors[connectorId];
        if (!connector || (!connector.highlighted && !highlighted)) {
            return;
        }

        connector.highlighted = highlighted;
        connector.displayButtons = highlighted;

        const { sourcePillId, targetPillId } = this.mappingConnectorToPills[connectorId];

        this.highlightPill(sourcePillId, highlighted);
        this.highlightPill(targetPillId, highlighted);
    }

    /**
     * @param {PillId} pillId
     * @param {boolean} highlighted
     */
    togglePillHighlighting(pillId, highlighted) {
        const pill = this.pills[pillId];
        if (!pill || pill.highlighted === highlighted) {
            return;
        }

        const { record } = pill;
        const pillIdsToHighlight = new Set([pillId]);

        if (record && this.shouldRenderRecordConnectors(record)) {
            // Find other related pills
            const { pills: relatedPills } = this.mappingRecordToPillsByRow[record.id];
            for (const pill of Object.values(relatedPills)) {
                pillIdsToHighlight.add(pill.id);
            }

            // Highlight related connectors
            for (const [connectorId, connector] of Object.entries(this.connectors)) {
                const ids = Object.values(this.getRecordIds(connectorId));
                if (ids.includes(record.id)) {
                    connector.highlighted = highlighted;
                    connector.displayButtons = false;
                }
            }
        }

        // Highlight pills from found IDs
        for (const id of pillIdsToHighlight) {
            this.highlightPill(id, highlighted);
        }
    }

    //-------------------------------------------------------------------------
    // Handlers
    //-------------------------------------------------------------------------

    /**
     * @param {Object} params
     * @param {RowId} params.rowId
     * @param {number} params.columnIndex
     */
    onCreate(rowId, columnStart, columnStop) {
        const { start, stop } = this.getColumnStartStop(columnStart, columnStop);
        const context = this.model.getDialogContext({
            rowId,
            start,
            stop,
            withDefault: true,
        });
        this.props.create(context);
    }

    onInteractionChange() {
        let { dragAction, mode } = this.interaction;
        if (mode === "drag") {
            mode = dragAction;
        }
        if (this.rootRef.el) {
            for (const [action, className] of INTERACTION_CLASSNAMES) {
                this.rootRef.el.classList.toggle(className, mode === action);
            }
        }
    }

    onSelectStart(ev) {
        if (ev.button !== 0) {
            return;
        }
        const { hoverable } = this.hovered;
        const { canCellCreate, canPlan } = this.model.metaData;
        if (canCellCreate || canPlan) {
            const isUngroupedCellHovered = hoverable?.matches(".o_gantt_cell:not(.o_gantt_group)");
            if (isUngroupedCellHovered && !ev?.target.closest(".o_connector_creator")) {
                this.selection.active = true;
                this.selection.rowId = hoverable.dataset.rowId;
                this.selection.initialIndex = Number(hoverable.dataset.columnIndex);
                this.selection.lastSelectId = this.selection.initialIndex;
                hoverable.classList.add("o_drag_hover");
            }
        }
    }

    onSelectStop() {
        const { canPlan } = this.model.metaData;
        if (this.selection.active) {
            this.selection.active = false;
            const { rowId, initialIndex, lastSelectId } = this.selection;
            const columnStart = Math.min(initialIndex, lastSelectId);
            const columnStop = Math.max(initialIndex, lastSelectId);
            for (const cell of this.getCellsOnRow(rowId)) {
                cell.classList.remove("o_drag_hover");
            }
            if (canPlan) {
                this.onPlan(rowId, columnStart, columnStop);
            } else {
                this.onCreate(rowId, columnStart, columnStop);
            }
        }
    }

    onPointerLeave() {
        this.throttledOnPointerMove.cancel();

        if (!this.isDragging) {
            const hoveredConnectorId = this.hovered.connector?.dataset.connectorId;
            this.toggleConnectorHighlighting(hoveredConnectorId, false);

            const hoveredPillId = this.hovered.pill?.dataset.pillId;
            this.togglePillHighlighting(hoveredPillId, false);
        }

        this.hovered.connector = null;
        this.hovered.pill = null;
        this.hovered.hoverable = null;

        this.computeDerivedParamsFromHover();
    }

    /**
     * Updates all hovered elements, then calls "computeDerivedParamsFromHover".
     *
     * @see computeDerivedParamsFromHover
     * @param {PointerEvent} ev
     */
    onPointerMove(ev) {
        // Lazily compute elements from point as it is a costly operation
        let els = null;
        const pointedEls = () => els || (els = document.elementsFromPoint(ev.clientX, ev.clientY));

        // To find hovered elements, also from pointed elements
        const find = (selector) =>
            ev.target.closest?.(selector) ||
            pointedEls().find((el) => el.matches(selector)) ||
            null;

        this.hovered.connector = find(".o_gantt_connector");
        this.hovered.hoverable = find(".o_gantt_hoverable");
        this.hovered.pill = find(".o_gantt_pill_wrapper");

        this.computeDerivedParamsFromHover(ev);
    }

    /**
     * @param {PointerEvent} ev
     * @param {Pill} pill
     */
    onPillClicked(ev, pill) {
        if (this.popover.isOpen) {
            return;
        }
        const popoverTarget = ev.target.closest(".o_gantt_pill_wrapper");
        this.popover.open(popoverTarget, this.getPopoverProps(pill));
    }

    /**
     * @param {Object} params
     * @param {RowId} params.rowId
     * @param {number} params.columnIndex
     */
    onPlan(rowId, columnStart, columnStop) {
        const { start, stop } = this.getColumnStartStop(columnStart, columnStop);
        this.dialogService.add(
            SelectCreateDialog,
            this.getSelectCreateDialogProps({ rowId, start, stop, withDefault: true })
        );
    }

    getRecordIds(connectorId) {
        const { sourcePillId, targetPillId } = this.mappingConnectorToPills[connectorId];
        return {
            masterId: this.pills[sourcePillId]?.record.id,
            slaveId: this.pills[targetPillId]?.record.id,
        };
    }

    /**
     *
     * @param {Object} params
     * @param {ConnectorId} connectorId
     */
    onRemoveButtonClick(connectorId) {
        const { masterId, slaveId } = this.getRecordIds(connectorId);
        this.model.removeDependency(masterId, slaveId);
    }

    /**
     *
     * @param {"forward" | "backward"} direction
     * @param {ConnectorId} connectorId
     */
    async onRescheduleButtonClick(direction, connectorId) {
        const { masterId, slaveId } = this.getRecordIds(connectorId);
        const result = await this.model.rescheduleAccordingToDependency(
            direction,
            masterId,
            slaveId
        );
        if (result && typeof result === "object") {
            this.actionService.doAction(result);
        }
    }

    /**
     * @param {KeyboardEvent} ev
     */
    onWindowKeyDown(ev) {
        if (ev.key === "Control") {
            this.prevDragAction =
                this.interaction.dragAction === "copy" ? "reschedule" : this.interaction.dragAction;
            this.interaction.dragAction = "copy";
        }
        if (ev.key === "Escape") {
            this.selection.active = false;
            document
                .querySelectorAll(".o_gantt_cell")
                .forEach((cell) => cell.classList.remove("o_drag_hover"));
        }
    }

    /**
     * @param {KeyboardEvent} ev
     */
    onWindowKeyUp(ev) {
        if (ev.key === "Control") {
            this.interaction.dragAction = this.prevDragAction || "reschedule";
        }
    }

    onCollapseClicked() {
        this.model.collapseRows();
    }

    onExpandClicked() {
        this.model.expandRows();
    }

    onNextPeriodClicked() {
        this.model.setFocusDate("next");
    }

    onPreviousPeriodClicked() {
        this.model.setFocusDate("previous");
    }

    onTodayClicked() {
        this.model.setFocusDate();
    }

    get displayExpandCollapseButtons() {
        return this.model.data.rows[0]?.isGroup; // all rows on same level have same type
    }
}
