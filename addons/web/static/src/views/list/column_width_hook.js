// @ts-check
/** @odoo-module native */

import {
    onMounted,
    onWillUnmount,
    status,
    useComponent,
    useEffect,
    useExternalListener,
} from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { localization } from "@web/core/l10n/localization";
import { measure, mutate } from "@web/core/utils/dom/layout_batch";
import { useDebounced } from "@web/core/utils/timing";
import { FIELD_WIDTHS } from "@web/fields/field_widths";

const DEFAULT_MIN_WIDTH = 80;
const SELECTOR_WIDTH = 20;
const OPEN_FORM_VIEW_BUTTON_WIDTH = 54;
const DELETE_BUTTON_WIDTH = 12;

/**
 * @param {HTMLTableElement} table
 * @param {{
 * columns: any[],
 * isEmpty: boolean,
 * hasSelectors: boolean,
 * hasOpenFormViewColumn: boolean,
 * hasActionsColumn: boolean,
 * }} state
 * @param {number} allowedWidth
 * @param {number[] | null} [startingWidths]
 * @param {number[]} [contentWidths]
 * @returns {Number[]}
 */
function computeWidths(table, state, allowedWidth, startingWidths, contentWidths = []) {
    let _columnWidths;
    const headers = [...table.querySelectorAll("thead th")];
    const columns = state.columns;
    const columnOffset = state.hasSelectors ? 1 : 0;
    const columnWidthSpecs = getWidthSpecs(columns, allowedWidth);
    const contentSized = columnWidthSpecs.map((spec) => spec.contentSized);

    if (startingWidths) {
        _columnWidths = startingWidths.slice();
    } else if (state.isEmpty) {
        _columnWidths = headers.map(() => allowedWidth / headers.length);
    } else {
        table.style.tableLayout = "auto";
        headers.forEach((th) => {
            th.style.width = "";
        });
        contentSized.forEach((fit, index) => {
            if (fit) {
                headers[index + columnOffset].style.width = "1px";
            }
        });
        table.classList.add("o_list_computing_widths");
        _columnWidths = headers.map((th) => th.getBoundingClientRect().width);
        table.classList.remove("o_list_computing_widths");
    }

    if (state.hasSelectors) {
        _columnWidths[0] = SELECTOR_WIDTH;
    }
    if (state.hasOpenFormViewColumn) {
        const index = _columnWidths.length - (state.hasActionsColumn ? 2 : 1);
        _columnWidths[index] = OPEN_FORM_VIEW_BUTTON_WIDTH;
    }
    if (state.hasActionsColumn) {
        _columnWidths[_columnWidths.length - 1] = DELETE_BUTTON_WIDTH;
    }
    contentSized.forEach((fit, index) => {
        if (fit && !state.isEmpty) {
            const thIndex = index + columnOffset;
            contentWidths[index] ??= Math.max(
                columnWidthSpecs[index].minWidth,
                _columnWidths[thIndex] -
                    (startingWidths ? 0 : getHorizontalPadding(headers[thIndex])),
            );
            columnWidthSpecs[index].maxWidth = contentWidths[index];
        }
    });
    for (let columnIndex = 0; columnIndex < columns.length; columnIndex++) {
        const thIndex = columnIndex + columnOffset;
        const { minWidth, maxWidth } = columnWidthSpecs[columnIndex];
        if (_columnWidths[thIndex] < minWidth) {
            _columnWidths[thIndex] = minWidth;
        } else if (maxWidth && _columnWidths[thIndex] > maxWidth) {
            _columnWidths[thIndex] = maxWidth;
        }
    }

    const totalWidth = _columnWidths.reduce((tot, width) => tot + width, 0);
    const diff = totalWidth - allowedWidth;
    if (diff >= 1) {
        const preferredSpecs = columnWidthSpecs.map((spec) =>
            spec.contentSized && spec.maxWidth
                ? { ...spec, minWidth: spec.maxWidth }
                : spec,
        );
        const remaining = shrinkColumns(
            _columnWidths,
            columns,
            preferredSpecs,
            columnOffset,
            diff,
        );
        if (remaining >= 1) {
            shrinkColumns(
                _columnWidths,
                columns,
                columnWidthSpecs,
                columnOffset,
                remaining,
            );
        }
    } else if (diff <= -1) {
        expandColumns(_columnWidths, columns, columnWidthSpecs, columnOffset, -diff);
    }
    return _columnWidths;
}

