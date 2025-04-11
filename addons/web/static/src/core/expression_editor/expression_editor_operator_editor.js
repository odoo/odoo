import { getDomainDisplayedOperators } from "@web/core/domain_selector/domain_selector_operator_editor";

const EXPRESSION_VALID_OPERATORS = [
    "<",
    "<=",
    ">",
    ">=",
    "today",
    "not_today",
    "between",
    "is_not_between",
    "last",
    "not_last",
    "next",
    "not_next",
    "in",
    "not in",
    "=",
    "!=",
    "set",
    "not_set",
];

export function getExpressionDisplayedOperators(fieldDef) {
    const operators = getDomainDisplayedOperators(fieldDef);
    return operators.filter((operator) => EXPRESSION_VALID_OPERATORS.includes(operator));
}
