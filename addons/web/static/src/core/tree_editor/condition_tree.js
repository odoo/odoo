import { Domain } from "@web/core/domain";
import { formatAST, parseExpr } from "@web/core/py_js/py";
import { toPyValue } from "@web/core/py_js/py_utils";

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
 * @property {(value: Value) => (null|Object)} [getFieldDef]
 * @property {boolean} [distributeNot]
 */

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
 * @param {string} value
 * @returns {ComplexCondition}
 */
export function complexCondition(value) {
    parseExpr(value);
    return { type: "complex_condition", value };
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

export const TRUE_TREE = condition(1, "=", 1);
export const FALSE_TREE = condition(0, "=", 1);

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

const areEqualValues = (value, otherValue) => formatValue(value) === formatValue(otherValue);

const areEqualArraysOfTrees = (array, otherArray) => {
    if (array.length !== otherArray.length) {
        return false;
    }
    for (let i = 0; i < array.length; i++) {
        const elem = array[i];
        const otherElem = otherArray[i];
        if (!areEqualTrees(elem, otherElem)) {
            return false;
        }
    }
    return true;
};

export const areEqualTrees = (tree, otherTree) => {
    if (tree.type !== otherTree.type) {
        return false;
    }
    if (tree.negate !== otherTree.negate) {
        return false;
    }
    if (tree.type === "condition") {
        if (!areEqualValues(tree.path, otherTree.path)) {
            return false;
        }
        if (!areEqualValues(tree.operator, otherTree.operator)) {
            return false;
        }
        if (isTree(tree.value)) {
            if (isTree(otherTree.value)) {
                return areEqualTrees(tree.value, otherTree.value);
            }
            return false;
        } else if (isTree(otherTree.value)) {
            return false;
        }
        if (!areEqualValues(tree.value, otherTree.value)) {
            return false;
        }
        return true;
    }
    if (!areEqualValues(tree.value, otherTree.value)) {
        return false;
    }
    if (tree.type === "complex_condition") {
        return true;
    }
    return areEqualArraysOfTrees(tree.children, otherTree.children);
};

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

export function astFromValue(value) {
    if (value instanceof Expression) {
        return value.toAST();
    }
    if (Array.isArray(value)) {
        return { type: 4, value: value.map(astFromValue) };
    }
    return toPyValue(value);
}

export function formatValue(value) {
    return formatAST(astFromValue(value));
}

export function normalizeValue(value) {
    return toValue(astFromValue(value)); // no array in array (see isWithinArray)
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
 * @param {Connector} parent
 * @param {Tree} child
 */
export function addChild(parent, child) {
    if (child.type === "connector" && !child.negate && child.value === parent.value) {
        parent.children.push(...child.children);
    } else {
        parent.children.push(child);
    }
}

export function applyTransformations(transformations, transformed, ...fixedParams) {
    for (let i = transformations.length - 1; i >= 0; i--) {
        const fn = transformations[i];
        transformed = fn(transformed, ...fixedParams);
    }
    return transformed;
}

function normalizeConnector(connector) {
    const newTree = { ...connector, children: [] };
    for (const child of connector.children) {
        addChild(newTree, child);
    }
    if (newTree.children.length === 1) {
        const child = newTree.children[0];
        if (newTree.negate) {
            const newChild = { ...child, negate: !child.negate };
            if (newChild.type === "condition") {
                return newChild;
            }
            return newChild;
        }
        return child;
    }
    return newTree;
}

function makeOptions(path, options) {
    return {
        ...options,
        getFieldDef: (p) => {
            if (typeof path === "string" && typeof p === "string") {
                return options.getFieldDef?.(`${path}.${p}`) || null;
            }
            return null;
        },
    };
}

/**
 * @param {Function} transformation
 * @param {Tree} tree
 * @param {Options} [options={}]
 * @param {"condition"|"connector"|"complex_condition"} [treeType="condition"]
 * @returns {Tree}
 */
export function operate(
    transformation,
    tree,
    options = {},
    treeType = "condition",
    traverseSubTrees = true
) {
    if (tree.type === "connector") {
        const newTree = {
            ...tree,
            children: tree.children.map((c) =>
                operate(transformation, c, options, treeType, traverseSubTrees)
            ),
        };
        if (treeType === "connector") {
            return normalizeConnector(transformation(newTree, options) || newTree);
        }
        return normalizeConnector(newTree);
    }
    const clone = cloneTree(tree);
    if (traverseSubTrees && tree.type === "condition" && isTree(tree.value)) {
        clone.value = operate(
            transformation,
            tree.value,
            makeOptions(tree.path, options),
            treeType,
            traverseSubTrees
        );
    }
    if (treeType === tree.type) {
        return transformation(clone, options) || clone;
    }
    return clone;
}

export function rewriteNConsecutiveChildren(transformation, N = 2) {
    return (c, options) => {
        const children = [];
        const currentChildren = c.children;
        for (let i = 0; i < currentChildren.length; i++) {
            const NconsecutiveChildren = currentChildren.slice(i, i + N);
            let replacement = null;
            if (NconsecutiveChildren.length === N) {
                replacement = transformation(connector(c.value, NconsecutiveChildren), options);
            }
            if (replacement) {
                children.push(replacement);
                i += N - 1;
            } else {
                children.push(NconsecutiveChildren[0]);
            }
        }
        return { ...c, children };
    };
}
