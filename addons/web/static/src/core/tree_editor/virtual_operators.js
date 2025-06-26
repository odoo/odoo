import {
    applyTransformations,
    areEqualTrees,
    astFromValue,
    cloneTree,
    condition,
    connector,
    Expression,
    expression,
    FALSE_TREE,
    isTree,
    normalizeValue,
    operate,
    rewriteNConsecutiveChildren,
    toValue,
    TRUE_TREE,
} from "./condition_tree";
import { Just, Nothing } from "./maybe_monad";
import { ASTPattern } from "./patterns/ast_pattern";
import { OperatorPattern } from "./patterns/operator_pattern";
import { Pattern } from "./patterns/pattern";

export const DATETIME_TODAY_STRING_EXPRESSION = `datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`;
export const DATETIME_END_OF_TODAY_STRING_EXPRESSION = `datetime.datetime.combine(context_today(), datetime.time(23, 59, 59)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`;
export const DATE_TODAY_STRING_EXPRESSION = `context_today().strftime("%Y-%m-%d")`;

export function isTodayExpr(val, type) {
    return type === "date"
        ? val._expr === DATE_TODAY_STRING_EXPRESSION
        : val._expr === DATETIME_TODAY_STRING_EXPRESSION;
}

export function isEndOfTodayExpr(val) {
    return val._expr === DATETIME_END_OF_TODAY_STRING_EXPRESSION;
}

const DELTA_DATE_PATTERN = ASTPattern.of(
    `(context_today() + relativedelta(period=amount)).strftime('%Y-%m-%d')`,
    {
        kwargs: ["fn.obj.right.kwargs"], // target in ast the kwargs with period=amount
    }
);

const DELTA_DATETIME_PATTERN = ASTPattern.of(
    `datetime.datetime.combine(context_today() + relativedelta(period=amount), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`,
    {
        kwargs: ["fn.obj.fn.obj.args[0].right.kwargs"], // target in ast the kwargs with period=amount
    }
);

function getProcessedDelta(expr, type) {
    if (!(expr instanceof Expression)) {
        return Nothing.of();
    }
    const ast = expr._ast;
    const mv =
        type === "date" ? DELTA_DATE_PATTERN.detect(ast) : DELTA_DATETIME_PATTERN.detect(ast);
    if (mv instanceof Nothing) {
        return null;
    }
    const { kwargs } = mv.value;
    if (Object.keys(kwargs).length !== 1) {
        return null;
    }
    const [option, amountAST] = Object.entries(kwargs)[0];
    return [toValue(amountAST), option];
}

function getDeltaExpression(val, type) {
    const [amount, option] = val;
    const values = { kwargs: { [option]: astFromValue(amount) } };
    const mv =
        type === "date" ? DELTA_DATE_PATTERN.make(values) : DELTA_DATETIME_PATTERN.make(values);
    if (mv instanceof Nothing) {
        return null;
    }
    const ast = mv.value;
    return expression(ast);
}

function _createVirtualOperator(c, options = {}) {
    const { negate, path, operator, value } = c;
    const fieldType = options.getFieldDef?.(path)?.type;
    if (typeof operator === "string" && ["=", "!="].includes(operator)) {
        if (fieldType) {
            if (fieldType === "boolean" && value === true) {
                return condition(path, operator === "=" ? "set" : "not_set", value, negate);
            } else if (!["many2one", "date", "datetime"].includes(fieldType) && value === false) {
                return condition(path, operator === "=" ? "not_set" : "set", value, negate);
            }
        }
    }
    if (typeof value === "string" && operator === "=ilike") {
        if (value.endsWith("%")) {
            return condition(path, "starts_with", value.slice(0, -1), negate);
        }
        if (value.startsWith("%")) {
            return condition(path, "ends_with", value.slice(1), negate);
        }
    }
    if (["between", "not_between"].includes(operator) && ["date", "datetime"].includes(fieldType)) {
        let delta;
        let virtualOperator;
        if (isTodayExpr(value[0], fieldType)) {
            delta = getProcessedDelta(value[1], fieldType);
            virtualOperator = operator === "between" ? "next" : "not_next";
        } else if (isTodayExpr(value[1], fieldType)) {
            delta = getProcessedDelta(value[0], fieldType);
            if (delta) {
                delta[0] = Number.isInteger(delta[0]) ? -delta[0] : delta[0];
            }
            virtualOperator = operator === "between" ? "last" : "not_last";
        }
        if (delta) {
            return condition(path, virtualOperator, [...delta, fieldType], negate);
        }
    }
    if (fieldType === "date" && ["=", "!="].includes(operator) && isTodayExpr(value, fieldType)) {
        return condition(path, operator === "=" ? "today" : "not_today", value, negate);
    }
    if (
        fieldType === "datetime" &&
        ["between", "not_between"].includes(operator) &&
        isTodayExpr(value[0], fieldType) &&
        isEndOfTodayExpr(value[1])
    ) {
        return condition(path, operator === "between" ? "today" : "not_today", value, negate);
    }
}

