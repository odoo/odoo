import { Component, props } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { charFieldProps } from "@web/views/fields/char/char_field";

export class CalendarOpenEventField extends Component {
    static template = "calendar.CalendarOpenEventField";
    props = props(charFieldProps);

    setup() {
        this.orm = useService("orm");
    }
    async onClickOpenRecord() {
        const action = await this.orm.call("calendar.event", "action_open_calendar_event", [
            this.props.record.resId,
        ]);
        this.actionService.doAction(action);
    }
}

export const calendarOpenEventField = {
    component: CalendarOpenEventField,
};

registry.category("fields").add("calendar_open_event", calendarOpenEventField);
