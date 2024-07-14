/** @odoo-module **/

import { click, drag, getFixture, triggerEvent, triggerEvents } from "@web/../tests/helpers/utils";
import { GanttRenderer } from "@web_gantt/gantt_renderer";

/**
 * @typedef CellHelperOptions
 * @property {number} [part=1] -- starts at 1
 * @property {boolean} [ignoreHoverableClass=false]
 */

/**
 * @typedef PillHelperOptions
 * @property {number} [nth=1] -- starts at 1
 */

/**
 * @typedef DragPillHelpers
 * @property {() => Promise<void>} cancel
 * @property {(params: DragParams) => Promise<void>} drop
 * @property {(params: DragParams) => Promise<void>} moveTo
 */

/**
 * @template T
 * @typedef {(row: number, column: number, options: CellHelperOptions) => T} CellHelper
 */

/**
 * @template T
 * @typedef {(text: string, options: PillHelperOptions) => T} PillHelper
 */

/** @typedef {CellHelperOptions & { row: number, column: number }} DragGridParams */

/** @typedef {PillHelperOptions & { pill: string }} DragPillParams */

/** @typedef {DragGridParams | DragPillParams} DragParams */

/**
 * @template {String} T
 * @param {T} key
 * @returns {`.${T}`}
 */
function makeClassSelector(key) {
    return `.${key}`;
}

export const CLASSES = {
    draggable: "o_draggable",
    group: "o_gantt_group",
    highlightedPill: "highlight",
    resizable: "o_resizable",

    // Connectors
    highlightedConnector: "o_connector_highlighted",
    highlightedConnectorCreator: "o_connector_creator_highlight",
    lockedConnectorCreator: "o_connector_creator_lock", // Connector creators highlight for initial pill
};

export const SELECTORS = {
    addButton: ".o_gantt_button_add",
    cell: ".o_gantt_cell",
    cellAddButton: ".o_gantt_cell_add",
    cellButtons: ".o_gantt_cell_buttons",
    cellContainer: ".o_gantt_cells",
    cellPlanButton: ".o_gantt_cell_plan",
    collapseButton: ".o_gantt_button_collapse_rows",
    draggable: makeClassSelector(CLASSES.draggable),
    expandButton: ".o_gantt_button_expand_rows",
    expandCollapseButtons: ".o_gantt_button_expand_rows, .o_gantt_button_collapse_rows",
    group: makeClassSelector(CLASSES.group),
    headerCell: ".o_gantt_header_cell",
    highlightedPill: makeClassSelector(CLASSES.highlightedPill),
    hoverable: ".o_gantt_hoverable",
    nextButton: ".o_gantt_button_next",
    noContentHelper: ".o_view_nocontent",
    pill: ".o_gantt_pill",
    pillWrapper: ".o_gantt_pill_wrapper",
    prevButton: ".o_gantt_button_prev",
    progressBar: ".o_gantt_row_header .o_gantt_progress_bar",
    progressBarBackground: ".o_gantt_row_header .o_gantt_progress_bar > span.bg-opacity-25",
    progressBarForeground:
        ".o_gantt_row_header .o_gantt_progress_bar > span > .o_gantt_group_hours",
    progressBarWarning:
        ".o_gantt_row_header .o_gantt_progress_bar > .o_gantt_group_hours > .fa-exclamation-triangle",
    renderer: ".o_gantt_renderer",
    resizable: makeClassSelector(CLASSES.resizable),
    resizeBadge: ".o_gantt_pill_resize_badge",
    resizeEndHandle: ".o_handle_end",
    resizeHandle: ".o_resize_handle",
    resizeStartHandle: ".o_handle_start",
    rowHeader: ".o_gantt_row_header",
    rowTitle: ".o_gantt_row_title",
    rowTotal: ".o_gantt_row_total",
    thumbnail: ".o_gantt_row_thumbnail",
    todayButton: ".o_gantt_button_today",
    undraggable: ".o_undraggable",
    view: ".o_gantt_view",
    viewContent: ".o_gantt_view .o_content",

    // Connectors
    connector: ".o_gantt_connector",
    connectorCreatorBullet: ".o_connector_creator_bullet",
    connectorCreatorRight: ".o_connector_creator_right",
    connectorCreatorWrapper: ".o_connector_creator_wrapper",
    connectorRemoveButton: ".o_connector_stroke_remove_button",
    connectorRescheduleButton: ".o_connector_stroke_reschedule_button",
    connectorStroke: ".o_connector_stroke",
    connectorStrokeButton: ".o_connector_stroke_button",
    highlightedConnector: makeClassSelector(CLASSES.highlightedConnector),
};

