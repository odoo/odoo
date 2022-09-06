/** @odoo-module */

import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";
import { Domain } from "@web/core/domain";

import CommandResult from "@spreadsheet/o_spreadsheet/cancelled_reason";
import { FILTER_DATE_OPTION, monthsOptions } from "@spreadsheet/assets_backend/constants";
import { getPeriodOptions } from "@web/search/utils/dates";
import { RELATIVE_DATE_RANGE_TYPES } from "@spreadsheet/helpers/constants";

const { DateTime } = luxon;

export function checkFiltersTypeValueCombination(type, value) {
    if (value !== undefined) {
        switch (type) {
            case "text":
                if (typeof value !== "string") {
                    return CommandResult.InvalidValueTypeCombination;
                }
                break;
            case "date":
                if (typeof value === "string") {
                    const expectedValues = RELATIVE_DATE_RANGE_TYPES.map((val) => val.type);
                    if (!expectedValues.includes(value)) {
                        return CommandResult.InvalidValueTypeCombination;
                    }
                } else if (typeof value !== "object" || Array.isArray(value)) {
                    // not a date
                    return CommandResult.InvalidValueTypeCombination;
                }
                break;
            case "relation":
                if (!Array.isArray(value)) {
                    return CommandResult.InvalidValueTypeCombination;
                }
                break;
        }
    }
    return CommandResult.Success;
}

/**
 * Get a date domain relative to the current date.
 * The domain will span the amount of time specified in rangeType and end the day before the current day.
 *
 *
 * @param {Object} now current time, as luxon time
 * @param {number} offset offset to add to the date
 * @param {"last_month" | "last_week" | "last_year" | "last_three_years"} rangeType
 * @param {string} fieldName
 * @param {"date" | "datetime"} fieldType
 *
 * @returns {Domain|undefined}
 */
export function getRelativeDateDomain(now, offset, rangeType, fieldName, fieldType) {
    let endDate = now.minus({ day: 1 }).endOf("day");
    let startDate = endDate;
    switch (rangeType) {
        case "last_week": {
            const offsetParam = { day: 7 * offset };
            endDate = endDate.plus(offsetParam);
            startDate = now.minus({ day: 7 }).plus(offsetParam);
            break;
        }
        case "last_month": {
            const offsetParam = { day: 30 * offset };
            endDate = endDate.plus(offsetParam);
            startDate = now.minus({ day: 30 }).plus(offsetParam);
            break;
        }
        case "last_year": {
            const offsetParam = { day: 365 * offset };
            endDate = endDate.plus(offsetParam);
            startDate = now.minus({ day: 365 }).plus(offsetParam);
            break;
        }
        case "last_three_years": {
            const offsetParam = { day: 3 * 365 * offset };
            endDate = endDate.plus(offsetParam);
            startDate = now.minus({ day: 3 * 365 }).plus(offsetParam);
            break;
        }
        default:
            return undefined;
    }
    startDate = startDate.startOf("day");

    let leftBound, rightBound;
    if (fieldType === "date") {
        leftBound = serializeDate(startDate);
        rightBound = serializeDate(endDate);
    } else {
        leftBound = serializeDateTime(startDate);
        rightBound = serializeDateTime(endDate);
    }

    return new Domain(["&", [fieldName, ">=", leftBound], [fieldName, "<=", rightBound]]);
}

/*
 * Return a list of time options to choose from according to the requested
 * type. Each option contains its (translated) description.
 * @see getPeriodOptions
 * @param {string} type "month" | "quarter" | "year"
 * @returns {Array<Object>}
 */
export function dateOptions(type) {
    if (type === "month") {
        return monthsOptions;
    } else {
        return getPeriodOptions(DateTime.local()).filter(({ id }) =>
            FILTER_DATE_OPTION[type].includes(id)
        );
    }
}
