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
        if (this.location) {
            let color = "text-muted";
            if (this.props.record.data.hr_presence_state !== "out_of_working_hour") {
                color = this.props.record.data.hr_presence_state === "present" ?  "text-success" : "o_icon_employee_absent";
            }
            return color;
        }
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
        if (this.location) {
            switch (this.location) {
                case "home":
                    return "fa-home";
                case "office":
                    return "fa-building";
                case "other":
                    return "fa-map-marker";
            }
        }
        return `fa-circle${this.value.startsWith("presence_archive") ? "-o" : ""}`;
    }

    get location() {
        let workLocation = this.value?.split("_")[1] || "";
        if (workLocation && !['home', 'office', 'other'].includes(workLocation)) {
            workLocation = "";
        }
        return workLocation;
    }

    get label() {
        if (this.location) {
            return this.props.record.data.work_location_name || _t("Unspecified");
        }
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
    displayName: _t("HR Presence Status"),
    fieldDependencies: [
        { name: "hr_presence_state", type: "selection" },
        { name: "work_location_name", type: "char" },
    ],
    extractProps({ viewType }, dynamicInfo) {
        return {
            tag: viewType === "kanban" ? "span" : "small",
        };
    },
};

registry.category("fields").add("hr_presence_status", hrPresenceStatus)
