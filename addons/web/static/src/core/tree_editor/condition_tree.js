import { formatAST, parseExpr } from "@web/core/py_js/py";
import { toPyValue } from "@web/core/py_js/py_utils";

/** @typedef { import("@web/core/py_js/py_parser").AST } AST */
/** @typedef {import("@web/core/domain").DomainRepr} DomainRepr */

/**
 * @typedef {number|string|boolean|Expression} Atom
 * @typedef {Atom|Atom[]} Value
 */

export class Expression {
    static of(ast) {
        return Expression.of(ast);
    }
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

const areEqualValues = (value, otherValue) => formatValue(value) === formatValue(otherValue);

const areEqualArraysOfTrees = (array, otherArray) => {
    if (array.length !== otherArray.length) {
        return false;
    }
    for (let i = 0; i < array.length; i++) {
        const elem = array[i];
        const otherElem = otherArray[i];
        if (!(elem instanceof ConditionTree) || !elem.equals(otherElem)) {
            return false;
        }
    }
    return true;
};

/**
 * @param {import("@web/core/py_js/py_parser").AST} ast
 * @returns {Value}
 */
export function valueFromAST(ast, isWithinArray = false) {
    if ([4, 10].includes(ast.type) && !isWithinArray) {
        /** 4: list, 10: tuple */
        return ast.value.map((v) => valueFromAST(v, true));
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
        return Expression.of(ast);
    }
}

export function ASTFromValue(value) {
    if (value instanceof Expression) {
        return value.toAST();
    }
    if (Array.isArray(value)) {
        return { type: 4, value: value.map(ASTFromValue) };
    }
    return toPyValue(value);
}

export function formatValue(value) {
    return formatAST(ASTFromValue(value));
}

export function normalizeValue(value) {
    return valueFromAST(ASTFromValue(value)); // no array in array (see isWithinArray)
}

export class ConditionTree {
    static get TRUE() {
        return Condition.of(1, "=", 1);
    }
    static get FALSE() {
        return Condition.of(0, "=", 1);
    }
    static get AND() {
        return Connector.of("&");
    }
    static get OR() {
        return Connector.of("|");
    }
    equals(other) {
        return false;
    }
    clone() {
        throw new Error();
    }
}

export class Connector extends ConditionTree {
    /**
     * @param {"&"|"|"} value
     * @param {ConditionTree[]} [children=[]]
     * @param {boolean} [negate=false]
     */
    static of(value, children, negate) {
        return new Connector(value, children, negate);
    }
    /**
     * @param {"&"|"|"} value
     * @param {ConditionTree[]} [children=[]]
     * @param {boolean} [negate=false]
     */
    constructor(value, children = [], negate = false) {
        super();
        this.value = value;
        this.children = children;
        this.negate = negate;
    }
    equals(other) {
        return (
            other instanceof Connector &&
            this.value === other.value &&
            areEqualArraysOfTrees(this.children, other.children) &&
            this.negate === other.negate
        );
    }
    clone() {
        return Connector.of(
            this.value,
            // @ts-ignore
            this.children.map((child) => child.clone()),
            this.negate
        );
    }
}

export class Condition extends ConditionTree {
    /**
     * @param {Value} path
     * @param {Value} operator
     * @param {Value|ConditionTree} value
     * @param {boolean} [negate=false]
     */
    static of(path, operator, value, negate = false) {
        return new Condition(path, operator, value, negate);
    }
    /**
     * @param {Value} path
     * @param {Value} operator
     * @param {Value|ConditionTree} value
     * @param {boolean} [negate=false]
     */
    constructor(path, operator, value, negate = false) {
        super();
        this.path = path;
        this.operator = operator;
        this.value = value;
        this.negate = negate;
    }
    equals(other) {
        return other instanceof Condition &&
            areEqualValues(this.path, other.path) &&
            areEqualValues(this.operator, other.operator) &&
            this.negate === other.negate &&
            isTree(this.value)
            ? isTree(other.value)
                ? this.value.equals(other.value)
                : false
            : areEqualValues(this.value, other.value);
    }
    clone() {
        return Condition.of(
            cloneValue(this.path),
            cloneValue(this.operator),
            // @ts-ignore
            isTree(this.value) ? this.value.clone() : cloneValue(this.value),
            this.negate
        );
    }
}

export class ComplexCondition extends ConditionTree {
    /**
     * @param {string} str
     */
    static of(str) {
        return new ComplexCondition(str);
    }
    /**
     * @param {string} str
     */
    constructor(str) {
        super();
        this.value = str;
    }
    equals(other) {
        return other instanceof ComplexCondition && this.value === other.value;
    }
    clone() {
        return ComplexCondition.of(this.value);
    }
}

/**
 * @param {Value} value
 * @returns {Value}
 */
function cloneValue(value) {
    if (value instanceof Expression) {
        return Expression.of(value.toAST());
    }
    if (Array.isArray(value)) {
        return value.map(cloneValue);
    }
    return value;
}

export function isTree(value) {
    return value instanceof ConditionTree;
}

/**
 * @param {Connector} parent
 * @param {ConditionTree} child
 */
export function addChild(parent, child) {
    if (child instanceof Connector && !child.negate && child.value === parent.value) {
        parent.children.push(...child.children);
    } else {
        parent.children.push(child);
    }
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
 * @param {ConditionTree} tree
 * @param {Options} [options={}]
 * @param {"condition"|"connector"|"complex_condition"} [treeType="condition"]
 * @returns {ConditionTree}
 */
export function operate(
    transformation,
    tree,
    options = {},
    treeType = "condition",
    traverseSubTrees = true
) {
    if (tree instanceof Connector) {
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
    if (traverseSubTrees && tree instanceof Condition && isTree(tree.value)) {
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
