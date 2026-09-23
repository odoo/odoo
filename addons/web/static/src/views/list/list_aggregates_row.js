// @ts-check
/** @odoo-module native */

import { Component, useRef } from "@odoo/owl";
import { getActiveHotkey } from "@web/core/browser/hotkeys";
import { useAutofocus } from "@web/core/utils/hooks";

import {
    getAggregateColumns as getAggregateColumnsUtil,
    getGroupNameCellColSpan as getGroupNameCellColSpanUtil,
} from "./list_group_layout.js";

export class ListAggregatesRow extends Component {
    static template = "web.ListAggregatesRow";

    static props = {
        /** @type {any} */
        agg: Object,
        /** @type {any} */
        list: Object,
        /** @type {any} */
        archInfo: Object,
        /** @type {any} */
        columns: Array,
        hasSelectors: Boolean,
        hasOpenFormViewColumn: Boolean,
        displayOptionalFields: Boolean,
        hasActionsColumn: Boolean,
        activeActions: Object,
        canCreateGroup: Boolean,
        showGroupInput: Boolean,
        onShowGroupInput: Function,
        onHideGroupInput: Function,
        /** @type {(value: string) => void} */
        onGroupInputConfirm: Function,
    };
    /** @type {import("@odoo/owl").Ref} */
    groupInputRef;

    setup() {
        this.groupInputRef = useRef("groupInput");
        useAutofocus({ refName: "groupInput" });
    }

    /** @returns {ReturnType<typeof import("./list_aggregates").useListAggregates>} */
    get agg() {
        return this.props.agg;
    }

    /** @returns {any[]} */
    get columns() {
        return this.props.columns;
    }

    /** @returns {Record<string, any>} */
    get fields() {
        return this.props.list.fields;
    }

    /**
     * @param {Record<string, object>} aggregates
     * @returns {any[]}
     */
    getAggregateColumns(aggregates) {
        return getAggregateColumnsUtil(
            /** @type {any} */ (this.columns),
            this.fields,
            aggregates,
        );
    }

    /**
     * @param {Record<string, object>} aggregates
     * @returns {number}
     */
    getGroupNameCellColSpan(aggregates) {
        return getGroupNameCellColSpanUtil(
            /** @type {any} */ (this.columns),
            this.fields,
            aggregates,
            { hasSelectors: this.props.hasSelectors },
        );
    }

    /** @param {KeyboardEvent} ev */
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

    _confirmGroupInput() {
        const value = /** @type {HTMLInputElement} */ (this.groupInputRef.el).value;
        this.props.onGroupInputConfirm(value);
    }

    /**
     * @param {MouseEvent} ev
     * @param {any} value
     * @param {string} fieldName
     */
    openMultiCurrencyPopover(ev, value, fieldName) {
        this.agg.openMultiCurrencyPopover(ev, value, fieldName);
    }
}
