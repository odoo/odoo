import { formatAST, parseExpr } from "@web/core/py_js/py";
import {
    addChild,
    applyTransformations,
    complexCondition,
    condition,
    connector,
    Expression,
    getNormalizedCondition,
    TERM_OPERATORS_NEGATION,
    toAST,
    toValue,
    VIRTUAL_OPERATORS_CREATION,
    VIRTUAL_OPERATORS_DESTRUCTION,
} from "@web/core/tree_editor/condition_tree";

const COMPARATORS = ["<", "<=", ">", ">=", "in", "not in", "==", "is", "!=", "is not"];

const EXCHANGE = {
    "<": ">",
    "<=": ">=",
    ">": "<",
    ">=": "<=",
    "=": "=",
    "!=": "!=",
};

const TERM_OPERATORS_NEGATION_EXTENDED = {
    ...TERM_OPERATORS_NEGATION,
    is: "is not",
    "is not": "is",
    "==": "!=",
    "!=": "==", // override here
};

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
    const simplifiedTree = applyTransformations(VIRTUAL_OPERATORS_DESTRUCTION, tree);
    return _expressionFromTree(simplifiedTree, options, true);
}
