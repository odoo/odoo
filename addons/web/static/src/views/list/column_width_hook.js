import { renderToElement } from "@web/core/utils/render";
import { useDebounced } from "@web/core/utils/timing";
import {
    formatDate,
    formatDateTime,
    toLocaleDateString,
    toLocaleDateTimeString,
} from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";

import {
    onMounted,
    onWillUnmount,
    status,
    useComponent,
    useEffect,
    useExternalListener,
    xml,
} from "@odoo/owl";

// This file defines a hook that encapsulates the column width logic of the list view. This logic
// aims at optimizing the available space between columns and, once computed, at freezing the table
// to ensure that the columns don't flicker. This hook is meant to be used by the ListRenderer only,
// it isn't a generic hook that can be used in various contexts.
//
// Widths computation specs
// ------------------------
//
// For some field types, we harcode the column width because we know the required space to display
// values for that type (e.g. a Date field always requires the same space). A width can also be
// hardcoded in the arch (`width="60px"`). In those cases, the column has a fixed width that we
// enforce. Note that the column width will be the given width + the cell's left and right paddings.
// Numeric fields don't technically have a fixed width, but rather a range: we always want enough
// space s.t. `1 million` would fit, and we consider that we don't need more space than `1 billion`
// would require to fit. Depending on the field type (integer, float, monetary), we determine the
// necessary width to display those numbers.
// The other columns have an hardcoded min width, that we always want to guarantee, but they have no
// max width.
//
// There're two cases. In both of them, we need to compute a starting point for the widths:
//   - there's no data in the table: we force all columns with hardcoded widths to those widths and
//     uniformly distribute the remaining space among the other columns.
//   - there're records in the table, we let the browser compute ideal widths based on the content
//     of the table.
// Once this is done, we ensure that each column complies with their min and max widths. It may
// happen that some columns are too narrow (because their content is small, and there're a lot of
// columns), so we expand them to their minimal width. It may also happen that some columns are too
// wide (if they have a max width), so we shrink them.
// Once this is done, we must ensure that the sum of the column widths still fills 100% of the
// table. That means that we might have to expand/narrow columns, again. It may happen that the
// table has too many columns s.t. they can't fit within the 100% by complying the the rules, it's
// fine, an horizontal scrollbar will be displayed in that case.
//
// Freeze logic
// ------------
//
// Once optimal widths have been computed, we want the table to be frozen s.t. columns don't resize
// upon user interaction, like inline edition, adding or removing a record... The computed widths
// are thus stored, and re-applied at each rendering. There're exceptions though. If the columns
// change (e.g. optional column toggled), if the window is resized, if we remove a filter or open
// a group s.t. the list contains records for the first time, we forget the computed widths and
// start over.

