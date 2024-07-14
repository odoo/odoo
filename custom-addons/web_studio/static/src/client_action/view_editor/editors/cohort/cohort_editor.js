/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { cohortView } from "@web_cohort/cohort_view";

import { Property } from "@web_studio/client_action/view_editor/property/property";
import { InteractiveEditorSidebar } from "@web_studio/client_action/view_editor/interactive_editor/interactive_editor_sidebar";
import { SidebarViewToolbox } from "@web_studio/client_action/view_editor/interactive_editor/sidebar_view_toolbox/sidebar_view_toolbox";
import { fieldsToChoices } from "@web_studio/client_action/view_editor/editors/utils";
import { useEditNodeAttributes } from "@web_studio/client_action/view_editor/view_editor_model";

export class CohortEditorSidebar extends Component {
    static template = "web_studio.ViewEditor.CohortEditorSidebar";
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
    }

    onViewAttributeChanged(value, name) {
        value = value ? value : "";
        return this.editArchAttributes({ [name]: value });
    }

    get modelParams() {
        return this.env.viewEditorModel.controllerProps.modelParams;
    }

    get dateFields() {
        return fieldsToChoices(
            this.viewEditorModel.fields,
            (field) => field.store && ["date", "datetime"].includes(field.type)
        );
    }

    get measureFields() {
        return fieldsToChoices(
            this.viewEditorModel.fields,
            (field) =>
                field.name !== "id" &&
                field.store &&
                ["integer", "float", "monetary"].includes(field.type)
        );
    }

    get intervalChoices() {
        return [
            { label: _t("Day"), value: "day" },
            { label: _t("Week"), value: "week" },
            { label: _t("Month"), value: "month" },
            { label: _t("Year"), value: "year" },
        ];
    }

    get modeChoices() {
        return [
            { label: _t("Retention"), value: "retention" },
            { label: _t("Churn"), value: "churn" },
        ];
    }

    get timelineChoices() {
        return [
            { label: _t("Forward"), value: "forward" },
            { label: _t("Backwards"), value: "backward" },
        ];
    }
}

registry.category("studio_editors").add("cohort", {
    ...cohortView,
    Sidebar: CohortEditorSidebar,
});
