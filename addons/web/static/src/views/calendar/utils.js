/** @odoo-module **/

export function getFormattedDateSpan(start, end) {
    const isSameDay = start.hasSame(end, "days");

    if (!isSameDay && start.hasSame(end, "month")) {
        // Simplify date-range if an event occurs into the same month (eg. "August 4-5, 2019")
        return start.toFormat("LLLL d") + "-" + end.toFormat("d, y");
    } else {
        return isSameDay
            ? start.toFormat("DDD")
            : start.toFormat("DDD") + " - " + end.toFormat("DDD");
    }
}
