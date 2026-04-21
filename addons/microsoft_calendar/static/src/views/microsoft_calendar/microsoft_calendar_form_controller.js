import { RadioField, radioField } from "@web/views/fields/radio/radio_field";
import { registry } from "@web/core/registry";

class MicrosoftRecurrenceUpdateField extends RadioField {
    get items() {
        const items = super.items;
        if (this.props.record.data.microsoft_sync_active) {
            return items.filter(([value]) => value !== "future_events");
        }
        return items;
    }
}

registry.category("fields").add("microsoft_recurrence_update", {
    ...radioField,
    component: MicrosoftRecurrenceUpdateField,
    additionalClasses: ["o_field_radio"],
});
