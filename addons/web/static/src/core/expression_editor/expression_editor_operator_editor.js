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
    const validOperators = Object.fromEntries(EXPRESSION_VALID_OPERATORS.map((o) => [o, true]));
    if (["char", "html", "text"].includes(fieldDef?.type)) {
        for (const op of ["ilike", "not ilike"]) {
            validOperators[op] = true;
        }
    }
    return operators.filter((operator) => validOperators[operator]);
}
