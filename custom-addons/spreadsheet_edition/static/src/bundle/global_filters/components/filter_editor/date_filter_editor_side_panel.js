/** @odoo-module */

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
 * @typedef {import("@spreadsheet/global_filters/plugins/global_filters_core_plugin").GlobalFilter} GlobalFilter
 * @typedef {import("@spreadsheet/data_sources/metadata_repository").Field} Field
 * @typedef {import("@spreadsheet/global_filters/plugins/global_filters_core_plugin").FieldMatching} FieldMatching
 *
 * @typedef DateState
 * @property {Object} defaultValue
 * @property {boolean} automaticDefaultValue
 * @property {"fixedPeriod" | "relative" | "from_to"} type type of the filter
 */

class DateFilterEditorFieldMatching extends FilterEditorFieldMatching {}

DateFilterEditorFieldMatching.components = {
    ...FilterEditorFieldMatching.components,
    FilterFieldOffset,
};

DateFilterEditorFieldMatching.template = "spreadsheet_edition.DateFilterEditorFieldMatching";

DateFilterEditorFieldMatching.props = {
    ...FilterEditorFieldMatching.props,
    onOffsetSelected: Function,
};

/**
 * This is the side panel to define/edit a global filter of type "date".
 */
export class DateFilterEditorSidePanel extends AbstractFilterEditorSidePanel {
    /**
     * @constructor
     */
    setup() {
        super.setup();

        this.type = "date";
        /** @type {DateState} */
        this.dateState = useState({
            defaultValue: undefined,
            automaticDefaultValue: false,
            type: "fixedPeriod",
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
        this.dateState.type = globalFilter.rangeType;
        this.dateState.defaultValue = globalFilter.defaultValue;
        this.dateState.automaticDefaultValue = globalFilter.automaticDefaultValue;
    }

    /**
     * @override
     * @param {string} index
     * @param {string|undefined} chain
     * @param {Field|undefined} field
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

    toggleDateDefaultValue(ev) {
        this.dateState.defaultValue = ev.target.checked ? "this_month" : undefined;
    }
}

DateFilterEditorSidePanel.template = "spreadsheet_edition.DateFilterEditorSidePanel";
DateFilterEditorSidePanel.components = {
    ...AbstractFilterEditorSidePanel.components,
    DateFilterEditorFieldMatching,
};
