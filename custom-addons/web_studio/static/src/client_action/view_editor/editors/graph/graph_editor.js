/** @odoo-module */

import { Component, onWillPatch, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { graphView } from "@web/views/graph/graph_view";

import { Property } from "@web_studio/client_action/view_editor/property/property";
import { InteractiveEditorSidebar } from "@web_studio/client_action/view_editor/interactive_editor/interactive_editor_sidebar";
import { SidebarViewToolbox } from "@web_studio/client_action/view_editor/interactive_editor/sidebar_view_toolbox/sidebar_view_toolbox";
import * as operationUtils from "@web_studio/client_action/view_editor/operations_utils";
import { fieldsToChoices } from "@web_studio/client_action/view_editor/editors/utils";
import { useEditNodeAttributes } from "@web_studio/client_action/view_editor/view_editor_model";

export class GraphEditorSidebar extends Component {
    static template = "web_studio.ViewEditor.GraphEditorSidebar";
    static props = {
        openViewInForm: { type: Function, optional: true },
        openDefaultValues: { type: Function, optional: true },
    };
    static components = {
        InteractiveEditorSidebar,
        Property,
        SidebarViewToolbox,
    };

    setup() {
        this.viewEditorModel = useState(this.env.viewEditorModel);
        this.editArchAttributes = useEditNodeAttributes({ isRoot: true });

        onWillPatch(() => {
            this.oldFieldValues = {
                firstDimension: this.modelParams.groupBy[0],
                secondDimension: this.modelParams.groupBy[1],
                measure:
                    this.modelParams.measure === "__count" ? undefined : this.modelParams.measure,
            };
        });
    }

    onViewAttributeChanged(value, name) {
        value = value ? value : "";
        return this.editArchAttributes({ [name]: value });
    }

    onGroupByChanged(type, newField, oldField) {
        const operation = operationUtils.viewGroupByOperation("graph", type, newField, oldField);
        this.viewEditorModel.doOperation(operation);
    }

    get modelParams() {
        return this.viewEditorModel.controllerProps.modelParams;
    }

    get typeChoices() {
        return [
            { label: _t("Bar"), value: "bar" },
            { label: _t("Line"), value: "line" },
            { label: _t("Pie"), value: "pie" },
        ];
    }

    get orderChoices() {
        return [
            { label: _t("Ascending"), value: "asc" },
            { label: _t("Descending"), value: "desc" },
        ];
    }

    get firstGroupbyChoices() {
        return fieldsToChoices(
            this.viewEditorModel.fields,
            (field) =>
                field.store &&
                this.viewEditorModel.GROUPABLE_TYPES.includes(field.type) &&
                field.name !== this.modelParams.groupBy[1]
        );
    }

    get secondGroupbyChoices() {
        return fieldsToChoices(
            this.viewEditorModel.fields,
            (field) =>
                field.store &&
                this.viewEditorModel.GROUPABLE_TYPES.includes(field.type) &&
                field.name !== this.modelParams.groupBy[0]
        );
    }

    get mesureChoices() {
        return fieldsToChoices(
            this.viewEditorModel.fields,
            (field) =>
                field.name !== "id" &&
                field.store &&
                ["integer", "float", "monetary"].includes(field.type)
        );
    }
}

registry.category("studio_editors").add("graph", {
    ...graphView,
    Sidebar: GraphEditorSidebar,
});
