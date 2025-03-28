import { Domain } from "@web/core/domain";
import { formatAST, parseExpr } from "@web/core/py_js/py";
import { toPyValue } from "@web/core/py_js/py_utils";
import { deepCopy, deepEqual } from "@web/core/utils/objects";

/** @typedef { import("@web/core/py_js/py_parser").AST } AST */
/** @typedef {import("@web/core/domain").DomainRepr} DomainRepr */

/**
 * @typedef {number|string|boolean|Expression} Atom
 */

/**
 * @typedef {Atom|Atom[]} Value
 */

/**
 * @typedef {Object} Condition
 * @property {"condition"} type
 * @property {Value} path
 * @property {Value} operator
 * @property {Value|Tree} value
 * @property {boolean} negate
 */

/**
 * @typedef {Object} ComplexCondition
 * @property {"complex_condition"} type
 * @property {string} value expression
 */

/**
 * @typedef {Object} Connector
 * @property {"connector"} type
 * @property {boolean} negate
 * @property {"|"|"&"} value
 * @property {Tree[]} children
 */

/**
 * @typedef {Connector|Condition|ComplexCondition} Tree
 */

/**
 * @typedef {Object} Options
 * @property {(value: Value | Couple) => (null|Object)} [getFieldDef]
 * @property {boolean} [distributeNot]
 */

export const TERM_OPERATORS_NEGATION = {
    "<": ">=",
    ">": "<=",
    "<=": ">",
    ">=": "<",
    "=": "!=",
    "!=": "=",
    in: "not in",
    like: "not like",
    ilike: "not ilike",
    "not in": "in",
    "not like": "like",
    "not ilike": "ilike",
};

const TERM_OPERATORS_NEGATION_EXTENDED = {
    ...TERM_OPERATORS_NEGATION,
    is: "is not",
    "is not": "is",
    "==": "!=",
    "!=": "==", // override here
};

const EXCHANGE = {
    "<": ">",
    "<=": ">=",
    ">": "<",
    ">=": "<=",
    "=": "=",
    "!=": "!=",
};

const COMPARATORS = ["<", "<=", ">", ">=", "in", "not in", "==", "is", "!=", "is not"];

