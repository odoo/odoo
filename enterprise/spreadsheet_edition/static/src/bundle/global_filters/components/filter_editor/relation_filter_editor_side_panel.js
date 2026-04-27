/** @ts-check */

import { ModelSelector } from "@web/core/model_selector/model_selector";
import { AbstractFilterEditorSidePanel } from "./filter_editor_side_panel";
import { FilterEditorFieldMatching } from "./filter_editor_field_matching";
import { useService } from "@web/core/utils/hooks";
import { MultiRecordSelector } from "@web/core/record_selectors/multi_record_selector";
import { Domain } from "@web/core/domain";
import { user } from "@web/core/user";
import { components } from "@odoo/o-spreadsheet";
import { useState } from "@odoo/owl";
import { SidePanelDomain } from "../../../components/side_panel_domain/side_panel_domain";

const { ValidationMessages } = components;

/**
 * @typedef {import("@spreadsheet").OdooField} OdooField
 * @typedef {import("@spreadsheet").GlobalFilter} GlobalFilter

 *
 * @typedef RelationState
 * @property {GlobalFilter["defaultValue"]} defaultValue
 * @property {Array} displayNames
 * @property {{label?: string, technical?: string}} relatedModel
 * @property {boolean} [includeChildren]
 */

/**
 * This is the side panel to define/edit a global filter of type "relation".
 */
export class RelationFilterEditorSidePanel extends AbstractFilterEditorSidePanel {
    static template = "spreadsheet_edition.RelationFilterEditorSidePanel";
    static components = {
        ...AbstractFilterEditorSidePanel.components,
        ModelSelector,
        MultiRecordSelector,
        FilterEditorFieldMatching,
        SidePanelDomain,
        ValidationMessages,
    };
    setup() {
        super.setup();

        this.type = "relation";
        /** @type {RelationState} */
        this.relationState = useState({
            defaultValue: [],
            displayNames: [],
            includeChildren: undefined,
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
            includeChildren: this.relationState.includeChildren,
            domainOfAllowedValues: this.relationState.domainOfAllowedValues,
        };
    }

    shouldDisplayFieldMatching() {
        return this.fieldMatchings.length && this.relationState.relatedModel.technical;
    }

    /**
     * @override
     * @param {GlobalFilter} globalFilter
     */
    loadSpecificFilterValues(globalFilter) {
        this.relationState.defaultValue = globalFilter.defaultValue;
        this.relationState.relatedModel.technical = globalFilter.modelName;
        this.relationState.includeChildren = globalFilter.includeChildren;
        this.relationState.restrictValuesToDomain = !!globalFilter.domainOfAllowedValues?.length;
        this.relationState.domainOfAllowedValues = globalFilter.domainOfAllowedValues;
    }

    async onWillStart() {
        await super.onWillStart();
        if (!this.isValid) {
            return;
        }
        const promises = [this.fetchModelFromName()];
        if (this.relationState.includeChildren) {
            this.relationState.relatedModel.hasParentRelation = true;
        } else {
            promises.push(this.fetchModelRelation());
        }
        await Promise.all(promises);
    }

    /**
     * Get the first field which could be a relation of the current related
     * model
     *
     * @param {string} model
     * @param {Object.<string, OdooField>} fields Fields to look in
     * @returns {field|undefined}
     */
    _findRelation(model, fields) {
        if (this.relationState.relatedModel.technical === model) {
            return Object.values(fields).find((field) => field.name === "id");
        }
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
        this.relationState.domainOfAllowedValues = [];

        this.fieldMatchings.forEach((object, index) => {
            const field = this._findRelation(object.model(), object.fields());
            this.onSelectedField(index, field ? field.name : undefined, field);
        });
        await this.fetchModelRelation();
        this.relationState.includeChildren = this.relationState.relatedModel.hasParentRelation;
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

    async fetchModelRelation() {
        const technicalName = this.relationState.relatedModel.technical;
        const hasParentRelation = await this.orm.call(
            "ir.model",
            "has_searchable_parent_relation",
            [technicalName]
        );
        this.relationState.relatedModel.hasParentRelation = hasParentRelation;
    }

    /**
     * @param {OdooField} field
     * @returns {boolean}
     */
    isFieldValid(field) {
        const relatedModel = this.relationState.relatedModel.technical;
        return super.isFieldValid(field) && (!relatedModel || field.relation === relatedModel);
    }

    /**
     * @override
     * @param {OdooField} field
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

    toggleDomainRestriction(isChecked) {
        this.relationState.restrictValuesToDomain = isChecked;
        this.relationState.domainOfAllowedValues = [];
    }

    onDomainUpdate(domain) {
        this.relationState.domainOfAllowedValues = domain;
    }

    getEvaluatedDomain() {
        const domain = this.relationState.domainOfAllowedValues;
        if (domain) {
            return new Domain(domain).toList(user.context);
        }
        return [];
    }
}
