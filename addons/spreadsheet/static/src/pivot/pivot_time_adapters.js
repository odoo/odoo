/** @odoo-module */
// @ts-check

import { registries, helpers, constants } from "@odoo/o-spreadsheet";
import { deserializeDate } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";

const { pivotTimeAdapterRegistry } = registries;
const { formatValue, toNumber, toJsDate, toString } = helpers;
const { DEFAULT_LOCALE } = constants;

const { DateTime } = luxon;

/**
 * The Time Adapter: Managing Time Periods for Pivot Functions
 * This is the extension of the one of o-spreadsheet to handle the normalization of
 * data received from the server. It also manage the increment of a date, used in
 * the autofill.
 *
 * Normalization Process:
 * When dealing with the server, the time adapter ensures that the received periods are
 * normalized before being stored in the datasource.
 * For example, if the server returns a day period as "2023-12-25 22:00:00," the time adapter
 * transforms it into the normalized form "12/25/2023" for storage in the datasource.
 *
 * Example:
 * To illustrate the normalization process, let's consider the day period:
 *
 * 1. The server returns a day period as "2023-12-25 22:00:00"
 * 2. The time adapter normalizes this period to "12/25/2023" for storage in the datasource.
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
 * e.g. in `PIVOT.VALUE(1, "amount", "create_date", "1/5/2023")`, the day is interpreted as being the 5th of January 2023,
 * even if the spreadsheet locale is set to French and such a date is usually interpreted as the 1st of May 2023.
 * The reason is PIVOT functions are currently generated without being aware of the spreadsheet locale.
 */

const odooNumberDateAdapter = {
    normalizeServerValue(groupBy, field, readGroupResult) {
        return Number(readGroupResult[groupBy]);
    },
    increment(normalizedValue, step) {
        return normalizedValue + step;
    },
};

const odooDayAdapter = {
    normalizeServerValue(groupBy, field, readGroupResult) {
        const serverDayValue = getGroupStartingDay(field, groupBy, readGroupResult);
        return toNumber(serverDayValue, DEFAULT_LOCALE);
    },
    increment(normalizedValue, step) {
        return normalizedValue + step;
    },
};

/**
 * Normalized value: "2/2023" for week 2 of 2023
 */
const odooWeekAdapter = {
    normalizeFunctionValue(value) {
        const [week, year] = toString(value).split("/");
        return `${Number(week)}/${Number(year)}`;
    },
    toValueAndFormat(normalizedValue, locale) {
        const [week, year] = normalizedValue.split("/");
        return {
            value: _t("W%(week)s %(year)s", { week, year }),
        };
    },
    toFunctionValue(normalizedValue) {
        return `"${normalizedValue}"`;
    },
    normalizeServerValue(groupBy, field, readGroupResult) {
        const weekValue = readGroupResult[groupBy];
        const { week, year } = parseServerWeekHeader(weekValue);
        return `${week}/${year}`;
    },
    increment(normalizedValue, step) {
        const [week, year] = normalizedValue.split("/");
        const weekNumber = Number(week);
        const yearNumber = Number(year);
        const date = DateTime.fromObject({ weekNumber, weekYear: yearNumber });
        const nextWeek = date.plus({ weeks: step });
        return `${nextWeek.weekNumber}/${nextWeek.weekYear}`;
    },
};

/**
 * normalized month value is a string formatted as "MM/yyyy" (luxon format)
 * e.g. "01/2020" for January 2020
 */
const odooMonthAdapter = {
    normalizeFunctionValue(value) {
        const date = toNumber(value, DEFAULT_LOCALE);
        return formatValue(date, { locale: DEFAULT_LOCALE, format: "mm/yyyy" });
    },
    toValueAndFormat(normalizedValue) {
        return {
            value: toNumber(normalizedValue, DEFAULT_LOCALE),
            format: "mmmm yyyy",
        };
    },
    toFunctionValue(normalizedValue) {
        return `"${normalizedValue}"`;
    },
    normalizeServerValue(groupBy, field, readGroupResult) {
        const firstOfTheMonth = getGroupStartingDay(field, groupBy, readGroupResult);
        const date = deserializeDate(firstOfTheMonth).reconfigure({ numberingSystem: "latn" });
        return date.toFormat("MM/yyyy");
    },
    increment(normalizedValue, step) {
        return DateTime.fromFormat(normalizedValue, "MM/yyyy", { numberingSystem: "latn" })
            .plus({ months: step })
            .toFormat("MM/yyyy");
    },
};

const NORMALIZED_QUARTER_REGEXP = /^[1-4]\/\d{4}$/;

/**
 * normalized quarter value is "quarter/year"
 * e.g. "1/2020" for Q1 2020
 */