export const DATETIME_TODAY_STRING_EXPRESSION = `datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`;
export const DATETIME_END_OF_TODAY_STRING_EXPRESSION = `datetime.datetime.combine(context_today(), datetime.time(23, 59, 59)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`;
export const DATE_TODAY_STRING_EXPRESSION = `context_today().strftime("%Y-%m-%d")`;
const DELTA_DATE_AST = parseExpr(
    `(context_today() + relativedelta(period=amount)).strftime('%Y-%m-%d')`
);
const DELTA_DATETIME_AST = parseExpr(
    `datetime.datetime.combine(context_today() + relativedelta(period=amount), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
);

function replaceKwargs(ast, fieldType, kwargs = {}) {
    const astCopy = deepCopy(ast);
    if (fieldType === "date") {
        astCopy.fn.obj.right.kwargs = kwargs;
    } else {
        astCopy.fn.obj.fn.obj.args[0].right.kwargs = kwargs;
    }
    return astCopy;
}

function getDelta(ast, fieldType) {
    const kwargs =
        (fieldType === "date"
            ? ast.fn?.obj?.right?.kwargs
            : ast.fn?.obj?.fn?.obj?.args?.[0]?.right?.kwargs) || {};
    if (Object.keys(kwargs).length !== 1) {
        return null;
    }
    if (
        !deepEqual(
            replaceKwargs(ast, fieldType),
            replaceKwargs(fieldType === "date" ? DELTA_DATE_AST : DELTA_DATETIME_AST, fieldType)
        )
    ) {
        return null;
    }
    const [option, amountAST] = Object.entries(kwargs)[0];
    return [toValue(amountAST), option];
}

function getProcessedDelta(val, fieldType) {
    return getDelta(toAST(val), fieldType);
}

function getDeltaExpression(value, fieldType) {
    const ast = replaceKwargs(
        fieldType === "date" ? DELTA_DATE_AST : DELTA_DATETIME_AST,
        fieldType,
        { [value[1]]: toAST(value[0]) }
    );
    return expression(formatAST(ast));
}

export function isTodayExpr(val, type) {
    return (
        val._expr ===
        (type === "date" ? DATE_TODAY_STRING_EXPRESSION : DATETIME_TODAY_STRING_EXPRESSION)
    );
}

export function isEndOfTodayExpr(val) {
    return val._expr === DATETIME_END_OF_TODAY_STRING_EXPRESSION;
}

export class Couple {
    constructor(x, y) {
        this.fst = x;
        this.snd = y;
    }
}

export class Expression {
    constructor(ast) {
        if (typeof ast === "string") {
            ast = parseExpr(ast);
        }
        this._ast = ast;
        this._expr = formatAST(ast);
    }

    toAST() {
        return this._ast;
    }

    toString() {
        return this._expr;
    }
}

/**
 * @param {string} expr
 * @returns {Expression}
 */
export function expression(expr) {
    return new Expression(expr);
}

/**
 * @param {"|"|"&"} value
 * @param {Tree[]} [children=[]]
 * @param {boolean} [negate=false]
 * @returns {Connector}
 */
export function connector(value, children = [], negate = false) {
    return { type: "connector", value, children, negate };
}

/**
 * @param {Value} path
 * @param {Value} operator
 * @param {Value|Tree} value
 * @param {boolean} [negate=false]
 * @returns {Condition}
 */
export function condition(path, operator, value, negate = false) {
    return { type: "condition", path, operator, value, negate };
}

/**
 * @param {string} value
 * @returns {ComplexCondition}
 */
export function complexCondition(value) {
    parseExpr(value);
    return { type: "complex_condition", value };
}

/**
 * @param {Value} value
 * @returns {Value}
 */
function cloneValue(value) {
    if (value instanceof Expression) {
        return new Expression(value.toAST());
    }
    if (Array.isArray(value)) {
        return value.map(cloneValue);
    }
    return value;
}

/**
 * @param {Tree} tree
 * @returns {Tree}
 */
export function cloneTree(tree) {
    const clone = {};
    for (const key in tree) {
        clone[key] = cloneValue(tree[key]);
    }
    return clone;
}

function _areEquivalentTrees(tree, otherTree) {
    if (tree.type !== otherTree.type) {
        return false;
    }
    if (tree.negate !== otherTree.negate) {
        return false;
    }
    if (tree.type === "condition") {
        if (formatValue(tree.path) !== formatValue(otherTree.path)) {
            return false;
        }
        if (formatValue(tree.operator) !== formatValue(otherTree.operator)) {
            return false;
        }
        if (isTree(tree.value)) {
            if (isTree(otherTree.value)) {
                return _areEquivalentTrees(tree.value, otherTree.value);
            }
            return false;
        } else if (isTree(otherTree.value)) {
            return false;
        }
        if (formatValue(tree.value) !== formatValue(otherTree.value)) {
            return false;
        }
        return true;
    }
    if (tree.value !== otherTree.value) {
        return false;
    }
    if (tree.type === "complex_condition") {
        return true;
    }
    if (tree.children.length !== otherTree.children.length) {
        return false;
    }
    for (let i = 0; i < tree.children.length; i++) {
        const child = tree.children[i];
        const otherChild = otherTree.children[i];
        if (!_areEquivalentTrees(child, otherChild)) {
            return false;
        }
    }
    return true;
}

export function areEquivalentTrees(tree, otherTree) {
    const simplifiedTree = applyTransformations(VIRTUAL_OPERATORS_DESTRUCTION, tree);
    const otherSimplifiedTree = applyTransformations(VIRTUAL_OPERATORS_DESTRUCTION, otherTree);
    return _areEquivalentTrees(simplifiedTree, otherSimplifiedTree);
}

export function formatValue(value) {
    return formatAST(toAST(value));
}

export function normalizeValue(value) {
    return toValue(toAST(value)); // no array in array (see isWithinArray)
}

/**
 * @param {import("@web/core/py_js/py_parser").AST} ast
 * @returns {Value}
 */
export function toValue(ast, isWithinArray = false) {
    if ([4, 10].includes(ast.type) && !isWithinArray) {
        /** 4: list, 10: tuple */
        return ast.value.map((v) => toValue(v, true));
    } else if ([0, 1, 2].includes(ast.type)) {
        /** 0: number, 1: string, 2: boolean */
        return ast.value;
    } else if (ast.type === 6 && ast.op === "-" && ast.right.type === 0) {
        /** 6: unary operator */
        return -ast.right.value;
    } else if (ast.type === 5 && ["false", "true"].includes(ast.value)) {
        /** 5: name */
        return JSON.parse(ast.value);
    } else {
        return new Expression(ast);
    }
}

export function isTree(value) {
    return (
        typeof value === "object" &&
        !(value instanceof Domain) &&
        !(value instanceof Expression) &&
        !Array.isArray(value) &&
        value !== null
    );
}

/**
 * @param {Value} value
 * @returns  {import("@web/core/py_js/py_parser").AST}
 */
function toAST(value) {
    if (isTree(value)) {
        const domain = new Domain(domainFromTree(value));
        return domain.ast;
    }
    if (value instanceof Expression) {
        return value.toAST();
    }
    if (Array.isArray(value)) {
        return { type: 4, value: value.map(toAST) };
    }
    return toPyValue(value);
}

/**
 * @param {Connector} parent
 * @param {Tree} child
 */
function addChild(parent, child) {
    if (child.type === "connector" && !child.negate && child.value === parent.value) {
        parent.children.push(...child.children);
    } else {
        parent.children.push(child);
    }
}

/**
 * @param {Condition} condition
 * @returns {Condition}
 */
function getNormalizedCondition(condition) {
    let { operator, negate } = condition;
    if (negate && typeof operator === "string" && TERM_OPERATORS_NEGATION[operator]) {
        operator = TERM_OPERATORS_NEGATION[operator];
        negate = false;
    }
    return { ...condition, operator, negate };
}

function normalizeCondition(condition) {
    Object.assign(condition, getNormalizedCondition(condition));
}

/**
 * @param {AST[]} ASTs
 * @param {Options} [options={}]
 * @param {boolean} [negate=false]
 * @returns {{ tree: Tree, remaimingASTs: AST[] }}
 */
function _construcTree(ASTs, options = {}, negate = false) {
    const [firstAST, ...tailASTs] = ASTs;

    if (firstAST.type === 1 && firstAST.value === "!") {
        return _construcTree(tailASTs, options, !negate);
    }

    const tree = { type: firstAST.type === 1 ? "connector" : "condition" };
    if (tree.type === "connector") {
        tree.value = firstAST.value;
        if (options.distributeNot && negate) {
            tree.value = tree.value === "&" ? "|" : "&";
            tree.negate = false;
        } else {
            tree.negate = negate;
        }
        tree.children = [];
    } else {
        const [pathAST, operatorAST, valueAST] = firstAST.value;
        tree.path = toValue(pathAST);
        tree.negate = negate;
        tree.operator = toValue(operatorAST);
        tree.value = toValue(valueAST);
        if (["any", "not any"].includes(tree.operator)) {
            try {
                tree.value = treeFromDomain(formatAST(valueAST), {
                    ...options,
                    getFieldDef: (p) => options.getFieldDef?.(new Couple(tree.path, p)) || null,
                });
            } catch {
                tree.value = Array.isArray(tree.value) ? tree.value : [tree.value];
            }
        }
        normalizeCondition(tree);
    }
    let remaimingASTs = tailASTs;
    if (tree.type === "connector") {
        for (let i = 0; i < 2; i++) {
            const { tree: child, remaimingASTs: otherASTs } = _construcTree(
                remaimingASTs,
                options,
                options.distributeNot && negate
            );
            remaimingASTs = otherASTs;
            addChild(tree, child);
        }
    }
    return { tree, remaimingASTs };
}

/**
 * @param {AST[]} initialASTs
 * @param {Options} [options={}]
 * @returns {Tree}
 */
function construcTree(initialASTs, options = {}) {
    if (!initialASTs.length) {
        return connector("&");
    }
    const { tree } = _construcTree(initialASTs, options);
    return tree;
}

/**
 * @param {Tree} tree
 * @returns {AST[]}
 */
function getASTs(tree) {
    const ASTs = [];
    if (tree.type === "condition") {
        if (tree.negate) {
            ASTs.push(toAST("!"));
        }
        ASTs.push({
            type: 10,
            value: [tree.path, tree.operator, tree.value].map(toAST),
        });
        return ASTs;
    }

    const length = tree.children.length;
    if (length && tree.negate) {
        ASTs.push(toAST("!"));
    }
    for (let i = 0; i < length - 1; i++) {
        ASTs.push(toAST(tree.value));
    }
    for (const child of tree.children) {
        ASTs.push(...getASTs(child));
    }
    return ASTs;
}

function not(ast) {
    if (isNot(ast)) {
        return ast.right;
    }
    if (ast.type === 2) {
        return { ...ast, value: !ast.value };
    }
    if (ast.type === 7 && COMPARATORS.includes(ast.op)) {
        return { ...ast, op: TERM_OPERATORS_NEGATION_EXTENDED[ast.op] }; // do not use this if ast is within a domain context!
    }
    return { type: 6, op: "not", right: isBool(ast) ? ast.args[0] : ast };
}

function bool(ast) {
    if (isBool(ast) || isNot(ast) || ast.type === 2) {
        return ast;
    }
    return { type: 8, fn: { type: 5, value: "bool" }, args: [ast], kwargs: {} };
}

function name(value) {
    return { type: 5, value };
}

function or(left, right) {
    return { type: 14, op: "or", left, right };
}

function and(left, right) {
    return { type: 14, op: "and", left, right };
}

function isNot(ast) {
    return ast.type === 6 && ast.op === "not";
}

function is(oneParamFunc, ast) {
    return (
        ast.type === 8 &&
        ast.fn.type === 5 &&
        ast.fn.value === oneParamFunc &&
        ast.args.length === 1
    ); // improve condition?
}

function isSet(ast) {
    return ast.type === 8 && ast.fn.type === 5 && ast.fn.value === "set" && ast.args.length <= 1;
}

function isBool(ast) {
    return is("bool", ast);
}

function isValidPath(ast, options) {
    const getFieldDef = options.getFieldDef || (() => null);
    if (ast.type === 5) {
        return getFieldDef(ast.value) !== null;
    }
    return false;
}

function isX2Many(ast, options) {
    if (isValidPath(ast, options)) {
        const fieldDef = options.getFieldDef(ast.value); // safe: isValidPath has not returned null;
        return ["many2many", "one2many"].includes(fieldDef.type);
    }
    return false;
}

function _getConditionFromComparator(ast, options) {
    if (["is", "is not"].includes(ast.op)) {
        // we could do something smarter here
        // e.g. if left is a boolean field and right is a boolean
        // we can create a condition based on "="
        return null;
    }

    let operator = ast.op;
    if (operator === "==") {
        operator = "=";
    }

    let left = ast.left;
    let right = ast.right;
    if (isValidPath(left, options) == isValidPath(right, options)) {
        return null;
    }

    if (!isValidPath(left, options)) {
        if (operator in EXCHANGE) {
            const temp = left;
            left = right;
            right = temp;
            operator = EXCHANGE[operator];
        } else {
            return null;
        }
    }

    return condition(left.value, operator, toValue(right));
}

function isValidPath2(ast, options) {
    if (!ast) {
        return null;
    }
    if ([4, 10].includes(ast.type) && ast.value.length === 1) {
        return isValidPath(ast.value[0], options);
    }
    return isValidPath(ast, options);
}

function _getConditionFromIntersection(ast, options, negate = false) {
    let left = ast.fn.obj.args[0];
    let right = ast.args[0];

    if (!left) {
        return condition(negate ? 1 : 0, "=", 1);
    }

    // left/right exchange
    if (isValidPath2(left, options) == isValidPath2(right, options)) {
        return null;
    }
    if (!isValidPath2(left, options)) {
        const temp = left;
        left = right;
        right = temp;
    }

    if ([4, 10].includes(left.type) && left.value.length === 1) {
        left = left.value[0];
    }

    if (!right) {
        return condition(left.value, negate ? "=" : "!=", false);
    }

    // try to extract the ast of an iterable
    // we only make simple conversions here
    if (isSet(right)) {
        if (!right.args[0]) {
            right = { type: 4, value: [] };
        }
        if ([4, 10].includes(right.args[0].type)) {
            right = right.args[0];
        }
    }

    if (![4, 10].includes(right.type)) {
        return null;
    }

    return condition(left.value, negate ? "not in" : "in", toValue(right));
}

/**
 * @param {AST} ast
 * @param {Options} options
 * @param {boolean} [negate=false]
 * @returns {Condition|ComplexCondition}
 */
function _leafFromAST(ast, options, negate = false) {
    if (isNot(ast)) {
        return _treeFromAST(ast.right, options, !negate);
    }

    if (ast.type === 5 /** name */ && isValidPath(ast, options)) {
        return condition(ast.value, negate ? "=" : "!=", false);
    }

    const astValue = toValue(ast);
    if (["boolean", "number", "string"].includes(typeof astValue)) {
        return condition(astValue ? 1 : 0, "=", 1);
    }

    if (
        ast.type === 8 &&
        ast.fn.type === 15 /** object lookup */ &&
        isSet(ast.fn.obj) &&
        ast.fn.key === "intersection"
    ) {
        const tree = _getConditionFromIntersection(ast, options, negate);
        if (tree) {
            return tree;
        }
    }

    if (ast.type === 7 && COMPARATORS.includes(ast.op)) {
        if (negate) {
            return _leafFromAST(not(ast), options);
        }
        const tree = _getConditionFromComparator(ast, options);
        if (tree) {
            return tree;
        }
    }

    // no conclusive/simple way to transform ast in a condition
    return complexCondition(formatAST(negate ? not(ast) : ast));
}

/**
 * @param {AST} ast
 * @param {Options} options
 * @param {boolean} [negate=false]
 * @returns {Tree}
 */
function _treeFromAST(ast, options, negate = false) {
    if (isNot(ast)) {
        return _treeFromAST(ast.right, options, !negate);
    }

    if (ast.type === 14) {
        const tree = connector(
            ast.op === "and" ? "&" : "|" // and/or are the only ops that are given type 14 (for now)
        );
        if (options.distributeNot && negate) {
            tree.value = tree.value === "&" ? "|" : "&";
        } else {
            tree.negate = negate;
        }
        const subASTs = [ast.left, ast.right];
        for (const subAST of subASTs) {
            const child = _treeFromAST(subAST, options, options.distributeNot && negate);
            addChild(tree, child);
        }
        return tree;
    }

    if (ast.type === 13) {
        const newAST = or(and(ast.condition, ast.ifTrue), and(not(ast.condition), ast.ifFalse));
        return _treeFromAST(newAST, options, negate);
    }

    return _leafFromAST(ast, options, negate);
}

function _expressionFromTree(tree, options, isRoot = false) {
    if (tree.type === "connector" && tree.value === "|" && tree.children.length === 2) {
        // check if we have an "if else"
        const isSimpleAnd = (tree) =>
            tree.type === "connector" && tree.value === "&" && tree.children.length === 2;
        if (tree.children.every((c) => isSimpleAnd(c))) {
            const [c1, c2] = tree.children;
            for (let i = 0; i < 2; i++) {
                const c1Child = c1.children[i];
                const str1 = _expressionFromTree({ ...c1Child }, options);
                for (let j = 0; j < 2; j++) {
                    const c2Child = c2.children[j];
                    const str2 = _expressionFromTree(c2Child, options);
                    if (str1 === `not ${str2}` || `not ${str1}` === str2) {
                        /** @todo smth smarter. this is very fragile */
                        const others = [c1.children[1 - i], c2.children[1 - j]];
                        const str = _expressionFromTree(c1Child, options);
                        const strs = others.map((c) => _expressionFromTree(c, options));
                        return `${strs[0]} if ${str} else ${strs[1]}`;
                    }
                }
            }
        }
    }

    if (tree.type === "connector") {
        const connector = tree.value === "&" ? "and" : "or";
        const subExpressions = tree.children.map((c) => _expressionFromTree(c, options));
        if (!subExpressions.length) {
            return connector === "and" ? "1" : "0";
        }
        let expression = subExpressions.join(` ${connector} `);
        if (!isRoot || tree.negate) {
            expression = `( ${expression} )`;
        }
        if (tree.negate) {
            expression = `not ${expression}`;
        }
        return expression;
    }

    if (tree.type === "complex_condition") {
        return tree.value;
    }

    tree = getNormalizedCondition(tree);
    const { path, operator, value } = tree;

    const op = operator === "=" ? "==" : operator; // do something about is ?
    if (typeof op !== "string" || !COMPARATORS.includes(op)) {
        throw new Error("Invalid operator");
    }

    // we can assume that negate = false here: comparators have negation defined
    // and the tree has been normalized

    if ([0, 1].includes(path)) {
        if (operator !== "=" || value !== 1) {
            // check if this is too restricive for us
            return new Error("Invalid condition");
        }
        return formatAST({ type: 2, value: Boolean(path) });
    }

    const pathAST = toAST(path);
    if (typeof path == "string" && isValidPath(name(path), options)) {
        pathAST.type = 5;
    }

    if (value === false && ["=", "!="].includes(operator)) {
        // true makes sense for non boolean fields?
        return formatAST(operator === "=" ? not(pathAST) : pathAST);
    }

    let valueAST = toAST(value);
    if (
        ["in", "not in"].includes(operator) &&
        !(value instanceof Expression) &&
        ![4, 10].includes(valueAST.type)
    ) {
        valueAST = { type: 4, value: [valueAST] };
    }

    if (pathAST.type === 5 && isX2Many(pathAST, options) && ["in", "not in"].includes(operator)) {
        const ast = {
            type: 8,
            fn: {
                type: 15,
                obj: {
                    args: [pathAST],
                    type: 8,
                    fn: {
                        type: 5,
                        value: "set",
                    },
                },
                key: "intersection",
            },
            args: [valueAST],
        };
        return formatAST(operator === "not in" ? not(ast) : ast);
    }

    // add case true for boolean fields

    return formatAST({
        type: 7,
        op,
        left: pathAST,
        right: valueAST,
    });
}

////////////////////////////////////////////////////////////////////////////////
// some helpers
////////////////////////////////////////////////////////////////////////////////

function getFieldType(path, options) {
    return options.getFieldDef?.(path)?.type;
}

function allEqual(...values) {
    return values.slice(1).every((v) => v === values[0]);
}

function applyTransformations(transformations, transformed, ...fixedParams) {
    for (let i = transformations.length - 1; i >= 0; i--) {
        const fn = transformations[i];
        transformed = fn(transformed, ...fixedParams);
    }
    return transformed;
}

function rewriteNConsecutiveConditions(transformation, connector, options = {}, N = 2) {
    const children = [];
    const currentChildren = connector.children;
    for (let i = 0; i < currentChildren.length; i++) {
        const NconsecutiveChildren = currentChildren.slice(i, i + N);
        let replacement = null;
        if (
            NconsecutiveChildren.length === N &&
            allEqual("condition", ...NconsecutiveChildren.map((c) => c.type))
        ) {
            replacement = transformation(connector, NconsecutiveChildren, options);
        }
        if (replacement) {
            children.push(replacement);
            i += N - 1;
        } else {
            children.push(NconsecutiveChildren[0]);
        }
    }
    return { ...connector, children };
}

function normalizeConnector(connector) {
    const newTree = { ...connector, children: [] };
    for (const child of connector.children) {
        addChild(newTree, child);
    }
    if (newTree.children.length === 1) {
        const child = newTree.children[0];
        if (newTree.negate) {
            return { ...child, negate: !child.negate };
        }
        return child;
    }
    return newTree;
}

/**
 * @param {Function} transformation
 * @param {Tree} tree
 * @param {Options} [options={}]
 * @param {"condition"|"connector"|"complex_condition"} [treeType="condition"]
 * @returns {Tree}
 */
function operate(transformation, tree, options = {}, treeType = "condition") {
    if (tree.type === "connector") {
        const newTree = {
            ...tree,
            children: tree.children.map((c) => operate(transformation, c, options, treeType)),
        };
        if (treeType === "connector") {
            return normalizeConnector(transformation(newTree, options) || newTree);
        }
        return normalizeConnector(newTree);
    }
    const clone = cloneTree(tree);
    if (treeType === tree.type) {
        return transformation(clone, options) || clone;
    }
    return clone;
}

////////////////////////////////////////////////////////////////////////////////
// between - is_not_between
////////////////////////////////////////////////////////////////////////////////

/**
 * @param {Connector} c
 * @param {[Condition, Condition]} param
 */
function _createBetweenOperator(c, [child1, child2]) {
    if (formatValue(child1.path) !== formatValue(child2.path)) {
        return;
    }
    if (c.value === "&" && child1.operator === ">=" && child2.operator === "<=") {
        return condition(child1.path, "between", normalizeValue([child1.value, child2.value]));
    }
    if (c.value === "|" && child1.operator === "<" && child2.operator === ">") {
        return condition(
            child1.path,
            "is_not_between",
            normalizeValue([child1.value, child2.value])
        );
    }
}

/**
 * @param {Condition} c
 */
function _removeBetweenOperator(c) {
    const { negate, path, operator, value } = c;
    if (!Array.isArray(value)) {
        return;
    }
    if (operator === "between") {
        return connector(
            "&",
            [condition(path, ">=", value[0]), condition(path, "<=", value[1])],
            negate
        );
    } else if (operator === "is_not_between") {
        return connector(
            "|",
            [condition(path, "<", value[0]), condition(path, ">", value[1])],
            negate
        );
    }
}

/////////////////////////////////////////////////////////////////////////////////
// set - not_set - starts_with - ends_with - next - not_next - last - not_last
// today - not_today
/////////////////////////////////////////////////////////////////////////////////

/**
 * @param {Condition} c
 * @param {Options} [options={}]
 */
function _createVirtualOperator(c, options = {}) {
    const { negate, path, operator, value } = c;
    const fieldType = getFieldType(path, options);
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
    if (
        ["between", "is_not_between"].includes(operator) &&
        ["date", "datetime"].includes(fieldType)
    ) {
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
        ["between", "is_not_between"].includes(operator) &&
        isTodayExpr(value[0], fieldType) &&
        isEndOfTodayExpr(value[1])
    ) {
        return condition(path, operator === "between" ? "today" : "not_today", value, negate);
    }
}

/**
 * @param {Condition} c
 */
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
            ["next", "last"].includes(operator) ? "between" : "is_not_between",
            expressions,
            negate
        );
    }
    if (["today", "not_today"].includes(operator)) {
        if (Array.isArray(value)) {
            return condition(
                path,
                operator === "today" ? "between" : "is_not_between",
                value,
                negate
            );
        } else {
            return condition(path, operator === "today" ? "=" : "!=", value, negate);
        }
    }
}

////////////////////////////////////////////////////////////////////////////////
// complex conditions
////////////////////////////////////////////////////////////////////////////////

/**
 * @param {Condition} c
 */
function _createComplexCondition(c) {
    if (c.path instanceof Expression && c.operator === "=" && c.value === 1) {
        return complexCondition(String(c.path));
    }
}

/**
 * @param {ComplexCondition} c
 */
function _removeComplexCondition(c) {
    const ast = parseExpr(c.value);
    return condition(new Expression(bool(ast)), "=", 1);
}

////////////////////////////////////////////////////////////////////////////////
//  operations on trees
////////////////////////////////////////////////////////////////////////////////

/**
 * @param {Tree} tree
 * @returns {Tree}
 */
function createBetweenOperators(tree) {
    return operate(
        (connector) => rewriteNConsecutiveConditions(_createBetweenOperator, connector),
        tree,
        {},
        "connector"
    );
}

/**
 * @param {Tree} tree
 * @returns {Tree}
 */
function removeBetweenOperators(tree) {
    return operate(_removeBetweenOperator, tree);
}

/**
 * @param {Tree} tree
 * @param {Options} [options=[]]
 * @returns {Tree}
 */
export function createVirtualOperators(tree, options = {}) {
    return operate(_createVirtualOperator, tree, options);
}

/**
 * @param {Tree} tree
 * @returns {Tree}
 */
export function removeVirtualOperators(tree) {
    return operate(_removeVirtualOperator, tree);
}

/**
 * @param {Tree} tree
 * @returns {Tree} the conditions better expressed as complex conditions become complex conditions
 */
function createComplexConditions(tree) {
    return operate(_createComplexCondition, tree);
}

/**
 * @param {Tree} tree
 * @returns {Tree} a simple tree (without complex conditions)
 */
function removeComplexConditions(tree) {
    return operate(_removeComplexCondition, tree, {}, "complex_condition");
}

////////////////////////////////////////////////////////////////////////////////
//  PUBLIC: MAPPINGS
//    tree <-> expression
//    domain <-> expression
//    expression <-> tree
////////////////////////////////////////////////////////////////////////////////

const VIRTUAL_OPERATORS_CREATION = [createVirtualOperators, createBetweenOperators];

const VIRTUAL_OPERATORS_DESTRUCTION = [removeBetweenOperators, removeVirtualOperators];

/**
 * @param {string} expression
 * @param {Options} [options={}]
 * @returns {Tree} a tree representation of an expression
 */
export function treeFromExpression(expression, options = {}) {
    const ast = parseExpr(expression);
    const tree = _treeFromAST(ast, options);
    return applyTransformations(VIRTUAL_OPERATORS_CREATION, tree, options);
}

/**
 * @param {Tree} tree
 * @param {Options} [options={}]
 * @returns {string} an expression
 */
export function expressionFromTree(tree, options = {}) {
    const simplifiedTree = applyTransformations(
        [createComplexConditions, ...VIRTUAL_OPERATORS_DESTRUCTION],
        tree
    );
    return _expressionFromTree(simplifiedTree, options, true);
}

/**
 * @param {Tree} tree
 * @returns {string} a string representation of a domain
 */
export function domainFromTree(tree) {
    const simplifiedTree = applyTransformations(
        [...VIRTUAL_OPERATORS_DESTRUCTION, removeComplexConditions],
        tree
    );
    const domainAST = {
        type: 4,
        value: getASTs(simplifiedTree),
    };
    return formatAST(domainAST);
}

/**
 * @param {DomainRepr} domain
 * @param {Object} [options={}] see construcTree API
 * @returns {Tree} a (simple) tree representation of a domain
 */
export function treeFromDomain(domain, options = {}) {
    domain = new Domain(domain);
    const domainAST = domain.ast;
    const tree = construcTree(domainAST.value, options); // a simple tree
    return applyTransformations(VIRTUAL_OPERATORS_CREATION, tree, options);
}

/**
 * @param {DomainRepr} domain a string representation of a domain
 * @param {Options} [options={}]
 * @returns {string} an expression
 */
export function expressionFromDomain(domain, options = {}) {
    const tree = treeFromDomain(domain, options);
    return expressionFromTree(tree, options);
}

/**
 * @param {string} expression an expression
 * @param {Options} [options={}]
 * @returns {string} a string representation of a domain
 */
export function domainFromExpression(expression, options = {}) {
    const tree = treeFromExpression(expression, options);
    return domainFromTree(tree);
}
