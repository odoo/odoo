// @ts-check

/** @module views/list/list_aggregates_row - Footer aggregate row component for ListRenderer */

import { Component, useRef } from "@odoo/owl";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { useAutofocus } from "@web/core/utils/hooks";
import { getActiveHotkey } from "@web/services/hotkeys/hotkey_service";

import { useListAggregates } from "./list_aggregates";
import { processAllColumns } from "./list_column_utils";
import {
    getAggregateColumns as getAggregateColumnsUtil,
    getGroupNameCellColSpan as getGroupNameCellColSpanUtil,
} from "./list_group_layout";

/**
 * Renders the single footer row (`<tr>`) inside the list `<tfoot>`.
 *
 * Extracted from ListRenderer so OWL's template-level reactive tracking applies
 * to aggregate computation: re-renders fire only when `list.records`,
 * `record.data`, or `record.selected` actually change — not on unrelated parent
 * re-renders (e.g. `editedRecord` toggling when a cell is clicked).
 *
 * The component also owns the "Add a <groupBy>" button and input, previously
 * managed on the parent.
 *
 * @extends Component
 */
export class ListAggregatesRow extends Component {
    static template = "web.ListAggregatesRow";

    static props = {
        /** @type {any} */
        list: Object,
        /** @type {any} - parsed view arch info */
        archInfo: Object,
        /** @type {any} - reactive (useState) optional field visibility */
        optionalActiveFields: Object,
        /** Whether a selector checkbox column is present */
        hasSelectors: Boolean,
        /** Whether the "open in form view" column is present */
        hasOpenFormViewColumn: Boolean,
        /** Whether there is at least one optional field (drives the trailing empty td) */
        displayOptionalFields: Boolean,
        /** Active actions object from the controller */
        activeActions: Object,
        /** Whether the current user can create a new group via the footer button */
        canCreateGroup: Boolean,
        /** Parent-managed flag controlling the group creation input visibility */
        showGroupInput: Boolean,
        /** Tell parent to show the group creation input */
        onShowGroupInput: Function,
        /** Tell parent to hide the group creation input */
        onHideGroupInput: Function,
        /**
         * Confirm a new group name — called with the string value typed by the user.
         * @type {(value: string) => void}
         */
        onGroupInputConfirm: Function,
    };

    /** Initialize group creation input ref and aggregate computation hook. */
    setup() {
        // Group creation input ref + autofocus (was on ListRenderer; moved here
        // because the DOM element lives in this component's template).
        this.groupInputRef = useRef("groupInput");
        // Re-focus the input whenever showGroupInput becomes true
        useAutofocus({ refName: "groupInput" });

        this.agg = useListAggregates({
            getColumns: () => this.columns,
            getFields: () => this.props.list.fields,
            getProps: () => this.props,
            getOptionalActiveFields: () => this.props.optionalActiveFields,
        });
    }

    // -------------------------------------------------------------------------
    // Column helpers (recomputed each template evaluation — OWL tracks the reads)
    // -------------------------------------------------------------------------

    /** @returns {any[]} All columns including expanded property fields. */
    get allColumns() {
        return processAllColumns(this.props.archInfo.columns, this.props.list);
    }

    /** @returns {any[]} Visible columns (excluding optional-hidden and column-invisible). */
    get columns() {
        return this.allColumns.filter((col) => {
            if (col.optional && !this.props.optionalActiveFields[col.name]) {
                return false;
            }
            if (
                evaluateBooleanExpr(col.column_invisible, this.props.list.evalContext)
            ) {
                return false;
            }
            return true;
        });
    }

    /** @returns {Record<string, object>} Computed aggregate values keyed by field name. */
    get aggregates() {
        // Called from template evaluation — OWL reactive tracking subscribes to
        // list.records, record.data[field], and record.selected inside this call.
        return this.agg.computeAggregates();
    }

    /** @returns {Record<string, any>} Field definitions from the list model. */
    get fields() {
        return this.props.list.fields;
    }

    // -------------------------------------------------------------------------
    // Layout helpers
    // -------------------------------------------------------------------------

    /** @returns {any[]} Columns that have aggregate values to display. */
    getAggregateColumns() {
        return getAggregateColumnsUtil(
            /** @type {any} */ (this.columns),
            this.fields,
            this.aggregates,
        );
    }

    /** @returns {number} Column span for the group name cell in the footer row. */
    getGroupNameCellColSpan() {
        return getGroupNameCellColSpanUtil(
            /** @type {any} */ (this.columns),
            this.fields,
            this.aggregates,
            { hasSelectors: this.props.hasSelectors },
        );
    }

    // -------------------------------------------------------------------------
    // Group creation input handlers
    // -------------------------------------------------------------------------

    /**
     * Handle keydown in the group creation input. Enter confirms, Escape cancels.
     *
     * @param {KeyboardEvent} ev
     */
    onGroupInputKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        if (hotkey === "enter") {
            ev.stopPropagation();
            this._confirmGroupInput();
        }
        if (hotkey === "escape") {
            ev.stopPropagation();
            this.props.onHideGroupInput();
        }
    }

    /** Read the group input value and pass it to the parent confirmation callback. */
    _confirmGroupInput() {
        const value = /** @type {HTMLInputElement} */ (this.groupInputRef.el).value;
        this.props.onGroupInputConfirm(value);
    }

    // -------------------------------------------------------------------------
    // Multi-currency popover
    // -------------------------------------------------------------------------

    /**
     * Open the multi-currency breakdown popover for a monetary aggregate cell.
     *
     * @param {MouseEvent} ev - click event on the aggregate cell
     * @param {any} value - the aggregate value object
     * @param {string} fieldName - the monetary field name
     */
    openMultiCurrencyPopover(ev, value, fieldName) {
        this.agg.openMultiCurrencyPopover(ev, value, fieldName);
    }
}
