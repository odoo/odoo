/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { formatValue, TERM_OPERATORS_NEGATION, toValue } from "@web/core/domain_tree";
import { parseExpr } from "@web/core/py_js/py";
import { Select } from "./domain_selector_components";

const OPERATOR_DESCRIPTIONS = {
    // valid operators (see TERM_OPERATORS in expression.py)
    "=": "=",
    "!=": "!=",
    "<=": "<=",
    "<": "<",
    ">": ">",
    ">=": ">=",
    "=?": "=?",
    "=like": _t("=like"),
    "=ilike": _t("=ilike"),
    like: _t("like"),
    "not like": _t("not like"),
    ilike: _t("contains"),
    "not ilike": _t("does not contain"),
    in: _t("is in"),
    "not in": _t("is not in"),
    child_of: _t("child of"),
    parent_of: _t("parent of"),

    // virtual operators (replace = and != in some cases)
    is: _t("is"),
    is_not: _t("is not"),
    set: _t("is set"),
    not_set: _t("is not set"),

    // virtual operator (equivalent to a couple (>=,<=))
    between: _t("is between"),
};

function getDisplayedOperators(fieldDef) {
    const { type, is_property } = fieldDef;

    if (is_property) {
        switch (type) {
            case "many2many":
            case "tags":
                return ["in", "not in", "set", "not_set"];
            case "many2one":
            case "selection":
                return ["=", "!=", "set", "not_set"];
        }
    }

    switch (type) {
        case "boolean":
            return ["is", "is_not"];
        case "selection":
            return ["=", "!=", "in", "not in", "set", "not_set"];
        case "char":
        case "text":
        case "html":
            return ["=", "!=", "ilike", "not ilike", "in", "not in", "set", "not_set"];
        case "date":
        case "datetime":
            return ["=", "!=", ">", ">=", "<", "<=", "between", "set", "not_set"];
        case "integer":
        case "float":
        case "monetary":
            return [
                "=",
                "!=",
                ">",
                ">=",
                "<",
                "<=",
                "between",
                "ilike",
                "not ilike",
                "set",
                "not_set",
            ];
        case "many2one":
        case "many2many":
        case "one2many":
            return ["in", "not in", "=", "!=", "ilike", "not ilike", "set", "not_set"];
        case "json":
            return ["=", "!=", "ilike", "not ilike", "set", "not_set"];
        case "properties":
            return ["set", "not_set"];
        case undefined:
            return ["="];
        default:
            return [
                "=",
                "!=",
                ">",
                ">=",
                "<",
                "<=",
                "ilike",
                "not ilike",
                "like",
                "not like",
                "=like",
                "=ilike",
                "child_of",
                "parent_of",
                "in",
                "not in",
                "set",
                "not_set",
            ];
    }
}

function toKey(operator, negate = false) {
    if (!negate && typeof operator === "string" && operator in OPERATOR_DESCRIPTIONS) {
        // this case is the main one. We keep it simple
        return operator;
    }
    return JSON.stringify([formatValue(operator), negate]);
}

function toOperator(key) {
    if (!key.includes("[")) {
        return [key, false];
    }
    const [expr, negate] = JSON.parse(key);
    return [toValue(parseExpr(expr)), negate];
}

export function getOperatorLabel(operator, negate = false) {
    let label;
    if (typeof operator === "string" && operator in OPERATOR_DESCRIPTIONS) {
        if (negate && operator in TERM_OPERATORS_NEGATION) {
            return OPERATOR_DESCRIPTIONS[TERM_OPERATORS_NEGATION[operator]];
        }
        label = OPERATOR_DESCRIPTIONS[operator];
    } else {
        label = formatValue(operator);
    }
    if (negate) {
        return _t(`not %s`, label);
    }
    return label;
}

function getOperatorInfo(operator, negate = false) {
    const key = toKey(operator, negate);
    const label = getOperatorLabel(operator, negate);
    return [key, label];
}

export function getOperatorEditorInfo(fieldDef) {
    const operators = getDisplayedOperators(fieldDef || {});
    const defaultOperator = operators[0];
    const operatorsInfo = operators.map((operator) => getOperatorInfo(operator));
    return {
        component: Select,
        extractProps: ({ update, value: [operator, negate] }) => {
            const [operatorKey, operatorLabel] = getOperatorInfo(operator, negate);
            const options = [...operatorsInfo];
            if (!options.some(([key]) => key === operatorKey)) {
                options.push([operatorKey, operatorLabel]);
            }
            return {
                value: operatorKey,
                update: (operatorKey) => update(...toOperator(operatorKey)),
                options,
            };
        },
        defaultValue: () => defaultOperator,
        isSupported: ([operator]) =>
            typeof operator === "string" && operator in OPERATOR_DESCRIPTIONS, // should depend on fieldDef too... (e.g. parent_id does not always make sense)
        message: _t("Operator not supported"),
        stringify: ([operator, negate]) => getOperatorLabel(operator, negate),
    };
}

export function getDefaultOperator(fieldDef) {
    const { defaultValue } = getOperatorEditorInfo(fieldDef);
    return defaultValue();
}
