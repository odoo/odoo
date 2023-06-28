/** @odoo-module **/

import { registry } from "@web/core/registry";
import { DateTimeField, dateField, dateRangeField, dateTimeField } from "./datetime_field";

export class ListDateTimeField extends DateTimeField {
    /**
     * @override
     */
    get showRange() {
        return this.relatedField && this.values.some(Boolean);
    }

    /**
     * @override
     * @param {number} valueIndex
     */
    getFormattedValue(valueIndex) {
        if (this.emptyField === this.startDateField) {
            valueIndex = valueIndex === 0 ? 1 : 0;
        }
        return super.getFormattedValue(valueIndex);
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
