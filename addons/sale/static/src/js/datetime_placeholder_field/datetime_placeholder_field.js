import { registry } from "@web/core/registry";
import { DateTimeField, dateTimeField } from "@web/views/fields/datetime/datetime_field";

export class DatetimePlaceholderField extends DateTimeField {
    static template = "sale.DatetimePlaceholderField";

    get placeholder() {
        return super.getFormattedValue(0) || this.props.placeholder;
    }
}

registry.category("fields").add("datetime_placeholder_field", {
    ...dateTimeField,
    component: DatetimePlaceholderField,
});
