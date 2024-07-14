/** @odoo-module */

import { ModelSelector } from "@web/core/model_selector/model_selector";
import { AbstractFilterEditorSidePanel } from "./filter_editor_side_panel";
import { FilterEditorFieldMatching } from "./filter_editor_field_matching";
import { useService } from "@web/core/utils/hooks";
import { MultiRecordSelector } from "@web/core/record_selectors/multi_record_selector";

import { useState } from "@odoo/owl";

/**
 * @typedef {import("@spreadsheet/data_sources/metadata_repository").Field} Field
 * @typedef {import("@spreadsheet/global_filters/plugins/global_filters_core_plugin").GlobalFilter} GlobalFilter

 *
 * @typedef RelationState
 * @property {GlobalFilter["defaultValue"]} defaultValue
 * @property {Array} displayNames
 * @property {{label?: string, technical?: string}} relatedModel
 */

/**
 * This is the side panel to define/edit a global filter of type "relation".
 */
export class RelationFilterEditorSidePanel extends AbstractFilterEditorSidePanel {
    setup() {
        super.setup();

        this.type = "relation";
        /** @type {RelationState} */
        this.relationState = useState({
            defaultValue: [],
            displayNames: [],
            relatedModel: {
                label: undefined,
                technical: undefined,
            },
        });
        this.nameService = useService("name");

        this.ALLOWED_FIELD_TYPES = ["many2one", "many2many", "one2many"];
    }

    get missingModel() {
        return this.genericState.saved && !this.relationState.relatedModel.technical;
    }

    get missingRequired() {
        return super.missingRequired || this.missingModel;
    }

    /**
     * @override
     */
    get filterValues() {
        const values = super.filterValues;
        return {
            ...values,
            defaultValue: this.relationState.defaultValue,
            defaultValueDisplayNames: this.relationState.displayNames,
            modelName: this.relationState.relatedModel.technical,
        };
    }

    shouldDisplayFieldMatching() {
        return this.fieldMatchings.length && this.relationState.relatedModel.technical;
    }

    /**
     * List of model names of all related models of all pivots
     * @returns {Array<string>}
     */
    get relatedModels() {
        const all = this.fieldMatchings.map((object) => Object.values(object.fields()));
        return [
            ...new Set(
                all
                    .flat()
                    .filter((field) => field.relation)
                    .map((field) => field.relation)
            ),
        ];
    }

    /**
     * @override
     * @param {GlobalFilter} globalFilter
     */
    loadSpecificFilterValues(globalFilter) {
        this.relationState.defaultValue = globalFilter.defaultValue;
        this.relationState.relatedModel.technical = globalFilter.modelName;
    }

    async onWillStart() {
        await super.onWillStart();
        await this.fetchModelFromName();
    }

    /**
     * Get the first field which could be a relation of the current related
     * model
     *
     * @param {Object.<string, Field>} fields Fields to look in
     * @returns {field|undefined}
     */
    _findRelation(fields) {
        const field = Object.values(fields).find(
            (field) =>
                field.searchable && field.relation === this.relationState.relatedModel.technical
        );
        return field;
    }

    async onModelSelected({ technical, label }) {
        if (!this.genericState.label) {
            this.genericState.label = label;
        }
        if (this.relationState.relatedModel.technical !== technical) {
            this.relationState.defaultValue = [];
        }
        this.relationState.relatedModel.technical = technical;
        this.relationState.relatedModel.label = label;

        this.fieldMatchings.forEach((object, index) => {
            const field = this._findRelation(object.fields());
            this.onSelectedField(index, field ? field.name : undefined, field);
        });
    }

    async fetchModelFromName() {
        if (!this.relationState.relatedModel.technical) {
            return;
        }
        const result = await this.orm.call("ir.model", "display_name_for", [
            [this.relationState.relatedModel.technical],
        ]);
        this.relationState.relatedModel.label = result[0] && result[0].display_name;
        if (!this.genericState.label) {
            this.genericState.label = this.relationState.relatedModel.label;
        }
    }

    /**
     * @param {Field} field
     * @returns {boolean}
     */
    isFieldValid(field) {
        const relatedModel = this.relationState.relatedModel.technical;
        return super.isFieldValid(field) && (!relatedModel || field.relation === relatedModel);
    }

    /**
     * @override
     * @param {Field} field
     * @returns {boolean}
     */
    matchingRelation(field) {
        return field.relation === this.relationState.relatedModel.technical;
    }

    /**
     * @param {Number[]} value
     */
    async onValuesSelected(resIds) {
        const displayNames = await this.nameService.loadDisplayNames(
            this.relationState.relatedModel.technical,
            resIds
        );
        this.relationState.defaultValue = resIds;
        this.relationState.displayNames = Object.values(displayNames);
    }

    toggleDefaultsToCurrentUser(ev) {
        this.relationState.defaultValue = ev.target.checked ? "current_user" : undefined;
    }
}

RelationFilterEditorSidePanel.template = "spreadsheet_edition.RelationFilterEditorSidePanel";
RelationFilterEditorSidePanel.components = {
    ...AbstractFilterEditorSidePanel.components,
    ModelSelector,
    MultiRecordSelector,
    FilterEditorFieldMatching,
};
