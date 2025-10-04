/** @odoo-module **/

import { getDomainDisplayedOperators } from "@web/core/domain_selector/domain_selector_operator_editor";

const EXPRESSION_VALID_OPERATORS = [
    "<",
    "<=",
    ">",
    ">=",
    "between",
    "in",
    "not in",
    "=",
    "!=",
    "set",
    "not_set",
    "is",
    "is_not",
];

export function getExpressionDisplayedOperators(fieldDef) {
    const operators = getDomainDisplayedOperators(fieldDef);
    return operators.filter((operator) => EXPRESSION_VALID_OPERATORS.includes(operator));
}
