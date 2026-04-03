import { Component } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class HrPresenceStatus extends Component {
    static template = "hr.HrPresenceStatus";
    static props = {
        ...standardFieldProps,
    };

    get classNames() {
        return `o_employee_availability oi ${this.iconClass} oi-fw o_button_icon hr_presence align-middle ${this.color}`;
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
                return "text-muted";
            default:
                return "";
        }
    }

    get icon() {
        if (this.location) {
            switch (this.location) {
                case "home":
                    return "home";
                case "office":
                    return "business";
                case "other":
                    return "location_on";
            }
        }
        return "circle";
    }

    get iconClass() {
        if (this.location === "office" || !this.location) {
            return "oi-filled";
        }
    }

    get location() {
        return this.props.record.data.work_location_type;
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

    get isActive() {
        return this.props.record.data.active;
    }
}

export const hrPresenceStatus = {
    additionalClasses: ["position-absolute", "d-flex", "align-items-center", "justify-content-center", "bg-light", "rounded-circle","top-0", "end-0"],
    component: HrPresenceStatus,
    fieldDependencies: [
        { name: "active", type: "boolean" },
        { name: "hr_presence_state", type: "selection" },
        { name: "work_location_type", type: "char" },
        { name: "work_location_name", type: "char" },
    ],
    displayName: _t("HR Presence Status"),
};

registry.category("fields").add("hr_presence_status", hrPresenceStatus)
