import { Component } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class HrPresenceStatus extends Component {
    static template = "hr.HrPresenceStatus";
    static props = {
        ...standardFieldProps,
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        tag: "small",
    };

    get classNames() {
        const classNames = ["fa"];
        classNames.push(
            this.icon,
            "fa-fw",
            "o_button_icon",
            "hr_presence",
            "align-middle",
            this.color,
        )
        return classNames.join(" ");
    }

    get color() {
        switch (this.value) {
            case "presence_present":
                return "text-success";
            case "presence_absent":
                return "o_icon_employee_absent";
            case "presence_out_of_working_hour":
            case "presence_archive":
                return "text-muted";
            default:
                return "";
        }
    }

    get icon() {
        return `fa-circle${this.value.startsWith("presence_archive") ? "-o" : ""}`;
    }

    get label() {
        return this.value !== false
            ? this.options.find(([value, label]) => value === this.value)[1]
            : "";
    }

    get options() {
        return this.props.record.fields[this.props.name].selection.filter(
            (option) => option[0] !== false && option[1] !== ""
        );
    }

    get value() {
        return this.props.record.data[this.props.name];
    }
}

export const hrPresenceStatus = {
    component: HrPresenceStatus,
    fieldDependencies: [],
    displayName: _t("HR Presence Status"),
    extractProps({ viewType }, dynamicInfo) {
        return {
            tag: viewType === "kanban" ? "span" : "small",
        };
    },
};

registry.category("fields").add("hr_presence_status", hrPresenceStatus)
