/* @odoo-module */

const { DateTime } = luxon;

export function computeDelay(dateStr) {
    const today = DateTime.now().startOf("day");
    const date = DateTime.fromISO(dateStr);
    return date.diff(today, "days").days;
}
