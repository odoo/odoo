/** @ts-check */

import { _t } from "@web/core/l10n/translation";
import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";
import { Domain } from "@web/core/domain";

import { CommandResult } from "@spreadsheet/o_spreadsheet/cancelled_reason";

import { Registry } from "@spreadsheet/o_spreadsheet/o_spreadsheet";

export const globalFieldMatchingRegistry = new Registry();

const { DateTime } = luxon;

export const RELATIVE_PERIODS = {
    last_7_days: _t("Last 7 Days"),
    last_30_days: _t("Last 30 Days"),
    last_90_days: _t("Last 90 Days"),
    last_12_months: _t("Last 12 Months"),
    year_to_date: _t("Year to Date"),
};

/**
 * Compute the display name of a date filter value.
 */
export function dateFilterValueToString(value) {
    switch (value?.type) {
        case "relative":
            return RELATIVE_PERIODS[value.period];
        case "month": {
            const month = DateTime.local().set({
                year: value.year,
                month: value.month,
            });
            return month.toFormat("LLLL yyyy");
        }
        case "quarter": {
            return _t("Q%(quarter)s %(year)s", {
                quarter: value.quarter,
                year: value.year,
            });
        }
        case "year":
            return String(value.year);
        case "range":
            if (value.from || value.to) {
                return _t("%(from)s to %(to)s", {
                    from: value.from || _t("All time"),
                    to: value.to || _t("all time"),
                });
            }
    }
    return _t("All time");
}

/**
 * @typedef {import("@spreadsheet").FieldMatching} FieldMatching
 */

/**
 * Check if the default value is valid for given filter.
 * @returns {boolean}
 */
export function checkFilterDefaultValueIsValid(filter, defaultValue) {
    if (defaultValue === undefined) {
        return true;
    }
    switch (filter.type) {
        case "text":
            return isTextFilterValueValid(defaultValue);
        case "date":
            return isDateFilterDefaultValueValid(defaultValue);
        case "relation":
            return isRelationFilterDefaultValueValid(defaultValue);
        case "boolean":
            return isBooleanFilterValueValid(defaultValue);
    }
    return false;
}

/**
 * Check if the value is valid for given filter.
 * @param {GlobalFilter | CmdGlobalFilter} filter
 * @param {any} value
 * @returns {boolean}
 */
export function checkFilterValueIsValid(filter, value) {
    if (value === undefined) {
        return true;
    }
    switch (filter.type) {
        case "text":
            return isTextFilterValueValid(value);
        case "date":
            return isDateFilterValueValid(value);
        case "relation":
            return isRelationFilterValueValid(value);
        case "boolean":
            return isBooleanFilterValueValid(value);
    }
    return false;
}

/**
 * A text filter value is valid if it is an array of strings. It's the same
 * for the default value.
 * @returns {boolean}
 */
function isTextFilterValueValid(value) {
    return Array.isArray(value) && value.every((text) => typeof text === "string");
}

/**
 * A relation filter default value is valid if it is either "current_user" or an array of numbers.
 * It differs from the relation filter value, which can only be an array of numbers.
 * @returns {boolean}
 */
function isRelationFilterDefaultValueValid(value) {
    return value === "current_user" || isRelationFilterValueValid(value);
}

/**
 * A relation filter value is valid if it is an array of numbers.
 * It differs from the relation filter default value, which can also be "current_user".
 * @returns {boolean}
 */
function isRelationFilterValueValid(value) {
    return Array.isArray(value) && value.every((v) => typeof v === "number");
}

/**
 * A boolean filter value is valid if it is an array of booleans. It's the same
 * for the default value.
 * @returns {boolean}
 */
function isBooleanFilterValueValid(value) {
    return Array.isArray(value) && value.every((v) => typeof v === "boolean");
}

/**
 * A date filter default value is valid if it's a known string representing
 * a relative period (like "last_7_days") or a "current" period (like "this_month", "this_quarter", "this_year"),
 * @returns {boolean}
 */
function isDateFilterDefaultValueValid(value) {
    return (
        Object.keys(RELATIVE_PERIODS).includes(value) ||
        ["this_month", "this_quarter", "this_year"].includes(value)
    );
}

/**
 * A date filter value is valid depending on its type:
 * - "relative": must have a valid period (like "last_7_days")
 * - "month": must have a valid year and month
 * - "quarter": must have a valid year and quarter
 * - "year": must have a valid year
 * - "range": must have valid from and to values (or be empty)
 * @returns {boolean}
 */