// Hardcoded widths
const DEFAULT_MIN_WIDTH = 80;
const SELECTOR_WIDTH = 20;
const OPEN_FORM_VIEW_BUTTON_WIDTH = 54;
const DELETE_BUTTON_WIDTH = 12;
let _dateWidths = null; // computed dynamically, lazily, see @computeOptimalDateWidths
export const FIELD_WIDTHS = Object.freeze({
    boolean: [20, 100], // [minWidth, maxWidth]
    char: [80], // only minWidth, no maxWidth
    get date() {
        if (!_dateWidths) {
            computeOptimalDateWidths();
        }
        return _dateWidths.date;
    },
    get datetime() {
        if (!_dateWidths) {
            computeOptimalDateWidths();
        }
        return _dateWidths.datetime;
    },
    get numeric_date() {
        if (!_dateWidths) {
            computeOptimalDateWidths();
        }
        return _dateWidths.numericDate;
    },
    get numeric_datetime() {
        if (!_dateWidths) {
            computeOptimalDateWidths();
        }
        return _dateWidths.numericDatetime;
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
    _dateWidths = null;
}

/**
 * Compute ideal date and datetime widths. There's no static value for them as they depend on the
 * localization. Moreover, as we want to have the exact minimum width necessary, it also depends on
 * the fonts (we never want to see "..." in date fields). So we render date(time) values, we insert
 * them into the DOM and compute their width.
 */
function computeOptimalDateWidths() {
    const { timeFormat } = localization;
    const values = {
        date: [],
        datetime: [],
        numericDate: [],
        numericDatetime: [],
    };
    // dates in the "human readable" format (must generate a date by month as width could vary)
    for (let month = 1; month <= 12; month++) {
        values.date.push(toLocaleDateString(luxon.DateTime.local(2017, month, 20)));
        values.datetime.push(
            toLocaleDateTimeString(luxon.DateTime.local(2017, month, 25, 10, 0, 0), {
                showSeconds: true,
            })
        );
        if (timeFormat === "hh:mm:ss a") {
            // generate a date in the afternoon if time is displayed with AM/PM or equivalent
            values.datetime.push(
                toLocaleDateTimeString(luxon.DateTime.local(2017, month, 25, 22, 0, 0), {
                    showSeconds: true,
                })
            );
        }
    }
    // dates in the "numeric" format
    values.numericDate.push(formatDate(luxon.DateTime.local(2017, 1, 1)));
    values.numericDatetime.push(formatDateTime(luxon.DateTime.local(2017, 1, 1, 10, 0, 0)));
    if (timeFormat === "hh:mm:ss a") {
        // generate a date in the afternoon if time is displayed with AM/PM or equivalent
        values.numericDatetime.push(formatDateTime(luxon.DateTime.local(2017, 1, 1, 22, 0, 0)));
    }

    const template = xml`
        <div class="invisible" style="font-variant-numeric: tabular-nums;">
            <div t-foreach="Object.keys(values)" t-as="key" t-key="key" t-att-class="key">
                <div t-foreach="values[key]" t-as="value" t-key="value_index">
                    <span t-esc="value"/>
                </div>
            </div>
        </div>`;
    const div = renderToElement(template, { values });
    document.body.append(div);
    _dateWidths = {};
    for (const key in values) {
        const spans = div.querySelectorAll(`.${key} span`);
        const widths = [...spans].map((span) => span.getBoundingClientRect().width);
        // add a 5% margin to cope with potential bold decorations
        _dateWidths[key] = Math.ceil(Math.max(...widths) * 1.05);
    }
    document.body.removeChild(div);
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
function computeWidths(table, state, allowedWidth, startingWidths) {
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
function getWidthSpecs(columns) {
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
function getHorizontalPadding(el) {
    const { paddingLeft, paddingRight } = getComputedStyle(el);
    return parseFloat(paddingLeft) + parseFloat(paddingRight);
}

export function useMagicColumnWidths(tableRef, getState) {
    const renderer = useComponent();
    let columnWidths = null;
    let allowedWidth = 0;
    let hasAlwaysBeenEmpty = true;
    let parentWidthFixed = false;
    let hash;
    let _resizing = false;

    /**
     * Apply the column widths in the DOM. If necessary, compute them first (e.g. if they haven't
     * been computed yet, or if columns have changed).
     *
     * Note: the following code manipulates the DOM directly to avoid having to wait for a
     * render + patch which would occur on the next frame and cause flickering.
     */
    function forceColumnWidths() {
        const table = tableRef.el;
        const headers = [...table.querySelectorAll("thead th")];
        const state = getState();

        // Generate a hash to be able to detect when the columns change
        const columns = state.columns;
        // The last part of the hash is there to detect that static columns changed (typically, the
        // selector column, which isn't displayed on small screens)
        const nextHash = `${columns.map((column) => column.id).join("/")}/${headers.length}`;
        if (nextHash !== hash) {
            hash = nextHash;
            unsetWidths();
        }
        // If the table has always been empty until now, and it now contains records, we want to
        // recompute the widths based on the records (typical case: we removed a filter).
        // Exception: we were in an empty editable list, and we just added a first record.
        if (hasAlwaysBeenEmpty && !state.isEmpty) {
            hasAlwaysBeenEmpty = false;
            const rows = table.querySelectorAll(".o_data_row");
            if (rows.length !== 1 || !rows[0].classList.contains("o_selected_row")) {
                unsetWidths();
            }
        }

        const parentPadding = getHorizontalPadding(table.parentNode);
        const cellPaddings = headers.map((th) => getHorizontalPadding(th));
        const totalCellPadding = cellPaddings.reduce((total, padding) => padding + total, 0);
        const nextAllowedWidth = table.parentNode.clientWidth - parentPadding - totalCellPadding;
        const allowedWidthDiff = Math.abs(allowedWidth - nextAllowedWidth);
        allowedWidth = nextAllowedWidth;

        // When a vertical scrollbar appears/disappears, it may (depending on the browser/os) change
        // the available width. When it does, we want to keep the current widths, but tweak them a
        // little bit s.t. the table fits in the new available space.
        if (!columnWidths || allowedWidthDiff > 0) {
            columnWidths = computeWidths(table, state, allowedWidth, columnWidths);
        }

        // Set the computed widths in the DOM.
        table.style.tableLayout = "fixed";
        headers.forEach((th, index) => {
            th.style.width = `${Math.floor(columnWidths[index] + cellPaddings[index])}px`;
        });
    }

    /**
     * Unsets the widths. After next patch, ideal widths will be recomputed.
     */
    function unsetWidths() {
        columnWidths = null;
        // Unset widths that might have been set on the table by resizing a column
        tableRef.el.style.width = null;
        if (parentWidthFixed) {
            tableRef.el.parentElement.style.width = null;
        }
    }

    /**
     * Handles the resize feature on the column headers
     *
     * @private
     * @param {MouseEvent} ev
     */
    function onStartResize(ev) {
        _resizing = true;
        const table = tableRef.el;
        const th = ev.target.closest("th");
        table.style.width = `${Math.floor(table.getBoundingClientRect().width)}px`;
        const thPosition = [...th.parentNode.children].indexOf(th);
        const resizingColumnElements = [...table.getElementsByTagName("tr")]
            .filter((tr) => tr.children.length === th.parentNode.children.length)
            .map((tr) => tr.children[thPosition]);
        const initialX = ev.clientX;
        const initialWidth = th.getBoundingClientRect().width;
        const initialTableWidth = table.getBoundingClientRect().width;
        const resizeStoppingEvents = ["keydown", "pointerdown", "pointerup"];

        // Fix the width so that if the resize overflows, it doesn't affect the layout of the parent
        if (!table.parentElement.style.width) {
            parentWidthFixed = true;
            table.parentElement.style.width = `${Math.floor(
                table.parentElement.getBoundingClientRect().width
            )}px`;
        }

        // Apply classes to the selected column
        for (const el of resizingColumnElements) {
            el.classList.add("o_column_resizing");
        }
        // Mousemove event : resize header
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
        window.addEventListener("pointermove", resizeHeader);

        // Mouse or keyboard events : stop resize
        const stopResize = (ev) => {
            _resizing = false;

            // Store current column widths to freeze them
            const headers = [...table.querySelectorAll("thead th")];
            columnWidths = headers.map(
                (th) => th.getBoundingClientRect().width - getHorizontalPadding(th)
            );

            // Ignores the 'left mouse button down' event as it used to start resizing
            if (ev.type === "pointerdown" && ev.button === 0) {
                return;
            }
            ev.preventDefault();
            ev.stopPropagation();

            for (const el of resizingColumnElements) {
                el.classList.remove("o_column_resizing");
            }

            window.removeEventListener("pointermove", resizeHeader);
            for (const eventType of resizeStoppingEvents) {
                window.removeEventListener(eventType, stopResize);
            }

            // We remove the focus to make sure that the there is no focus inside
            // the tr.  If that is the case, there is some css to darken the whole
            // thead, and it looks quite weird with the small css hover effect.
            document.activeElement.blur();
        };
        // We have to listen to several events to properly stop the resizing function. Those are:
        // - pointerdown (e.g. pressing right click)
        // - pointerup : logical flow of the resizing feature (drag & drop)
        // - keydown : (e.g. pressing 'Alt' + 'Tab' or 'Windows' key)
        for (const eventType of resizeStoppingEvents) {
            window.addEventListener(eventType, stopResize);
        }
    }

    /**
     * Forces a recomputation of column widths
     */
    function resetWidths() {
        unsetWidths();
        forceColumnWidths();
    }

    // Side effects
    if (renderer.constructor.useMagicColumnWidths) {
        useEffect(forceColumnWidths);
        // Forget computed widths (and potential manual column resize) on window resize
        useExternalListener(window, "resize", unsetWidths);
        // Listen to width changes on the parent node of the table, to recompute ideal widths
        // Note: we compute the widths once, directly, and once after parent width stabilization.
        // The first call is only necessary to avoid an annoying flickering when opening form views
        // with an x2many list and a chatter (when it is displayed below the form) as it may happen
        // that the display of chatter messages introduces a vertical scrollbar, thus reducing the
        // available width.
        const component = useComponent();
        let parentWidth;
        const debouncedForceColumnWidths = useDebounced(
            () => {
                if (status(component) !== "destroyed") {
                    forceColumnWidths();
                }
            },
            200,
            { immediate: true, trailing: true }
        );
        const resizeObserver = new ResizeObserver(() => {
            const newParentWidth = tableRef.el.parentNode.clientWidth;
            if (newParentWidth !== parentWidth) {
                parentWidth = newParentWidth;
                debouncedForceColumnWidths();
            }
        });
        onMounted(() => {
            parentWidth = tableRef.el.parentNode.clientWidth;
            resizeObserver.observe(tableRef.el.parentNode);
        });
        onWillUnmount(() => resizeObserver.disconnect());
    }

    // API
    return {
        get resizing() {
            return _resizing;
        },
        onStartResize,
        resetWidths,
    };
}
