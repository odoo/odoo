/** @odoo-module **/
// @ts-check

import { _t } from "@web/core/l10n/translation";
import { getOdooFunctions } from "../helpers/odoo_functions_helpers";
import { sprintf } from "@web/core/utils/strings";
import { EvaluationError } from "@odoo/o-spreadsheet";

/** @typedef {import("@odoo/o-spreadsheet").Token} Token */

export const pivotFormulaRegex = /^=.*PIVOT/;

export const AGGREGATOR_NAMES = {
    count: _t("Count"),
    count_distinct: _t("Count Distinct"),
    bool_and: _t("Boolean And"),
    bool_or: _t("Boolean Or"),
    max: _t("Maximum"),
    min: _t("Minimum"),
    avg: _t("Average"),
    sum: _t("Sum"),
};

const NUMBER_AGGREGATORS = ["max", "min", "avg", "sum", "count_distinct", "count"];
const DATE_AGGREGATORS = ["max", "min", "count_distinct", "count"];

const AGGREGATORS_BY_FIELD_TYPE = {
    integer: NUMBER_AGGREGATORS,
    float: NUMBER_AGGREGATORS,
    monetary: NUMBER_AGGREGATORS,
    date: DATE_AGGREGATORS,
    datetime: DATE_AGGREGATORS,
    boolean: ["count_distinct", "count", "bool_and", "bool_or"],
    char: ["count_distinct", "count"],
    many2one: ["count_distinct", "count"],
};

export const AGGREGATORS = {};

for (const type in AGGREGATORS_BY_FIELD_TYPE) {
    AGGREGATORS[type] = {};
    for (const aggregator of AGGREGATORS_BY_FIELD_TYPE[type]) {
        AGGREGATORS[type][aggregator] = AGGREGATOR_NAMES[aggregator];
    }
}

const DATE_FIELDS = ["date", "datetime"];

//--------------------------------------------------------------------------
// Public
//--------------------------------------------------------------------------

/**
 * Parse a spreadsheet formula and detect the number of PIVOT functions that are
 * present in the given formula.
 *
 * @param {Token[]} tokens
 *
 * @returns {number}
 */
export function getNumberOfPivotFormulas(tokens) {
    return getOdooFunctions(tokens, ["PIVOT.VALUE", "PIVOT.HEADER", "ODOO.PIVOT.POSITION", "PIVOT"])
        .length;
}

/**
 * Get the first Pivot function description of the given formula.
 *
 * @param {Token[]} tokens
 *
 * @returns {import("../helpers/odoo_functions_helpers").OdooFunctionDescription|undefined}
 */
export function getFirstPivotFunction(tokens) {
    return getOdooFunctions(tokens, [
        "PIVOT.VALUE",
        "PIVOT.HEADER",
        "ODOO.PIVOT.POSITION",
        "PIVOT",
    ])[0];
}

/**
 * Build a pivot formula expression
 *
 * @param {string} formula formula to be used (PIVOT or PIVOT.HEADER)
 * @param {*} args arguments of the formula
 *
 * @returns {string}
 */
export function makePivotFormula(formula, args) {
    return `=${formula}(${args
        .map((arg) => {
            const stringIsNumber =
                typeof arg == "string" && !isNaN(Number(arg)) && Number(arg).toString() === arg;
            const convertToNumber = typeof arg == "number" || stringIsNumber;
            return convertToNumber ? `${arg}` : `"${arg.toString().replace(/"/g, '\\"')}"`;
        })
        .join(",")})`;
}

export const PERIODS = {
    day: _t("Day"),
    week: _t("Week"),
    month: _t("Month"),
    quarter: _t("Quarter"),
    year: _t("Year"),
};

/**
 * @typedef {import("@spreadsheet").Field} Field
 */

/**
 * Parses the positional char (#), the field and operator string of pivot group.
 * e.g. "create_date:month"
 * @param {Record<string, Field | undefined>} allFields
 * @param {string} groupFieldString
 * @returns {{field: Field, granularity: string, isPositional: boolean, dimensionWithGranularity: string}}
 */
export function parseGroupField(allFields, groupFieldString) {
    let fieldName = groupFieldString;
    let granularity = undefined;
    const index = groupFieldString.indexOf(":");
    if (index !== -1) {
        fieldName = groupFieldString.slice(0, index);
        granularity = groupFieldString.slice(index + 1);
    }
    const isPositional = fieldName.startsWith("#");
    fieldName = isPositional ? fieldName.substring(1) : fieldName;
    const field = allFields[fieldName];
    if (field === undefined) {
        throw new EvaluationError(sprintf(_t("Field %s does not exist"), fieldName));
    }
    const dimensionWithGranularity = granularity ? `${fieldName}:${granularity}` : fieldName;
    if (isDateField(field)) {
        granularity = granularity || "month";
    }
    return {
        isPositional,
        field,
        granularity,
        dimensionWithGranularity,
    };
}

/**
 * Parse a dimension string into a pivot dimension definition.
 * e.g "create_date:month" => { name: "create_date", granularity: "month" }
 *
 * @param {string} dimension
 * @returns {import("@spreadsheet").PivotDimensionDefinition}
 */
export function parseDimension(dimension) {
    const [name, granularity] = dimension.split(":");
    if (granularity) {
        return { name, granularity };
    }
    return { name };
}

/**
 * @param {Field} field
 * @returns {boolean}
 */
export function isDateField(field) {
    return DATE_FIELDS.includes(field.type);
}
