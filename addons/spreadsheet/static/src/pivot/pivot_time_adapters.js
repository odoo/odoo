/** @odoo-module */

import { helpers, constants } from "@odoo/o-spreadsheet";
import { deserializeDate } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";
import { session } from "@web/session";
const { toNumber, formatValue } = helpers;
const { DEFAULT_LOCALE } = constants;

const { DateTime } = luxon;

/**
 * @param {"day" | "week" | "month" | "quarter" | "month"} groupAggregate
 * @returns {PivotTimeAdapter}
 */
export function pivotTimeAdapter(groupAggregate) {
    return TIME_ADAPTERS[groupAggregate];
}

/**
 * The Time Adapter: Managing Time Periods for Pivot Functions
 *
 * Overview:
 * A time adapter is responsible for managing time periods associated with pivot functions.
 * Each type of period (day, week, month, quarter, etc.) has its own dedicated adapter.
 * The adapter's primary role is to normalize period values between spreadsheet functions,
 * the server, and the datasource.
 * By normalizing the period value, it can be stored consistently in the datasource.
 *
 * Normalization Process:
 * When dealing with the server, the time adapter ensures that the received periods are
 * normalized before being stored in the datasource.
 * For example, if the server returns a day period as "2023-12-25 22:00:00," the time adapter
 * transforms it into the normalized form "12/25/2023" for storage in the datasource.
 *
 * Similarly, when working with functions in the spreadsheet, the time adapter normalizes
 * the provided period to facilitate accurate lookup of values in the datasource.
 * For instance, if the spreadsheet function represents a day period as a number generated
 * by the DATE function (DATE(2023, 12, 25)), the time adapter will normalize it accordingly.
 *
 * Example:
 * To illustrate the normalization process, let's consider the day period:
 *
 * 1. The server returns a day period as "2023-12-25 22:00:00"
 * 2. The time adapter normalizes this period to "12/25/2023" for storage in the datasource.
 * 3. Meanwhile, the spreadsheet function represents the day period as a number obtained from
 *    the DATE function (DATE(2023, 12, 25)).
 *
 * By applying the appropriate normalization, the time adapter ensures that the periods from
 * different sources are consistently represented and can be effectively utilized for lookup
 * operations in the datasource.
 *
 * Implementation notes/tips:
 * - Do not mix luxon and spreadsheet dates in the same function. Timezones are not handled the same way.
 *   Spreadsheet dates are naive dates (no timezone) while luxon dates are timezone aware dates.
 *   **Don't do this**: DateTime.fromJSDate(toJsDate(value)) (it will be interpreted as UTC)
 *
 * - spreadsheet formats and luxon formats are not the same but can be equivalent.
 *   For example: "MM/dd/yyyy" (luxon format) is equivalent to "mm/dd/yyyy" (spreadsheet format)
 *
 * Limitations:
 * If a period value is provided as a **string** to a function, it will interpreted as being in the default locale.
 * e.g. in `ODOO.PIVOT(1, "amount", "create_date", "1/5/2023")`, the day is interpreted as being the 5th of January 2023,
 * even if the spreadsheet locale is set to French and such a date is usually interpreted as the 1st of May 2023.
 * The reason is ODOO.PIVOT functions are currently generated without being aware of the spreadsheet locale.
 *
 * @typedef {Object} PivotTimeAdapter
 * @property {(groupBy: string, field: string, readGroupResult: object) => string} normalizeServerValue
 * @property {(value: string) => string} normalizeFunctionValue
 * @property {(normalizedValue: string, step: number) => string} increment
 * @property {(normalizedValue: string, locale: Object) => string} format
 */

/**
 * @type {PivotTimeAdapter}
 * Normalized value: "12/25/2023"
 *
 * Note: Those two format are equivalent:
 * - "MM/dd/yyyy" (luxon format)
 * - "mm/dd/yyyy" (spreadsheet format)
 **/
const dayAdapter = {
    normalizeServerValue(groupBy, field, readGroupResult) {
        const serverDayValue = getGroupStartingDay(field, groupBy, readGroupResult);
        const date = deserializeDate(serverDayValue);
        return date.toFormat("MM/dd/yyyy");
    },
    normalizeFunctionValue(value) {
        const date = toNumber(value, DEFAULT_LOCALE);
        return formatValue(date, { locale: DEFAULT_LOCALE, format: "mm/dd/yyyy" });
    },
    increment(normalizedValue, step) {
        const date = DateTime.fromFormat(normalizedValue, "MM/dd/yyyy");
        return date.plus({ days: step }).toFormat("MM/dd/yyyy");
    },
    format(normalizedValue, locale) {
        const value = toNumber(normalizedValue, DEFAULT_LOCALE);
        return formatValue(value, { locale, format: locale.dateFormat });
    },
};

/**
 * @type {PivotTimeAdapter}
 * Normalized value: "2/2023" for week 2 of 2023
 */
const weekAdapter = {
    normalizeServerValue(groupBy, field, readGroupResult) {
        const weekValue = readGroupResult[groupBy];
        const { week, year } = parseServerWeekHeader(weekValue);
        return `${week}/${year}`;
    },
    normalizeFunctionValue(value) {
        const [week, year] = value.split("/");
        return `${Number(week)}/${Number(year)}`;
    },
    increment(normalizedValue, step) {
        const [week, year] = normalizedValue.split("/");
        const weekNumber = Number(week);
        const yearNumber = Number(year);
        const date = DateTime.fromObject({ weekNumber, weekYear: yearNumber });
        const nextWeek = date.plus({ weeks: step });
        return `${nextWeek.weekNumber}/${nextWeek.weekYear}`;
    },
    format(normalizedValue, locale) {
        const [week, year] = normalizedValue.split("/");
        return sprintf(_t("W%(week)s %(year)s"), { week, year });
    },
};

