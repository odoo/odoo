import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Component, props, providePlugins, types as t } from "@odoo/owl";
import { View } from "@web/views/view";
import { ResourceCalendarPlugin } from "@resource/plugins/resource_calendar_plugin";
import "@resource/views/resource_calendar_attendance_calendar/resource_calendar_attendance_calendar_view";

export class CalendarOne2Many extends Component {
    static template = "resource.CalendarOne2Many";
    static components = { View };

    // When available, to replace with owl3 standardFieldProps
    props = props({
        id: t.string().optional(),
        name: t.string(),
        readonly: t.boolean().optional(),
        record: t.record(),
    });

    setup() {
        super.setup();
        providePlugins([ResourceCalendarPlugin], { record: this.props.record });
    }

    get viewProps() {
        return {
            type: "calendar",
            resModel: this.props.record.data[this.props.name].resModel,
            domain: [
                ["calendar_id", "=", this.props.record.resId],
                ["date", "!=", false],
            ],
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
    displayName: _t("Calendar One2Many"),
    supportedTypes: ["one2many"],
    useSubView: true,
};

registry.category("fields").add("resource_calendar_attendance_calendar_one2many", calendarOne2Many);
