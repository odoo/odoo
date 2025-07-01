import { useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useAutoresize } from "@web/core/utils/autoresize";
import { DateTimeField, dateField, dateRangeField, dateTimeField } from "./datetime_field";

export class ListDateTimeField extends DateTimeField {
    setup() {
        super.setup();
        const startDateRef = useRef("start-date");
        useAutoresize(startDateRef, { offset: -5, ignoreIfEmpty: true });
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