/**
 * @param {number[]} widths
 * @param {any[]} columns
 * @param {{ minWidth: number, maxWidth?: number, canShrink: boolean, contentSized?: boolean }[]} specs
 * @param {number} columnOffset
 * @param {number} diff
 * @returns {number} Unallocated overflow after shrinking eligible columns.
 */
function shrinkColumns(widths, columns, specs, columnOffset, diff) {
    const shrinkableColumns = [];
    let totalAvailableSpace = 0;
    for (let columnIndex = 0; columnIndex < columns.length; columnIndex++) {
        const thIndex = columnIndex + columnOffset;
        const { minWidth, canShrink } = specs[columnIndex];
        if (widths[thIndex] > minWidth && canShrink) {
            shrinkableColumns.push({ thIndex, minWidth });
            totalAvailableSpace += widths[thIndex] - minWidth;
        }
    }
    if (diff > totalAvailableSpace) {
        for (const { thIndex, minWidth } of shrinkableColumns) {
            widths[thIndex] = minWidth;
        }
        return diff - totalAvailableSpace;
    }
    let remainingColumnsToShrink = shrinkableColumns.length;
    while (diff >= 1 && remainingColumnsToShrink > 0) {
        const colDiff = diff / remainingColumnsToShrink;
        for (const { thIndex, minWidth } of shrinkableColumns) {
            const currentWidth = widths[thIndex];
            if (currentWidth === minWidth) {
                continue;
            }
            const newWidth = Math.max(currentWidth - colDiff, minWidth);
            diff -= currentWidth - newWidth;
            widths[thIndex] = newWidth;
            if (newWidth === minWidth) {
                remainingColumnsToShrink--;
            }
        }
    }
    return diff;
}

/**
 * @param {number[]} widths
 * @param {any[]} columns
 * @param {{ minWidth: number, maxWidth?: number, canShrink: boolean, contentSized?: boolean }[]} specs
 * @param {number} columnOffset
 * @param {number} diff
 */
function expandColumns(widths, columns, specs, columnOffset, diff) {
    const expandableColumns = [];
    for (let columnIndex = 0; columnIndex < columns.length; columnIndex++) {
        const thIndex = columnIndex + columnOffset;
        const maxWidth = specs[columnIndex].maxWidth;
        if (!maxWidth || widths[thIndex] < maxWidth) {
            expandableColumns.push({ thIndex, maxWidth });
        }
    }
    let remainingExpandableColumns = expandableColumns.length;
    while (diff >= 1 && remainingExpandableColumns > 0) {
        const colDiff = diff / remainingExpandableColumns;
        for (const { thIndex, maxWidth } of expandableColumns) {
            const currentWidth = widths[thIndex];
            if (currentWidth === maxWidth) {
                continue;
            }
            const newWidth = Math.min(
                currentWidth + colDiff,
                maxWidth || Number.MAX_VALUE,
            );
            diff -= newWidth - currentWidth;
            widths[thIndex] = newWidth;
            if (newWidth === maxWidth) {
                remainingExpandableColumns--;
            }
        }
    }
    if (diff < 1) {
        return;
    }
    const flexible = [];
    for (let columnIndex = 0; columnIndex < columns.length; columnIndex++) {
        if (!specs[columnIndex].maxWidth) {
            flexible.push(columnIndex + columnOffset);
        }
    }
    const nonContent = columns.flatMap((_, index) =>
        specs[index].contentSized ? [] : [index + columnOffset],
    );
    const targets = flexible.length
        ? flexible
        : nonContent.length
          ? nonContent
          : columns.map((_, columnIndex) => columnIndex + columnOffset);
    for (const thIndex of targets) {
        widths[thIndex] += diff / targets.length;
    }
}

