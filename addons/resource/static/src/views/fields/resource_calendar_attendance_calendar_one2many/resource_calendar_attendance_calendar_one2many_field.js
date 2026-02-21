/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component } from "@odoo/owl";
import { View } from "@web/views/view";

import "@resource/views/resource_calendar_attendance_calendar/resource_calendar_attendance_calendar_view";

export class CalendarOne2Many extends Component {
    static template = "resource.CalendarOne2Many";
    static components = { View };
    static props = {
        ...standardFieldProps,
    };

    get viewProps() {
        return {
            type: "calendar",
            resModel: this.props.record.data[this.props.name].resModel,
            domain: [["calendar_id", "=", this.props.record.resId]],
            display: { controlPanel: false },
            searchViewId: false,
            className: "h-100 w-100 d-flex",
            context: {
                ...this.props.context,
                default_calendar_id: this.props.record.resId,
            },
        };
    }
}

export const calendarOne2Many = {
    component: CalendarOne2Many,
    displayName: _t("Relational table"),
    supportedTypes: ["one2many"],
    useSubView: true,
};

registry.category("fields").add("resource_calendar_attendance_calendar_one2many", calendarOne2Many);