/**
 * @param {string} selector
 * @returns {string | null}
 */
export function getText(selector) {
    const texts = getTexts(selector);
    return texts.length ? texts[0] : null;
}

/**
 * @param {string} selector
 * @returns {string[]}
 */
export function getTexts(selector) {
    const elements = [];
    if (typeof selector === "string") {
        elements.push(...getFixture().querySelectorAll(selector));
    } else if (selector[Symbol.iterator]) {
        elements.push(...selector);
    } else {
        elements.push(selector);
    }
    return elements.map((el) => el.innerText.trim().replace(/\n/g, ""));
}

export function getActiveScale() {
    return getText(".scale_button_selection");
}

/**
 * @param {string} scale
 */
export async function setScale(scale) {
    const fixture = getFixture();
    if (!fixture.querySelector(".scale_button_selection + .o-dropdown--menu")) {
        // open scale menu
        await click(fixture, ".scale_button_selection");
    }
    await click(fixture, `.o_scale_button_${scale}`);
}

/** @type {PillHelper<Promise<DragPillHelpers>>} */
export async function dragPill(text, options) {
    /** @param {DragParams} params */
    const drop = async (params) => {
        await moveTo(params);
        return dragActions.drop();
    };

    /** @param {DragParams} params */
    const moveTo = async (params) => {
        let cell;
        if (params?.row && params?.column) {
            cell = await hoverGridCell(params.row, params.column, params);
        } else if (params?.pill) {
            cell = await hoverPillCell(getPillWrapper(params.pill, params));
        }
        return dragActions.moveTo(cell);
    };

    const pill = getPillWrapper(text, options);
    await hoverPillCell(pill);
    const dragActions = await drag(pill);

    return { ...dragActions, drop, moveTo };
}

/** @type {PillHelper<Promise<void>>} */
export async function editPill(text, options) {
    await click(getPill(text, options));
    await click(getFixture(), ".o_popover .popover-footer .btn-primary");
}

/** @type {CellHelper<HTMLElement>} */
export function getCell(row, column, options) {
    const ignoreHoverableClass = options?.ignoreHoverableClass ?? false;
    const selector = `${SELECTORS.cell}[data-column-index='${column - 1}']`;
    let currentRowNumber = 0;
    let currentGridRowStart = 0;
    for (const cell of getFixture().querySelectorAll(selector)) {
        const [rowStart] = getGridStyle(cell).row;
        if (currentGridRowStart !== rowStart) {
            currentGridRowStart = rowStart;
            currentRowNumber += 1;
        }
        if (
            row === currentRowNumber &&
            (ignoreHoverableClass || cell.matches(SELECTORS.hoverable))
        ) {
            return cell;
        }
    }
    throw new Error(`Could not find hoverable cell at row ${row} and column ${column}`);
}

/** @type {CellHelper<string[]>} */
export function getCellColorProperties(row, column) {
    const cell = getCell(row, column, { ignoreHoverableClass: true });
    const cssVarRegex = /(--[\w-]+)/g;

    if (cell.style.background) {
        return cell.style.background.match(cssVarRegex);
    } else if (cell.style.backgroundColor) {
        return cell.style.backgroundColor.match(cssVarRegex);
    } else if (cell.style.backgroundImage) {
        return cell.style.backgroundImage.match(cssVarRegex);
    }

    return [];
}

/**
 * @param {HTMLElement} pill
 * @returns {HTMLElement}
 */
export function getCellFromPill(pill) {
    if (!pill.matches(SELECTORS.pillWrapper)) {
        pill = pill.closest(SELECTORS.pillWrapper);
    }
    const { row, column } = getGridStyle(pill);
    for (const cell of getFixture().querySelectorAll(SELECTORS.cell)) {
        const { row: cellRow, column: cellColumn } = getGridStyle(cell);
        if (row[0] < cellRow[0] + cellRow[1] && column[0] < cellColumn[0] + cellColumn[1]) {
            return cell;
        }
    }
    throw new Error(`Could not find hoverable cell for pill "${getText(pill)}".`);
}

