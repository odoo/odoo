import { formatAST, parseExpr } from "@web/core/py_js/py";
import { isBool, isNot } from "./ast_utils";
import {
    astFromValue,
    condition,
    Expression,
    FALSE_TREE,
    isTree,
    TRUE_TREE,
} from "./condition_tree";

function bool(ast) {
    if (isBool(ast) || isNot(ast) || ast.type === 2) {
        return ast;
    }
    return { type: 8, fn: { type: 5, value: "bool" }, args: [ast], kwargs: {} };
}

function getASTs(tree, isSubTree = false) {
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

    if (tree.type === "complex_condition") {
        const ast = parseExpr(tree.value);
        return getASTs(condition(new Expression(bool(ast)), "=", 1));
    }

    const length = tree.children.length;
    if (length === 0) {
        if (tree.value === "|") {
            return tree.negate ? getASTs(TRUE_TREE) : getASTs(FALSE_TREE);
        } else {
            return tree.negate ? getASTs(FALSE_TREE) : isSubTree ? getASTs(TRUE_TREE) : [];
        }
    }

    if (tree.negate) {
        ASTs.push(toAST("!"));
    }
    for (let i = 0; i < length - 1; i++) {
        ASTs.push(toAST(tree.value));
    }
    for (const child of tree.children) {
        ASTs.push(...getASTs(child, true));
    }
    return ASTs;
}

function toAST(value) {
    if (isTree(value)) {
        return { type: 4, value: getASTs(value) };
    }
    return astFromValue(value);
}

export function constructDomainFromTree(tree) {
    return formatAST(toAST(tree));
}