const WIDTH_ATTRIBUTE_REGEX = /^\s*(\d+(?:\.\d+)?)\s*(px|%)?\s*$/;

/**
 * @param {string} value
 * @param {Number} allowedWidth
 * @returns {Number | null}
 */
function parseWidthAttribute(value, allowedWidth) {
    const match = WIDTH_ATTRIBUTE_REGEX.exec(value);
    if (!match) {
        return null;
    }
    const amount = Number.parseFloat(match[1]);
    return match[2] === "%" ? (amount / 100) * allowedWidth : amount;
}

/**
 * @param {Object[]} columns
 * @param {Number} allowedWidth
 * @returns {Object[]}
 */
function getWidthSpecs(columns, allowedWidth) {
    return columns.map((column) => {
        let minWidth;
        let maxWidth;
        let contentSized = false;
        const declaredWidth = column.attrs?.width
            ? parseWidthAttribute(column.attrs.width, allowedWidth)
            : null;
        if (declaredWidth) {
            minWidth = maxWidth = declaredWidth;
        } else {
            let width;
            if (column.type === "field") {
                if (column.field.listViewWidth) {
                    width = column.field.listViewWidth;
                    if (typeof width === "function") {
                        width = width({
                            type: column.fieldType,
                            fieldDefinition: column.fieldDefinition,
                            hasLabel: column.hasLabel,
                            options: column.options,
                        });
                    }
                } else {
                    width = FIELD_WIDTHS[column.widget || column.fieldType];
                }
            } else if (column.type === "widget") {
                width = column.widget.listViewWidth;
            }
            if (width === "content") {
                minWidth = DEFAULT_MIN_WIDTH;
                contentSized = true;
            } else if (width) {
                minWidth = Array.isArray(width) ? width[0] : width;
                maxWidth = Array.isArray(width) ? width[1] : width;
            } else {
                minWidth = DEFAULT_MIN_WIDTH;
            }
        }
        return { minWidth, maxWidth, contentSized, canShrink: column.type === "field" };
    });
}

/**
 * @param {HTMLElement} el
 * @returns {Number}
 */
function getHorizontalPadding(el) {
    const { paddingLeft, paddingRight } = getComputedStyle(el);
    return Number.parseFloat(paddingLeft) + Number.parseFloat(paddingRight);
}

export class MagicColumnWidths {
    /** @type {number[] | null} */
    columnWidths = null;
    /** @type {number} */
    allowedWidth = 0;
    /** @type {boolean} */
    hasAlwaysBeenEmpty = true;
    /** @type {boolean} */
    parentWidthFixed = false;
    /** @type {string | undefined} */
    hash;
    /** @type {boolean} */
    _justResized = false;
    /** @type {number | undefined} */
    parentWidth;
    /** @type {number | null} */
    lastAppliedParentWidth = null;
    /** @type {number[] | null} */
    cellPaddings = null;
    /** @type {(() => void) | null} */
    cleanupResize = null;
    /** @type {number[]} */
    contentWidths = [];
    /** @type {number[]} */
    contentColumns = [];
    /** @type {string | undefined} */
    contentSignature;
    hasManualWidths = false;

    /**
     * @param {any} tableRef
     * @param {() => any} getState
     */
    constructor(tableRef, getState) {
        this.tableRef = tableRef;
        this.getState = getState;
    }

    /** @returns {boolean} */
    get justResized() {
        return this._justResized;
    }

