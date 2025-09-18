// @ts-check

/** @module @web/views/calendar/calendar_utils - Utility functions for calendar record-to-event conversion, color mapping, and date formatting */

/**
 * Convert a calendar record into a FullCalendar event object.
 *
 * @param {Object} record - calendar record with id, title, start, end, isAllDay
 * @param {boolean} [forceAllDay=false] - treat the event as all-day regardless of record flags
 * @returns {{ id: number, title: string, start: string, end: string, allDay: boolean }}
 */
export function convertRecordToEvent(record, forceAllDay = false) {
    const allDay =
        forceAllDay ||
        record.isAllDay ||
        record.end.diff(record.start, "hours").hours >= 24;
    let end = record.end;
    if (
        record.isAllDay ||
        (allDay && end.toMillis() !== end.startOf("day").toMillis())
    ) {
        end = end.plus({ days: 1 });
    }
    return {
        id: record.id,
        title: record.title,
        start: record.start.toISO(),
        end: end.toISO(),
        allDay,
    };
}

const CSS_COLOR_REGEX =
    /^((#[A-F0-9]{3})|(#[A-F0-9]{6})|((hsl|rgb)a?\(\s*(?:(\s*\d{1,3}%?\s*),?){3}(\s*,[0-9.]{1,4})?\))|)$/i;
const colorMap = new Map();
/**
 * Map a key to a stable calendar color index or CSS color string.
 *
 * CSS color strings are returned as-is. Numeric keys are mapped to a
 * palette index (1-55). Other keys receive a deterministic rotating index.
 *
 * @param {string|number|false} key - color key (record id, CSS color, or falsy)
 * @returns {string|number|false} palette index, CSS color string, or false
 */
export function getColor(key) {
    if (!key) {
        return false;
    }
    if (colorMap.has(key)) {
        return colorMap.get(key);
    }

    // check if the key is a css color
    if (typeof key === "string" && CSS_COLOR_REGEX.test(key)) {
        colorMap.set(key, key);
    } else if (typeof key === "number") {
        colorMap.set(key, ((key - 1) % 55) + 1);
    } else {
        colorMap.set(key, (((colorMap.size + 1) * 5) % 24) + 1);
    }

    return colorMap.get(key);
}

/**
 * Format a start/end date pair as a human-readable date span string.
 *
 * Same-month ranges are collapsed (e.g. "August 4-5, 2019"), same-day
 * ranges show a single date, and cross-month ranges show full dates.
 *
 * @param {import("luxon").DateTime} start
 * @param {import("luxon").DateTime} end
 * @returns {string} formatted date span
 */
export function getFormattedDateSpan(start, end) {
    const isSameDay = start.hasSame(end, "days");

    if (!isSameDay && start.hasSame(end, "month")) {
        // Simplify date-range if an event occurs into the same month (eg. "August 4-5, 2019")
        return `${start.toFormat("LLLL d")}-${end.toFormat("d, y")}`;
    } else {
        return isSameDay
            ? start.toFormat("DDD")
            : `${start.toFormat("DDD")} - ${end.toFormat("DDD")}`;
    }
}
