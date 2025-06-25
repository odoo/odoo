import { _t } from "@web/core/l10n/translation";
import {
    formatValue,
    TERM_OPERATORS_NEGATION,
    toValue,
} from "@web/core/tree_editor/condition_tree";
import { sprintf } from "@web/core/utils/strings";
import { parseExpr } from "@web/core/py_js/py";
import { Select } from "@web/core/tree_editor/tree_editor_components";

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

    starts_with: _t("starts with"),
    ends_with: _t("ends with"),

    // virtual operator (equivalent to a couple (>=,<=))
    between: _t("is between"),
    within: _t("is within"),

    any: (fieldDefType) => {
        switch (fieldDefType) {
            case "many2one":
                return _t("matches");
            default:
                return _t("match");
        }
    },
    "not any": (fieldDefType) => {
        switch (fieldDefType) {
            case "many2one":
                return _t("matches none of");
            default:
                return _t("match none of");
        }
    },
};

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

function getOperatorDescription(operator, fieldDefType) {
    const description = OPERATOR_DESCRIPTIONS[operator];
    if (
        typeof description === "function" &&
        description.constructor?.name !== "LazyTranslatedString"
    ) {
        return description(fieldDefType);
    }
    return description;
}

export function getOperatorLabel(operator, fieldDefType, negate = false) {
    let label;
    if (typeof operator === "string" && operator in OPERATOR_DESCRIPTIONS) {
        if (negate && operator in TERM_OPERATORS_NEGATION) {
            return getOperatorDescription(TERM_OPERATORS_NEGATION[operator], fieldDefType);
        }
        label = getOperatorDescription(operator, fieldDefType);
    } else {
        label = formatValue(operator);
    }
    if (negate) {
        return sprintf(`not %s`, label);
    }
    return label;
}

function getOperatorInfo(operator, fieldDefType, negate = false) {
    const key = toKey(operator, negate);
    const label = getOperatorLabel(operator, fieldDefType, negate);
    return [key, label];
}

export function getOperatorEditorInfo(operators, fieldDef) {
    const defaultOperator = operators[0];
    const operatorsInfo = operators.map((operator) => getOperatorInfo(operator, fieldDef?.type));
    return {
        component: Select,
        extractProps: ({ update, value: [operator, negate] }) => {
            const [operatorKey, operatorLabel] = getOperatorInfo(operator, fieldDef?.type, negate);
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
