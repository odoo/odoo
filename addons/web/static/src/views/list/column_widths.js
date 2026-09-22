import { renderToElement } from "@web/core/utils/render";
import { formatDate, formatDateTime } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { xml } from "@odoo/owl";

// Hardcoded widths
export const DEFAULT_MIN_WIDTH = 80;
export const SELECTOR_WIDTH = 20;
export const OPEN_FORM_VIEW_BUTTON_WIDTH = 54;
export const DELETE_BUTTON_WIDTH = 12;
let _dateFieldWidth = null; // computed dynamically, lazily, see @computeOptimalDateWidths
let _datetimeFieldWidth = null; // computed dynamically, lazily, see @computeOptimalDateWidths
export const FIELD_WIDTHS = Object.freeze({
    boolean: [20, 100], // [minWidth, maxWidth]
    char: [80], // only minWidth, no maxWidth
    get date() {
        if (!_dateFieldWidth) {
            computeOptimalDateWidths();
        }
        return _dateFieldWidth;
    },
    get datetime() {
        if (!_datetimeFieldWidth) {
            computeOptimalDateWidths();
        }
        return _datetimeFieldWidth;
    },
    float: 93,
    integer: 71,
    many2many: [80],
    many2one_reference: [80],
    many2one: [80],
    monetary: 105,
    one2many: [80],
    reference: [80],
    selection: [80],
    text: [80, 1200],
});

export function resetDateFieldWidths() {
    // useful for tests
    _dateFieldWidth = null;
    _datetimeFieldWidth = null;
}

/**
 * Compute ideal date and datetime widths. There's no static value for them as they depend on the
 * localization. Moreover, as we want to have the exact minimum width necessary, it also depends on
 * the fonts (we never want to see "..." in date fields). So we render date(time) values, we insert
 * them into the DOM and compute their width.
 */
export function computeOptimalDateWidths() {
    const dates = [];
    const datetimes = [];
    const { dateFormat, timeFormat } = localization;
    const escapedPartsRegex = /('[^']*')/g;
    const dateFormatWoEscParts = dateFormat.replaceAll(escapedPartsRegex, "");
    // generate a date for each month if date format contains MMMM or MMM (full or abbrev. month)
    for (let month = 1; month <= (/MMM/.test(dateFormatWoEscParts) ? 12 : 1); month++) {
        // generate a date for each day if date format contains cccc or ccc (full or abbrev. day)
        for (let day = 1; day <= (/ccc/.test(dateFormatWoEscParts) ? 7 : 1); day++) {
            dates.push(formatDate(luxon.DateTime.local(2017, month, day)));
            datetimes.push(formatDateTime(luxon.DateTime.local(2017, month, day, 8, 0, 0)));
            const timeFormatWoEscParts = timeFormat.replaceAll(escapedPartsRegex, "");
            if (/a/.test(timeFormatWoEscParts)) {
                // generate a date in the afternoon if time is displayed with AM/PM or equivalent
                datetimes.push(formatDateTime(luxon.DateTime.local(2017, month, day, 20, 0, 0)));
            }
        }
    }
    const template = xml`
        <div class="invisible" style="font-variant-numeric: tabular-nums;">
            <div class="dates">
                <div t-foreach="dates" t-as="date" t-key="date_index">
                    <span t-esc="date"/>
                </div>
            </div>
            <div class="datetimes">
                <div t-foreach="datetimes" t-as="datetime" t-key="datetime_index">
                    <span t-esc="datetime"/>
                </div>
            </div>
        </div>`;
    const div = renderToElement(template, { dates, datetimes });
    document.body.append(div);
    const dateSpans = div.querySelectorAll(".dates span");
    const dateWidths = [...dateSpans].map((span) => span.getBoundingClientRect().width);
    const datetimeSpans = div.querySelectorAll(".datetimes span");
    const datetimeWidths = [...datetimeSpans].map((span) => span.getBoundingClientRect().width);
    document.body.removeChild(div);
    // add a 5% margin to cope with potential bold decorations
    _dateFieldWidth = Math.ceil(Math.max(...dateWidths) * 1.05);
    _datetimeFieldWidth = Math.ceil(Math.max(...datetimeWidths) * 1.05);
}

/**
 * Compute ideal widths based on the rules described on top of this file.
 *
 * @params {Element} table
 * @params {Object} state
 * @params {Number} allowedWidth
 * @params {Number[]} startingWidths
 * @returns {Number[]}
 */