    forceColumnWidths() {
        const table = this.tableRef.el;
        const headers = [...table.querySelectorAll("thead th")];
        const state = this.getState();

        const columns = state.columns;
        const nextHash = `${columns.map((column) => column.id).join("/")}/${headers.length}`;
        if (nextHash !== this.hash) {
            this.hash = nextHash;
            this.unsetWidths();
            this.contentColumns = getWidthSpecs(
                columns,
                table.parentNode.clientWidth,
            ).flatMap((spec, index) =>
                spec.contentSized ? [index + (state.hasSelectors ? 1 : 0)] : [],
            );
        }
        if (this.hasAlwaysBeenEmpty && !state.isEmpty) {
            this.hasAlwaysBeenEmpty = false;
            const rows = table.querySelectorAll(".o_data_row");
            if (rows.length !== 1 || !rows[0].classList.contains("o_selected_row")) {
                this.unsetWidths();
            }
        }

        this.updateContentWidths(table, state.isEditing);

        if (
            this.columnWidths &&
            this.lastAppliedParentWidth !== null &&
            this.parentWidth === this.lastAppliedParentWidth &&
            table.style.tableLayout === "fixed" &&
            headers.every((th) => th.style.width)
        ) {
            return;
        }

        const parentPadding = getHorizontalPadding(table.parentNode);
        if (!this.cellPaddings || this.cellPaddings.length !== headers.length) {
            this.cellPaddings = headers.map((th) => getHorizontalPadding(th));
        }
        const cellPaddings = this.cellPaddings;
        const totalCellPadding = cellPaddings.reduce(
            (total, padding) => padding + total,
            0,
        );
        const parentClientWidth = table.parentNode.clientWidth;
        const nextAllowedWidth = parentClientWidth - parentPadding - totalCellPadding;
        const allowedWidthDiff = Math.abs(this.allowedWidth - nextAllowedWidth);
        this.allowedWidth = nextAllowedWidth;

        const columnWidths =
            !this.columnWidths || allowedWidthDiff > 0
                ? computeWidths(
                      table,
                      state,
                      this.allowedWidth,
                      this.columnWidths,
                      this.contentWidths,
                  )
                : this.columnWidths;
        this.columnWidths = columnWidths;

        table.style.tableLayout = "fixed";
        headers.forEach((th, index) => {
            th.style.width = `${Math.floor(
                columnWidths[index] + cellPaddings[index],
            )}px`;
        });
        this.lastAppliedParentWidth = parentClientWidth;
        this.parentWidth = parentClientWidth;
    }

    unsetWidths() {
        this.columnWidths = null;
        this.contentWidths = [];
        this.contentSignature = undefined;
        this.hasManualWidths = false;
        this.lastAppliedParentWidth = null;
        this.cellPaddings = null;
        this.tableRef.el.style.width = null;
        if (this.parentWidthFixed) {
            this.tableRef.el.parentElement.style.width = null;
            this.parentWidthFixed = false;
        }
    }

    /**
     * @param {HTMLTableElement} table
     * @param {boolean} isEditing
     */
    updateContentWidths(table, isEditing) {
        if (!this.contentColumns.length || isEditing || this.hasManualWidths) {
            return;
        }
        const rows = [...table.querySelectorAll(".o_data_row")];
        const signature = JSON.stringify(
            this.contentColumns.map((index) =>
                rows.map((row) => row.children[index]?.textContent || "").sort(),
            ),
        );
        if (signature !== this.contentSignature) {
            this.contentSignature = signature;
            this.contentWidths = [];
            this.columnWidths = null;
        }
    }

    resetWidths() {
        this.unsetWidths();
        this.forceColumnWidths();
    }

