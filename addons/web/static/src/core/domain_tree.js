/** @odoo-module **/

import { Domain } from "@web/core/domain";
import { formatAST, toPyValue } from "@web/core/py_js/py_utils";

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

/** @typedef { import("@web/core/py_js/py_parser").AST } AST */
/** @typedef {import("@web/core/domain").DomainRepr} DomainRepr */

/**
 * @typedef {Object} Condition
 * @property {"condition"} type
 * @property {string|1|0} path
 * @property {string} operator
 * @property {AST} valueAST
 * @property {boolean} negate // used in case operator has no negation defined
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
        tree.path = pathAST.value;
        if (negate && TERM_OPERATORS_NEGATION[operatorAST.value]) {
            tree.operator = TERM_OPERATORS_NEGATION[operatorAST.value];
        } else {
            tree.operator = operatorAST.value;
            tree.negate = negate;
        }
        tree.valueAST = valueAST;
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
    if (tree.type === "condition") {
        return [
            {
                type: 10,
                value: [toPyValue(tree.path), toPyValue(tree.operator), tree.valueAST],
            },
        ];
    }

    const ASTs = [];
    const length = tree.children.length;
    if (length && tree.negate) {
        ASTs.push(toPyValue("!"));
    }
    for (let i = 0; i < length - 1; i++) {
        ASTs.push(toPyValue(tree.value));
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
    if (tree.type === "condition") {
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
            child1.path === child2.path &&
            child1.operator === ">=" &&
            child2.operator === "<="
        ) {
            children.push({
                type: "condition",
                negate: false,
                path: child1.path,
                operator: "between",
                valueAST: {
                    type: 4,
                    value: [child1.valueAST, child2.valueAST],
                },
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
    if (tree.type === "condition") {
        if (tree.operator !== "between") {
            return tree;
        }
        const { path, valueAST } = tree;
        return {
            type: "connector",
            negate: false,
            value: "&",
            children: [
                { type: "condition", path, operator: ">=", valueAST: valueAST.value[0] },
                { type: "condition", path, operator: "<=", valueAST: valueAST.value[1] },
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
