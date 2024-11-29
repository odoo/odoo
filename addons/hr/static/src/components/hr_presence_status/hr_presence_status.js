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
        classNames.push(this.icon, "fa-fw", "o_button_icon", "align-middle", this.color);
        return classNames.join(" ");
    }

    get color() {
        switch (this.value) {
            case "online":
            case "bot":
            case "presence_present":
                return "text-success";
            case "presence_absent":
                return "o_icon_employee_absent";
            case "offline":
                return "text-700";
            case "away":
            case "presence_out_of_working_hour":
            case "presence_archive":
                return "text-muted";
            default:
                return "";
        }
    }

    get icon() {
        switch (this.status) {
            case "online":
            case "presence_present":
            case "presence_to_define":
                return "fa-circle";
            case "offline":
            case "presence_absent":
            case "presence_absent_active":
                return "fa-circle-o";
            case "bot":
                return "fa-heart";
            default:
                return "fa-question-circle";
        }
    }

    get label() {
        if (!this.im_status) {
            return this.value && this.value !== false
                ? this.options.find(([value, label]) => value === this.value)[1]
                : "";
        }
        switch (this.status) {
            case "online":
                return "User is online";
            case "away":
                return "User is idle";
            case "offline":
                return "User is offline";
            case "bot":
                return "User is a bot";
            default:
                return "No IM status available";
        }
    }

    get options() {
        return this.props.record.fields[this.props.name].selection.filter(
            (option) => option[0] !== false && option[1] !== ""
        );
    }

    get value() {
        return this.props.record.data[this.props.name];
    }

    get im_status() {
        return this.props.record.data.im_status;
    }

    get status() {
        return this.im_status || this.value;
    }
}

export const hrPresenceStatus = {
    component: HrPresenceStatus,
    displayName: _t("HR Presence Status"),
    extractProps({ viewType }, dynamicInfo) {
        return {
            tag: viewType === "kanban" ? "span" : "small",
        };
    },
    fieldDependencies: [{ name: "im_status", type: "char" }],
};

registry.category("fields").add("hr_presence_status", hrPresenceStatus);
