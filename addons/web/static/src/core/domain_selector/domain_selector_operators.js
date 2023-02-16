/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";

export const OPERATOR_DESCRIPTIONS = [
    { key: "is", label: _lt("is"), symbol: "=" },
    { key: "is_not", label: _lt("is not"), symbol: "!=" },
    { key: "equal", label: "=", symbol: "=" },
    { key: "not_equal", label: "!=", symbol: "!=" },
    { key: "greater_than", label: ">", symbol: ">" },
    { key: "greater_equal", label: ">=", symbol: ">=" },
    { key: "less_than", label: "<", symbol: "<" },
    { key: "less_equal", label: "<=", symbol: "<=" },
    { key: "ilike", label: _lt("contains"), symbol: "ilike" },
    { key: "not_ilike", label: _lt("does not contain"), symbol: "not ilike" },
    { key: "like", label: _lt("like"), symbol: "like" },
    { key: "not_like", label: _lt("not like"), symbol: "not like" },
    { key: "equal_like", label: _lt("=like"), symbol: "=like" },
    { key: "equal_ilike", label: _lt("=ilike"), symbol: "=ilike" },
    { key: "child_of", label: _lt("child of"), symbol: "child_of" },
    { key: "parent_of", label: _lt("parent of"), symbol: "parent_of" },
    { key: "in", label: _lt("in"), symbol: "in", valueMode: "multiple" },
    { key: "not_in", label: _lt("not in"), symbol: "not in", valueMode: "multiple" },
    { key: "set", label: _lt("is set"), symbol: "!=", valueMode: "none" },
    { key: "not_set", label: _lt("is not set"), symbol: "=", valueMode: "none" },
];

export function findOperator(key) {
    return OPERATOR_DESCRIPTIONS.find((op) => op.key === key);
}

export function selectOperators(keys) {
    const operators = Object.fromEntries(OPERATOR_DESCRIPTIONS.map((op) => [op.key, op]));
    return keys.map((key) => operators[key]);
}

export function parseOperator(symbol) {
    return OPERATOR_DESCRIPTIONS.filter(
        (op) => !["is", "is_not", "set", "not_set"].includes(op.key)
    ).find((op) => op.symbol === symbol);
}