function _removeVirtualOperator(c) {
    const { negate, path, operator, value } = c;
    if (typeof operator !== "string") {
        return;
    }
    if (["set", "not_set"].includes(operator)) {
        if (value === true) {
            return condition(path, operator === "set" ? "=" : "!=", value, negate);
        }
        return condition(path, operator === "set" ? "!=" : "=", value, negate);
    }
    if (["starts_with", "ends_with"].includes(operator)) {
        return condition(
            path,
            "=ilike",
            operator === "starts_with" ? `${value}%` : `%${value}`,
            negate
        );
    }
    if (["next", "not_next", "last", "not_last"].includes(operator)) {
        const fieldType = value[2];
        const val =
            ["last", "not_last"].includes(operator) && Number.isInteger(value[0])
                ? [-value[0], value[1], value[2]]
                : value;

        const expressions = [
            expression(
                fieldType === "date"
                    ? DATE_TODAY_STRING_EXPRESSION
                    : DATETIME_TODAY_STRING_EXPRESSION
            ),
            getDeltaExpression(val, fieldType),
        ];
        if (["last", "not_last"].includes(operator)) {
            expressions.reverse();
        }
        return condition(
            path,
            ["next", "last"].includes(operator) ? "between" : "not_between",
            expressions,
            negate
        );
    }
    if (["today", "not_today"].includes(operator)) {
        if (Array.isArray(value)) {
            return condition(path, operator === "today" ? "between" : "not_between", value, negate);
        } else {
            return condition(path, operator === "today" ? "=" : "!=", value, negate);
        }
    }
}

function createVirtualOperators(tree, options = {}) {
    return operate(_createVirtualOperator, tree, options);
}

function removeVirtualOperators(tree) {
    return operate(_removeVirtualOperator, tree);
}

const patternBetween = OperatorPattern.of(
    "between",
    `["&", (path, ">=", value1), (path, "<=", value2)]`
);
const patternNotBetween = OperatorPattern.of(
    "not_between",
    `["|", (path, "<", value1), (path, ">", value2)]`
);

function splitPath(path) {
    const pathParts = typeof path === "string" ? path.split(".") : [];
    const lastPart = pathParts.pop() || "";
    const initialPath = pathParts.join(".");
    return { initialPath, lastPart };
}

function isSimplePath(path) {
    return typeof path === "string" && !splitPath(path).initialPath;
}

function wrapInAny(tree, initialPath, negate) {
    let con = cloneTree(tree);
    if (initialPath) {
        con = condition(initialPath, "any", con);
    }
    con.negate = negate;
    return Just.of(con);
}

function _createBetweenOperator(c) {
    return Pattern.S([patternBetween, patternNotBetween])
        .detect(c)
        .bind(({ path, operator, value1, value2 }) => {
            if (isSimplePath(path)) {
                return Just.of(condition(path, operator, normalizeValue([value1, value2])));
            }
            return Nothing.of();
        });
}

function _removeBetweenOperator(c) {
    const { negate, path, operator, value } = c;
    // @ts-ignore
    if (
        !Array.isArray(value) ||
        !["between", "not_between"].includes(operator) ||
        typeof path !== "string"
    ) {
        return;
    }
    const { initialPath, lastPart } = splitPath(path);
    return Pattern.S([patternBetween, patternNotBetween])
        .make({
            path: lastPart,
            operator,
            value1: value[0],
            value2: value[1],
        })
        .bind((tree) => wrapInAny(tree, initialPath, negate));
}

function createBetweenOperators(tree, options = {}) {
    return operate(rewriteNConsecutiveChildren(_createBetweenOperator), tree, options, "connector");
}

function removeBetweenOperators(tree) {
    return operate(_removeBetweenOperator, tree);
}

function _removeAnyOperator(c) {
    const { path, operator, value, negate } = c;
    if (
        operator === "any" &&
        isTree(value) &&
        value.type === "condition" &&
        typeof path === "string" &&
        typeof value.path === "string" &&
        !negate &&
        !value.negate &&
        ["between", "not_between"].includes(value.operator)
    ) {
        return condition(`${path}.${value.path}`, value.operator, value.value);
    }
}

function removeAnyOperators(tree) {
    return operate(_removeAnyOperator, tree);
}

function _removeFalseTrueLeaves(c) {
    const { path, operator, value, negate } = c;
    if (areEqualTrees(condition(path, operator, value), FALSE_TREE)) {
        return connector(negate ? "&" : "|", []);
    }
    if (areEqualTrees(condition(path, operator, value), TRUE_TREE)) {
        return connector(negate ? "|" : "&", []);
    }
}

function removeFalseTrueLeaves(tree) {
    return operate(_removeFalseTrueLeaves, tree);
}

export function introduceVirtualOperators(tree, options) {
    return applyTransformations(
        [removeAnyOperators, createVirtualOperators, createBetweenOperators],
        tree,
        options
    );
}

export function eliminateVirtualOperators(tree) {
    return applyTransformations([removeBetweenOperators, removeVirtualOperators], tree);
}

export function areEquivalentTrees(tree, otherTree) {
    const simplifiedTree = removeFalseTrueLeaves(eliminateVirtualOperators(tree));
    const otherSimplifiedTree = removeFalseTrueLeaves(eliminateVirtualOperators(otherTree));
    return areEqualTrees(simplifiedTree, otherSimplifiedTree);
}
