/** @odoo-module **/

import { _lt, _t } from "@web/core/l10n/translation";
import { Domain } from "@web/core/domain";
import { findOperator, parseOperator } from "./domain_selector_operators";
import { formatAST, toPyValue } from "@web/core/py_js/py_utils";
import { sprintf } from "@web/core/utils/strings";

export class DomainValueExpr {
    constructor(ast) {
        this.ast = ast;
        this.expr = formatAST(ast);
    }
}

class DomainNode {
    static nextId = 0;

    constructor(type, options = {}) {
        this.id = options.id ?? ++DomainNode.nextId;
        this.type = type;
        this.negate = options.negate ?? false;
    }

    toDomain() {
        return new Domain();
    }
}

// ----------------------------------------------------------------------------

const TITLES = {
    AND: {
        false: _lt("all"),
        true: _lt("not all"),
    },
    OR: {
        false: _lt("any"),
        true: _lt("none"),
    },
};

export class BranchDomainNode extends DomainNode {
    constructor(connector, children, options = {}) {
        super("branch", options);
        this.connector = connector;
        this.children = children;
    }

    get title() {
        return TITLES[this.connector][this.negate];
    }

    toDomain() {
        let domain = Domain.combine(
            this.children.map((c) => c.toDomain()),
            this.connector
        );
        if (this.negate) {
            domain = Domain.not(domain);
        }
        return domain;
    }

    add(node) {
        this.children.push(node);
    }

    insertAfter(id, node) {
        const childIndex = this.children.findIndex((c) => c.id === id);
        this.children.splice(childIndex + 1, 0, node);
    }

    delete(id) {
        const childIndex = this.children.findIndex((c) => c.id === id);
        this.children.splice(childIndex, 1);
    }
}

// ----------------------------------------------------------------------------

export class LeafDomainNode extends DomainNode {
    constructor(pathInfo, operatorInfo, value, options = {}) {
        super("leaf", options);
        this.pathInfo = pathInfo;
        this.operatorInfo = operatorInfo;
        this.value = value;
    }

    formatValue(value) {
        if (value instanceof DomainValueExpr) {
            return value.expr;
        } else if (Array.isArray(value)) {
            return `[${value.map((v) => this.formatValue(v)).join(", ")}]`;
        } else {
            return formatAST(toPyValue(value));
        }
    }

    toDomain() {
        const value = this.formatValue(this.value);
        let domain = new Domain(
            `[("${this.pathInfo.path}", "${this.operatorInfo.symbol}", ${value})]`
        );
        if (this.negate) {
            domain = Domain.not(domain);
        }
        return domain;
    }

    clone() {
        return new LeafDomainNode(this.pathInfo, this.operatorInfo, this.value, {
            negate: this.negate,
        });
    }
}

// ----------------------------------------------------------------------------

/**
 * @param {import("@web/core/py_js/py_parser").AST} ast
 * @returns {any}
 */
export function getValue(ast) {
    if ([4, 10].includes(ast.type)) {
        return ast.value.map((v) => getValue(v));
    } else if ([0, 1, 2, 3].includes(ast.type)) {
        return ast.value;
    } else if (ast.type === 6 && ast.op === "-" && ast.right.type === 0) {
        return -ast.right.value;
    } else {
        return new DomainValueExpr(ast);
    }
}
/**
 * @param {import("@web/core/domain_tree").Tree} tree
 * @param {Object} fieldDef
 * @returns
 */
export function getLeafOperatorInfo(tree, fieldDef) {
    const { type: fieldType } = fieldDef || {};
    const rawOperator = tree.operator;
    const negate = tree.negate;
    const isInvalid = typeof rawOperator !== "string" || !parseOperator(rawOperator);
    let operatorInfo;
    if (isInvalid) {
        // symbol not defined
        const operatorInfo = {
            isInvalid: true,
            key: rawOperator,
            label: rawOperator,
            symbol: rawOperator,
        };
        if (negate) {
            operatorInfo.label = sprintf(_t(`not %s`), rawOperator);
        }
        return operatorInfo;
    }

    if (fieldType && fieldType === "boolean") {
        operatorInfo = findOperator(rawOperator === "=" ? "is" : "is_not");
    } else if (tree.valueAST.type === 2) {
        operatorInfo = findOperator(rawOperator === "!=" ? "set" : "not_set");
    } else {
        operatorInfo = parseOperator(rawOperator);
    }

    if (negate) {
        operatorInfo = { ...operatorInfo, label: sprintf(_t(`not %s`), rawOperator) };
    }

    return operatorInfo;
}

/**
 * @param {import("@web/core/domain_tree").Tree} tree
 * @param {Object} pathsInfo
 * @param {LeafDomainNode|BranchDomainNode} [previousTree]
 * @returns {LeafDomainNode|BranchDomainNode}
 */
export function toDomainSelectorTree(tree, pathsInfo, previousTree = null) {
    if (tree.type === "condition") {
        const path = tree.path;
        const negate = tree.negate;
        const pathInfo = pathsInfo[path];
        const operatorInfo = getLeafOperatorInfo(tree, pathInfo.fieldDef);
        const value = getValue(tree.valueAST);
        const id = previousTree instanceof LeafDomainNode ? previousTree.id : null;
        return new LeafDomainNode(pathInfo, operatorInfo, value, { negate, id });
    }
    const connector = tree.value === "&" ? "AND" : "OR";
    const negate = tree.negate;
    const children = tree.children.map((child, index) => {
        const subTree =
            previousTree instanceof BranchDomainNode ? previousTree.children[index] : null;
        return toDomainSelectorTree(child, pathsInfo, subTree);
    });
    const id = previousTree instanceof BranchDomainNode ? previousTree.id : null;
    return new BranchDomainNode(connector, children, { negate, id });
}
