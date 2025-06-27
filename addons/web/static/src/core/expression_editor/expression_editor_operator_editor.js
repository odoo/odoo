import { getDomainDisplayedOperators } from "@web/core/domain_selector/domain_selector_operator_editor";

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

export function getExpressionDisplayedOperators(fieldDef) {
    const operators = getDomainDisplayedOperators(fieldDef);
    return operators.filter((operator) => EXPRESSION_VALID_OPERATORS.includes(operator));
}
