/** @odoo-module **/

import {
    deserializeDate,
    deserializeDateTime,
    serializeDate,
    serializeDateTime,
} from "@web/core/l10n/dates";

export function calculateWeekNumber(date) {
    //WOWL: USED ONLY FOR THE DATEPICKER (NEEDED ???)
    return luxon.DateTime.fromJSDate(date).weekNumber;
}

export function deserialize(value, type) {
    return type === "date" ? deserializeDate(value) : deserializeDateTime(value);
}
export function serialize(value, type) {
    return type === "date" ? serializeDate(value) : serializeDateTime(value);
}