export function computeWidths(table, state, allowedWidth, startingWidths) {
    let _columnWidths;
    const headers = [...table.querySelectorAll("thead th")];
    const columns = state.columns;

    // Starting point: compute widths
    if (startingWidths) {
        _columnWidths = startingWidths.slice();
    } else if (state.isEmpty) {
        // Table is empty => uniform distribution as starting point
        _columnWidths = headers.map(() => allowedWidth / headers.length);
    } else {
        // Table contains records => let the browser compute ideal widths
        // Set table layout auto and remove inline style
        table.style.tableLayout = "auto";
        headers.forEach((th) => {
            th.style.width = null;
        });
        // Toggle a className used to remove style that could interfere with the ideal width
        // computation algorithm (e.g. prevent text fields from being wrapped during the
        // computation, to prevent them from being completely crushed)
        table.classList.add("o_list_computing_widths");
        _columnWidths = headers.map((th) => th.getBoundingClientRect().width);
        table.classList.remove("o_list_computing_widths");
    }

    // Force columns to comply with their min and max widths
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
    const columnWidthSpecs = getWidthSpecs(columns);
    const columnOffset = state.hasSelectors ? 1 : 0;
    for (let columnIndex = 0; columnIndex < columns.length; columnIndex++) {
        const thIndex = columnIndex + columnOffset;
        const { minWidth, maxWidth } = columnWidthSpecs[columnIndex];
        if (_columnWidths[thIndex] < minWidth) {
            _columnWidths[thIndex] = minWidth;
        } else if (maxWidth && _columnWidths[thIndex] > maxWidth) {
            _columnWidths[thIndex] = maxWidth;
        }
    }

    // Expand/shrink columns for the table to fill 100% of available space
    const totalWidth = _columnWidths.reduce((tot, width) => tot + width, 0);
    let diff = totalWidth - allowedWidth;
    if (diff >= 1) {
        // Case 1: table overflows its parent => shrink some columns
        const shrinkableColumns = [];
        let totalAvailableSpace = 0; // total space we can gain by shrinking columns
        for (let columnIndex = 0; columnIndex < columns.length; columnIndex++) {
            const thIndex = columnIndex + columnOffset;
            const { minWidth, canShrink } = columnWidthSpecs[columnIndex];
            if (_columnWidths[thIndex] > minWidth && canShrink) {
                shrinkableColumns.push({ thIndex, minWidth });
                totalAvailableSpace += _columnWidths[thIndex] - minWidth;
            }
        }
        if (diff > totalAvailableSpace) {
            // We can't find enough space => set all columns to their min width, and there'll be an
            // horizontal scrollbar
            for (const { thIndex, minWidth } of shrinkableColumns) {
                _columnWidths[thIndex] = minWidth;
            }
        } else {
            // There's enough available space among shrinkable columns => shrink them uniformly
            let remainingColumnsToShrink = shrinkableColumns.length;
            while (diff >= 1) {
                const colDiff = diff / remainingColumnsToShrink;
                for (const { thIndex, minWidth } of shrinkableColumns) {
                    const currentWidth = _columnWidths[thIndex];
                    if (currentWidth === minWidth) {
                        continue;
                    }
                    const newWidth = Math.max(currentWidth - colDiff, minWidth);
                    diff -= currentWidth - newWidth;
                    _columnWidths[thIndex] = newWidth;
                    if (newWidth === minWidth) {
                        remainingColumnsToShrink--;
                    }
                }
            }
        }
    } else if (diff <= -1) {
        // Case 2: table is narrower than its parent => expand some columns
        diff = -diff; // for better readability
        const expandableColumns = [];
        for (let columnIndex = 0; columnIndex < columns.length; columnIndex++) {
            const thIndex = columnIndex + columnOffset;
            const maxWidth = columnWidthSpecs[columnIndex].maxWidth;
            if (!maxWidth || _columnWidths[thIndex] < maxWidth) {
                expandableColumns.push({ thIndex, maxWidth });
            }
        }
        // Expand all expandable columns uniformly (i.e. at most, expand columns with a maxWidth
        // to their maxWidth)
        let remainingExpandableColumns = expandableColumns.length;
        while (diff >= 1 && remainingExpandableColumns > 0) {
            const colDiff = diff / remainingExpandableColumns;
            for (const { thIndex, maxWidth } of expandableColumns) {
                const currentWidth = _columnWidths[thIndex];
                const newWidth = Math.min(currentWidth + colDiff, maxWidth || Number.MAX_VALUE);
                diff -= newWidth - currentWidth;
                _columnWidths[thIndex] = newWidth;
                if (newWidth === maxWidth) {
                    remainingExpandableColumns--;
                }
            }
        }
        if (diff >= 1) {
            // All columns have a maxWidth and have been expanded to their max => expand them more
            for (let columnIndex = 0; columnIndex < columns.length; columnIndex++) {
                const thIndex = columnIndex + columnOffset;
                _columnWidths[thIndex] += diff / columns.length;
            }
        }
    }
    return _columnWidths;
}

/**
 * Returns for each column its minimal and (if any) maximal widths.
 *
 * @param {Object[]} columns
 * @returns {Object[]} each entry in this array has a minWidth and optionally a maxWidth key
 */
export function getWidthSpecs(columns) {
    return columns.map((column) => {
        let minWidth;
        let maxWidth;
        if (column.attrs && column.attrs.width) {
            minWidth = maxWidth = parseInt(column.attrs.width.split("px")[0]);
        } else {
            let width;
            if (column.type === "field") {
                if (column.field.listViewWidth) {
                    width = column.field.listViewWidth;
                    if (typeof width === "function") {
                        width = width({
                            type: column.fieldType,
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
            if (width) {
                minWidth = Array.isArray(width) ? width[0] : width;
                maxWidth = Array.isArray(width) ? width[1] : width;
            } else {
                minWidth = DEFAULT_MIN_WIDTH;
            }
        }
        return { minWidth, maxWidth, canShrink: column.type === "field" };
    });
}

/**
 * Given an html element, returns the sum of its left and right padding.
 *
 * @param {HTMLElement} el
 * @returns {Number}
 */
export function getHorizontalPadding(el) {
    const { paddingLeft, paddingRight } = getComputedStyle(el);
    return parseFloat(paddingLeft) + parseFloat(paddingRight);
}