const odooQuarterAdapter = {
    normalizeFunctionValue(value) {
        // spreadsheet normally interprets "4/2020" as the 1st April
        // but it should be understood as a quarter here.
        if (typeof value === "string" && NORMALIZED_QUARTER_REGEXP.test(value)) {
            return value;
        }
        // Any other value is interpreted as any date-like spreadsheet value
        const dateTime = toJsDate(value, DEFAULT_LOCALE);
        return `${dateTime.getQuarter()}/${dateTime.getFullYear()}`;
    },
    toValueAndFormat(normalizedValue) {
        const [quarter, year] = normalizedValue.split("/");
        return {
            value: _t("Q%(quarter)s %(year)s", { quarter, year }),
        };
    },
    toFunctionValue(normalizedValue) {
        return `"${normalizedValue}"`;
    },
    normalizeServerValue(groupBy, field, readGroupResult) {
        const firstOfTheQuarter = getGroupStartingDay(field, groupBy, readGroupResult);
        const date = deserializeDate(firstOfTheQuarter);
        return `${date.quarter}/${date.year}`;
    },
    increment(normalizedValue, step) {
        const [quarter, year] = normalizedValue.split("/");
        const date = DateTime.fromObject({ year: Number(year), month: Number(quarter) * 3 });
        const nextQuarter = date.plus({ quarters: step });
        return `${nextQuarter.quarter}/${nextQuarter.year}`;
    },
};

const odooDayOfWeekAdapter = {
    normalizeServerValue(groupBy, field, readGroupResult) {
        /**
         * 0: First day of the week in the locale.
         */
        return Number(readGroupResult[groupBy]) + 1;
    },
    increment(normalizedValue, step) {
        return (normalizedValue + step) % 7;
    },
};

const odooHourNumberAdapter = {
    normalizeServerValue(groupBy, field, readGroupResult) {
        return Number(readGroupResult[groupBy]);
    },
    increment(normalizedValue, step) {
        return (normalizedValue + step) % 24;
    },
};
const odooMinuteNumberAdapter = {
    normalizeServerValue(groupBy, field, readGroupResult) {
        return Number(readGroupResult[groupBy]);
    },
    increment(normalizedValue, step) {
        return (normalizedValue + step) % 60;
    },
};
const odooSecondNumberAdapter = {
    normalizeServerValue(groupBy, field, readGroupResult) {
        return Number(readGroupResult[groupBy]);
    },
    increment(normalizedValue, step) {
        return (normalizedValue + step) % 60;
    },
};

/**
 * Decorate adapter functions to handle the empty value "false"
 */
function falseHandlerDecorator(adapter) {
    return {
        normalizeServerValue(groupBy, field, readGroupResult) {
            if (readGroupResult[groupBy] === false) {
                return false;
            }
            return adapter.normalizeServerValue(groupBy, field, readGroupResult);
        },
        increment(normalizedValue, step) {
            if (
                normalizedValue === false ||
                (typeof normalizedValue === "string" && normalizedValue.toLowerCase() === "false")
            ) {
                return false;
            }
            return adapter.increment(normalizedValue, step);
        },
        normalizeFunctionValue(value) {
            if (value.toLowerCase() === "false") {
                return false;
            }
            return adapter.normalizeFunctionValue(value);
        },
        toValueAndFormat(normalizedValue, locale) {
            if (
                normalizedValue === false ||
                (typeof normalizedValue === "string" && normalizedValue.toLowerCase() === "false")
            ) {
                return { value: _t("None") };
            }
            return adapter.toValueAndFormat(normalizedValue, locale);
        },
        toFunctionValue(value) {
            if (value === false) {
                return "FALSE";
            }
            return adapter.toFunctionValue(value);
        },
    };
}

function extendSpreadsheetAdapter(granularity, adapter) {
    const originalAdapter = pivotTimeAdapterRegistry.get(granularity);
    pivotTimeAdapterRegistry.add(
        granularity,
        falseHandlerDecorator({
            ...originalAdapter,
            ...adapter,
        })
    );
}

pivotTimeAdapterRegistry.add("week", falseHandlerDecorator(odooWeekAdapter));
pivotTimeAdapterRegistry.add("month", falseHandlerDecorator(odooMonthAdapter));
pivotTimeAdapterRegistry.add("quarter", falseHandlerDecorator(odooQuarterAdapter));

extendSpreadsheetAdapter("day", odooDayAdapter);
extendSpreadsheetAdapter("year", odooNumberDateAdapter);
extendSpreadsheetAdapter("day_of_month", odooNumberDateAdapter);
extendSpreadsheetAdapter("day", odooDayAdapter);
extendSpreadsheetAdapter("iso_week_number", odooNumberDateAdapter);
extendSpreadsheetAdapter("month_number", odooNumberDateAdapter);
extendSpreadsheetAdapter("quarter_number", odooNumberDateAdapter);
extendSpreadsheetAdapter("day_of_week", odooDayOfWeekAdapter);
extendSpreadsheetAdapter("hour_number", odooHourNumberAdapter);
extendSpreadsheetAdapter("minute_number", odooMinuteNumberAdapter);
extendSpreadsheetAdapter("second_number", odooSecondNumberAdapter);

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
    const userTz = user.tz || luxon.Settings.defaultZone.name;
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
