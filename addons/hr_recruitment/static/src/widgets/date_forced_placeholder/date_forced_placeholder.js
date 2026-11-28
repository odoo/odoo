import { registry } from "@web/core/registry";
import { ListDateTimeField, listDateField } from "@web/views/fields/datetime/list_datetime_field";

export class DateForcedPlaceholder extends ListDateTimeField {
    static template = "hr_recruitment.DateForcedPlaceholder";
}

registry.category("fields").add("hr_recruitment.date_forced_placeholder", {
    ...listDateField,
    component: DateForcedPlaceholder,
});