/**
 * @type {PivotTimeAdapter}
 * normalized month value is a string formatted as "MM/yyyy" (luxon format)
 * e.g. "01/2020" for January 2020
 */
const monthAdapter = {
    normalizeServerValue(groupBy, field, readGroupResult) {
        const firstOfTheMonth = getGroupStartingDay(field, groupBy, readGroupResult);
        const date = deserializeDate(firstOfTheMonth);
        return date.toFormat("MM/yyyy");
    },
    normalizeFunctionValue(value) {
        const date = toNumber(value, DEFAULT_LOCALE);
        return formatValue(date, { DEFAULT_LOCALE, format: "mm/yyyy" });
    },
    increment(normalizedValue, step) {
        return DateTime.fromFormat(normalizedValue, "MM/yyyy")
            .plus({ months: step })
            .toFormat("MM/yyyy");
    },
    format(normalizedValue, locale) {
        const value = toNumber(normalizedValue, DEFAULT_LOCALE);
        return formatValue(value, { locale, format: "mmmm yyyy" });
    },
};

/**
 * @type {PivotTimeAdapter}
 * normalized quarter value is "quarter/year"
 * e.g. "1/2020" for Q1 2020
 */
const quarterAdapter = {
    normalizeServerValue(groupBy, field, readGroupResult) {
        const firstOfTheQuarter = getGroupStartingDay(field, groupBy, readGroupResult);
        const date = deserializeDate(firstOfTheQuarter);
        return `${date.quarter}/${date.year}`;
    },
    normalizeFunctionValue(value) {
        const [quarter, year] = value.split("/");
        return `${quarter}/${year}`;
    },
    increment(normalizedValue, step) {
        const [quarter, year] = normalizedValue.split("/");
        const date = DateTime.fromObject({ year: Number(year), month: Number(quarter) * 3 });
        const nextQuarter = date.plus({ quarters: step });
        return `${nextQuarter.quarter}/${nextQuarter.year}`;
    },
    format(normalizedValue, locale) {
        const [quarter, year] = normalizedValue.split("/");
        return sprintf(_t("Q%(quarter)s %(year)s"), { quarter, year });
    },
};
/**
 * @type {PivotTimeAdapter}
 */
const yearAdapter = {
    normalizeServerValue(groupBy, field, readGroupResult) {
        return Number(readGroupResult[groupBy]);
    },
    normalizeFunctionValue(value) {
        return toNumber(value, DEFAULT_LOCALE);
    },
    increment(normalizedValue, step) {
        return normalizedValue + step;
    },
    format(normalizedValue, locale) {
        return formatValue(normalizedValue, { locale, format: "0" });
    },
};

/**
 * Decorate adapter functions to handle the empty value "false"
 * @param {PivotTimeAdapter} adapter
 */
function falseHandlerDecorator(adapter) {
    return {
        normalizeServerValue(groupBy, field, readGroupResult) {
            if (readGroupResult[groupBy] === false) {
                return false;
            }
            return adapter.normalizeServerValue(groupBy, field, readGroupResult);
        },
        normalizeFunctionValue(value) {
            if (value === false || value === "false") {
                return false;
            }
            return adapter.normalizeFunctionValue(value);
        },
        increment(normalizedValue, step) {
            if (normalizedValue === false) {
                return false;
            }
            return adapter.increment(normalizedValue, step);
        },
        format(normalizedValue, locale) {
            if (normalizedValue === false) {
                return _t("None");
            }
            return adapter.format(normalizedValue, locale);
        },
    };
}

const TIME_ADAPTERS = {
    day: falseHandlerDecorator(dayAdapter),
    week: falseHandlerDecorator(weekAdapter),
    month: falseHandlerDecorator(monthAdapter),
    quarter: falseHandlerDecorator(quarterAdapter),
    year: falseHandlerDecorator(yearAdapter),
};

/**
 * When grouping by a time field, return
 * the group starting day (local to the timezone)
 * @param {object} field
 * @param {string} groupBy
 * @param {object} readGroup
 * @returns {string | undefined}
 */
function getGroupStartingDay(field, groupBy, readGroup) {
    if (!readGroup["__range"] || !readGroup["__range"][groupBy]) {
        return undefined;
    }
    const sqlValue = readGroup["__range"][groupBy].from;
    if (field.type === "date") {
        return sqlValue;
    }
    const userTz = session.user_context.tz || luxon.Settings.defaultZoneName;
    return DateTime.fromSQL(sqlValue, { zone: "utc" }).setZone(userTz).toISODate();
}

/**
 * Parses a pivot week header value.
 * @param {string} value
 * @example
 * parseServerWeekHeader("W1 2020") // { week: 1, year: 2020 }
 */
function parseServerWeekHeader(value) {
    // Value is always formatted as "W1 2020", no matter the language.
    // Parsing this formatted value is the only way to ensure we get the same
    // locale aware week number as the one used in the server.
    const [week, year] = value.split(" ");
    return { week: Number(week.slice(1)), year: Number(year) };
}
