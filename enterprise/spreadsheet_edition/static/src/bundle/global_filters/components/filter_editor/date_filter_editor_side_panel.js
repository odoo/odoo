/** @ts-check */

import { _t } from "@web/core/l10n/translation";
import { FilterFieldOffset } from "../filter_field_offset";
import { RELATIVE_DATE_RANGE_TYPES } from "@spreadsheet/helpers/constants";
import { AbstractFilterEditorSidePanel } from "./filter_editor_side_panel";
import { FilterEditorFieldMatching } from "./filter_editor_field_matching";
import { useState } from "@odoo/owl";

const RANGE_TYPES = [
    { type: "fixedPeriod", description: _t("Month / Quarter") },
    { type: "relative", description: _t("Relative Period") },
    { type: "from_to", description: _t("From / To") },
];

/**
 * @typedef {import("@spreadsheet").GlobalFilter} GlobalFilter
 * @typedef {import("@spreadsheet").OdooField} OdooField
 * @typedef {import("@spreadsheet").FieldMatching} FieldMatching
 * @typedef {import("@spreadsheet").FixedPeriods} FixedPeriods
 *
 *
 * @typedef DateState
 * @property {Object} defaultValue
 * @property {"fixedPeriod" | "relative" | "from_to"} type type of the filter
 * @property {FixedPeriods[]} disabledPeriods
 */

class DateFilterEditorFieldMatching extends FilterEditorFieldMatching {
    static components = {
        ...FilterEditorFieldMatching.components,
        FilterFieldOffset,
    };
    static template = "spreadsheet_edition.DateFilterEditorFieldMatching";
    static props = {
        ...FilterEditorFieldMatching.props,
        onOffsetSelected: Function,
    };
}

/**
 * This is the side panel to define/edit a global filter of type "date".
 */
export class DateFilterEditorSidePanel extends AbstractFilterEditorSidePanel {
    static template = "spreadsheet_edition.DateFilterEditorSidePanel";
    static components = {
        ...AbstractFilterEditorSidePanel.components,
        DateFilterEditorFieldMatching,
    };

    /**
     * @constructor
     */
    setup() {
        super.setup();

        this.type = "date";
        /** @type {DateState} */
        this.dateState = useState({
            defaultValue: undefined,
            type: "fixedPeriod",
            disabledPeriods: [],
        });

        this.relativeDateRangesTypes = RELATIVE_DATE_RANGE_TYPES;
        this.dateRangeTypes = RANGE_TYPES;

        this.ALLOWED_FIELD_TYPES = ["datetime", "date"];
    }

    /**
     * @override
     */
    get filterValues() {
        const values = super.filterValues;
        return {
            ...values,
            defaultValue: this.dateState.defaultValue,
            rangeType: this.dateState.type,
            disabledPeriods: this.dateState.disabledPeriods,
        };
    }

    shouldDisplayFieldMatching() {
        return this.fieldMatchings.length;
    }

    isDateTypeSelected(dateType) {
        return dateType === this.dateState.type;
    }

    /**
     * @override
     * @param {GlobalFilter} globalFilter
     */
    loadSpecificFilterValues(globalFilter) {
        if(globalFilter.type !== "date"){
            return;
        }
        this.dateState.type = globalFilter.rangeType;
        this.dateState.defaultValue = globalFilter.defaultValue;
        if (globalFilter.rangeType === "fixedPeriod") {
            this.dateState.disabledPeriods = globalFilter.disabledPeriods || [];
        }
    }

    /**
     * @override
     * @param {number} index
     * @param {string|undefined} chain
     * @param {OdooField|undefined} field
     */
    onSelectedField(index, chain, field) {
        super.onSelectedField(index, chain, field);
        this.fieldMatchings[index].fieldMatch.offset = 0;
    }

    /**
     * @param {number} index
     * @param {number} offset
     */
    onOffsetSelected(index, offset) {
        this.fieldMatchings[index].fieldMatch.offset = offset;
    }

    onTimeRangeChanged(defaultValue) {
        this.dateState.defaultValue = defaultValue;
    }

    onDateOptionChange(ev) {
        this.dateState.type = ev.target.value;
        this.dateState.defaultValue = undefined;
    }

    toggleDateDefaultValue(checked) {
        const defaultValue = this.dateState.disabledPeriods.includes("month")
            ? "this_year"
            : "this_month";
        this.dateState.defaultValue = checked ? defaultValue : undefined;
    }

    toggleAllowedPeriod(period) {
        const disabledPeriods = this.dateState.disabledPeriods;
        if (disabledPeriods.includes(period)) {
            this.dateState.disabledPeriods = disabledPeriods.filter((p) => p !== period);
        } else {
            this.dateState.disabledPeriods = [...disabledPeriods, period];
        }

        if (
            this.dateState.defaultValue === "this_month" &&
            this.dateState.disabledPeriods.includes("month")
        ) {
            this.dateState.defaultValue = "this_year";
        } else if (
            this.dateState.defaultValue === "this_quarter" &&
            this.dateState.disabledPeriods.includes("quarter")
        ) {
            this.dateState.defaultValue = "this_year";
        }
    }

    get allowedAutomaticValues() {
        const values = [{ value: "this_year", label: _t("Year") }];
        if (!this.dateState.disabledPeriods.includes("month")) {
            values.push({ value: "this_month", label: _t("Month") });
        }
        if (!this.dateState.disabledPeriods.includes("quarter")) {
            values.push({ value: "this_quarter", label: _t("Quarter") });
        }
        return values;
    }
}
