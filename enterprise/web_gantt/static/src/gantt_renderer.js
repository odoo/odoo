import {
    Component,
    onWillRender,
    onWillStart,
    onWillUpdateProps,
    reactive,
    useEffect,
    useExternalListener,
    useRef,
    markup,
} from "@odoo/owl";
import { hasTouch, isMobileOS } from "@web/core/browser/feature_detection";
import { Domain } from "@web/core/domain";
import {
    getStartOfLocalWeek,
    is24HourFormat,
    serializeDate,
    serializeDateTime,
} from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { omit, pick } from "@web/core/utils/objects";
import { debounce, throttleForAnimation } from "@web/core/utils/timing";
import { url } from "@web/core/utils/urls";
import { escape } from "@web/core/utils/strings";
import { useVirtualGrid } from "@web/core/virtual_grid_hook";
import { formatFloatTime } from "@web/views/fields/formatters";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { GanttConnector } from "./gantt_connector";
import {
    dateAddFixedOffset,
    diffColumn,
    getCellColor,
    getColorIndex,
    getCellsOnRow,
    localEndOf,
    localStartOf,
    useGanttConnectorDraggable,
    useGanttDraggable,
    useGanttResizable,
    useGanttSelectable,
    useGanttUndraggable,
    useMultiHover,
} from "./gantt_helpers";
import { GanttPopover } from "./gantt_popover";
import { GanttRendererControls } from "./gantt_renderer_controls";
import { GanttResizeBadge } from "./gantt_resize_badge";
import { GanttRowProgressBar } from "./gantt_row_progress_bar";
import { clamp } from "@web/core/utils/numbers";

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
        GanttRendererControls,
        GanttResizeBadge,
        GanttRowProgressBar,
        Popover: GanttPopover,
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
    static groupPillTemplate = "web_gantt.GanttRenderer.GroupPill";
    static rowContentTemplate = "web_gantt.GanttRenderer.RowContent";
    static rowHeaderTemplate = "web_gantt.GanttRenderer.RowHeader";
    static totalRowTemplate = "web_gantt.GanttRenderer.TotalRow";

    static getRowHeaderWidth = (width) => 100 / (width > 768 ? 6 : 3);

    setup() {
        this.model = this.props.model;

        this.gridRef = useRef("grid");
        this.cellContainerRef = useRef("cellContainer");

        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.notificationService = useService("notification");
        this.orm = useService("orm");

        this.is24HourFormat = is24HourFormat();

        /** @type {HoveredInfo} */
        this.hovered = {
            connector: null,
            hoverable: null,
            pill: null,
        };

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
        this.progressBarsReactive = reactive({ hoveredRowId: null });
        /** @type {ResizeBadge} */
        this.resizeBadgeReactive = reactive({});

        /** @type {Object[]} */
        this.columnsGroups = [];
        /** @type {Column[]} */
        this.columns = [];
        /** @type {Pill[]} */
        this.extraPills = [];
        /** @type {Record<PillId, Pill>} */
        this.pills = {}; // mapping to retrieve pills from pill ids
        /** @type {Row[]} */
        this.rows = [];
        /** @type {SubColumn[]} */
        this.subColumns = [];
        /** @type {Record<RowId, Pill[]>} */
        this.rowPills = {};

        this.mappingColToColumn = new Map();
        this.mappingColToSubColumn = new Map();
        this.cursorPosition = {
            x: 0,
            y: 0,
        };
        const position = "bottom";
        this.popover = usePopover(this.constructor.components.Popover, {
            position,
            onPositioned: (el, { direction }) => {
                if (direction !== position) {
                    return;
                }
                const { left, right } = el.getBoundingClientRect();
                if ((0 <= left && right <= window.innerWidth) || window.innerWidth < right - left) {
                    return;
                }
                const { left: pillLeft, right: pillRight } =
                    this.popover.target.getBoundingClientRect();
                const middle =
                    (clamp(pillLeft, 0, window.innerWidth) +
                        clamp(pillRight, 0, window.innerWidth)) /
                    2;
                el.style.left = `0px`;
                const { width } = el.getBoundingClientRect();
                el.style.left = `${middle - width / 2}px`;
            },
            onClose: () => {
                delete this.popover.target;
            },
        });

        this.throttledComputeHoverParams = throttleForAnimation((ev) =>
            this.computeHoverParams(ev)
        );

        useExternalListener(window, "keydown", (ev) => this.onWindowKeyDown(ev));
        useExternalListener(window, "keyup", (ev) => this.onWindowKeyUp(ev));

        useExternalListener(
            window,
            "resize",
            debounce(() => {
                this.shouldComputeSomeWidths = true;
                this.render();
            }, 100)
        );

        useMultiHover({
            ref: this.gridRef,
            selector: ".o_gantt_group",
            related: ["data-row-id"],
            className: "o_gantt_group_hovered",
        });

        // Draggable pills
        this.cellForDrag = { el: null, part: 0 };
        const dragState = useGanttDraggable({
            enable: () => Boolean(this.cellForDrag.el),
            // Refs and selectors
            ref: this.gridRef,
            hoveredCell: this.cellForDrag,
            elements: ".o_draggable",
            ignore: ".o_resize_handle,.o_connector_creator_bullet",
            cells: ".o_gantt_cell:not(.o_gantt_readonly)",
            // Style classes
            cellDragClassName: "o_gantt_cell o_drag_hover",
            ghostClassName: "o_dragged_pill_ghost",
            addStickyCoordinates: (rows, columns) => {
                this.stickyGridRows = Object.assign({}, ...rows.map((row) => ({ [row]: true })));
                this.stickyGridColumns = Object.assign(
                    {},
                    ...columns.map((column) => ({ [column]: true }))
                );
                this.setSomeGridStyleProperties();
            },
            // Handlers
            onDragStart: ({ pill }) => {
                this.popover.close();
                this.setStickyPill(pill);
                this.toggleRowsReadonly(false);
                this.interaction.mode = "drag";
            },
            onDragEnd: () => {
                this.toggleRowsReadonly(true);
                this.setStickyPill();
                this.interaction.mode = null;
            },
            onDrop: (params) => this.dragPillDrop(params),
        });

        // Un-draggable pills
        const unDragState = useGanttUndraggable({
            // Refs and selectors
            ref: this.gridRef,
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

        // Cells selection
        const selectState = useGanttSelectable({
            enable: () => {
                const { canCellCreate, canPlan } = this.model.metaData;
                return Boolean(this.cellForDrag.el) && (canCellCreate || canPlan);
            },
            ref: this.gridRef,
            hoveredCell: this.cellForDrag,
            elements: ".o_gantt_cell:not(.o_gantt_group)",
            edgeScrolling: { speed: 40, threshold: 150, direction: "horizontal" },
            rtl: () => localization.direction === "rtl",
            onDrop: ({ rowId, startCol, stopCol }) => {
                const { canPlan } = this.model.metaData;
                if (canPlan) {
                    this.onPlan(rowId, startCol, stopCol);
                } else {
                    this.onCreate(rowId, startCol, stopCol);
                }
            },
        });

        // Resizable pills
        const resizeState = useGanttResizable({
            // Refs and selectors
            ref: this.gridRef,
            hoveredCell: this.cellForDrag,
            elements: ".o_resizable",
            innerPills: ".o_gantt_pill",
            cells: ".o_gantt_cell",
            // Other params
            handles: "o_resize_handle",
            edgeScrolling: { speed: 40, threshold: 150, direction: "horizontal" },
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
                this.setStickyPill(pill);
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
                this.setStickyPill();
                removeClass(pill, "o_resized");
                this.interaction.mode = null;
            },
            onDrop: (params) => this.resizePillDrop(params),
        });

        // Draggable connector
        let initialPillId;
        this.connectorDragState = useGanttConnectorDraggable({
            ref: this.gridRef,
            elements: ".o_connector_creator_bullet",
            parentWrapper: ".o_gantt_cells .o_gantt_pill_wrapper",
            onDragStart: ({ sourcePill, x, y, addClass }) => {
                this.popover.close();
                initialPillId = sourcePill.dataset.pillId;
                addClass(sourcePill, "o_connector_creator_lock");
                this.setConnector({
                    id: NEW_CONNECTOR_ID,
                    highlighted: true,
                    sourcePoint: { left: x, top: y },
                    targetPoint: { left: x, top: y },
                });
                this.setStickyPill(sourcePill);
                this.interaction.mode = "connect";
            },
            onDrag: ({ connectorCenter, x, y }) => {
                this.setConnector({
                    id: NEW_CONNECTOR_ID,
                    sourcePoint: { left: connectorCenter.x, top: connectorCenter.y },
                    targetPoint: { left: x, top: y },
                });
            },
            onDragEnd: () => {
                this.setConnector({ id: NEW_CONNECTOR_ID, sourcePoint: null, targetPoint: null });
                this.setStickyPill();
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

        this.dragStates = [dragState, unDragState, resizeState, selectState];

        onWillStart(this.computeDerivedParams);
        onWillUpdateProps(this.computeDerivedParams);

        this.virtualGrid = useVirtualGrid({
            scrollableRef: this.props.contentRef,
            initialScroll: this.props.scrollPosition,
            bufferCoef: 0.1,
            onChange: (changed) => {
                if ("columnsIndexes" in changed) {
                    this.shouldComputeGridColumns = true;
                }
                if ("rowsIndexes" in changed) {
                    this.shouldComputeGridRows = true;
                }
                this.render();
            },
        });

        onWillRender(this.onWillRender);

        useEffect(
            (content) => {
                content.addEventListener("scroll", this.throttledComputeHoverParams);
                return () => {
                    content.removeEventListener("scroll", this.throttledComputeHoverParams);
                };
            },
            () => [this.gridRef.el?.parentElement]
        );

        useEffect(() => {
            if (this.useFocusDate) {
                this.useFocusDate = false;
                this.focusDate(this.model.metaData.focusDate);
            }
        });

        this.env.getCurrentFocusDateCallBackRecorder.add(this, this.getCurrentFocusDate.bind(this));
    }

    //-------------------------------------------------------------------------
    // Getters
    //-------------------------------------------------------------------------

    get controlsProps() {
        return {
            displayExpandCollapseButtons: this.rows[0]?.isGroup, // all rows on same level have same type
            model: this.model,
            focusToday: () => this.focusToday(),
            getCurrentFocusDate: () => this.getCurrentFocusDate(),
        };
    }

    /**
     * @returns {boolean}
     */
    get hasRowHeaders() {
        const { groupedBy } = this.model.metaData;
        const { displayMode } = this.model.displayParams;
        return groupedBy.length || displayMode === "sparse";
    }

    get isDragging() {
        return this.dragStates.some((s) => s.dragging);
    }

    /**
     * @returns {boolean}
     */
    get isTouchDevice() {
        return isMobileOS() || hasTouch();
    }

    //-------------------------------------------------------------------------
    // Methods
    //-------------------------------------------------------------------------

    /**
     *
     * @param {Object} param
     * @param {Object} param.grid
     */
    addCoordinatesToCoarseGrid({ grid }) {
        if (grid.row) {
            this.coarseGridRows[this.getFirstGridRow({ grid })] = true;
            this.coarseGridRows[this.getLastGridRow({ grid })] = true;
        }
        if (grid.column) {
            this.coarseGridCols[this.getFirstGridCol({ grid })] = true;
            this.coarseGridCols[this.getLastGridCol({ grid })] = true;
        }
    }

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
     * Conditional function for aggregating pills when grouping the gantt view
     * The first, unused parameter is added in case it's needed when overwriting the method.
     * @param {Row} row
     * @param {Group} group
     * @returns {boolean}
     */
    shouldAggregate(row, group) {
        return Boolean(group.pills.length);
    }

    /**
     * Aggregates overlapping pills in group rows.
     *
     * @param {Pill[]} pills
     * @param {Row} row
     */
    aggregatePills(pills, row) {
        /** @type {Record<number, Group>} */
        const groups = {};
        function getGroup(col) {
            if (!(col in groups)) {
                groups[col] = {
                    break: false,
                    col,
                    pills: [],
                    aggregateValue: 0,
                    grid: { column: [col, col + 1] },
                };
                // group.break = true means that the group cannot be merged with the previous one
                // We will merge groups that can be merged together (if this.shouldMergeGroups returns true)
            }
            return groups[col];
        }

        const lastCol = this.columnCount * this.model.metaData.scale.cellPart + 1;
        for (const pill of pills) {
            let addedInPreviousCol = false;
            let col;
            for (col = this.getFirstGridCol(pill); col < this.getLastGridCol(pill); col++) {
                const group = getGroup(col);
                const added = this.addTo(pill, group);
                if (addedInPreviousCol !== added) {
                    group.break = true;
                }
                addedInPreviousCol = added;
            }
            // here col = this.getLastGridCol(pill)
            if (addedInPreviousCol && col < lastCol) {
                const group = getGroup(col);
                group.break = true;
            }
        }

        const filteredGroups = Object.values(groups).filter((g) => this.shouldAggregate(row, g));

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
                maxCol: this.getLastGridCol(firstPill) - 1,
            },
        ];
        for (const currentPill of pills.slice(1)) {
            const lastCol = this.getLastGridCol(currentPill) - 1;
            for (let l = 0; l < levels.length; l++) {
                const level = levels[l];
                if (this.getFirstGridCol(currentPill) > level.maxCol) {
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

    makeSubColumn(start, delta, cellTime, time) {
        const subCellStart = dateAddFixedOffset(start, { [time]: delta * cellTime });
        const subCellStop = dateAddFixedOffset(start, {
            [time]: (delta + 1) * cellTime,
            seconds: -1,
        });
        return { start: subCellStart, stop: subCellStop };
    }

    computeVisibleColumns() {
        const [firstIndex, lastIndex] = this.virtualGrid.columnsIndexes;
        this.columnsGroups = [];
        this.columns = [];
        this.subColumns = [];
        this.coarseGridCols = {
            1: true,
            [this.columnCount * this.model.metaData.scale.cellPart + 1]: true,
        };

        const { globalStart, globalStop, scale } = this.model.metaData;
        const { cellPart, interval, unit } = scale;

        const now = DateTime.local();

        const nowStart = now.startOf(interval);
        const nowEnd = now.endOf(interval);

        const groupsLeftBound = DateTime.max(
            globalStart,
            localStartOf(globalStart.plus({ [interval]: firstIndex }), unit)
        );
        const groupsRightBound = DateTime.min(
            localEndOf(globalStart.plus({ [interval]: lastIndex }), unit),
            globalStop
        );
        let currentGroup = null;
        for (let j = firstIndex; j <= lastIndex; j++) {
            const columnId = `__column__${j + 1}`;
            const col = j * cellPart + 1;
            const { start, stop } = this.getColumnFromColNumber(col);
            const column = {
                id: columnId,
                grid: { column: [col, col + cellPart] },
                start,
                stop,
            };
            const isToday = nowStart <= start && start <= nowEnd;
            if (isToday) {
                column.isToday = true;
            }
            this.columns.push(column);

            for (let i = 0; i < cellPart; i++) {
                const subColumn = this.getSubColumnFromColNumber(col + i);
                this.subColumns.push({ ...subColumn, isToday, columnId });
                this.coarseGridCols[col + i] = true;
            }

            const groupStart = localStartOf(start, unit);
            if (!currentGroup || !groupStart.equals(currentGroup.start)) {
                const groupId = `__group__${this.columnsGroups.length + 1}`;
                const startingBound = DateTime.max(groupsLeftBound, groupStart);
                const endingBound = DateTime.min(groupsRightBound, localEndOf(groupStart, unit));
                const [groupFirstCol, groupLastCol] = this.getGridColumnFromDates(
                    startingBound,
                    endingBound
                );
                currentGroup = {
                    id: groupId,
                    grid: { column: [groupFirstCol, groupLastCol] },
                    start: groupStart,
                };
                this.columnsGroups.push(currentGroup);
                this.coarseGridCols[groupFirstCol] = true;
                this.coarseGridCols[groupLastCol] = true;
            }
        }
    }

    computeVisibleRows() {
        this.coarseGridRows = {
            1: true,
            [this.getLastGridRow(this.rows[this.rows.length - 1])]: true,
        };
        const [rowStart, rowEnd] = this.virtualGrid.rowsIndexes;
        this.rowsToRender = new Set();
        for (const row of this.rows) {
            const [first, last] = row.grid.row;
            if (last <= rowStart + 1 || first > rowEnd + 1) {
                continue;
            }
            this.addToRowsToRender(row);
        }
    }

    getFirstGridCol({ grid }) {
        const [first] = grid.column;
        return first;
    }

    getLastGridCol({ grid }) {
        const [, last] = grid.column;
        return last;
    }

    getFirstGridRow({ grid }) {
        const [first] = grid.row;
        return first;
    }

    getLastGridRow({ grid }) {
        const [, last] = grid.row;
        return last;
    }

    addToPillsToRender(pill) {
        this.pillsToRender.add(pill);
        this.addCoordinatesToCoarseGrid(pill);
    }

    addToRowsToRender(row) {
        this.rowsToRender.add(row);
        const [first, last] = row.grid.row;
        for (let i = first; i <= last; i++) {
            this.coarseGridRows[i] = true;
        }
    }

    /**
     * give bounds only
     */
    getVisibleCols() {
        const [columnStart, columnEnd] = this.virtualGrid.columnsIndexes;
        const { cellPart } = this.model.metaData.scale;
        const firstVisibleCol = 1 + cellPart * columnStart;
        const lastVisibleCol = 1 + cellPart * (columnEnd + 1);
        return [firstVisibleCol, lastVisibleCol];
    }

    /**
     * give bounds only
     */
    getVisibleRows() {
        const [rowStart, rowEnd] = this.virtualGrid.rowsIndexes;
        const firstVisibleRow = rowStart + 1;
        const lastVisibleRow = rowEnd + 1;
        return [firstVisibleRow, lastVisibleRow];
    }

    computeVisiblePills() {
        this.pillsToRender = new Set();

        const [firstVisibleCol, lastVisibleCol] = this.getVisibleCols();
        const [firstVisibleRow, lastVisibleRow] = this.getVisibleRows();

        const isOut = (pill, filterOnRow = true) =>
            this.getFirstGridCol(pill) > lastVisibleCol ||
            this.getLastGridCol(pill) < firstVisibleCol ||
            (filterOnRow &&
                (this.getFirstGridRow(pill) > lastVisibleRow ||
                    this.getLastGridRow(pill) - 1 < firstVisibleRow));

        const getRowPills = (row, filterOnRow) =>
            (this.rowPills[row.id] || []).filter((pill) => !isOut(pill, filterOnRow));

        for (const row of this.rowsToRender) {
            for (const rowPill of getRowPills(row)) {
                this.addToPillsToRender(rowPill);
            }
            if (!row.isGroup && row.unavailabilities?.length) {
                row.cellColors = this.getRowCellColors(row);
            }
        }

        if (this.stickyPillId) {
            this.addToPillsToRender(this.pills[this.stickyPillId]);
        }

        if (this.totalRow) {
            this.totalRow.pills = getRowPills(this.totalRow, false);
            for (const pill of this.totalRow.pills) {
                this.addCoordinatesToCoarseGrid({ grid: omit(pill.grid, "row") });
            }
        }
    }

    computeVisibleConnectors() {
        const visibleConnectorIds = new Set([NEW_CONNECTOR_ID]);

        for (const pill of this.pillsToRender) {
            const row = this.getRowFromPill(pill);
            if (row.isGroup) {
                continue;
            }
            for (const connectorId of this.mappingPillToConnectors[pill.id] || []) {
                visibleConnectorIds.add(connectorId);
            }
        }

        this.connectorsToRender = [];
        for (const connectorId in this.connectors) {
            if (!visibleConnectorIds.has(connectorId)) {
                continue;
            }
            this.connectorsToRender.push(this.connectors[connectorId]);
            const { sourcePillId, targetPillId } = this.mappingConnectorToPills[connectorId];
            if (sourcePillId) {
                this.addToPillsToRender(this.pills[sourcePillId]);
            }
            if (targetPillId) {
                this.addToPillsToRender(this.pills[targetPillId]);
            }
        }
    }

    getRowFromPill(pill) {
        return this.rowByIds[pill.rowId];
    }

    getColInCoarseGridKeys() {
        return Object.keys({ ...this.coarseGridCols, ...this.stickyGridColumns });
    }

    getRowInCoarseGridKeys() {
        return Object.keys({ ...this.coarseGridRows, ...this.stickyGridRows });
    }

    computeColsTemplate() {
        const colsTemplate = [];
        const colInCoarseGridKeys = this.getColInCoarseGridKeys();
        for (let i = 0; i < colInCoarseGridKeys.length - 1; i++) {
            const x = +colInCoarseGridKeys[i];
            const y = +colInCoarseGridKeys[i + 1];
            const colName = `c${x}`;
            const width = (y - x) * this.cellPartWidth;
            colsTemplate.push(`[${colName}]minmax(${width}px,1fr)`);
        }
        colsTemplate.push(`[c${colInCoarseGridKeys.at(-1)}]`);
        return colsTemplate.join("");
    }

    computeRowsTemplate() {
        const rowsTemplate = [];
        const rowInCoarseGridKeys = this.getRowInCoarseGridKeys();
        for (let i = 0; i < rowInCoarseGridKeys.length - 1; i++) {
            const x = +rowInCoarseGridKeys[i];
            const y = +rowInCoarseGridKeys[i + 1];
            const rowName = `r${x}`;
            const height = this.gridRows.slice(x - 1, y - 1).reduce((a, b) => a + b, 0);
            rowsTemplate.push(`[${rowName}]${height}px`);
        }
        rowsTemplate.push(`[r${rowInCoarseGridKeys.at(-1)}]`);
        return rowsTemplate.join("");
    }

    computeSomeWidths() {
        const { cellPart, minimalColumnWidth } = this.model.metaData.scale;
        this.contentRefWidth = this.props.contentRef.el?.clientWidth ?? document.body.clientWidth;
        const rowHeaderWidthPercentage = this.hasRowHeaders
            ? this.constructor.getRowHeaderWidth(this.contentRefWidth)
            : 0;
        this.rowHeaderWidth = this.hasRowHeaders
            ? Math.round((rowHeaderWidthPercentage * this.contentRefWidth) / 100)
            : 0;
        this.cellContainerWidth = this.contentRefWidth - this.rowHeaderWidth;
        const columnWidth = Math.floor(this.cellContainerWidth / this.columnCount);
        const rectifiedColumnWidth = Math.max(columnWidth, minimalColumnWidth);
        this.cellPartWidth = Math.floor(rectifiedColumnWidth / cellPart);
        this.columnWidth = this.cellPartWidth * cellPart;
        if (columnWidth <= minimalColumnWidth) {
            // overflow
            this.totalWidth = this.rowHeaderWidth + this.columnWidth * this.columnCount;
        } else {
            this.totalWidth = null;
        }
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

        const { globalStart, globalStop, scale, startDate, stopDate } = this.model.metaData;
        this.columnCount = diffColumn(globalStart, globalStop, scale.interval);
        if (
            !this.currentStartDate ||
            diffColumn(this.currentStartDate, startDate, "day") ||
            diffColumn(this.currentStopDate, stopDate, "day") ||
            this.currentScaleId !== scale.id
        ) {
            this.useFocusDate = true;
            this.mappingColToColumn = new Map();
            this.mappingColToSubColumn = new Map();
        }
        this.currentStartDate = startDate;
        this.currentStopDate = stopDate;
        this.currentScaleId = scale.id;

        this.currentGridRow = 1;
        this.gridRows = [];
        this.nextPillId = 1;

        this.pills = {}; // mapping to retrieve pills from pill ids
        this.rows = [];
        this.rowPills = {};
        this.rowByIds = {};

        const prePills = this.getPills();

        let pillsToProcess = [...prePills];
        for (const row of modelRows) {
            const result = this.processRow(row, pillsToProcess);
            this.rows.push(...result.rows);
            pillsToProcess = result.pillsToProcess;
        }

        const { displayTotalRow } = this.model.metaData;
        if (displayTotalRow) {
            this.totalRow = this.getTotalRow(prePills);
        }

        if (this.shouldRenderConnectors()) {
            this.initializeConnectors();
            this.generateConnectors();
        }

        this.shouldComputeSomeWidths = true;
        this.shouldComputeGridColumns = true;
        this.shouldComputeGridRows = true;
    }

    computeDerivedParamsFromHover() {
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
            this.cellForDrag.part = Math.floor(
                (this.cursorPosition.x - x) / (width / scale.cellPart)
            );
            if (localization.direction === "rtl") {
                this.cellForDrag.part = scale.cellPart - 1 - this.cellForDrag.part;
            }
        }

        if (this.isDragging) {
            this.progressBarsReactive.hoveredRowId = null;
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
                this.progressBarsReactive.hoveredRowId = null;
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

        // Update progress bars
        this.progressBarsReactive.hoveredRowId = hoverable ? hoverable.dataset.rowId : null;
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
        const params = this.getScheduleParams(pill);

        params.start =
            diff && dateAddFixedOffset(record[dateStartField], { [time]: cellTime * diff });
        params.stop =
            diff && dateAddFixedOffset(record[dateStopField], { [time]: cellTime * diff });
        params.rowId = rowId;

        const schedule = this.model.getSchedule(params);

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
            const pillContext = Object.assign({}, user.context);
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

    focusDate(date, ifInBounds) {
        const { globalStart, globalStop } = this.model.metaData;
        const diff = date.diff(globalStart);
        const totalDiff = globalStop.diff(globalStart);
        const factor = diff / totalDiff;
        if (ifInBounds && (factor < 0 || 1 <= factor)) {
            return false;
        }
        const rtlFactor = localization.direction === "rtl" ? -1 : 1;
        const scrollLeft =
            factor * this.cellContainerRef.el.clientWidth +
            this.rowHeaderWidth -
            (this.contentRefWidth + this.rowHeaderWidth) / 2;
        this.props.contentRef.el.scrollLeft = rtlFactor * scrollLeft;
        return true;
    }

    focusFirstPill(rowId) {
        const pill = this.rowPills[rowId][0];
        if (pill) {
            const col = this.getFirstGridCol(pill);
            const { start: date } = this.getColumnFromColNumber(col);
            this.focusDate(date);
        }
    }

    focusToday() {
        return this.focusDate(DateTime.local().startOf("day"), true);
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
     * @param {number} startCol
     * @param {number} stopCol
     * @param {boolean} [roundUpStop=true]
     */
    getColumnStartStop(startCol, stopCol, roundUpStop = true) {
        const { start } = this.getColumnFromColNumber(startCol);
        let { stop } = this.getColumnFromColNumber(stopCol);
        if (roundUpStop) {
            stop = stop.plus({ millisecond: 1 });
        }
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
     * @param {Row} row
     * @param {Column} column
     * @return {Object}
     */
    ganttCellAttClass(row, column) {
        return {
            o_sample_data_disabled: this.isDisabled(row),
            o_gantt_today: column.isToday,
            o_gantt_group: row.isGroup,
            o_gantt_hoverable: this.isHoverable(row),
            o_group_open: !this.model.isClosed(row.id),
            o_gantt_readonly: row.readonly,
        };
    }

    getCurrentFocusDate() {
        const { globalStart, globalStop } = this.model.metaData;
        const rtlFactor = localization.direction === "rtl" ? -1 : 1;
        const cellGridMiddleX =
            rtlFactor * this.props.contentRef.el.scrollLeft +
            (this.contentRefWidth + this.rowHeaderWidth) / 2;
        const factor =
            (cellGridMiddleX - this.rowHeaderWidth) / this.cellContainerRef.el.clientWidth;
        const totalDiff = globalStop.diff(globalStart);
        const diff = factor * totalDiff;
        const focusDate = globalStart.plus(diff);
        return focusDate;
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
     * Get schedule parameters
     *
     * @param {Element} pill
     * @returns {Object} - An object containing parameters needed for scheduling the pill.
     */
    getScheduleParams(pill) {
        return {};
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

        const spanAccrossDays = stopDate.startOf("day") > startDate.startOf("day");
        const spanAccrossWeeks = getStartOfLocalWeek(stopDate) > getStartOfLocalWeek(startDate);
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
            const durationStr = this.getDurationStr(record);
            labelElements.push(startDate.toFormat("t"), `${stopDate.toFormat("t")}${durationStr}`);
        }

        // Original Display Name
        if (scaleId !== "month" || !record.allocated_hours || spanAccrossDays) {
            labelElements.push(record.display_name);
        }

        return labelElements.filter((el) => !!el).join(" - ");
    }

    /**
     * @param {RelationalRecord} record
     */
    getDurationStr(record) {
        const durationStr = formatFloatTime(record.allocated_hours, {
            noLeadingZeroHour: true,
        }).replace(/(:00|:)/g, "h");
        return ` (${durationStr})`;
    }

    /**
     * @param {Pill} pill
     */
    getGroupPillDisplayName(pill) {
        return pill.aggregateValue;
    }

    /**
     * @param {{ column?: [number, number], row?: [number, number] }} position
     */
    getGridPosition(position) {
        const style = [];
        const keys = Object.keys(pick(position, "column", "row"));
        for (const key of keys) {
            const prefix = key.slice(0, 1);
            const [first, last] = position[key];
            style.push(`grid-${key}:${prefix}${first}/${prefix}${last}`);
        }
        return style.join(";");
    }

    /**
     * @param {{ column?: [number, number], row?: [number, number] }} position
     */
    getGroupHeaderStyle(position) {
        return this.getGridPosition(position) + `;max-width: ${this.cellContainerWidth}px`;
    }

    setSomeGridStyleProperties() {
        const rowsTemplate = this.computeRowsTemplate();
        const colsTemplate = this.computeColsTemplate();
        this.gridRef.el.style.setProperty("--Gantt__GridRows-grid-template-rows", rowsTemplate);
        this.gridRef.el.style.setProperty(
            "--Gantt__GridColumns-grid-template-columns",
            colsTemplate
        );
    }

    getGridStyle() {
        const rowsTemplate = this.computeRowsTemplate();
        const colsTemplate = this.computeColsTemplate();
        const style = {
            "--Gantt__RowHeader-width": `${this.rowHeaderWidth}px`,
            "--Gantt__Pill-height": "35px",
            "--Gantt__Thumbnail-max-height": "16px",
            "--Gantt__GridRows-grid-template-rows": rowsTemplate,
            "--Gantt__GridColumns-grid-template-columns": colsTemplate,
        };
        if (this.totalWidth !== null) {
            style.width = `${this.totalWidth}px`;
        }
        return Object.entries(style)
            .map((entry) => entry.join(":"))
            .join(";");
    }

    /**
     * @param {RelationalRecord} record
     * @returns {Partial<Pill>}
     */
    getPill(record) {
        const { canEdit, dateStartField, dateStopField, disableDrag, globalStart, globalStop } =
            this.model.metaData;

        const startOutside = record[dateStartField] < globalStart;

        let recordDateStopField = record[dateStopField];
        if (this.model.dateStopFieldIsDate()) {
            recordDateStopField = recordDateStopField.plus({ day: 1 });
        }

        const stopOutside = recordDateStopField > globalStop;

        /** @type {DateTime} */
        const pillStartDate = startOutside ? globalStart : record[dateStartField];
        /** @type {DateTime} */
        const pillStopDate = stopOutside ? globalStop : recordDateStopField;

        const disableStartResize = !canEdit || startOutside;
        const disableStopResize = !canEdit || stopOutside;

        /** @type {Partial<Pill>} */
        const pill = {
            disableDrag: disableDrag || disableStartResize || disableStopResize,
            disableStartResize,
            disableStopResize,
            grid: { column: this.getGridColumnFromDates(pillStartDate, pillStopDate) },
            record,
        };

        return pill;
    }

    getGridColumnFromDates(startDate, stopDate) {
        const { globalStart, scale } = this.model.metaData;
        const { cellPart, interval } = scale;
        const { column: column1, delta: delta1 } = this.getSubColumnFromDate(startDate);
        const { column: column2, delta: delta2 } = this.getSubColumnFromDate(stopDate, false);
        const firstCol = 1 + diffColumn(globalStart, column1, interval) * cellPart + delta1;
        const span = diffColumn(column1, column2, interval) * cellPart + delta2 - delta1;
        return [firstCol, firstCol + span];
    }

    getSubColumnFromDate(date, onLeft = true) {
        const { interval, cellPart, cellTime, time } = this.model.metaData.scale;
        const column = date.startOf(interval);
        let delta;
        if (onLeft) {
            delta = 0;
            for (let i = 1; i < cellPart; i++) {
                const subCellStart = dateAddFixedOffset(column, { [time]: i * cellTime });
                if (subCellStart <= date) {
                    delta += 1;
                } else {
                    break;
                }
            }
        } else {
            delta = cellPart;
            for (let i = cellPart - 1; i >= 0; i--) {
                const subCellStart = dateAddFixedOffset(column, { [time]: i * cellTime });
                if (subCellStart >= date) {
                    delta -= 1;
                } else {
                    break;
                }
            }
        }
        return { column, delta };
    }

    getSubColumnFromColNumber(col) {
        let subColumn = this.mappingColToSubColumn.get(col);
        if (!subColumn) {
            const { globalStart, scale } = this.model.metaData;
            const { interval, cellPart, cellTime, time } = scale;
            const delta = (col - 1) % cellPart;
            const columnIndex = (col - 1 - delta) / cellPart;
            const start = globalStart.plus({ [interval]: columnIndex });
            subColumn = this.makeSubColumn(start, delta, cellTime, time);
            this.mappingColToSubColumn.set(col, subColumn);
        }
        return subColumn;
    }

    getColumnFromColNumber(col) {
        let column = this.mappingColToColumn.get(col);
        if (!column) {
            const { globalStart, scale } = this.model.metaData;
            const { interval, cellPart } = scale;
            const delta = (col - 1) % cellPart;
            const columnIndex = (col - 1 - delta) / cellPart;
            const start = globalStart.plus({ [interval]: columnIndex });
            const stop = start.endOf(interval);
            column = { start, stop };
            this.mappingColToColumn.set(col, column);
        }
        return column;
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
        const { id: resId, display_name: displayName } = record;
        const { canEdit, dateStartField, dateStopField, popoverArchParams, resModel } =
            this.model.metaData;
        const context = popoverArchParams.bodyTemplate
            ? { ...record }
            : /* Default context */ {
                  name: displayName,
                  start: record[dateStartField].toFormat("f"),
                  stop: record[dateStopField].toFormat("f"),
              };

        return {
            ...popoverArchParams,
            title: displayName,
            context,
            resId,
            resModel,
            reload: () => this.model.fetchData(),
            buttons: [
                {
                    id: "open_view_edit_dialog",
                    text: canEdit ? _t("Edit") : _t("View"),
                    class: "btn btn-sm btn-primary",
                    // Sync with the mutex to wait for potential changes on the view
                    onClick: () =>
                        this.model.mutex.exec(
                            () => this.props.openDialog({ resId }) // (canEdit is also considered in openDialog)
                        ),
                },
            ],
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
     * @param {Row} row
     */
    getRowCellColors(row) {
        const { unavailabilities } = row;
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
            if (index < unavailabilities.length) {
                let subSlotUnavailable = 0;
                for (let i = index; i < unavailabilities.length; i++) {
                    const u = unavailabilities[i];
                    if (stop > u.stop) {
                        index++;
                        continue;
                    } else if (u.start <= start) {
                        subSlotUnavailable = 1;
                    }
                    break;
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

    getFromData(groupedByField, resId, key, defaultVal) {
        const values = this.model.data[key];
        if (groupedByField) {
            return values[groupedByField]?.[resId ?? false] || defaultVal;
        }
        return values.__default?.false || defaultVal;
    }

    /**
     * @param {string} [groupedByField]
     * @param {false|number} [resId]
     * @returns {Object}
     */
    getRowProgressBar(groupedByField, resId) {
        return this.getFromData(groupedByField, resId, "progressBars", null);
    }

    /**
     * @param {string} [groupedByField]
     * @param {false|number} [resId]
     * @returns {{ start: DateTime, stop: DateTime }[]}
     */
    getRowUnavailabilities(groupedByField, resId) {
        return this.getFromData(groupedByField, resId, "unavailabilities", []);
    }

    /**
     * @param {"t0" | "t1" | "t2"} type
     * @returns {number}
     */
    getRowTypeHeight(type) {
        return {
            t0: 24,
            t1: 36,
            t2: 16,
        }[type];
    }

    getRowTitleStyle(row) {
        return `grid-column: ${row.groupLevel + 2} / -1`;
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
            rows: [],
            name: _t("Total"),
            recordIds: pills.map(({ record }) => record.id),
        };

        this.currentGridRow = 1;
        const result = this.processRow(preRow, pills);
        const [totalRow] = result.rows;
        const allPills = this.rowPills[totalRow.id] || [];
        const maxAggregateValue = Math.max(...allPills.map((p) => p.aggregateValue));

        totalRow.factor = maxAggregateValue ? 90 / maxAggregateValue : 0;

        return totalRow;
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
        return this.cellPartWidth * pill.grid.column[1] < pill.displayName.length * 10;
    }

    /**
     * @param {Row} row
     */
    isDisabled(row = null) {
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
            group.aggregateValue = this.getAggregateValue(group, previousGroup);
        }
        return [...left, ...right];
    }

    onWillRender() {
        if (this.noDisplayedConnectors && this.shouldRenderConnectors()) {
            delete this.noDisplayedConnectors;
            this.computeDerivedParams();
        }

        if (this.shouldComputeSomeWidths) {
            this.computeSomeWidths();
        }

        if (this.shouldComputeSomeWidths || this.shouldComputeGridColumns) {
            this.virtualGrid.setColumnsWidths(new Array(this.columnCount).fill(this.columnWidth));
            this.computeVisibleColumns();
        }

        if (this.shouldComputeGridRows) {
            this.virtualGrid.setRowsHeights(this.gridRows);
            this.computeVisibleRows();
        }

        if (
            this.shouldComputeSomeWidths ||
            this.shouldComputeGridColumns ||
            this.shouldComputeGridRows
        ) {
            delete this.shouldComputeSomeWidths;
            delete this.shouldComputeGridColumns;
            delete this.shouldComputeGridRows;
            this.computeVisiblePills();
            if (this.shouldRenderConnectors()) {
                this.computeVisibleConnectors();
            } else {
                this.noDisplayedConnectors = true;
            }
        }

        if (this.containsReadonlyGroup()) {
            this.setupInitialReadonly();
        }

        delete this.shouldComputeSomeWidths;
        delete this.shouldComputeGridColumns;
        delete this.shouldComputeGridRows;
    }

    pushGridRows(gridRows) {
        for (const key of ["t0", "t1", "t2"]) {
            if (key in gridRows) {
                const types = new Array(gridRows[key]).fill(this.getRowTypeHeight(key));
                this.gridRows.push(...types);
            }
        }
    }

    processPillsAsRows(row, pills) {
        const rows = [];
        const parsedId = JSON.parse(row.id);
        if (pills.length) {
            for (const pill of pills) {
                const { id: resId, display_name: name } = pill.record;
                const subRow = {
                    id: JSON.stringify([...parsedId, { id: resId }]),
                    resId,
                    name,
                    groupLevel: row.groupLevel + 1,
                    recordIds: [resId],
                    fromServer: row.fromServer,
                    parentResId: row.resId ?? row.parentResId,
                    parentGroupedField: row.groupedByField || row.parentGroupedField,
                };
                const res = this.processRow(subRow, [pill], false);
                rows.push(...res.rows);
            }
        } else {
            const subRow = {
                id: JSON.stringify([...parsedId, {}]),
                resId: false,
                name: "",
                groupLevel: row.groupLevel + 1,
                recordIds: [],
                fromServer: row.fromServer,
                parentResId: row.resId ?? row.parentResId,
                parentGroupedField: row.groupedByField || row.parentGroupedField,
            };
            const res = this.processRow(subRow, [], false);
            rows.push(...res.rows);
        }

        return rows;
    }

    /**
     * @param {Row} row
     * @param {Pill[]} pills
     * @param {boolean} [processAsGroup=false]
     */
    processRow(row, pills, processAsGroup = true) {
        const { dependencyField, displayUnavailability, fields } = this.model.metaData;
        const { displayMode } = this.model.displayParams;
        const {
            consolidate,
            fromServer,
            groupedByField,
            groupLevel,
            id,
            name,
            parentResId,
            parentGroupedField,
            resId,
            rows,
            recordIds,
            __extra__,
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

        if (displayMode === "sparse" && __extra__) {
            const rows = this.processPillsAsRows(row, groupPills);
            return { rows, pillsToProcess: remainingPills };
        }

        const isGroup = displayMode === "sparse" ? processAsGroup : Boolean(rows);

        const gridRowTypes = isGroup ? { t0: 1 } : { t1: 1 };
        if (rowPills.length) {
            if (isGroup) {
                if (this.shouldComputeAggregateValues(row)) {
                    const groups = this.aggregatePills(rowPills, row);
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
                gridRowTypes.t1 = level;
                if (!this.isTouchDevice) {
                    gridRowTypes.t2 = 1;
                }
            }
        }

        const progressBar = this.getRowProgressBar(groupedByField, resId);
        if (progressBar && this.isTouchDevice && (!gridRowTypes.t1 || gridRowTypes.t1 === 1)) {
            // In mobile: rows span over 2 rows to alllow progressbars to properly display
            gridRowTypes.t1 = (gridRowTypes.t1 || 0) + 1;
        }
        if (row.id !== "[]") {
            this.pushGridRows(gridRowTypes);
        }

        for (const rowPill of rowPills) {
            rowPill.id = `__pill__${this.nextPillId++}`;
            const pillFirstRow = this.currentGridRow + rowPill.level;
            rowPill.grid = {
                ...rowPill.grid, // rowPill is a shallow copy of a prePill (possibly copied several times)
                row: [pillFirstRow, pillFirstRow + 1],
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
            rowPill.rowId = id;
            this.pills[rowPill.id] = rowPill;
        }

        this.rowPills[id] = rowPills; // all row pills

        const subRowsCount = Object.values(gridRowTypes).reduce((acc, val) => acc + val, 0);
        /** @type {Row} */
        const processedRow = {
            cellColors: {},
            fromServer,
            groupedByField,
            groupLevel,
            id,
            isGroup,
            name,
            progressBar,
            resId,
            grid: {
                row: [this.currentGridRow, this.currentGridRow + subRowsCount],
            },
        };
        if (displayUnavailability && !isGroup) {
            processedRow.unavailabilities = this.getRowUnavailabilities(
                parentGroupedField || groupedByField,
                parentResId ?? resId
            );
        }

        this.rowByIds[id] = processedRow;

        this.currentGridRow += subRowsCount;

        const field = this.model.metaData.thumbnails[groupedByField];
        if (field) {
            const model = this.model.metaData.fields[groupedByField].relation;
            processedRow.thumbnailUrl = url("/web/image", {
                model,
                id: resId,
                field,
            });
        }

        const result = { rows: [processedRow], pillsToProcess: remainingPills };

        if (!this.model.isClosed(id)) {
            if (rows) {
                let pillsToProcess = groupPills;
                for (const subRow of rows) {
                    const res = this.processRow(subRow, pillsToProcess);
                    result.rows.push(...res.rows);
                    pillsToProcess = res.pillsToProcess;
                }
            } else if (displayMode === "sparse" && processAsGroup) {
                const rows = this.processPillsAsRows(row, groupPills);
                result.rows.push(...rows);
            }
        }

        return result;
    }

    /**
     * @param {string} [groupedByField]
     * @param {false|number} [resId]
     * @returns {{ start: DateTime, stop: DateTime }[]}
     */
    _getRowUnavailabilities(groupedByField, resId) {
        const { unavailabilities } = this.model.data;
        if (groupedByField) {
            return unavailabilities[groupedByField]?.[resId ?? false] || [];
        }
        return unavailabilities.__default?.false || [];
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
        const params = this.getScheduleParams(pill);

        if (direction === "start") {
            params.start = dateAddFixedOffset(record[dateStartField], { [time]: cellTime * diff });
            if (params.start > record[dateStopField]) {
                return this.notificationService.add(
                    _t("Starting date cannot be after the ending date"),
                    {
                        type: "warning",
                    }
                );
            }
        } else {
            params.stop = dateAddFixedOffset(record[dateStopField], { [time]: cellTime * diff });
            if (params.stop < record[dateStartField]) {
                return this.notificationService.add(
                    _t("Ending date cannot be before the starting date"),
                    {
                        type: "warning",
                    }
                );
            }
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
     * @param {HTMLElement} [pillEl]
     */
    setStickyPill(pillEl) {
        this.stickyPillId = pillEl ? pillEl.dataset.pillId : null;
    }

    /**
     * @returns {boolean}: whether one of the "groupedBy" fields of the model is readonly
     */
    containsReadonlyGroup() {
        return this.model.metaData.groupedBy.some((groupedByField) => {
            return this.model.metaData.fields[groupedByField].readonly;
        });
    }

    /**
     * For all rows to render, specify whether the row is grouped by a readonly
     * field or is a child of a row grouped by a readonly field - by setting its'
     * 'readonly' and 'readonlyChild' properties.
     */
    setupInitialReadonly() {
        let foundReadonlyField = false;
        const readonlyGroups = [];
        const readonlyChildren = [];
        for (const groupedByField of this.props.model.metaData.groupedBy) {
            // Field itself is readonly
            if (this.model.metaData.fields[groupedByField].readonly) {
                foundReadonlyField = true;
                readonlyGroups.push(groupedByField);
            }
            // There is a readonly parent group
            else if (foundReadonlyField) {
                readonlyChildren.push(groupedByField);
            }
        }

        for (const row of this.rowsToRender) {
            row.readonlyChild = readonlyChildren.includes(row.groupedByField);
            row.readonly = readonlyGroups.includes(row.groupedByField) || row.readonlyChild;
        }
    }

    /**
     * @param {boolean} addReadonly: whether to add or remove the readonly class
     */
    toggleRowsReadonly(addReadonly) {
        if (!this.stickyPillId || !this.containsReadonlyGroup()) {
            return;
        }
        const startingRowId = this.pills[this.stickyPillId].rowId;
        const rowIdx = this.rows.findIndex((r) => r.id === startingRowId);
        this.toggleReadonly(this.rows[rowIdx], addReadonly);
        // Also update rows that are part of the same "child group"
        if (this.rows[rowIdx].readonlyChild) {
            for (const row of this.rows.slice(0, rowIdx).reverse()) {
                if (!row.readonlyChild) {
                    break;
                }
                this.toggleReadonly(row, addReadonly);
            }
            for (const row of this.rows.slice(rowIdx + 1, this.rows.length)) {
                if (!row.readonlyChild) {
                    break;
                }
                this.toggleReadonly(row, addReadonly);
            }
        }
    }

    toggleReadonly(row, addReadonly) {
        for (const cell of getCellsOnRow(this.gridRef.el, row.id)) {
            if (addReadonly) {
                cell.classList.add("o_gantt_readonly");
            } else {
                cell.classList.remove("o_gantt_readonly");
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
     *
     * @return {boolean}
     */
    shouldRenderConnectors() {
        return (
            this.model.metaData.dependencyField && !this.model.useSampleModel && !this.env.isSmall
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

    onCellClicked(rowId, col) {
        if (!this.preventClick) {
            this.preventClick = true;
            setTimeout(() => (this.preventClick = false), 1000);
            const { canCellCreate, canPlan } = this.model.metaData;
            if (canPlan) {
                this.onPlan(rowId, col, col);
            } else if (canCellCreate) {
                this.onCreate(rowId, col, col);
            }
        }
    }

    onCreate(rowId, startCol, stopCol) {
        const { start, stop } = this.getColumnStartStop(startCol, stopCol);
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
        if (this.gridRef.el) {
            for (const [action, className] of INTERACTION_CLASSNAMES) {
                this.gridRef.el.classList.toggle(className, mode === action);
            }
        }
    }

    onPointerLeave() {
        this.throttledComputeHoverParams.cancel();

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
     * @param {Event} ev
     */
    computeHoverParams(ev) {
        // Lazily compute elements from point as it is a costly operation
        let els = null;
        let position = {};
        if (ev.type === "scroll") {
            position = this.cursorPosition;
        } else {
            position.x = ev.clientX;
            position.y = ev.clientY;
            this.cursorPosition = position;
        }
        const pointedEls = () => els || (els = document.elementsFromPoint(position.x, position.y));

        // To find hovered elements, also from pointed elements
        const find = (selector) =>
            ev.target.closest?.(selector) ||
            pointedEls().find((el) => el.matches(selector)) ||
            null;

        this.hovered.connector = find(".o_gantt_connector");
        this.hovered.hoverable = find(".o_gantt_hoverable");
        this.hovered.pill = find(".o_gantt_pill_wrapper");

        this.computeDerivedParamsFromHover();
    }

    /**
     * @param {PointerEvent} ev
     * @param {Pill} pill
     */
    onPillClicked(ev, pill) {
        if (this.popover.isOpen) {
            return;
        }
        this.popover.target = ev.target.closest(".o_gantt_pill_wrapper");
        this.popover.open(this.popover.target, this.getPopoverProps(pill));
    }

    onPlan(rowId, startCol, stopCol) {
        const { start, stop } = this.getColumnStartStop(startCol, stopCol);
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
    rescheduleAccordingToDependencyCallback(result) {
        const isWarning = result.type === "warning";
        if (!isWarning && "old_vals_per_pill_id" in result) {
            this.model.toggleHighlightPlannedFilter(
                Object.keys(result["old_vals_per_pill_id"]).map(Number)
            );
        }
        this.notificationFn?.();
        const icon = isWarning ? "fa-warning" : "fa-check";
        this.notificationFn = this.notificationService.add(
            markup(
                `<i class="fa ${icon}"></i><span class="ms-1">${escape(result["message"])}</span>`
            ),
            {
                type: result["type"],
                sticky: true,
                buttons:
                    isWarning || !result.old_vals_per_pill_id
                        ? []
                        : [
                              {
                                  name: "Undo",
                                  icon: "fa-undo",
                                  onClick: async () => {
                                      const ids = Object.keys(result["old_vals_per_pill_id"]).map(
                                          Number
                                      );
                                      await this.orm.call(
                                          this.model.metaData.resModel,
                                          "action_rollback_scheduling",
                                          [ids, result["old_vals_per_pill_id"]]
                                      );
                                      this.notificationFn();
                                      await this.model.fetchData();
                                  },
                              },
                          ],
            }
        );
    }

    /**
     *
     * @param {"forward" | "backward"} direction
     * @param {ConnectorId} connectorId
     */
    async onRescheduleButtonClick(direction, connectorId) {
        const { masterId, slaveId } = this.getRecordIds(connectorId);
        await this.model.rescheduleAccordingToDependency(
            direction,
            masterId,
            slaveId,
            this.rescheduleAccordingToDependencyCallback.bind(this)
        );
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
    }

    /**
     * @param {KeyboardEvent} ev
     */
    onWindowKeyUp(ev) {
        if (ev.key === "Control") {
            this.interaction.dragAction = this.prevDragAction || "reschedule";
        }
    }
}
