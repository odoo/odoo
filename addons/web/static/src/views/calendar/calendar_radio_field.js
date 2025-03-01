import { onWillRender } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { radioField, RadioField } from "@web/views/fields/radio/radio_field";

export class CalendarRadioField extends RadioField {
    static template = "web.CalendarRadioField";

    setup() {
        super.setup();
        this.counters = {};
        onWillRender(() => {
            this.counters = this.env.calendarModel.computeCounters(this.props.name);
        });
    }
}

export const calendarRadioField = {
    ...radioField,
    component: CalendarRadioField,
};

registry.category("fields").add("calendar_radio", calendarRadioField);
