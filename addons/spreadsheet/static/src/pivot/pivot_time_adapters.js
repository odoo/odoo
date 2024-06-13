/** @odoo-module */
// @ts-check

import { registries } from "@odoo/o-spreadsheet";
import { deserializeDate } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";

const { pivotTimeAdapterRegistry } = registries;

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

const odooDayAdapter = {
    normalizeServerValue(groupBy, field, readGroupResult) {
        const serverDayValue = getGroupStartingDay(field, groupBy, readGroupResult);
        const date = deserializeDate(serverDayValue);
        return date.toFormat("MM/dd/yyyy");
    },
    increment(normalizedValue, step) {
        const date = DateTime.fromFormat(normalizedValue, "MM/dd/yyyy");
        return date.plus({ days: step }).toFormat("MM/dd/yyyy");
    },
};

const odooWeekAdapter = {
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

const odooMonthAdapter = {
    normalizeServerValue(groupBy, field, readGroupResult) {
        const firstOfTheMonth = getGroupStartingDay(field, groupBy, readGroupResult);
        const date = deserializeDate(firstOfTheMonth);
        return date.toFormat("MM/yyyy");
    },
    increment(normalizedValue, step) {
        return DateTime.fromFormat(normalizedValue, "MM/yyyy")
            .plus({ months: step })
            .toFormat("MM/yyyy");
    },
};

const odooQuarterAdapter = {
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
const odooYearAdapter = {
    normalizeServerValue(groupBy, field, readGroupResult) {
        return Number(readGroupResult[groupBy]);
    },
    increment(normalizedValue, step) {
        return normalizedValue + step;
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
            if (normalizedValue === false) {
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
        getFormat: adapter.getFormat.bind(adapter),
        formatValue(normalizedValue, locale) {
            if (normalizedValue === false) {
                return _t("None");
            }
            return adapter.formatValue(normalizedValue, locale);
        },
        toCellValue(normalizedValue) {
            if (normalizedValue === false) {
                return _t("None");
            }
            return adapter.toCellValue(normalizedValue);
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

extendSpreadsheetAdapter("day", odooDayAdapter);
extendSpreadsheetAdapter("week", odooWeekAdapter);
extendSpreadsheetAdapter("month", odooMonthAdapter);
extendSpreadsheetAdapter("quarter", odooQuarterAdapter);
extendSpreadsheetAdapter("year", odooYearAdapter);

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
