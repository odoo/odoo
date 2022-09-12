/** @odoo-module **/

import {
    deserializeDate,
    deserializeDateTime,
    serializeDate,
    serializeDateTime,
} from "@web/core/l10n/dates";

export function calculateWeekNumber(date) {
    return luxon.DateTime.fromJSDate(date).weekNumber;
}

export function deserialize(value, type) {
    return type === "date" ? deserializeDate(value) : deserializeDateTime(value);
}
export function serialize(value, type) {
    return type === "date" ? serializeDate(value) : serializeDateTime(value);
}
