import { useDebounced } from "@web/core/utils/timing";
import { localization } from "@web/core/l10n/localization";

import {
    onMounted,
    onWillUnmount,
    status,
    useComponent,
    useEffect,
    useExternalListener,
} from "@odoo/owl";

import { getHorizontalPadding, computeWidths } from "./column_widths";

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


export { FIELD_WIDTHS, resetDateFieldWidths } from "./column_widths";

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
            resetWidths();
        }
        // If the table has always been empty until now, and it now contains records, we want to
        // recompute the widths based on the records (typical case: we removed a filter).
        // Exception: we were in an empty editable list, and we just added a first record.
        if (hasAlwaysBeenEmpty && !state.isEmpty) {
            hasAlwaysBeenEmpty = false;
            const rows = table.querySelectorAll(".o_data_row");
            if (rows.length !== 1 || !rows[0].classList.contains("o_selected_row")) {
                resetWidths();
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
     * Resets the widths. After next patch, ideal widths will be recomputed.
     */
    function resetWidths() {
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
        const handler = th.querySelector(".o_resize");
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

        // Apply classes to table and selected column
        table.classList.add("o_resizing");
        for (const el of resizingColumnElements) {
            el.classList.add("o_column_resizing");
            handler.classList.add("bg-primary", "opacity-100");
            handler.classList.remove("bg-black-25", "opacity-50-hover");
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

            table.classList.remove("o_resizing");
            for (const el of resizingColumnElements) {
                el.classList.remove("o_column_resizing");
                handler.classList.remove("bg-primary", "opacity-100");
                handler.classList.add("bg-black-25", "opacity-50-hover");
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

    // Side effects
    if (renderer.constructor.useMagicColumnWidths) {
        useEffect(forceColumnWidths);
        // Forget computed widths (and potential manual column resize) on window resize
        useExternalListener(window, "resize", resetWidths);
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
    };
}