function isDateFilterValueValid(value) {
    switch (value.type) {
        case "relative":
            return Object.keys(RELATIVE_PERIODS).includes(value.period);
        case "month":
            return (
                typeof value.year === "number" &&
                typeof value.month === "number" &&
                value.month >= 1 &&
                value.month <= 12
            );
        case "quarter":
            return (
                typeof value.year === "number" &&
                typeof value.quarter === "number" &&
                value.quarter >= 1 &&
                value.quarter <= 4
            );
        case "year":
            return typeof value.year === "number";
        case "range":
            return (
                (value.from === undefined || typeof value.from === "string") &&
                (value.to === undefined || typeof value.to === "string")
            );
    }
    return false;
}

/**
 *
 * @param {Record<string, FieldMatching>} fieldMatchings
 */
export function checkFilterFieldMatching(fieldMatchings) {
    for (const fieldMatch of Object.values(fieldMatchings)) {
        if (fieldMatch.offset && (!fieldMatch.chain || !fieldMatch.type)) {
            return CommandResult.InvalidFieldMatch;
        }
    }

    return CommandResult.Success;
}

/**
 * The from-to date range from a date filter value.
 *
 * @returns {{ from?: DateTime, to?: DateTime }}
 */
export function getDateRange(value, offset = 0) {
    if (!value) {
        return {};
    }
    const now = DateTime.local();
    switch (value.type) {
        case "month":
        case "quarter":
        case "year":
            return getFixedPeriodFromTo(now, offset, value);
        case "relative":
            return getRelativeDateFromTo(now, offset, value.period);
        case "range":
            return {
                from: value.from && DateTime.fromISO(value.from).startOf("day"),
                to: value.to && DateTime.fromISO(value.to).endOf("day"),
            };
    }
}

function getFixedPeriodFromTo(now, offset, value) {
    let granularity = "year";
    const noYear = value.year === undefined;
    if (noYear) {
        return {};
    }
    const setParam = { year: value.year };
    const plusParam = {};
    switch (value.type) {
        case "year":
            plusParam.year = offset;
            break;
        case "month":
            if (value.month !== undefined) {
                granularity = "month";
                setParam.month = value.month;
                plusParam.month = offset;
            }
            break;
        case "quarter":
            if (value.quarter !== undefined) {
                granularity = "quarter";
                setParam.quarter = value.quarter;
                plusParam.quarter = offset;
            }
            break;
    }
    if ("quarter" in setParam) {
        // Luxon does not consider quarter key in setParam (like moment did)
        setParam.month = setParam.quarter * 3 - 2; // start of the quarter
        delete setParam.quarter;
    }
    const date = now.set(setParam).plus(plusParam || {});
    return {
        from: date.startOf(granularity),
        to: date.endOf(granularity),
    };
}

export function getRelativeDateFromTo(now, offset, period) {
    const startOfNextDay = now.plus({ days: 1 }).startOf("day");
    let to = now.endOf("day");
    let from = to;
    switch (period) {
        case "year_to_date": {
            const offsetParam = { years: offset };
            from = now.startOf("year").plus(offsetParam);
            to = now.endOf("day").plus(offsetParam);
            break;
        }
        case "last_7_days": {
            const offsetParam = { days: 7 * offset };
            to = to.plus(offsetParam);
            from = startOfNextDay.minus({ days: 7 }).plus(offsetParam);
            break;
        }
        case "last_30_days": {
            const offsetParam = { days: 30 * offset };
            to = to.plus(offsetParam);
            from = startOfNextDay.minus({ days: 30 }).plus(offsetParam);
            break;
        }
        case "last_90_days": {
            const offsetParam = { days: 90 * offset };
            to = to.plus(offsetParam);
            from = startOfNextDay.minus({ days: 90 }).plus(offsetParam);
            break;
        }
        case "last_12_months": {
            const offsetParam = { months: 12 * offset };
            to = startOfNextDay.minus({ months: 1 }).endOf("month").plus(offsetParam);
            from = startOfNextDay.minus({ months: 12 }).startOf("month").plus(offsetParam);
            break;
        }
        default:
            return undefined;
    }
    return { from, to };
}

export function getDateDomain(from, to, field, fieldType) {
    const serialize = fieldType === "date" ? serializeDate : serializeDateTime;
    if (from && to) {
        return new Domain(["&", [field, ">=", serialize(from)], [field, "<=", serialize(to)]]);
    }
    if (from) {
        return new Domain([[field, ">=", serialize(from)]]);
    }
    if (to) {
        return new Domain([[field, "<=", serialize(to)]]);
    }
    return new Domain();
}
