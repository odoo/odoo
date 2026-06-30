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

/**
 * Get the week number of a given date.
 * Returns the ISO week number of the Monday nearest to the first day of the week.
 *
 * @param {Date | luxon.DateTime} date
 * @param {number} first day of the week (optional)
 * @returns {number} week number
 */
export function getWeekNumber(date, firstDay) {
    if (!date.isLuxonDateTime) {
        date = luxon.DateTime.fromJSDate(date);
    }
    if (Number.isInteger(firstDay)) { // go to start of week
        date = date.minus({ days: (date.weekday + 7 - firstDay) % 7 });
    } else {
        firstDay = date.weekday;
    }
    // go to nearest Monday, up to 3 days back- or forwards
    date = firstDay > 1 && firstDay < 5 // if firstDay after Mon & before Fri
        ? date.minus({ days: (date.weekday + 6) % 7 }) // then go back 1-3 days
        : date.plus({ days: (8 - date.weekday) % 7 }); // else go forwards 0-3 days
    date = date.plus({ days: 6 }); // go to last weekday of ISO week
    const jan4 = luxon.DateTime.local(date.year, 1, 4);
    // count from previous year if week falls before Jan 4
    const diffDays = date < jan4
        ? date.diff(jan4.minus({ years: 1 }), 'day').days
        : date.diff(jan4, 'day').days;
    return Math.trunc(diffDays / 7) + 1;
}
