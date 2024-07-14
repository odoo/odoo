/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { pivotView } from "@web/views/pivot/pivot_view";

import { Property } from "@web_studio/client_action/view_editor/property/property";
import { InteractiveEditorSidebar } from "@web_studio/client_action/view_editor/interactive_editor/interactive_editor_sidebar";
import { SidebarViewToolbox } from "@web_studio/client_action/view_editor/interactive_editor/sidebar_view_toolbox/sidebar_view_toolbox";
import * as operationUtils from "@web_studio/client_action/view_editor/operations_utils";
import { fieldsToChoices } from "@web_studio/client_action/view_editor/editors/utils";

import { Record } from "@web/model/record";
import { Many2ManyTagsField } from "@web/views/fields/many2many_tags/many2many_tags_field";

import { useEditNodeAttributes } from "@web_studio/client_action/view_editor/view_editor_model";
import { computeReportMeasures } from "@web/views/utils";
import { MultiRecordSelector } from "@web/core/record_selectors/multi_record_selector";

function getFieldNameFromGroupby(str) {
    return str.split(":")[0];
}

export class PivotEditorSidebar extends Component {
    static template = "web_studio.ViewEditor.PivotEditorSidebar";
    static props = {
        openViewInForm: { type: Function, optional: true },
        openDefaultValues: { type: Function, optional: true },
    };
    static components = {
        InteractiveEditorSidebar,
        Property,
        SidebarViewToolbox,
        Record,
        Many2ManyTagsField,
        MultiRecordSelector,
    };

    setup() {
        this.viewEditorModel = useState(this.env.viewEditorModel);
        this.editArchAttributes = useEditNodeAttributes({ isRoot: true });
    }

    get possibleMeasures() {
        const { fieldAttrs, activeMeasures } = this.archInfo;
        return computeReportMeasures(this.viewEditorModel.fields, fieldAttrs, activeMeasures);
    }

    get multiRecordSelectorProps() {
        return {
            resModel: "ir.model.fields",
            update: this.changeMeasureFields.bind(this),
            resIds: this.currentMeasureFields,
            domain: [
                ["model", "=", this.viewEditorModel.resModel],
                ["name", "in", Object.keys(this.possibleMeasures)],
            ],
        };
    }

    get currentMeasureFields() {
        return (
            JSON.parse(
                this.viewEditorModel.xmlDoc.firstElementChild.getAttribute(
                    "studio_pivot_measure_field_ids"
                )
            ) || []
        );
    }

    get archInfo() {
        return this.viewEditorModel.controllerProps.modelParams.metaData;
    }

    get rowGroupBys() {
        return this.archInfo.rowGroupBys.map((fName) => getFieldNameFromGroupby(fName));
    }

    get colGroupBys() {
        return this.archInfo.colGroupBys.map((fName) => getFieldNameFromGroupby(fName));
    }

    /**
     * @param {Array<Number>} resIds
     */
    changeMeasureFields(resIds) {
        const currentFullIds = this.currentMeasureFields;
        const newIds = resIds.filter((id) => !currentFullIds.includes(id));
        let toRemoveIds;

        const operationType = newIds.length ? "add" : "remove";

        if (operationType === "remove") {
            toRemoveIds = currentFullIds.filter((id) => !resIds.includes(id));
        }

        this.viewEditorModel.doOperation({
            type: "pivot_measures_fields",
            target: {
                operation_type: operationType,
                field_ids: operationType === "add" ? newIds : toRemoveIds,
            },
        });
    }

    onGroupByChanged(type, newValue, oldValue) {
        const operation = operationUtils.viewGroupByOperation("pivot", type, newValue, oldValue);
        this.viewEditorModel.doOperation(operation);
    }

    onViewAttributeChanged(value, name) {
        value = value ? value : "";
        return this.editArchAttributes({ [name]: value });
    }

    get columnGroupbyChoices() {
        return fieldsToChoices(
            this.viewEditorModel.fields,
            (field) =>
                field.store &&
                this.viewEditorModel.GROUPABLE_TYPES.includes(field.type) &&
                ![this.archInfo.rowGroupBys[0], this.archInfo.rowGroupBys[1]].includes(field.name)
        );
    }

    get rowGroupbyChoices_first() {
        return fieldsToChoices(
            this.viewEditorModel.fields,
            (field) =>
                field.store &&
                this.viewEditorModel.GROUPABLE_TYPES.includes(field.type) &&
                ![this.archInfo.colGroupBys[0], this.archInfo.rowGroupBys[1]].includes(field.name)
        );
    }

    get rowGroupbyChoices_second() {
        return fieldsToChoices(
            this.viewEditorModel.fields,
            (field) =>
                field.store &&
                this.viewEditorModel.GROUPABLE_TYPES.includes(field.type) &&
                ![this.archInfo.colGroupBys[0], this.archInfo.rowGroupBys[0]].includes(field.name)
        );
    }
}

registry.category("studio_editors").add("pivot", {
    ...pivotView,
    Sidebar: PivotEditorSidebar,
});
