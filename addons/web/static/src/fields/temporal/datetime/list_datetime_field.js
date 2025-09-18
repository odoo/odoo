// @ts-check

/** @module @web/fields/temporal/datetime/list_datetime_field - List-view variant of datetime/date fields with auto-resizing input */

import { useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useAutoresize } from "@web/core/utils/dom/autoresize";

import {
    dateField,
    dateRangeField,
    DateTimeField,
    dateTimeField,
} from "./datetime_field";

export class ListDateTimeField extends DateTimeField {
    setup() {
        super.setup();
        const startDateRef = useRef("start-date");
        useAutoresize(/** @type {any} */ (startDateRef), {
            ignoreIfEmpty: true,
        });
    }
}

export const listDateField = { ...dateField, component: ListDateTimeField };
export const listDateRangeField = {
    ...dateRangeField,
    component: ListDateTimeField,
};
export const listDateTimeField = {
    ...dateTimeField,
    component: ListDateTimeField,
};

registry
    .category("fields")
    .add("list.date", /** @type {any} */ (listDateField))
    .add("list.daterange", /** @type {any} */ (listDateRangeField))
    .add("list.datetime", /** @type {any} */ (listDateTimeField));
