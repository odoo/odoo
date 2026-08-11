import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Component, providePlugins } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { View } from "@web/views/view";
import { ResourceCalendarPlugin } from "@resource/plugins/resource_calendar_plugin";
import "@resource/views/resource_calendar_attendance_calendar/resource_calendar_attendance_calendar_view";

export class CalendarOne2Many extends Component {
    static template = "resource.CalendarOne2Many";
    static components = { View };
    static props = standardFieldProps;

    setup() {
        super.setup();
        providePlugins([ResourceCalendarPlugin], { record: this.props.record });
    }

    get viewProps() {
        // Only rebuild when resId changes, otherwise the calendar reloads unnecessarily.
        const resId = this.props.record.resId;
        if (this._resId !== resId) {
            this._resId = resId;
            this._viewProps = {
                type: "calendar",
                resModel: this.props.record.data[this.props.name].resModel,
                domain: [
                    ["calendar_id", "=", resId],
                    ["date", "!=", false],
                ],
                display: { controlPanel: false },
                searchViewId: false,
                className: "h-100 w-100 d-flex",
                context: {
                    ...this.props.context,
                    default_calendar_id: resId,
                },
            };
        }
        return this._viewProps;
    }
}

export const calendarOne2Many = {
    component: CalendarOne2Many,
    displayName: _t("Calendar One2Many"),
    supportedTypes: ["one2many"],
    useSubView: true,
};

registry.category("fields").add("resource_calendar_attendance_calendar_one2many", calendarOne2Many);
