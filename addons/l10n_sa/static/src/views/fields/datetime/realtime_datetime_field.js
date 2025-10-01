/** @odoo-module **/
import { DateTimeField, dateTimeField } from "@web/views/fields/datetime/datetime_field";
import { registry } from "@web/core/registry";

const { DateTime } = luxon;

class RealTimeDateTimeField extends DateTimeField {
    isDateInTheFuture(index) {
        return this.values[index] > DateTime.local();
    }
}

export const realTimeDateTimeField = {
    ...dateTimeField,
    component: RealTimeDateTimeField,
}

registry.category("fields").add("real_time_datetime", realTimeDateTimeField);
