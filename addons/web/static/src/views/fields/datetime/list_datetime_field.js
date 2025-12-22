import { registry } from "@web/core/registry";
import { DateTimeField, dateField, dateRangeField, dateTimeField } from "./datetime_field";

export class ListDateTimeField extends DateTimeField {
    /**
     * @override
     */
    shouldShowSeparator() {
        return this.props.readonly
            ? this.relatedField && this.values.some(Boolean)
            : super.shouldShowSeparator();
    }
}

export const listDateField = { ...dateField, component: ListDateTimeField };
export const listDateRangeField = { ...dateRangeField, component: ListDateTimeField };
export const listDateTimeField = { ...dateTimeField, component: ListDateTimeField };

registry
    .category("fields")
    .add("list.date", listDateField)
    .add("list.daterange", listDateRangeField)
    .add("list.datetime", listDateTimeField);
