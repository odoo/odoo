import { ganttView } from "@web_gantt/gantt_view";
import { registry } from "@web/core/registry";

import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { InteractiveEditorSidebar } from "@web_studio/client_action/view_editor/interactive_editor/interactive_editor_sidebar";
import { Property } from "@web_studio/client_action/view_editor/property/property";
import { SidebarViewToolbox } from "@web_studio/client_action/view_editor/interactive_editor/sidebar_view_toolbox/sidebar_view_toolbox";
import { useEditNodeAttributes } from "@web_studio/client_action/view_editor/view_editor_model";

export class GanttEditorSidebar extends Component {
    static template = "web_studio.ViewEditor.GanttEditorSidebar";
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

    get colorChoices() {
        return this.modelParams.decorationFields.map((value) => {
            return {
                label: this.modelParams.fields[value].string,
                value,
            };
        });
    }

    get currentDayPrecision() {
        return this.dayPrecisionChoices.find((e) => e.value === this.precisionValues.day)?.value;
    }

    get currentWeekPrecision() {
        return this.weekAndMonthPrecisionChoices.find((e) => e.value === this.precisionValues.week)
            ?.value;
    }

    get currentMonthPrecision() {
        return this.weekAndMonthPrecisionChoices.find((e) => e.value === this.precisionValues.month)
            ?.value;
    }

    get dayPrecisionChoices() {
        return [
            { label: _t("Quarter Hour"), value: "hour:quarter" },
            { label: _t("Half Hour"), value: "hour:half" },
            { label: _t("Hour"), value: "hour:full" },
        ];
    }

    get defaultOrderChoices() {
        return [
            { value: "asc", label: _t("Ascending") },
            { value: "desc", label: _t("Descending") },
        ];
    }

    get defaultScalesChoices() {
        const allowedScales = Object.keys(this.modelParams.scales);
        return [
            { value: "day", label: _t("Day") },
            { value: "week", label: _t("Week") },
            { value: "week_2", label: _t("Week (expanded)") },
            { value: "month", label: _t("Month") },
            { value: "month_3", label: _t("Month (expanded)") },
            { value: "year", label: _t("Year") },
        ].filter((e) => allowedScales.includes(e.value));
    }

    get displayModeChoices() {
        return [
            { label: _t("Dense"), value: "dense" },
            { label: _t("Sparse"), value: "sparse" },
        ];
    }

    get fieldsChoices() {
        return Object.values(this.modelParams.fields)
            .filter((f) => f.groupable && this.viewEditorModel.GROUPABLE_TYPES.includes(f.type))
            .map((f) => {
                return {
                    label: f.string,
                    value: f.name,
                };
            });
    }

    get fieldsDateChoices() {
        return Object.values(this.modelParams.fields)
            .filter((f) => f.store && ["date", "datetime"].includes(f.type))
            .map((f) => {
                return {
                    label: f.string,
                    value: f.name,
                };
            });
    }

    get modelParams() {
        return this.viewEditorModel.controllerProps.modelParams.metaData;
    }

    get weekAndMonthPrecisionChoices() {
        return [
            { label: _t("Half Day"), value: "day:half" },
            { label: _t("Day"), value: "day:full" },
        ];
    }

    get precisionValues() {
        const precision =
            this.viewEditorModel.xmlDoc
                .querySelector("gantt")
                .getAttribute("precision")
                ?.replace(/'/g, '"') || "{}";
        return JSON.parse(precision);
    }

    onDefaultGroupByChanged(selection) {
        this.onViewAttributeChanged(selection.join(","), "default_group_by");
    }

    onPrecisionChanged(value, name) {
        const precision = this.precisionValues;
        precision[name] = value;
        this.onViewAttributeChanged(JSON.stringify(precision), "precision");
    }

    onViewAttributeChanged(value, name) {
        return this.editArchAttributes({ [name]: value });
    }
}

registry.category("studio_editors").add("gantt", {
    ...ganttView,
    Sidebar: GanttEditorSidebar,
});
