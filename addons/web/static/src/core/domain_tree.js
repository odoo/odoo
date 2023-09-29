/** @odoo-module **/

import { Domain } from "@web/core/domain";
import { formatAST, toPyValue } from "@web/core/py_js/py_utils";
import { parseExpr } from "@web/core/py_js/py";

const TERM_OPERATORS_NEGATION = {
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

export class Expression {
    constructor(ast) {
        this._ast = ast;
        this._expr = formatAST(ast);
    }

    toAST() {
        return this._ast;
    }

    toString() {
        return this._expr;
    }

    isPath() {
        const envValueReqExp = /\b(True|False|None|self|uid|context|context_today|active_id|active_ids|allowed_company_ids|current_company_id|active_model|current_date)\b/;
        return !envValueReqExp.test(this._expr);
    }
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

/**
 * @param {Value} value
 * @returns  {import("@web/core/py_js/py_parser").AST}
 */
export function toAST(value) {
    if (value instanceof Expression) {
        return value.toAST();
    }
    if (Array.isArray(value)) {
        return { type: 4, value: value.map(toAST) };
    }
    return toPyValue(value);
}

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
 * @property {Value} value
 * @property {boolean} negate
 */

/**
 * @typedef {Object} Expression
 * @property {"expression"} type
 * @property {Value} value
 */

/**
 * @typedef {Object} AND
 * @property {"connector"} type
 * @property {boolean} negate
 * @property {"&"} value
 * @property {(Connector|OR)[]} children
 */

/**
 * @typedef {Object} OR
 * @property {"connector"} type
 * @property {boolean} negate
 * @property {"|"} value
 * @property {(Connector|AND)[]} children
 */

/**
 * @typedef {AND|OR|Condition} Tree
 */

/**
 * @param {AST[]} ASTs
 * @param {boolean} distributeNot
 * @param {boolean} [negate=false]
 * @returns {{ tree: Tree, remaimingASTs: AST[] }}
 */
function _construcTree(ASTs, distributeNot, negate = false) {
    const [firstAST, ...tailASTs] = ASTs;

    if (firstAST.type === 1 && firstAST.value === "!") {
        return _construcTree(tailASTs, distributeNot, !negate);
    }

    const tree = { type: firstAST.type === 1 ? "connector" : "condition" };
    if (tree.type === "connector") {
        tree.value = firstAST.value;
        if (distributeNot && negate) {
            tree.value = tree.value === "&" ? "|" : "&";
            tree.negate = false;
        } else {
            tree.negate = negate;
        }
        tree.children = [];
    } else {
        const [pathAST, operatorAST, valueAST] = firstAST.value;
        tree.path = toValue(pathAST);
        const operator = toValue(operatorAST);
        if (negate && typeof operator === "string" && TERM_OPERATORS_NEGATION[operator]) {
            tree.operator = TERM_OPERATORS_NEGATION[operator];
        } else {
            tree.operator = operator;
            tree.negate = negate;
        }
        tree.value = toValue(valueAST);
    }
    let remaimingASTs = tailASTs;
    if (tree.type === "connector") {
        for (let i = 0; i < 2; i++) {
            const { tree: child, remaimingASTs: otherASTs } = _construcTree(
                remaimingASTs,
                distributeNot,
                distributeNot && negate
            );
            remaimingASTs = otherASTs;
            if (child.type === "connector" && !child.negate && child.value === tree.value) {
                tree.children.push(...child.children);
            } else {
                tree.children.push(child);
            }
        }
    }
    return { tree, remaimingASTs };
}

/**
 * @param {AST[]} initialASTs
 * @param {"&"|"|"} [defaultConnector="&"]
 * @param {boolean} [distributeNot=false]
 * @returns {Tree}
 */
function construcTree(initialASTs, options) {
    const value = options.defaultConnector || "&";
    if (!initialASTs.length) {
        return { type: "connector", value, negate: false, children: [] };
    }
    const { tree } = _construcTree(initialASTs, options.distributeNot);
    if (tree.type === "condition") {
        return { type: "connector", value, negate: false, children: [tree] };
    }
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
    if (tree.type === "expression") {
        let expression = tree.value;
        if (tree.negate) {
            expression = `not (${expression})`;
        } else {
            expression = `bool(${expression})`;
        }
        return [{
            type: 10,
            value: [new parseExpr(expression), toAST("="), toAST(1)],
        }];
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

/**
 * @param {Tree} tree
 * @param {boolean} [isRoot=true]
 * @returns {Tree}
 */
function createBetweenOperators(tree, isRoot = true) {
    if (tree.type === "condition" || tree.type === "expression") {
        return tree;
    }
    const processedChildren = tree.children.map((c) => createBetweenOperators(c, false));
    if (tree.value === "|") {
        return { ...tree, children: processedChildren };
    }
    const children = [];
    for (let i = 0; i < processedChildren.length; i++) {
        const child1 = processedChildren[i];
        const child2 = processedChildren[i + 1];
        if (
            child1.type === "condition" &&
            child2 &&
            child2.type === "condition" &&
            formatValue(child1.path) === formatValue(child2.path) &&
            child1.operator === ">=" &&
            child2.operator === "<="
        ) {
            children.push({
                type: "condition",
                negate: false,
                path: child1.path,
                operator: "between",
                value: normalizeValue([child1.value, child2.value]),
            });
            i += 1;
        } else {
            children.push(child1);
        }
    }
    if (children.length === 1 && !isRoot) {
        return { ...children[0] };
    }
    return { ...tree, children };
}

/**
 * @param {Tree} tree
 * @returns {Tree}
 */
function removeBetweenOperators(tree) {
    if (tree.type === "expression") {
        return tree;
    }
    if (tree.type === "condition") {
        if (tree.operator !== "between") {
            return tree;
        }
        const { negate, path, value } = tree;
        return {
            type: "connector",
            negate,
            value: "&",
            children: [
                {
                    type: "condition",
                    negate: false,
                    path,
                    operator: ">=",
                    value: value[0],
                },
                {
                    type: "condition",
                    negate: false,
                    path,
                    operator: "<=",
                    value: value[1],
                },
            ],
        };
    }
    const processedChildren = tree.children.map((c) => removeBetweenOperators(c));
    if (tree.value === "|") {
        return { ...tree, children: processedChildren };
    }
    const children = [];
    // after processing a child might have become a connector "&" --> normalize
    for (let i = 0; i < processedChildren.length; i++) {
        const child = processedChildren[i];
        if (child.type === "connector" && !child.negate && child.value === "&") {
            children.push(...child.children);
        } else {
            children.push(child);
        }
    }
    return { ...tree, children };
}

/**
 * @param {Tree} tree
 * @returns {string} a string representation of a domain
 */
export function toDomain(tree) {
    const simplifiedTree = removeBetweenOperators(tree);
    const domainAST = {
        type: 4,
        value: getASTs(simplifiedTree),
    };
    return formatAST(domainAST);
}

/**
 * @param {DomainRepr} domain
 * @param {Object} [options={}] see construcTree API
 * @returns {Tree} a tree representation of a domain
 */
export function toTree(domain, options = {}) {
    domain = new Domain(domain);
    const domainAST = domain.ast;
    const tree = construcTree(domainAST.value, options);
    return createBetweenOperators(tree);
}


/**
 * @param {Tree} tree
 * @returns {string} a string representation of an python expression
 */
export function toExpression(tree) {
    const simplifiedTree = removeBetweenOperators(tree);
    const ast = getASTs(simplifiedTree);

    const parts = [];
    while (ast.length) {
        const astLeaf = ast.pop();
        if (astLeaf.type === 10) {
            const path = astLeaf.value[0].value;
            const value = formatAST(astLeaf.value[2]);
            let operator = astLeaf.value[1].value;
            if (operator === '=') {
                operator = '==';
            }

            parts.unshift(`${path} ${operator} ${value}`);
        } else if (astLeaf.value === '&') {
            if (parts.length < 2) {
                throw new Error();
            }
            const items = parts.splice(0, Infinity);
            parts.push(`${items.shift()} and ${items.shift()}`);
            parts.push(...items);
        } else if (astLeaf.value === '|') {
            if (parts.length < 2) {
                throw new Error();
            }
            const items = parts.splice(0, Infinity);
            parts.push(`(${items.shift()}) or (${items.shift()})`);
            parts.push(...items);
        } else if (astLeaf.value === '!') {
            if (parts.length < 1) {
                throw new Error();
            }
            const items = parts.splice(0, Infinity);
            parts.push(`not (${items.shift()})`);
            parts.push(...items);
        }
    }
    return parts.join(' and ') || 'True';
}

/**
 * @param {PythonExpression} expression
 * @param {Object} [options={}] see construcTree API
 * @returns {Tree} a tree representation of a domain
 */
export function expressionToTree(expression, options = {}) {
    const ast = new parseExpr(expression);

    function _construcTree(ast, forceTree=false) {
        switch(ast.type) {
            case 0 /* Number */:
            case 1 /* String */:
            case 2 /* Boolean */:
            case 3 /* None */:
            case 10 /* Tuple */:
            case 11 /* Dictionary */: {
                const expr = new Expression(ast);
                if (!forceTree) {
                    return expr;
                }
                return {
                    type: "expression",
                    value: expr.toString(),
                };
            }
            case 5 /* Name */:
            case 12 /* Lookup */:
            case 15 /* ObjLookup */: {
                const expr = new Expression(ast);
                if (!forceTree) {
                    return expr;
                }
                if (expr.isPath()) {
                    return {
                        type: "condition",
                        path: expr.toString(),
                        operator: "!=",
                        value: false,
                    };
                } else {
                    return {
                        type: "expression",
                        value: expr.toString(),
                    };
                }
            }
            case 4 /* List */: {
                const tree = ast.value.length === 1 && _construcTree(ast.value[0], true);
                if (tree?.type !== "expression") {
                    return tree;
                }
                const expr = new Expression(ast);
                if (!forceTree) {
                    return expr;
                }
                return {
                    type: "expression",
                    value: expr.toString(),
                };
            }
            case 8 /* FunctionCall */: {
                if (ast.fn.value === "any") {
                    const tree = _construcTree(ast.args[0]);
                    if (tree.type !== "expression") {
                        return tree;
                    }
                }
                const expr = new Expression(ast);
                if (!forceTree) {
                    return expr;
                }
                return {
                    type: "expression",
                    value: expr.toString(),
                };
            }
            case 6 /* UnaryOperator */: {
                const tree = _construcTree(ast.right, true);
                if (!tree.negate && typeof tree.operator === "string" && TERM_OPERATORS_NEGATION[tree.operator]) {
                    tree.operator = TERM_OPERATORS_NEGATION[tree.operator];
                } else {
                    tree.negate = !tree.negate;
                }
                return tree;
            }
            case 7 /* BinaryOperator */: {
                const left = _construcTree(ast.left);
                const right = _construcTree(ast.right);
                if (!left?.isPath() && !right?.isPath()) {
                    return new Expression(ast);
                }
                switch (ast.op) {
                    case "<":
                    case "<=":
                    case ">":
                    case ">=":
                    case "in":
                    case "not in":
                    case "!=":
                    case "is":
                    case "is not":
                    case "==": {
                        let operator = ast.op;
                        if (operator === "==" || operator === "is") {
                            operator = "=";
                        }
                        if (operator === "is not") {
                            operator = "!=";
                        }
                        return {
                            type: "condition",
                            path: left.toString(),
                            operator: operator,
                            value: right,
                        };
                    }
                    default:
                        return new Expression(ast);
                }
            }
            case 13 /* BinaryOperator */: {
                const ifTrue = _construcTree(ast.ifTrue, true);
                const ifFalse = _construcTree(ast.ifFalse, true);
                const condition = _construcTree(ast.condition, true);
                const notCondition = {...condition, negate: !condition.negate};

                return {
                    type: "connector",
                    value: "|",
                    children: [
                        {
                            type: "connector",
                            value: "&",
                            children: [
                                condition,
                                ifTrue,
                            ],
                        },
                        {
                            type: "connector",
                            value: "&",
                            children: [
                                notCondition,
                                ifFalse,
                            ],
                        }
                    ],
                }
            }
            case 14 /* BooleanOperator */:
                return {
                    type: "connector",
                    value: ast.op === "and" ? "&" : "|",
                    children: [
                        _construcTree(ast.left, true),
                        _construcTree(ast.right, true),
                    ],
                }
            case 16 /* List/Dict/Set comprehension */: {
                const iterator = new Expression(ast.iterator);
                if (!iterator.isPath() || ast.condition?.left.type !== 5) {
                    return {
                        type: "expression",
                        value: formatAST(ast),
                    };
                }
                const condition = new Expression(ast.condition.right);
                return {
                    type: "condition",
                    path: iterator.toString(),
                    operator: "in",
                    value: condition,
                };
            }
        }
    }

    const tree = _construcTree(ast, true);
    return createBetweenOperators(tree);
}
