// @ts-check

/** @module @web/components/expression_editor/expression_editor_operator_editor - Filters domain operators to the subset valid for Python expressions */

import { getDomainDisplayedOperators } from "@web/components/domain_selector/domain_selector_operator_editor";

/** @type {string[]} */
const EXPRESSION_VALID_OPERATORS = [
    "<",
    "<=",
    ">",
    ">=",
    "between",
    "in range",
    "in",
    "not in",
    "=",
    "!=",
    "set",
    "not set",
];

/**
 * @param {Object} fieldDef - field definition with type and metadata
 * @returns {string[]} domain operators valid for use in Python expressions
 */
export function getExpressionDisplayedOperators(fieldDef) {
    const operators = getDomainDisplayedOperators(fieldDef);
    return operators.filter((operator) =>
        EXPRESSION_VALID_OPERATORS.includes(operator),
    );
}
