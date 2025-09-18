// @ts-check

/** @module @web/core/l10n/date_utils - Pure date comparison, clamping, range checks, and locale-aware week helpers */

import { localization } from "@web/core/l10n/localization";
import { ensureArray } from "@web/core/utils/collections/arrays";

const { DateTime } = /** @type {any} */ (luxon);

/**
 * Checks whether 2 given dates or date ranges are equal. Both values are allowed
 * to be falsy or to not be of the same type (which will return false).
 *
 * @param {any} d1
 * @param {any} d2
 * @returns {boolean}
 */
export function areDatesEqual(d1, d2) {
    if (Array.isArray(d1) || Array.isArray(d2)) {
        d1 = ensureArray(d1);
        d2 = ensureArray(d2);
        return (
            d1.length === d2.length &&
            d1.every((d1Val, i) => areDatesEqual(d1Val, d2[i]))
        );
    }
    if (d1 instanceof DateTime && d2 instanceof DateTime && d1 !== d2) {
        return d1.equals(d2);
    } else {
        return d1 === d2;
    }
}

/**
 * Clamp a DateTime between min and max bounds.
 *
 * @param {any} desired - Luxon DateTime
 * @param {any} minDate - Luxon DateTime
 * @param {any} maxDate - Luxon DateTime
 * @returns {any} Luxon DateTime
 */
export function clampDate(desired, minDate, maxDate) {
    if (maxDate < desired) {
        return maxDate;
    }
    if (minDate > desired) {
        return minDate;
    }
    return desired;
}

/**
 * Get the week year, week number, and start date of a given date's week,
 * respecting the user's locale `weekStart` setting.
 *
 * @param {any} date - JS Date or Luxon DateTime
 * @returns {{ year: number, week: number, startDate: any }}
 */
export function getLocalYearAndWeek(date) {
    if (!date.isLuxonDateTime) {
        date = DateTime.fromJSDate(date);
    }
    const { weekStart } = localization;
    // go to start of week
    const startDate = date.minus({ days: (date.weekday + 7 - weekStart) % 7 });
    // go to nearest Monday, up to 3 days back- or forwards
    date =
        weekStart > 1 && weekStart < 5 // if firstDay after Mon & before Fri
            ? startDate.minus({ days: (startDate.weekday + 6) % 7 }) // then go back 1-3 days
            : startDate.plus({ days: (8 - startDate.weekday) % 7 }); // else go forwards 0-3 days
    date = date.plus({ days: 6 }); // go to last weekday of ISO week
    const jan4 = DateTime.local(date.year, 1, 4);
    // count from previous year if week falls before Jan 4
    const diffDays =
        date < jan4
            ? date.diff(jan4.minus({ years: 1 }), "day").days
            : date.diff(jan4, "day").days;
    return {
        year: date.year,
        week: Math.trunc(diffDays / 7) + 1,
        startDate,
    };
}

/**
 * Get the start of the week for the given date, respecting the user's locale `weekStart`.
 *
 * @param {any} date - Luxon DateTime
 * @returns {any} Luxon DateTime
 */
export function getStartOfLocalWeek(date) {
    const { weekStart } = localization;
    const weekday = date.weekday < weekStart ? weekStart - 7 : weekStart;
    return date.set({ weekday }).startOf("day");
}

/**
 * Get the end of the week for the given date, respecting the user's locale `weekStart`.
 *
 * @param {any} date - Luxon DateTime
 * @returns {any} Luxon DateTime
 */
export function getEndOfLocalWeek(date) {
    return getStartOfLocalWeek(date).plus({ days: 6 }).endOf("day");
}

/**
 * Check whether a value (date or date range) falls within a given range.
 *
 * @param {any} value - DateTime, [DateTime, DateTime], or falsy
 * @param {[any, any]} range - [start, end] DateTime pair
 * @returns {boolean}
 */
export function isInRange(value, range) {
    if (!value || !range) {
        return false;
    }
    if (Array.isArray(value)) {
        const actualValues = value.filter(Boolean).sort();
        if (actualValues.length < 2) {
            return isInRange(actualValues[0], range);
        }
        return (
            (actualValues[0] <= range[0] && range[0] <= actualValues[1]) ||
            (range[0] <= actualValues[0] && actualValues[0] <= range[1])
        );
    } else {
        return range[0] <= value && value <= range[1];
    }
}

/**
 * Returns the start of the current day as a Luxon DateTime.
 * @returns {any}
 */
export function today() {
    return DateTime.local().startOf("day");
}
