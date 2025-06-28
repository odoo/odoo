/* @odoo-module */

const { DateTime } = luxon;

export function computeDelay(dateStr) {
    const today = DateTime.now().startOf("day");
    const date = DateTime.fromISO(dateStr);
    return date.diff(today, "days").days;
}

export function getMsToTomorrow() {
    const now = new Date();
    const night = new Date(
        now.getFullYear(),
        now.getMonth(),
        now.getDate() + 1, // the next day
        0,
        0,
        0 // at 00:00:00 hours
    );
    return night.getTime() - now.getTime();
}
