/** @odoo-module */

import { ModelFieldSelector } from "@web/core/model_field_selector/model_field_selector";

import { Component } from "@odoo/owl";

/**
 * @typedef {import("@spreadsheet/global_filters/plugins/global_filters_core_plugin").FieldMatching} FieldMatching
 * @typedef {import("@spreadsheet/data_sources/metadata_repository").Field} Field
 */

export class FilterEditorFieldMatching extends Component {
    /**
     *
     * @param {FieldMatching} fieldMatch
     * @returns {string}
     */
    getModelField(fieldMatch) {
        if (!fieldMatch || !fieldMatch.chain) {
            return "";
        }
        return fieldMatch.chain;
    }
}
FilterEditorFieldMatching.template = "spreadsheet_edition.FilterEditorFieldMatching";

FilterEditorFieldMatching.components = {
    ModelFieldSelector,
};

FilterEditorFieldMatching.props = {
    // See AbstractFilterEditorSidePanel fieldMatchings
    fieldMatchings: Array,
    wrongFieldMatchings: Array,
    selectField: Function,
    filterModelFieldSelectorField: Function,
};
