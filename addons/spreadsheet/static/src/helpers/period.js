/** @odoo-module native */
import * as spreadsheet from "@odoo/o-spreadsheet";
import { EvaluationError } from "@odoo/o-spreadsheet";
import { _t } from "@web/core/translation";
const { functionRegistry } = spreadsheet.registries;
const { toString, toNumber, toJsDate } = spreadsheet.helpers;

const QuarterRegexp = /^q([1-4])\/(\d{4})$/i;
const MonthRegexp = /^0?([1-9]|1[0-2])\/(\d{4})$/i;

/**
 * @typedef {Object} YearDateRange
 * @property {"year"} rangeType
 * @property {number} year
 */

/**
 * @typedef {Object} QuarterDateRange
 * @property {"quarter"} rangeType
 * @property {number} year
 * @property {number} quarter
 */

/**
 * @typedef {Object} MonthDateRange
 * @property {"month"} rangeType
 * @property {number} year
 * @property {number} month
 */

/**
 * @typedef {Object} DayDateRange
 * @property {"day"} rangeType
 * @property {number} year
 * @property {number} month
 * @property {number} day
 */

/**
 * @typedef {YearDateRange | QuarterDateRange | MonthDateRange | DayDateRange} DateRange
 */

/**
 * @param {object | undefined} dateRange
 * @returns {QuarterDateRange | undefined}
 */
function parseAccountingQuarter(dateRange) {
    const found = toString(dateRange?.value).trim().match(QuarterRegexp);
    return found
        ? {
              rangeType: "quarter",
              year: Number(found[2]),
              quarter: Number(found[1]),
          }
        : undefined;
}

/**
 * @param {object | undefined} dateRange
 * @returns {MonthDateRange | undefined}
 */
function parseAccountingMonth(dateRange, locale) {
    if (
        typeof dateRange?.value === "number" &&
        dateRange.format?.includes("m") &&
        !dateRange.format?.includes("d")
    ) {
        const date = toJsDate(dateRange.value, locale);
        return {
            rangeType: "month",
            year: date.getFullYear(),
            month: date.getMonth() + 1,
        };
    }
    const found = toString(dateRange?.value).trim().match(MonthRegexp);
    return found
        ? {
              rangeType: "month",
              year: Number(found[2]),
              month: Number(found[1]),
          }
        : undefined;
}

/**
 * @param {object | undefined} dateRange
 * @returns {YearDateRange | undefined}
 */
function parseAccountingYear(dateRange, locale) {
    const dateNumber = toNumber(dateRange?.value, locale);
    // This allows a bit of flexibility for the user if they were to input a
    // numeric value instead of a year.
    // Users won't need to fetch accounting info for year 3000 before a long time
    // And the numeric value 3000 corresponds to 18th march 1908, so it's not an
    //issue to prevent them from fetching accounting data prior to that date.
    if (dateNumber < 3000) {
        return { rangeType: "year", year: dateNumber };
    }
    return undefined;
}

/**
 * @param {object | undefined} dateRange
 * @returns {DayDateRange}
 */
function parseAccountingDay(dateRange, locale) {
    const dateNumber = toNumber(dateRange?.value, locale);
    return {
        rangeType: "day",
        year: functionRegistry.get("YEAR").compute.bind({ locale })(dateNumber),
        month: functionRegistry.get("MONTH").compute.bind({ locale })(dateNumber),
        day: functionRegistry.get("DAY").compute.bind({ locale })(dateNumber),
    };
}

/**
 * @param {object | undefined} dateRange
 * @returns {DateRange}
 */
export function parsePeriod(dateRange, locale) {
    try {
        return (
            parseAccountingQuarter(dateRange) ||
            parseAccountingMonth(dateRange, locale) ||
            parseAccountingYear(dateRange, locale) ||
            parseAccountingDay(dateRange, locale)
        );
    } catch {
        throw new EvaluationError(
            _t(
                `'%s' is not a valid period. Supported formats are "21/12/2022", "Q1/2022", "12/2022", and "2022".`,
                dateRange?.value,
            ),
        );
    }
}
