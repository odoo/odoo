/** @odoo-module */

import { ModelFieldSelector } from "@web/core/model_field_selector/model_field_selector";

import { Component } from "@odoo/owl";

/**
 * @typedef {import("@spreadsheet").FieldMatching} FieldMatching
 */

export class FilterEditorFieldMatching extends Component {
    static template = "spreadsheet_edition.FilterEditorFieldMatching";
    static components = {
        ModelFieldSelector,
    };

    static props = {
        // See AbstractFilterEditorSidePanel fieldMatchings
        fieldMatchings: Array,
        wrongFieldMatchings: Array,
        selectField: Function,
        filterModelFieldSelectorField: Function,
    };

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
