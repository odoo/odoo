/** @ts-check */

import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";
import { Domain } from "@web/core/domain";

import { CommandResult } from "@spreadsheet/o_spreadsheet/cancelled_reason";
import { RELATIVE_DATE_RANGE_TYPES } from "@spreadsheet/helpers/constants";

import { Registry } from "@spreadsheet/o_spreadsheet/o_spreadsheet";

export const globalFieldMatchingRegistry = new Registry();

/**
 * @typedef {import("@spreadsheet").FieldMatching} FieldMatching
 */

/**
 * Check if the value is valid for given filter.
 * @param {GlobalFilter | CmdGlobalFilter} filter
 * @param {any} value
 * @returns {boolean}
 */
export function checkFilterValueIsValid(filter, value) {
    const { type } = filter;
    if (value !== undefined) {
        switch (type) {
            case "text":
                return Array.isArray(value) && value.every((text) => typeof text === "string");
            case "date": {
                return checkDateFilterValueIsValid(filter, value);
            }
            case "relation":
                if (value === "current_user") {
                    return true;
                }
                if (!Array.isArray(value)) {
                    return false;
                }
                break;
        }
    }
    return true;
}

/**
 * Check if the value is valid for given filter.
 * @param {DateGlobalFilter} filter
 * @param {any} value
 * @returns {boolean}
 */
function checkDateFilterValueIsValid(filter, value) {
    if (!value) {
        return true;
    }
    switch (filter.rangeType) {
        case "fixedPeriod": {
            const period = value.period;
            if (!filter.disabledPeriods || !filter.disabledPeriods.length) {
                return true;
            }
            if (filter.disabledPeriods.includes("month")) {
                return value !== "this_month" && typeof period !== "number";
            }
            if (filter.disabledPeriods.includes("quarter")) {
                return value !== "this_quarter" && typeof period !== "number";
            }
            return true;
        }
        case "relative": {
            const expectedValues = RELATIVE_DATE_RANGE_TYPES.map((val) => val.type);
            expectedValues.push("this_month", "this_quarter", "this_year");
            return expectedValues.includes(value);
        }
        case "from_to":
            return typeof value === "object";
    }
    return true;
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

export function getRelativeDateFromTo(now, offset, rangeType) {
    const startOfNextDay = now.plus({ days: 1 }).startOf("day");
    let to = now.endOf("day");
    let from = to;
    switch (rangeType) {
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
