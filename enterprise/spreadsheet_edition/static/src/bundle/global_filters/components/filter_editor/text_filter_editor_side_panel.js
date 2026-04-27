/** @ts-check */

import { AbstractFilterEditorSidePanel } from "./filter_editor_side_panel";
import { FilterEditorFieldMatching } from "./filter_editor_field_matching";
import { TextFilterValue } from "@spreadsheet/global_filters/components/filter_text_value/filter_text_value";

import { components } from "@odoo/o-spreadsheet";
import { useState } from "@odoo/owl";

const { SelectionInput } = components;

/**
 * @typedef {import("@spreadsheet").GlobalFilter} GlobalFilter
 *
 * @typedef TextState
 * @property {string} defaultValue

 */

/**
 * This is the side panel to define/edit a global filter of type "text".
 */
export class TextFilterEditorSidePanel extends AbstractFilterEditorSidePanel {
    static template = "spreadsheet_edition.TextFilterEditorSidePanel";
    static components = {
        ...AbstractFilterEditorSidePanel.components,
        FilterEditorFieldMatching,
        TextFilterValue,
        SelectionInput,
    };

    setup() {
        super.setup();

        this.type = "text";
        /** @type {TextState} */
        this.textState = useState({
            defaultValue: "",
            restrictValuesToRange: false,
            rangeOfAllowedValues: undefined,
        });
        this.ALLOWED_FIELD_TYPES = ["many2one", "text", "char"];
    }

    get rangesForSelectionInput() {
        // SelectionInput expects an array of ranges
        if (!this.textState.rangeOfAllowedValues) {
            return [];
        }
        return [this.textState.rangeOfAllowedValues];
    }

    get textOptionsFromRange() {
        if (!this.textState.restrictValuesToRange) {
            return [];
        }
        const range = this.env.model.getters.getRangeFromSheetXC(
            this.env.model.getters.getActiveSheetId(),
            this.textState.rangeOfAllowedValues
        );
        return this.env.model.getters.getTextFilterOptionsFromRange(range, [
            this.textState.defaultValue,
        ]);
    }

    /**
     * @override
     */
    shouldDisplayFieldMatching() {
        return this.fieldMatchings.length;
    }

    /**
     * @override
     */
    get filterValues() {
        const values = super.filterValues;
        const sheetId = this.env.model.getters.getActiveSheetId();
        const { restrictValuesToRange, rangeOfAllowedValues, defaultValue } = this.textState;
        const rangeString = restrictValuesToRange && rangeOfAllowedValues;
        const range = rangeString
            ? this.env.model.getters.getRangeDataFromXc(sheetId, rangeString)
            : undefined;
        return {
            ...values,
            defaultValue: defaultValue,
            rangeOfAllowedValues: range,
        };
    }

    /**
     * @override
     * @param {GlobalFilter} globalFilter
     */
    loadSpecificFilterValues(globalFilter) {
        const { rangeOfAllowedValues, defaultValue } = globalFilter;
        this.textState.defaultValue = defaultValue;
        this.textState.restrictValuesToRange = !!rangeOfAllowedValues;
        if (rangeOfAllowedValues) {
            const rangeString = this.env.model.getters.getRangeString(
                rangeOfAllowedValues,
                this.env.model.getters.getActiveSheetId()
            );
            this.textState.rangeOfAllowedValues = rangeString;
        }
    }

    onRangeChanged(ranges) {
        this.textState.rangeOfAllowedValues = ranges[0];
    }

    onRangeConfirmed() {}
}