export function getGridContent() {
    const fixture = getFixture();

    const columnHeaders = getTexts(".o_gantt_header_cell");
    const range = getTexts(".o_gantt_header_scale > div > *:not(.o_gantt_header_cell)")[2];
    const viewTitle = getText(".o_gantt_title");

    const renderer = fixture.querySelector(SELECTORS.renderer);
    const templateColumns = Number(renderer.style.getPropertyValue("--Gantt__Template-columns"));
    const cellParts = templateColumns / columnHeaders.length;
    const pillEls = new Set(
        fixture.querySelectorAll(`${SELECTORS.cellContainer} ${SELECTORS.pillWrapper}`)
    );
    const rowEls = [...fixture.querySelectorAll(`.o_gantt_row_headers > ${SELECTORS.rowHeader}`)];
    const singleRowMode = rowEls.length === 0;
    if (singleRowMode) {
        rowEls.push(document.createElement("div"));
    }
    const totalRow = fixture.querySelector(SELECTORS.rowTotal);
    const totalPillEls = new Set(
        fixture.querySelectorAll(`.o_gantt_row_total ${SELECTORS.pillWrapper}`)
    );
    if (totalRow) {
        totalRow._isTotal = true;
        rowEls.push(totalRow);
    }
    const rows = [];
    for (const rowEl of rowEls) {
        const isGroup = rowEl.classList.contains(CLASSES.group);
        const { row: gridRow } = getGridStyle(rowEl);
        const rowEndLevel = gridRow[0] - 1 + gridRow[1];
        const row = singleRowMode ? {} : { title: getText(rowEl) };
        if (isGroup) {
            row.isGroup = true;
        }
        if (rowEl._isTotal) {
            row.isTotalRow = true;
        }
        const pills = [];
        for (const pillEl of rowEl._isTotal ? totalPillEls : pillEls) {
            const pillRowLevel = Number(pillEl.style.gridRowStart);
            const { column: gridColumn } = getGridStyle(pillEl);
            const columnEnd = gridColumn[0] - 1 + gridColumn[1];
            const pillInRow = pillRowLevel >= gridRow[0] && pillRowLevel < rowEndLevel;
            if (singleRowMode || pillInRow || rowEl._isTotal) {
                let start = columnHeaders[Math.floor((gridColumn[0] - 1) / cellParts)];
                let end = columnHeaders[Math.floor((columnEnd - 1) / cellParts)];
                const startPart = (gridColumn[0] - 1) % cellParts;
                const endPart = columnEnd % cellParts;
                if (startPart) {
                    start += ` (${startPart}/${cellParts})`;
                }
                if (endPart) {
                    end += ` (${endPart}/${cellParts})`;
                }
                const pill = {
                    title: getText(pillEl),
                    colSpan: `${start} -> ${end}`,
                };
                if (!isGroup) {
                    pill.level = singleRowMode
                        ? (pillRowLevel - 1) / GanttRenderer.ROW_SPAN
                        : (pillRowLevel - gridRow[0]) / GanttRenderer.ROW_SPAN;
                }
                pills.push(pill);
                pillEls.delete(pillEl);
            }
        }
        if (pills.length) {
            row.pills = pills;
        }
        rows.push(row);
    }

    return { columnHeaders, range, rows, viewTitle };
}

/**
 * @param {HTMLElement} el
 */
export function getGridStyle(el) {
    /**
     * @param {"row" | "column"} prop
     * @returns {[number, number]}
     */
    const getGridProp = (prop) => {
        const values = [Number(style.getPropertyValue(`grid-${prop}-start`))];
        const end = style.getPropertyValue(`grid-${prop}-end`);
        const [spanKey, span] = end.split(" ");
        if (spanKey === "span") {
            values.push(Number(span));
        } else {
            values.push(Number(spanKey) || 1);
        }
        return values;
    };

    const style = getComputedStyle(el);

    return {
        row: getGridProp("row"),
        column: getGridProp("column"),
    };
}

/**
 * @param {HTMLElement} cell
 * @param {CellHelperOptions} [options]
 */