    /** @param {MouseEvent} ev */
    onStartResize(ev) {
        const table = this.tableRef.el;
        const th = /** @type {HTMLElement} */ (ev.target).closest("th");
        const thRow = th?.parentNode;
        if (!th || !thRow) {
            return;
        }
        table.style.width = `${Math.floor(table.getBoundingClientRect().width)}px`;
        const thPosition = [...thRow.children].indexOf(th);
        const resizingColumnElements = [...table.getElementsByTagName("tr")]
            .filter((tr) => tr.children.length === thRow.children.length)
            .map((tr) => tr.children[thPosition]);
        const initialX = ev.clientX;
        const initialWidth = th.getBoundingClientRect().width;
        const initialTableWidth = table.getBoundingClientRect().width;
        const resizeStoppingEvents = ["keydown", "pointerdown", "pointerup"];

        if (!table.parentElement.style.width) {
            this.parentWidthFixed = true;
            table.parentElement.style.width = `${Math.floor(
                table.parentElement.getBoundingClientRect().width,
            )}px`;
        }

        for (const el of resizingColumnElements) {
            el.classList.add("o_column_resizing");
        }
        const resizeHeader = (ev) => {
            ev.preventDefault();
            ev.stopPropagation();
            let delta = ev.clientX - initialX;
            delta = localization.direction === "rtl" ? -delta : delta;
            const newWidth = Math.max(10, initialWidth + delta);
            const tableDelta = newWidth - initialWidth;
            th.style.width = `${Math.floor(newWidth)}px`;
            table.style.width = `${Math.floor(initialTableWidth + tableDelta)}px`;
        };
        browser.addEventListener("pointermove", resizeHeader);

        const cleanup = () => {
            for (const el of resizingColumnElements) {
                el.classList.remove("o_column_resizing");
            }
            browser.removeEventListener("pointermove", resizeHeader);
            for (const eventType of resizeStoppingEvents) {
                browser.removeEventListener(eventType, stopResize);
            }
            this.cleanupResize = null;
        };
        this.cleanupResize = cleanup;

        const stopResize = (ev) => {
            if (ev.type === "pointerdown" && ev.button === 0) {
                return;
            }
            this._justResized = true;

            const headers = [...table.querySelectorAll("thead th")];
            this.columnWidths = headers.map(
                (th) => th.getBoundingClientRect().width - getHorizontalPadding(th),
            );
            this.hasManualWidths = true;
            this.contentWidths = [];

            ev.preventDefault();
            ev.stopPropagation();

            cleanup();

            const active = /** @type {HTMLElement} */ (document.activeElement);
            if (active && table.querySelector("thead")?.contains(active)) {
                active.blur();
            }
        };
        for (const eventType of resizeStoppingEvents) {
            browser.addEventListener(eventType, stopResize);
        }
    }

    clearJustResized() {
        this._justResized = false;
    }
}

/**
 * @param {any} tableRef
 * @param {() => any} getState
 * @returns {MagicColumnWidths}
 */
export function useMagicColumnWidths(tableRef, getState) {
    const renderer = useComponent();
    const widths = new MagicColumnWidths(tableRef, getState);

    if (/** @type {any} */ (renderer.constructor).useMagicColumnWidths) {
        useEffect(() =>
            mutate(() => {
                if (tableRef.el?.isConnected) {
                    widths.forceColumnWidths();
                }
            }),
        );
        useExternalListener(window, "resize", () => widths.unsetWidths());
        const debouncedForceColumnWidths = useDebounced(
            () => {
                if (status(renderer) !== "destroyed") {
                    widths.forceColumnWidths();
                }
            },
            200,
            { immediate: true, trailing: true },
        );
        const resizeObserver = new ResizeObserver(() => {
            const newParentWidth = tableRef.el.parentNode.clientWidth;
            if (newParentWidth !== widths.parentWidth) {
                widths.parentWidth = newParentWidth;
                debouncedForceColumnWidths();
            }
        });
        onMounted(() =>
            measure(() => {
                if (!tableRef.el?.isConnected) {
                    return;
                }
                widths.parentWidth = tableRef.el.parentNode.clientWidth;
                resizeObserver.observe(tableRef.el.parentNode);
            }),
        );
        onWillUnmount(() => resizeObserver.disconnect());
    }

    onWillUnmount(() => widths.cleanupResize?.());

    useExternalListener(window, "pointerdown", () => widths.clearJustResized(), {
        capture: true,
    });

    return widths;
}
