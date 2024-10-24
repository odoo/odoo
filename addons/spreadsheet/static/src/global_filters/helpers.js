/** @ts-check */

import { CommandResult } from "@spreadsheet/o_spreadsheet/cancelled_reason";
import { monthsOptions } from "@spreadsheet/assets_backend/constants";
import { QUARTER_OPTIONS } from "@web/search/utils/dates";
import {
    RELATIVE_DATE_RANGE_REFERENCES,
    RELATIVE_DATE_RANGE_UNITS,
} from "@spreadsheet/helpers/constants";

/**
 * @typedef {import("@spreadsheet").FieldMatching} FieldMatching
 */

const monthsOptionsIds = monthsOptions.map((option) => option.id);
const quarterOptionsIds = Object.values(QUARTER_OPTIONS).map((option) => option.id);

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
                if (typeof value !== "string") {
                    return false;
                }
                break;
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

const EXPECTED_REFERENCES = RELATIVE_DATE_RANGE_REFERENCES.map((ref) => ref.type);
const EXPECTED_UNITS = RELATIVE_DATE_RANGE_UNITS.map((unit) => unit.type);

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
                return value !== "this_month" && !monthsOptionsIds.includes(period);
            }
            if (filter.disabledPeriods.includes("quarter")) {
                return value !== "this_quarter" && !quarterOptionsIds.includes(period);
            }
            return true;
        }
        case "relative": {
            if (
                EXPECTED_REFERENCES.includes(value.reference) &&
                EXPECTED_UNITS.includes(value.unit)
            ) {
                return CommandResult.Success;
            }
            return CommandResult.InvalidValueTypeCombination;
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
