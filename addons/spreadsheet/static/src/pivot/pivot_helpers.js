/** @odoo-module **/
// @ts-check

import { _t } from "@web/core/l10n/translation";
import { EvaluationError, helpers } from "@odoo/o-spreadsheet";
import { sprintf } from "@web/core/utils/strings";

const { isDateField } = helpers;

/** @typedef {import("@odoo/o-spreadsheet").Token} Token */

export const pivotFormulaRegex = /^=.*PIVOT/;

//--------------------------------------------------------------------------
// Public
//--------------------------------------------------------------------------

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