async function hoverCell(cell, options) {
    const part = options?.part ?? 1;
    const rect = cell.getBoundingClientRect();
    const evAttrs = {
        clientX: rect.x,
        clientY: rect.y,
    };

    if (part > 1) {
        const columnHeadersCount = getTexts(".o_gantt_header_cell").length;
        const gridStyle = getComputedStyle(cell.parentElement);
        const templateColumns = Number(gridStyle.getPropertyValue("--Gantt__Template-columns"));
        const cellParts = templateColumns / columnHeadersCount;
        const partWidth = rect.width / cellParts;

        evAttrs.clientX += Math.ceil(partWidth * (part - 1));
    }

    await triggerEvents(cell, null, ["pointerenter", ["pointermove", evAttrs]]);
}

/**
 * Hovers a cell found from given grid coordinates.
 * @type {CellHelper<Promise<HTMLElement>>}
 */
export async function hoverGridCell(row, column, options) {
    const cell = getCell(row, column, options);
    await hoverCell(cell, options);
    return cell;
}

/**
 * Click on a cell found from given grid coordinates.
 * @type {CellHelper<Promise<HTMLElement>>}
 */
export async function clickCell(row, column, options) {
    const cell = getCell(row, column, options);
    await click(cell);
}

/**
 * Hovers a cell found from a pill element.
 * @param {HTMLElement} pill
 * @returns {Promise<HTMLElement>}
 */
async function hoverPillCell(pill) {
    const cell = getCellFromPill(pill);
    const pStart = getGridStyle(pill).column[0];
    const cellStyle = getGridStyle(cell).column[0];
    const part = pStart - cellStyle + 1;
    await hoverCell(cell, { part });
    return cell;
}

/**
 * @param {HTMLElement} pill
 * @param {"start" | "end"} side
 * @param {number | { x: number }} deltaOrPosition
 * @param {boolean} [shouldDrop=true]
 */
export async function resizePill(pill, side, deltaOrPosition, shouldDrop = true) {
    const drop = async () => {
        await dropHandle();
        await triggerEvent(pill, null, "pointerleave");
    };

    await triggerEvent(pill, null, "pointerenter");

    const { row, column } = getGridStyle(pill);

    // Calculate cell parts
    const columnHeadersCount = getTexts(".o_gantt_header_cell").length;
    const gridStyle = getComputedStyle(pill.parentElement);
    const templateColumns = Number(gridStyle.getPropertyValue("--Gantt__Template-columns"));
    const cellParts = templateColumns / columnHeadersCount;

    // Calculate delta or position
    const delta = typeof deltaOrPosition === "object" ? 0 : deltaOrPosition;
    const position = typeof deltaOrPosition === "object" ? deltaOrPosition : {};
    const targetColumn = column[0] + (column[1] - 1) + delta * cellParts;

    let targetCell;
    let targetPart;
    for (const cell of getFixture().querySelectorAll(SELECTORS.cell)) {
        const { row: cRow, column: cCol } = getGridStyle(cell);
        if (cRow[0] !== row[0]) {
            continue;
        }
        if (cCol[0] <= targetColumn && targetColumn < cCol[0] + cCol[1]) {
            targetCell = cell;
            targetPart = targetColumn - cCol[0];
            break;
        }
    }

    // Assign position if delta
    if (!position.x) {
        const rect = targetCell.getBoundingClientRect();
        position.x = (targetPart + 0.5) * (rect.width / cellParts);
    }

    // Actual drag actions
    const { moveTo, drop: dropHandle } = await drag(
        pill.querySelector(
            side === "start" ? SELECTORS.resizeStartHandle : SELECTORS.resizeEndHandle
        )
    );

    await moveTo(targetCell, position);

    if (shouldDrop) {
        await drop();
    } else {
        return drop;
    }
}

/** @type {PillHelper<HTMLElement>} */
export function getPill(text, options) {
    const nth = options?.nth ?? 1;
    const regex = new RegExp(text, "i");
    const pill = [...getFixture().querySelectorAll(SELECTORS.pill)].filter((pill) =>
        regex.test(getText(pill))
    )[nth - 1];
    if (!pill) {
        throw new Error(`Could not find pill with text "${text}" (nth: ${nth})`);
    }
    return pill;
}

/** @type {PillHelper<HTMLElement>} */
export function getPillWrapper(text, options) {
    return getPill(text, options).closest(SELECTORS.pillWrapper);
}
