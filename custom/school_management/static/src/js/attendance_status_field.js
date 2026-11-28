/** @odoo-module **/

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class AttendanceStatusField extends Component {
    static template = "school_management.AttendanceStatusField";
    static props = {
        ...standardFieldProps,
    };

    get value() {
        return this.props.record.data[this.props.name];
    }

    get choices() {
        return [
            { value: "present", label: "P", title: _t("Present"), icon: "fa-check", color: "success" },
            { value: "late", label: "L", title: _t("Late"), icon: "fa-clock-o", color: "warning" },
            { value: "absent", label: "A", title: _t("Absent"), icon: "fa-times", color: "danger" },
        ];
    }

    getChoiceClass(choice) {
        return [
            "btn btn-sm o_attendance_status_choice",
            `text-${choice.color}`,
            this.value === choice.value
                ? `is-selected fw-bold border border-2 border-${choice.color}`
                : "opacity-50 border border-light",
        ];
    }

    selectStatus(value) {
        if (!this.props.readonly && this.value !== value) {
            this.props.record.update({ [this.props.name]: value });
        }
    }
}

export const attendanceStatusField = {
    component: AttendanceStatusField,
    displayName: _t("Attendance Status"),
    supportedTypes: ["selection"],
};

registry.category("fields").add("attendance_status", attendanceStatusField);
