/** @ts-check */

import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";
import { Domain } from "@web/core/domain";

const { Interval } = luxon;

/**
 * @typedef {import("@spreadsheet").RelativeDateValue} RelativeDateValue
 * @typedef {import("@spreadsheet").RelativeUnit} RelativeUnit
 */

const unitsToLuxon = {
    day: "days",
    week: "weeks",
    week_to_date: "weeks",
    month: "months",
    month_to_date: "months",
    quarter: "quarters",
    year: "years",
    year_to_date: "years",
};

/**
 * Compute the interval (start and end dat§es) for a relative date value, with
 * a period offset.
 *
 * @param {luxon.DateTime} now current time, as luxon time
 * @param {RelativeDateValue} value
 * @param {number} periodOffset
 *
 * @returns {luxon.Interval}
 */
export function getRelativeDateInterval(now, value, periodOffset) {
    const intervalWithoutOffset = relativeDateValueToInterval(now, value);
    return applyOffsetToInterval(intervalWithoutOffset, value, periodOffset);
}

/**
 * Get a date domain relative to the current date.
 * The domain will span the amount of time specified in rangeType and end the day before the current day.
 *
 *
 * @param {luxon.DateTime} now current time, as luxon time
 * @param {number} periodOffset offset to add to the date
 * @param {RelativeDateValue} relativeDateValue
 * @param {string} fieldName
 * @param {"date" | "datetime"} fieldType
 *
 * @returns {Domain|undefined}
 */
export function getRelativeDateDomain(now, periodOffset, relativeDateValue, fieldName, fieldType) {
    const interval = getRelativeDateInterval(now, relativeDateValue, periodOffset);
    const leftBound = serializeDateOrDateTime(interval.start.startOf("day"), fieldType);
    const rightBound = serializeDateOrDateTime(interval.end.endOf("day"), fieldType);

    return new Domain(["&", [fieldName, ">=", leftBound], [fieldName, "<=", rightBound]]);
}

/**
 * Serialize a luxon.DateTime object to a date or datetime server format string.
 * @param {luxon.DateTime} dateTime
 * @param {"date" | "datetime"} type
 */
function serializeDateOrDateTime(dateTime, type) {
    return type === "date" ? serializeDate(dateTime) : serializeDateTime(dateTime);
}

/**
 * Get the interval for a relative date value.
 *
 * @param {luxon.DateTime} now
 * @param {RelativeDateValue} value
 * @returns {luxon.Interval}
 */
function relativeDateValueToInterval(now, value) {
    const interval = value.interval || 1;
    if (!unitsToLuxon[value.unit]) {
        throw new Error(`Unknown unit: ${value.unit}`);
    }
    const luxonUnit = unitsToLuxon[value.unit];
    let start = now;
    let end = now;
    switch (value.unit) {
        case "day":
        case "week":
        case "month":
        case "quarter":
        case "year": {
            switch (value.reference) {
                case "this":
                    start = now.startOf(luxonUnit);
                    end = now.endOf(luxonUnit);
                    break;
                case "next":
                    start = now.plus({ [luxonUnit]: 1 }).startOf(luxonUnit);
                    end = now.plus({ [luxonUnit]: interval }).endOf(luxonUnit);
                    break;
                case "last":
                    start = now.minus({ [luxonUnit]: interval }).startOf(luxonUnit);
                    end = now.minus({ [luxonUnit]: 1 }).endOf(luxonUnit);
                    break;
            }
            break;
        }
        case "month_to_date":
        case "year_to_date":
        case "week_to_date": {
            switch (value.reference) {
                case "this": {
                    start = now.plus({ [luxonUnit]: -1, days: 1 });
                    break;
                }
                case "next": {
                    start = now.plus({ days: 1 });
                    end = now.plus({ [luxonUnit]: interval });
                    break;
                }
                case "last": {
                    start = now.plus({ [luxonUnit]: -interval, days: 1 });
                    end = now;
                    break;
                }
            }
            break;
        }
    }
    return Interval.fromDateTimes(start.startOf("day"), end.endOf("day"));
}

/**
 * Returns a new interval, with the given offset applied.
 * The offset is applied in the given unit, for example an offset of -1 in
 * the unit "day" with an interval of 7 days will return an interval with the 7
 * days before the given interval.
 *
 * @param {luxon.Interval} interval
 * @param {RelativeDateValue} value
 * @param {number} periodOffset (-x for previous, +x for next)
 *
 * @returns {luxon.Interval}
 */
function applyOffsetToInterval(interval, value, periodOffset) {
    const { unit } = value;
    let start = interval.start;
    let end = interval.end;

    if (!unitsToLuxon[unit]) {
        throw new Error(`Unknown unit: ${unit}`);
    }

    // We need to ceil the duration because it's not a whole number of periods
    // as the start hour is 00:00:00 and the end hour is 23:59:59, which is not
    // exactly a whole number of days.
    const duration = Math.ceil(interval.length(unitsToLuxon[unit]));
    const offset = periodOffset * duration;

    start = start.plus({ [unitsToLuxon[unit]]: offset });
    end = end.plus({ [unitsToLuxon[unit]]: offset });

    if (!unit.includes("to_date")) {
        start = start.startOf(unitsToLuxon[unit]);
        end = end.endOf(unitsToLuxon[unit]);
    }

    return Interval.fromDateTimes(start, end);
}
